import { useCallback, useEffect, useRef, useState } from 'react'
import { toast } from 'sonner'
import { getProject, putProject } from '@/lib/api'
import { emptyProject, type Project } from '@/types'

const SAVE_DELAY_MS = 250

/**
 * One project's state with debounced autosave to the backend.
 * Mount it with `key={projectId}` so switching projects starts from fresh state.
 */
export function useProject(projectId: string) {
  const [project, setProject] = useState<Project>(emptyProject)
  const [loaded, setLoaded] = useState(false)
  const latest = useRef(project)
  const timer = useRef<ReturnType<typeof setTimeout>>(undefined)
  const dirty = useRef(false)

  const flush = useCallback(async () => {
    clearTimeout(timer.current)
    dirty.current = false
    try {
      await putProject(projectId, latest.current)
    } catch (e) {
      toast.error(`Save failed: ${(e as Error).message}`)
    }
  }, [projectId])

  const update = useCallback(
    (fn: (p: Project) => Project) => {
      latest.current = fn(latest.current)
      setProject(latest.current)
      dirty.current = true
      clearTimeout(timer.current)
      timer.current = setTimeout(flush, SAVE_DELAY_MS)
    },
    [flush],
  )

  useEffect(() => {
    let cancelled = false
    getProject(projectId)
      .then((p) => {
        if (cancelled) return
        latest.current = p
        setProject(p)
        setLoaded(true)
      })
      .catch((e) => !cancelled && toast.error(`Could not load project: ${e.message}`))
    return () => {
      cancelled = true
      if (dirty.current) flush() // leaving the project (or the app) with an unsaved edit
    }
  }, [projectId, flush])

  return { project, loaded, update, flush }
}
