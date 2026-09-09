import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import ForceGraph2D, { type ForceGraphMethods, type LinkObject, type NodeObject } from 'react-force-graph-2d'
import { getCaseGraph, type CaseGraphResponse } from '../api/graph'
import { CASE_ID } from '../data/mockCase'
import { useLanguage } from '../i18n/LanguageContext'
import type { Entity, GraphLink, GraphStats } from '../types'

interface NetworkGraphViewProps {
  caseId?: string
  selectedId: string | null
  highlightedIds: Set<string>
  onSelect: (id: string) => void
  onEntitiesLoaded?: (entities: Entity[]) => void
  refreshKey?: number
}

type GraphNode = Entity & { x?: number; y?: number; fx?: number; fy?: number }
type GraphLinkObj = GraphLink & { source: string | GraphNode; target: string | GraphNode }

const ROLE_COLORS: Partial<Record<NonNullable<Entity['role']>, string>> = {
  suspect: '#e85d4c',
  associate: '#d4a017',
  facilitator: '#4a90d9',
  witness: '#5cba7a',
  complainant: '#8b7aa8',
  handler: '#a855f7',
}

const ROLE_LABELS: Partial<Record<NonNullable<Entity['role']>, string>> = {
  suspect: 'Suspect',
  associate: 'Associate',
  facilitator: 'Facilitator',
  witness: 'Witness',
  complainant: 'Complainant',
  handler: 'Handler',
}

const LINK_STYLE: Record<string, { color: string; dash: number[] }> = {
  phone_call: { color: 'rgba(232, 93, 76, 0.85)', dash: [] },
  relationship: { color: 'rgba(139, 122, 168, 0.7)', dash: [6, 4] },
  shared_contact: { color: 'rgba(196, 163, 90, 0.9)', dash: [3, 3] },
}

function asNodeId(value: string | GraphNode): string {
  return typeof value === 'string' ? value : (value.id ?? '')
}

function linkEndpoints(link: GraphLinkObj): [string, string] {
  return [asNodeId(link.source as string | GraphNode), asNodeId(link.target as string | GraphNode)]
}

function linkTouchesFocus(link: GraphLink, focusId: string | null | undefined): boolean {
  if (!focusId) return false
  return link.source === focusId || link.target === focusId
}

