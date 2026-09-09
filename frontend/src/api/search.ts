import { apiGet, apiPostForm, isApiConfigured } from './client'
import { demoFaceMatch, runInvestigationSearch } from '../lib/investigationSearch'
import type { InvestigationSearchResult, SearchFilters } from '../types'

export interface FaceSearchResponse {
  person_id: string | null
  similarity_score: number
  score_type: string
  simulated: boolean
  match_quality: string
  requires_officer_review: boolean
  disclaimer: string
  message: string
}

export async function searchInvestigation(
  caseId: string,
  filters: SearchFilters,
): Promise<InvestigationSearchResult> {
  if (isApiConfigured()) {
    const params = new URLSearchParams()
    if (filters.nameQuery) params.set('name', filters.nameQuery)
    if (filters.phoneQuery) params.set('phone', filters.phoneQuery)
    if (filters.areaQuery) params.set('area', filters.areaQuery)
    if (filters.roleFilter !== 'all') params.set('role', filters.roleFilter)
    if (filters.genderQuery) params.set('gender', filters.genderQuery)
    if (filters.ageQuery) params.set('age', filters.ageQuery)
    if (filters.fatherNameQuery) params.set('father_name', filters.fatherNameQuery)
    if (filters.faceMatchPersonId) params.set('face_person_id', filters.faceMatchPersonId)
    if (filters.selectedPersonId) params.set('selected_person_id', filters.selectedPersonId)
    return apiGet<InvestigationSearchResult>(`/cases/${caseId}/search?${params}`)
  }
  return runInvestigationSearch(filters)
}

export async function searchByFace(caseId: string, file: File): Promise<FaceSearchResponse> {
  if (isApiConfigured()) {
    const body = new FormData()
    body.append('photo', file)
    return apiPostForm<FaceSearchResponse>(`/cases/${caseId}/search/face`, body)
  }
  const demo = demoFaceMatch(file)
  return {
    person_id: demo.personId,
    similarity_score: demo.similarityScore,
    score_type: 'demo_similarity',
    simulated: true,
    match_quality: 'demo_stub',
    requires_officer_review: true,
    disclaimer: 'Mock mode — no biometric engine.',
    message: 'Demo stub match for offline training.',
  }
}
