import { isApiConfigured, apiGet } from './client'
import { entities } from '../data/mockCase'
import type { Entity, SeverityBand } from '../types'

export interface CentralityEntry {
  entity_id: string
  label: string
  entity_type: string
  betweenness: number
  pagerank: number
  rank: number
}

export interface CentralityResponse {
  case_id: string
  rankings: CentralityEntry[]
}

export interface CommunityCluster {
  community_id: string
  entity_ids: string[]
  label: string
  member_count: number
  suspicion_score: number
}

export interface CommunitiesResponse {
  case_id: string
  communities: CommunityCluster[]
}

function severityFromScore(score: number): SeverityBand {
  if (score >= 75) return 'high'
  if (score >= 50) return 'medium'
  return 'low'
}

export function centralityToEntities(rankings: CentralityEntry[]): Entity[] {
  return rankings
    .filter((r) => r.entity_type === 'person')
    .map((r) => {
      const score = Math.min(99, Math.round(r.pagerank * 500 + r.betweenness * 200 + 35))
      return {
        id: r.entity_id,
        label: r.label,
        type: 'person' as const,
        score,
        severity: severityFromScore(score),
        sources: ['network_analysis'],
        explainability: [
          `PageRank ${r.pagerank.toFixed(4)} · betweenness ${r.betweenness.toFixed(4)} · rank #${r.rank}`,
        ],
        connections: [],
        metadata: {
          pagerank: String(r.pagerank),
          betweenness: String(r.betweenness),
          rank: String(r.rank),
        },
      }
    })
}

export async function getCentrality(caseId: string): Promise<CentralityResponse> {
  if (isApiConfigured()) {
    return apiGet<CentralityResponse>(`/cases/${caseId}/analyze/centrality`)
  }
  const mockRankings: CentralityEntry[] = [...entities]
    .sort((a, b) => b.score - a.score)
    .map((e, i) => ({
      entity_id: e.id,
      label: e.label,
      entity_type: e.type,
      betweenness: (100 - i * 7) / 1000,
      pagerank: (100 - i * 5) / 1000,
      rank: i + 1,
    }))
  return { case_id: caseId, rankings: mockRankings }
}

export async function getCommunities(caseId: string): Promise<CommunitiesResponse> {
  if (isApiConfigured()) {
    return apiGet<CommunitiesResponse>(`/cases/${caseId}/analyze/communities`)
  }
  return { case_id: caseId, communities: [] }
}
