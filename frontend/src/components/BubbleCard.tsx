import { Flag, Loader2 } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'
import type { Box } from '@/types'

interface Props {
  box: Box
  index: number
  selected: boolean
  busy: boolean
  onSelect: () => void
  onChange: (patch: Partial<Box>) => void
  onOcr: () => void
  onDraft: () => void
  onDelete: () => void
}

export function BubbleCard({ box, index, selected, busy, onSelect, onChange, onOcr, onDraft, onDelete }: Props) {
  return (
    <Card className={cn('gap-3 p-3', selected && 'ring-2 ring-green-500')} onClick={onSelect}>
      <div className="flex items-center gap-2">
        <strong>#{index + 1}</strong>
        <Button size="sm" variant="outline" disabled={busy} onClick={onOcr}>
          OCR
        </Button>
        <Button size="sm" disabled={busy || !box.ja} onClick={onDraft}>
          {busy ? <Loader2 className="animate-spin" /> : 'Draft / Check'}
        </Button>
        <span className="flex-1" />
        <Button size="sm" variant="ghost" onClick={onDelete}>
          Delete
        </Button>
      </div>

      <div className="grid gap-1.5">
        <Label className="text-muted-foreground">Japanese (editable if OCR is off)</Label>
        <Textarea className="text-lg" value={box.ja} onChange={(e) => onChange({ ja: e.target.value })} />
      </div>

      <div className="grid gap-1.5">
        <Label className="text-muted-foreground">Your draft</Label>
        <Textarea
          value={box.draft}
          placeholder="Write your own translation, then hit Draft / check"
          onChange={(e) => onChange({ draft: e.target.value })}
        />
      </div>

      {(box.suggestion || box.literal) && (
        <div className="grid gap-2">
          <Label className="text-muted-foreground">Suggested</Label>
          <p>{box.suggestion}</p>
          <div className="flex gap-2">
            <Button size="sm" variant="outline" onClick={() => onChange({ final: box.suggestion })}>
              Use
            </Button>
            <Button size="sm" variant="outline" onClick={() => onChange({ draft: box.suggestion })}>
              Copy to draft
            </Button>
          </div>
          <Collapsible>
            <CollapsibleTrigger className="text-muted-foreground cursor-pointer text-sm">
              Literal gloss &amp; notes
            </CollapsibleTrigger>
            <CollapsibleContent className="text-muted-foreground space-y-1 pt-1 text-sm">
              <div>Literal: {box.literal}</div>
              {box.notes && <div>Notes: {box.notes}</div>}
            </CollapsibleContent>
          </Collapsible>
          {box.flags.map((f, i) => (
            <Badge key={i} variant="outline" className="h-auto items-start gap-1.5 py-1 text-left whitespace-normal text-amber-500">
              <Flag className="mt-0.5 shrink-0" /> {f}
            </Badge>
          ))}
        </div>
      )}

      <div className="grid gap-1.5">
        <Label className="text-muted-foreground">Final</Label>
        <Textarea
          value={box.final}
          placeholder="Leave blank to export draft → suggestion"
          onChange={(e) => onChange({ final: e.target.value })}
        />
      </div>
    </Card>
  )
}
