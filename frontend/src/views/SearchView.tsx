import { useCallback, useMemo, useState, type FormEvent } from 'react'
import { searchByFace, searchInvestigation } from '../api/search'
import { DemoScenarioChips } from '../components/DemoScenarioChips'
import { CASE_ID, narrativeTags } from '../data/mockCase'
import { useLanguage } from '../i18n/LanguageContext'
import { getPersonPhoneDisplay, listSearchAreas, matchTypeLabel } from '../lib/investigationSearch'
import type { Entity, NameMatchHit, RoleFilter, SearchFilters } from '../types'

interface SearchViewProps {
  selectedId: string | null
  onSelect: (id: string) => void
  onSearchPerformed?: (summary: string, entityId: string) => void
  onEntitiesLoaded?: (entities: Entity[]) => void
}

const emptyFilters: SearchFilters = {
  nameQuery: '',
  phoneQuery: '',
  areaQuery: '',
  roleFilter: 'all',
  faceMatchPersonId: null,
  selectedPersonId: null,
}

export function SearchView({ selectedId, onSelect, onSearchPerformed, onEntitiesLoaded }: SearchViewProps) {
  const { t } = useLanguage()
  const areas = useMemo(() => listSearchAreas(), [])
  const [filters, setFilters] = useState<SearchFilters>(emptyFilters)
  const [draft, setDraft] = useState(emptyFilters)
  const [results, setResults] = useState<Awaited<ReturnType<typeof searchInvestigation>> | null>(null)
  const [loading, setLoading] = useState(false)
  const [faceStatus, setFaceStatus] = useState<string | null>(null)

  const runSearch = useCallback(
    async (next: SearchFilters) => {
      setLoading(true)
      setFilters(next)
      try {
        const data = await searchInvestigation(CASE_ID, next)
        setResults(data)
        const loaded = [
          ...data.nameCandidates.map((h) => h.entity),
          ...data.primaryMatches,
          ...data.relatedPeople.map((r) => r.entity),
          ...data.linkedRecords,
        ]
        onEntitiesLoaded?.(loaded)
        if (!data.needsDisambiguation && data.primaryMatches.length === 1) {
          onSearchPerformed?.(
            `Person confirmed: ${data.primaryMatches[0].label}`,
            data.primaryMatches[0].id,
          )
        } else if (data.nameCandidates.length > 0) {
          onSearchPerformed?.(
            `Name search "${next.nameQuery}": ${data.nameCandidates.length} candidate(s)`,
            data.nameCandidates[0]?.entity.id ?? CASE_ID,
          )
        }
      } finally {
        setLoading(false)
      }
    },
    [onSearchPerformed, onEntitiesLoaded],
  )

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    void runSearch({ ...draft, faceMatchPersonId: filters.faceMatchPersonId, selectedPersonId: null })
  }

  function handleDemoRun(next: SearchFilters) {
    setDraft(next)
    void runSearch(next)
  }

  function confirmPerson(personId: string) {
    const next = { ...filters, ...draft, selectedPersonId: personId }
    onSelect(personId)
    void runSearch(next)
  }

  async function handleFaceFile(file: File | null) {
    if (!file) return
    setFaceStatus(t.search.faceScanning)
    try {
      const match = await searchByFace(CASE_ID, file)
      const next = { ...draft, faceMatchPersonId: match.personId, selectedPersonId: match.personId }
      setDraft(next)
      setFaceStatus(t.search.faceMatchResult.replace('{confidence}', String(match.confidence)))
      onSelect(match.personId)
      await runSearch(next)
    } catch {
      setFaceStatus(t.search.faceError)
    }
  }

  function severityClass(severity: Entity['severity']) {
    if (severity === 'high') return 'text-risk-high border-risk-high/40 bg-risk-high/10'
    if (severity === 'medium') return 'text-risk-medium border-risk-medium/40 bg-risk-medium/10'
    return 'text-risk-low border-risk-low/40 bg-risk-low/10'
  }

  function matchBadge(type: NameMatchHit['matchType']) {
    if (type === 'typo') return 'border-risk-medium/50 text-risk-medium bg-risk-medium/10'
    if (type === 'alias') return 'border-accent-steel/50 text-accent-steel bg-accent-steel/10'
    return 'border-console-border-strong text-text-muted bg-console-raised'
  }

  function isBridgeLink(reason: string) {
    const r = reason.toLowerCase()
    return r.includes('prepaid') || r.includes('burner') || r.includes('shared') || r.includes('bridge')
  }

  const candidateList: NameMatchHit[] = results
    ? results.needsDisambiguation
      ? results.nameCandidates.filter((h) =>
          results.primaryMatches.some((p) => p.id === h.entity.id),
        )
      : results.nameCandidates
    : []

  const showPickList = results?.needsDisambiguation && candidateList.length > 0

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <header className="border-b border-console-border px-5 py-3">
        <div className="flex items-center gap-3">
          <h1 className="text-base font-semibold text-text-primary">{t.views.search.header}</h1>
          <span className="border border-accent-amber/40 bg-accent-amber/10 px-2 py-0.5 text-[10px] text-accent-amber">
            {narrativeTags.search}
          </span>
        </div>
        <p className="mt-1 text-sm text-text-secondary">{t.views.search.description}</p>
      </header>

      <div className="grid flex-1 grid-cols-1 gap-0 overflow-hidden xl:grid-cols-[340px_1fr]">
        <aside className="overflow-y-auto border-b border-console-border p-4 xl:border-b-0 xl:border-r">
          <DemoScenarioChips onRun={handleDemoRun} disabled={loading} />
          <p className="mb-3 text-xs leading-relaxed text-text-muted">{t.search.typoHint}</p>
          <form onSubmit={handleSubmit} className="space-y-4">
            <label className="block">
              <span className="text-sm font-medium text-text-primary">{t.search.nameLabel}</span>
              <input
                type="search"
                value={draft.nameQuery}
                onChange={(e) =>
                  setDraft((d) => ({ ...d, nameQuery: e.target.value, selectedPersonId: null }))
                }
                placeholder={t.search.namePlaceholder}
                className="mt-1.5 w-full border border-console-border-strong bg-console-bg px-3 py-3 text-base text-text-primary outline-none focus:border-accent-amber"
              />
            </label>

            <label className="block">
              <span className="text-sm font-medium text-text-primary">{t.search.phoneLabel}</span>
              <input
                type="tel"
                inputMode="numeric"
                value={draft.phoneQuery}
                onChange={(e) => setDraft((d) => ({ ...d, phoneQuery: e.target.value }))}
                placeholder={t.search.phonePlaceholder}
                className="mt-1.5 w-full border border-console-border-strong bg-console-bg px-3 py-3 text-base text-text-primary outline-none focus:border-accent-amber"
              />
            </label>

            <label className="block">
              <span className="text-sm font-medium text-text-primary">{t.search.areaLabel}</span>
              <input
                list="vigil-areas"
                value={draft.areaQuery}
                onChange={(e) => setDraft((d) => ({ ...d, areaQuery: e.target.value }))}
                placeholder={t.search.areaPlaceholder}
                className="mt-1.5 w-full border border-console-border-strong bg-console-bg px-3 py-3 text-base text-text-primary outline-none focus:border-accent-amber"
              />
              <datalist id="vigil-areas">
                {areas.map((a) => (
                  <option key={a} value={a} />
                ))}
              </datalist>
            </label>

            <label className="block">
              <span className="text-sm font-medium text-text-primary">{t.search.roleLabel}</span>
              <select
                value={draft.roleFilter}
                onChange={(e) => setDraft((d) => ({ ...d, roleFilter: e.target.value as RoleFilter }))}
                className="mt-1.5 w-full border border-console-border-strong bg-console-bg px-3 py-3 text-sm text-text-primary outline-none focus:border-accent-amber"
              >
                <option value="all">{t.search.roleAll}</option>
                <option value="suspect">{t.role.suspect}</option>
                <option value="associate">{t.role.associate}</option>
                <option value="facilitator">{t.role.facilitator}</option>
                <option value="witness">{t.role.witness}</option>
              </select>
            </label>

            <div className="border border-console-border bg-console-bg p-3">
              <p className="text-sm font-medium text-text-primary">{t.search.faceLabel}</p>
              <p className="mt-1 text-xs text-text-muted">{t.search.faceHint}</p>
              <input
                type="file"
                accept="image/*"
                className="mt-2 w-full text-xs text-text-secondary file:mr-2 file:border file:border-accent-steel/50 file:bg-console-raised file:px-2 file:py-1 file:text-accent-steel"
                onChange={(e) => void handleFaceFile(e.target.files?.[0] ?? null)}
              />
              {faceStatus && <p className="mt-2 text-xs text-accent-amber">{faceStatus}</p>}
            </div>

            <div className="flex gap-2">
              <button
                type="submit"
                disabled={loading}
                className="min-h-[44px] flex-1 border border-accent-amber/60 bg-accent-amber/15 text-sm font-semibold text-accent-amber hover:bg-accent-amber/25 disabled:opacity-50"
              >
                {loading ? t.search.searching : t.search.runSearch}
              </button>
              <button
                type="button"
                onClick={() => {
                  setDraft(emptyFilters)
                  setFilters(emptyFilters)
                  setResults(null)
                  setFaceStatus(null)
                }}
                className="min-h-[44px] border border-console-border-strong px-3 text-sm text-text-secondary hover:bg-console-raised"
              >
                {t.search.clear}
              </button>
            </div>
          </form>
        </aside>

        <section className="flex flex-col overflow-hidden">
          {!results ? (
            <div className="flex flex-1 flex-col items-center justify-center px-6 text-center">
              <p className="text-base text-text-secondary">{t.search.emptyTitle}</p>
              <p className="mt-2 max-w-md text-sm text-text-muted">{t.search.emptyHint}</p>
              <p className="mt-4 text-xs text-accent-steel">{t.search.tryExample}</p>
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto p-4">
              {showPickList && (
                <div className="mb-6 border border-accent-amber/40 bg-accent-amber/5 p-4">
                  <h2 className="text-sm font-semibold text-accent-amber">{t.search.multipleTitle}</h2>
                  <p className="mt-1 text-sm text-text-secondary">{t.search.multipleHint}</p>
                </div>
              )}

              {showPickList &&
                candidateList.map((hit) => {
                  const entity = hit.entity
                  const phone = getPersonPhoneDisplay(entity.id)
                  return (
                    <div
                      key={entity.id}
                      className={`mb-3 border px-4 py-3 ${
                        filters.selectedPersonId === entity.id
                          ? 'border-accent-amber bg-accent-amber/10'
                          : 'border-console-border bg-console-surface'
                      }`}
                    >
                      <div className="flex flex-wrap items-start justify-between gap-2">
                        <div>
                          <p className="text-base font-semibold text-text-primary">{entity.label}</p>
                          {entity.subtitle && (
                            <p className="mt-0.5 text-xs text-text-secondary">{entity.subtitle}</p>
                          )}
                          <p className="mt-2 text-sm text-text-primary">
                            {entity.metadata.city ?? '—'}
                            {phone ? ` · ${phone}` : ''}
                            {entity.metadata.dob ? ` · DOB ${entity.metadata.dob}` : ''}
                          </p>
                          {entity.aliases && entity.aliases.length > 0 && (
                            <p className="mt-1 text-xs text-text-muted">
                              {t.search.alsoKnownAs}: {entity.aliases.join(', ')}
                            </p>
                          )}
                          <span
                            className={`mt-2 inline-block border px-2 py-0.5 text-[10px] ${matchBadge(hit.matchType)}`}
                          >
                            {matchTypeLabel(hit.matchType)} · {hit.confidence}%
                          </span>
                        </div>
                        <span className={`shrink-0 border px-2 py-0.5 text-[10px] ${severityClass(entity.severity)}`}>
                          {entity.role ? t.role[entity.role] : t.entityType.person}
                        </span>
                      </div>
                      <button
                        type="button"
                        onClick={() => confirmPerson(entity.id)}
                        className="mt-3 min-h-[40px] w-full border border-accent-amber/60 bg-accent-amber/15 text-sm font-medium text-accent-amber hover:bg-accent-amber/25"
                      >
                        {t.search.confirmPerson}
                      </button>
                    </div>
                  )
                })}

              {!showPickList &&
                results.primaryMatches.length === 1 &&
                !filters.selectedPersonId &&
                results.nameCandidates.length > 1 && (
                  <p className="mb-4 text-sm text-accent-steel">{t.search.narrowedToOne}</p>
                )}

              {!showPickList && results.primaryMatches.length === 0 && results.nameCandidates.length === 0 && (
                <p className="text-sm text-text-muted">{t.search.noResults}</p>
              )}

              {!results.needsDisambiguation && results.relatedPeople.length > 0 && (
                <div className="mb-6">
                  <h2 className="text-sm font-semibold text-text-primary">{t.search.relatedPeople}</h2>
                  <p className="mt-1 text-xs text-text-muted">{t.search.relatedHint}</p>
                  <ul className="mt-3 space-y-2">
                    {results.relatedPeople.map(({ entity, hops, connectionReason }) => (
                      <li key={entity.id}>
                        <button
                          type="button"
                          onClick={() => onSelect(entity.id)}
                          className={`w-full border px-4 py-3 text-left transition-colors ${
                            selectedId === entity.id
                              ? 'border-accent-amber bg-accent-amber/10'
                              : isBridgeLink(connectionReason)
                                ? 'border-risk-high/40 bg-risk-high/5 hover:border-risk-high/60'
                                : 'border-console-border hover:border-accent-steel/40'
                          }`}
                        >
                          <div className="flex flex-wrap items-center gap-2">
                            <p className="text-sm font-medium text-text-primary">{entity.label}</p>
                            {isBridgeLink(connectionReason) && (
                              <span className="border border-risk-high/50 bg-risk-high/10 px-1.5 py-0.5 text-[10px] text-risk-high">
                                {t.search.bridgeLink}
                              </span>
                            )}
                          </div>
                          <p className="mt-1 text-xs text-text-secondary">
                            {t.search.hopsAway.replace('{n}', String(hops))} — {connectionReason}
                          </p>
                          {isBridgeLink(connectionReason) && (
                            <p className="mt-1 text-[10px] text-text-muted">{t.search.bridgeHint}</p>
                          )}
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {!results.needsDisambiguation && results.linkedRecords.length > 0 && (
                <div>
                  <h2 className="text-sm font-semibold text-text-primary">{t.search.linkedRecords}</h2>
                  <div className="mt-3 flex flex-wrap gap-2">
                    {results.linkedRecords.map((entity) => (
                      <button
                        key={entity.id}
                        type="button"
                        onClick={() => onSelect(entity.id)}
                        className="border border-console-border-strong bg-console-raised px-3 py-2 text-left text-xs hover:border-accent-steel"
                      >
                        <span className="text-accent-steel">{t.entityType[entity.type]}</span>
                        <p className="mt-0.5 font-medium text-text-primary">{entity.label}</p>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
