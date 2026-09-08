import { DEMO_USERS, SESSION_KEY, SESSION_MINUTES } from './users'
import type { AuthUser, SessionPayload } from './types'

function encode(payload: SessionPayload): string {
  return btoa(JSON.stringify(payload))
}

function decode(raw: string): SessionPayload | null {
  try {
    const payload = JSON.parse(atob(raw)) as SessionPayload
    if (!payload.user?.badgeId || !payload.expiresAt) return null
    return payload
  } catch {
    return null
  }
}

export function authenticate(badgeId: string, password: string): AuthUser | null {
  const entry = DEMO_USERS[badgeId.trim().toUpperCase()]
  if (!entry || entry.password !== password) return null
  return entry.user
}

export function saveSession(user: AuthUser): SessionPayload {
  const now = Date.now()
  const payload: SessionPayload = {
    user,
    issuedAt: now,
    expiresAt: now + SESSION_MINUTES * 60 * 1000,
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
  return saveSession(current.user)
}

export function sessionMinutesLeft(payload: SessionPayload): number {
  return Math.max(0, Math.ceil((payload.expiresAt - Date.now()) / 60000))
}
