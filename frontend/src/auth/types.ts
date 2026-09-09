export type UserRole = 'investigator' | 'supervisor'

export interface AuthUser {
  badgeId: string
  name: string
  role: UserRole
  station: string
  caseIds?: string[]
}

export interface SessionPayload {
  user: AuthUser
  issuedAt: number
  expiresAt: number
  accessToken?: string | null
}
