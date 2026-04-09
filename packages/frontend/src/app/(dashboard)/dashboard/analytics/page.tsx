'use client'

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { BarChart3, Crosshair, Target, TrendingUp } from 'lucide-react'
import { api } from '@/lib/api-client'
import { PageSkeleton } from '@/components/common/skeleton'

interface PlayerListItem {
  player_steam_id: string
  player_name: string
  total_matches: number
  total_kills: number
  total_deaths: number
  kd_ratio: number
  avg_adr: number
  avg_rating: number | null
}

export default function AnalyticsPage() {
  const [topPlayers, setTopPlayers] = useState<PlayerListItem[]>([])
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState({ demos: 0, matches: 0, players: 0 })

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const [playersData, demosData] = await Promise.all([
        api.get<{ items: PlayerListItem[]; total: number }>('/players?page=1&page_size=10'),
        api.get<{ items: unknown[]; total: number }>('/demos?page=1&page_size=1'),
      ])
      setTopPlayers(playersData.items)
      setStats({
        demos: demosData.total,
        matches: demosData.total,
        players: playersData.total,
      })
    } catch {
      // silently handle
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  if (loading) {
    return <PageSkeleton />
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6 flex items-center gap-2">
        <BarChart3 className="h-6 w-6 text-primary" />
        Analytics
      </h1>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-bg-card border border-border rounded-xl p-5">
          <div className="flex items-center gap-2 text-text-muted text-xs mb-1">
            <Target className="h-3.5 w-3.5" />
            Total Demos
          </div>
          <div className="text-3xl font-bold">{stats.demos}</div>
        </div>
        <div className="bg-bg-card border border-border rounded-xl p-5">
          <div className="flex items-center gap-2 text-text-muted text-xs mb-1">
            <BarChart3 className="h-3.5 w-3.5" />
            Matches Analyzed
          </div>
          <div className="text-3xl font-bold">{stats.matches}</div>
        </div>
        <div className="bg-bg-card border border-border rounded-xl p-5">
          <div className="flex items-center gap-2 text-text-muted text-xs mb-1">
            <Crosshair className="h-3.5 w-3.5" />
            Unique Players
          </div>
          <div className="text-3xl font-bold">{stats.players}</div>
        </div>
      </div>

      <div className="bg-bg-card border border-border rounded-xl p-6">
        <h2 className="text-lg font-bold mb-4 flex items-center gap-2">
          <TrendingUp className="h-4 w-4 text-primary" />
          Top Players by Rating
        </h2>
        {topPlayers.length === 0 ? (
          <p className="text-text-dim text-sm">
            No player data yet. Upload and process demos to see analytics.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-text-muted text-xs">
                  <th className="px-4 py-2 text-left font-medium">#</th>
                  <th className="px-4 py-2 text-left font-medium">Player</th>
                  <th className="px-4 py-2 text-center font-medium">Matches</th>
                  <th className="px-4 py-2 text-center font-medium">K/D</th>
                  <th className="px-4 py-2 text-center font-medium">ADR</th>
                  <th className="px-4 py-2 text-center font-medium">Rating</th>
                </tr>
              </thead>
              <tbody>
                {topPlayers.map((player, i) => (
                  <tr
                    key={player.player_steam_id}
                    className="border-b border-border last:border-0 hover:bg-bg-elevated/50"
                  >
                    <td className="px-4 py-2 text-text-dim">{i + 1}</td>
                    <td className="px-4 py-2 font-medium">
                      <Link
                        href={`/dashboard/players/${player.player_steam_id}`}
                        className="hover:text-primary transition-colors"
                      >
                        {player.player_name}
                      </Link>
                    </td>
                    <td className="px-4 py-2 text-center">{player.total_matches}</td>
                    <td className="px-4 py-2 text-center">{player.kd_ratio}</td>
                    <td className="px-4 py-2 text-center">{player.avg_adr}</td>
                    <td className="px-4 py-2 text-center font-bold text-primary">
                      {player.avg_rating?.toFixed(2) ?? '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
