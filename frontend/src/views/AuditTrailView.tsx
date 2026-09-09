import { useMemo, useState } from 'react'
import { CASE_DISPLAY_REF } from '../data/mockCase'
import { useLanguage } from '../i18n/LanguageContext'
import type { AuditEntry, Entity } from '../types'

interface AuditTrailViewProps {
  logs: AuditEntry[]
  entityLookup?: Record<string, Entity>
  chainStatus?: string
  canExport?: boolean
  exportedBy?: string
  onExported?: () => void
}

function chainLabel(status: string, t: ReturnType<typeof useLanguage>['t']) {
  if (status === 'verified' || status === 'ok') return t.audit.chainVerified
  if (status === 'broken') return t.audit.chainBroken
  return t.audit.chainUnknown
}

function chainClass(status: string) {
  if (status === 'verified' || status === 'ok') return 'border-risk-low/40 text-risk-low bg-risk-low/10'
  if (status === 'broken') return 'border-risk-high/40 text-risk-high bg-risk-high/10'
  return 'border-console-border-strong text-text-muted bg-console-raised'
}

function actionCategory(action: string, t: ReturnType<typeof useLanguage>['t']) {
  const lower = action.toLowerCase()
  if (lower.includes('osint') || lower.includes('lookup')) return t.audit.categoryOsint
  if (lower.includes('search') || lower.includes('person confirmed')) return t.audit.categorySearch
  if (lower.includes('review')) return t.audit.categoryReview
  if (lower.includes('login') || lower.includes('logout')) return t.audit.categoryAuth
  if (lower.includes('ingest') || lower.includes('fir')) return t.audit.categoryIngest
  return t.audit.categoryOther
}

function categoryClass(action: string) {
  const lower = action.toLowerCase()
  if (lower.includes('osint')) return 'border-accent-steel/40 text-accent-steel bg-accent-steel/10'
  if (lower.includes('search') || lower.includes('person confirmed')) return 'border-accent-amber/40 text-accent-amber bg-accent-amber/10'
  if (lower.includes('review')) return 'border-risk-medium/40 text-risk-medium bg-risk-medium/10'
  if (lower.includes('login') || lower.includes('logout')) return 'border-console-border-strong text-text-muted bg-console-raised'
  if (lower.includes('ingest') || lower.includes('fir')) return 'border-risk-low/40 text-risk-low bg-risk-low/10'
  return 'border-console-border text-text-secondary bg-console-bg'
}

function recordLabel(entityId: string, lookup: Record<string, Entity>) {
  const entity = lookup[entityId]
  if (entity) return `${entity.label} (${entityId})`
  return entityId
}

export function AuditTrailView({
  logs,
  entityLookup = {},
  chainStatus = 'unknown',
  canExport = false,
  exportedBy = 'Unknown',
  onExported,
}: AuditTrailViewProps) {
  const { t } = useLanguage()
  const [exportNotice, setExportNotice] = useState<string | null>(null)

  const sortedLogs = useMemo(
    () => [...logs].sort((a, b) => b.timestamp.localeCompare(a.timestamp)),
    [logs],
  )

  function handleExport() {
    if (!canExport) return

    const bundle = {
      watermark: t.audit.exportWatermark,
      caseId: CASE_DISPLAY_REF,
      exportedAt: new Date().toISOString(),
      exportedBy,
      chainStatus,
      entryCount: logs.length,
      entries: logs,
    }

    const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = `vigil-disclosure-${CASE_DISPLAY_REF.replace(/\//g, '-')}-${Date.now()}.json`
    anchor.click()
    URL.revokeObjectURL(url)

    setExportNotice(t.audit.exportSuccess)
    onExported?.()
    window.setTimeout(() => setExportNotice(null), 4000)
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <header className="border-b border-console-border px-5 py-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="text-base font-semibold text-text-primary">{t.views.audit.header}</h1>
              <span className={`border px-2 py-0.5 text-[10px] ${chainClass(chainStatus)}`}>
                {chainLabel(chainStatus, t)}
              </span>
            </div>
            <p className="mt-1 text-sm text-text-secondary">{t.views.audit.description}</p>
          </div>
          <div className="flex flex-col items-end gap-1">
            <button
              type="button"
              onClick={handleExport}
              disabled={!canExport}
              title={canExport ? t.audit.exportTitleSupervisor : t.audit.exportTitleDenied}
              className="min-h-[44px] border border-console-border-strong px-4 py-2 text-sm text-text-secondary hover:border-accent-steel hover:text-accent-steel disabled:cursor-not-allowed disabled:opacity-40 presentation-mode:min-h-[52px]"
            >
              {t.audit.export}
            </button>
            {exportNotice && <p className="text-xs text-risk-low">{exportNotice}</p>}
          </div>
        </div>
      </header>

      <div className="flex-1 overflow-auto">
        {sortedLogs.length === 0 ? (
          <p className="px-5 py-8 text-sm text-text-muted">{t.audit.empty}</p>
        ) : (
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="sticky top-0 bg-console-surface text-xs text-text-muted">
              <tr className="border-b border-console-border">
                <th className="px-4 py-3 font-semibold">{t.audit.colWhen}</th>
                <th className="px-3 py-3 font-semibold">Type</th>
                <th className="px-3 py-3 font-semibold">{t.audit.colAction}</th>
                <th className="px-3 py-3 font-semibold">{t.audit.colRecord}</th>
                <th className="px-3 py-3 font-semibold">{t.audit.colOfficer}</th>
              </tr>
            </thead>
            <tbody>
              {sortedLogs.map((log) => (
                <tr key={log.id} className="border-b border-console-border/50 hover:bg-console-raised/50">
                  <td className="px-4 py-3 text-xs text-accent-amber whitespace-nowrap">{log.timestamp}</td>
                  <td className="px-3 py-3">
                    <span className={`inline-block border px-2 py-0.5 text-[10px] ${categoryClass(log.action)}`}>
                      {actionCategory(log.action, t)}
                    </span>
                  </td>
                  <td className="px-3 py-3 text-text-primary">{log.action}</td>
                  <td className="px-3 py-3 text-xs text-accent-steel">
                    {recordLabel(log.entityId, entityLookup)}
                  </td>
                  <td className="px-3 py-3 text-text-secondary">{log.operator}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
