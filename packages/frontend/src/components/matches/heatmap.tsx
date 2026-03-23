'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { Crosshair, Download, Loader2 } from 'lucide-react'
import { api } from '@/lib/api-client'

const MAP_WIDTH = 600
const MAP_HEIGHT = 600

interface HeatmapPoint {
  x: number
  y: number
  z?: number
  player_steam_id: string
  round_number?: number
  type: string
  severity?: string
  intensity: number
}

interface HeatmapData {
  match_id: string
  map: string
  heatmap_type: string
  total_points: number
  positioned_points: HeatmapPoint[]
  summary: {
    total_kills: number
    total_deaths: number
    players: number
  }
}

interface HeatmapProps {
  matchId: string
}

type BuyFilter = 'all' | 'pistol' | 'eco' | 'force' | 'full'

export function Heatmap({ matchId }: HeatmapProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [data, setData] = useState<HeatmapData | null>(null)
  const [loading, setLoading] = useState(true)
  const [heatmapType, setHeatmapType] = useState<'kills' | 'deaths'>('deaths')
  const [showErrors, setShowErrors] = useState(true)
  const [buyFilter, setBuyFilter] = useState<BuyFilter>('all')
  const [sideFilter, setSideFilter] = useState<'all' | 'T' | 'CT'>('all')

  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      let url = `/matches/${matchId}/heatmap?type=${heatmapType}`
      if (sideFilter !== 'all') url += `&side=${sideFilter}`
      const result = await api.get<HeatmapData>(url)
      setData(result)
    } catch {
      // Heatmap data may not be available
    } finally {
      setLoading(false)
    }
  }, [matchId, heatmapType, sideFilter])

  useEffect(() => {
    loadData()
  }, [loadData])

  useEffect(() => {
    if (!data || !canvasRef.current) return

    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // Clear
    ctx.fillStyle = '#0a0a0f'
    ctx.fillRect(0, 0, MAP_WIDTH, MAP_HEIGHT)

    // Draw grid
    ctx.strokeStyle = '#1a1a2e'
    ctx.lineWidth = 0.5
    for (let i = 0; i < MAP_WIDTH; i += 50) {
      ctx.beginPath()
      ctx.moveTo(i, 0)
      ctx.lineTo(i, MAP_HEIGHT)
      ctx.stroke()
      ctx.beginPath()
      ctx.moveTo(0, i)
      ctx.lineTo(MAP_WIDTH, i)
      ctx.stroke()
    }

    // Draw map name + type
    ctx.fillStyle = '#4a4a6a'
    ctx.font = '14px monospace'
    ctx.fillText(`${data.map} — ${heatmapType}`, 10, 20)

    // Filter points by buy type if needed
    const points = data.positioned_points
    if (buyFilter !== 'all') {
      // Buy type filter would need round economy data joined
      // For now, all points pass through
    }

    // Draw positioned points as heatmap dots
    for (const point of points) {
      const x = ((point.x + 3000) / 6000) * MAP_WIDTH
      const y = ((point.y + 3000) / 6000) * MAP_HEIGHT

      const radius = point.intensity * 12
      const gradient = ctx.createRadialGradient(x, y, 0, x, y, radius)

      if (!showErrors && point.severity) continue

      if (point.severity === 'critical') {
        gradient.addColorStop(0, 'rgba(255, 50, 50, 0.8)')
        gradient.addColorStop(1, 'rgba(255, 50, 50, 0)')
      } else if (point.severity === 'minor') {
        gradient.addColorStop(0, 'rgba(255, 180, 50, 0.6)')
        gradient.addColorStop(1, 'rgba(255, 180, 50, 0)')
      } else {
        gradient.addColorStop(0, 'rgba(100, 150, 255, 0.6)')
        gradient.addColorStop(1, 'rgba(100, 150, 255, 0)')
      }

      ctx.fillStyle = gradient
      ctx.beginPath()
      ctx.arc(x, y, radius, 0, Math.PI * 2)
      ctx.fill()
    }

    // Legend
    ctx.fillStyle = '#8888aa'
    ctx.font = '11px monospace'
    ctx.fillText(
      `${data.summary.total_kills} kills / ${data.summary.total_deaths} deaths | ${points.length} positioned`,
      10,
      MAP_HEIGHT - 10
    )
  }, [data, showErrors, buyFilter, heatmapType])

  const exportPNG = () => {
    if (!canvasRef.current) return
    const link = document.createElement('a')
    link.download = `heatmap-${matchId}-${heatmapType}.png`
    link.href = canvasRef.current.toDataURL('image/png')
    link.click()
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-10">
        <Loader2 className="h-5 w-5 text-text-muted animate-spin" />
      </div>
    )
  }

  if (!data) return null

  return (
    <div className="mb-6">
      <h2 className="text-lg font-bold mb-3 flex items-center gap-2">
        <Crosshair className="h-4 w-4 text-primary" />
        Heatmap
      </h2>
      <div className="bg-bg-card border border-border rounded-xl p-4">
        {/* Filter row 1: type + side */}
        <div className="flex flex-wrap gap-2 mb-2">
          {(['kills', 'deaths'] as const).map((t) => (
            <button
              key={t}
              onClick={() => setHeatmapType(t)}
              className={`px-3 py-1 rounded text-xs ${
                heatmapType === t ? 'bg-primary text-white' : 'bg-bg-elevated text-text-muted'
              }`}
            >
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
          <span className="border-l border-border mx-1" />
          {(['all', 'T', 'CT'] as const).map((s) => (
            <button
              key={s}
              onClick={() => setSideFilter(s)}
              className={`px-3 py-1 rounded text-xs ${
                sideFilter === s ? 'bg-primary text-white' : 'bg-bg-elevated text-text-muted'
              }`}
            >
              {s === 'all' ? 'Both' : s}
            </button>
          ))}
        </div>

        {/* Filter row 2: buy type + overlays + export */}
        <div className="flex flex-wrap items-center gap-2 mb-3">
          {(['all', 'pistol', 'eco', 'force', 'full'] as const).map((b) => (
            <button
              key={b}
              onClick={() => setBuyFilter(b)}
              className={`px-2 py-0.5 rounded text-[10px] ${
                buyFilter === b ? 'bg-primary/80 text-white' : 'bg-bg-elevated text-text-dim'
              }`}
            >
              {b === 'all' ? 'All Rounds' : b.charAt(0).toUpperCase() + b.slice(1)}
            </button>
          ))}
          <span className="border-l border-border mx-1" />
          <label className="flex items-center gap-1 text-xs text-text-muted cursor-pointer">
            <input
              type="checkbox"
              checked={showErrors}
              onChange={(e) => setShowErrors(e.target.checked)}
              className="rounded border-border"
            />
            Show Errors
          </label>
          <button
            onClick={exportPNG}
            className="ml-auto flex items-center gap-1 px-2 py-1 text-xs bg-bg-elevated text-text-muted rounded hover:text-text"
          >
            <Download className="h-3 w-3" />
            PNG
          </button>
        </div>

        <canvas
          ref={canvasRef}
          width={MAP_WIDTH}
          height={MAP_HEIGHT}
          className="w-full max-w-[600px] rounded border border-border"
        />
      </div>
    </div>
  )
}
