import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { ReactFlow, Background, Controls, Handle, Position, useNodesState, useEdgesState, type Node, type Edge, type NodeProps } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import type { AppData, CompItem, MapGraph, MapNode } from './types'
import { api } from './api'
import { CodeBadge, Icon, ProvTag, StatusPill, STATUS_TEXT, Term } from './ui'
import { AiTag } from './suggest'
import { FIXABLE } from './fields'

const NODE_ICON: Record<string, string> = { complete: 'check', missing: 'alert', uncertain: 'question', needs_professional: 'pro', lookup: 'book' }

function MapNodeView({ data }: NodeProps) {
  const d = data as any
  return (
    <div className={`mnode st-${d.status} ${d.selected ? 'sel' : ''} ${d.big ? 'big' : ''}`}>
      <Handle type="target" position={Position.Left} style={{ opacity: 0 }} />
      <span className="mic"><Icon name={NODE_ICON[d.status] || 'question'} size={14} /></span>
      <span className="mtx"><span className="mlabel">{d.label}</span><span className="mstat">{d.sub ? `${STATUS_TEXT[d.status] || d.status}, ${d.sub}` : STATUS_TEXT[d.status] || d.status}</span></span>
      <Handle type="source" position={Position.Right} style={{ opacity: 0 }} />
    </div>
  )
}
const nodeTypes = { m: MapNodeView }

function layout(g: MapGraph): Record<string, { x: number; y: number }> {
  const kids: Record<string, string[]> = {}
  const hasParent = new Set<string>()
  g.edges.forEach(e => { (kids[e.source] ||= []).push(e.target); hasParent.add(e.target) })
  const roots = g.nodes.filter(n => !hasParent.has(n.id)).map(n => n.id)
  const pos: Record<string, { x: number; y: number }> = {}
  let row = 0
  const GAP = 54, XS = 250
  const place = (id: string, depth: number, seen: Set<string>): number => {
    if (seen.has(id)) return pos[id]?.y ?? 0
    seen.add(id)
    const ch = kids[id] || []
    if (!ch.length) { const y = row * GAP; row++; pos[id] = { x: depth * XS, y }; return y }
    const ys = ch.map(c => place(c, depth + 1, seen))
    const y = (Math.min(...ys) + Math.max(...ys)) / 2
    pos[id] = { x: depth * XS, y }
    return y
  }
  const seen = new Set<string>()
  roots.forEach(r => place(r, 0, seen))
  g.nodes.forEach(n => { if (!pos[n.id]) { pos[n.id] = { x: 0, y: row++ * GAP } } })
  return pos
}

export function MindMap({ graph, selectedId, onSelect }: { graph: MapGraph | null; selectedId: string | null; onSelect: (n: MapNode) => void }) {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([])
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([])
  const [open, setOpen] = useState<Set<string>>(new Set())
  const kids = useMemo(() => {
    const k: Record<string, string[]> = {}
    graph?.edges.forEach(e => { (k[e.source] ||= []).push(e.target) })
    return k
  }, [graph])
  const view = useMemo(() => {
    if (!graph) return null
    const hasParent = new Set(graph.edges.map(e => e.target))
    const roots = graph.nodes.filter(n => !hasParent.has(n.id)).map(n => n.id)
    const vis = new Set<string>()
    const walk = (id: string) => { vis.add(id); if (id.startsWith('root') || roots.includes(id) || open.has(id)) (kids[id] || []).forEach(walk) }
    roots.forEach(walk)
    return { nodes: graph.nodes.filter(n => vis.has(n.id)), edges: graph.edges.filter(e => vis.has(e.source) && vis.has(e.target)) }
  }, [graph, open, kids])
  const pos = useMemo(() => (view ? layout(view) : {}), [view])
  useEffect(() => {
    if (!view) return
    const hasParent = new Set(view.edges.map(e => e.target))
    setNodes(view.nodes.map(n => {
      const nk = kids[n.id]?.length || 0
      const d: any = n.data || {}
      const sub = nk && d.total != null ? `${d.complete ?? 0} of ${d.total} done` : undefined
      return { id: n.id, type: 'm', position: pos[n.id] || { x: 0, y: 0 },
        data: { label: n.label, status: n.status, selected: n.id === selectedId, big: !hasParent.has(n.id), sub, expandable: nk > 0 && hasParent.has(n.id), expanded: open.has(n.id) } }
    }))
    setEdges(view.edges.map(e => ({ id: `${e.source}-${e.target}`, source: e.source, target: e.target, style: { stroke: '#1a1815', strokeWidth: 2 } })))
  }, [view, selectedId, pos, open, kids, setNodes, setEdges])
  const toggle = (id: string) => setOpen(o => { const n = new Set(o); if (n.has(id)) n.delete(id); else n.add(id); return n })
  const expandable = graph ? graph.nodes.filter(n => (kids[n.id]?.length || 0) > 0 && graph.edges.some(e => e.target === n.id)).map(n => n.id) : []
  return (
    <div className="mapwrap" role="group" aria-label="Application mind map. Use the checklist for a keyboard-friendly version.">
      {!graph && <p className="muted pad">Loading the map...</p>}
      <ReactFlow nodes={nodes} edges={edges} nodeTypes={nodeTypes} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
        onNodeClick={(_, n) => { const m = graph?.nodes.find(x => x.id === n.id); if (m) { onSelect(m); if (kids[m.id]?.length) toggle(m.id) } }}
        key={[...open].sort().join('|')} fitView fitViewOptions={{ padding: 0.12, maxZoom: 1.1 }} nodesConnectable={false} nodesDraggable={false} minZoom={0.3} proOptions={{ hideAttribution: true }}>
        <Background color="#cbc7bd" gap={22} />
        <Controls showInteractive={false} />
      </ReactFlow>
      <div className="mapopt">
        <span>Click a section to open it.</span>
        <button type="button" className="linkbtn" onClick={() => setOpen(new Set(open.size ? [] : expandable))}>{open.size ? 'Collapse all' : 'Expand all'}</button>
      </div>
      <ul className="legend" aria-label="Legend">
        {['complete', 'missing', 'uncertain', 'needs_professional', 'lookup'].map(s => <li key={s}><StatusPill status={s} /></li>)}
      </ul>
    </div>
  )
}

