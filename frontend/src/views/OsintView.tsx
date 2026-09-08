import { useCallback, useEffect, useState } from 'react'
import {
  enrichEntity,
  getOsintAuditLog,
  type OsintEnrichResponse,
  verifyAuditChain,
} from '../api/osint'
import { CASE_ID, narrativeTags, osintLookups } from '../data/mockCase'
import { useAuth } from '../auth/AuthContext'
import { useLanguage } from '../i18n/LanguageContext'
import type { AuditEntry, Entity } from '../types'

interface OsintViewProps {
  selectedId: string | null
  entityLookup: Record<string, Entity>
  onRunLookup: (lookupId: string, entityId: string, result?: OsintEnrichResponse) => void
  recentLogs: AuditEntry[]
  onAuditRefresh?: (entries: AuditEntry[]) => void
}

export function OsintView({
  selectedId,
  entityLookup,
  onRunLookup,
  recentLogs,
  onAuditRefresh,
}: OsintViewProps) {
  const { t } = useLanguage()
  const { user } = useAuth()
  const entity = selectedId ? entityLookup[selectedId] : null
  const [loading, setLoading] = useState<string | null>(null)
  const [lastResult, setLastResult] = useState<OsintEnrichResponse | null>(null)
  const [chainStatus, setChainStatus] = useState<string>('unknown')
  const [error, setError] = useState<string | null>(null)

  const refreshAudit = useCallback(async () => {
    try {
      const [log, verify] = await Promise.all([
        getOsintAuditLog(CASE_ID),
        verifyAuditChain(CASE_ID),
      ])
      setChainStatus(verify.status)
      onAuditRefresh?.(log.entries)
    } catch {
      setChainStatus('offline')
    }
  }, [onAuditRefresh])

  useEffect(() => {
    refreshAudit()
  }, [refreshAudit])

  const runLookup = async (lookupId: string) => {
    if (!entity) return
    setError(null)
    setLoading(lookupId)
    try {
      const result = await enrichEntity({
        case_id: CASE_ID,
        entity_id: entity.id,
        lookup_id: lookupId,
        operator: user?.badgeId ?? 'INV-2847',
        operator_name: user?.name ?? 'Investigator',
      })
      setLastResult(result)
      onRunLookup(lookupId, entity.id, result)
      await refreshAudit()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Lookup failed')
      onRunLookup(lookupId, entity.id)
    } finally {
      setLoading(null)
    }
  }

  const osintLogs = recentLogs.filter((l) => l.action.includes('OSINT'))

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="border-b border-risk-medium/30 bg-risk-medium/5 px-5 py-2.5">
        <p className="text-sm text-risk-medium">{t.osint.policy}</p>
        {chainStatus === 'verified' && (
          <p className="mt-1 text-xs text-risk-low">Audit hash chain: verified</p>
        )}
        {chainStatus === 'broken' && (
          <p className="mt-1 text-xs text-risk-high">Audit hash chain: TAMPER DETECTED</p>
        )}
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

          {error && <p className="mt-3 text-sm text-risk-high">{error}</p>}

          <h2 className="mt-6 text-sm font-semibold text-text-primary">{t.osint.availableSearches}</h2>
          <ul className="mt-3 space-y-3">
            {osintLookups.map((lookup) => (
              <li key={lookup.id} className="border border-console-border bg-console-bg p-4">
                <p className="text-sm font-medium text-text-primary">{lookup.label}</p>
                <p className="mt-1 text-sm text-text-secondary">{lookup.description}</p>
                <button
                  type="button"
                  disabled={!entity || loading === lookup.id}
                  onClick={() => runLookup(lookup.id)}
                  className="mt-3 min-h-[44px] border border-accent-amber/50 px-4 py-2 text-sm font-medium text-accent-amber transition-colors hover:bg-accent-amber/10 disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {loading === lookup.id ? '…' : t.osint.runSearch}
                </button>
              </li>
            ))}
          </ul>

          {lastResult && (
            <div className="mt-6 border border-accent-steel/30 bg-accent-steel/5 p-4">
              <p className="text-xs font-semibold text-accent-steel">Latest enrichment</p>
              <ul className="mt-2 space-y-2">
                {lastResult.results.map((hit) => (
                  <li key={hit.title} className="text-sm text-text-secondary">
                    <span className="font-medium text-text-primary">{hit.title}</span>
                    <br />
                    {hit.detail}
                  </li>
                ))}
              </ul>
              <p className="mt-2 font-mono text-[10px] text-text-muted">
                audit {lastResult.audit_entry_id} · {lastResult.audit_hash.slice(0, 16)}…
              </p>
            </div>
          )}
        </section>

        <section className="flex flex-col overflow-hidden p-5">
          <h2 className="text-sm font-semibold text-text-primary">{t.osint.recentSearches}</h2>
          <div className="mt-3 flex-1 overflow-y-auto border border-console-border bg-console-bg">
            {osintLogs.length === 0 ? (
              <p className="p-4 text-sm text-text-muted">{t.osint.noSearches}</p>
            ) : (
              osintLogs.map((log) => (
                <div key={log.id} className="border-b border-console-border px-4 py-3 text-sm">
                  <p className="text-xs text-accent-amber">{log.timestamp}</p>
                  <p className="mt-1 text-text-primary">{log.action}</p>
                  <p className="mt-1 text-xs text-text-muted">{log.source}</p>
                  <p className="mt-1 text-xs text-text-muted">{log.operator}</p>
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
