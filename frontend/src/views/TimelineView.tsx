import { timelineEvents, narrativeTags, entityMap } from '../data/mockCase'
import { useLanguage } from '../i18n/LanguageContext'
import type { Entity } from '../types'

interface TimelineViewProps {
  selectedId: string | null
  highlightedIds: Set<string>
  onSelectEntity: (id: string) => void
  onHoverEntities: (ids: string[]) => void
}

const entityDotColor = (type: Entity['type']) => {
  const map = { person: '#5b8bb0', phone: '#d9a441', account: '#7a9e8e', address: '#8b7aa8' }
  return map[type]
}

export function TimelineView({
  selectedId,
  highlightedIds,
  onSelectEntity,
  onHoverEntities,
}: TimelineViewProps) {
  const { t } = useLanguage()

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <header className="border-b border-console-border px-5 py-3">
        <div className="flex items-center gap-3">
          <h1 className="text-base font-semibold text-text-primary">{t.views.timeline.header}</h1>
          <span className="border border-accent-steel/30 bg-accent-steel/10 px-2 py-0.5 text-[10px] text-accent-steel">
            {narrativeTags.timeline}
          </span>
        </div>
        <p className="mt-1 text-sm text-text-secondary">{t.views.timeline.description}</p>
      </header>

      <div className="flex-1 overflow-y-auto px-5 py-4">
        <div className="relative ml-4 border-l border-console-border-strong pl-8">
          {timelineEvents.map((event, idx) => {
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
                <p className="mt-2 text-xs text-text-muted">
                  {t.timeline.source}: {event.source}
                </p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {event.entityIds.map((id) => {
                    const linked = entityMap[id]
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
                {idx < timelineEvents.length - 1 && (
                  <div className="mt-4 flex gap-1">
                    {event.entityIds.slice(0, 3).map((id) => (
                      <span
                        key={id}
                        className="h-1 w-6"
                        style={{
                          backgroundColor: entityDotColor(
                            id.startsWith('P')
                              ? 'person'
                              : id.startsWith('PH')
                                ? 'phone'
                                : id.startsWith('AC')
                                  ? 'account'
                                  : 'address',
                          ),
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
