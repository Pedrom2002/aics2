'use client'

import { useCallback, useEffect, useState } from 'react'
import { Loader2, Pause, Play, SkipBack, SkipForward } from 'lucide-react'
import { api } from '@/lib/api-client'

interface ReplayPlayer {
  steam_id: string
  name: string
  side: string | null
  kills: number
  deaths: number
  adr: number | null
  rating: number | null
}

interface ReplayRound {
  round_number: number
  winner_side: string | null
  win_reason: string | null
  team1_score: number
  team2_score: number
  bomb_planted: boolean | null
  bomb_defused: boolean | null
  plant_site: string | null
  duration_seconds: number | null
  t_buy_type: string | null
  ct_buy_type: string | null
}

interface ReplayData {
  match_id: string
  map: string
  tickrate: number
  total_rounds: number
  players: ReplayPlayer[]
  rounds: ReplayRound[]
}

interface ReplayViewerProps {
  matchId: string
}

export function ReplayViewer({ matchId }: ReplayViewerProps) {
  const [data, setData] = useState<ReplayData | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedRound, setSelectedRound] = useState(1)
  const [isPlaying, setIsPlaying] = useState(false)

  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      const result = await api.get<ReplayData>(`/matches/${matchId}/replay`)
      setData(result)
    } catch {
      // Replay data may not be available
    } finally {
      setLoading(false)
    }
  }, [matchId])

  useEffect(() => {
    loadData()
  }, [loadData])

  // Auto-play through rounds
  useEffect(() => {
    if (!isPlaying || !data) return
    const timer = setInterval(() => {
      setSelectedRound((prev) => {
        if (prev >= data.total_rounds) {
          setIsPlaying(false)
          return prev
        }
        return prev + 1
      })
    }, 2000) // 2 seconds per round
    return () => clearInterval(timer)
  }, [isPlaying, data])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-10">
        <Loader2 className="h-5 w-5 text-text-muted animate-spin" />
      </div>
    )
  }

  if (!data || data.rounds.length === 0) return null

  const currentRound = data.rounds.find((r) => r.round_number === selectedRound)
  const tPlayers = data.players.filter((p) => p.side === 'T')
  const ctPlayers = data.players.filter((p) => p.side === 'CT')

  return (
    <div className="mb-6">
      <h2 className="text-lg font-bold mb-3 flex items-center gap-2">
        <Play className="h-4 w-4 text-primary" />
        2D Replay
      </h2>
      <div className="bg-bg-card border border-border rounded-xl p-4">
        {/* Controls */}
        <div className="flex items-center gap-3 mb-4">
          <button
            onClick={() => setSelectedRound(Math.max(1, selectedRound - 1))}
            className="p-1.5 rounded bg-bg-elevated hover:bg-bg-elevated/80 transition-colors"
          >
            <SkipBack className="h-4 w-4" />
          </button>
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            className="p-2 rounded bg-primary hover:bg-primary/80 text-white transition-colors"
          >
            {isPlaying ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
          </button>
          <button
            onClick={() => setSelectedRound(Math.min(data.total_rounds, selectedRound + 1))}
            className="p-1.5 rounded bg-bg-elevated hover:bg-bg-elevated/80 transition-colors"
          >
            <SkipForward className="h-4 w-4" />
          </button>
          <span className="text-sm text-text-muted">
            Round {selectedRound} / {data.total_rounds}
          </span>
          <input
            type="range"
            min={1}
            max={data.total_rounds}
            value={selectedRound}
            onChange={(e) => setSelectedRound(Number(e.target.value))}
            className="flex-1"
          />
        </div>

        {/* Round Info */}
        {currentRound && (
          <div className="grid grid-cols-3 gap-4 mb-4 text-sm">
            <div className="bg-bg-elevated rounded-lg p-3 text-center">
              <div className="text-amber-400 font-bold text-lg">
                {currentRound.team1_score}
              </div>
              <div className="text-text-dim text-xs">T-Side</div>
              <div className="text-text-muted text-xs mt-1">
                {currentRound.t_buy_type || '-'}
              </div>
            </div>
            <div className="flex flex-col items-center justify-center">
              <div className={`text-xs font-medium px-2 py-0.5 rounded ${
                currentRound.winner_side === 'T'
                  ? 'bg-amber-500/20 text-amber-400'
                  : currentRound.winner_side === 'CT'
                    ? 'bg-blue-500/20 text-blue-400'
                    : 'bg-bg-elevated text-text-dim'
              }`}>
                {currentRound.winner_side ? `${currentRound.winner_side} Win` : '-'}
              </div>
              <div className="text-text-dim text-xs mt-1">
                {currentRound.win_reason?.replace('_', ' ') || '-'}
              </div>
              {currentRound.bomb_planted && (
                <div className="text-xs text-amber-400 mt-1">
                  Bomb: {currentRound.plant_site || '?'}
                  {currentRound.bomb_defused && ' (defused)'}
                </div>
              )}
            </div>
            <div className="bg-bg-elevated rounded-lg p-3 text-center">
              <div className="text-blue-400 font-bold text-lg">
                {currentRound.team2_score}
              </div>
              <div className="text-text-dim text-xs">CT-Side</div>
              <div className="text-text-muted text-xs mt-1">
                {currentRound.ct_buy_type || '-'}
              </div>
            </div>
          </div>
        )}

        {/* Player Panels */}
        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="text-xs font-medium text-amber-400 mb-2">T-Side</div>
            {tPlayers.map((p) => (
              <div key={p.steam_id} className="flex justify-between text-xs py-1 border-b border-border last:border-0">
                <span className="text-text">{p.name}</span>
                <span className="text-text-muted">
                  {p.kills}K {p.deaths}D {p.rating?.toFixed(2) || '-'}
                </span>
              </div>
            ))}
          </div>
          <div>
            <div className="text-xs font-medium text-blue-400 mb-2">CT-Side</div>
            {ctPlayers.map((p) => (
              <div key={p.steam_id} className="flex justify-between text-xs py-1 border-b border-border last:border-0">
                <span className="text-text">{p.name}</span>
                <span className="text-text-muted">
                  {p.kills}K {p.deaths}D {p.rating?.toFixed(2) || '-'}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
