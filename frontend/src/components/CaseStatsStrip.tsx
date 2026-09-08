import { useLanguage } from '../i18n/LanguageContext'

const STAT_KEYS = ['people', 'cases', 'networks', 'identityScenarios'] as const

export function CaseStatsStrip() {
  const { t } = useLanguage()

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
