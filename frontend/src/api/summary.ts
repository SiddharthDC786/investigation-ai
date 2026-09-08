import { isApiConfigured, apiGet } from './client'

export interface CaseSummaryResponse {
  case_id: string
  title: string
  narrative: string
  key_findings: string[]
  top_subjects: string[]
  timeline_highlights: string[]
  generated_in_ms: number
}

export async function getCaseSummary(caseId: string): Promise<CaseSummaryResponse | null> {
  if (!isApiConfigured()) return null
  return apiGet<CaseSummaryResponse>(`/case-summary/${encodeURIComponent(caseId)}`)
}
