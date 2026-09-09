import { useCallback, useEffect, useMemo, useState } from 'react'
import { useAuth } from './auth/AuthContext'
import type { AuthUser } from './auth/types'
import { CaseStatsStrip } from './components/CaseStatsStrip'
import { InvestigationGuide } from './components/InvestigationGuide'
import { InspectorPanel } from './components/InspectorPanel'
import { LoginPage } from './components/LoginPage'
import { NavRail } from './components/NavRail'
import { SecurityBanner } from './components/SecurityBanner'
import { TopBar } from './components/TopBar'
import { CASE_ID, entityMap, osintLookups, seedAuditLog } from './data/mockCase'
import { getOsintAuditLog } from './api/osint'
import { isApiConfigured } from './api/client'
import { useLanguage } from './i18n/LanguageContext'
import type { OsintEnrichResponse } from './api/osint'
import type { AuditEntry, Entity, ReviewDecision, ViewId } from './types'
import { SearchView } from './views/SearchView'
import { AuditTrailView } from './views/AuditTrailView'
import { NetworkGraphView } from './views/NetworkGraphView'
import { OsintView } from './views/OsintView'
import { RiskScoringView } from './views/RiskScoringView'
import { TimelineView } from './views/TimelineView'

function nowStamp() {
  return new Date().toISOString().replace('T', ' ').slice(0, 19)
}

