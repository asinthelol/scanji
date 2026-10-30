export interface Box {
  id: string
  // natural pixel space of the page image
  x: number
  y: number
  w: number
  h: number
  ja: string
  draft: string
  suggestion: string
  literal: string
  notes: string
  flags: string[]
  final: string
}

export interface GlossaryEntry {
  ja: string
  en: string
  note: string
}

export interface ExportSettings {
  title_heading: string
  page_heading: string
}

export interface Chapter {
  id: string
  title: string
  pages: Record<string, Box[]>
}

export interface Project {
  title: string
  export: ExportSettings
  context: string // shared by all chapters
  glossary: GlossaryEntry[] // shared by all chapters
  chapters: Chapter[]
}

export interface ProjectSummary {
  id: string
  title: string
  chapters: number
  pages: number
  bubbles: number
  updated: number // unix seconds
}

export interface DraftResult {
  literal: string
  suggestion: string
  notes: string
  flags: string[]
}

export const emptyProject = (): Project => ({
  title: '',
  export: { title_heading: '# {title} - {chapter}', page_heading: '## {page}' },
  context: '',
  glossary: [],
  chapters: [],
})

export const newBox = (x: number, y: number, w: number, h: number): Box => ({
  id: Math.random().toString(36).slice(2, 9),
  x,
  y,
  w,
  h,
  ja: '',
  draft: '',
  suggestion: '',
  literal: '',
  notes: '',
  flags: [],
  final: '',
})
