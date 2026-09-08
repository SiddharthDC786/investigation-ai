import { isApiConfigured, apiGet } from './client'
import { entities, graphLinks } from '../data/mockCase'
import type { Entity, GraphLink } from '../types'

export interface CaseGraphResponse {
  nodes: Entity[]
  links: GraphLink[]
}

export async function getCaseGraph(
  caseId: string,
  centerPersonId?: string | null,
): Promise<CaseGraphResponse> {
  if (isApiConfigured()) {
    const params = new URLSearchParams()
    if (centerPersonId) params.set('center_person_id', centerPersonId)
    const qs = params.toString()
    return apiGet<CaseGraphResponse>(
      `/cases/${caseId}/graph${qs ? `?${qs}` : ''}`,
    )
  }
  return {
    nodes: entities,
    links: graphLinks.map((l) => ({ ...l })),
  }
}

export function graphNodesToEntityMap(nodes: Entity[]): Record<string, Entity> {
  return Object.fromEntries(nodes.map((n) => [n.id, n]))
}