function VigilDashboard({ user }: { user: AuthUser }) {
  const { logout } = useAuth()
  const { t } = useLanguage()
  const [view, setView] = useState<ViewId>('search')
  const [guideOpen, setGuideOpen] = useState(false)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [highlightedIds, setHighlightedIds] = useState<Set<string>>(new Set())
  const [auditLog, setAuditLog] = useState<AuditEntry[]>(() =>
    isApiConfigured() ? [] : [...seedAuditLog],
  )
  const [chainStatus, setChainStatus] = useState<string>('unknown')
  const [reviews, setReviews] = useState<Record<string, ReviewDecision>>({})
  const [liveEntities, setLiveEntities] = useState<Record<string, Entity>>({})
  const [timelineRefreshKey, setTimelineRefreshKey] = useState(0)

  const mergeLiveEntities = useCallback((items: Entity[]) => {
    if (items.length === 0) return
    setLiveEntities((prev) => {
      const next = { ...prev }
      for (const e of items) next[e.id] = e
      return next
    })
  }, [])

  const operator = user.name

  useEffect(() => {
    if (!isApiConfigured()) return
    let cancelled = false
    void getOsintAuditLog(CASE_ID)
      .then((res) => {
        if (cancelled) return
        setChainStatus(res.chain_status)
        setAuditLog((prev) => {
          const backendIds = new Set(res.entries.map((e) => e.id))
          const sessionOnly = prev.filter((p) => !backendIds.has(p.id))
          return [...sessionOnly, ...res.entries]
        })
      })
      .catch(() => {
        if (!cancelled) setChainStatus('offline')
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    setAuditLog((prev) => [
      {
        id: `AUD-LOGIN-${Date.now()}`,
        timestamp: nowStamp(),
        action: `Secure login: ${user.badgeId}`,
        entityId: CASE_ID,
        source: 'Vigil auth',
        operator,
        lawfulBasis: 'Authorised session — investigation workstation',
      },
      ...prev,
    ])
  }, [user.badgeId, operator])

  const appendAudit = useCallback(
    (entry: Omit<AuditEntry, 'id' | 'timestamp' | 'operator'>) => {
      setAuditLog((prev) => [
        {
          ...entry,
          id: `AUD-${Date.now()}`,
          timestamp: nowStamp(),
          operator,
        },
        ...prev,
      ])
    },
    [operator],
  )

  const handleOsintLookup = useCallback(
    (lookupId: string, entityId: string, result?: OsintEnrichResponse) => {
      const lookup = osintLookups.find((l) => l.id === lookupId)
      if (!lookup) return
      if (result) {
        return
      }
      appendAudit({
        action: `OSINT lookup: ${lookup.label}`,
        entityId,
        source: `lawful_api://${lookupId}`,
        lawfulBasis: 'Public records / licensed directory — logged enrichment',
      })
    },
    [appendAudit],
  )

  const handleReview = useCallback(
    (decision: ReviewDecision) => {
      if (!selectedId) return
      setReviews((prev) => ({ ...prev, [selectedId]: decision }))
      if (decision) {
        appendAudit({
          action: `Officer review: ${decision.replace('_', ' ')} on AI suggestion`,
          entityId: selectedId,
          source: 'Vigil review queue',
          lawfulBasis: 'Human review of AI recommendation',
        })
      }
    },
    [selectedId, appendAudit],
  )

  const handleLogout = () => {
    appendAudit({
      action: 'Secure logout',
      entityId: CASE_ID,
      source: 'Vigil auth',
      lawfulBasis: 'Session terminated by user',
    })
    logout()
  }

  const selectedEntity = selectedId
    ? liveEntities[selectedId] ?? entityMap[selectedId] ?? null
    : null
  const reviewDecision = selectedId ? reviews[selectedId] ?? null : null

  const handleExportAudit = useCallback(() => {
    appendAudit({
      action: 'Supervisor exported disclosure bundle (JSON)',
      entityId: CASE_ID,
      source: 'Vigil audit export',
      lawfulBasis: 'Court disclosure / supervisory review',
    })
  }, [appendAudit])

  const handleIngested = useCallback(
    (summary: string) => {
      setTimelineRefreshKey((k) => k + 1)
      appendAudit({
        action: summary,
        entityId: selectedId ?? CASE_ID,
        source: 'Vigil FIR ingest',
        lawfulBasis: 'Officer-uploaded FIR document — NLP extraction logged',
      })
    },
    [appendAudit, selectedId],
  )

  const handleSearchPerformed = useCallback(
    (summary: string, entityId: string) => {
      appendAudit({
        action: summary,
        entityId,
        source: 'Vigil person search',
        lawfulBasis: 'Investigator-led query — logged for disclosure',
      })
    },
    [appendAudit],
  )

  const mainContent = useMemo(() => {
    switch (view) {
      case 'search':
        return (
          <SearchView
            selectedId={selectedId}
            onSelect={setSelectedId}
            onSearchPerformed={handleSearchPerformed}
            onEntitiesLoaded={mergeLiveEntities}
          />
        )
      case 'network':
        return (
          <NetworkGraphView
            selectedId={selectedId}
            highlightedIds={highlightedIds}
            onSelect={setSelectedId}
            onEntitiesLoaded={mergeLiveEntities}
          />
        )
      case 'timeline':
        return (
          <TimelineView
            selectedId={selectedId}
            highlightedIds={highlightedIds}
            entityLookup={{ ...entityMap, ...liveEntities }}
            timelineRefreshKey={timelineRefreshKey}
            onSelectEntity={setSelectedId}
            onHoverEntities={(ids) => setHighlightedIds(new Set(ids))}
          />
        )
      case 'risk':
        return <RiskScoringView selectedId={selectedId} onSelect={setSelectedId} />
      case 'osint':
        return (
          <OsintView
            selectedId={selectedId}
            entityLookup={{ ...entityMap, ...liveEntities }}
            onRunLookup={handleOsintLookup}
            recentLogs={auditLog}
            onAuditRefresh={(entries, status) => {
              if (status) setChainStatus(status)
              setAuditLog((prev) => {
                const ids = new Set(entries.map((e) => e.id))
                return [...entries, ...prev.filter((p) => !ids.has(p.id))]
              })
            }}
          />
        )
      case 'audit':
        return (
          <AuditTrailView
            logs={auditLog}
            entityLookup={{ ...entityMap, ...liveEntities }}
            chainStatus={chainStatus}
            canExport={user.role === 'supervisor'}
            exportedBy={`${user.badgeId} · ${user.name}`}
            onExported={handleExportAudit}
          />
        )
      default:
        return null
    }
  }, [view, selectedId, highlightedIds, auditLog, chainStatus, timelineRefreshKey, handleOsintLookup, handleSearchPerformed, handleExportAudit, mergeLiveEntities, user.role, user.badgeId, user.name])

  return (
    <div className="flex h-full flex-col bg-console-bg">
      <SecurityBanner />
      <TopBar />
      <CaseStatsStrip />
      <div className="flex min-h-0 flex-1">
        <NavRail active={view} onChange={setView} />
        <div className="flex min-w-0 flex-1 flex-col">
          <InvestigationGuide
            activeView={view}
            onNavigate={setView}
            collapsed={!guideOpen}
            onToggle={() => setGuideOpen((v) => !v)}
          />
          <main className="min-h-0 flex-1">{mainContent}</main>
        </div>
        <InspectorPanel
          entity={selectedEntity}
          entityLookup={{ ...entityMap, ...liveEntities }}
          caseId={CASE_ID}
          reviewDecision={reviewDecision}
          onReview={handleReview}
          onIngested={handleIngested}
        />
      </div>
      <footer className="flex shrink-0 flex-wrap items-center justify-between gap-2 border-t border-console-border bg-console-surface px-4 py-2 text-xs text-text-muted">
        <span>
          {user.badgeId} · {user.name} · {t.footer.actionsSaved}
        </span>
        <button type="button" onClick={handleLogout} className="min-h-[36px] text-accent-steel hover:text-accent-amber">
          {t.footer.endSession}
        </button>
      </footer>
    </div>
  )
}

export default function App() {
  const { user } = useAuth()

  if (!user) {
    return <LoginPage />
  }

  return <VigilDashboard user={user} />
}
