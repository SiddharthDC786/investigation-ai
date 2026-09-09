import { apiGet, getApiBase, isApiConfigured, setAccessToken } from './client'
import type { AuthUser, UserRole } from '../auth/types'
import { DEMO_USERS } from '../auth/users'

export interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: {
    badge_id: string
    name: string
    role: UserRole
    case_ids: string[]
  }
}

export async function loginWithApi(badgeId: string, password: string): Promise<AuthUser | null> {
  if (!isApiConfigured()) {
    const entry = DEMO_USERS[badgeId.trim().toUpperCase()]
    if (!entry || entry.password !== password) return null
    return entry.user
  }
  try {
    const res = await fetch(`${getApiBase()}/auth/login`, {
      method: 'POST',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
      body: JSON.stringify({
        badge_id: badgeId.trim().toUpperCase(),
        password,
      }),
    })
    if (!res.ok) return null
    const data = (await res.json()) as LoginResponse
    setAccessToken(data.access_token)
    return {
      badgeId: data.user.badge_id,
      name: data.user.name,
      role: data.user.role,
      station: 'Cyber Cell — Demo',
      caseIds: data.user.case_ids ?? [],
    }
  } catch {
    return null
  }
}

export async function fetchCurrentUser(): Promise<AuthUser | null> {
  if (!isApiConfigured()) return null
  try {
    const me = await apiGet<LoginResponse['user']>('/auth/me')
    return {
      badgeId: me.badge_id,
      name: me.name,
      role: me.role,
      station: 'Cyber Cell — Demo',
      caseIds: me.case_ids ?? [],
    }
  } catch {
    setAccessToken(null)
    return null
  }
}

export function logoutApi(): void {
  setAccessToken(null)
}
