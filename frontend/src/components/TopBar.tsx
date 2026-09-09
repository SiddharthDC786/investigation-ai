import { useEffect, useState } from 'react'
import { useAuth } from '../auth/AuthContext'
import { getCase } from '../api/case'
import { getCaseSummary } from '../api/summary'
import { CASE_DISPLAY_REF } from '../data/mockCase'
import { displayCaseTitle } from '../lib/displayCase'
import { useCase } from '../context/CaseContext'
import { useLanguage } from '../i18n/LanguageContext'
import { usePresentationMode } from '../i18n/PresentationModeContext'
import { ConnectionStatusBadge } from './ConnectionStatusBadge'
import { LanguageSelector } from './LanguageSelector'
import { SihBadge } from './SihBadge'

export function TopBar() {
  const { user, minutesLeft, logout } = useAuth()
  const { t } = useLanguage()
  const { enabled: presentationMode, toggle: togglePresentation } = usePresentationMode()
  const { caseId, cases, setCaseId, loading: casesLoading } = useCase()
  const [caseTitle, setCaseTitle] = useState('Loading case…')
  const [briefing, setBriefing] = useState<string | null>(null)

  useEffect(() => {
    if (!caseId) return
    void getCase(caseId)
      .then((c) => setCaseTitle(displayCaseTitle(c.title)))
      .catch(() => setCaseTitle('Active investigation'))
    void getCaseSummary(caseId)
      .then((s) => {
        if (!s?.narrative) return
        const line = displayCaseTitle(s.narrative)
        if (!/synthetic|CASE0001/i.test(line)) setBriefing(line)
      })
  }, [caseId])

  return (
    <header className="flex min-h-12 shrink-0 flex-wrap items-center justify-between gap-2 border-b border-console-border bg-console-surface px-4 py-2">
      <div className="flex min-w-0 items-center gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center border border-accent-amber/50 bg-console-bg">
          <span className="text-sm font-bold text-accent-amber">V</span>
        </div>
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-base font-semibold text-text-primary">Vigil</span>
            <SihBadge compact />
            <span className="text-xs text-accent-steel">{CASE_DISPLAY_REF}</span>
            {cases.length > 1 && (
              <select
                value={caseId}
                disabled={casesLoading}
                onChange={(e) => setCaseId(e.target.value)}
                className="border border-console-border-strong bg-console-bg px-2 py-1 text-xs text-text-primary"
                aria-label="Select investigation case"
              >
                {cases.map((c) => (
                  <option key={c.case_id} value={c.case_id}>
                    {c.case_id} — {c.title}
                  </option>
                ))}
              </select>
            )}
          </div>
          <p className="truncate text-sm text-text-secondary">{caseTitle}</p>
          {briefing && (
            <p className="mt-1 line-clamp-1 max-w-xl text-xs leading-relaxed text-text-muted">{briefing}</p>
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3 text-sm">
        <ConnectionStatusBadge />
        <LanguageSelector compact />
        <button
          type="button"
          onClick={togglePresentation}
          title={t.presentation.hint}
          className={`min-h-[40px] border px-3 py-2 text-xs ${
            presentationMode
              ? 'border-accent-amber/60 bg-accent-amber/15 text-accent-amber'
              : 'border-console-border-strong text-text-secondary hover:border-accent-steel/40'
          }`}
        >
          {presentationMode ? t.presentation.on : t.presentation.off}
        </button>
        <div className="hidden text-right sm:block">
          <p className="font-medium text-text-primary">{user?.name}</p>
          <p className="text-xs text-text-muted">
            {user?.role === 'supervisor' ? t.topBar.supervisor : t.topBar.investigator} · {user?.station}
          </p>
        </div>
        <div className="border border-console-border-strong px-2.5 py-1 text-center">
          <p className="text-[10px] text-text-muted">{t.topBar.timeLeft}</p>
          <p className="text-sm text-accent-amber">
            {minutesLeft} {t.topBar.minutesUnit}
          </p>
        </div>
        <button
          type="button"
          onClick={logout}
          className="min-h-[40px] border border-console-border-strong px-4 py-2 text-sm text-text-secondary hover:border-risk-high/50 hover:text-risk-high"
        >
          {t.topBar.logout}
        </button>
      </div>
    </header>
  )
}
