import { isApiConfigured, apiGet } from './client'
import { entities, graphLinks } from '../data/mockCase'
import type { Entity, GraphLink, GraphStats } from '../types'

export interface CaseGraphResponse {
  nodes: Entity[]
  links: GraphLink[]
  focus_person_id?: string | null
  summary?: string | null
  connection_story?: string[]
  stats?: GraphStats | null
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
      'Rahul Mukherjee is the hub of this network. Red lines = phone calls; gold diamonds = shared contact numbers.',
    connection_story: [
      'Rahul Mukherjee is the investigation focus. Every connection is supported by call records.',
      'Sunil Patel (facilitator) — 9 calls with Rahul. CDR records.',
      'Gopal Nair (associate) — 7 calls with Rahul. CDR records.',
    ],
    stats: { person_count: 4, link_count: 4, shared_contact_count: 0 },
  }
}

export function graphNodesToEntityMap(nodes: Entity[]): Record<string, Entity> {
  return Object.fromEntries(nodes.map((n) => [n.id, n]))
}
