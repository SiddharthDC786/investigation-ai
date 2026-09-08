import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { entities, narrativeTags } from '../data/mockCase'
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
  const ranked = [...entities].sort((a, b) => b.score - a.score)
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

        <div className="overflow-y-auto">
          <table className="w-full text-left text-xs">
            <thead className="sticky top-0 bg-console-surface text-xs text-text-muted">
              <tr className="border-b border-console-border">
                <th className="px-4 py-3 font-semibold">{t.risk.colName}</th>
                <th className="px-2 py-3 font-semibold">{t.risk.colScore}</th>
                <th className="px-2 py-3 font-semibold">{t.risk.colPriority}</th>
                <th className="px-2 py-3 font-semibold">{t.risk.colType}</th>
              </tr>
            </thead>
            <tbody>
              {ranked.map((entity, rank) => (
                <tr
                  key={entity.id}
                  onClick={() => onSelect(entity.id)}
                  className={`cursor-pointer border-b border-console-border/60 transition-colors hover:bg-console-raised ${
                    selectedId === entity.id ? 'bg-console-raised ring-1 ring-inset ring-accent-amber/40' : ''
                  }`}
                >
                  <td className="px-4 py-3">
                    <span className="text-xs text-text-muted">#{rank + 1}</span>
                    <p className="text-sm font-medium text-text-primary">{entity.label}</p>
                  </td>
                  <td className="px-2 py-3 text-base text-accent-amber">{entity.score}</td>
                  <td className="px-2 py-3">{severityBadge(entity.severity, t.severity[entity.severity])}</td>
                  <td className="px-2 py-3 text-sm text-text-secondary">{t.entityType[entity.type]}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
