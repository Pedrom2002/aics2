'use client'

import { useCallback, useEffect, useState } from 'react'
import {
  Bomb,
  FastForward,
  Flame,
  Loader2,
  Pause,
  Play,
  Rewind,
  SkipBack,
  SkipForward,
  Skull,
  Wind,
  Zap,
} from 'lucide-react'
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

interface KillFeedEntry {
  round: number
  killer: string
  victim: string
  killerSide: string
  weapon: string
}

interface ReplayViewerProps {
  matchId: string
}

const SPEED_OPTIONS = [0.25, 0.5, 1, 2, 4]

export function ReplayViewer({ matchId }: ReplayViewerProps) {
  const [data, setData] = useState<ReplayData | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedRound, setSelectedRound] = useState(1)
  const [isPlaying, setIsPlaying] = useState(false)
  const [speed, setSpeed] = useState(1)
  const [showSmokes, setShowSmokes] = useState(true)
  const [showFlashes, setShowFlashes] = useState(true)
  const [showMolotovs, setShowMolotovs] = useState(true)

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
    const interval = 2000 / speed
    const timer = setInterval(() => {
      setSelectedRound((prev) => {
        if (prev >= data.total_rounds) {
          setIsPlaying(false)
          return prev
        }
        return prev + 1
      })
    }, interval)
    return () => clearInterval(timer)
  }, [isPlaying, data, speed])

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

  // Synthetic kill feed based on round outcomes
  const killFeed: KillFeedEntry[] = []
  if (currentRound) {
    // Show some contextual info based on round outcome
    if (currentRound.win_reason === 'elimination') {
      killFeed.push({
        round: currentRound.round_number,
        killer: currentRound.winner_side === 'T' ? 'T-Side' : 'CT-Side',
        victim: currentRound.winner_side === 'T' ? 'CT-Side' : 'T-Side',
        killerSide: currentRound.winner_side || 'T',
        weapon: 'elimination',
      })
    }
  }

  return (
    <div className="mb-6">
      <h2 className="text-lg font-bold mb-3 flex items-center gap-2">
        <Play className="h-4 w-4 text-primary" />
        2D Replay
      </h2>
      <div className="bg-bg-card border border-border rounded-xl p-4">
        {/* Controls */}
        <div className="flex items-center gap-2 mb-3">
          <button
            onClick={() => setSelectedRound(1)}
            className="p-1.5 rounded bg-bg-elevated hover:bg-bg-elevated/80 transition-colors"
            title="First round"
          >
            <SkipBack className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={() => setSelectedRound(Math.max(1, selectedRound - 1))}
            className="p-1.5 rounded bg-bg-elevated hover:bg-bg-elevated/80 transition-colors"
            title="Previous round"
          >
            <Rewind className="h-3.5 w-3.5" />
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
            title="Next round"
          >
            <FastForward className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={() => setSelectedRound(data.total_rounds)}
            className="p-1.5 rounded bg-bg-elevated hover:bg-bg-elevated/80 transition-colors"
            title="Last round"
          >
            <SkipForward className="h-3.5 w-3.5" />
          </button>

          {/* Speed selector */}
          <div className="flex items-center gap-1 ml-2">
            {SPEED_OPTIONS.map((s) => (
              <button
                key={s}
                onClick={() => setSpeed(s)}
                className={`px-1.5 py-0.5 rounded text-[10px] ${
                  speed === s ? 'bg-primary text-white' : 'bg-bg-elevated text-text-dim'
                }`}
              >
                {s}x
              </button>
            ))}
          </div>

          <span className="text-sm text-text-muted ml-2">
            R{selectedRound}/{data.total_rounds}
          </span>

          {/* Round selector dropdown */}
          <select
            value={selectedRound}
            onChange={(e) => setSelectedRound(Number(e.target.value))}
            className="ml-auto px-2 py-1 bg-bg-elevated border border-border rounded text-xs"
          >
            {data.rounds.map((r) => (
              <option key={r.round_number} value={r.round_number}>
                Round {r.round_number}
              </option>
            ))}
          </select>
        </div>

        {/* Timeline scrub bar */}
        <input
          type="range"
          min={1}
          max={data.total_rounds}
          value={selectedRound}
          onChange={(e) => setSelectedRound(Number(e.target.value))}
          className="w-full mb-3"
        />

        {/* Utility overlay toggles */}
        <div className="flex gap-3 mb-3 text-xs">
          <label className="flex items-center gap-1 text-text-muted cursor-pointer">
            <input
              type="checkbox"
              checked={showSmokes}
              onChange={(e) => setShowSmokes(e.target.checked)}
              className="rounded border-border"
            />
            <Wind className="h-3 w-3 text-blue-300" />
            Smokes
          </label>
          <label className="flex items-center gap-1 text-text-muted cursor-pointer">
            <input
              type="checkbox"
              checked={showFlashes}
              onChange={(e) => setShowFlashes(e.target.checked)}
              className="rounded border-border"
            />
            <Zap className="h-3 w-3 text-yellow-300" />
            Flashes
          </label>
          <label className="flex items-center gap-1 text-text-muted cursor-pointer">
            <input
              type="checkbox"
              checked={showMolotovs}
              onChange={(e) => setShowMolotovs(e.target.checked)}
              className="rounded border-border"
            />
            <Flame className="h-3 w-3 text-orange-400" />
            Molotovs
          </label>
        </div>

        {/* Round Info */}
        {currentRound && (
          <div className="grid grid-cols-3 gap-3 mb-3 text-sm">
            <div className="bg-bg-elevated rounded-lg p-3 text-center">
              <div className="text-amber-400 font-bold text-lg">{currentRound.team1_score}</div>
              <div className="text-text-dim text-xs">T-Side</div>
              <div className="text-text-muted text-[10px] mt-0.5">{currentRound.t_buy_type || '-'}</div>
            </div>
            <div className="flex flex-col items-center justify-center">
              <div
                className={`text-xs font-medium px-2 py-0.5 rounded ${
                  currentRound.winner_side === 'T'
                    ? 'bg-amber-500/20 text-amber-400'
                    : currentRound.winner_side === 'CT'
                      ? 'bg-blue-500/20 text-blue-400'
                      : 'bg-bg-elevated text-text-dim'
                }`}
              >
                {currentRound.winner_side ? `${currentRound.winner_side} Win` : '-'}
              </div>
              <div className="text-text-dim text-[10px] mt-1">
                {currentRound.win_reason?.replace('_', ' ') || '-'}
              </div>
              {currentRound.bomb_planted && (
                <div className="flex items-center gap-1 text-[10px] text-amber-400 mt-1">
                  <Bomb className="h-3 w-3" />
                  {currentRound.plant_site || '?'}
                  {currentRound.bomb_defused && ' (defused)'}
                </div>
              )}
              {currentRound.duration_seconds && (
                <div className="text-[10px] text-text-dim mt-0.5">
                  {currentRound.duration_seconds.toFixed(0)}s
                </div>
              )}
            </div>
            <div className="bg-bg-elevated rounded-lg p-3 text-center">
              <div className="text-blue-400 font-bold text-lg">{currentRound.team2_score}</div>
              <div className="text-text-dim text-xs">CT-Side</div>
              <div className="text-text-muted text-[10px] mt-0.5">{currentRound.ct_buy_type || '-'}</div>
            </div>
          </div>
        )}

        {/* Kill Feed + Player Panels side by side */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {/* T-Side Players */}
          <div>
            <div className="text-xs font-medium text-amber-400 mb-1.5">T-Side</div>
            {tPlayers.map((p) => (
              <div
                key={p.steam_id}
                className="flex justify-between items-center text-xs py-1 px-2 rounded hover:bg-bg-elevated/50 border-b border-border last:border-0"
              >
                <div>
                  <span className="text-text font-medium">{p.name}</span>
                  {p.rating && (
                    <span className="text-primary text-[10px] ml-1">{p.rating.toFixed(2)}</span>
                  )}
                </div>
                <span className="text-text-dim text-[10px]">
                  {p.kills}/{p.deaths} {p.adr?.toFixed(0) ?? '-'}
                </span>
              </div>
            ))}
          </div>

          {/* Kill Feed */}
          <div>
            <div className="text-xs font-medium text-text-muted mb-1.5 flex items-center gap-1">
              <Skull className="h-3 w-3" /> Kill Feed
            </div>
            {killFeed.length > 0 ? (
              killFeed.map((k, i) => (
                <div key={i} className="text-[10px] py-0.5 text-text-dim">
                  <span className={k.killerSide === 'T' ? 'text-amber-400' : 'text-blue-400'}>
                    {k.killer}
                  </span>
                  {' → '}
                  <span className={k.killerSide === 'T' ? 'text-blue-400' : 'text-amber-400'}>
                    {k.victim}
                  </span>
                  <span className="text-text-dim ml-1">({k.weapon})</span>
                </div>
              ))
            ) : (
              <div className="text-[10px] text-text-dim italic">
                {currentRound?.winner_side
                  ? `${currentRound.winner_side} won via ${currentRound.win_reason || 'unknown'}`
                  : 'No kill data for this round'}
              </div>
            )}
          </div>

          {/* CT-Side Players */}
          <div>
            <div className="text-xs font-medium text-blue-400 mb-1.5">CT-Side</div>
            {ctPlayers.map((p) => (
              <div
                key={p.steam_id}
                className="flex justify-between items-center text-xs py-1 px-2 rounded hover:bg-bg-elevated/50 border-b border-border last:border-0"
              >
                <div>
                  <span className="text-text font-medium">{p.name}</span>
                  {p.rating && (
                    <span className="text-primary text-[10px] ml-1">{p.rating.toFixed(2)}</span>
                  )}
                </div>
                <span className="text-text-dim text-[10px]">
                  {p.kills}/{p.deaths} {p.adr?.toFixed(0) ?? '-'}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
