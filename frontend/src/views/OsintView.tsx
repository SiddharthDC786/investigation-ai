import { CASE_ID, entityMap, narrativeTags, osintLookups } from '../data/mockCase'
import { useLanguage } from '../i18n/LanguageContext'
import type { AuditEntry } from '../types'

interface OsintViewProps {
  selectedId: string | null
  onRunLookup: (lookupId: string, entityId: string) => void
  recentLogs: AuditEntry[]
}

export function OsintView({ selectedId, onRunLookup, recentLogs }: OsintViewProps) {
  const { t } = useLanguage()
  const entity = selectedId ? entityMap[selectedId] : null

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="border-b border-risk-medium/30 bg-risk-medium/5 px-5 py-2.5">
        <p className="text-sm text-risk-medium">{t.osint.policy}</p>
      </div>

      <header className="border-b border-console-border px-5 py-3">
        <div className="flex items-center gap-3">
          <h1 className="text-base font-semibold text-text-primary">{t.views.osint.header}</h1>
          <span className="border border-accent-steel/30 bg-accent-steel/10 px-2 py-0.5 text-[10px] text-accent-steel">
            {narrativeTags.osint}
          </span>
        </div>
        <p className="mt-1 text-sm text-text-secondary">{t.views.osint.description}</p>
      </header>

      <div className="grid flex-1 grid-cols-1 gap-0 overflow-hidden lg:grid-cols-2">
        <section className="border-b border-console-border p-5 lg:border-b-0 lg:border-r">
          <h2 className="text-sm font-semibold text-text-primary">{t.osint.selectedTarget}</h2>
          {entity ? (
            <div className="mt-3 border border-console-border bg-console-raised p-4">
              <p className="text-lg font-semibold text-text-primary">{entity.label}</p>
              <p className="mt-1 text-sm text-text-secondary">
                {t.entityType[entity.type]}
                {entity.role ? ` · ${t.role[entity.role]}` : ''}
              </p>
            </div>
          ) : (
            <p className="mt-3 text-sm text-text-muted">{t.osint.selectFirst}</p>
          )}

          <h2 className="mt-6 text-sm font-semibold text-text-primary">{t.osint.availableSearches}</h2>
          <ul className="mt-3 space-y-3">
            {osintLookups.map((lookup) => (
              <li key={lookup.id} className="border border-console-border bg-console-bg p-4">
                <p className="text-sm font-medium text-text-primary">{lookup.label}</p>
                <p className="mt-1 text-sm text-text-secondary">{lookup.description}</p>
                <button
                  type="button"
                  disabled={!entity}
                  onClick={() => entity && onRunLookup(lookup.id, entity.id)}
                  className="mt-3 min-h-[44px] border border-accent-amber/50 px-4 py-2 text-sm font-medium text-accent-amber transition-colors hover:bg-accent-amber/10 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {t.osint.runSearch}
                </button>
              </li>
            ))}
          </ul>
        </section>

        <section className="flex flex-col overflow-hidden p-5">
          <h2 className="text-sm font-semibold text-text-primary">{t.osint.recentSearches}</h2>
          <div className="mt-3 flex-1 overflow-y-auto border border-console-border bg-console-bg">
            {recentLogs.filter((l) => l.action.includes('OSINT')).length === 0 ? (
              <p className="p-4 text-sm text-text-muted">{t.osint.noSearches}</p>
            ) : (
              recentLogs
                .filter((l) => l.action.includes('OSINT'))
                .map((log) => (
                  <div key={log.id} className="border-b border-console-border px-4 py-3 text-sm">
                    <p className="text-xs text-accent-amber">{log.timestamp}</p>
                    <p className="mt-1 text-text-primary">{log.action}</p>
                    <p className="mt-1 text-xs text-text-muted">{log.source}</p>
                  </div>
                ))
            )}
          </div>
          <p className="mt-3 text-xs text-text-muted">
            {t.osint.caseLabel}: {CASE_ID}
          </p>
        </section>
      </div>
    </div>
  )
}
