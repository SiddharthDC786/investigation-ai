import { useState, type FormEvent } from 'react'
import { useAuth } from '../auth/AuthContext'
import { useLanguage } from '../i18n/LanguageContext'
import { LanguageSelector } from './LanguageSelector'
import { SihBadge } from './SihBadge'

export function LoginPage() {
  const { login } = useAuth()
  const { t } = useLanguage()
  const [badgeId, setBadgeId] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [showHelp, setShowHelp] = useState(false)

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    if (!login(badgeId, password)) {
      setError(t.login.error)
      return
    }
  }

  return (
    <div className="relative flex min-h-full items-center justify-center bg-console-bg px-4 py-8">
      <div className="pointer-events-none absolute inset-0 opacity-[0.03]">
        <p className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rotate-[-18deg] text-6xl font-bold tracking-[0.3em] text-text-primary">
          RESTRICTED
        </p>
      </div>

      <div className="absolute right-4 top-4 sm:right-6 sm:top-6">
        <LanguageSelector />
      </div>

      <div className="w-full max-w-md border border-console-border bg-console-surface p-6 sm:p-8">
        <div className="mb-6 border-b border-console-border pb-4">
          <p className="text-xs font-semibold text-risk-high">{t.login.restricted}</p>
          <p className="mt-2 text-[11px] font-medium text-accent-steel">{t.sih.loginTagline}</p>
          <h1 className="mt-2 text-2xl font-semibold text-text-primary">{t.login.title}</h1>
          <p className="mt-1 text-sm text-text-secondary">{t.login.subtitle}</p>
          <div className="mt-3">
            <SihBadge />
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4" autoComplete="off">
          <label className="block">
            <span className="text-sm font-medium text-text-secondary">{t.login.badgeId}</span>
            <input
              type="text"
              value={badgeId}
              onChange={(e) => setBadgeId(e.target.value.toUpperCase())}
              className="mt-1.5 w-full border border-console-border-strong bg-console-bg px-3 py-3 text-base text-text-primary outline-none focus:border-accent-amber"
              placeholder="INV-2847"
              required
            />
          </label>
          <label className="block">
            <span className="text-sm font-medium text-text-secondary">{t.login.password}</span>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1.5 w-full border border-console-border-strong bg-console-bg px-3 py-3 text-base text-text-primary outline-none focus:border-accent-amber"
              placeholder={t.login.passwordPlaceholder}
              required
            />
          </label>
          {error && (
            <p className="border border-risk-high/40 bg-risk-high/10 px-3 py-2.5 text-sm text-risk-high">
              {error}
            </p>
          )}
          <button
            type="submit"
            className="w-full border border-accent-amber/60 bg-accent-amber/15 py-3.5 text-base font-semibold text-accent-amber hover:bg-accent-amber/25"
          >
            {t.login.signIn}
          </button>
        </form>

        <button
          type="button"
          onClick={() => setShowHelp((v) => !v)}
          className="mt-4 text-sm text-accent-steel hover:underline"
        >
          {showHelp ? t.login.hideDemo : t.login.showDemo}
        </button>
        {showHelp && (
          <div className="mt-2 space-y-2 border border-console-border bg-console-bg p-3 text-sm text-text-secondary">
            <p>
              <span className="font-mono-data text-accent-amber">INV-2847</span> / vigil2026 —{' '}
              {t.login.demoInvestigator}
            </p>
            <p>
              <span className="font-mono-data text-accent-amber">SUP-1001</span> / admin2026 —{' '}
              {t.login.demoSupervisor}
            </p>
          </div>
        )}

        <ul className="mt-6 space-y-1.5 border-t border-console-border pt-4 text-xs text-text-muted">
          <li>• {t.login.ruleIdle}</li>
          <li>• {t.login.ruleAudit}</li>
          <li>• {t.login.ruleShare}</li>
        </ul>
      </div>
    </div>
  )
}
