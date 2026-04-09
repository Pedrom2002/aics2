'use client'

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { Crosshair, Search, Users } from 'lucide-react'
import { api } from '@/lib/api-client'
import { TableSkeleton } from '@/components/common/skeleton'

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

interface PaginatedPlayers {
  items: PlayerListItem[]
  total: number
  page: number
  page_size: number
  pages: number
}

export default function PlayersListPage() {
  const [data, setData] = useState<PaginatedPlayers | null>(null)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)

  const loadPlayers = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({ page: String(page), page_size: '20' })
      if (search) params.set('search', search)
      const result = await api.get<PaginatedPlayers>(`/players?${params}`)
      setData(result)
    } catch {
      // silently handle
    } finally {
      setLoading(false)
    }
  }, [page, search])

  useEffect(() => {
    const timer = setTimeout(loadPlayers, search ? 300 : 0)
    return () => clearTimeout(timer)
  }, [loadPlayers, search])

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6 flex items-center gap-2">
        <Users className="h-6 w-6 text-primary" />
        Players
      </h1>

      <div className="relative mb-4 max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-dim" />
        <input
          type="text"
          value={search}
          onChange={(e) => {
            setSearch(e.target.value)
            setPage(1)
          }}
          placeholder="Search players..."
          aria-label="Search players"
          className="w-full pl-9 pr-3 py-2 bg-bg-card border border-border rounded-lg text-sm focus:outline-none focus:border-primary"
        />
      </div>

      {loading ? (
        <TableSkeleton rows={8} />
      ) : !data || data.items.length === 0 ? (
        <div className="text-center py-20 text-text-dim">
          {search ? 'No players found matching your search' : 'No players found. Upload and process some demos first.'}
        </div>
      ) : (
        <>
          <div className="bg-bg-card border border-border rounded-xl overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-text-muted text-xs">
                  <th className="px-4 py-2.5 text-left font-medium">Player</th>
                  <th className="px-4 py-2.5 text-center font-medium">Matches</th>
                  <th className="px-4 py-2.5 text-center font-medium">K</th>
                  <th className="px-4 py-2.5 text-center font-medium">D</th>
                  <th className="px-4 py-2.5 text-center font-medium">K/D</th>
                  <th className="px-4 py-2.5 text-center font-medium">ADR</th>
                  <th className="px-4 py-2.5 text-center font-medium">Rating</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((player) => (
                  <tr
                    key={player.player_steam_id}
                    className="border-b border-border last:border-0 hover:bg-bg-elevated/50 transition-colors"
                  >
                    <td className="px-4 py-2.5">
                      <Link
                        href={`/dashboard/players/${player.player_steam_id}`}
                        className="font-medium hover:text-primary transition-colors flex items-center gap-2"
                      >
                        <Crosshair className="h-3.5 w-3.5 text-text-dim" />
                        {player.player_name}
                      </Link>
                    </td>
                    <td className="px-4 py-2.5 text-center">{player.total_matches}</td>
                    <td className="px-4 py-2.5 text-center">{player.total_kills}</td>
                    <td className="px-4 py-2.5 text-center">{player.total_deaths}</td>
                    <td className="px-4 py-2.5 text-center font-medium">{player.kd_ratio}</td>
                    <td className="px-4 py-2.5 text-center">{player.avg_adr}</td>
                    <td className="px-4 py-2.5 text-center font-bold text-primary">
                      {player.avg_rating?.toFixed(2) ?? '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {data.pages > 1 && (
            <div className="flex items-center justify-between mt-4">
              <span className="text-xs text-text-dim">
                {data.total} players total
              </span>
              <div className="flex gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="px-3 py-1 text-xs bg-bg-card border border-border rounded-lg disabled:opacity-50"
                >
                  Previous
                </button>
                <span className="px-3 py-1 text-xs text-text-muted">
                  {page} / {data.pages}
                </span>
                <button
                  onClick={() => setPage((p) => Math.min(data.pages, p + 1))}
                  disabled={page >= data.pages}
                  className="px-3 py-1 text-xs bg-bg-card border border-border rounded-lg disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}
