'use client'

import { useCallback, useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import {
  ArrowLeft,
  Bomb,
  Clock,
  Crosshair,
  Loader2,
  Map,
  Shield,
  Skull,
  Target,
  Users,
  Zap,
} from 'lucide-react'
import Link from 'next/link'
import { api, ApiError } from '@/lib/api-client'
import { EconomyChart } from '@/components/matches/economy-chart'
import { Heatmap } from '@/components/matches/heatmap'
import { ReplayViewer } from '@/components/matches/replay-viewer'
import type { MatchDetail, PlayerStats } from '@/types/demo'

function formatDuration(seconds: number | null): string {
  if (!seconds) return '-'
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

function StatCard({ label, value, icon: Icon }: { label: string; value: string | number; icon: typeof Crosshair }) {
  return (
    <div className="bg-bg-card border border-border rounded-xl p-4">
      <div className="flex items-center gap-2 text-text-muted text-xs mb-1">
        <Icon className="h-3.5 w-3.5" />
        {label}
      </div>
      <div className="text-xl font-bold">{value}</div>
    </div>
  )
}

function PlayerRow({ player }: { player: PlayerStats }) {
  const kd = player.deaths > 0 ? (player.kills / player.deaths).toFixed(2) : player.kills.toFixed(2)
  const hsPercent = player.kills > 0 ? Math.round((player.headshot_kills / player.kills) * 100) : 0

  return (
    <tr className="border-b border-border last:border-0 hover:bg-bg-elevated/50 transition-colors">
      <td className="px-4 py-2.5 font-medium">
        <Link
          href={`/dashboard/players/${player.player_steam_id}`}
          className="hover:text-primary transition-colors"
        >
          {player.player_name}
        </Link>
      </td>
      <td className="px-4 py-2.5 text-center">{player.kills}</td>
      <td className="px-4 py-2.5 text-center">{player.assists}</td>
      <td className="px-4 py-2.5 text-center">{player.deaths}</td>
      <td className="px-4 py-2.5 text-center font-medium">{kd}</td>
      <td className="px-4 py-2.5 text-center">{player.adr?.toFixed(1) ?? '-'}</td>
      <td className="px-4 py-2.5 text-center">{hsPercent}%</td>
      <td className="px-4 py-2.5 text-center">{player.flash_assists}</td>
      <td className="px-4 py-2.5 text-center">{player.first_kills}</td>
      <td className="px-4 py-2.5 text-center font-bold text-primary">
        {player.overall_rating?.toFixed(2) ?? '-'}
      </td>
    </tr>
  )
}

export default function MatchDetailPage() {
  const params = useParams()
  const router = useRouter()
  const matchId = params.id as string

  const [match, setMatch] = useState<MatchDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadMatch = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await api.get<MatchDetail>(`/demos/matches/${matchId}`)
      setMatch(data)
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message)
      } else {
        setError('Failed to load match')
      }
    } finally {
      setLoading(false)
    }
  }, [matchId])

  useEffect(() => {
    loadMatch()
  }, [loadMatch])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 text-text-muted animate-spin" />
      </div>
    )
  }

  if (error || !match) {
    return (
      <div className="text-center py-20">
        <p className="text-error mb-4">{error || 'Match not found'}</p>
        <div className="flex items-center justify-center gap-4">
          <button
            onClick={loadMatch}
            className="text-primary text-sm hover:underline"
          >
            Retry
          </button>
          <button
            onClick={() => router.back()}
            className="text-text-muted text-sm hover:underline"
          >
            Go back
          </button>
        </div>
      </div>
    )
  }

  const team1Players = match.player_stats.filter((p) => p.team_side === 'T' || p.team_side === null)
  const team2Players = match.player_stats.filter((p) => p.team_side === 'CT')

  // If we can't determine sides, split evenly
  const hasTeamSides = match.player_stats.some((p) => p.team_side)
  const displayPlayers = hasTeamSides
    ? [
        { name: match.team1_name || 'Team 1', players: team1Players },
        { name: match.team2_name || 'Team 2', players: team2Players },
      ]
    : [{ name: 'All Players', players: match.player_stats }]

  return (
    <div>
      <button
        onClick={() => router.back()}
        className="inline-flex items-center gap-1 text-text-muted hover:text-text text-sm mb-6 transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Back
      </button>

      {/* Match Header */}
      <div className="bg-bg-card border border-border rounded-xl p-6 mb-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-6">
            <div className="text-center">
              <div className="text-text-muted text-xs mb-1">{match.team1_name || 'Team 1'}</div>
              <div className="text-4xl font-bold">{match.team1_score}</div>
            </div>
            <div className="text-text-dim text-lg font-medium">vs</div>
            <div className="text-center">
              <div className="text-text-muted text-xs mb-1">{match.team2_name || 'Team 2'}</div>
              <div className="text-4xl font-bold">{match.team2_score}</div>
            </div>
          </div>
          <div className="text-right space-y-1">
            <div className="flex items-center gap-1.5 text-text-muted text-sm">
              <Map className="h-3.5 w-3.5" />
              {match.map}
            </div>
            <div className="flex items-center gap-1.5 text-text-muted text-sm">
              <Clock className="h-3.5 w-3.5" />
              {formatDuration(match.duration_seconds)}
            </div>
            <div className="text-text-dim text-xs">
              {match.total_rounds} rounds · {match.tickrate} tick
            </div>
          </div>
        </div>
      </div>

      {/* Stats Overview */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard label="Total Rounds" value={match.total_rounds} icon={Target} />
        <StatCard label="Overtime" value={match.overtime_rounds} icon={Zap} />
        <StatCard label="Duration" value={formatDuration(match.duration_seconds)} icon={Clock} />
        <StatCard label="Tickrate" value={match.tickrate} icon={Crosshair} />
      </div>

      {/* Player Stats */}
      {displayPlayers.map((team) => (
        <div key={team.name} className="mb-6">
          <h2 className="text-lg font-bold mb-3 flex items-center gap-2">
            <Users className="h-4 w-4 text-primary" />
            {team.name}
          </h2>
          <div className="bg-bg-card border border-border rounded-xl overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-text-muted text-xs">
                  <th className="px-4 py-2.5 text-left font-medium">Player</th>
                  <th className="px-4 py-2.5 text-center font-medium">K</th>
                  <th className="px-4 py-2.5 text-center font-medium">A</th>
                  <th className="px-4 py-2.5 text-center font-medium">D</th>
                  <th className="px-4 py-2.5 text-center font-medium">K/D</th>
                  <th className="px-4 py-2.5 text-center font-medium">ADR</th>
                  <th className="px-4 py-2.5 text-center font-medium">HS%</th>
                  <th className="px-4 py-2.5 text-center font-medium">FA</th>
                  <th className="px-4 py-2.5 text-center font-medium">FK</th>
                  <th className="px-4 py-2.5 text-center font-medium">Rating</th>
                </tr>
              </thead>
              <tbody>
                {team.players.map((player) => (
                  <PlayerRow key={player.id} player={player} />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ))}

      {/* Economy Chart */}
      <EconomyChart matchId={matchId} />

      {/* Heatmap */}
      <Heatmap matchId={matchId} />

      {/* 2D Replay */}
      <ReplayViewer matchId={matchId} />

      {/* Round Timeline */}
      {match.rounds.length > 0 && (
        <div>
          <h2 className="text-lg font-bold mb-3 flex items-center gap-2">
            <Shield className="h-4 w-4 text-primary" />
            Round Timeline
          </h2>
          <div className="bg-bg-card border border-border rounded-xl p-4">
            <div className="flex flex-wrap gap-1.5">
              {match.rounds.map((round) => {
                const isTWin = round.winner_side === 'T'
                const isCTWin = round.winner_side === 'CT'
                const isBombRelated =
                  round.win_reason === 'bomb_exploded' || round.win_reason === 'defuse'

                return (
                  <div
                    key={round.id}
                    className={`w-8 h-8 rounded flex items-center justify-center text-xs font-medium border ${
                      isTWin
                        ? 'bg-amber-500/10 border-amber-500/30 text-amber-400'
                        : isCTWin
                          ? 'bg-blue-500/10 border-blue-500/30 text-blue-400'
                          : 'bg-bg-elevated border-border text-text-dim'
                    }`}
                    title={`Round ${round.round_number}: ${round.winner_side || '?'} win (${round.win_reason || '?'}) — ${round.team1_score}:${round.team2_score}`}
                  >
                    {isBombRelated ? (
                      <Bomb className="h-3 w-3" />
                    ) : round.win_reason === 'elimination' ? (
                      <Skull className="h-3 w-3" />
                    ) : (
                      round.round_number
                    )}
                  </div>
                )
              })}
            </div>
            <div className="flex gap-4 mt-3 text-xs text-text-dim">
              <span className="flex items-center gap-1">
                <div className="w-3 h-3 rounded bg-amber-500/20 border border-amber-500/30" /> T
              </span>
              <span className="flex items-center gap-1">
                <div className="w-3 h-3 rounded bg-blue-500/20 border border-blue-500/30" /> CT
              </span>
              <span className="flex items-center gap-1">
                <Bomb className="h-3 w-3" /> Bomb
              </span>
              <span className="flex items-center gap-1">
                <Skull className="h-3 w-3" /> Elimination
              </span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
