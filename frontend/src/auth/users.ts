import type { AuthUser } from './types'

/** Demo accounts — replace with backend JWT auth in production. */
export const DEMO_USERS: Record<string, { password: string; user: AuthUser }> = {
  'INV-2847': {
    password: 'vigil2026',
    user: {
      badgeId: 'INV-2847',
      name: 'SI Sharma',
      role: 'investigator',
      station: 'Cyber Cell — Mumbai',
    },
  },
  'SUP-1001': {
    password: 'admin2026',
    user: {
      badgeId: 'SUP-1001',
      name: 'DySP Mehta',
      role: 'supervisor',
      station: 'Central Crime Branch',
    },
  },
}

export const SESSION_KEY = 'vigil_session'
export const SESSION_MINUTES = 30
