import { isApiConfigured, apiGet } from './client'
import { CASE_ID, CASE_TITLE } from '../data/mockCase'

export interface CaseSummary {
  case_id: string
  title: string
  description?: string | null
  status?: string
}

export async function getCase(caseId: string): Promise<CaseSummary> {
  if (isApiConfigured()) {
    return apiGet<CaseSummary>(`/cases/${caseId}`)
  }
  return {
    case_id: CASE_ID,
    title: CASE_TITLE,
    description: 'Demo case — mock mode',
    status: 'OPEN',
  }
}

export async function listCases(): Promise<CaseSummary[]> {
  if (isApiConfigured()) {
    return apiGet<CaseSummary[]>('/cases')
  }
  return [
    {
      case_id: CASE_ID,
      title: CASE_TITLE,
      status: 'OPEN',
    },
  ]
}

export interface CaseStats {
  case_id: string
  persons: number
  cdr_records: number
  transactions: number
  timeline_events: number
}

export async function getCaseStats(caseId: string): Promise<CaseStats | null> {
  if (!isApiConfigured()) return null
  return apiGet<CaseStats>(`/cases/${caseId}/stats`)
}
