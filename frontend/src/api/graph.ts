import { isApiConfigured, apiGet } from './client'
import { entities, graphLinks } from '../data/mockCase'
import type { Entity, GraphLink } from '../types'

export interface CaseGraphResponse {
  nodes: Entity[]
  links: GraphLink[]
  focus_person_id?: string | null
  summary?: string | null
}

export async function getCaseGraph(
  caseId: string,
  centerPersonId?: string | null,
): Promise<CaseGraphResponse> {
  if (isApiConfigured()) {
    const params = new URLSearchParams({ simplified: 'true' })
    if (centerPersonId) params.set('center_person_id', centerPersonId)
    const qs = params.toString()
    return apiGet<CaseGraphResponse>(
      `/cases/${caseId}/graph${qs ? `?${qs}` : ''}`,
    )
  }
  return {
    nodes: entities.filter((e) => e.type === 'person'),
    links: graphLinks
      .filter((l) => l.source.startsWith('P') && l.target.startsWith('P'))
      .map((l) => ({ ...l, weight: 2 })),
    focus_person_id: 'P00014',
    summary:
      'Rahul Mukherjee is the primary suspect at the centre of this ring. Line thickness shows how often they spoke on the phone.',
  }
}

export function graphNodesToEntityMap(nodes: Entity[]): Record<string, Entity> {
  return Object.fromEntries(nodes.map((n) => [n.id, n]))
}
