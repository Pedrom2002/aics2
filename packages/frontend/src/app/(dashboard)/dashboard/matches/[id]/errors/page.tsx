'use client'

import { useCallback, useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { AlertTriangle, ArrowLeft, ChevronRight, Filter, Loader2, Shield } from 'lucide-react'
import { api, ApiError } from '@/lib/api-client'
import type { DetectedError, MatchErrorsResponse } from '@/types/demo'

function SeverityBadge({ severity }: { severity: string }) {
  const colors: Record<string, string> = {
    critical: 'bg-red-500/20 text-red-400 border-red-500/30',
    minor: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    info: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  }
  return (
    <span className={`text-xs px-2 py-0.5 rounded border ${colors[severity] || 'bg-bg-elevated text-text-dim border-border'}`}>
      {severity}
    </span>
  )
}

function ShapWaterfall({ importances }: { importances: { feature: string; value: number | string; impact: number }[] }) {
  const maxImpact = Math.max(...importances.map((f) => Math.abs(f.impact)), 0.01)

  return (
    <div className="space-y-1.5">
      <div className="text-xs font-medium text-text-muted mb-2">Feature Importance</div>
      {importances.map((f) => {
        const width = Math.min(Math.abs(f.impact) / maxImpact * 100, 100)
        const isPositive = f.impact > 0
        return (
          <div key={f.feature} className="flex items-center gap-2 text-xs">
            <span className="w-32 text-text-muted truncate text-right">{f.feature}</span>
            <div className="flex-1 h-4 bg-bg-elevated rounded overflow-hidden relative">
              <div
                className={`h-full rounded ${isPositive ? 'bg-red-500/60' : 'bg-green-500/60'}`}
                style={{ width: `${width}%` }}
              />
            </div>
            <span className={`w-12 text-right ${isPositive ? 'text-red-400' : 'text-green-400'}`}>
              {f.impact > 0 ? '+' : ''}{f.impact.toFixed(2)}
            </span>
          </div>
        )
      })}
    </div>
  )
}

function ErrorDetailPanel({ error, onClose }: { error: DetectedError; onClose: () => void }) {
  return (
    <div className="bg-bg-card border border-border rounded-xl p-5 space-y-4">
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <SeverityBadge severity={error.severity} />
            <span className="text-xs text-text-dim capitalize">{error.error_type}</span>
          </div>
          <h3 className="font-medium">{error.description}</h3>
        </div>
        <button onClick={onClose} className="text-text-dim hover:text-text text-sm">X</button>
      </div>

      <div className="grid grid-cols-3 gap-3 text-xs">
        <div className="bg-bg-elevated rounded-lg p-2">
          <div className="text-text-dim">Round</div>
          <div className="font-medium">{error.round_number}</div>
        </div>
        <div className="bg-bg-elevated rounded-lg p-2">
          <div className="text-text-dim">Confidence</div>
          <div className="font-medium">{(error.confidence * 100).toFixed(0)}%</div>
        </div>
        <div className="bg-bg-elevated rounded-lg p-2">
          <div className="text-text-dim">Model</div>
          <div className="font-medium text-[10px]">{error.model_name}</div>
        </div>
      </div>

      {/* SHAP Waterfall */}
      {error.explanation && error.explanation.feature_importances.length > 0 && (
        <ShapWaterfall importances={error.explanation.feature_importances} />
      )}

      {/* Explanation text */}
      {error.explanation && (
        <div className="bg-bg-elevated rounded-lg p-3">
          <div className="text-xs text-text-dim mb-1">AI Explanation</div>
          <p className="text-sm text-text-muted">{error.explanation.explanation_text}</p>
        </div>
      )}

      {/* Recommendation */}
      {error.recommendation && (
        <div className="bg-primary/5 border border-primary/20 rounded-lg p-3">
          <div className="text-xs text-primary font-medium mb-1">{error.recommendation.title}</div>
          <p className="text-sm text-text-muted">{error.recommendation.description}</p>
          {error.recommendation.expected_impact && (
            <p className="text-xs text-text-dim mt-2">Expected: {error.recommendation.expected_impact}</p>
          )}
        </div>
      )}
    </div>
  )
}

export default function MatchErrorsPage() {
  const params = useParams()
  const router = useRouter()
  const matchId = params.id as string

  const [data, setData] = useState<MatchErrorsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedError, setSelectedError] = useState<DetectedError | null>(null)
  const [severityFilter, setSeverityFilter] = useState<string>('all')
  const [typeFilter, setTypeFilter] = useState<string>('all')
  const [playerFilter, setPlayerFilter] = useState<string>('all')

  const loadErrors = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const result = await api.get<MatchErrorsResponse>(`/matches/${matchId}/errors`)
      setData(result)
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to load errors')
    } finally {
      setLoading(false)
    }
  }, [matchId])

  useEffect(() => {
    loadErrors()
  }, [loadErrors])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 text-text-muted animate-spin" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-20">
        <p className="text-error">{error}</p>
      </div>
    )
  }

  if (!data) return null

  // Get unique players
  const players = [...new Set(data.errors.map((e) => e.player_steam_id))]

  // Filter errors
  const filteredErrors = data.errors.filter((e) => {
    if (severityFilter !== 'all' && e.severity !== severityFilter) return false
    if (typeFilter !== 'all' && e.error_type !== typeFilter) return false
    if (playerFilter !== 'all' && e.player_steam_id !== playerFilter) return false
    return true
  })

  return (
    <div>
      <button
        onClick={() => router.back()}
        className="inline-flex items-center gap-1 text-text-muted hover:text-text text-sm mb-6 transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to Match
      </button>

      <h1 className="text-2xl font-bold mb-2 flex items-center gap-2">
        <AlertTriangle className="h-6 w-6 text-primary" />
        Error Analysis
      </h1>

      {/* Summary Cards */}
      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="bg-bg-card border border-border rounded-xl p-4 text-center">
          <div className="text-3xl font-bold">{data.total_errors}</div>
          <div className="text-text-muted text-xs">Total Errors</div>
        </div>
        <div className="bg-red-500/5 border border-red-500/20 rounded-xl p-4 text-center">
          <div className="text-3xl font-bold text-red-400">{data.critical_count}</div>
          <div className="text-text-muted text-xs">Critical</div>
        </div>
        <div className="bg-amber-500/5 border border-amber-500/20 rounded-xl p-4 text-center">
          <div className="text-3xl font-bold text-amber-400">{data.minor_count}</div>
          <div className="text-text-muted text-xs">Minor</div>
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 mb-4">
        <Filter className="h-4 w-4 text-text-dim" />
        <select
          value={severityFilter}
          onChange={(e) => setSeverityFilter(e.target.value)}
          className="px-3 py-1.5 bg-bg-card border border-border rounded-lg text-sm"
        >
          <option value="all">All Severities</option>
          <option value="critical">Critical</option>
          <option value="minor">Minor</option>
          <option value="info">Info</option>
        </select>
        <select
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          className="px-3 py-1.5 bg-bg-card border border-border rounded-lg text-sm"
        >
          <option value="all">All Types</option>
          <option value="positioning">Positioning</option>
          <option value="utility">Utility</option>
          <option value="timing">Timing</option>
        </select>
        <select
          value={playerFilter}
          onChange={(e) => setPlayerFilter(e.target.value)}
          className="px-3 py-1.5 bg-bg-card border border-border rounded-lg text-sm"
        >
          <option value="all">All Players</option>
          {players.map((p) => (
            <option key={p} value={p}>{p}</option>
          ))}
        </select>
      </div>

      {/* Error list + detail split view */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Error List */}
        <div className="space-y-2">
          {filteredErrors.length === 0 ? (
            <div className="text-center py-10 text-text-dim">
              <Shield className="h-8 w-8 mx-auto mb-2 opacity-50" />
              No errors match filters
            </div>
          ) : (
            filteredErrors.map((err) => (
              <button
                key={err.id}
                onClick={() => setSelectedError(err)}
                className={`w-full text-left bg-bg-card border rounded-lg p-3 transition-colors hover:border-primary/40 ${
                  selectedError?.id === err.id ? 'border-primary/60 bg-primary/5' : 'border-border'
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <SeverityBadge severity={err.severity} />
                    <span className="text-sm font-medium">R{err.round_number}</span>
                    <span className="text-xs text-text-dim capitalize">{err.error_type}</span>
                  </div>
                  <ChevronRight className="h-4 w-4 text-text-dim" />
                </div>
                <p className="text-xs text-text-muted mt-1 line-clamp-1">{err.description}</p>
              </button>
            ))
          )}
        </div>

        {/* Error Detail */}
        <div>
          {selectedError ? (
            <ErrorDetailPanel error={selectedError} onClose={() => setSelectedError(null)} />
          ) : (
            <div className="bg-bg-card border border-border rounded-xl p-10 text-center text-text-dim">
              <AlertTriangle className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">Select an error to view details</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
