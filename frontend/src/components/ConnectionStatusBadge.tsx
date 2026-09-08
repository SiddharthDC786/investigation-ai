import { isApiConfigured } from '../api/client'
import { useLanguage } from '../i18n/LanguageContext'

export function ConnectionStatusBadge() {
  const { t } = useLanguage()
  const live = isApiConfigured()

  return (
    <div
      className={`border px-2.5 py-1 text-center ${
        live
          ? 'border-risk-low/50 bg-risk-low/10'
          : 'border-accent-amber/40 bg-accent-amber/10'
      }`}
      title={live ? t.connection.liveHint : t.connection.demoHint}
    >
      <p className="flex items-center justify-center gap-1.5 text-[10px] font-semibold uppercase tracking-wide">
        <span
          className={`inline-block h-1.5 w-1.5 rounded-full ${live ? 'bg-risk-low' : 'bg-accent-amber'}`}
          aria-hidden
        />
        {live ? t.connection.live : t.connection.demo}
      </p>
    </div>
  )
}
