import { useEffect, useMemo, useState } from 'react'
import { getCaseTimeline } from '../api/timeline'
import { formatApiError } from '../api/client'
import { useCase } from '../context/CaseContext'
import { useLanguage } from '../i18n/LanguageContext'
import type { Entity, TimelineEvent } from '../types'

interface TimelineViewProps {
  selectedId: string | null
  highlightedIds: Set<string>
  entityLookup: Record<string, Entity>
  timelineRefreshKey?: number
  onSelectEntity: (id: string) => void
  onHoverEntities: (ids: string[]) => void
}

const entityDotColor = (type: Entity['type']) => {
  const map = { person: '#5b8bb0', phone: '#d9a441', account: '#7a9e8e', address: '#8b7aa8' }
  return map[type]
}

const inferType = (id: string): Entity['type'] => {
  if (id.startsWith('PH')) return 'phone'
  if (id.startsWith('AC')) return 'account'
  if (id.startsWith('LOC')) return 'address'
  return 'person'
}

function eventMatchesPerson(
  event: TimelineEvent,
  personId: string,
  lookup: Record<string, Entity>,
): boolean {
  if (event.entityIds.includes(personId)) return true
  return event.entityIds.some((id) => lookup[id]?.metadata?.person_id === personId)
}

export function TimelineView({
  selectedId,
  highlightedIds,
  entityLookup,
  timelineRefreshKey = 0,
  onSelectEntity,
  onHoverEntities,
}: TimelineViewProps) {
  const { t } = useLanguage()
  const { caseId } = useCase()
  const [events, setEvents] = useState<TimelineEvent[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    getCaseTimeline(caseId)
      .then((res) => {
        if (!cancelled) setEvents(res.events)
      })
      .catch((err) => {
        if (!cancelled) {
          setEvents([])
          setError(formatApiError(err, t.timeline.apiError))
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [caseId, t.timeline.apiError, timelineRefreshKey])

  const selectedPerson = selectedId?.startsWith('P') ? entityLookup[selectedId] : null
  const personFilterId = selectedPerson ? selectedId : null

  const visibleEvents = useMemo(() => {
    if (!personFilterId) return []
    return events.filter((event) => eventMatchesPerson(event, personFilterId, entityLookup))
  }, [events, personFilterId, entityLookup])

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <header className="border-b border-console-border px-5 py-3">
        <div className="flex items-center gap-3">
          <h1 className="text-base font-semibold text-text-primary">{t.views.timeline.header}</h1>
        </div>
        <p className="mt-1 text-sm text-text-secondary">{t.views.timeline.description}</p>
        {selectedPerson && (
          <p className="mt-2 text-xs text-accent-amber">
            {t.timeline.filteredFor}: <span className="font-medium">{selectedPerson.label}</span>
          </p>
        )}
      </header>

      <div className="flex-1 overflow-y-auto px-5 py-4">
        {loading && (
          <p className="text-sm text-text-muted">{t.views.timeline.description}…</p>
        )}
        {!loading && error && (
          <p className="border border-risk-high/40 bg-risk-high/10 px-3 py-2 text-sm text-risk-high">{error}</p>
        )}
        {!loading && !error && !personFilterId && (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <p className="max-w-md text-sm text-text-muted">{t.timeline.selectPersonFirst}</p>
          </div>
        )}
        {!loading && !error && personFilterId && visibleEvents.length === 0 && (
          <p className="text-sm text-text-muted">{t.timeline.noEventsForPerson}</p>
        )}
        <div className="relative ml-4 border-l border-console-border-strong pl-8">
          {visibleEvents.map((event, idx) => {
            const active = event.entityIds.some((id) => id === selectedId || highlightedIds.has(id))
            return (
              <article
                key={event.id}
                className={`relative mb-6 pb-2 ${active ? 'opacity-100' : 'opacity-90'}`}
                onMouseEnter={() => onHoverEntities(event.entityIds)}
                onMouseLeave={() => onHoverEntities([])}
              >
                <span
                  className={`absolute -left-[37px] top-1 flex h-3 w-3 items-center justify-center border ${
                    active ? 'border-accent-amber bg-accent-amber/20' : 'border-console-border-strong bg-console-raised'
                  }`}
                />
                <p className="text-xs text-accent-amber">{event.timestamp}</p>
                <h2 className="mt-1 text-base font-semibold text-text-primary">{event.title}</h2>
                <p className="mt-1 text-sm leading-relaxed text-text-secondary">{event.description}</p>
                <p className="mt-1 text-[10px] text-text-muted">
                  {t.timeline.source}: {event.source}
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {event.entityIds.map((id) => {
                    const linked = entityLookup[id]
                    return (
                      <button
                        key={id}
                        type="button"
                        onClick={() => onSelectEntity(id)}
                        className={`min-h-[36px] border px-3 py-1.5 text-sm transition-colors ${
                          selectedId === id
                            ? 'border-accent-amber text-accent-amber'
                            : 'border-console-border text-text-primary hover:border-accent-steel'
                        }`}
                      >
                        {linked?.label ?? id}
                      </button>
                    )
                  })}
                </div>
                {idx < visibleEvents.length - 1 && (
                  <div className="mt-4 flex gap-1">
                    {event.entityIds.slice(0, 3).map((id) => (
                      <span
                        key={id}
                        className="h-1 w-6"
                        style={{
                          backgroundColor: entityDotColor(linkedType(id, entityLookup)),
                        }}
                      />
                    ))}
                  </div>
                )}
              </article>
            )
          })}
        </div>
      </div>
    </div>
  )
}

function linkedType(id: string, lookup: Record<string, Entity>): Entity['type'] {
  return lookup[id]?.type ?? inferType(id)
}
