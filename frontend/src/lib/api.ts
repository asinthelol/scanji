import type { Box, DictionaryResult, DraftResult, Project, ProjectSummary } from '@/types'
import { emptyProject } from '@/types'

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, init)
  if (!res.ok) {
    let detail = res.statusText
    try {
      detail = (await res.json()).detail ?? detail
    } catch {
      /* body was not JSON */
    }
    throw new Error(detail)
  }
  const type = res.headers.get('content-type') ?? ''
  return (type.includes('json') ? res.json() : res.text()) as Promise<T>
}

const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

const projectUrl = (pid: string) => `/api/projects/${encodeURIComponent(pid)}`

// ---- projects ----

export const listProjects = () => request<ProjectSummary[]>('/api/projects')

export const createProject = (title: string) =>
  request<{ id: string; title: string }>('/api/projects', json('POST', { title }))

export const deleteProject = (pid: string) => request<{ ok: boolean }>(projectUrl(pid), { method: 'DELETE' })

export async function getProject(pid: string): Promise<Project> {
  // Older project files may lack newer fields, so merge over the defaults.
  return { ...emptyProject(), ...(await request<Partial<Project>>(projectUrl(pid))) }
}

export const putProject = (pid: string, p: Project) => request<{ ok: boolean }>(projectUrl(pid), json('PUT', p))

// ---- chapters ----

const chapterUrl = (pid: string, cid: string) => `${projectUrl(pid)}/chapters/${encodeURIComponent(cid)}`

export const createChapter = (pid: string, title: string) =>
  request<{ id: string; title: string }>(`${projectUrl(pid)}/chapters`, json('POST', { title }))

export const deleteChapter = (pid: string, cid: string) =>
  request<{ ok: boolean }>(chapterUrl(pid, cid), { method: 'DELETE' })

// ---- pages ----

export const pageUrl = (pid: string, cid: string, name: string) =>
  `${chapterUrl(pid, cid)}/pages/${encodeURIComponent(name)}`

export function uploadPage(pid: string, cid: string, file: File): Promise<{ name: string }> {
  const fd = new FormData()
  fd.append('file', file)
  return request(`${chapterUrl(pid, cid)}/pages`, { method: 'POST', body: fd })
}

// ---- OCR, detection, drafting, export ----

export const ocrRegion = (pid: string, cid: string, page: string, b: Pick<Box, 'x' | 'y' | 'w' | 'h'>) =>
  request<{ ja: string }>(`${chapterUrl(pid, cid)}/ocr`, json('POST', { page, x: b.x, y: b.y, w: b.w, h: b.h }))

export interface DetectedBox {
  x: number
  y: number
  w: number
  h: number
  kind: string
  score: number
}

/** Detect bubble text regions in reading order. */
export const detectBubbles = (pid: string, cid: string, page: string, includeFree = false) =>
  request<{ boxes: DetectedBox[] }>(`${chapterUrl(pid, cid)}/detect`, json('POST', { page, include_free: includeFree }))

/** Box ids sorted into manga reading order. */
export const readingOrder = (boxes: Pick<Box, 'id' | 'x' | 'y' | 'w' | 'h'>[]) =>
  request<{ ids: string[] }>('/api/reading-order', json('POST', { boxes }))

export const draftBubble = (body: {
  ja: string
  draft: string
  context: string
  glossary: Project['glossary']
  neighbors: string[]
}) => request<DraftResult>('/api/draft', json('POST', body))

export const exportScript = (pid: string, cid: string) => request<string>(`${chapterUrl(pid, cid)}/export`)

// ---- dictionary ----

export const lookupWord = (q: string) => request<DictionaryResult>(`/api/dictionary?q=${encodeURIComponent(q)}`)
