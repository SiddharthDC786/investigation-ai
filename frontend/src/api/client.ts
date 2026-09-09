const API_BASE = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') ?? ''
const TOKEN_KEY = 'vigil_access_token'

export function getApiBase(): string {
  return API_BASE
}

export function isApiConfigured(): boolean {
  return API_BASE.length > 0
}

export function getAccessToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY)
}

export function setAccessToken(token: string | null): void {
  if (token) sessionStorage.setItem(TOKEN_KEY, token)
  else sessionStorage.removeItem(TOKEN_KEY)
}

function authHeaders(extra?: HeadersInit): HeadersInit {
  const token = getAccessToken()
  return {
    Accept: 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extra,
  }
}

export interface HealthResponse {
  status: string
  service: string
  postgres?: boolean
  neo4j?: boolean
  auth_enabled?: boolean
  nlp?: {
    engine: string
    spacy_model?: string | null
  }
}

export async function fetchHealth(): Promise<HealthResponse | null> {
  if (!API_BASE) return null
  try {
    const res = await fetch(`${API_BASE}/health`, { headers: { Accept: 'application/json' } })
    if (!res.ok) return null
    return res.json() as Promise<HealthResponse>
  } catch {
    return null
  }
}

export function formatApiError(err: unknown, fallback: string): string {
  if (err instanceof Error) {
    if (err.message.includes('Failed to fetch') || err.message.includes('NetworkError')) {
      return fallback
    }
    if (err.message.includes('401')) return 'Session expired — please sign in again.'
    if (err.message.includes('403')) return 'You do not have access to this case.'
    return err.message.length > 120 ? fallback : err.message
  }
  return fallback
}

export async function apiGet<T>(path: string, init?: RequestInit): Promise<T> {
  if (!API_BASE) {
    throw new Error('VITE_API_BASE_URL is not set — using mock data. Copy frontend/.env.example to .env')
  }

  const res = await fetch(`${API_BASE}${path.startsWith('/') ? path : `/${path}`}`, {
    ...init,
    headers: authHeaders(init?.headers),
  })

  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(`API ${res.status}: ${text}`)
  }

  return res.json() as Promise<T>
}

export async function apiPost<T>(path: string, body: unknown, init?: RequestInit): Promise<T> {
  if (!API_BASE) {
    throw new Error('VITE_API_BASE_URL is not set — using mock data. Copy frontend/.env.example to .env')
  }

  const res = await fetch(`${API_BASE}${path.startsWith('/') ? path : `/${path}`}`, {
    method: 'POST',
    ...init,
    headers: authHeaders({
      'Content-Type': 'application/json',
      ...init?.headers,
    }),
    body: JSON.stringify(body),
  })

  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(`API ${res.status}: ${text}`)
  }

  return res.json() as Promise<T>
}

export async function apiPostForm<T>(path: string, form: FormData, init?: RequestInit): Promise<T> {
  if (!API_BASE) {
    throw new Error('VITE_API_BASE_URL is not set')
  }
  const res = await fetch(`${API_BASE}${path.startsWith('/') ? path : `/${path}`}`, {
    method: 'POST',
    ...init,
    headers: authHeaders(init?.headers),
    body: form,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(`API ${res.status}: ${text}`)
  }
  return res.json() as Promise<T>
}
