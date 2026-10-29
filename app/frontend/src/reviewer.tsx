import { useEffect, useMemo, useRef, useState } from 'react'
import { api } from './api'
import type { AppData, CompItem, MapGraph, MapNode, Meters, TopIssue } from './types'
import { Icon, Meter, StatusPill } from './ui'
import { MindMap, NodePanel } from './components'
import { AiFieldsList } from './privacy'
import { Binder, type Hue, type TabDef } from './rail'
import { QuestionsReview } from './questions'

const SECTIONS: [string, string, string, Hue][] = [['A', 'A', 'Applicant', 'orange'], ['B', 'B', 'Project', 'yellow'], ['C', 'C', 'Code', 'grass'], ['D', 'D', 'Docs', 'teal'], ['SIGN', 'S', 'Sign', 'violet']]
const GROUP_TEXT: Record<string, string> = {
  precedent: 'Earlier decisions', citations: 'Code articles', alternative: 'Alternative', documents: 'Documents', professional: 'Professional',
  admin: 'Administrative', signature: 'Signatures', jurisdiction: 'Local rules',
}
const groupName = (g?: string) => (g ? GROUP_TEXT[g] || g : 'Other')

function RfiModal({ rfi, onClose }: { rfi: any; onClose: () => void }) {
  const ref = useRef<HTMLDivElement>(null)
  const [copied, setCopied] = useState(false)
  useEffect(() => {
    const prev = document.activeElement as HTMLElement | null
    ref.current?.focus()
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', onKey)
    return () => { document.removeEventListener('keydown', onKey); prev?.focus() }
  }, [onClose])
  const obj = typeof rfi === 'object' && rfi
  const text = obj ? `To: ${rfi.to || ''}\nSubject: ${rfi.subject}\n\n${rfi.body}` : String(rfi)
  const paras = obj && rfi.body ? String(rfi.body).split(/\n{1,}/).filter(Boolean) : [String(rfi)]
  const items: any[] = obj && Array.isArray(rfi.items) ? rfi.items : []
  const grouped = useMemo(() => {
    const m = new Map<string, any[]>()
    items.forEach(i => { const k = i.group || 'other'; m.set(k, [...(m.get(k) || []), i]) })
    return [...m.entries()]
  }, [items])
  return (
    <div className="scrim" onMouseDown={e => { if (e.target === e.currentTarget) onClose() }}>
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby="rfi-h" tabIndex={-1} ref={ref}>
        <header>
          <h2 id="rfi-h">Request for information <span className="draft">Draft</span></h2>
          <button type="button" className="btn sm" onClick={onClose}>Close</button>
        </header>
        <p className="sm">A reviewer must read, edit and send this. It is not sent automatically.</p>
        <div className="email">
          <dl className="ehead">
            <div><dt>To</dt><dd>{obj && rfi.to ? rfi.to : <span className="muted">Applicant (add the address before sending)</span>}</dd></div>
            {obj && rfi.reviewer_recipient_hint && <div><dt>Authority</dt><dd>{rfi.reviewer_recipient_hint}</dd></div>}
            <div><dt>Subject</dt><dd><strong>{obj ? String(rfi.subject).replace(/^DRAFT:\s*/i, '') : 'Request for information'}</strong></dd></div>
          </dl>
          <div className="ebody">
            {paras.filter(p => !/^DRAFT - /.test(p)).map((p, i) => /^(\d+\.|-)/.test(p) ? <p key={i} className="eitem">{p}</p> : <p key={i}>{p}</p>)}
          </div>
          {grouped.length > 0 && (
            <details className="egroups">
              <summary>{items.length} open items by group</summary>
              {grouped.map(([g, its]) => (
                <div key={g}>
                  <h3>{groupName(g)}</h3>
                  <ul>{its.map((i, n) => <li key={i.id ?? n}>{i.code_ref && <span className="tag mono">{i.code_ref}</span>} {i.text || i.label}</li>)}</ul>
                </div>
              ))}
            </details>
          )}
        </div>
        <footer>
          <button type="button" className="btn" onClick={async () => { try { await navigator.clipboard.writeText(text); setCopied(true) } catch { setCopied(false) } }}>{copied ? 'Copied' : 'Copy text'}</button>
          <button type="button" className="btn primary" onClick={onClose}>Done</button>
        </footer>
      </div>
    </div>
  )
}

function profNote(app: AppData): string | null {
  const f = app.professional_flags || []
  if (!f.length) return null
  if (f.some(x => x.stop === true)) return 'A registered professional is required (Edmonton PAB guide p.8)'
  return 'Confirm with the Safety Codes Officer whether a registered professional is required (NBC Division C 2.4.1.1)'
}

