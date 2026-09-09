import { useEffect, useMemo, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { getCommunities, getRiskScores, riskScoresToEntities } from '../api/analyze'
import { formatApiError } from '../api/client'
import { useCase } from '../context/CaseContext'
import { useLanguage } from '../i18n/LanguageContext'
import type { Entity } from '../types'

interface RiskScoringViewProps {
  selectedId: string | null
  onSelect: (id: string) => void
  refreshKey?: number
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

export function RiskScoringView({ selectedId, onSelect, refreshKey = 0 }: RiskScoringViewProps) {
  const { t } = useLanguage()
  const { caseId } = useCase()
  const [ranked, setRanked] = useState<Entity[]>([])
  const [communities, setCommunities] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    Promise.all([getRiskScores(caseId), getCommunities(caseId)])
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
  }, [caseId, refreshKey, t.risk.apiError])

  const chartRows = useMemo(() => {
    const rahuls = ranked.filter((e) => e.label.toLowerCase().startsWith('rahul'))
    const others = ranked.filter((e) => !e.label.toLowerCase().startsWith('rahul'))
    const combined = [...rahuls, ...others].slice(0, 12)
    return combined.map((e) => ({
      id: e.id,
      label:
        e.label.length > 14
          ? `${e.label.slice(0, 14)}…`
          : e.label,
      fullLabel: e.label,
      city: e.metadata.city ?? '',
      role: e.role ?? '',
      rank: e.metadata.triage_rank ?? '',
      score: e.score,
      centrality: e.metadata.centrality ?? '0',
      roleScore: e.metadata.role_component ?? '0',
      evidence: e.metadata.case_history ?? '0',
      fill: e.severity === 'high' ? '#9e4a42' : e.severity === 'medium' ? '#b8893a' : '#4a7c59',
    }))
  }, [ranked])

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <header className="border-b border-console-border px-5 py-3">
        <div className="flex items-center gap-3">
          <h1 className="text-base font-semibold text-text-primary">{t.views.risk.header}</h1>
        </div>
        <p className="mt-1 text-sm text-text-secondary">{t.views.risk.description}</p>
        <p className="mt-1 text-xs text-text-muted">{t.risk.chartHint}</p>
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
          <div className="mt-3 h-[320px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartRows} layout="vertical" margin={{ left: 4, right: 12 }}>
                <CartesianGrid stroke="#1e2a3a" horizontal={false} />
                <XAxis type="number" domain={[0, 100]} tick={{ fill: '#5c7085', fontSize: 10 }} />
                <YAxis
                  type="category"
                  dataKey="label"
                  width={100}
                  tick={{ fill: '#8fa3b8', fontSize: 9, fontFamily: 'IBM Plex Mono' }}
                />
                <Tooltip
                  content={({ active, payload }) => {
                    if (!active || !payload?.[0]?.payload) return null
                    const row = payload[0].payload as (typeof chartRows)[0]
                    return (
                      <div className="border border-console-border-strong bg-console-bg p-2 text-xs">
                        <p className="font-semibold text-text-primary">
                          #{row.rank} {row.fullLabel}
                        </p>
                        {row.city && <p className="text-text-muted">{row.city}</p>}
                        {row.role && <p className="text-accent-steel capitalize">{row.role}</p>}
                        <p className="mt-1 text-accent-amber">Score: {row.score}/99</p>
                        <p className="text-text-muted">
                          Network {row.centrality} · Role {row.roleScore} · Evidence {row.evidence}
                        </p>
                      </div>
                    )
                  }}
                />
                <Bar dataKey="score" radius={0}>
                  {chartRows.map((row) => (
                    <Cell
                      key={row.id}
                      fill={row.fill}
                      stroke={selectedId === row.id ? '#d9a441' : undefined}
                      strokeWidth={selectedId === row.id ? 2 : 0}
                    />
                  ))}
                </Bar>
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
                    <span className="block text-sm font-medium text-text-primary">
                      #{entity.metadata.triage_rank} {entity.label}
                      {entity.metadata.city ? ` · ${entity.metadata.city}` : ''}
                    </span>
                    {entity.role && (
                      <span className="text-xs capitalize text-accent-steel">{entity.role}</span>
                    )}
                    <span className="mt-0.5 block text-xs text-text-muted">{entity.explainability[0]}</span>
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
