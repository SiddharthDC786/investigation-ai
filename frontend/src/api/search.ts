import { isApiConfigured, apiGet } from './client'
import { demoFaceMatch, runInvestigationSearch } from '../lib/investigationSearch'
import type { InvestigationSearchResult, SearchFilters } from '../types'

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

export async function searchByFace(caseId: string, file: File) {
  if (isApiConfigured()) {
    const body = new FormData()
    body.append('photo', file)
    const res = await fetch(`${import.meta.env.VITE_API_BASE_URL}/cases/${caseId}/search/face`, {
      method: 'POST',
      body,
    })
    if (!res.ok) throw new Error('Face search failed')
    return res.json() as Promise<{ personId: string; confidence: number }>
  }
  return demoFaceMatch(file)
}
