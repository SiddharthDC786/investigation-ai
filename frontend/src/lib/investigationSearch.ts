import { entities, entityMap, graphLinks } from '../data/mockCase'
import type {
  Entity,
  InvestigationSearchResult,
  NameMatchHit,
  NameMatchType,
  RelatedPersonHit,
  SearchFilters,
} from '../types'

function norm(s: string) {
  return s.trim().toLowerCase().replace(/\s+/g, ' ')
}

function levenshtein(a: string, b: string): number {
  const m = a.length
  const n = b.length
  if (m === 0) return n
  if (n === 0) return m
  const dp = Array.from({ length: m + 1 }, (_, i) =>
    Array.from({ length: n + 1 }, (_, j) => (i === 0 ? j : j === 0 ? i : 0)),
  )
  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      dp[i][j] =
        a[i - 1] === b[j - 1]
          ? dp[i - 1][j - 1]
          : 1 + Math.min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1])
    }
  }
  return dp[m][n]
}

function nameVariants(entity: Entity): string[] {
  return [
    entity.label,
    entity.subtitle ?? '',
    ...(entity.aliases ?? []),
    ...Object.values(entity.metadata),
  ].filter(Boolean)
}

function phoneForPerson(personId: string): string | null {
  const phone = entities.find(
    (e) => e.type === 'phone' && e.metadata.person_id === personId,
  )
  return phone?.label ?? null
}

function scoreNameMatch(entity: Entity, query: string): NameMatchHit | null {
  if (entity.type !== 'person') return null
  const q = norm(query)
  if (!q) return null

  for (const variant of nameVariants(entity)) {
    const v = norm(variant)
    if (v === q) {
      return { entity, matchType: 'exact', matchedOn: variant, confidence: 100 }
    }
    if (v.includes(q) || q.includes(v)) {
      return { entity, matchType: 'partial', matchedOn: variant, confidence: 88 }
    }
  }

  const qTokens = q.split(' ').filter((t) => t.length >= 2)
  for (const variant of nameVariants(entity)) {
    const vTokens = norm(variant).split(' ')
    for (const qt of qTokens) {
      for (const vt of vTokens) {
        if (vt === qt) {
          return { entity, matchType: 'partial', matchedOn: variant, confidence: 82 }
        }
        const dist = levenshtein(qt, vt)
        const maxDist = qt.length <= 4 ? 1 : 2
        if (dist > 0 && dist <= maxDist) {
          return {
            entity,
            matchType: 'typo',
            matchedOn: variant,
            confidence: Math.max(55, 92 - dist * 12),
          }
        }
      }
    }
  }

  for (const alias of entity.aliases ?? []) {
    const a = norm(alias)
    if (levenshtein(a, q) <= 2) {
      return { entity, matchType: 'alias', matchedOn: alias, confidence: 78 }
    }
  }

  return null
}

function findNameCandidates(nameQuery: string): NameMatchHit[] {
  const hits: NameMatchHit[] = []
  const seen = new Set<string>()
  for (const entity of entities) {
    const hit = scoreNameMatch(entity, nameQuery)
    if (!hit || seen.has(entity.id)) continue
    seen.add(entity.id)
    hits.push(hit)
  }
  return hits.sort((a, b) => b.confidence - a.confidence || b.entity.score - a.entity.score)
}

function personIdsFromPhoneQuery(phoneQuery: string): string[] {
  if (!phoneQuery.trim()) return []
  const q = phoneQuery.replace(/\D/g, '')
  return entities
    .filter((e) => e.type === 'phone' && e.label.replace(/\D/g, '').includes(q))
    .flatMap((e) => (e.metadata.person_id ? [e.metadata.person_id] : []))
}

function buildAdjacency() {
  const adj = new Map<string, { id: string; reason: string }[]>()
  const add = (a: string, b: string, reason: string) => {
    if (!adj.has(a)) adj.set(a, [])
    adj.get(a)!.push({ id: b, reason })
  }
  for (const link of graphLinks) {
    add(link.source, link.target, link.label)
    add(link.target, link.source, link.label)
  }
  for (const e of entities) {
    for (const c of e.connections) {
      add(e.id, c.targetId, c.reason)
      add(c.targetId, e.id, c.reason)
    }
  }
  return adj
}

const adjacency = buildAdjacency()

function findRelatedPeople(seedPersonIds: string[], maxHops = 3): RelatedPersonHit[] {
  const seen = new Set<string>(seedPersonIds)
  const results: RelatedPersonHit[] = []

  for (const seed of seedPersonIds) {
    let frontier = [{ id: seed, hops: 0, reason: 'Search match' }]
    for (let hop = 1; hop <= maxHops; hop++) {
      const next: typeof frontier = []
      for (const node of frontier) {
        for (const edge of adjacency.get(node.id) ?? []) {
          if (seen.has(edge.id)) continue
          seen.add(edge.id)
          const entity = entityMap[edge.id]
          if (!entity) continue
          if (entity.type === 'person') {
            results.push({ entity, hops: hop, connectionReason: edge.reason })
          }
          next.push({ id: edge.id, hops: hop, reason: edge.reason })
        }
      }
      frontier = next
    }
  }

  return results.sort((a, b) => a.hops - b.hops || b.entity.score - a.entity.score)
}

