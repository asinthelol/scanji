import { Plus, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import { Navbar } from '@/components/Navbar'
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
import { Card } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { createProject, deleteProject, listProjects } from '@/lib/api'
import type { ProjectSummary } from '@/types'

const plural = (n: number, word: string) => `${n} ${word}${n === 1 ? '' : 's'}`

export default function Home() {
  const navigate = useNavigate()
  const [projects, setProjects] = useState<ProjectSummary[] | null>(null)
  const [name, setName] = useState('')
  const [pendingDelete, setPendingDelete] = useState<ProjectSummary | null>(null)

  const refresh = () => listProjects().then(setProjects, (e) => toast.error(`Could not load projects: ${e.message}`))
  useEffect(() => {
    refresh()
  }, [])

  const onCreate = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return
    try {
      const { id } = await createProject(name.trim())
      navigate(`/p/${id}`)
    } catch (err) {
      toast.error(`Could not create project: ${(err as Error).message}`)
    }
  }

  const onDelete = async () => {
    if (!pendingDelete) return
    try {
      await deleteProject(pendingDelete.id)
      toast.success(`Deleted "${pendingDelete.title}"`)
    } catch (err) {
      toast.error(`Could not delete project: ${(err as Error).message}`)
    }
    setPendingDelete(null)
    refresh()
  }

  return (
    <div className="flex h-screen flex-col">
      <Navbar />
      <main className="mx-auto w-full max-w-3xl flex-1 overflow-auto p-6">
        <h2 className="mb-4 text-xl font-semibold">Projects</h2>

        <form onSubmit={onCreate} className="mb-6 flex gap-2">
          <Input value={name} placeholder="New project name (the series)" onChange={(e) => setName(e.target.value)} />
          <Button type="submit" disabled={!name.trim()}>
            <Plus /> Add project
          </Button>
        </form>

        {projects && !projects.length && (
          <p className="text-muted-foreground">No projects yet. Name one above to get started.</p>
        )}

        <div className="grid gap-3">
          {projects?.map((p) => (
            <Card key={p.id} className="flex-row items-center gap-3 p-4">
              <Link to={`/p/${p.id}`} className="flex-1 hover:opacity-80">
                <div className="font-medium">{p.title}</div>
                <div className="text-muted-foreground text-sm">
                  {plural(p.chapters, 'chapter')} · {plural(p.pages, 'page')} · {plural(p.bubbles, 'bubble')} · edited{' '}
                  {new Date(p.updated * 1000).toLocaleDateString()}
                </div>
              </Link>
              <Button size="icon" variant="ghost" aria-label={`Delete ${p.title}`} onClick={() => setPendingDelete(p)}>
                <Trash2 />
              </Button>
            </Card>
          ))}
        </div>
      </main>

      <AlertDialog open={!!pendingDelete} onOpenChange={(open) => !open && setPendingDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete "{pendingDelete?.title}"?</AlertDialogTitle>
            <AlertDialogDescription>
              This permanently deletes the project's chapters, pages, bubbles, drafts and glossary. It cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={onDelete}>Delete project</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
