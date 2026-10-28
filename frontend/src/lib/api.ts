import type { Box, DraftResult, Project } from '@/types'
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

export const pageUrl = (name: string) => `/api/pages/${encodeURIComponent(name)}`

export async function getProject(): Promise<Project> {
  // Older project files may lack newer fields, so merge over the defaults.
  return { ...emptyProject(), ...(await request<Partial<Project>>('/api/project')) }
}

export const putProject = (p: Project) => request<{ ok: boolean }>('/api/project', json('PUT', p))

export function uploadPage(file: File): Promise<{ name: string }> {
  const fd = new FormData()
  fd.append('file', file)
  return request('/api/pages', { method: 'POST', body: fd })
}

export const ocrRegion = (page: string, b: Pick<Box, 'x' | 'y' | 'w' | 'h'>) =>
  request<{ ja: string }>('/api/ocr', json('POST', { page, x: b.x, y: b.y, w: b.w, h: b.h }))

export const draftBubble = (body: {
  ja: string
  draft: string
  context: string
  glossary: Project['glossary']
  neighbors: string[]
}) => request<DraftResult>('/api/draft', json('POST', body))

export const exportScript = () => request<string>('/api/export')
