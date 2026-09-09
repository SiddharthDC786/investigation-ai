import { DEMO_USERS, SESSION_KEY, SESSION_MINUTES } from './users'
import type { AuthUser, SessionPayload } from './types'

function encode(payload: SessionPayload): string {
  // btoa only supports Latin1; station names may include Unicode (e.g. em dash).
  return btoa(unescape(encodeURIComponent(JSON.stringify(payload))))
}

function decode(raw: string): SessionPayload | null {
  try {
    const payload = JSON.parse(decodeURIComponent(escape(atob(raw)))) as SessionPayload
    if (!payload.user?.badgeId || !payload.expiresAt) return null
    return payload
  } catch {
    return null
  }
}

export function saveSession(user: AuthUser, accessToken: string | null = null): SessionPayload {
  const now = Date.now()
  const payload: SessionPayload = {
    user,
    issuedAt: now,
    expiresAt: now + SESSION_MINUTES * 60 * 1000,
    accessToken,
  }
  sessionStorage.setItem(SESSION_KEY, encode(payload))
  return payload
}

export function loadSession(): SessionPayload | null {
  const raw = sessionStorage.getItem(SESSION_KEY)
  if (!raw) return null
  const payload = decode(raw)
  if (!payload) {
    sessionStorage.removeItem(SESSION_KEY)
    return null
  }
  if (Date.now() > payload.expiresAt) {
    sessionStorage.removeItem(SESSION_KEY)
    return null
  }
  return payload
}

export function clearSession(): void {
  sessionStorage.removeItem(SESSION_KEY)
}

export function extendSession(): SessionPayload | null {
  const current = loadSession()
  if (!current) return null
  return saveSession(current.user, current.accessToken ?? null)
}

export function sessionMinutesLeft(payload: SessionPayload): number {
  return Math.max(0, Math.ceil((payload.expiresAt - Date.now()) / 60000))
}

// Legacy export for mock-only fallback
export function authenticate(badgeId: string, password: string): AuthUser | null {
  const entry = DEMO_USERS[badgeId.trim().toUpperCase()]
  if (!entry || entry.password !== password) return null
  return entry.user
}
