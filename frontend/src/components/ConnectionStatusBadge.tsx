import { useEffect, useState } from 'react'
import { fetchHealth, isApiConfigured } from '../api/client'
import { useLanguage } from '../i18n/LanguageContext'

type HealthState = 'demo' | 'checking' | 'live' | 'down' | 'degraded'

export function ConnectionStatusBadge() {
  const { t } = useLanguage()
  const [state, setState] = useState<HealthState>(() =>
    isApiConfigured() ? 'checking' : 'demo',
  )

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
        return
      }
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

  const hints: Record<HealthState, string> = {
    live: t.connection.liveHint,
    demo: t.connection.demoHint,
    checking: t.connection.checking,
    down: t.connection.downHint,
    degraded: t.connection.downHint,
  }

  return (
    <div
      className={`border px-2.5 py-1 text-center ${styles[state]}`}
      title={hints[state]}
    >
      <p className="flex items-center justify-center gap-1.5 text-[10px] font-semibold uppercase tracking-wide">
        <span className={`inline-block h-1.5 w-1.5 rounded-full ${dotStyles[state]}`} aria-hidden />
        {labels[state]}
      </p>
    </div>
  )
}