export function Reviewer({ app, graph }: { app: AppData; graph: MapGraph | null }) {
  const [summary, setSummary] = useState<any>(null)
  const [rfi, setRfi] = useState<any>(null)
  const [busy, setBusy] = useState(false)
  const [sel, setSel] = useState<MapNode | null>(null)
  useEffect(() => { api.reviewerSummary(app.id).then(setSummary).catch(e => setSummary({ summary: String(e) })) }, [app.id, app.completeness?.percent])

  const items = app.completeness?.items || []
  const total = items.length
  const done = items.filter(i => i.status === 'complete').length
  const gaps = items.filter(i => i.status === 'missing' || i.status === 'uncertain').length
  const openIn = (s: string) => items.filter(i => i.section === s && i.status !== 'complete').length
  const [secSel, setSecSel] = useState<string>(() => SECTIONS.find(s => openIn(s[0]) > 0)?.[0] || 'A')
  const draft = async () => { setBusy(true); try { setRfi(await api.rfiDraft(app.id)) } catch (e) { setRfi(String(e)) } setBusy(false) }
  const pick = (i: CompItem) => { const n = graph?.nodes.find(x => x.id === (i.node_id || i.id)); setSel(n || { id: i.id, label: i.label, status: i.status as any, section: i.section }) }
  const selId = sel?.id
  useEffect(() => { if (location.hash.includes('rfi=1')) void draft() }, [app.id]) // eslint-disable-line react-hooks/exhaustive-deps
  const docs = app.section_d || []
  const headline: string = summary?.headline || app.completeness?.headline || `${gaps} ${gaps === 1 ? 'gap' : 'gaps'} to resolve before this can be reviewed`
  const rawText = typeof summary?.summary === 'string' ? summary.summary : ''
  const hl = headline.trim()
  const text = (rawText.trim().startsWith(hl) ? rawText.trim().slice(hl.length) : rawText).replace(/^[\s.:;,-]+/, '')
  const top: TopIssue[] = (summary?.top_issues?.length ? summary.top_issues : app.completeness?.top_issues) || []
  const meters: Meters | undefined = summary?.meters || app.completeness?.meters
  const pn = profNote(app)

  const tabs: TabDef[] = SECTIONS.map(([k, n, label, hue]) => ({ key: k, n, label, hue, open: openIn(k), current: secSel === k, onClick: () => setSecSel(k) }))
  const cur = SECTIONS.find(s => s[0] === secSel)!
  const its = items.filter(i => i.section === secSel)

  return (
    <Binder hue={cur[3]} tabs={tabs} railLabel="Form sections" wide strip={<>Reviewing · Section {cur[1]} · {cur[2]}</>}>
      <div className="rv">
        <section className="rlead" aria-labelledby="rs-h">
          <div className="rlead-main">
            <h1 id="rs-h">{headline}</h1>
            {top.length > 0 && (
              <ol className="topissues" aria-label="Top issues">
                {top.map(t => (
                  <li key={t.id}>
                    <strong>{t.severity && <span className={`tag ${t.severity}`}>{t.severity === 'blocker' ? 'Blocker' : 'Confirm'}</span>} {t.label}</strong>
                    {t.why && <span>{t.why}</span>}
                    {t.group && <span className="gtag">{groupName(t.group)}</span>}
                  </li>
                ))}
              </ol>
            )}
            {text && <p className="rtext"><span className="draft">Draft summary</span> {text.replace(/\s*STOP\.?/g, '').replace(/\s*Completeness check only.*$/i, '').replace(/\[to be completed by applicant\]/g, 'the applicant')}</p>}
            {pn && <p className="rprof">{pn}</p>}
            <AiFieldsList app={app} info={summary?.ai_assisted} />
          </div>
          <div className="rlead-side">
            <div className="meters stack">
              {meters ? (
                <>
                  <div><span className="mlab">Administrative details <b>{meters.admin.done}/{meters.admin.total}</b></span><Meter done={meters.admin.done} total={meters.admin.total} label="Administrative details" /></div>
                  <div><span className="mlab">Technical content <b>{meters.technical.done}/{meters.technical.total}</b></span><Meter done={meters.technical.done} total={meters.technical.total} label="Technical content" /></div>
                </>
              ) : (
                <div><span className="mlab">Items complete <b>{done}/{total}</b></span><Meter done={done} total={total} label="Items complete" /></div>
              )}
            </div>
            <button type="button" className="btn primary lg" onClick={draft} disabled={busy}><Icon name="mail" />{busy ? 'Drafting...' : 'Draft request for information'}</button>
            <p className="sm muted">Creates an editable email listing open items. Completeness only, not a technical opinion.</p>
          </div>
        </section>
        <QuestionsReview app={app} />
        <div className="panes">
          <section className="pane" aria-labelledby="pc-h">
            <h2 id="pc-h">Checklist: {cur[0] === 'SIGN' ? 'Signatures' : `Section ${cur[0]}`}</h2>
            <div className="pscroll">
              <ul className="clist">
                {its.map(i => (
                  <li key={i.id}>
                    <button type="button" className={`citem ${selId === (i.node_id || i.id) ? 'on' : ''}`} onClick={() => pick(i)} aria-pressed={selId === (i.node_id || i.id)}>
                      <span>{i.label}</span><StatusPill status={i.status} />
                      {i.group && <span className="gtag">{groupName(i.group)}</span>}
                    </button>
                  </li>
                ))}
              </ul>
              {!its.length && <p className="muted pad">No checklist items in this section.</p>}
            </div>
          </section>
          <section className="pane mid" aria-labelledby="pm-h">
            <h2 id="pm-h">Mind map</h2>
            <MindMap graph={graph} selectedId={selId || null} onSelect={setSel} />
          </section>
          <section className="pane" aria-labelledby="pe-h">
            <h2 id="pe-h">Evidence</h2>
            <div className="pscroll">
              <NodePanel node={sel} app={app} />
              <h3 className="dh">Documents ({docs.length})</h3>
              {docs.length
                ? <ul className="dlist">{docs.map(d => <li key={d.id}><span>{d.document_name.length > 120 ? d.document_name.slice(0, 117) + '...' : d.document_name}</span><span className="tag">{d.status.replace(/_/g, ' ')}</span></li>)}</ul>
                : <p className="muted">No documents listed.</p>}
            </div>
          </section>
        </div>
      </div>
      {rfi && <RfiModal rfi={rfi} onClose={() => setRfi(null)} />}
    </Binder>
  )
}
