import { apiGet, apiPost, isApiConfigured } from './client'
import type { AuditEntry } from '../types'

export interface OsintEnrichRequest {
  case_id: string
  entity_id: string
  lookup_id: string
}

export interface OsintEnrichmentHit {
  title: string
  detail: string
  source_registry: string
  relevance_score: number
  match_quality: string
  simulated: boolean
  source_type: string
  requires_officer_review: boolean
}

export interface OsintEnrichResponse {
  enrichment_id: string
  entity_id: string
  lookup_id: string
  lookup_label: string
  case_id: string
  simulated: boolean
  disclaimer: string
  results: OsintEnrichmentHit[]
  graph_links_added: string[]
  suggested_links: string[]
  audit_entry_id: string
  audit_hash: string
}

export interface OsintAuditLogResponse {
  case_id: string | null
  entries: (AuditEntry & { entryHash?: string; prevHash?: string })[]
  chain_status: string
}

export interface AuditVerifyResponse {
  status: string
  entries_checked: number
  broken_entry_id: string | null
  message: string
}

export async function enrichEntity(
  payload: OsintEnrichRequest,
): Promise<OsintEnrichResponse> {
  return apiPost<OsintEnrichResponse>('/osint/enrich', payload)
}

export async function getOsintAuditLog(caseId: string): Promise<OsintAuditLogResponse> {
  return apiGet<OsintAuditLogResponse>(`/osint/audit-log?case_id=${encodeURIComponent(caseId)}`)
}

export async function verifyAuditChain(caseId?: string): Promise<AuditVerifyResponse> {
  const qs = caseId ? `?case_id=${encodeURIComponent(caseId)}` : ''
  return apiGet<AuditVerifyResponse>(`/audit/verify${qs}`)
}

export function isOsintLive(): boolean {
  return isApiConfigured()
}
