import { useEffect, useState } from 'react'
import { getEntityExplanation } from '../api/explain'
import { useLanguage } from '../i18n/LanguageContext'
import type { ReviewDecision, Entity } from '../types'
import { CollapsibleSection } from './CollapsibleSection'
import { IngestPanel } from './IngestPanel'

interface InspectorPanelProps {
  entity: Entity | null
  entityLookup: Record<string, Entity>
  caseId: string
  reviewDecision: ReviewDecision
  onReview: (decision: ReviewDecision) => void
  onIngested?: (summary: string) => void
}

function severityClass(severity: Entity['severity']) {
  if (severity === 'high') return 'text-risk-high border-risk-high/40 bg-risk-high/10'
  if (severity === 'medium') return 'text-risk-medium border-risk-medium/40 bg-risk-medium/10'
  return 'text-risk-low border-risk-low/40 bg-risk-low/10'
}

const reviewKeys: { value: Exclude<ReviewDecision, null>; labelKey: 'confirm' | 'needsEvidence' | 'dismiss'; hintKey: 'confirmHint' | 'needsEvidenceHint' | 'dismissHint' }[] = [
  { value: 'confirm', labelKey: 'confirm', hintKey: 'confirmHint' },
  { value: 'needs_evidence', labelKey: 'needsEvidence', hintKey: 'needsEvidenceHint' },
  { value: 'dismiss', labelKey: 'dismiss', hintKey: 'dismissHint' },
]

