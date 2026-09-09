import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { listCases, type CaseSummary } from '../api/case'
import { CASE_DISPLAY_REF, CASE_ID, CASE_TITLE } from '../data/mockCase'
import { useAuth } from '../auth/AuthContext'

interface CaseContextValue {
  caseId: string
  caseTitle: string
  displayRef: string
  cases: CaseSummary[]
  loading: boolean
  error: string | null
  setCaseId: (id: string) => void
  refreshKey: number
  bumpRefresh: () => void
}

const CaseContext = createContext<CaseContextValue | null>(null)

export function CaseProvider({ children }: { children: ReactNode }) {
  const { user } = useAuth()
  const [caseId, setCaseId] = useState(CASE_ID)
  const [cases, setCases] = useState<CaseSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [refreshKey, setRefreshKey] = useState(0)

  const bumpRefresh = useCallback(() => setRefreshKey((k) => k + 1), [])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    void listCases()
      .then((rows) => {
        if (cancelled) return
        setCases(rows)
        if (rows.length > 0) {
          const allowed =
            user?.caseIds && user.caseIds.length > 0
              ? rows.filter((c) => user.caseIds!.includes(c.case_id))
              : rows
          const pick = allowed.find((c) => c.case_id === caseId) ?? allowed[0] ?? rows[0]
          if (pick) setCaseId(pick.case_id)
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : 'Could not load cases')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [user?.badgeId])

  const active = cases.find((c) => c.case_id === caseId)
  const value = useMemo(
    () => ({
      caseId,
      caseTitle: active?.title ?? CASE_TITLE,
      displayRef: CASE_DISPLAY_REF,
      cases,
      loading,
      error,
      setCaseId,
      refreshKey,
      bumpRefresh,
    }),
    [caseId, active, cases, loading, error, refreshKey, bumpRefresh],
  )

  return <CaseContext.Provider value={value}>{children}</CaseContext.Provider>
}

export function useCase() {
  const ctx = useContext(CaseContext)
  if (!ctx) throw new Error('useCase must be used within CaseProvider')
  return ctx
}
