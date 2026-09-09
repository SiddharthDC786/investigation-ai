import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import ForceGraph2D, { type ForceGraphMethods, type LinkObject, type NodeObject } from 'react-force-graph-2d'
import { getCaseGraph } from '../api/graph'
import { CASE_ID } from '../data/mockCase'
import { useLanguage } from '../i18n/LanguageContext'
import type { Entity, GraphLink } from '../types'

interface NetworkGraphViewProps {
  caseId?: string
  selectedId: string | null
  highlightedIds: Set<string>
  onSelect: (id: string) => void
  onEntitiesLoaded?: (entities: Entity[]) => void
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

function asNodeId(value: string | GraphNode): string {
  return typeof value === 'string' ? value : (value.id ?? '')
}

function linkEndpoints(link: GraphLinkObj): [string, string] {
  return [asNodeId(link.source as string | GraphNode), asNodeId(link.target as string | GraphNode)]
}

export function NetworkGraphView({
  caseId = CASE_ID,
  selectedId,
  highlightedIds,
  onSelect,
  onEntitiesLoaded,
}: NetworkGraphViewProps) {
  const { t } = useLanguage()
  const fgRef = useRef<ForceGraphMethods<NodeObject<GraphNode>, LinkObject<GraphNode, GraphLinkObj>> | undefined>(
    undefined,
  )
  const [nodes, setNodes] = useState<Entity[]>([])
  const [links, setLinks] = useState<GraphLink[]>([])
  const [focusId, setFocusId] = useState<string | null>(null)
  const [summary, setSummary] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const centerId = selectedId ?? focusId

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    void getCaseGraph(caseId, selectedId)
      .then((data) => {
        if (cancelled) return
        setNodes(data.nodes)
        setLinks(data.links)
        setFocusId(data.focus_person_id ?? null)
        setSummary(data.summary ?? null)
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
  }, [caseId, selectedId, onEntitiesLoaded])

  const graphData = useMemo(
    () => ({
      nodes: nodes.map((e) => ({ ...e, id: e.id, name: e.label })),
      links: links.map((l) => ({ ...l, weight: l.weight ?? 1 })),
    }),
    [nodes, links],
  )

  const focusEntity = useMemo(
    () => nodes.find((n) => n.id === centerId) ?? nodes.find((n) => n.role === 'suspect'),
    [nodes, centerId],
  )

  const directConnections = useMemo(() => {
    const fid = centerId ?? focusId
    if (!fid) return []
    return links
      .filter((l) => l.source === fid || l.target === fid)
      .map((l) => {
        const otherId = l.source === fid ? l.target : l.source
        const other = nodes.find((n) => n.id === otherId)
        return {
          id: otherId,
          label: other?.label ?? otherId,
          role: other?.role,
          linkLabel: l.label,
          weight: l.weight ?? 1,
          isPhone: other?.type === 'phone',
        }
      })
      .sort((a, b) => b.weight - a.weight)
  }, [links, nodes, centerId, focusId])

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

    const ring = dataNodes.filter((n) => n.id !== anchor)
    ring.forEach((node: GraphNode, index: number) => {
      const angle = (2 * Math.PI * index) / Math.max(ring.length, 1) - Math.PI / 2
      const radius = ring.length <= 4 ? 110 : 140
      node.fx = Math.cos(angle) * radius
      node.fy = Math.sin(angle) * radius
    })

    fgRef.current.d3ReheatSimulation()

    const timer = window.setTimeout(() => {
      fgRef.current?.zoomToFit(450, 80)
    }, 650)
    return () => window.clearTimeout(timer)
  }, [loading, graphData, centerId, focusId])

  const paintNode = useCallback(
    (node: GraphNode, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const isFocus = node.id === (centerId ?? focusId)
      const isSelected = node.id === selectedId
      const isHighlighted = highlightedIds.has(node.id)
      const isPhone = node.type === 'phone'
      const baseSize = isFocus ? 16 : isPhone ? 7 : 10
      const color = ROLE_COLORS[node.role ?? 'associate'] ?? '#4a90d9'

      if (isFocus) {
        ctx.beginPath()
        ctx.arc(node.x!, node.y!, baseSize + 6, 0, 2 * Math.PI)
        ctx.fillStyle = 'rgba(232, 93, 76, 0.15)'
        ctx.fill()
        ctx.strokeStyle = 'rgba(232, 93, 76, 0.55)'
        ctx.lineWidth = 2 / globalScale
        ctx.stroke()
      }

      ctx.beginPath()
      if (isPhone) {
        const s = baseSize * 0.85
        ctx.moveTo(node.x!, node.y! - s)
        ctx.lineTo(node.x! + s, node.y!)
        ctx.lineTo(node.x!, node.y! + s)
        ctx.lineTo(node.x! - s, node.y!)
        ctx.closePath()
        ctx.fillStyle = '#c4a35a'
      } else {
        ctx.arc(node.x!, node.y!, baseSize, 0, 2 * Math.PI)
        ctx.fillStyle = isSelected ? '#d9a441' : isHighlighted ? '#e8edf4' : color
      }
      ctx.fill()

      ctx.strokeStyle = isSelected ? '#d9a441' : isFocus ? '#ffb4a8' : '#1e2a3a'
      ctx.lineWidth = (isFocus || isSelected ? 2.5 : 1.2) / globalScale
      ctx.stroke()

      const label = node.label.length > 20 ? `${node.label.slice(0, 18)}…` : node.label
      const fontSize = Math.max(10, 12 / globalScale)
      ctx.font = `600 ${fontSize}px IBM Plex Sans, sans-serif`
      ctx.fillStyle = isFocus ? '#ffe8e4' : '#c8d4e0'
      ctx.textAlign = 'center'
      ctx.fillText(label, node.x!, node.y! + baseSize + 14 / globalScale)

      if (node.role && !isPhone) {
        ctx.font = `500 ${Math.max(8, 9 / globalScale)}px IBM Plex Sans, sans-serif`
        ctx.fillStyle = isFocus ? '#ffb4a8' : '#7a8fa3'
        ctx.fillText(ROLE_LABELS[node.role] ?? node.role, node.x!, node.y! + baseSize + 26 / globalScale)
      }
    },
    [selectedId, highlightedIds, centerId, focusId],
  )

  const paintLink = useCallback(
    (link: GraphLinkObj, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const source = link.source as GraphNode
      const target = link.target as GraphNode
      if (!source.x || !source.y || !target.x || !target.y) return

      const weight = link.weight ?? 1
      const width = Math.max(1.5, Math.min(8, Math.sqrt(weight) * 1.4))
      const [sourceId, targetId] = linkEndpoints(link)
      const touchesFocus =
        sourceId === (centerId ?? focusId) || targetId === (centerId ?? focusId)

      ctx.beginPath()
      ctx.moveTo(source.x, source.y)
      ctx.lineTo(target.x, target.y)
      ctx.strokeStyle = touchesFocus ? 'rgba(232, 93, 76, 0.75)' : 'rgba(74, 144, 217, 0.45)'
      ctx.lineWidth = width / globalScale
      ctx.stroke()

      const midX = (source.x + target.x) / 2
      const midY = (source.y + target.y) / 2
      const label = link.label
      if (label && globalScale > 0.55) {
        ctx.font = `${Math.max(8, 10 / globalScale)}px IBM Plex Sans, sans-serif`
        ctx.fillStyle = '#9fb3c8'
        ctx.textAlign = 'center'
        ctx.fillText(label, midX, midY - 4 / globalScale)
      }
    },
    [centerId, focusId],
  )

  const legendRoles = useMemo(() => {
    const roles = new Set(nodes.map((n) => n.role).filter(Boolean))
    return Array.from(roles) as NonNullable<Entity['role']>[]
  }, [nodes])

  return (
    <div className="flex h-full flex-col">
      <header className="border-b border-console-border px-5 py-3">
        <h1 className="text-base font-semibold text-text-primary">{t.views.network.header}</h1>
        {summary ? (
          <p className="mt-1 text-sm leading-relaxed text-text-secondary">{summary}</p>
        ) : (
          <p className="mt-1 text-sm text-text-secondary">{t.views.network.description}</p>
        )}
        <p className="mt-2 text-xs text-text-muted">{t.network.simpleHint}</p>
      </header>

      <div className="flex min-h-0 flex-1">
        <div className="relative min-w-0 flex-1 bg-console-bg">
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
              backgroundColor="#0a0e15"
              cooldownTicks={120}
              d3AlphaDecay={0.025}
              d3VelocityDecay={0.4}
              enableNodeDrag
              onNodeDragEnd={(node) => {
                node.fx = node.x
                node.fy = node.y
              }}
              nodeCanvasObject={paintNode}
              nodePointerAreaPaint={(node, color, ctx) => {
                ctx.fillStyle = color
                ctx.beginPath()
                ctx.arc(node.x!, node.y!, 18, 0, 2 * Math.PI)
                ctx.fill()
              }}
              onNodeClick={(node) => onSelect(node.id!)}
            />
          )}
          {!loading && nodes.length === 0 && !error && (
            <p className="absolute inset-0 flex items-center justify-center text-sm text-text-muted">
              {t.network.empty}
            </p>
          )}

          {legendRoles.length > 0 && !loading && (
            <div className="absolute bottom-4 left-4 flex flex-wrap gap-2 rounded border border-console-border/80 bg-console-panel/90 px-3 py-2 text-xs">
              {legendRoles.map((role) => (
                <span key={role} className="flex items-center gap-1.5 text-text-secondary">
                  <span
                    className="inline-block h-2.5 w-2.5 rounded-full"
                    style={{ backgroundColor: ROLE_COLORS[role] ?? '#4a90d9' }}
                  />
                  {ROLE_LABELS[role] ?? role}
                </span>
              ))}
              <span className="w-full text-text-muted">{t.network.lineThickness}</span>
            </div>
          )}
        </div>

        <aside className="flex w-72 shrink-0 flex-col border-l border-console-border bg-console-panel/40">
          {focusEntity && (
            <div className="border-b border-console-border px-4 py-4">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-risk-high">
                {t.network.primarySuspect}
              </p>
              <p className="mt-1 text-base font-semibold text-text-primary">{focusEntity.label}</p>
              {focusEntity.role && (
                <p className="mt-0.5 text-xs capitalize text-text-muted">
                  {ROLE_LABELS[focusEntity.role] ?? focusEntity.role}
                  {focusEntity.subtitle ? ` · ${focusEntity.subtitle.split('·')[0]?.trim()}` : ''}
                </p>
              )}
            </div>
          )}

          <div className="flex-1 overflow-y-auto px-4 py-3">
            <p className="text-[10px] font-semibold uppercase tracking-wider text-text-muted">
              {t.network.directLinks}
            </p>
            {directConnections.length === 0 && !loading && (
              <p className="mt-3 text-sm text-text-muted">{t.network.empty}</p>
            )}
            <ul className="mt-2 space-y-2">
              {directConnections.map((conn) => (
                <li key={conn.id}>
                  <button
                    type="button"
                    onClick={() => onSelect(conn.id)}
                    className="w-full rounded border border-console-border/60 bg-console-bg/50 px-3 py-2 text-left transition hover:border-accent/40 hover:bg-console-bg"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-sm font-medium text-text-primary">{conn.label}</span>
                      <span
                        className="shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium uppercase"
                        style={{
                          backgroundColor: `${ROLE_COLORS[conn.role ?? 'associate'] ?? '#4a90d9'}22`,
                          color: ROLE_COLORS[conn.role ?? 'associate'] ?? '#4a90d9',
                        }}
                      >
                        {conn.isPhone ? t.network.legendPhone : (ROLE_LABELS[conn.role ?? 'associate'] ?? 'Link')}
                      </span>
                    </div>
                    <p className="mt-1 text-xs text-text-muted">{conn.linkLabel}</p>
                  </button>
                </li>
              ))}
            </ul>
            <p className="mt-4 text-xs text-text-muted">{t.network.tapForProfile}</p>
          </div>
        </aside>
      </div>
    </div>
  )
}