export function InspectorPanel({ entity, entityLookup, caseId, reviewDecision, onReview, onIngested }: InspectorPanelProps) {
  const { t } = useLanguage()
  const [liveExplain, setLiveExplain] = useState<string[]>([])
  const [liveNarrative, setLiveNarrative] = useState<string | null>(null)

  useEffect(() => {
    if (!entity) {
      setLiveExplain([])
      setLiveNarrative(null)
      return
    }
    let cancelled = false
    getEntityExplanation(entity.id, caseId)
      .then((res) => {
        if (cancelled || !res) return
        setLiveExplain(res.reasoning_steps)
        setLiveNarrative(res.narrative)
      })
      .catch(() => {
        if (!cancelled) {
          setLiveExplain([])
          setLiveNarrative(null)
        }
      })
    return () => {
      cancelled = true
    }
  }, [entity?.id, caseId])

  const explainLines = liveExplain.length > 0 ? liveExplain : entity?.explainability ?? []

  return (
    <aside className="flex h-full w-[min(100%,380px)] shrink-0 flex-col border-l border-console-border bg-console-surface">
      <header className="border-b border-console-border px-4 py-3">
        <h1 className="text-base font-semibold text-text-primary">{t.inspector.title}</h1>
        <p className="mt-1 text-sm text-text-secondary">{t.inspector.subtitle}</p>
      </header>

      {!entity ? (
        <div className="flex flex-1 flex-col overflow-y-auto">
          <IngestPanel
            caseId={caseId}
            onIngested={(result) =>
              onIngested?.(
                `FIR ingested: ${result.entities_extracted} entities extracted, ${result.entities_merged} merged (${result.source_id})`,
              )
            }
          />
          <div className="flex flex-1 flex-col items-center justify-center px-6 text-center">
            <p className="text-base text-text-secondary">{t.inspector.emptyTitle}</p>
            <p className="mt-2 text-sm text-text-muted">{t.inspector.emptyHint}</p>
          </div>
        </div>
      ) : (
        <div className="flex flex-1 flex-col overflow-y-auto">
          <IngestPanel
            caseId={caseId}
            onIngested={(result) =>
              onIngested?.(
                `FIR ingested: ${result.entities_extracted} entities extracted, ${result.entities_merged} merged (${result.source_id})`,
              )
            }
          />
          <section className="border-b border-console-border px-4 py-4">
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="text-xs text-text-muted">{t.entityType[entity.type]}</p>
                <h2 className="mt-1 text-lg font-semibold text-text-primary">{entity.label}</h2>
                {entity.subtitle && <p className="mt-1 text-sm text-text-secondary">{entity.subtitle}</p>}
              </div>
              <span
                className={`shrink-0 border px-2 py-1 text-[11px] font-semibold ${severityClass(entity.severity)}`}
              >
                {t.severity[entity.severity]}
              </span>
            </div>
            {entity.role && (
              <p className="mt-3 text-sm text-accent-steel">{t.role[entity.role]}</p>
            )}
            <div className="mt-4 flex items-baseline gap-2">
              <p className="text-3xl font-semibold text-accent-amber">{entity.score}</p>
              <p className="text-sm text-text-muted">{t.inspector.importanceScore}</p>
            </div>
          </section>

          {liveNarrative && (
            <section className="border-b border-console-border bg-accent-steel/5 px-4 py-4">
              <h3 className="text-sm font-semibold text-accent-steel">Court-defensible summary</h3>
              <p className="mt-2 text-sm leading-relaxed text-text-primary">{liveNarrative}</p>
            </section>
          )}

          <section className="border-b border-console-border px-4 py-4">
            <h3 className="text-sm font-semibold text-text-primary">{t.inspector.whyFlagged}</h3>
            <ul className="mt-3 space-y-2">
              {explainLines.map((line) => (
                <li key={line} className="text-sm leading-relaxed text-text-primary">
                  • {line}
                </li>
              ))}
            </ul>
          </section>

          {entity.aliases && entity.aliases.length > 0 && (
            <section className="border-b border-console-border px-4 py-4">
              <h3 className="text-sm font-semibold text-text-primary">{t.inspector.alsoKnownAsTitle}</h3>
              <ul className="mt-3 space-y-2">
                {entity.aliases.map((alias) => (
                  <li
                    key={alias}
                    className="border border-accent-steel/30 bg-accent-steel/5 px-3 py-2 text-sm text-text-primary"
                  >
                    {alias}
                  </li>
                ))}
              </ul>
              <p className="mt-3 text-xs leading-relaxed text-text-muted">{t.inspector.identityNote}</p>
            </section>
          )}

          <section className="border-b border-console-border px-4 py-4">
            <h3 className="text-sm font-semibold text-text-primary">{t.inspector.linkedTo}</h3>
            <ul className="mt-3 space-y-3">
              {entity.connections.map((c) => {
                const target = entityLookup[c.targetId]
                return (
                  <li key={c.targetId} className="text-sm text-text-secondary">
                    <span className="font-medium text-text-primary">
                      {target?.label ?? c.targetId}
                    </span>
                    <span className="text-text-muted"> — </span>
                    {c.reason}
                  </li>
                )
              })}
            </ul>
          </section>

          <CollapsibleSection title={t.inspector.techTitle} subtitle={t.inspector.techSubtitle}>
            <dl className="space-y-2">
              <div className="flex justify-between gap-2 text-xs">
                <dt className="text-text-muted">{t.inspector.recordId}</dt>
                <dd className="font-mono-data text-text-primary">{entity.id}</dd>
              </div>
              {Object.entries(entity.metadata).map(([k, v]) => (
                <div key={k} className="flex justify-between gap-2 text-xs">
                  <dt className="font-mono-data text-text-muted">{k}</dt>
                  <dd className="font-mono-data text-text-primary">{v}</dd>
                </div>
              ))}
            </dl>
          </CollapsibleSection>

          <section className="px-4 py-4">
            <h3 className="text-sm font-semibold text-text-primary">{t.inspector.yourDecision}</h3>
            <p className="mt-1 text-sm text-text-secondary">{t.inspector.decisionHint}</p>
            <div className="mt-4 grid grid-cols-1 gap-2">
              {reviewKeys.map(({ value, labelKey, hintKey }) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => onReview(reviewDecision === value ? null : value)}
                  className={`min-h-[52px] border px-3 py-3 text-left transition-colors ${
                    reviewDecision === value
                      ? 'border-accent-amber bg-accent-amber/15 ring-1 ring-accent-amber'
                      : 'border-console-border-strong hover:bg-console-raised'
                  }`}
                >
                  <span className="block text-sm font-medium text-text-primary">{t.review[labelKey]}</span>
                  <span className="mt-0.5 block text-xs text-text-muted">{t.review[hintKey]}</span>
                </button>
              ))}
            </div>
          </section>
        </div>
      )}
    </aside>
  )
}
