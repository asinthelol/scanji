import type { Box, DraftResult, Project, ProjectSummary } from '@/types'
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

// ---- pages ----

export const pageUrl = (pid: string, name: string) => `${projectUrl(pid)}/pages/${encodeURIComponent(name)}`

export function uploadPage(pid: string, file: File): Promise<{ name: string }> {
  const fd = new FormData()
  fd.append('file', file)
  return request(`${projectUrl(pid)}/pages`, { method: 'POST', body: fd })
}

// ---- OCR, detection, drafting, export ----

export const ocrRegion = (pid: string, page: string, b: Pick<Box, 'x' | 'y' | 'w' | 'h'>) =>
  request<{ ja: string }>(`${projectUrl(pid)}/ocr`, json('POST', { page, x: b.x, y: b.y, w: b.w, h: b.h }))

export interface DetectedBox {
  x: number
  y: number
  w: number
  h: number
  kind: string
  score: number
}

/** Detect bubble text regions in reading order. */
export const detectBubbles = (pid: string, page: string, includeFree = false) =>
  request<{ boxes: DetectedBox[] }>(`${projectUrl(pid)}/detect`, json('POST', { page, include_free: includeFree }))

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

export const exportScript = (pid: string) => request<string>(`${projectUrl(pid)}/export`)
