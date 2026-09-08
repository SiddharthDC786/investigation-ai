import { useLanguage } from '../i18n/LanguageContext'
import type { ViewId } from '../types'

const STEPS: ViewId[] = ['search', 'network', 'timeline', 'risk', 'osint', 'audit']

interface InvestigationGuideProps {
  activeView: ViewId
  onNavigate: (view: ViewId) => void
  collapsed: boolean
  onToggle: () => void
}

export function InvestigationGuide({ activeView, onNavigate, collapsed, onToggle }: InvestigationGuideProps) {
  const { t } = useLanguage()

  if (collapsed) {
    return (
      <button
        type="button"
        onClick={onToggle}
        className="shrink-0 border-b border-console-border bg-console-raised px-4 py-3 text-left text-sm text-accent-steel hover:bg-console-surface"
      >
        {t.guide.show}
      </button>
    )
  }

  return (
    <div className="shrink-0 border-b border-console-border bg-console-raised px-4 py-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className="text-sm font-semibold text-text-primary">{t.guide.title}</p>
          <p className="mt-0.5 text-xs text-text-muted">{t.guide.subtitle}</p>
        </div>
        <button type="button" onClick={onToggle} className="text-xs text-text-muted hover:text-text-secondary">
          {t.guide.hide}
        </button>
      </div>
      <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-6">
        {STEPS.map((view, idx) => {
          const step = t.views[view]
          return (
            <button
              key={view}
              type="button"
              onClick={() => onNavigate(view)}
              className={`min-h-[88px] border px-3 py-3 text-left transition-colors ${
                activeView === view
                  ? 'border-accent-amber/50 bg-accent-amber/10'
                  : 'border-console-border bg-console-bg hover:border-accent-steel/40'
              }`}
            >
              <p className="font-mono-data text-[11px] text-accent-amber">
                {t.guide.step} {idx + 1}
              </p>
              <p className="mt-1 text-sm font-medium text-text-primary">{step.title}</p>
              <p className="mt-1.5 text-[11px] leading-snug text-text-muted">{step.hint}</p>
            </button>
          )
        })}
      </div>
    </div>
  )
}
