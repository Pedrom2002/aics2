'use client'

import { useMemo } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import { useTranslations } from 'next-intl'
import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, ArrowRight } from 'lucide-react'
import * as matchesApi from '@/lib/api/matches'
import { QUERY_KEYS } from '@/lib/constants'
import type { DetectedError } from '@/types/demo'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'

type GroupedErrors = Record<string, DetectedError[]>

export default function CoachingInsightsPage() {
  const params = useParams()
  const id = params?.id as string
  const t = useTranslations('coaching')

  const { data, isLoading } = useQuery({
    queryKey: [QUERY_KEYS.match, id, 'errors'],
    queryFn: () => matchesApi.errors(id),
    enabled: Boolean(id),
  })

  const grouped = useMemo<GroupedErrors>(() => {
    const errors = data?.errors ?? []
    return errors.reduce<GroupedErrors>((acc, err) => {
      const key = err.player_steam_id ?? 'unknown'
      acc[key] ??= []
      acc[key].push(err)
      return acc
    }, {})
  }, [data])

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-32 w-full" />
        <Skeleton className="h-32 w-full" />
      </div>
    )
  }

  const entries = Object.entries(grouped)

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold">{t('title')}</h1>
        <p className="text-sm text-text-muted">{t('subtitle')}</p>
      </header>

      {entries.length === 0 ? (
        <Card>
          <CardContent className="py-10 text-center text-text-muted">
            {t('noErrors')}
          </CardContent>
        </Card>
      ) : (
        entries.map(([player, errs]) => (
          <Card key={player}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <AlertTriangle className="h-4 w-4 text-amber-500" />
                {player}
                <Badge variant="secondary">{errs.length}</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {errs.map((err, idx) => (
                <div
                  key={`${err.round_number}-${idx}`}
                  className="flex items-center gap-3 border-b border-border py-2 last:border-0"
                >
                  <Badge variant={err.severity === 'critical' ? 'critical' : 'secondary'}>
                    {err.severity}
                  </Badge>
                  <div className="flex-1 text-sm">
                    <span className="font-medium">{err.error_type}</span>
                    <span className="text-text-muted ml-2">
                      {t('round')} {err.round_number} · {t('tick')} {err.tick ?? '—'}
                    </span>
                    {err.description && (
                      <p className="text-xs text-text-muted mt-1">{err.description}</p>
                    )}
                  </div>
                  {err.tick != null && (
                    <Link
                      href={`/dashboard/matches/${id}/replay?tick=${err.tick}&player=${err.player_steam_id}`}
                    >
                      <Button variant="ghost" size="sm">
                        {t('jumpToTick')}
                        <ArrowRight className="h-4 w-4 ml-1" />
                      </Button>
                    </Link>
                  )}
                </div>
              ))}
            </CardContent>
          </Card>
        ))
      )}
    </div>
  )
}