function collectLinkedRecords(personIds: Set<string>, maxItems = 8): Entity[] {
  const phones: Entity[] = []
  const accounts: Entity[] = []
  const linked = new Set<string>()
  for (const pid of personIds) {
    for (const edge of adjacency.get(pid) ?? []) {
      const e = entityMap[edge.id]
      if (!e || e.type === 'person' || linked.has(e.id)) continue
      linked.add(e.id)
      if (e.type === 'phone') phones.push(e)
      else if (e.type === 'account') accounts.push(e)
    }
  }
  const remaining = Math.max(0, maxItems - phones.length)
  return [...phones, ...accounts.slice(0, remaining)]
}

function passesRole(entity: Entity, roleFilter: SearchFilters['roleFilter']) {
  if (roleFilter === 'all') return true
  return entity.role === roleFilter
}

function passesArea(entity: Entity, areaQuery: string) {
  if (!areaQuery.trim()) return true
  const q = norm(areaQuery)
  const city = entity.metadata.city ? norm(entity.metadata.city) : ''
  const label = norm(entity.label)
  return city.includes(q) || label.includes(q)
}

function passesGender(entity: Entity, genderQuery: string) {
  if (!genderQuery.trim()) return true
  const q = norm(genderQuery)
  const gender = entity.metadata.gender ? norm(entity.metadata.gender) : ''
  return gender.includes(q)
}

function passesAge(entity: Entity, ageQuery: string) {
  if (!ageQuery.trim()) return true
  const target = parseInt(ageQuery, 10)
  if (Number.isNaN(target)) return false
  const age = entity.metadata.age ? parseInt(entity.metadata.age, 10) : NaN
  return age === target
}

function intersectSets(sets: string[][]): string[] {
  if (sets.length === 0) return []
  let result = new Set(sets[0])
  for (let i = 1; i < sets.length; i++) {
    const next = new Set(sets[i])
    result = new Set([...result].filter((id) => next.has(id)))
  }
  return [...result]
}

function personIdsFromAreaQuery(areaQuery: string): string[] {
  if (!areaQuery.trim()) return []
  return entities
    .filter((e) => e.type === 'person' && passesArea(e, areaQuery))
    .map((e) => e.id)
}

function applyFilters(candidates: Entity[], filters: SearchFilters): Entity[] {
  let list = [...candidates]

  if (filters.selectedPersonId) {
    const picked = entityMap[filters.selectedPersonId]
    return picked?.type === 'person' ? [picked] : list.filter((e) => e.id === filters.selectedPersonId)
  }

  if (filters.areaQuery.trim()) {
    list = list.filter((e) => passesArea(e, filters.areaQuery))
  }
  if (filters.roleFilter !== 'all') {
    list = list.filter((e) => passesRole(e, filters.roleFilter))
  }

  const phonePersonIds = personIdsFromPhoneQuery(filters.phoneQuery)
  if (filters.phoneQuery.trim()) {
    list = list.filter((e) => phonePersonIds.includes(e.id))
  }

  if (filters.faceMatchPersonId && entityMap[filters.faceMatchPersonId]) {
    const face = entityMap[filters.faceMatchPersonId]
    if (face.type === 'person') {
      list = list.filter((e) => e.id === face.id)
    }
  }

  if (filters.genderQuery.trim()) {
    list = list.filter((e) => passesGender(e, filters.genderQuery))
  }

  if (filters.ageQuery.trim()) {
    list = list.filter((e) => passesAge(e, filters.ageQuery))
  }

  return list
}

