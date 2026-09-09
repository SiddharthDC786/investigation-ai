import { useEffect, useState } from 'react'
import { getCaseStats } from '../api/case'
import { isApiConfigured } from '../api/client'
import { useCase } from '../context/CaseContext'
import { useLanguage } from '../i18n/LanguageContext'

const STAT_KEYS = ['people', 'cases', 'networks', 'identityScenarios'] as const

export function CaseStatsStrip() {
  const { t } = useLanguage()
  const { caseId, refreshKey } = useCase()
  const [liveLine, setLiveLine] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(false)

  useEffect(() => {
    if (!isApiConfigured() || !caseId) return
    let cancelled = false
    setLoading(true)
    setError(false)
    void getCaseStats(caseId)
      .then((stats) => {
        if (cancelled || !stats) return
        setLiveLine(
          `${stats.persons} people linked · ${stats.cdr_records} calls · ${stats.transactions} transfers · ${stats.timeline_events} events`,
        )
      })
      .catch(() => {
        if (!cancelled) {
          setLiveLine(null)
          setError(true)
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [caseId, refreshKey])

  if (loading && isApiConfigured()) {
    return (
      <div className="shrink-0 border-b border-console-border bg-console-bg px-4 py-2 text-xs text-text-muted">
        Loading case statistics…
      </div>
    )
  }

  if (liveLine) {
    return (
      <div className="flex shrink-0 flex-wrap items-center gap-2 border-b border-console-border bg-console-bg px-4 py-2">
        <span className="border border-risk-low/40 bg-risk-low/10 px-2.5 py-1 text-[11px] text-risk-low">
          {liveLine}
        </span>
        {error && (
          <span className="text-[11px] text-risk-medium">Some stats unavailable — retry after ingest.</span>
        )}
      </div>
    )
  }

  return (
    <div className="flex shrink-0 flex-wrap items-center gap-2 border-b border-console-border bg-console-bg px-4 py-2">
      {STAT_KEYS.map((key) => (
        <span
          key={key}
          className="border border-console-border-strong bg-console-raised px-2.5 py-1 text-[11px] text-text-secondary"
        >
          {t.stats[key]}
        </span>
      ))}
    </div>
  )
}
