'use client'

import { useCallback, useEffect, useState } from 'react'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ReferenceLine,
} from 'recharts'
import { DollarSign, Loader2 } from 'lucide-react'
import { api } from '@/lib/api-client'
import type { MatchEconomy } from '@/types/demo'

interface EconomyChartProps {
  matchId: string
}

export function EconomyChart({ matchId }: EconomyChartProps) {
  const [economy, setEconomy] = useState<MatchEconomy | null>(null)
  const [loading, setLoading] = useState(true)

  const loadEconomy = useCallback(async () => {
    try {
      setLoading(true)
      const data = await api.get<MatchEconomy>(`/matches/${matchId}/economy`)
      setEconomy(data)
    } catch {
      // Silently fail — economy data might not be available
    } finally {
      setLoading(false)
    }
  }, [matchId])

  useEffect(() => {
    loadEconomy()
  }, [loadEconomy])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-5 w-5 text-text-muted animate-spin" />
      </div>
    )
  }

  if (!economy || economy.rounds.length === 0) {
    return null
  }

  const hasEconomyData = economy.rounds.some(
    (r) => r.t_equipment_value !== null || r.ct_equipment_value !== null
  )

  if (!hasEconomyData) {
    return null
  }

  const chartData = economy.rounds.map((round) => ({
    round: round.round_number,
    T: round.t_equipment_value ?? 0,
    CT: round.ct_equipment_value ?? 0,
    winner: round.winner_side,
    t_buy: round.t_buy_type,
    ct_buy: round.ct_buy_type,
    score: `${round.team1_score}:${round.team2_score}`,
  }))

  return (
    <div>
      <h2 className="text-lg font-bold mb-3 flex items-center gap-2">
        <DollarSign className="h-4 w-4 text-primary" />
        Economy
      </h2>
      <div className="bg-bg-card border border-border rounded-xl p-4">
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData} barGap={0} barCategoryGap="20%">
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
            <XAxis
              dataKey="round"
              tick={{ fill: '#888', fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
            />
            <YAxis
              tick={{ fill: '#888', fontSize: 11 }}
              tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}k`}
              tickLine={false}
              axisLine={{ stroke: 'rgba(255,255,255,0.1)' }}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#1a1a2e',
                border: '1px solid rgba(255,255,255,0.1)',
                borderRadius: '8px',
                fontSize: '12px',
              }}
              labelFormatter={(label) => `Round ${label}`}
              formatter={(value, name) => [
                `$${Number(value).toLocaleString()}`,
                String(name),
              ]}
            />
            <Legend wrapperStyle={{ fontSize: '12px' }} />
            <ReferenceLine y={4500} stroke="rgba(255,255,255,0.15)" strokeDasharray="5 5" />
            <Bar dataKey="T" fill="#f59e0b" opacity={0.8} radius={[2, 2, 0, 0]} />
            <Bar dataKey="CT" fill="#3b82f6" opacity={0.8} radius={[2, 2, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>

        {/* Buy type indicators */}
        <div className="flex flex-wrap gap-1 mt-3">
          {economy.rounds.map((round) => {
            const buyType = round.t_buy_type || round.ct_buy_type
            if (!buyType) return null

            const colors: Record<string, string> = {
              pistol: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
              eco: 'bg-red-500/20 text-red-300 border-red-500/30',
              force: 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
              semi: 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30',
              full: 'bg-green-500/20 text-green-300 border-green-500/30',
            }

            return (
              <div
                key={round.round_number}
                className={`text-[10px] px-1.5 py-0.5 rounded border ${colors[round.t_buy_type || ''] || 'bg-bg-elevated border-border text-text-dim'}`}
                title={`R${round.round_number}: T=${round.t_buy_type} CT=${round.ct_buy_type}`}
              >
                {round.round_number}
              </div>
            )
          })}
        </div>
        <div className="flex gap-3 mt-2 text-[10px] text-text-dim">
          <span className="flex items-center gap-1"><div className="w-2 h-2 rounded bg-purple-500/40" /> Pistol</span>
          <span className="flex items-center gap-1"><div className="w-2 h-2 rounded bg-red-500/40" /> Eco</span>
          <span className="flex items-center gap-1"><div className="w-2 h-2 rounded bg-yellow-500/40" /> Force</span>
          <span className="flex items-center gap-1"><div className="w-2 h-2 rounded bg-green-500/40" /> Full</span>
        </div>
      </div>
    </div>
  )
}
