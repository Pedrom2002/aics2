'use client'

import { useCallback, useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import {
  ArrowLeft,
  Crosshair,
  Loader2,
  Map,
  Shield,
  Target,
  TrendingUp,
  Zap,
} from 'lucide-react'
import { api, ApiError } from '@/lib/api-client'
import type { PlayerAggregatedStats } from '@/types/demo'

function StatCard({
  label,
  value,
  icon: Icon,
  highlight,
}: {
  label: string
  value: string | number
  icon: typeof Crosshair
  highlight?: boolean
}) {
  return (
    <div
      className={`bg-bg-card border rounded-xl p-4 ${highlight ? 'border-primary/40' : 'border-border'}`}
    >
      <div className="flex items-center gap-2 text-text-muted text-xs mb-1">
        <Icon className="h-3.5 w-3.5" />
        {label}
      </div>
      <div className={`text-xl font-bold ${highlight ? 'text-primary' : ''}`}>{value}</div>
    </div>
  )
}

export default function PlayerStatsPage() {
  const params = useParams()
  const router = useRouter()
  const steamId = params.steamId as string

  const [stats, setStats] = useState<PlayerAggregatedStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadStats = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await api.get<PlayerAggregatedStats>(`/players/${steamId}/stats`)
      setStats(data)
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message)
      } else {
        setError('Failed to load player stats')
      }
    } finally {
      setLoading(false)
    }
  }, [steamId])

  useEffect(() => {
    loadStats()
  }, [loadStats])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 text-text-muted animate-spin" />
      </div>
    )
  }

  if (error || !stats) {
    return (
      <div className="text-center py-20">
        <p className="text-error mb-4">{error || 'Player not found'}</p>
        <div className="flex items-center justify-center gap-4">
          <button onClick={loadStats} className="text-primary text-sm hover:underline">
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

  const mapEntries = Object.entries(stats.maps_played).sort((a, b) => b[1] - a[1])

  return (
    <div>
      <button
        onClick={() => router.back()}
        className="inline-flex items-center gap-1 text-text-muted hover:text-text text-sm mb-6 transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Back
      </button>

      {/* Player Header */}
      <div className="bg-bg-card border border-border rounded-xl p-6 mb-6">
        <h1 className="text-2xl font-bold mb-1">{stats.player_name}</h1>
        <p className="text-text-muted text-sm">
          {stats.total_matches} matches · {stats.total_rounds} rounds
        </p>
      </div>

      {/* Key Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard
          label="HLTV Rating"
          value={stats.avg_hltv_rating.toFixed(2)}
          icon={TrendingUp}
          highlight
        />
        <StatCard label="K/D Ratio" value={stats.avg_kd_ratio.toFixed(2)} icon={Crosshair} />
        <StatCard label="ADR" value={stats.avg_adr.toFixed(1)} icon={Target} />
        <StatCard label="HS%" value={`${stats.avg_headshot_pct.toFixed(1)}%`} icon={Zap} />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <StatCard label="KAST%" value={`${stats.avg_kast_pct.toFixed(1)}%`} icon={Shield} />
        <StatCard
          label="Opening Win%"
          value={`${stats.avg_opening_duel_win_rate.toFixed(1)}%`}
          icon={Crosshair}
        />
        <StatCard label="Impact" value={stats.avg_impact_rating.toFixed(2)} icon={Zap} />
        <StatCard
          label="Consistency"
          value={`±${stats.rating_std_deviation.toFixed(2)}`}
          icon={TrendingUp}
        />
      </div>

      {/* Totals */}
      <div className="mb-6">
        <h2 className="text-lg font-bold mb-3 flex items-center gap-2">
          <Target className="h-4 w-4 text-primary" />
          Career Totals
        </h2>
        <div className="bg-bg-card border border-border rounded-xl overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-text-muted text-xs">
                <th className="px-4 py-2.5 text-center font-medium">Kills</th>
                <th className="px-4 py-2.5 text-center font-medium">Deaths</th>
                <th className="px-4 py-2.5 text-center font-medium">Assists</th>
                <th className="px-4 py-2.5 text-center font-medium">HS Kills</th>
                <th className="px-4 py-2.5 text-center font-medium">First Kills</th>
                <th className="px-4 py-2.5 text-center font-medium">Clutches</th>
                <th className="px-4 py-2.5 text-center font-medium">3k+</th>
                <th className="px-4 py-2.5 text-center font-medium">4k+</th>
                <th className="px-4 py-2.5 text-center font-medium">Aces</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="px-4 py-2.5 text-center font-medium">{stats.total_kills}</td>
                <td className="px-4 py-2.5 text-center">{stats.total_deaths}</td>
                <td className="px-4 py-2.5 text-center">{stats.total_assists}</td>
                <td className="px-4 py-2.5 text-center">{stats.total_headshot_kills}</td>
                <td className="px-4 py-2.5 text-center">{stats.total_first_kills}</td>
                <td className="px-4 py-2.5 text-center">{stats.total_clutch_wins}</td>
                <td className="px-4 py-2.5 text-center">{stats.total_multi_kills_3k}</td>
                <td className="px-4 py-2.5 text-center">{stats.total_multi_kills_4k}</td>
                <td className="px-4 py-2.5 text-center">{stats.total_multi_kills_5k}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Maps */}
      {mapEntries.length > 0 && (
        <div>
          <h2 className="text-lg font-bold mb-3 flex items-center gap-2">
            <Map className="h-4 w-4 text-primary" />
            Maps Played
          </h2>
          <div className="bg-bg-card border border-border rounded-xl p-4">
            <div className="flex flex-wrap gap-2">
              {mapEntries.map(([mapName, count]) => (
                <div
                  key={mapName}
                  className={`px-3 py-1.5 rounded-lg border text-sm ${
                    mapName === stats.best_map
                      ? 'border-primary/40 bg-primary/10 text-primary'
                      : 'border-border bg-bg-elevated text-text-muted'
                  }`}
                >
                  {mapName}{' '}
                  <span className="text-xs opacity-70">
                    ({count} {count === 1 ? 'match' : 'matches'})
                  </span>
                </div>
              ))}
            </div>
            {stats.best_map && (
              <p className="text-xs text-text-dim mt-2">Best map: {stats.best_map}</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
