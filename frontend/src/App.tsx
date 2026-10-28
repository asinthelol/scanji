import { useState } from 'react'
import { toast } from 'sonner'
import { BubbleCard } from '@/components/BubbleCard'
import { PageViewer } from '@/components/PageViewer'
import { ProjectSettings } from '@/components/ProjectSettings'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Toaster } from '@/components/ui/sonner'
import { useProject } from '@/hooks/useProject'
import { draftBubble, exportScript, ocrRegion, uploadPage } from '@/lib/api'
import { newBox, type Box } from '@/types'

const NEIGHBOR_RADIUS = 3 // bubbles of context sent on each side

export default function App() {
  const { project, loaded, update, flush, reload } = useProject()
  const [chosenPage, setChosenPage] = useState('')
  const [selectedId, setSelectedId] = useState('')
  const [busy, setBusy] = useState<ReadonlySet<string>>(new Set())

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
        const { ja } = await ocrRegion(page, b)
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

  const removeBox = (id: string) =>
    update((p) => ({ ...p, pages: { ...p.pages, [page]: p.pages[page].filter((b) => b.id !== id) } }))

  const onUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? [])
    e.target.value = ''
    let last = ''
    for (const f of files) {
      try {
        last = (await uploadPage(f)).name
      } catch (err) {
        toast.error(`${f.name}: ${(err as Error).message}`)
      }
    }
    await flush() // persist pending edits before the server's page list replaces local state
    await reload()
    if (last) setChosenPage(last)
  }

  const onExport = async () => {
    try {
      await flush()
      const text = await exportScript()
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
      <header className="flex items-center gap-3 border-b px-4 py-2.5">
        <h1 className="mr-2 text-base font-semibold">manga-assist</h1>
        <Input
          className="w-60"
          value={project.title}
          placeholder="Series / chapter title"
          onChange={(e) => update((p) => ({ ...p, title: e.target.value }))}
        />
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
        <span className="flex-1" />
        <Button onClick={onExport}>Export script</Button>
      </header>

      <main className="grid min-h-0 flex-1 grid-cols-[minmax(0,1.2fr)_minmax(360px,1fr)]">
        <section className="overflow-auto border-r p-4">
          {page ? (
            <PageViewer page={page} boxes={boxes} selectedId={selectedId} onSelect={setSelectedId} onCreate={createBox} />
          ) : (
            <p className="text-muted-foreground p-6">Add a page image to start. Drag on the page to draw a box around each bubble.</p>
          )}
        </section>

        <section className="space-y-3 overflow-auto p-4">
          <ProjectSettings project={project} update={update} />
          {page && !boxes.length && <p className="text-muted-foreground p-6">Drag on the page to add a bubble.</p>}
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
        </section>
      </main>
      <Toaster />
    </div>
  )
}
