import { apiGet, apiPost, isApiConfigured } from './client'
import type { ReviewDecision } from '../types'

export interface ReviewRecord {
  entity_id: string
  decision: ReviewDecision
  notes?: string | null
  reviewer_badge: string
  reviewer_name: string
}

export async function listReviews(caseId: string): Promise<ReviewRecord[]> {
  if (!isApiConfigured()) return []
  return apiGet<ReviewRecord[]>(`/cases/${caseId}/reviews`)
}

export async function saveReview(
  caseId: string,
  entityId: string,
  decision: ReviewDecision,
  notes?: string,
): Promise<ReviewRecord> {
  if (!isApiConfigured()) {
    return {
      entity_id: entityId,
      decision,
      notes: notes ?? null,
      reviewer_badge: 'LOCAL',
      reviewer_name: 'Local session',
    }
  }
  return apiPost<ReviewRecord>(`/cases/${caseId}/reviews`, {
    entity_id: entityId,
    decision,
    notes: notes ?? null,
  })
}
