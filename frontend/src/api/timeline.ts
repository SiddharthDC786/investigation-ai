import { isApiConfigured, apiGet } from './client'
import { timelineEvents } from '../data/mockCase'
import type { TimelineEvent } from '../types'

export interface TimelineResponse {
  case_id: string
  events: TimelineEvent[]
}

export async function getCaseTimeline(caseId: string): Promise<TimelineResponse> {
  if (isApiConfigured()) {
    return apiGet<TimelineResponse>(`/cases/${caseId}/timeline`)
  }
  return { case_id: caseId, events: timelineEvents }
}
