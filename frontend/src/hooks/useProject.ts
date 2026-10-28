import { useCallback, useEffect, useRef, useState } from 'react'
import { toast } from 'sonner'
import { getProject, putProject } from '@/lib/api'
import { emptyProject, type Project } from '@/types'

const SAVE_DELAY_MS = 250

/** Project state with debounced autosave to the backend. */
export function useProject() {
  const [project, setProject] = useState<Project>(emptyProject)
  const [loaded, setLoaded] = useState(false)
  const latest = useRef(project)
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined)

  const flush = useCallback(async () => {
    clearTimeout(timer.current)
    try {
      await putProject(latest.current)
    } catch (e) {
      toast.error(`Save failed: ${(e as Error).message}`)
    }
  }, [])

  const update = useCallback(
    (fn: (p: Project) => Project) => {
      latest.current = fn(latest.current)
      setProject(latest.current)
      clearTimeout(timer.current)
      timer.current = setTimeout(flush, SAVE_DELAY_MS)
    },
    [flush],
  )

  /** Replace state with what the server has, without triggering a save. */
  const reload = useCallback(async () => {
    const p = await getProject()
    latest.current = p
    setProject(p)
  }, [])

  useEffect(() => {
    reload()
      .catch((e) => toast.error(`Could not load project: ${e.message}`))
      .finally(() => setLoaded(true))
  }, [reload])

  return { project, loaded, update, flush, reload }
}
