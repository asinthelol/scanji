import {
  closestCenter,
  DndContext,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import { restrictToParentElement, restrictToVerticalAxis } from '@dnd-kit/modifiers'
import { arrayMove,SortableContext, sortableKeyboardCoordinates, verticalListSortingStrategy } from '@dnd-kit/sortable'
import { Loader2 } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'
import { BubbleCard } from '@/components/BubbleCard'
import { PageViewer } from '@/components/PageViewer'
import { ProjectSettings } from '@/components/ProjectSettings'
import { Button } from '@/components/ui/button'
import { Navbar } from '@/components/Navbar'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { useProject } from '@/hooks/useProject'
import { detectBubbles, draftBubble, exportScript, getProject, ocrRegion, readingOrder, uploadPage } from '@/lib/api'
import { newBox, type Box } from '@/types'

const NEIGHBOR_RADIUS = 3 // bubbles of context sent on each side
const DUPLICATE_OVERLAP = 0.3 // detected boxes overlapping an existing one this much are skipped

/** Intersection over union of two boxes. */
function overlap(a: Pick<Box, 'x' | 'y' | 'w' | 'h'>, b: Pick<Box, 'x' | 'y' | 'w' | 'h'>) {
  const w = Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x)
  const h = Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y)
  if (w <= 0 || h <= 0) return 0
  return (w * h) / (a.w * a.h + b.w * b.h - w * h)
}

