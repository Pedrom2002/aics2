'use client'

import { useCallback, useEffect, useState } from 'react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { Activity, Loader2, TrendingDown, TrendingUp } from 'lucide-react'
import { api } from '@/lib/api-client'

interface WinProbPoint {
  tick: number
  prob_t: number
  alive_t: number
  alive_ct: number
  victim_name: string
  victim_side: string
}

interface WinProbRound {
  round_number: number
  points: WinProbPoint[]
}

interface TopDeath {
  round_number: number
  victim_name: string
  victim_side: string
  attacker_name: string | null
  weapon: string | null
  headshot: boolean
  was_traded: boolean
  win_delta: number
  prob_before: number
  prob_after: number
  alive_t: number
  alive_ct: number
}

interface PlayerImpact {
  steam_id: string
  name: string
  deaths: number
  kills: number
  total_lost: number
  total_gained: number
  net_impact: number
  avg_lost_per_death: number
  avg_gained_per_kill: number
}

interface WinProbData {
  match_id: string
  map: string
  total_kills: number
  rounds: WinProbRound[]
  top_deaths: TopDeath[]
  player_impacts: PlayerImpact[]
}

interface WinProbChartProps {
  matchId: string
}

export function WinProbChart({ matchId }: WinProbChartProps) {
  const [data, setData] = useState<WinProbData | null>(null)
  const [loading, setLoading] = useState(true)
  const [selectedRound, setSelectedRound] = useState<number | null>(null)

  const load = useCallback(async () => {
    try {
      setLoading(true)
      const result = await api.get<WinProbData>(`/matches/${matchId}/winprob`)
      if (result && !('error' in result)) {
        setData(result)
        if (result.rounds.length > 0) {
          setSelectedRound(result.rounds[0].round_number)
        }
      }
    } catch {
      // Silent
    } finally {
      setLoading(false)
    }
  }, [matchId])

  useEffect(() => {
    load()
  }, [load])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-6 w-6 text-text-muted animate-spin" />
      </div>
    )
  }

  if (!data || data.rounds.length === 0) {
    return null
  }

  const currentRound = data.rounds.find((r) => r.round_number === selectedRound)

  // Build chart data with starting point at 50%
  const chartData = currentRound
    ? [
        { tick: 0, prob_t: 0.5, label: 'start' },
        ...currentRound.points.map((p, i) => ({
          tick: i + 1,
          prob_t: p.prob_t,
          label: `${p.victim_name} died (${p.victim_side.toUpperCase()})`,
          alive_t: p.alive_t,
          alive_ct: p.alive_ct,
        })),
      ]
    : []

  return (
    <div className="space-y-6">
      <div className="bg-bg-card border border-border rounded-xl p-6">
        <h2 className="text-lg font-bold mb-1 flex items-center gap-2">
          <Activity className="h-5 w-5 text-primary" />
          Win Probability Curve
        </h2>
        <p className="text-xs text-text-dim mb-4">
          T-side win probability throughout the round, computed by ML model after each kill
        </p>

        {/* Round selector */}
        <div className="flex flex-wrap gap-1.5 mb-4 max-h-24 overflow-y-auto">
          {data.rounds.map((r) => (
            <button
              key={r.round_number}
              onClick={() => setSelectedRound(r.round_number)}
              className={`px-2 py-1 text-xs rounded border transition-colors ${
                selectedRound === r.round_number
                  ? 'bg-primary text-white border-primary'
                  : 'bg-bg-elevated border-border text-text-muted hover:text-text'
              }`}
            >
              R{r.round_number}
            </button>
          ))}
        </div>

        {/* Chart */}
        <ResponsiveContainer width="100%" height={300}>
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id="probT" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.8} />
                <stop offset="95%" stopColor="#f59e0b" stopOpacity={0.1} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3a" />
            <XAxis
              dataKey="tick"
              label={{ value: 'Kill #', position: 'insideBottom', offset: -5, fontSize: 11 }}
              tick={{ fontSize: 10, fill: '#888' }}
            />
            <YAxis
              domain={[0, 1]}
              tickFormatter={(v) => `${Math.round(v * 100)}%`}
              tick={{ fontSize: 10, fill: '#888' }}
              label={{ value: 'T win prob', angle: -90, position: 'insideLeft', fontSize: 11 }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#12121a',
                border: '1px solid #2a2a3a',
                borderRadius: '8px',
                fontSize: '12px',
              }}
              formatter={(value) => [`${(Number(value) * 100).toFixed(1)}%`, 'T win prob']}
              labelFormatter={(label, payload) => {
                if (payload && payload[0]) {
                  return payload[0].payload.label
                }
                return ''
              }}
            />
            <ReferenceLine y={0.5} stroke="#666" strokeDasharray="3 3" />
            <Area
              type="stepAfter"
              dataKey="prob_t"
              stroke="#f59e0b"
              fill="url(#probT)"
              strokeWidth={2}
            />
          </AreaChart>
        </ResponsiveContainer>

        <div className="flex items-center gap-4 text-xs text-text-dim mt-2">
          <span className="flex items-center gap-1">
            <div className="w-3 h-1 bg-amber-500" /> T side
          </span>
          <span>50% line = balanced</span>
        </div>
      </div>

      {/* Top impact deaths */}
      {data.top_deaths.length > 0 && (
        <div className="bg-bg-card border border-border rounded-xl p-6">
          <h2 className="text-lg font-bold mb-1 flex items-center gap-2">
            <TrendingDown className="h-5 w-5 text-red-400" />
            Top Impact Deaths
          </h2>
          <p className="text-xs text-text-dim mb-4">
            Deaths that hurt their team's chances the most
          </p>
          <div className="space-y-2">
            {data.top_deaths.map((d, i) => (
              <div
                key={i}
                className="flex items-center justify-between p-3 bg-bg-elevated rounded-lg"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <div className="text-xs font-mono text-text-dim w-8">#{i + 1}</div>
                  <div className="text-xs font-mono text-text-muted w-12">R{d.round_number}</div>
                  <div className="min-w-0">
                    <div className="text-sm font-medium truncate">
                      {d.victim_name}
                      <span className="text-xs text-text-dim ml-2">
                        ({d.victim_side.toUpperCase()})
                      </span>
                    </div>
                    <div className="text-xs text-text-dim truncate">
                      Killed by {d.attacker_name || '?'} ({d.weapon || '?'})
                      {d.headshot && ' · HS'}
                      {d.was_traded && ' · traded'}
                    </div>
                  </div>
                </div>
                <div className="text-right shrink-0">
                  <div className="text-sm font-bold text-red-400 font-mono">
                    -{(d.win_delta * 100).toFixed(1)}%
                  </div>
                  <div className="text-xs text-text-dim">
                    {(d.prob_before * 100).toFixed(0)}% → {(d.prob_after * 100).toFixed(0)}%
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Player impacts */}
      {data.player_impacts.length > 0 && (
        <div className="bg-bg-card border border-border rounded-xl p-6">
          <h2 className="text-lg font-bold mb-1 flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-green-400" />
            Player Impact Rankings
          </h2>
          <p className="text-xs text-text-dim mb-4">
            Net win probability impact (kills gained - deaths lost)
          </p>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-text-muted text-xs">
                  <th className="px-3 py-2 text-left font-medium">Player</th>
                  <th className="px-3 py-2 text-center font-medium">K</th>
                  <th className="px-3 py-2 text-center font-medium">D</th>
                  <th className="px-3 py-2 text-center font-medium">+Win%</th>
                  <th className="px-3 py-2 text-center font-medium">-Win%</th>
                  <th className="px-3 py-2 text-center font-medium">Net</th>
                </tr>
              </thead>
              <tbody>
                {data.player_impacts.map((p) => (
                  <tr
                    key={p.steam_id}
                    className="border-b border-border last:border-0 hover:bg-bg-elevated/50"
                  >
                    <td className="px-3 py-2 font-medium">{p.name}</td>
                    <td className="px-3 py-2 text-center font-mono">{p.kills}</td>
                    <td className="px-3 py-2 text-center font-mono">{p.deaths}</td>
                    <td className="px-3 py-2 text-center font-mono text-green-400">
                      +{(p.total_gained * 100).toFixed(0)}
                    </td>
                    <td className="px-3 py-2 text-center font-mono text-red-400">
                      -{(p.total_lost * 100).toFixed(0)}
                    </td>
                    <td
                      className={`px-3 py-2 text-center font-mono font-bold ${
                        p.net_impact > 0 ? 'text-green-400' : 'text-red-400'
                      }`}
                    >
                      {p.net_impact > 0 ? '+' : ''}
                      {(p.net_impact * 100).toFixed(0)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