export function NetworkGraphView({
  caseId = CASE_ID,
  selectedId,
  highlightedIds,
  onSelect,
  onEntitiesLoaded,
  refreshKey = 0,
}: NetworkGraphViewProps) {
  const { t } = useLanguage()
  const fgRef = useRef<ForceGraphMethods<NodeObject<GraphNode>, LinkObject<GraphNode, GraphLinkObj>> | undefined>(
    undefined,
  )
  const [nodes, setNodes] = useState<Entity[]>([])
  const [links, setLinks] = useState<GraphLink[]>([])
  const [focusId, setFocusId] = useState<string | null>(null)
  const [summary, setSummary] = useState<string | null>(null)
  const [connectionStory, setConnectionStory] = useState<string[]>([])
  const [stats, setStats] = useState<GraphStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [hoverLink, setHoverLink] = useState<GraphLink | null>(null)
  const [hoverNodeId, setHoverNodeId] = useState<string | null>(null)

  const centerId = selectedId ?? focusId

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    void getCaseGraph(caseId, selectedId)
      .then((data: CaseGraphResponse) => {
        if (cancelled) return
        setNodes(data.nodes)
        setLinks(data.links)
        setFocusId(data.focus_person_id ?? null)
        setSummary(data.summary ?? null)
        setConnectionStory(data.connection_story ?? [])
        setStats(data.stats ?? null)
        onEntitiesLoaded?.(data.nodes)
      })
      .catch((err: Error) => {
        if (cancelled) return
        setError(err.message)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [caseId, selectedId, onEntitiesLoaded, refreshKey])

  const graphData = useMemo(
    () => ({
      nodes: nodes.map((e) => ({ ...e, id: e.id, name: e.label })),
      links: links.map((l) => ({ ...l, weight: l.weight ?? 1, link_type: l.link_type ?? 'phone_call' })),
    }),
    [nodes, links],
  )

  const focusEntity = useMemo(
    () => nodes.find((n) => n.id === centerId) ?? nodes.find((n) => n.role === 'suspect'),
    [nodes, centerId],
  )

  const nodeMap = useMemo(() => Object.fromEntries(nodes.map((n) => [n.id, n])), [nodes])

  const groupedConnections = useMemo(() => {
    const fid = centerId ?? focusId
    const direct: typeof links = []
    const innerRing: typeof links = []
    const shared: typeof links = []

    for (const link of links) {
      if (link.link_type === 'shared_contact') {
        shared.push(link)
      } else if (fid && linkTouchesFocus(link, fid) && link.link_type === 'phone_call') {
        direct.push(link)
      } else if (link.link_type === 'phone_call') {
        innerRing.push(link)
      }
    }

    const sortByWeight = (a: GraphLink, b: GraphLink) => (b.weight ?? 1) - (a.weight ?? 1)
    return {
      direct: direct.sort(sortByWeight),
      innerRing: innerRing.sort(sortByWeight),
      shared: shared.sort(sortByWeight),
    }
  }, [links, centerId, focusId])

  const renderConnectionRow = (link: GraphLink, key: string) => {
    const fid = centerId ?? focusId
    const isPersonLink = link.link_type !== 'shared_contact'
    const otherId =
      isPersonLink && fid
        ? link.source === fid
          ? link.target
          : link.source
        : link.source.startsWith('P')
          ? link.source
          : link.target
    const other = nodeMap[otherId] ?? nodeMap[link.target] ?? nodeMap[link.source]
    const label = other?.label ?? otherId

    return (
      <li key={key}>
        <button
          type="button"
          onClick={() => onSelect(otherId)}
          className="w-full rounded border border-console-border/60 bg-console-bg/50 px-3 py-2.5 text-left transition hover:border-accent/40 hover:bg-console-bg"
        >
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <span className="block text-sm font-medium text-text-primary">{label}</span>
              {other?.metadata?.city && (
                <span className="text-[11px] text-text-muted">{other.metadata.city}</span>
              )}
            </div>
            <span
              className="shrink-0 rounded px-1.5 py-0.5 text-[10px] font-semibold uppercase"
              style={{
                backgroundColor:
                  link.link_type === 'shared_contact'
                    ? '#c4a35a22'
                    : `${ROLE_COLORS[other?.role ?? 'associate'] ?? '#4a90d9'}22`,
                color:
                  link.link_type === 'shared_contact'
                    ? '#c4a35a'
                    : ROLE_COLORS[other?.role ?? 'associate'] ?? '#4a90d9',
              }}
            >
              {link.link_type === 'shared_contact'
                ? t.network.legendPhone
                : (ROLE_LABELS[other?.role ?? 'associate'] ?? 'Link')}
            </span>
          </div>
          <p className="mt-1.5 text-xs font-medium text-accent-amber/90">{link.label}</p>
          {link.evidence && <p className="mt-1 text-[11px] leading-snug text-text-muted">{link.evidence}</p>}
        </button>
      </li>
    )
  }

  useEffect(() => {
    if (loading || graphData.nodes.length === 0 || !fgRef.current) return
    const anchor = centerId ?? focusId ?? graphData.nodes.find((n) => n.role === 'suspect')?.id
    if (!anchor) return

    const dataNodes = graphData.nodes as GraphNode[]
    const focusNode = dataNodes.find((n) => n.id === anchor)
    if (focusNode) {
      focusNode.fx = 0
      focusNode.fy = 0
    }

    const people = dataNodes.filter((n) => n.id !== anchor && n.type === 'person')
    const phones = dataNodes.filter((n) => n.type === 'phone')

    people.forEach((node, index) => {
      const angle = (2 * Math.PI * index) / Math.max(people.length, 1) - Math.PI / 2
      const isDirect = links.some(
        (l) =>
          l.link_type === 'phone_call' &&
          ((l.source === anchor && l.target === node.id) || (l.target === anchor && l.source === node.id)),
      )
      const radius = isDirect ? 125 : 155
      node.fx = Math.cos(angle) * radius
      node.fy = Math.sin(angle) * radius
    })

    phones.forEach((phone, index) => {
      const connected = links.filter((l) => l.source === phone.id || l.target === phone.id)
      const personIds = connected
        .flatMap((l) => [l.source, l.target])
        .filter((id) => id !== phone.id && nodeMap[id]?.type === 'person')
      const positions = personIds
        .map((pid) => dataNodes.find((n) => n.id === pid))
        .filter((n): n is GraphNode => Boolean(n?.fx != null && n?.fy != null))
      if (positions.length >= 1) {
        const cx = positions.reduce((s, p) => s + (p.fx ?? 0), 0) / positions.length
        const cy = positions.reduce((s, p) => s + (p.fy ?? 0), 0) / positions.length
        phone.fx = cx * 0.45
        phone.fy = cy * 0.45
      } else {
        const angle = (2 * Math.PI * index) / Math.max(phones.length, 1)
        phone.fx = Math.cos(angle) * 55
        phone.fy = Math.sin(angle) * 55
      }
    })

    fgRef.current.d3ReheatSimulation()

    const timer = window.setTimeout(() => {
      fgRef.current?.zoomToFit(480, 90)
    }, 700)
    return () => window.clearTimeout(timer)
  }, [loading, graphData, centerId, focusId, links, nodeMap])

  const connectedToHover = useMemo(() => {
    if (!hoverNodeId) return new Set<string>()
    const ids = new Set<string>([hoverNodeId])
    for (const l of links) {
      if (l.source === hoverNodeId) ids.add(l.target)
      if (l.target === hoverNodeId) ids.add(l.source)
    }
    return ids
  }, [hoverNodeId, links])

  const paintNode = useCallback(
    (node: GraphNode, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const isFocus = node.id === (centerId ?? focusId)
      const isSelected = node.id === selectedId
      const isPhone = node.type === 'phone'
      const isBridge = node.metadata?.bridge === 'true'
      const dimmed = hoverNodeId && !connectedToHover.has(node.id)
      const baseSize = isFocus ? 18 : isPhone ? 9 : 11
      const color = isBridge ? '#c4a35a' : ROLE_COLORS[node.role ?? 'associate'] ?? '#4a90d9'

      if (dimmed) ctx.globalAlpha = 0.25
      else ctx.globalAlpha = 1

      if (isFocus) {
        ctx.beginPath()
        ctx.arc(node.x!, node.y!, baseSize + 10, 0, 2 * Math.PI)
        ctx.fillStyle = 'rgba(232, 93, 76, 0.12)'
        ctx.fill()
        ctx.strokeStyle = 'rgba(232, 93, 76, 0.5)'
        ctx.lineWidth = 2.5 / globalScale
        ctx.stroke()
      }

      ctx.beginPath()
      if (isPhone) {
        const s = baseSize
        ctx.moveTo(node.x!, node.y! - s)
        ctx.lineTo(node.x! + s, node.y!)
        ctx.lineTo(node.x!, node.y! + s)
        ctx.lineTo(node.x! - s, node.y!)
        ctx.closePath()
        ctx.fillStyle = isBridge ? '#e8c468' : '#c4a35a'
      } else {
        ctx.arc(node.x!, node.y!, baseSize, 0, 2 * Math.PI)
        ctx.fillStyle = isSelected ? '#d9a441' : highlightedIds.has(node.id) ? '#e8edf4' : color
      }
      ctx.fill()

      ctx.strokeStyle = isSelected ? '#d9a441' : isFocus ? '#ffb4a8' : '#1e2a3a'
      ctx.lineWidth = (isFocus || isSelected ? 2.5 : 1.2) / globalScale
      ctx.stroke()

      const label = node.label.length > 22 ? `${node.label.slice(0, 20)}…` : node.label
      const fontSize = Math.max(10, 12 / globalScale)
      ctx.font = `600 ${fontSize}px IBM Plex Sans, sans-serif`
      ctx.fillStyle = isFocus ? '#ffe8e4' : '#c8d4e0'
      ctx.textAlign = 'center'
      ctx.fillText(label, node.x!, node.y! + baseSize + 14 / globalScale)

      if (node.role && !isPhone) {
        ctx.font = `500 ${Math.max(8, 9 / globalScale)}px IBM Plex Sans, sans-serif`
        ctx.fillStyle = isFocus ? '#ffb4a8' : '#7a8fa3'
        const city = node.metadata?.city ? ` · ${node.metadata.city}` : ''
        ctx.fillText(`${ROLE_LABELS[node.role] ?? node.role}${city}`, node.x!, node.y! + baseSize + 26 / globalScale)
      } else if (isPhone && isBridge) {
        ctx.font = `500 ${Math.max(8, 9 / globalScale)}px IBM Plex Sans, sans-serif`
        ctx.fillStyle = '#c4a35a'
        ctx.fillText('Shared number', node.x!, node.y! + baseSize + 18 / globalScale)
      }

      ctx.globalAlpha = 1
    },
    [selectedId, highlightedIds, centerId, focusId, hoverNodeId, connectedToHover],
  )

  const paintLink = useCallback(
    (link: GraphLinkObj, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const source = link.source as GraphNode
      const target = link.target as GraphNode
      if (source.x == null || source.y == null || target.x == null || target.y == null) return

      const weight = link.weight ?? 1
      const linkType = link.link_type ?? 'phone_call'
      const style = LINK_STYLE[linkType] ?? LINK_STYLE.phone_call
      const width = Math.max(1.5, Math.min(9, Math.sqrt(weight) * 1.5))
      const [sourceId, targetId] = linkEndpoints(link)
      const touchesFocus =
        sourceId === (centerId ?? focusId) || targetId === (centerId ?? focusId)
      const isHovered =
        hoverLink &&
        ((hoverLink.source === sourceId && hoverLink.target === targetId) ||
          (hoverLink.source === targetId && hoverLink.target === sourceId))
      const dimmed = hoverNodeId && !connectedToHover.has(sourceId) && !connectedToHover.has(targetId)

      if (dimmed) ctx.globalAlpha = 0.15
      else ctx.globalAlpha = isHovered ? 1 : touchesFocus ? 0.95 : 0.55

      ctx.beginPath()
      ctx.moveTo(source.x, source.y)
      ctx.lineTo(target.x, target.y)
      ctx.strokeStyle = isHovered ? '#ffffff' : style.color
      ctx.lineWidth = (isHovered ? width + 1 : width) / globalScale
      ctx.setLineDash(style.dash.map((d) => d / globalScale))
      ctx.stroke()
      ctx.setLineDash([])

      const midX = (source.x + target.x) / 2
      const midY = (source.y + target.y) / 2
      if (link.label && globalScale > 0.45) {
        const pad = 4 / globalScale
        const text = link.label
        ctx.font = `600 ${Math.max(8, 10 / globalScale)}px IBM Plex Sans, sans-serif`
        const tw = ctx.measureText(text).width
        ctx.fillStyle = 'rgba(10, 14, 21, 0.85)'
        ctx.fillRect(midX - tw / 2 - pad, midY - 8 / globalScale, tw + pad * 2, 14 / globalScale)
        ctx.fillStyle = isHovered ? '#ffffff' : '#b8c9dc'
        ctx.textAlign = 'center'
        ctx.fillText(text, midX, midY + 2 / globalScale)
      }

      ctx.globalAlpha = 1
    },
    [centerId, focusId, hoverLink, hoverNodeId, connectedToHover],
  )

  const legendRoles = useMemo(() => {
    const roles = new Set(nodes.filter((n) => n.type === 'person').map((n) => n.role).filter(Boolean))
    return Array.from(roles) as NonNullable<Entity['role']>[]
  }, [nodes])

  return (
    <div className="flex h-full flex-col">
      <header className="border-b border-console-border px-5 py-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <h1 className="text-base font-semibold text-text-primary">{t.views.network.header}</h1>
            {summary && <p className="mt-1 text-sm leading-relaxed text-text-secondary">{summary}</p>}
          </div>
          {stats && !loading && (
            <div className="flex shrink-0 flex-wrap gap-2 text-xs">
              <span className="rounded border border-console-border bg-console-bg px-2.5 py-1 text-text-secondary">
                {stats.person_count} people
              </span>
              <span className="rounded border border-console-border bg-console-bg px-2.5 py-1 text-text-secondary">
                {stats.link_count} links
              </span>
              {stats.shared_contact_count > 0 && (
                <span className="rounded border border-amber-500/30 bg-amber-500/10 px-2.5 py-1 text-amber-200/90">
                  {stats.shared_contact_count} shared number(s)
                </span>
              )}
            </div>
          )}
        </div>
        <p className="mt-2 text-xs text-text-muted">{t.network.simpleHint}</p>
      </header>

      <div className="flex min-h-0 flex-1">
        <div className="relative min-w-0 flex-1 bg-[#080c12]">
          {loading && (
            <p className="absolute inset-0 z-10 flex items-center justify-center text-sm text-text-muted">
              {t.network.loading}
            </p>
          )}
          {error && (
            <p className="absolute left-4 top-4 z-10 border border-risk-high/40 bg-risk-high/10 px-3 py-2 text-sm text-risk-high">
              {error}
            </p>
          )}
          {!loading && nodes.length > 0 && (
            <ForceGraph2D
              ref={fgRef}
              graphData={graphData}
              nodeId="id"
              linkCanvasObjectMode={() => 'replace'}
              linkCanvasObject={paintLink}
              backgroundColor="#080c12"
              cooldownTicks={140}
              d3AlphaDecay={0.02}
              d3VelocityDecay={0.45}
              enableNodeDrag
              onNodeDragEnd={(node) => {
                node.fx = node.x
                node.fy = node.y
              }}
              onNodeHover={(node) => setHoverNodeId(node?.id ?? null)}
              onLinkHover={(link) => setHoverLink(link ? (link as GraphLinkObj) : null)}
              nodeCanvasObject={paintNode}
              nodePointerAreaPaint={(node, color, ctx) => {
                ctx.fillStyle = color
                ctx.beginPath()
                ctx.arc(node.x!, node.y!, 20, 0, 2 * Math.PI)
                ctx.fill()
              }}
              onNodeClick={(node) => onSelect(node.id!)}
            />
          )}

          {hoverLink?.evidence && (
            <div className="pointer-events-none absolute left-1/2 top-4 z-20 max-w-md -translate-x-1/2 rounded border border-console-border bg-console-panel/95 px-4 py-2 text-center text-xs text-text-secondary shadow-lg">
              <span className="font-semibold text-text-primary">{hoverLink.label}</span>
              <span className="mt-1 block">{hoverLink.evidence}</span>
            </div>
          )}

          {!loading && nodes.length > 0 && (
            <div className="absolute bottom-4 left-4 max-w-sm rounded border border-console-border/80 bg-console-panel/95 px-3 py-2.5 text-[11px]">
              <p className="mb-1.5 font-semibold uppercase tracking-wide text-text-muted">How to read</p>
              <div className="space-y-1 text-text-secondary">
                <p>
                  <span className="inline-block h-2 w-4 rounded-sm bg-[#e85d4c] align-middle" /> Solid red = phone
                  calls (thicker = more calls)
                </p>
                <p>
                  <span className="inline-block h-2 w-4 border border-dashed border-[#c4a35a] align-middle" /> Gold
                  diamond = shared number link
                </p>
                <p>
                  <span className="inline-block h-2 w-4 rounded-full bg-[#e85d4c] align-middle" /> Centre = primary
                  suspect
                </p>
              </div>
              {legendRoles.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-2 border-t border-console-border/50 pt-2">
                  {legendRoles.map((role) => (
                    <span key={role} className="flex items-center gap-1 text-text-muted">
                      <span
                        className="inline-block h-2 w-2 rounded-full"
                        style={{ backgroundColor: ROLE_COLORS[role] }}
                      />
                      {ROLE_LABELS[role]}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <aside className="flex w-80 shrink-0 flex-col border-l border-console-border bg-console-panel/50">
          {focusEntity && (
            <div className="border-b border-console-border px-4 py-4">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-risk-high">
                {t.network.primarySuspect}
              </p>
              <p className="mt-1 text-lg font-semibold text-text-primary">{focusEntity.label}</p>
              <p className="mt-0.5 text-xs text-text-muted">
                {ROLE_LABELS[focusEntity.role ?? 'suspect']}
                {focusEntity.metadata?.city ? ` · ${focusEntity.metadata.city}` : ''}
              </p>
            </div>
          )}

          {connectionStory.length > 0 && (
            <div className="border-b border-console-border px-4 py-3">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-text-muted">
                What this map shows
              </p>
              <ul className="mt-2 space-y-2">
                {connectionStory.map((line, i) => (
                  <li key={i} className="flex gap-2 text-xs leading-relaxed text-text-secondary">
                    <span className="mt-0.5 shrink-0 text-accent-amber">•</span>
                    <span>{line}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="flex-1 overflow-y-auto px-4 py-3">
            {groupedConnections.direct.length > 0 && (
              <>
                <p className="text-[10px] font-semibold uppercase tracking-wider text-text-muted">
                  Calls with suspect
                </p>
                <ul className="mt-2 space-y-2">{groupedConnections.direct.map((l, i) => renderConnectionRow(l, `d-${i}`))}</ul>
              </>
            )}

            {groupedConnections.innerRing.length > 0 && (
              <>
                <p className="mt-4 text-[10px] font-semibold uppercase tracking-wider text-text-muted">
                  Inner ring (associate ↔ associate)
                </p>
                <ul className="mt-2 space-y-2">
                  {groupedConnections.innerRing.map((l, i) => renderConnectionRow(l, `i-${i}`))}
                </ul>
              </>
            )}

            {groupedConnections.shared.length > 0 && (
              <>
                <p className="mt-4 text-[10px] font-semibold uppercase tracking-wider text-amber-200/80">
                  Shared contact numbers
                </p>
                <ul className="mt-2 space-y-2">
                  {groupedConnections.shared.map((l, i) => renderConnectionRow(l, `s-${i}`))}
                </ul>
              </>
            )}

            {links.length === 0 && !loading && (
              <p className="text-sm text-text-muted">{t.network.empty}</p>
            )}

            <p className="mt-4 text-[11px] text-text-muted">{t.network.tapForProfile}</p>
          </div>
        </aside>
      </div>
    </div>
  )
}