export default function Workspace({ projectId }: { projectId: string }) {
  const { project, loaded, update, flush } = useProject(projectId)
  const [chosenPage, setChosenPage] = useState('')
  const [selectedId, setSelectedId] = useState('')
  const [detecting, setDetecting] = useState(false)
  const [busy, setBusy] = useState<ReadonlySet<string>>(new Set())

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }), // a normal click on the handle is not a drag
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  )

  const pageNames = Object.keys(project.pages)
  const page = pageNames.includes(chosenPage) ? chosenPage : (pageNames[0] ?? '')
  const boxes = page ? (project.pages[page] ?? []) : []

  const setBox = (id: string, patch: Partial<Box>) =>
    update((p) => ({
      ...p,
      pages: { ...p.pages, [page]: p.pages[page].map((b) => (b.id === id ? { ...b, ...patch } : b)) },
    }))

  const withBusy = async (id: string, task: () => Promise<void>) => {
    setBusy((s) => new Set(s).add(id))
    try {
      await task()
    } finally {
      setBusy((s) => {
        const next = new Set(s)
        next.delete(id)
        return next
      })
    }
  }

  const runOcr = (b: Pick<Box, 'id' | 'x' | 'y' | 'w' | 'h'>) =>
    withBusy(b.id, async () => {
      try {
        const { ja } = await ocrRegion(projectId, page, b)
        setBox(b.id, { ja })
      } catch (e) {
        toast.error(`OCR failed: ${(e as Error).message}`)
      }
    })

  const runDraft = (b: Box) =>
    withBusy(b.id, async () => {
      const i = boxes.findIndex((x) => x.id === b.id)
      const neighbors = boxes
        .slice(Math.max(0, i - NEIGHBOR_RADIUS), i + NEIGHBOR_RADIUS + 1)
        .filter((n) => n.id !== b.id && n.ja)
        .map((n) => n.ja)
      try {
        const d = await draftBubble({ ja: b.ja, draft: b.draft, context: project.context, glossary: project.glossary, neighbors })
        setBox(b.id, { suggestion: d.suggestion, literal: d.literal, notes: d.notes, flags: d.flags })
      } catch (e) {
        toast.error(`Draft failed: ${(e as Error).message}`)
      }
    })

  const createBox = (r: { x: number; y: number; w: number; h: number }) => {
    const box = newBox(r.x, r.y, r.w, r.h)
    update((p) => ({ ...p, pages: { ...p.pages, [page]: [...(p.pages[page] ?? []), box] } }))
    setSelectedId(box.id)
    runOcr(box)
  }

  const onDetect = async () => {
    setDetecting(true)
    try {
      const { boxes: found } = await detectBubbles(projectId, page)
      const fresh = found
        .filter((d) => !boxes.some((b) => overlap(b, d) > DUPLICATE_OVERLAP))
        .map((d) => newBox(d.x, d.y, d.w, d.h))
      if (!fresh.length) {
        toast.info(found.length ? 'No new bubbles; everything detected is already boxed.' : 'No bubbles detected.')
        return
      }
      update((p) => ({ ...p, pages: { ...p.pages, [page]: [...(p.pages[page] ?? []), ...fresh] } }))
      toast.success(`Added ${fresh.length} bubble${fresh.length > 1 ? 's' : ''}. Running OCR…`)
      for (const b of fresh) await runOcr(b) // manga-ocr handles one crop at a time
    } catch (e) {
      toast.error(`Detection failed: ${(e as Error).message}`)
    } finally {
      setDetecting(false)
    }
  }

  const onSortOrder = async () => {
    try {
      const { ids } = await readingOrder(boxes)
      update((p) => {
        const byId = new Map(p.pages[page].map((b) => [b.id, b]))
        return { ...p, pages: { ...p.pages, [page]: ids.map((id) => byId.get(id)!) } }
      })
    } catch (e) {
      toast.error(`Sorting failed: ${(e as Error).message}`)
    }
  }

  const onDragEnd = ({ active, over }: DragEndEvent) => {
    if (!over || active.id === over.id) return
    update((p) => {
      const list = p.pages[page]
      const from = list.findIndex((b) => b.id === active.id)
      const to = list.findIndex((b) => b.id === over.id)
      return { ...p, pages: { ...p.pages, [page]: arrayMove(list, from, to) } }
    })
  }

  const removeBox = (id: string) =>
    update((p) => ({ ...p, pages: { ...p.pages, [page]: p.pages[page].filter((b) => b.id !== id) } }))

  const onUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? [])
    e.target.value = ''
    let last = ''
    for (const f of files) {
      try {
        last = (await uploadPage(projectId, f)).name
      } catch (err) {
        toast.error(`${f.name}: ${(err as Error).message}`)
      }
    }
    try {
      // The server registered the new pages. Take its page list (and order) but keep local boxes,
      // so unsaved edits survive and the next save does not overwrite the new pages.
      const server = await getProject(projectId)
      update((p) => ({
        ...p,
        pages: Object.fromEntries(Object.keys(server.pages).map((n) => [n, p.pages[n] ?? server.pages[n]])),
      }))
      if (last) setChosenPage(last)
    } catch (err) {
      toast.error(`Could not refresh pages: ${(err as Error).message}`)
    }
  }

  const onExport = async () => {
    try {
      await flush()
      const text = await exportScript(projectId)
      const a = document.createElement('a')
      a.href = URL.createObjectURL(new Blob([text], { type: 'text/markdown' }))
      a.download = `${project.title || 'script'}.md`
      a.click()
      URL.revokeObjectURL(a.href)
    } catch (err) {
      toast.error(`Export failed: ${(err as Error).message}`)
    }
  }

  if (!loaded) return null

  return (
    <div className="flex h-screen flex-col">
      <Navbar projectId={projectId}>
        <Select value={page} onValueChange={setChosenPage} disabled={!pageNames.length}>
          <SelectTrigger className="w-40">
            <SelectValue placeholder="No pages" />
          </SelectTrigger>
          <SelectContent>
            {pageNames.map((n) => (
              <SelectItem key={n} value={n}>
                {n}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Button variant="outline" asChild>
          <label className="cursor-pointer">
            Add pages
            <input type="file" accept="image/*" multiple hidden onChange={onUpload} />
          </label>
        </Button>
        <Button variant="outline" disabled={!page || detecting} onClick={onDetect}>
          {detecting && <Loader2 className="animate-spin" />} Detect bubbles
        </Button>
        <Button variant="outline" disabled={boxes.length < 2} onClick={onSortOrder} title="Right-to-left, top-to-bottom">
          Sort order
        </Button>
        <span className="flex-1" />
        <Button onClick={onExport}>Export script</Button>
      </Navbar>

      <main className="grid min-h-0 flex-1 grid-cols-[minmax(0,1.2fr)_minmax(360px,1fr)]">
        <section className="overflow-auto border-r p-4">
          {page ? (
            <PageViewer projectId={projectId} page={page} boxes={boxes} selectedId={selectedId} onSelect={setSelectedId} onCreate={createBox} />
          ) : (
            <p className="text-muted-foreground p-6">Add a page image to start. Drag on the page to draw a box around each bubble.</p>
          )}
        </section>

        <section className="space-y-3 overflow-auto p-4">
          <ProjectSettings project={project} update={update} />
          {page && !boxes.length && <p className="text-muted-foreground p-6">Drag on the page to add a bubble.</p>}
          {/* A dragged card is moved by a transform, which would otherwise
              extend the scroll area, and auto-scroll would then chase it forever. */}
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            modifiers={[restrictToVerticalAxis, restrictToParentElement]}
            onDragEnd={onDragEnd}
          >
            <SortableContext items={boxes.map((b) => b.id)} strategy={verticalListSortingStrategy}>
              <div className="space-y-3">
                {boxes.map((b, i) => (
                  <BubbleCard
                    key={b.id}
                    box={b}
                    index={i}
                    selected={b.id === selectedId}
                    busy={busy.has(b.id)}
                    onSelect={() => setSelectedId(b.id)}
                    onChange={(patch) => setBox(b.id, patch)}
                    onOcr={() => runOcr(b)}
                    onDraft={() => runDraft(b)}
                    onDelete={() => removeBox(b.id)}
                  />
                ))}
              </div>
            </SortableContext>
          </DndContext>
        </section>
      </main>
    </div>
  )
}
