'use client'

import { useEffect, useState } from 'react'
import { useTranslations } from 'next-intl'
import { Sparkles, Loader2 } from 'lucide-react'
import { api } from '@/lib/api-client'

interface ArchetypeFeature {
  feature: string
  z_score: number
}

interface PlayerArchetype {
  cluster_id: number
  archetype: string
  size: number
  top_features: ArchetypeFeature[]
  x: number
  y: number
}

interface ArchetypeCardProps {
  steamId: string
}

export function ArchetypeCard({ steamId }: ArchetypeCardProps) {
  const t = useTranslations('archetypes')
  const [data, setData] = useState<PlayerArchetype | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    api
      .get<PlayerArchetype>(`/players/${steamId}/archetype`)
      .then((res) => {
        if (!cancelled) setData(res)
      })
      .catch(() => {
        if (!cancelled) setData(null)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [steamId])

  if (loading) {
    return (
      <div className="bg-bg-card border border-border rounded-xl p-6">
        <Loader2 className="h-5 w-5 text-text-muted animate-spin" />
      </div>
    )
  }

  if (!data) return null

  return (
    <div className="bg-bg-card border border-border rounded-xl p-6">
      <div className="flex items-center gap-2 mb-2">
        <Sparkles className="h-5 w-5 text-primary" />
        <h3 className="text-lg font-bold">{t('title')}</h3>
      </div>
      <p className="text-2xl font-bold text-primary mb-1">{data.archetype}</p>
      <p className="text-xs text-text-dim mb-4">
        {t('subtitle', { count: data.size })}
      </p>

      {data.top_features.length > 0 && (
        <>
          <p className="text-xs font-medium text-text-muted uppercase mb-2">
            {t('definingTraits')}
          </p>
          <div className="space-y-2">
            {data.top_features.slice(0, 5).map((f) => {
              const positive = f.z_score > 0
              const magnitude = Math.min(Math.abs(f.z_score) * 50, 100)
              return (
                <div key={f.feature} className="flex items-center gap-3">
                  <span className="text-xs text-text-muted w-24 truncate">
                    {f.feature}
                  </span>
                  <div className="flex-1 h-2 bg-bg-elevated rounded-full overflow-hidden relative">
                    <div
                      className={`absolute top-0 h-full ${
                        positive ? 'bg-green-500/60 left-1/2' : 'bg-red-500/60 right-1/2'
                      }`}
                      style={{ width: `${magnitude / 2}%` }}
                    />
                    <div className="absolute top-0 left-1/2 h-full w-px bg-border" />
                  </div>
                  <span
                    className={`text-xs font-mono w-12 text-right ${
                      positive ? 'text-green-400' : 'text-red-400'
                    }`}
                  >
                    {f.z_score > 0 ? '+' : ''}
                    {f.z_score.toFixed(2)}
                  </span>
                </div>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}
