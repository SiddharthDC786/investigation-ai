import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import ForceGraph2D, { type ForceGraphMethods, type NodeObject } from 'react-force-graph-2d'
import { getCaseGraph } from '../api/graph'
import { isApiConfigured } from '../api/client'
import { CASE_ID, HIDDEN_BRIDGE_PHONE_ID, narrativeTags } from '../data/mockCase'
import { useLanguage } from '../i18n/LanguageContext'
import type { Entity, GraphLink } from '../types'

interface NetworkGraphViewProps {
  caseId?: string
  selectedId: string | null
  highlightedIds: Set<string>
  onSelect: (id: string) => void
  onEntitiesLoaded?: (entities: Entity[]) => void
}

type GraphNode = Entity & { x?: number; y?: number }

const typeColor: Record<Entity['type'], string> = {
  person: '#5b8bb0',
  phone: '#d9a441',
  account: '#7a9e8e',
  address: '#8b7aa8',
}

const roleRing: Partial<Record<NonNullable<Entity['role']>, string>> = {
  suspect: '#9e4a42',
  associate: '#b8893a',
  facilitator: '#5b8bb0',
  witness: '#4a7c59',
  complainant: '#8b7aa8',
  handler: '#9e4a42',
}

export function NetworkGraphView({
  caseId = CASE_ID,
  selectedId,
  highlightedIds,
  onSelect,
  onEntitiesLoaded,
}: NetworkGraphViewProps) {
  const { t } = useLanguage()
  const fgRef = useRef<ForceGraphMethods<NodeObject<GraphNode>> | undefined>(undefined)
  const [nodes, setNodes] = useState<Entity[]>([])
  const [links, setLinks] = useState<GraphLink[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    void getCaseGraph(caseId, selectedId)
      .then((data) => {
        if (cancelled) return
        setNodes(data.nodes)
        setLinks(data.links)
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

  const bridgeIds = useMemo(() => {
    const ids = new Set<string>()
    for (const n of nodes) {
      if (n.type === 'phone' && n.explainability.some((e) => /bridge|prepaid|burner/i.test(e))) {
        ids.add(n.id)
      }
    }
    if (!isApiConfigured()) {
      ;[
        HIDDEN_BRIDGE_PHONE_ID,
        'P00014',
        'P00055',
        'P00089',
        'PH-6749921640',
        'PH-7788990011',
        'PH-6655443322',
      ].forEach((id) => ids.add(id))
    }
    return ids
  }, [nodes])

  const graphData = useMemo(
    () => ({
      nodes: nodes.map((e) => ({ ...e, id: e.id, name: e.label })),
      links: links.map((l) => ({ ...l })),
    }),
    [nodes, links],
  )

  useEffect(() => {
    if (loading || nodes.length === 0) return
    const timer = window.setTimeout(() => {
      fgRef.current?.zoomToFit(400, 40)
    }, 600)
    return () => window.clearTimeout(timer)
  }, [loading, nodes, links])

  const paintNode = useCallback(
    (node: GraphNode, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const isBridge = bridgeIds.has(node.id)
      const size = isBridge ? 9 : node.type === 'person' ? 7 : node.type === 'account' ? 6 : 5
      const isSelected = node.id === selectedId
      const isHighlighted = highlightedIds.has(node.id) || isBridge
      const color = isBridge ? '#c45c5c' : typeColor[node.type]

      ctx.beginPath()
      if (node.type === 'account') {
        ctx.rect(node.x! - size, node.y! - size, size * 2, size * 2)
      } else if (node.type === 'address') {
        ctx.moveTo(node.x!, node.y! - size)
        ctx.lineTo(node.x! + size, node.y!)
        ctx.lineTo(node.x!, node.y! + size)
        ctx.lineTo(node.x! - size, node.y!)
        ctx.closePath()
      } else {
        ctx.arc(node.x!, node.y!, size, 0, 2 * Math.PI)
      }
      ctx.fillStyle = isSelected ? '#d9a441' : isHighlighted ? '#e8edf4' : color
      ctx.fill()

      if (isBridge) {
        ctx.strokeStyle = '#e87878'
        ctx.lineWidth = 2.5 / globalScale
        ctx.stroke()
      } else if (node.role) {
        const ring = roleRing[node.role]
        if (ring) {
          ctx.strokeStyle = ring
          ctx.lineWidth = isSelected ? 2.5 / globalScale : 1.5 / globalScale
          ctx.stroke()
        }
      }

      if (globalScale > 1.2) {
        ctx.font = `${10 / globalScale}px IBM Plex Mono, monospace`
        ctx.fillStyle = isBridge ? '#e87878' : '#8fa3b8'
        ctx.fillText(isBridge ? 'BRIDGE' : node.id, node.x! + size + 2, node.y! + 3)
      }
    },
    [selectedId, highlightedIds, bridgeIds],
  )

  const showBridgeBanner = !isApiConfigured() || bridgeIds.size > 0

  return (
    <div className="flex h-full flex-col">
      <header className="border-b border-console-border px-5 py-3">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-base font-semibold text-text-primary">{t.views.network.header}</h1>
              <span className="border border-accent-steel/30 bg-accent-steel/10 px-2 py-0.5 text-[10px] text-accent-steel">
                {isApiConfigured() ? 'Live graph' : narrativeTags.network}
              </span>
            </div>
            <p className="mt-1 text-sm text-text-secondary">{t.views.network.description}</p>
          </div>
          <div className="hidden flex-wrap gap-3 text-xs text-text-muted md:flex">
            <span>
              <span className="mr-1 inline-block h-2.5 w-2.5 rounded-full bg-node-person" />
              {t.network.legendPerson}
            </span>
            <span>
              <span className="mr-1 inline-block h-2.5 w-2.5 bg-node-phone" />
              {t.network.legendPhone}
            </span>
            <span>
              <span className="mr-1 inline-block h-2.5 w-2.5 bg-node-account" />
              {t.network.legendBank}
            </span>
            <span className="text-accent-amber">{t.network.legendRing}</span>
          </div>
        </div>
        {showBridgeBanner && (
          <div className="mt-3 border border-risk-high/40 bg-risk-high/10 px-3 py-2">
            <p className="text-sm text-text-primary">{t.network.bridgeCallout}</p>
            <p className="mt-1 text-xs text-text-muted">{t.network.bridgeTap}</p>
          </div>
        )}
      </header>
      <div className="relative flex-1 bg-console-bg">
        {loading && (
          <p className="absolute inset-0 z-10 flex items-center justify-center text-sm text-text-muted">
            Loading connection map…
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
            linkLabel="label"
            linkColor={(link) => {
              const src = typeof link.source === 'object' ? (link.source as GraphNode).id : link.source
              const tgt = typeof link.target === 'object' ? (link.target as GraphNode).id : link.target
              if (bridgeIds.has(String(src)) || bridgeIds.has(String(tgt))) return '#c45c5c99'
              return '#2a3d5488'
            }}
            linkWidth={(link) => {
              const src = typeof link.source === 'object' ? (link.source as GraphNode).id : link.source
              const tgt = typeof link.target === 'object' ? (link.target as GraphNode).id : link.target
              return bridgeIds.has(String(src)) || bridgeIds.has(String(tgt)) ? 2 : 1
            }}
            linkDirectionalParticles={2}
            linkDirectionalParticleWidth={2}
            linkDirectionalParticleColor={() => '#5b8bb066'}
            backgroundColor="#0a0e15"
            cooldownTicks={120}
            d3AlphaDecay={0.02}
            d3VelocityDecay={0.3}
            nodeCanvasObject={paintNode}
            nodePointerAreaPaint={(node, color, ctx) => {
              const size = 12
              ctx.fillStyle = color
              ctx.beginPath()
              ctx.arc(node.x!, node.y!, size, 0, 2 * Math.PI)
              ctx.fill()
            }}
            onNodeClick={(node) => onSelect(node.id!)}
          />
        )}
      </div>
    </div>
  )
}
