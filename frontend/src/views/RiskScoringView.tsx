import { useEffect, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { getCommunities, getRiskScores, riskScoresToEntities } from '../api/analyze'
import { formatApiError } from '../api/client'
import { CASE_ID, narrativeTags } from '../data/mockCase'
import { useLanguage } from '../i18n/LanguageContext'
import type { Entity } from '../types'

interface RiskScoringViewProps {
  selectedId: string | null
  onSelect: (id: string) => void
}

function severityBadge(severity: Entity['severity'], label: string) {
  const cls = {
    high: 'text-risk-high border-risk-high/40',
    medium: 'text-risk-medium border-risk-medium/40',
    low: 'text-risk-low border-risk-low/40',
  }[severity]
  return (
    <span className={`border px-2 py-0.5 text-[11px] font-semibold ${cls}`}>{label}</span>
  )
}

export function RiskScoringView({ selectedId, onSelect }: RiskScoringViewProps) {
  const { t } = useLanguage()
  const [ranked, setRanked] = useState<Entity[]>([])
  const [communities, setCommunities] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    Promise.all([getRiskScores(CASE_ID), getCommunities(CASE_ID)])
      .then(([risk, comm]) => {
        if (cancelled) return
        setRanked(riskScoresToEntities(risk.scores))
        setCommunities(comm.communities.map((c) => `${c.label} (${c.member_count})`))
      })
      .catch((err) => {
        if (cancelled) return
        setRanked([])
        setCommunities([])
        setError(formatApiError(err, t.risk.apiError))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [t.risk.apiError])

  const chartData = ranked.map((e) => ({
    id: e.id,
    label: e.label.length > 12 ? `${e.label.slice(0, 12)}…` : e.label,
    score: e.score,
    fill: e.severity === 'high' ? '#9e4a42' : e.severity === 'medium' ? '#b8893a' : '#4a7c59',
  }))

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <header className="border-b border-console-border px-5 py-3">
        <div className="flex items-center gap-3">
          <h1 className="text-base font-semibold text-text-primary">{t.views.risk.header}</h1>
          <span className="border border-accent-amber/40 bg-accent-amber/10 px-2 py-0.5 text-[10px] text-accent-amber">
            {narrativeTags.risk}
          </span>
        </div>
        <p className="mt-1 text-sm text-text-secondary">{t.views.risk.description}</p>
        {loading && <p className="mt-2 text-sm text-text-muted">{t.risk.loading}</p>}
        {error && (
          <p className="mt-2 border border-risk-high/40 bg-risk-high/10 px-3 py-2 text-sm text-risk-high">
            {error}
          </p>
        )}
        {!loading && !error && ranked.length === 0 && (
          <p className="mt-2 text-sm text-text-muted">{t.risk.empty}</p>
        )}
      </header>

      <div className="grid flex-1 grid-cols-1 gap-0 overflow-hidden lg:grid-cols-2">
        <div className="border-b border-console-border p-4 lg:border-b-0 lg:border-r">
          <h2 className="text-sm font-semibold text-text-primary">{t.risk.scoreChart}</h2>
          <div className="mt-3 h-[280px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} layout="vertical" margin={{ left: 8, right: 8 }}>
                <CartesianGrid stroke="#1e2a3a" horizontal={false} />
                <XAxis type="number" domain={[0, 100]} tick={{ fill: '#5c7085', fontSize: 10 }} />
                <YAxis
                  type="category"
                  dataKey="label"
                  width={90}
                  tick={{ fill: '#8fa3b8', fontSize: 10, fontFamily: 'IBM Plex Mono' }}
                />
                <Tooltip
                  contentStyle={{
                    background: '#0d1219',
                    border: '1px solid #1e2a3a',
                    borderRadius: 0,
                    fontFamily: 'IBM Plex Mono',
                    fontSize: 11,
                  }}
                />
                <Bar dataKey="score" radius={0} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="overflow-y-auto p-4">
          <h2 className="text-sm font-semibold text-text-primary">{t.risk.colPriority}</h2>
          {communities.length > 0 && (
            <div className="mt-2 border border-console-border bg-console-raised p-3 text-xs text-text-secondary">
              <p className="font-semibold text-accent-steel">Detected rings (Louvain)</p>
              <ul className="mt-2 list-inside list-disc space-y-1">
                {communities.slice(0, 4).map((c) => (
                  <li key={c}>{c}</li>
                ))}
              </ul>
            </div>
          )}
          <ul className="mt-4 space-y-2">
            {ranked.map((entity) => (
              <li key={entity.id}>
                <button
                  type="button"
                  onClick={() => onSelect(entity.id)}
                  className={`flex w-full items-center justify-between border px-3 py-2 text-left transition-colors ${
                    selectedId === entity.id
                      ? 'border-accent-amber bg-accent-amber/5'
                      : 'border-console-border hover:border-accent-steel'
                  }`}
                >
                  <span>
                    <span className="block text-sm font-medium text-text-primary">{entity.label}</span>
                    <span className="text-xs text-text-muted">{entity.explainability[0]}</span>
                  </span>
                  <span className="flex items-center gap-2">
                    <span className="font-mono text-sm text-accent-amber">{entity.score}</span>
                    {severityBadge(
                      entity.severity,
                      entity.severity === 'high'
                        ? 'High'
                        : entity.severity === 'medium'
                          ? 'Medium'
                          : 'Low',
                    )}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}