export function runInvestigationSearch(filters: SearchFilters): InvestigationSearchResult {
  const hasQuery =
    filters.nameQuery.trim() ||
    filters.phoneQuery.trim() ||
    filters.areaQuery.trim() ||
    filters.genderQuery.trim() ||
    filters.ageQuery.trim() ||
    filters.fatherNameQuery.trim() ||
    filters.faceMatchPersonId ||
    filters.selectedPersonId

  if (!hasQuery) {
    return {
      nameCandidates: [],
      needsDisambiguation: false,
      primaryMatches: [],
      relatedPeople: [],
      linkedRecords: [],
    }
  }

  if (filters.fatherNameQuery.trim()) {
    return {
      nameCandidates: [],
      needsDisambiguation: false,
      primaryMatches: [],
      relatedPeople: [],
      linkedRecords: [],
      message: 'Father name is not available in the FIR database for this case.',
    }
  }

  if (filters.selectedPersonId) {
    const picked = entityMap[filters.selectedPersonId]
    const primaryMatches = picked?.type === 'person' ? [picked] : []
    let nameCandidates: NameMatchHit[] = []
    if (filters.nameQuery.trim()) {
      nameCandidates = findNameCandidates(filters.nameQuery).filter((h) =>
        primaryMatches.some((p) => p.id === h.entity.id),
      )
    }
    return finalizeMockSearch(filters, nameCandidates, primaryMatches)
  }

  const idSets: string[][] = []
  let nameCandidates: NameMatchHit[] = []

  if (filters.nameQuery.trim()) {
    nameCandidates = findNameCandidates(filters.nameQuery)
    const nameIds = nameCandidates.map((h) => h.entity.id)
    if (nameIds.length) idSets.push(nameIds)
  }

  if (filters.areaQuery.trim()) {
    const areaIds = personIdsFromAreaQuery(filters.areaQuery)
    if (areaIds.length) idSets.push(areaIds)
  }

  if (filters.phoneQuery.trim()) {
    const phoneIds = personIdsFromPhoneQuery(filters.phoneQuery)
    if (!phoneIds.length) {
      return {
        nameCandidates,
        needsDisambiguation: false,
        primaryMatches: [],
        relatedPeople: [],
        linkedRecords: [],
        message: 'No data available — no person is registered with this phone number.',
      }
    }
    idSets.push(phoneIds)
  }

  if (filters.genderQuery.trim()) {
    const genderIds = entities
      .filter((e) => e.type === 'person' && passesGender(e, filters.genderQuery))
      .map((e) => e.id)
    if (genderIds.length) idSets.push(genderIds)
  }

  if (filters.ageQuery.trim()) {
    const ageIds = entities
      .filter((e) => e.type === 'person' && passesAge(e, filters.ageQuery))
      .map((e) => e.id)
    if (ageIds.length) idSets.push(ageIds)
  }

  if (filters.faceMatchPersonId && entityMap[filters.faceMatchPersonId]?.type === 'person') {
    idSets.push([filters.faceMatchPersonId])
  }

  if (!idSets.length) {
    return {
      nameCandidates,
      needsDisambiguation: false,
      primaryMatches: [],
      relatedPeople: [],
      linkedRecords: [],
    }
  }

  const finalIds = intersectSets(idSets)
  let primaryMatches = finalIds
    .map((id) => entityMap[id])
    .filter((e): e is Entity => e?.type === 'person')

  primaryMatches = applyFilters(primaryMatches, { ...filters, selectedPersonId: null })

  if (filters.nameQuery.trim()) {
    const matchIds = new Set(primaryMatches.map((e) => e.id))
    nameCandidates = nameCandidates.filter((h) => matchIds.has(h.entity.id))
  }

  return finalizeMockSearch(filters, nameCandidates, primaryMatches, primaryMatches.length ? undefined : 'No data available — no person matches all search filters.')
}

function finalizeMockSearch(
  filters: SearchFilters,
  nameCandidates: NameMatchHit[],
  primaryMatches: Entity[],
  message?: string,
): InvestigationSearchResult {
  const needsDisambiguation = primaryMatches.length > 1

  let relatedPeople: RelatedPersonHit[] = []
  let linkedRecords: Entity[] = []

  if (!needsDisambiguation && primaryMatches.length === 1) {
    const seedIds = primaryMatches.map((e) => e.id)
    relatedPeople = findRelatedPeople(seedIds)
    if (filters.roleFilter !== 'all') {
      relatedPeople = relatedPeople.filter((r) => passesRole(r.entity, filters.roleFilter))
    }
    linkedRecords = collectLinkedRecords(new Set(seedIds))
  }

  return {
    nameCandidates,
    needsDisambiguation,
    primaryMatches,
    relatedPeople,
    linkedRecords,
    message,
  }
}

export function listSearchAreas(): string[] {
  const cities = new Set<string>()
  for (const e of entities) {
    if (e.metadata.city) cities.add(e.metadata.city)
    if (e.type === 'address') cities.add(e.label.split(' ')[0])
  }
  return [...cities].sort()
}

export function getPersonPhoneDisplay(personId: string): string | null {
  return phoneForPerson(personId)
}

export function matchTypeLabel(type: NameMatchType): string {
  const map: Record<NameMatchType, string> = {
    exact: 'Exact name',
    alias: 'Known alias / variant',
    typo: 'Possible typo match',
    partial: 'Partial name',
  }
  return map[type]
}

export function demoFaceMatch(_file: File): { personId: string; similarityScore: number } {
  return { personId: 'P00014', similarityScore: 72 }
}
