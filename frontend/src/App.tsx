import { useCallback, useEffect, useMemo, useState } from 'react'
import { useAuth } from './auth/AuthContext'
import type { AuthUser } from './auth/types'
import { listReviews, saveReview } from './api/reviews'
import { CaseStatsStrip } from './components/CaseStatsStrip'
import { InvestigationGuide } from './components/InvestigationGuide'
import { InspectorPanel } from './components/InspectorPanel'
import { LoginPage } from './components/LoginPage'
import { NavRail } from './components/NavRail'
import { SecurityBanner } from './components/SecurityBanner'
import { TopBar } from './components/TopBar'
import { entityMap, seedAuditLog } from './data/mockCase'
import { getOsintAuditLog } from './api/osint'
import { isApiConfigured } from './api/client'
import { CaseProvider, useCase } from './context/CaseContext'
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
  const { caseId, refreshKey, bumpRefresh } = useCase()
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
    if (!isApiConfigured() || !caseId) return
    let cancelled = false
    void getOsintAuditLog(caseId)
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
    void listReviews(caseId)
      .then((rows) => {
        if (cancelled) return
        const map: Record<string, ReviewDecision> = {}
        for (const r of rows) map[r.entity_id] = r.decision
        setReviews(map)
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [caseId])

  useEffect(() => {
    setAuditLog((prev) => [
      {
        id: `AUD-LOGIN-${Date.now()}`,
        timestamp: nowStamp(),
        action: `Secure login: ${user.badgeId}`,
        entityId: caseId,
        source: 'Vigil auth',
        operator,
        lawfulBasis: 'Authorised session — investigation workstation',
      },
      ...prev,
    ])
  }, [user.badgeId, operator, caseId])

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
    (_lookupId: string, _entityId: string, result?: OsintEnrichResponse) => {
      if (result) bumpRefresh()
    },
    [bumpRefresh],
  )

  const handleReview = useCallback(
    (decision: ReviewDecision) => {
      if (!selectedId || !decision) return
      setReviews((prev) => ({ ...prev, [selectedId]: decision }))
      void saveReview(caseId, selectedId, decision).catch(() => {
        appendAudit({
          action: `Review save failed for ${selectedId}`,
          entityId: selectedId,
          source: 'Vigil review queue',
          lawfulBasis: 'Retry required — server unavailable',
        })
      })
      appendAudit({
        action: `Officer review: ${decision.replace('_', ' ')} on AI suggestion`,
        entityId: selectedId,
        source: 'Vigil review queue',
        lawfulBasis: 'Human review persisted server-side when API available',
      })
    },
    [selectedId, caseId, appendAudit],
  )

  const handleLogout = () => {
    appendAudit({
      action: 'Secure logout',
      entityId: caseId,
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
      entityId: caseId,
      source: 'Vigil audit export',
      lawfulBasis: 'Court disclosure / supervisory review',
    })
  }, [appendAudit, caseId])

  const handleIngested = useCallback(
    (summary: string) => {
      setTimelineRefreshKey((k) => k + 1)
      bumpRefresh()
      appendAudit({
        action: summary,
        entityId: selectedId ?? caseId,
        source: 'Vigil FIR ingest',
        lawfulBasis: 'Officer-uploaded FIR document — NLP extraction logged',
      })
    },
    [appendAudit, selectedId, caseId, bumpRefresh],
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

  const dataRefreshKey = timelineRefreshKey + refreshKey

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
            caseId={caseId}
            selectedId={selectedId}
            highlightedIds={highlightedIds}
            onSelect={setSelectedId}
            onEntitiesLoaded={mergeLiveEntities}
            refreshKey={dataRefreshKey}
          />
        )
      case 'timeline':
        return (
          <TimelineView
            selectedId={selectedId}
            highlightedIds={highlightedIds}
            entityLookup={{ ...entityMap, ...liveEntities }}
            timelineRefreshKey={dataRefreshKey}
            onSelectEntity={setSelectedId}
            onHoverEntities={(ids) => setHighlightedIds(new Set(ids))}
          />
        )
      case 'risk':
        return (
          <RiskScoringView
            selectedId={selectedId}
            onSelect={setSelectedId}
            refreshKey={dataRefreshKey}
          />
        )
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
  }, [
    view,
    caseId,
    selectedId,
    highlightedIds,
    auditLog,
    chainStatus,
    dataRefreshKey,
    handleOsintLookup,
    handleSearchPerformed,
    handleExportAudit,
    mergeLiveEntities,
    user.role,
    user.badgeId,
    user.name,
  ])

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
          caseId={caseId}
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

  return (
    <CaseProvider>
      <VigilDashboard user={user} />
    </CaseProvider>
  )
}
