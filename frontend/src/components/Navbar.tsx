import { useEffect, useState, type ReactNode } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { listProjects } from '@/lib/api'
import type { ProjectSummary } from '@/types'

interface Props {
  /** Current project; shows the project switcher when set. */
  projectId?: string
  /** Page-level actions rendered after the switcher. */
  children?: ReactNode
}

export function Navbar({ projectId, children }: Props) {
  const navigate = useNavigate()
  const [projects, setProjects] = useState<ProjectSummary[]>([])

  useEffect(() => {
    if (projectId) listProjects().then(setProjects, () => setProjects([]))
  }, [projectId])

  return (
    <header className="flex items-center gap-3 border-b px-4 py-2.5">
      <Link to="/" className="mr-2 text-base font-semibold hover:opacity-80">
        Scanji
      </Link>
      {projectId && (
        <Select value={projectId} onValueChange={(id) => navigate(`/p/${id}`)}>
          <SelectTrigger className="w-52" aria-label="Switch project">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {projects.map((p) => (
              <SelectItem key={p.id} value={p.id}>
                {p.title}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      )}
      {children}
    </header>
  )
}
