import { Plus, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import type { GlossaryEntry, Project } from '@/types'

interface Props {
  project: Project
  update: (fn: (p: Project) => Project) => void
}

export function ProjectSettings({ project, update }: Props) {
  const setEntry = (i: number, patch: Partial<GlossaryEntry>) =>
    update((p) => ({ ...p, glossary: p.glossary.map((g, j) => (j === i ? { ...g, ...patch } : g)) }))

  return (
    <Card className="p-3">
      <Collapsible>
        <CollapsibleTrigger className="text-muted-foreground cursor-pointer text-sm">
          Series context, glossary &amp; export
        </CollapsibleTrigger>
        <CollapsibleContent className="grid gap-4 pt-3">
          <div className="grid gap-1.5">
            <Label className="text-muted-foreground">Context (characters, tone, setting)</Label>
            <Textarea
              value={project.context}
              placeholder="e.g. School comedy. X is a blunt, deadpan class rep. Casual speech."
              onChange={(e) => update((p) => ({ ...p, context: e.target.value }))}
            />
          </div>

          <div className="grid gap-1.5">
            <Label className="text-muted-foreground">
              Export headings ({'{title}'}, {'{chapter}'} and {'{page}'} are replaced; blank = no heading line)
            </Label>
            <div className="flex gap-2">
              <Input
                value={project.export.title_heading}
                placeholder="# {title} - {chapter}"
                onChange={(e) => update((p) => ({ ...p, export: { ...p.export, title_heading: e.target.value } }))}
              />
              <Input
                value={project.export.page_heading}
                placeholder="## {page}"
                onChange={(e) => update((p) => ({ ...p, export: { ...p.export, page_heading: e.target.value } }))}
              />
            </div>
          </div>

          <div className="grid gap-1.5">
            <Label className="text-muted-foreground">Glossary</Label>
            {project.glossary.map((g, i) => (
              <div key={i} className="flex gap-2">
                <Input className="w-[30%]" value={g.ja} placeholder="JA" onChange={(e) => setEntry(i, { ja: e.target.value })} />
                <Input className="w-[30%]" value={g.en} placeholder="EN" onChange={(e) => setEntry(i, { en: e.target.value })} />
                <Input value={g.note} placeholder="note" onChange={(e) => setEntry(i, { note: e.target.value })} />
                <Button
                  size="icon"
                  variant="ghost"
                  aria-label="Remove term"
                  onClick={() => update((p) => ({ ...p, glossary: p.glossary.filter((_, j) => j !== i) }))}
                >
                  <X />
                </Button>
              </div>
            ))}
            <Button
              size="sm"
              variant="outline"
              className="w-fit"
              onClick={() => update((p) => ({ ...p, glossary: [...p.glossary, { ja: '', en: '', note: '' }] }))}
            >
              <Plus /> Term
            </Button>
          </div>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  )
}
