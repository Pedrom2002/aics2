'use client'

import { useEffect, useRef, useState } from 'react'

export interface PlayerDot {
  steam_id: string
  name: string
  side: 'T' | 'CT'
  x: number // 0..1 normalized on map
  y: number // 0..1 normalized on map
  alive: boolean
}

interface MapCanvasProps {
  width?: number
  height?: number
  mapName?: string
  players: PlayerDot[]
  highlightSteamId?: string | null
}

const RADAR_MAPS = new Set([
  'de_mirage',
  'de_inferno',
  'de_dust2',
  'de_nuke',
  'de_anubis',
  'de_ancient',
  'de_vertigo',
  'de_overpass',
  'de_train',
])

function radarUrl(mapName: string | undefined): string | null {
  if (!mapName) return null
  const slug = mapName.toLowerCase()
  if (!RADAR_MAPS.has(slug)) return null
  return `/radars/${slug}.png`
}

/**
 * Canvas-based map renderer with optional radar image background.
 * Player positions are expected as normalized 0..1 coordinates.
 */
export function MapCanvas({
  width = 520,
  height = 520,
  mapName,
  players,
  highlightSteamId,
}: MapCanvasProps) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null)
  const [radar, setRadar] = useState<HTMLImageElement | null>(null)

  useEffect(() => {
    const url = radarUrl(mapName)
    if (!url) {
      setRadar(null)
      return
    }
    const img = new Image()
    img.src = url
    img.onload = () => setRadar(img)
    img.onerror = () => setRadar(null)
    return () => {
      img.onload = null
      img.onerror = null
    }
  }, [mapName])

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    ctx.fillStyle = '#0c0c14'
    ctx.fillRect(0, 0, width, height)

    if (radar) {
      ctx.globalAlpha = 0.85
      ctx.drawImage(radar, 0, 0, width, height)
      ctx.globalAlpha = 1
    } else {
      ctx.strokeStyle = 'rgba(255,255,255,0.05)'
      ctx.lineWidth = 1
      const step = 32
      for (let x = 0; x <= width; x += step) {
        ctx.beginPath()
        ctx.moveTo(x, 0)
        ctx.lineTo(x, height)
        ctx.stroke()
      }
      for (let y = 0; y <= height; y += step) {
        ctx.beginPath()
        ctx.moveTo(0, y)
        ctx.lineTo(width, y)
        ctx.stroke()
      }
    }

    if (mapName) {
      ctx.fillStyle = radar ? 'rgba(255,255,255,0.85)' : 'rgba(255,255,255,0.2)'
      ctx.font = 'bold 14px sans-serif'
      ctx.fillText(mapName.toUpperCase(), 12, 22)
    }

    for (const p of players) {
      const cx = p.x * width
      const cy = p.y * height
      const color = p.side === 'T' ? '#f59e0b' : '#3b82f6'
      ctx.globalAlpha = p.alive ? 1 : 0.35

      ctx.beginPath()
      ctx.arc(cx, cy, 8, 0, Math.PI * 2)
      ctx.fillStyle = color
      ctx.fill()
      ctx.strokeStyle = 'rgba(0,0,0,0.6)'
      ctx.lineWidth = 1
      ctx.stroke()

      if (highlightSteamId === p.steam_id) {
        ctx.strokeStyle = '#ffffff'
        ctx.lineWidth = 2
        ctx.beginPath()
        ctx.arc(cx, cy, 12, 0, Math.PI * 2)
        ctx.stroke()
      }

      ctx.globalAlpha = 1
      ctx.fillStyle = '#ffffff'
      ctx.strokeStyle = 'rgba(0,0,0,0.8)'
      ctx.lineWidth = 3
      ctx.font = '10px sans-serif'
      ctx.strokeText(p.name, cx + 10, cy + 3)
      ctx.fillText(p.name, cx + 10, cy + 3)
    }
  }, [width, height, players, mapName, highlightSteamId, radar])

  return (
    <canvas
      ref={canvasRef}
      width={width}
      height={height}
      className="rounded-lg border border-border bg-bg-card"
      style={{ width, height }}
    />
  )
}
