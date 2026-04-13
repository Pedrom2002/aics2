'use client'

import { useParams } from 'next/navigation'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/lib/api-client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'

interface TeamOverview {
  id: string
  name: string
  roster: { steam_id: string; role?: string | null }[]
  map_preference: { map: string; count: number }[]
  archetypes: { archetype: string; count: number }[]
  averages: { rating: number | null; adr: number | null; hs_pct: number | null }
}

export default function TeamPage() {
  const params = useParams()
  const teamId = params?.teamId as string

  const { data, isLoading } = useQuery({
    queryKey: ['team', teamId],
    queryFn: () => api.get<TeamOverview>(`/teams/${teamId}`),
    enabled: Boolean(teamId),
  })

  if (isLoading || !data) {
    return <Skeleton className="h-64 w-full" />
  }

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold">{data.name}</h1>
      </header>

      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Averages</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <div>Rating: {data.averages.rating?.toFixed(2) ?? '—'}</div>
            <div>ADR: {data.averages.adr?.toFixed(1) ?? '—'}</div>
            <div>HS%: {data.averages.hs_pct?.toFixed(1) ?? '—'}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Roster ({data.roster.length})</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            {data.roster.map((r) => (
              <div key={r.steam_id} className="flex justify-between">
                <span>{r.steam_id}</span>
                {r.role && <Badge variant="secondary">{r.role}</Badge>}
              </div>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Composition</CardTitle>
          </CardHeader>
          <CardContent className="space-y-1 text-sm">
            {data.archetypes.map((a) => (
              <div key={a.archetype} className="flex justify-between">
                <span>{a.archetype}</span>
                <span className="text-text-muted">{a.count}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Map Preference</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {data.map_preference.map((m) => (
              <div key={m.map} className="flex items-center gap-3">
                <span className="w-32 text-sm">{m.map}</span>
                <div className="h-2 flex-1 overflow-hidden rounded-full bg-bg-elevated">
                  <div
                    className="h-full bg-primary"
                    style={{
                      width: `${Math.min(100, (m.count / (data.map_preference[0]?.count ?? 1)) * 100)}%`,
                    }}
                  />
                </div>
                <span className="w-10 text-right text-xs font-mono">{m.count}</span>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
