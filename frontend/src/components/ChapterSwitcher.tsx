import { Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import type { Chapter } from '@/types'

interface Props {
  chapters: Chapter[]
  // Id of the open chapter, '' when there is none.
  value: string
  onChange: (id: string) => void
  onCreate: (title: string) => Promise<void>
  onDelete: (chapter: Chapter) => Promise<void>
}

/** Chapter select with add and delete (both ask for details or confirmation in a dialog). */
export function ChapterSwitcher({ chapters, value, onChange, onCreate, onDelete }: Props) {
  const [creating, setCreating] = useState(false)
  const [title, setTitle] = useState('')
  const [confirmingDelete, setConfirmingDelete] = useState(false)
  const current = chapters.find((c) => c.id === value)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!title.trim()) return
    await onCreate(title.trim())
    setCreating(false)
    setTitle('')
  }

  return (
    <>
      <Select value={value} onValueChange={onChange} disabled={!chapters.length}>
        <SelectTrigger className="w-44" aria-label="Switch chapter">
          <SelectValue placeholder="No chapters" />
        </SelectTrigger>
        <SelectContent>
          {chapters.map((c) => (
            <SelectItem key={c.id} value={c.id}>
              {c.title}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Button size="icon" variant="outline" aria-label="Add chapter" onClick={() => setCreating(true)}>
        <Plus />
      </Button>
      <Button
        size="icon"
        variant="ghost"
        aria-label="Delete chapter"
        disabled={!current}
        onClick={() => setConfirmingDelete(true)}
      >
        <Trash2 />
      </Button>

      <AlertDialog open={creating} onOpenChange={setCreating}>
        <AlertDialogContent>
          <form onSubmit={submit} className="grid gap-4">
            <AlertDialogHeader>
              <AlertDialogTitle>New chapter</AlertDialogTitle>
              <AlertDialogDescription>
                Chapters keep their own pages and are exported separately. They share the project's glossary and context.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <Input autoFocus value={title} placeholder="e.g. Chapter 12" onChange={(e) => setTitle(e.target.value)} />
            <AlertDialogFooter>
              <AlertDialogCancel type="button">Cancel</AlertDialogCancel>
              <Button type="submit" disabled={!title.trim()}>
                Create chapter
              </Button>
            </AlertDialogFooter>
          </form>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog open={confirmingDelete} onOpenChange={setConfirmingDelete}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete "{current?.title}"?</AlertDialogTitle>
            <AlertDialogDescription>
              This permanently deletes the chapter's pages, bubbles and drafts. It cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={() => current && onDelete(current)}>Delete chapter</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  )
}
