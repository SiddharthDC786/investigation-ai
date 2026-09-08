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
