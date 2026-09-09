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

export interface RiskScoreComponents {
  centrality: number
  role: number
  case_history: number
}

export interface RiskScoreEntry {
  entity_id: string
  label: string
  city?: string | null
  role: Entity['role'] | null
  composite_score: number
  severity: SeverityBand
  components: RiskScoreComponents
  triage_rank: number
  explainability: string[]
}

export interface RiskScoreResponse {
  case_id: string
  scores: RiskScoreEntry[]
}

function severityFromScore(score: number): SeverityBand {
  if (score >= 75) return 'high'
  if (score >= 50) return 'medium'
  return 'low'
}

export function riskScoresToEntities(scores: RiskScoreEntry[]): Entity[] {
  return scores.map((r) => ({
    id: r.entity_id,
    label: r.label,
    type: 'person' as const,
    role: r.role ?? undefined,
    score: r.composite_score,
    severity: r.severity,
    sources: ['risk_score'],
    explainability: r.explainability,
    connections: [],
    metadata: {
      triage_rank: String(r.triage_rank),
      city: r.city ?? '',
      centrality: String(r.components.centrality),
      role_component: String(r.components.role),
      case_history: String(r.components.case_history),
    },
  }))
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

export async function getRiskScores(caseId: string): Promise<RiskScoreResponse> {
  if (isApiConfigured()) {
    return apiGet<RiskScoreResponse>(`/cases/${caseId}/analyze/risk-score`)
  }
  const mockScores: RiskScoreEntry[] = [...entities]
    .filter((e) => e.type === 'person')
    .sort((a, b) => b.score - a.score)
    .map((e, i) => ({
      entity_id: e.id,
      label: e.label,
      role: e.role ?? null,
      composite_score: e.score,
      severity: e.severity,
      components: { centrality: 20, role: 15, case_history: 10 },
      triage_rank: i + 1,
      explainability: e.explainability,
    }))
  return { case_id: caseId, scores: mockScores }
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
