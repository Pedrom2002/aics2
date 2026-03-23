'use client'

import { useCallback, useEffect, useState } from 'react'
import { Loader2, Search, Trophy } from 'lucide-react'
import { api } from '@/lib/api-client'

interface ProMatch {
  id: string
  source: string
  team1_name: string
  team2_name: string
  team1_score: number | null
  team2_score: number | null
  map: string
  event_name: string | null
  event_tier: string | null
  match_date: string | null
  status: string
  ml_analyzed: boolean
}

interface ProMatchesResponse {
  items: ProMatch[]
  total: number
  page: number
  page_size: number
  pages: number
}

export default function ProMatchesPage() {
  const [data, setData] = useState<ProMatchesResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [page, setPage] = useState(1)
  const [teamFilter, setTeamFilter] = useState('')
  const [mapFilter, setMapFilter] = useState('')
  const [eventFilter, setEventFilter] = useState('')

  const loadMatches = useCallback(async () => {
    try {
      setLoading(true)
      let url = `/pro/matches?page=${page}&page_size=20`
      if (teamFilter) url += `&team=${encodeURIComponent(teamFilter)}`
      if (mapFilter) url += `&map=${encodeURIComponent(mapFilter)}`
      if (eventFilter) url += `&event=${encodeURIComponent(eventFilter)}`
      const result = await api.get<ProMatchesResponse>(url)
      setData(result)
    } catch {
      // Pro matches may not be available yet
      setData({ items: [], total: 0, page: 1, page_size: 20, pages: 0 })
    } finally {
      setLoading(false)
    }
  }, [page, teamFilter, mapFilter, eventFilter])

  useEffect(() => {
    loadMatches()
  }, [loadMatches])

  const tierBadge = (tier: string | null) => {
    if (!tier) return null
    const colors: Record<string, string> = {
      tier1: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
      tier2: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
      tier3: 'bg-green-500/20 text-green-400 border-green-500/30',
      regional: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
    }
    return (
      <span className={`text-xs px-1.5 py-0.5 rounded border ${colors[tier] || 'bg-bg-elevated text-text-dim border-border'}`}>
        {tier.replace('tier', 'T')}
      </span>
    )
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6 flex items-center gap-2">
        <Trophy className="h-6 w-6 text-primary" />
        Pro Matches
      </h1>

      {/* Filters */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-6">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-text-dim" />
          <input
            type="text"
            placeholder="Search team..."
            value={teamFilter}
            onChange={(e) => { setTeamFilter(e.target.value); setPage(1) }}
            className="w-full pl-9 pr-3 py-2 bg-bg-card border border-border rounded-lg text-sm focus:outline-none focus:border-primary"
          />
        </div>
        <select
          value={mapFilter}
          onChange={(e) => { setMapFilter(e.target.value); setPage(1) }}
          className="px-3 py-2 bg-bg-card border border-border rounded-lg text-sm focus:outline-none focus:border-primary"
        >
          <option value="">All Maps</option>
          {['de_mirage', 'de_dust2', 'de_inferno', 'de_nuke', 'de_overpass', 'de_ancient', 'de_anubis', 'de_vertigo'].map(m => (
            <option key={m} value={m}>{m.replace('de_', '')}</option>
          ))}
        </select>
        <input
          type="text"
          placeholder="Search event..."
          value={eventFilter}
          onChange={(e) => { setEventFilter(e.target.value); setPage(1) }}
          className="px-3 py-2 bg-bg-card border border-border rounded-lg text-sm focus:outline-none focus:border-primary"
        />
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-6 w-6 text-text-muted animate-spin" />
        </div>
      ) : data && data.items.length > 0 ? (
        <>
          <div className="bg-bg-card border border-border rounded-xl overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-text-muted text-xs">
                  <th className="px-4 py-2.5 text-left font-medium">Date</th>
                  <th className="px-4 py-2.5 text-left font-medium">Team 1</th>
                  <th className="px-4 py-2.5 text-center font-medium">Score</th>
                  <th className="px-4 py-2.5 text-left font-medium">Team 2</th>
                  <th className="px-4 py-2.5 text-left font-medium">Map</th>
                  <th className="px-4 py-2.5 text-left font-medium">Event</th>
                  <th className="px-4 py-2.5 text-center font-medium">Source</th>
                  <th className="px-4 py-2.5 text-center font-medium">AI</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((match) => (
                  <tr key={match.id} className="border-b border-border last:border-0 hover:bg-bg-elevated/50 transition-colors">
                    <td className="px-4 py-2.5 text-text-muted text-xs">
                      {match.match_date ? new Date(match.match_date).toLocaleDateString() : '-'}
                    </td>
                    <td className="px-4 py-2.5 font-medium">{match.team1_name}</td>
                    <td className="px-4 py-2.5 text-center font-bold">
                      {match.team1_score ?? '-'} : {match.team2_score ?? '-'}
                    </td>
                    <td className="px-4 py-2.5 font-medium">{match.team2_name}</td>
                    <td className="px-4 py-2.5 text-text-muted">
                      {match.map.replace('de_', '')}
                    </td>
                    <td className="px-4 py-2.5 text-text-muted text-xs">
                      {match.event_name || '-'}
                      {match.event_tier && <span className="ml-1">{tierBadge(match.event_tier)}</span>}
                    </td>
                    <td className="px-4 py-2.5 text-center">
                      <span className="text-xs px-1.5 py-0.5 rounded bg-bg-elevated text-text-dim">
                        {match.source}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-center">
                      {match.ml_analyzed ? (
                        <span className="text-xs text-primary">Analyzed</span>
                      ) : (
                        <span className="text-xs text-text-dim">Pending</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {data.pages > 1 && (
            <div className="flex items-center justify-center gap-2 mt-4">
              <button
                onClick={() => setPage(Math.max(1, page - 1))}
                disabled={page === 1}
                className="px-3 py-1 text-sm rounded bg-bg-elevated text-text-muted disabled:opacity-50"
              >
                Previous
              </button>
              <span className="text-sm text-text-muted">
                Page {page} of {data.pages}
              </span>
              <button
                onClick={() => setPage(Math.min(data.pages, page + 1))}
                disabled={page === data.pages}
                className="px-3 py-1 text-sm rounded bg-bg-elevated text-text-muted disabled:opacity-50"
              >
                Next
              </button>
            </div>
          )}
        </>
      ) : (
        <div className="text-center py-20">
          <Trophy className="h-12 w-12 text-text-dim mx-auto mb-3" />
          <p className="text-text-muted">No pro matches found</p>
          <p className="text-text-dim text-sm mt-1">
            Pro match ingestion runs automatically. Check back soon.
          </p>
        </div>
      )}
    </div>
  )
}
