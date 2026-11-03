import { Loader2, Search } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { lookupWord } from '@/lib/api'
import type { DictionaryEntry, DictionaryResult } from '@/types'

const TYPING_DELAY_MS = 300
const SETUP_POLL_MS = 1500 // while the dictionary downloads for the first time

function Entry({ entry }: { entry: DictionaryEntry }) {
  return (
    <Card className="gap-2 p-3">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="text-lg font-medium">{(entry.kanji.length ? entry.kanji : entry.kana).join('、')}</span>
        {entry.kanji.length > 0 && <span className="text-muted-foreground">{entry.kana.join('、')}</span>}
        {entry.common && (
          <Badge variant="secondary" className="ml-auto">
            common
          </Badge>
        )}
      </div>
      <ol className="space-y-1 text-sm">
        {entry.senses.map((sense, i) => {
          // part of speech is shown once per run of senses that share it
          const pos = sense.pos.join(', ')
          const showPos = pos && pos !== entry.senses[i - 1]?.pos.join(', ')
          return (
            <li key={i}>
              {showPos && <div className="text-muted-foreground mt-1.5 text-xs">{pos}</div>}
              <span className="text-muted-foreground mr-1.5">{i + 1}.</span>
              {sense.gloss.join('; ')}
            </li>
          )
        })}
      </ol>
    </Card>
  )
}

/** Offline JMdict lookup by Japanese word, reading or English. */
export function DictionaryPanel() {
  const [query, setQuery] = useState('')
  const [result, setResult] = useState<DictionaryResult | null>(null)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0) // bumped by Retry
  const q = query.trim()

  useEffect(() => {
    let cancelled = false
    let timer: ReturnType<typeof setTimeout>
    const run = async () => {
      try {
        const r = await lookupWord(q)
        if (cancelled) return
        setResult(r)
        setError('')
        if (r.status === 'downloading' || r.status === 'indexing') timer = setTimeout(run, SETUP_POLL_MS)
      } catch (e) {
        if (!cancelled) setError((e as Error).message)
      }
    }
    // An empty search still asks, which starts the first-run download as soon as the panel opens.
    timer = setTimeout(run, q ? TYPING_DELAY_MS : 0)
    return () => {
      cancelled = true
      clearTimeout(timer)
    }
  }, [q, attempt])

  const settingUp = result?.status === 'downloading' || result?.status === 'indexing'
  const failure = error || (result?.status === 'error' ? result.message : '')

  return (
    <div className="grid content-start gap-3">
      <div className="relative">
        <Search className="text-muted-foreground absolute top-2.5 left-2.5 size-4" />
        <Input
          autoFocus
          className="pl-8"
          value={query}
          placeholder="Japanese, reading, or English"
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>

      {settingUp && (
        <p className="text-muted-foreground flex items-center gap-2 text-sm">
          <Loader2 className="size-4 animate-spin" /> {result.message}
        </p>
      )}

      {failure && (
        <div className="grid justify-items-start gap-2 text-sm">
          <p className="text-destructive">{failure}</p>
          <Button size="sm" variant="outline" onClick={() => setAttempt((n) => n + 1)}>
            Retry
          </Button>
        </div>
      )}

      {result?.status === 'ready' && result.fallback === 'inflection' && (
        <p className="text-muted-foreground text-sm">
          No entry for "{q}". Showing dictionary forms of "{result.stem}…".
        </p>
      )}
      {result?.status === 'ready' && result.fallback === 'prefix' && (
        <p className="text-muted-foreground text-sm">
          No entry for "{q}". Showing words that start with "{result.stem}".
        </p>
      )}
      {result?.status === 'ready' && q && !result.entries.length && (
        <p className="text-muted-foreground text-sm">No entries for "{q}".</p>
      )}
      {result?.status === 'ready' && !q && (
        <p className="text-muted-foreground text-sm">
          Look up a word. Conjugated forms such as 食べた find their dictionary form. Dictionary: JMdict.
        </p>
      )}

      {result?.status === 'ready' && result.entries.map((entry) => <Entry key={entry.id} entry={entry} />)}
    </div>
  )
}
