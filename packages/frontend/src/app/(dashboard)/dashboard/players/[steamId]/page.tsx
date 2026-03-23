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
import type { PlayerAggregatedStats, PlayerErrorSummary } from '@/types/demo'

function RadarChart({ data }: { data: { label: string; value: number }[] }) {
  const size = 250
  const cx = size / 2
  const cy = size / 2
  const radius = 100
  const levels = 5

  const angleStep = (2 * Math.PI) / data.length
  const startAngle = -Math.PI / 2

  const getPoint = (angle: number, r: number) => ({
    x: cx + r * Math.cos(angle),
    y: cy + r * Math.sin(angle),
  })

  // Grid rings
  const rings = Array.from({ length: levels }, (_, i) => {
    const r = (radius / levels) * (i + 1)
    const points = data.map((_, j) => getPoint(startAngle + j * angleStep, r))
    return points.map((p) => `${p.x},${p.y}`).join(' ')
  })

  // Data polygon
  const dataPoints = data.map((d, i) => {
    const r = (d.value / 100) * radius
    return getPoint(startAngle + i * angleStep, r)
  })
  const dataPolygon = dataPoints.map((p) => `${p.x},${p.y}`).join(' ')

  // Axis lines + labels
  const axes = data.map((d, i) => {
    const angle = startAngle + i * angleStep
    const end = getPoint(angle, radius + 15)
    const labelPos = getPoint(angle, radius + 28)
    return { end, labelPos, label: d.label, value: Math.round(d.value) }
  })

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="mx-auto">
      {/* Grid */}
      {rings.map((points, i) => (
        <polygon key={i} points={points} fill="none" stroke="#1a1a2e" strokeWidth="1" />
      ))}
      {/* Axes */}
      {axes.map((a, i) => (
        <g key={i}>
          <line x1={cx} y1={cy} x2={a.end.x} y2={a.end.y} stroke="#1a1a2e" strokeWidth="1" />
          <text
            x={a.labelPos.x}
            y={a.labelPos.y}
            textAnchor="middle"
            dominantBaseline="middle"
            className="fill-text-muted"
            fontSize="10"
          >
            {a.label}
          </text>
        </g>
      ))}
      {/* Data fill */}
      <polygon points={dataPolygon} fill="rgba(99, 102, 241, 0.2)" stroke="rgb(99, 102, 241)" strokeWidth="2" />
      {/* Data points */}
      {dataPoints.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r="3" fill="rgb(99, 102, 241)" />
      ))}
    </svg>
  )
}

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
  const [errorSummary, setErrorSummary] = useState<PlayerErrorSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const loadStats = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await api.get<PlayerAggregatedStats>(`/players/${steamId}/stats`)
      setStats(data)
      // Load error summary (non-blocking)
      try {
        const errors = await api.get<PlayerErrorSummary>(`/players/${steamId}/errors`)
        setErrorSummary(errors)
      } catch {
        // Errors may not be available
      }
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

      {/* Radar Chart — Skill Profile */}
      <div className="mb-6">
        <h2 className="text-lg font-bold mb-3 flex items-center gap-2">
          <Target className="h-4 w-4 text-primary" />
          Skill Profile
        </h2>
        <div className="bg-bg-card border border-border rounded-xl p-4">
          <RadarChart
            data={[
              { label: 'Aim', value: Math.min(stats.avg_headshot_pct * 1.5, 100) },
              { label: 'Impact', value: Math.min(stats.avg_impact_rating * 50, 100) },
              { label: 'Game Sense', value: Math.min(stats.avg_kast_pct, 100) },
              { label: 'Utility', value: Math.min((stats.total_flash_assists / Math.max(stats.total_rounds, 1)) * 500, 100) },
              { label: 'Positioning', value: Math.min(stats.avg_survival_rate, 100) },
              { label: 'Consistency', value: Math.max(0, 100 - stats.rating_std_deviation * 200) },
            ]}
          />
        </div>
      </div>

      {/* Error Summary */}
      {errorSummary && (
        <div className="mb-6">
          <h2 className="text-lg font-bold mb-3 flex items-center gap-2">
            <Shield className="h-4 w-4 text-primary" />
            Error Analysis
          </h2>
          <div className="bg-bg-card border border-border rounded-xl p-4">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
              <div className="bg-bg-elevated rounded-lg p-3 text-center">
                <div className="text-xl font-bold">{errorSummary.total_errors}</div>
                <div className="text-text-dim text-xs">Total Errors</div>
              </div>
              <div className="bg-bg-elevated rounded-lg p-3 text-center">
                <div className="text-xl font-bold text-red-400">{errorSummary.critical_count}</div>
                <div className="text-text-dim text-xs">Critical</div>
              </div>
              <div className="bg-bg-elevated rounded-lg p-3 text-center">
                <div className="text-xl font-bold">{errorSummary.positioning_errors}</div>
                <div className="text-text-dim text-xs">Positioning</div>
              </div>
              <div className="bg-bg-elevated rounded-lg p-3 text-center">
                <div className="text-xl font-bold">{errorSummary.utility_errors}</div>
                <div className="text-text-dim text-xs">Utility</div>
              </div>
            </div>

            {errorSummary.top_recommendations.length > 0 && (
              <div>
                <h3 className="text-sm font-medium text-text-muted mb-2">Top Recommendations</h3>
                <div className="space-y-2">
                  {errorSummary.top_recommendations.map((rec, i) => (
                    <div key={i} className="bg-primary/5 border border-primary/20 rounded-lg p-3">
                      <div className="text-xs text-primary font-medium">{rec.title}</div>
                      <p className="text-xs text-text-muted mt-1">{rec.description}</p>
                      {rec.expected_impact && (
                        <p className="text-[10px] text-text-dim mt-1">{rec.expected_impact}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

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
