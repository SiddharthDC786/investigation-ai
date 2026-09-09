import { useCallback, useEffect, useState } from 'react'
import { getEntityExplanation } from '../api/explain'
import {
  enrichEntity,
  getOsintAuditLog,
  type OsintEnrichResponse,
  verifyAuditChain,
} from '../api/osint'
import { CASE_DISPLAY_REF, osintLookups } from '../data/mockCase'
import { useCase } from '../context/CaseContext'
import { useLanguage } from '../i18n/LanguageContext'
import { getPersonPhoneDisplay } from '../lib/investigationSearch'
import type { AuditEntry, Entity } from '../types'

interface OsintViewProps {
  selectedId: string | null
  entityLookup: Record<string, Entity>
  onRunLookup: (lookupId: string, entityId: string, result?: OsintEnrichResponse) => void
  recentLogs: AuditEntry[]
  onAuditRefresh?: (entries: AuditEntry[], chainStatus?: string) => void
}

export function OsintView({
  selectedId,
  entityLookup,
  onRunLookup,
  recentLogs,
  onAuditRefresh,
}: OsintViewProps) {
  const { t } = useLanguage()
  const { caseId } = useCase()
  const entity = selectedId ? entityLookup[selectedId] : null
  const personEntity = entity?.type === 'person' ? entity : entity?.metadata?.person_id
    ? entityLookup[entity.metadata.person_id]
    : null
  const dossier = personEntity ?? (entity?.type === 'person' ? entity : null)

  const [loading, setLoading] = useState<string | null>(null)
  const [lastResult, setLastResult] = useState<OsintEnrichResponse | null>(null)
  const [chainStatus, setChainStatus] = useState<string>('unknown')
  const [error, setError] = useState<string | null>(null)
  const [explain, setExplain] = useState<Awaited<ReturnType<typeof getEntityExplanation>>>(null)

  const refreshAudit = useCallback(async () => {
    try {
      const [log, verify] = await Promise.all([
        getOsintAuditLog(caseId),
        verifyAuditChain(caseId),
      ])
      setChainStatus(verify.status)
      onAuditRefresh?.(log.entries, verify.status)
    } catch {
      setChainStatus('offline')
    }
  }, [onAuditRefresh, caseId])

  useEffect(() => {
    refreshAudit()
  }, [refreshAudit])

  useEffect(() => {
    if (!dossier?.id) {
      setExplain(null)
      return
    }
    let cancelled = false
    getEntityExplanation(dossier.id, caseId)
      .then((res) => {
        if (!cancelled) setExplain(res)
      })
      .catch(() => {
        if (!cancelled) setExplain(null)
      })
    return () => {
      cancelled = true
    }
  }, [dossier?.id, caseId])

  const runLookup = async (lookupId: string) => {
    const target = dossier ?? entity
    if (!target) return
    setError(null)
    setLoading(lookupId)
    try {
      const result = await enrichEntity({
        case_id: caseId,
        entity_id: target.id,
        lookup_id: lookupId,
      })
      setLastResult(result)
      onRunLookup(lookupId, target.id, result)
      await refreshAudit()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Lookup failed')
      onRunLookup(lookupId, target.id)
    } finally {
      setLoading(null)
    }
  }

  const osintLogs = recentLogs.filter(
    (l) => l.action.includes('OSINT') && (!dossier || l.entityId === dossier.id),
  )

  const phone = dossier ? getPersonPhoneDisplay(dossier.id) : null

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="border-b border-risk-medium/30 bg-risk-medium/5 px-5 py-2.5">
        <p className="text-sm font-semibold text-risk-medium">SIMULATED OSINT — synthetic demo data only</p>
        <p className="mt-1 text-xs text-text-secondary">{t.osint.policy}</p>
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
        </div>
        <p className="mt-1 text-sm text-text-secondary">{t.views.osint.description}</p>
      </header>

      <div className="grid flex-1 grid-cols-1 gap-0 overflow-hidden lg:grid-cols-2">
        <section className="overflow-y-auto border-b border-console-border p-5 lg:border-b-0 lg:border-r">
          <h2 className="text-sm font-semibold text-text-primary">{t.osint.dossierTitle}</h2>
          {dossier ? (
            <div className="mt-3 space-y-4">
              <div className="border border-accent-amber/40 bg-accent-amber/5 p-4">
                <p className="text-lg font-semibold text-text-primary">{dossier.label}</p>
                <p className="mt-1 text-sm text-text-secondary">
                  {dossier.role ? t.role[dossier.role] : t.entityType.person}
                  {dossier.metadata.city ? ` · ${dossier.metadata.city}` : ''}
                </p>
                <dl className="mt-3 grid gap-1 text-sm text-text-primary">
                  {dossier.metadata.dob && (
                    <div>
                      <dt className="inline text-text-muted">DOB: </dt>
                      <dd className="inline">{dossier.metadata.dob}</dd>
                    </div>
                  )}
                  {dossier.metadata.age && (
                    <div>
                      <dt className="inline text-text-muted">Age: </dt>
                      <dd className="inline">{dossier.metadata.age}</dd>
                    </div>
                  )}
                  {dossier.metadata.gender && (
                    <div>
                      <dt className="inline text-text-muted">Gender: </dt>
                      <dd className="inline">{dossier.metadata.gender}</dd>
                    </div>
                  )}
                  {phone && (
                    <div>
                      <dt className="inline text-text-muted">Phone: </dt>
                      <dd className="inline">{phone}</dd>
                    </div>
                  )}
                </dl>
              </div>

              {explain && explain.relationships.length > 0 && (
                <div className="border border-console-border bg-console-raised p-4">
                  <h3 className="text-xs font-semibold text-text-primary">{t.osint.relationships}</h3>
                  <ul className="mt-2 space-y-2 text-sm">
                    {explain.relationships.slice(0, 8).map((rel) => (
                      <li key={rel.related_entity_id} className="text-text-secondary">
                        <span className="font-medium text-text-primary">{rel.related_label}</span>
                        {' — '}
                        {rel.relationship.replace(/_/g, ' ')}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {explain && explain.source_citations.length > 0 && (
                <div className="border border-console-border bg-console-bg p-4">
                  <h3 className="text-xs font-semibold text-text-primary">{t.osint.sourcesCited}</h3>
                  <ul className="mt-2 space-y-1 text-xs text-text-muted">
                    {explain.source_citations.slice(0, 6).map((c, i) => (
                      <li key={`${c.source_id}-${i}`}>
                        {c.source_type}: {c.excerpt ?? c.source_id}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {explain?.narrative && (
                <p className="text-sm leading-relaxed text-text-secondary">{explain.narrative}</p>
              )}
            </div>
          ) : (
            <p className="mt-3 text-sm text-text-muted">{t.osint.selectFirst}</p>
          )}

          {error && <p className="mt-3 text-sm text-risk-high">{error}</p>}

          <h2 className="mt-6 text-sm font-semibold text-text-primary">{t.osint.availableSearches}</h2>
          <p className="mt-1 text-xs text-text-muted">{t.osint.runLookupHint}</p>
          <ul className="mt-3 space-y-3">
            {osintLookups.map((lookup) => (
              <li key={lookup.id} className="border border-console-border bg-console-bg p-4">
                <p className="text-sm font-medium text-text-primary">{lookup.label}</p>
                <p className="mt-1 text-sm text-text-secondary">{lookup.description}</p>
                <button
                  type="button"
                  disabled={!dossier || loading === lookup.id}
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
              <p className="text-xs font-semibold text-accent-steel">
                Latest lookup result {lastResult.simulated ? '(simulated — review required)' : ''}
              </p>
              {lastResult.disclaimer && (
                <p className="mt-1 text-xs text-text-muted">{lastResult.disclaimer}</p>
              )}
              <ul className="mt-2 space-y-2">
                {lastResult.results.map((hit) => (
                  <li key={hit.title} className="text-sm text-text-secondary">
                    <span className="font-medium text-text-primary">{hit.title}</span>
                    <span className="ml-2 text-xs text-text-muted">
                      relevance {hit.relevance_score}/100 · {hit.source_type}
                    </span>
                    <br />
                    {hit.detail}
                  </li>
                ))}
              </ul>
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
                </div>
              ))
            )}
          </div>
          <p className="mt-3 text-xs text-text-muted">
            {t.osint.caseLabel}: {CASE_DISPLAY_REF}
          </p>
        </section>
      </div>
    </div>
  )
}