/* ---------- code-row helpers ---------- */
export function splitList(s?: string): string[] {
  if (!s) return []
  return s.split(/;\s+(?=[A-Z]{1,3}\d)/).map(x => x.trim()).filter(Boolean)
}
export function stripCode(s: string) { return s.replace(/^[A-Z]{1,3}\d+(\.\d+)*(\s*\([^)]*\))?:\s*/, '') }
export function firstSentences(s: string | undefined, max = 230): string {
  if (!s) return ''
  const t = s.replace(/\s+/g, ' ').trim()
  if (t.length <= max) return t
  const cut = t.slice(0, max)
  const i = Math.max(cut.lastIndexOf('. '), cut.lastIndexOf(', '))
  return (i > 80 ? cut.slice(0, i) : cut.slice(0, cut.lastIndexOf(' '))) + '...'
}

export function Kv({ obj }: { obj: any }) {
  if (obj == null || typeof obj !== 'object') return null
  const entries = Object.entries(obj).filter(([, v]) => v != null && v !== '')
  if (!entries.length) return null
  return (
    <dl className="kv">
      {entries.map(([k, v]) => (
        <div key={k}>
          <dt>{k.replace(/_/g, ' ')}</dt>
          <dd>{typeof v === 'object' ? <Kv obj={v} /> : typeof v === 'boolean' ? (v ? 'Yes' : 'No') : String(v)}</dd>
        </div>
      ))}
    </dl>
  )
}

/** Evidence/details for a selected map node. */
export function NodePanel({ node, app, onClose, children }: { node: MapNode | null; app: AppData; onClose?: () => void; children?: ReactNode }) {
  const [cite, setCite] = useState<any>(null)
  const d = node?.data || {}
  const m = node?.id.match(/^C\.row\.(\d+)$/)
  const row = m ? app.variance.section_c?.[Number(m[1])] : undefined
  const article = d.article || row?.article
  const source = d.source || row?.source
  useEffect(() => { setCite(null) }, [node?.id])
  if (!node) {
    return <div className="empty"><p>Select an item on the checklist or the map to see its evidence here.</p></div>
  }
  const item: CompItem | undefined = app.completeness?.items?.find(i => i.node_id === node.id || i.id === node.id)
  const objs = splitList(row?.objective)
  const funcs = splitList(row?.function)
  return (
    <div className="evidence">
      <div className="ev-head">
        <h3>{node.label}</h3>
        {onClose && <button type="button" className="btn ghost sm" onClick={onClose}>Close</button>}
      </div>
      <p className="ev-status"><StatusPill status={node.status} /> <ProvTag source={node.provenance || undefined} />{FIXABLE[item?.id || node.id] && <AiTag app={app} path={FIXABLE[item?.id || node.id].path} />}</p>
      {item?.message && <p className="ev-why">{item.message}</p>}
      {(row || article) && (
        <div className="ev-code">
          <dl className="kv">
            <div><dt>Article</dt><dd><CodeBadge code={row?.code} /> <strong className="mono">{article || 'Not found'}</strong>{row?.code_edition ? <span className="tag mono ed">{row.code_edition}</span> : null}</dd></div>
            <div><dt>Source</dt><dd>{source?.doc ? `${source.doc}, page ${source.page ?? 'unknown'}` : 'Not recorded'}</dd></div>
            <div><dt>Verified against code text</dt><dd>{(d.verified ?? row?.verified) ? 'Yes' : 'Not yet'}</dd></div>
          </dl>
          {objs.length > 0 && <><h4><Term word="objective">Objectives</Term></h4><ul className="bul">{objs.map((o, i) => <li key={i}>{stripCode(o)}</li>)}</ul></>}
          {funcs.length > 0 && <><h4><Term word="function">Functions</Term></h4><ul className="bul">{funcs.map((o, i) => <li key={i}>{stripCode(o)}</li>)}</ul></>}
          {row?.intent && <><h4><Term word="intent statement">Intent</Term>{row.intent_edition ? <span className="tag mono ed">{row.intent_edition}</span> : null}</h4><p className="clamp">{firstSentences(row.intent, 520)}</p></>}
          {article && (
            <button type="button" className="btn sm" onClick={async () => { try { setCite(await api.verifyCitation(article)) } catch (e) { setCite({ text_excerpt: String(e) }) } }}>
              Check this article in the code text
            </button>
          )}
          {cite && <blockquote className="quote">{cite.exists === false ? 'This article was not found in the code text.' : cite.text_excerpt || 'No excerpt returned.'}</blockquote>}
        </div>
      )}
      {!row && <Kv obj={Object.fromEntries(Object.entries(d).filter(([k]) => k !== 'message'))} />}
      {children}
    </div>
  )
}
