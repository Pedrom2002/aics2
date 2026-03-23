'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { Crosshair, Loader2 } from 'lucide-react'
import { api } from '@/lib/api-client'

// CS2 map dimensions (approximate normalized coordinates)
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

export function Heatmap({ matchId }: HeatmapProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [data, setData] = useState<HeatmapData | null>(null)
  const [loading, setLoading] = useState(true)
  const [heatmapType, setHeatmapType] = useState<'kills' | 'deaths'>('deaths')

  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      const result = await api.get<HeatmapData>(
        `/matches/${matchId}/heatmap?type=${heatmapType}`
      )
      setData(result)
    } catch {
      // Heatmap data may not be available
    } finally {
      setLoading(false)
    }
  }, [matchId, heatmapType])

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

    // Draw map name
    ctx.fillStyle = '#4a4a6a'
    ctx.font = '14px monospace'
    ctx.fillText(data.map, 10, 20)

    // Draw positioned points as heatmap dots
    for (const point of data.positioned_points) {
      // Normalize coordinates to canvas
      const x = ((point.x + 3000) / 6000) * MAP_WIDTH
      const y = ((point.y + 3000) / 6000) * MAP_HEIGHT

      const radius = point.intensity * 12
      const gradient = ctx.createRadialGradient(x, y, 0, x, y, radius)

      if (point.severity === 'critical') {
        gradient.addColorStop(0, 'rgba(255, 50, 50, 0.8)')
        gradient.addColorStop(1, 'rgba(255, 50, 50, 0)')
      } else {
        gradient.addColorStop(0, 'rgba(255, 180, 50, 0.6)')
        gradient.addColorStop(1, 'rgba(255, 180, 50, 0)')
      }

      ctx.fillStyle = gradient
      ctx.beginPath()
      ctx.arc(x, y, radius, 0, Math.PI * 2)
      ctx.fill()
    }

    // Legend
    ctx.fillStyle = '#8888aa'
    ctx.font = '11px monospace'
    ctx.fillText(`${data.summary.total_kills} kills / ${data.summary.total_deaths} deaths`, 10, MAP_HEIGHT - 10)
  }, [data])

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
        <div className="flex gap-2 mb-3">
          <button
            onClick={() => setHeatmapType('kills')}
            className={`px-3 py-1 rounded text-xs ${
              heatmapType === 'kills'
                ? 'bg-primary text-white'
                : 'bg-bg-elevated text-text-muted'
            }`}
          >
            Kills
          </button>
          <button
            onClick={() => setHeatmapType('deaths')}
            className={`px-3 py-1 rounded text-xs ${
              heatmapType === 'deaths'
                ? 'bg-primary text-white'
                : 'bg-bg-elevated text-text-muted'
            }`}
          >
            Deaths
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
