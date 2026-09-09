export type ViewId = 'search' | 'network' | 'timeline' | 'risk' | 'osint' | 'audit'

export type RoleFilter = NonNullable<Entity['role']> | 'all'

export interface SearchFilters {
  nameQuery: string
  phoneQuery: string
  areaQuery: string
  roleFilter: RoleFilter
  faceMatchPersonId: string | null
  /** Set when officer picks one person from multiple same-name matches */
  selectedPersonId: string | null
}

export interface RelatedPersonHit {
  entity: Entity
  hops: number
  connectionReason: string
}

export interface InvestigationSearchResult {
  nameCandidates: NameMatchHit[]
  needsDisambiguation: boolean
  primaryMatches: Entity[]
  relatedPeople: RelatedPersonHit[]
  linkedRecords: Entity[]
}

export type EntityType = 'person' | 'phone' | 'account' | 'address'

export type ReviewDecision = 'confirm' | 'dismiss' | 'needs_evidence' | null

export type SeverityBand = 'high' | 'medium' | 'low'

export interface Entity {
  id: string
  label: string
  type: EntityType
  role?: 'suspect' | 'associate' | 'facilitator' | 'witness' | 'complainant' | 'handler'
  subtitle?: string
  /** FIR typos, married names, aliases from recorded_names */
  aliases?: string[]
  score: number
  severity: SeverityBand
  sources: string[]
  explainability: string[]
  connections: { targetId: string; reason: string }[]
  metadata: Record<string, string>
}

export type NameMatchType = 'exact' | 'alias' | 'typo' | 'partial'

export interface NameMatchHit {
  entity: Entity
  matchType: NameMatchType
  matchedOn: string
  confidence: number
}

export interface GraphLink {
  source: string
  target: string
  label: string
  weight?: number
}

export interface TimelineEvent {
  id: string
  timestamp: string
  title: string
  description: string
  entityIds: string[]
  source: string
}

export interface AuditEntry {
  id: string
  timestamp: string
  action: string
  entityId: string
  source: string
  operator: string
  lawfulBasis: string
}

export interface OsintLookup {
  id: string
  label: string
  description: string
}
