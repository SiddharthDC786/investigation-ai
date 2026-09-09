import { useEffect, useState } from 'react'
import { fetchHealth, isApiConfigured } from '../api/client'
import { useLanguage } from '../i18n/LanguageContext'

type HealthState = 'demo' | 'checking' | 'live' | 'down' | 'degraded'

export function ConnectionStatusBadge() {
  const { t } = useLanguage()
  const [state, setState] = useState<HealthState>(() =>
    isApiConfigured() ? 'checking' : 'demo',
  )
  const [neo4j, setNeo4j] = useState<boolean | null>(null)
  const [nlpEngine, setNlpEngine] = useState<string | null>(null)

  useEffect(() => {
    if (!isApiConfigured()) {
      setState('demo')
      return
    }

    let cancelled = false
    const poll = async () => {
      const health = await fetchHealth()
      if (cancelled) return
      if (!health) {
        setState('down')
        setNeo4j(null)
        setNlpEngine(null)
        return
      }
      setNeo4j(health.neo4j ?? false)
      setNlpEngine(health.nlp?.engine ?? null)
      if (health.status === 'degraded' || health.postgres === false) {
        setState('degraded')
        return
      }
      setState('live')
    }

    void poll()
    const id = window.setInterval(() => void poll(), 30_000)
    return () => {
      cancelled = true
      window.clearInterval(id)
    }
  }, [])

  const styles: Record<HealthState, string> = {
    live: 'border-risk-low/50 bg-risk-low/10',
    demo: 'border-accent-amber/40 bg-accent-amber/10',
    checking: 'border-console-border-strong bg-console-raised',
    down: 'border-risk-high/50 bg-risk-high/10',
    degraded: 'border-risk-medium/50 bg-risk-medium/10',
  }

  const dotStyles: Record<HealthState, string> = {
    live: 'bg-risk-low',
    demo: 'bg-accent-amber',
    checking: 'bg-text-muted animate-pulse',
    down: 'bg-risk-high',
    degraded: 'bg-risk-medium',
  }

  const labels: Record<HealthState, string> = {
    live: t.connection.live,
    demo: t.connection.demo,
    checking: t.connection.checking,
    down: t.connection.down,
    degraded: t.connection.degraded,
  }

  const stackHint =
    state === 'live'
      ? [
          neo4j ? t.connection.neo4jOn : null,
          nlpEngine ? `${t.connection.nlp}: ${nlpEngine}` : null,
        ]
          .filter(Boolean)
          .join(' · ') || t.connection.liveHint
      : state === 'demo'
        ? t.connection.demoHint
        : state === 'down' || state === 'degraded'
          ? t.connection.downHint
          : t.connection.checking

  return (
    <div className={`border px-2.5 py-1 text-center ${styles[state]}`} title={stackHint}>
      <p className="flex items-center justify-center gap-1.5 text-[10px] font-semibold uppercase tracking-wide">
        <span className={`inline-block h-1.5 w-1.5 rounded-full ${dotStyles[state]}`} aria-hidden />
        {labels[state]}
      </p>
      {state === 'live' && stackHint && (
        <p className="mt-0.5 text-[9px] normal-case tracking-normal text-text-muted">{stackHint}</p>
      )}
    </div>
  )
}
