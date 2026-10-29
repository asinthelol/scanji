import { useEffect, useRef, useState } from 'react'
import { pageUrl } from '@/lib/api'
import { cn } from '@/lib/utils'
import type { Box } from '@/types'

const MIN_BOX_PX = 12 // smaller drags count as clicks

interface Rect {
  x: number
  y: number
  w: number
  h: number
}

interface Props {
  projectId: string
  page: string
  boxes: Box[]
  selectedId: string
  onSelect: (id: string) => void
  onCreate: (rect: Rect) => void
}

/** Page image with draw-to-create bubble boxes. Boxes are stored in natural image pixels. */
export function PageViewer({ projectId, page, boxes, selectedId, onSelect, onCreate }: Props) {
  const stage = useRef<HTMLDivElement>(null)
  const img = useRef<HTMLImageElement>(null)
  const [scale, setScale] = useState(1) // natural px per displayed px
  const [drawing, setDrawing] = useState<Rect | null>(null)
  const origin = useRef<{ x: number; y: number } | null>(null)

  /*
   * Measures the user's selection area scale from the image element itself.
   * The page viewer cahched its scale before images finished loading, resulting
   * in a scale of 0.
  */ 
  const measure = () => {
    const el = img.current
    return el && el.naturalWidth && el.clientWidth ? el.naturalWidth / el.clientWidth : 0
  }

  useEffect(() => {
    const el = img.current
    if (!el) return
    const observer = new ResizeObserver(() => setScale(measure() || 1))
    observer.observe(el)
    return () => observer.disconnect()
  }, [page])

  const point = (e: React.PointerEvent) => {
    const r = stage.current!.getBoundingClientRect()
    return {
      x: Math.max(0, Math.min(e.clientX - r.left, r.width)),
      y: Math.max(0, Math.min(e.clientY - r.top, r.height)),
    }
  }

  const onPointerDown = (e: React.PointerEvent) => {
    if (!measure()) return // image not loaded yet; a box would collapse to zero size
    e.currentTarget.setPointerCapture(e.pointerId)
    origin.current = point(e)
    setDrawing({ ...origin.current, w: 0, h: 0 })
  }

  const onPointerMove = (e: React.PointerEvent) => {
    const o = origin.current
    if (!o) return
    const p = point(e)
    setDrawing({ x: Math.min(o.x, p.x), y: Math.min(o.y, p.y), w: Math.abs(p.x - o.x), h: Math.abs(p.y - o.y) })
  }

  const onPointerUp = () => {
    const d = drawing
    origin.current = null
    setDrawing(null)
    if (!d) return
    const k = measure()
    if (d.w >= MIN_BOX_PX && d.h >= MIN_BOX_PX && k) {
      onCreate({ x: d.x * k, y: d.y * k, w: d.w * k, h: d.h * k })
      return
    }
    // A click: select the topmost box under the pointer.
    const hit = [...boxes].reverse().find(
      (b) => d.x >= b.x / scale && d.x <= (b.x + b.w) / scale && d.y >= b.y / scale && d.y <= (b.y + b.h) / scale,
    )
    if (hit) onSelect(hit.id)
  }

  const style = (r: Rect, k: number) => ({ left: r.x * k, top: r.y * k, width: r.w * k, height: r.h * k })

  return (
    <div
      ref={stage}
      className="relative inline-block cursor-crosshair touch-none select-none"
      onPointerDown={onPointerDown}
      onPointerMove={onPointerMove}
      onPointerUp={onPointerUp}
    >
      <img ref={img} src={pageUrl(projectId, page)} alt={page} draggable={false} onLoad={() => setScale(measure() || 1)} className="block h-auto max-w-full" />
      {boxes.map((b, i) => (
        <div
          key={b.id}
          style={style(b, 1 / scale)}
          className={cn(
            'pointer-events-none absolute border-2',
            b.id === selectedId ? 'border-green-500 bg-green-500/20' : 'border-blue-400 bg-blue-400/10',
          )}
        >
          <span
            className={cn(
              'absolute -top-px -left-px rounded-br px-1.5 text-[11px] text-black',
              b.id === selectedId ? 'bg-green-500' : 'bg-blue-400',
            )}
          >
            {i + 1}
          </span>
        </div>
      ))}
      {drawing && (
        <div style={style(drawing, 1)} className="pointer-events-none absolute border-2 border-blue-400 bg-blue-400/10" />
      )}
    </div>
  )
}
