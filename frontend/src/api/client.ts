const API_BASE = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') ?? ''

export function getApiBase(): string {
  return API_BASE
}

export function isApiConfigured(): boolean {
  return API_BASE.length > 0
}

export interface HealthResponse {
  status: string
  service: string
  postgres?: boolean
  neo4j?: boolean
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
    headers: {
      Accept: 'application/json',
      ...init?.headers,
    },
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
    headers: {
      Accept: 'application/json',
      'Content-Type': 'application/json',
      ...init?.headers,
    },
    body: JSON.stringify(body),
  })

  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(`API ${res.status}: ${text}`)
  }

  return res.json() as Promise<T>
}

/** Example once friend implements routes: apiGet('/cases') */
