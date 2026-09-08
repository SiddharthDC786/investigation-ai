import { useEffect, useState } from 'react'
import { getCaseStats } from '../api/case'
import { isApiConfigured } from '../api/client'
import { CASE_ID } from '../data/mockCase'
import { useLanguage } from '../i18n/LanguageContext'

const STAT_KEYS = ['people', 'cases', 'networks', 'identityScenarios'] as const

export function CaseStatsStrip() {
  const { t } = useLanguage()
  const [liveLine, setLiveLine] = useState<string | null>(null)

  useEffect(() => {
    if (!isApiConfigured()) return
    let cancelled = false
    void getCaseStats(CASE_ID)
      .then((stats) => {
        if (cancelled || !stats) return
        setLiveLine(
          `${stats.persons} linked · ${stats.cdr_records} CDR · ${stats.transactions} TXN · ${stats.timeline_events} events`,
        )
      })
      .catch(() => {
        if (!cancelled) setLiveLine(null)
      })
    return () => {
      cancelled = true
    }
  }, [])

  if (liveLine) {
    return (
      <div className="flex shrink-0 flex-wrap items-center gap-2 border-b border-console-border bg-console-bg px-4 py-2">
        <span className="border border-risk-low/40 bg-risk-low/10 px-2.5 py-1 text-[11px] text-risk-low">
          {CASE_ID} — {liveLine}
        </span>
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
