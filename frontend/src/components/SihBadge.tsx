import { useLanguage } from '../i18n/LanguageContext'

export function SihBadge({ compact = false }: { compact?: boolean }) {
  const { t } = useLanguage()

  if (compact) {
    return (
      <span className="border border-accent-steel/40 bg-accent-steel/10 px-2 py-0.5 text-[10px] font-semibold text-accent-steel">
        {t.sih.problemId}
      </span>
    )
  }

  return (
    <div className="border border-accent-steel/30 bg-accent-steel/5 px-3 py-2">
      <p className="text-[10px] font-semibold uppercase tracking-wider text-accent-steel">{t.sih.problemId}</p>
      <p className="mt-0.5 text-xs text-text-secondary">{t.sih.tagline}</p>
    </div>
  )
}
