import { isApiConfigured, apiGet } from './client'

export interface SourceCitation {
  source_type: string
  source_id: string
  excerpt: string | null
}

export interface RelationshipFact {
  related_entity_id: string
  related_label: string
  relationship: string
}

export interface ExplainResponse {
  entity_id: string
  case_id: string
  label: string
  narrative: string
  reasoning_steps: string[]
  source_citations: SourceCitation[]
  relationships: RelationshipFact[]
  risk_factors: string[]
}

export async function getEntityExplanation(
  entityId: string,
  caseId: string,
): Promise<ExplainResponse | null> {
  if (!isApiConfigured()) return null
  return apiGet<ExplainResponse>(
    `/explain/${encodeURIComponent(entityId)}?case_id=${encodeURIComponent(caseId)}`,
  )
}
