import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import {
  authenticate,
  clearSession,
  extendSession,
  loadSession,
  saveSession,
  sessionMinutesLeft,
} from './session'
import type { AuthUser, SessionPayload } from './types'

interface AuthContextValue {
  user: AuthUser | null
  session: SessionPayload | null
  minutesLeft: number
  login: (badgeId: string, password: string) => boolean
  logout: () => void
  touchSession: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

const IDLE_MS = 30 * 60 * 1000

export function AuthProvider({ children }: { children: ReactNode }) {
  const [session, setSession] = useState<SessionPayload | null>(() => loadSession())
  const [minutesLeft, setMinutesLeft] = useState(() =>
    session ? sessionMinutesLeft(session) : 0,
  )

  const logout = useCallback(() => {
    clearSession()
    setSession(null)
    setMinutesLeft(0)
  }, [])

  const login = useCallback((badgeId: string, password: string) => {
    const user = authenticate(badgeId, password)
    if (!user) return false
    const next = saveSession(user)
    setSession(next)
    setMinutesLeft(sessionMinutesLeft(next))
    return true
  }, [])

  const touchSession = useCallback(() => {
    const next = extendSession()
    if (next) {
      setSession(next)
      setMinutesLeft(sessionMinutesLeft(next))
    } else {
      logout()
    }
  }, [logout])

  useEffect(() => {
    if (!session) return
    const tick = window.setInterval(() => {
      const current = loadSession()
      if (!current) {
        logout()
        return
      }
      setSession(current)
      setMinutesLeft(sessionMinutesLeft(current))
    }, 15000)
    return () => window.clearInterval(tick)
  }, [session, logout])

  useEffect(() => {
    if (!session) return
    let idleTimer = window.setTimeout(logout, IDLE_MS)
    const reset = () => {
      window.clearTimeout(idleTimer)
      touchSession()
      idleTimer = window.setTimeout(logout, IDLE_MS)
    }
    window.addEventListener('mousemove', reset)
    window.addEventListener('keydown', reset)
    window.addEventListener('click', reset)
    return () => {
      window.clearTimeout(idleTimer)
      window.removeEventListener('mousemove', reset)
      window.removeEventListener('keydown', reset)
      window.removeEventListener('click', reset)
    }
  }, [session, logout, touchSession])

  const value = useMemo(
    () => ({
      user: session?.user ?? null,
      session,
      minutesLeft,
      login,
      logout,
      touchSession,
    }),
    [session, minutesLeft, login, logout, touchSession],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
