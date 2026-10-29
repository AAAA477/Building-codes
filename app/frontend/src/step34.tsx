import { useEffect, useState, type ReactNode } from 'react'
import { api } from './api'
import type { AppData, MapGraph, MapNode, Overlay, SectionDRow } from './types'
import { FIXABLE, nest, toValue } from './fields'
import { Field, Icon, Meter, StatusPill } from './ui'
import { MindMap, NodePanel, firstSentences, splitList, stripCode } from './components'
import { AsideTip, CtaBar, FieldInput, Page, ProfCard, type Ctx } from './page'
import type { Suggestion, SuggestResponse } from './types'
import { EvidenceControl } from './evidence'
import { AiTag, Disclaimer, ErrorSlip, Rejected, Why, useSuggest } from './suggest'

/** A source arrives as text or as {doc, page}; always render text, never an object. */
function srcText(s: unknown): string {
  if (!s) return ''
  if (typeof s === 'string') return s
  const o = s as { doc?: string; page?: number | string }
  return o.doc ? `${o.doc}, page ${o.page ?? '?'}` : ''
}

/* ---------------- Step 3: Fill and review ---------------- */

const SEC_TITLE: Record<string, [string, string]> = {
  A: ['Section A: About you', 'Owner and contact details'],
  B: ['Section B: The project', 'Building facts and location'],
  C: ['Section C: Code and your alternative', 'Articles, and what you propose instead'],
  D: ['Section D: Supporting documents', 'What must be attached to the request'],
  OV: ['Local rules', 'Checks for your authority, answered in the panel below'],
  P: ['Earlier decisions', 'Check whether a similar variance already exists'],
}
const GROUP_TEXT: Record<string, string> = {
  precedent: 'Earlier decisions', citations: 'Code articles', alternative: 'Your alternative', documents: 'Documents', professional: 'Professional',
  admin: 'Details', signature: 'Signatures', jurisdiction: 'Local rules',
}

function FixRow({ id, ctx, go }: { id: string; ctx: Ctx; go: (n: number) => void }) {
  const { app, saveNow } = ctx
  const [open, setOpen] = useState(false)
  const [val, setVal] = useState('')
  const [busy, setBusy] = useState(false)
  const def = FIXABLE[id]
  const apply = async (patch: any) => { setBusy(true); await saveNow(patch); setBusy(false); setOpen(false); setVal('') }
  const sd = app.section_d || []
  let label = 'Fix now'
  let body: ReactNode = null
  if (def) {
    body = (
      <form className="inlinefix" onSubmit={e => { e.preventDefault(); apply(nest(def.path, toValue(def, val))) }}>
        <Field label={def.label} help={def.help} htmlFor={'fx-' + id}><FieldInput f={def} id={'fx-' + id} value={val} onChange={setVal} /></Field>
        <button type="submit" className="btn primary sm" disabled={busy || val === ''}>Save</button>
      </form>
    )
  } else if (id === 'C.mitigations') {
    label = 'Add a feature'
    body = (
      <form className="inlinefix" onSubmit={e => { e.preventDefault(); const ms = app.variance.proposed_alternative?.mitigations || []; apply({ variance: { proposed_alternative: { mitigations: [...ms, { id: 'M' + (ms.length + 1), label: val.trim(), detail: '', evidence_ids: [] }] } } }) }}>
        <Field label="Protective feature in your design" help="For example: fire-rated stair enclosure, or smoke control. One at a time." htmlFor={'fx-' + id}>
          <input id={'fx-' + id} value={val} onChange={e => setVal(e.target.value)} />
        </Field>
        <button type="submit" className="btn primary sm" disabled={busy || !val.trim()}>Add</button>
      </form>
    )
  } else if (id === 'D.professional_named') {
    label = 'Name them'
    body = (
      <form className="inlinefix" onSubmit={e => { e.preventDefault(); apply({ section_d: sd.map(r => r.professional_required ? { ...r, responsible_party: val.trim() } : r) }) }}>
        <Field label="Registered professional or firm" help="The qualified fire protection or life safety code consultant responsible for the analysis." htmlFor={'fx-' + id}>
          <input id={'fx-' + id} value={val} onChange={e => setVal(e.target.value)} />
        </Field>
        <button type="submit" className="btn primary sm" disabled={busy || !val.trim()}>Save</button>
      </form>
    )
  } else if (id === 'D.documents') {
    label = 'Add a document'
    body = (
      <form className="inlinefix" onSubmit={e => { e.preventDefault(); apply({ section_d: [...sd, { id: 'D' + (sd.length + 1), document_name: val.trim(), responsible_party: '', professional_required: false, status: 'to_be_prepared', date: '' }] }) }}>
        <Field label="Document name" help="For example: site plan, or fire protection consultant's report." htmlFor={'fx-' + id}>
          <input id={'fx-' + id} value={val} onChange={e => setVal(e.target.value)} />
        </Field>
        <button type="submit" className="btn primary sm" disabled={busy || !val.trim()}>Add</button>
      </form>
    )
  } else if (id.startsWith('C.') || id.startsWith('P.')) {
    return <button type="button" className="btn sm" onClick={() => go(2)}>Go to Rules</button>
  } else return null
  return (
    <div className="fixwrap">
      {!open && <button type="button" className="btn sm" onClick={() => setOpen(true)}>{label}</button>}
      {open && <>{body}<button type="button" className="linkbtn" onClick={() => setOpen(false)}>Cancel</button></>}
    </div>
  )
}

const FACT_IDS = ['B.occupancy', 'B.new_or_renovation', 'B.storeys', 'B.building_area_m2', 'B.units_per_floor', 'B.sprinklered']
const noStop = (m?: string) => (m || '').replace(/\s*STOP\.?/g, '')

/** The open Section B facts as one inline group with a single save. */
function FactsGroup({ ids, ctx }: { ids: string[]; ctx: Ctx }) {
  const [vals, setVals] = useState<Record<string, string>>({})
  const [busy, setBusy] = useState(false)
  const filled = ids.filter(id => (vals[id] ?? '') !== '')
  const apply = async () => {
    setBusy(true)
    const patch: any = {}
    filled.forEach(id => { const d = FIXABLE[id]; const p = nest(d.path, toValue(d, vals[id])); Object.assign(patch, mergeDeep(patch, p)) })
    await ctx.saveNow(patch); setBusy(false); setVals({})
  }
  return (
    <form className="facts" onSubmit={e => { e.preventDefault(); void apply() }} aria-label="Building facts">
      <h3>Building facts</h3>
      <p className="sub">{ids.length} facts are missing. Fill in what you know; leave the rest for later.</p>
      <div className="fgrid">
        {ids.map(id => { const d = FIXABLE[id]; return (
          <Field key={id} label={d.label} help={d.help} htmlFor={'fg-' + id}><FieldInput f={d} id={'fg-' + id} value={vals[id] ?? ''} onChange={v => setVals(o => ({ ...o, [id]: v }))} /></Field>
        ) })}
      </div>
      <button type="submit" className="btn primary sm" disabled={busy || !filled.length}>{busy ? 'Saving...' : `Save ${filled.length || ''} ${filled.length === 1 ? 'fact' : 'facts'}`}</button>
    </form>
  )
}
function mergeDeep(t: any, s: any) { for (const k of Object.keys(s)) { if (s[k] && typeof s[k] === 'object' && !Array.isArray(s[k])) { t[k] = mergeDeep(t[k] || {}, s[k]) } else t[k] = s[k] } return t }

/** Guidance for one open item, from the missing_info suggestions (loaded once on first click). */
function SuggestRow({ id, ai, ctx, go }: { id: string; ai: { res: SuggestResponse | null; busy: boolean; err: string; load: () => void }; ctx: Ctx; go: (n: number) => void }) {
  const [open, setOpen] = useState(false)
  const item = ai.res?.items.find(i => i.id === 'missing-' + id)
  return (
    <div className="suggrow">
      <button type="button" className="linkbtn" aria-expanded={open} onClick={() => { if (!ai.res && !ai.busy) ai.load(); setOpen(o => !o) }}>{open ? 'Hide suggestion' : 'Suggest'}</button>
      {open && (
        <div className="prompt">
          {ai.busy && !ai.res && <span>Looking for guidance...</span>}
          {ai.err && <span>We could not get a suggestion just now.</span>}
          {ai.res && !item && <span>We have no specific guidance for this item. Use Fix now to fill it in.</span>}
          {item && (
            <>
              <strong>Why we ask</strong>
              <p className="sm">{item.why || 'The reviewer needs this to assess the file.'}</p>
              <FixRow id={id} ctx={ctx} go={go} />
            </>
          )}
        </div>
      )}
    </div>
  )
}

/** Options others have used (mitigations). Checkable cards; adding is the user's own click. */
function Options({ ctx }: { ctx: Ctx }) {
  const { app, saveNow } = ctx
  const s = useSuggest(app.id)
  const [res, setRes] = useState<SuggestResponse | null>(null)
  const [picked, setPicked] = useState<Set<string>>(new Set())
  const have = new Set((app.variance.proposed_alternative?.mitigations || []).map(m => m.label))
  const items = (res?.items || []).filter(i => i.kind === 'option' && i.status !== 'rejected')
  const add = async () => {
    const ms = app.variance.proposed_alternative?.mitigations || []
    const add = items.filter(i => picked.has(i.id) && !have.has(i.label)).map((i, n) => ({ id: 'M' + (ms.length + n + 1), label: i.label, detail: String(i.value ?? ''), evidence_ids: [] as string[] }))
    if (!add.length) return
    await saveNow({ variance: { proposed_alternative: { mitigations: [...ms, ...add] } } })
    setPicked(new Set())
  }
  return (
    <div className="aipanel optpanel">
      <h3>Options others have used</h3>
      <p className="sub">Options others have used. Whether they achieve equivalent performance is for your registered professional.</p>
      {!res && <button type="button" className="btn sm" disabled={s.busy} onClick={async () => { const r = await s.run({ kind: 'mitigations' }); if (r) setRes(r) }}>{s.busy ? 'Looking...' : 'Show options'}</button>}
      {s.err && <ErrorSlip>We could not get options just now. {s.err}</ErrorSlip>}
      {res && !items.length && <p className="sub">We have no options to show for this application.</p>}
      {items.length > 0 && (
        <ul className="optlist">
          {items.map(i => {
            const added = have.has(i.label)
            return (
              <li key={i.id} className={`optcard ${picked.has(i.id) ? 'on' : ''}`}>
                <input id={'opt-' + i.id} type="checkbox" disabled={added} checked={added || picked.has(i.id)} onChange={e => setPicked(p => { const n = new Set(p); if (e.target.checked) n.add(i.id); else n.delete(i.id); return n })} />
                <div>
                  <label htmlFor={'opt-' + i.id}><strong>{i.label}</strong>{added ? ' (already in your list)' : ''}</label>
                  <p className="sm">{String(i.value)}</p>
                  <Why item={i} />
                </div>
              </li>
            )
          })}
        </ul>
      )}
      {items.length > 0 && <button type="button" className="btn sm primary" disabled={!picked.size} onClick={() => void add()}>Add {picked.size || ''} to my protective features</button>}
      {res && <Disclaimer res={res} />}
    </div>
  )
}

/** Jurisdiction checks (Edmonton emergency-services questions, Calgary permit rule). Degrades to nothing when the server has no overlay. */
function JurisdictionPanel({ app }: { app: AppData }) {
  const [ov, setOv] = useState<Overlay | null>(null)
  const [err, setErr] = useState('')
  const jur = app.jurisdiction || 'scc'
  useEffect(() => { setOv(null); api.overlay(app.id, jur).then(setOv).catch(() => setOv(null)) }, [app.id, jur])
  if (!ov || (!ov.sections.length && !ov.questions.length)) return null
  const answer = async (qid: string, a: string) => {
    setErr('')
    setOv(o => o && { ...o, questions: o.questions.map(q => q.id === qid ? { ...q, answer: a } : q) })
    try { await api.overlayAnswer(app.id, qid, a) } catch (e) { setErr(e instanceof Error ? e.message : String(e)) }
  }
  return (
    <section className="blk jpanel" aria-labelledby="jp-h">
      <h2 id="jp-h">Local rules: {ov.label}</h2>
      {ov.note && <p className="sub">{ov.note}</p>}
      {ov.sections.map(s => (
        <div key={s.id} className="jsec">
          <h3>{s.title}</h3>
          <ul className="titems">
            {s.checks.map(c => (
              <li key={c.id} className="titem">
                <div className="tline">
                  <StatusPill status={c.status} />
                  <div className="ttext"><strong>{c.label}</strong>{c.why && <span>{c.why}</span>}{c.source && <span className="src mono">Source: {srcText(c.source)}</span>}</div>
                </div>
              </li>
            ))}
          </ul>
        </div>
      ))}
      {ov.questions.length > 0 && (
        <div className="jsec">
          <h3>Questions for your authority</h3>
          <ul className="qlist">
            {ov.questions.map(q => (
              <li key={q.id}>
                <fieldset>
                  <legend>{q.prompt}</legend>
                  {q.help && <p className="fhelp">{q.help}</p>}
                  <div className="yn" role="radiogroup">
                    {(q.options?.length ? q.options : ['yes', 'no', 'unsure']).map(o => (
                      <label key={o} className="pick"><input type="radio" name={'q-' + q.id} checked={q.answer === o} onChange={() => answer(q.id, o)} /><span>{o.charAt(0).toUpperCase() + o.slice(1)}</span></label>
                    ))}
                  </div>
                  {q.source && <p className="src mono">Source: {srcText(q.source)}</p>}
                </fieldset>
              </li>
            ))}
          </ul>
        </div>
      )}
      {err && <p className="errata" role="alert"><strong>Error</strong><span>{err}</span></p>}
    </section>
  )
}

export function BriefButton({ id }: { id: string }) {
  const [brief, setBrief] = useState<{ title: string; text: string } | null>(null)
  const [msg, setMsg] = useState('')
  const [busy, setBusy] = useState(false)
  const load = async () => { setBusy(true); setMsg(''); try { setBrief(await api.preApplicationBrief(id)) } catch (e) { setMsg(e instanceof Error ? e.message : String(e)) } setBusy(false) }
  return (
    <div className="brief">
      <button type="button" className="btn sm" onClick={load} disabled={busy}>{busy ? 'Preparing...' : 'Pre-application brief'}</button>
      {msg && <p className="errata" role="alert"><strong>Error</strong><span>{msg}</span></p>}
      {brief && (
        <div className="briefbody">
          <h3>{brief.title} <span className="draft">Draft</span></h3>
          <pre>{brief.text}</pre>
          <button type="button" className="linkbtn" onClick={() => setBrief(null)}>Close</button>
        </div>
      )}
    </div>
  )
}

export function Step3({ ctx, go, graph, loadGraph }: { ctx: Ctx; go: (n: number) => void; graph: MapGraph | null; loadGraph: () => void }) {
  const { app, saveNow } = ctx
  const [tab, setTab] = useState<'todo' | 'map'>('todo')
  const [sel, setSel] = useState<MapNode | null>(null)
  useEffect(() => { loadGraph() }, [app.completeness?.percent]) // eslint-disable-line react-hooks/exhaustive-deps
  const items = app.completeness?.items || []
  const body = items.filter(i => i.section !== 'SIGN')
  const done = body.filter(i => i.status === 'complete').length
  const todo = body.filter(i => i.status !== 'complete' && i.status !== 'needs_professional')
  const m = app.completeness?.meters
  const mi = useSuggest(app.id)
  const [miRes, setMiRes] = useState<SuggestResponse | null>(null)
  const ai = { res: miRes, busy: mi.busy, err: mi.err, load: () => { void mi.run({ kind: 'missing_info' }).then(r => { if (r) setMiRes(r) }) } }
  const setDocStatus = (r: SectionDRow, status: SectionDRow['status']) =>
    saveNow({ section_d: app.section_d.map(x => x.id === r.id ? { ...x, status } : x) })

  return (
    <Page title="Fill and review"
      lead={todo.length ? `${todo.length} ${todo.length === 1 ? 'thing needs' : 'things need'} your attention. Fix them here, or leave them and come back.` : 'Everything you can do yourself is filled in. Review the professional items below, then continue.'}>
      <div className="summarybar">
        <div className="meters">
          {m ? (
            <>
              <div><span className="mlab">Administrative details <b className="mono">{m.admin.done}/{m.admin.total}</b></span><Meter done={m.admin.done} total={m.admin.total} label="Administrative details" /></div>
              <div><span className="mlab">Technical content <b className="mono">{m.technical.done}/{m.technical.total}</b></span><Meter done={m.technical.done} total={m.technical.total} label="Technical content" /></div>
            </>
          ) : (
            <div><span className="mlab">Items complete <b className="mono">{done}/{body.length}</b></span><Meter done={done} total={body.length} label="Items complete" /></div>
          )}
        </div>
        <div className="tabs" role="tablist" aria-label="View">
          <button role="tab" id="t-todo" aria-selected={tab === 'todo'} aria-controls="p-todo" onClick={() => setTab('todo')}><Icon name="list" />To-do list</button>
          <button role="tab" id="t-map" aria-selected={tab === 'map'} aria-controls="p-map" onClick={() => setTab('map')}><Icon name="map" />Overview map</button>
        </div>
      </div>
      <ProfCard app={app} />
      {tab === 'todo' && (
        <div id="p-todo" role="tabpanel" aria-labelledby="t-todo" className="todo">
          {(['A', 'B', 'C', 'D', 'OV', 'P'] as const).map(s => {
            const its = body.filter(i => i.section === s)
            if (!its.length) return null
            const open = its.filter(i => i.status !== 'complete' && i.status !== 'needs_professional')
            const proRows = its.filter(i => i.status === 'needs_professional')
            const proDocs = s === 'D' ? proRows.filter(i => /^document/i.test(i.label)) : []
            const proOther = proRows.filter(i => !proDocs.includes(i))
            const ok = its.filter(i => i.status === 'complete')
            const factItems = s === 'B' ? open.filter(i => FACT_IDS.includes(i.id)) : []
            const rows = [...open.filter(i => !factItems.includes(i)), ...proOther]
            const byMsg = new Map<string, typeof rows>()
            rows.forEach(i => { if (i.message) byMsg.set(noStop(i.message), [...(byMsg.get(noStop(i.message)) || []), i]) })
            const repeated = (i: (typeof rows)[number]) => (i.message ? (byMsg.get(noStop(i.message))?.length || 0) >= 3 : false)
            const seenMsg = new Set<string>()
            return (
              <section key={s} className="tsec" aria-labelledby={'ts-' + s}>
                <header>
                  <div><h2 id={'ts-' + s}>{SEC_TITLE[s][0]}</h2><p className="sub">{SEC_TITLE[s][1]}</p></div>
                  <span className={`count2 ${open.length ? '' : 'allok'}`}>{open.length ? `${open.length} to do` : 'All done'}</span>
                </header>
                {factItems.length > 0 && <FactsGroup ids={factItems.map(i => i.id)} ctx={ctx} />}
                <ul className="titems">
                  {rows.map(i => {
                    if (repeated(i)) {
                      const k = noStop(i.message)
                      if (seenMsg.has(k)) return null
                      seenMsg.add(k)
                      const grp = byMsg.get(k)!
                      return (
                        <li key={'g-' + i.id} className="titem">
                          <div className="tline">
                            <StatusPill status={i.status} />
                            <div className="ttext"><strong>{grp.length} items: {k}</strong>
                              <details className="okdet"><summary>Show the {grp.length} items</summary><ul>{grp.map(g => <li key={g.id}>{g.label}</li>)}</ul></details></div>
                            {i.id.startsWith('C.') && <button type="button" className="btn sm" onClick={() => go(2)}>Go to Rules</button>}
                          </div>
                        </li>
                      )
                    }
                    return (
                    <li key={i.id} className="titem">
                      <div className="tline">
                        <StatusPill status={i.status} />
                        <div className="ttext"><strong>{i.label}</strong>{i.message && <span>{noStop(i.message)}</span>}{i.status !== 'needs_professional' && <SuggestRow id={i.id} ai={ai} ctx={ctx} go={go} />}</div>
                        {i.status !== 'needs_professional' && <FixRow id={i.id} ctx={ctx} go={go} />}
                      </div>
                    </li>
                    )
                  })}
                </ul>
                {s === 'C' && <Options ctx={ctx} />}
                {s === 'C' && (app.variance.section_c || []).length > 0 && (
                  <details className="okdet"><summary>{app.variance.section_c!.length} code articles in Section C</summary>
                    <ul className="crows">{app.variance.section_c!.map((r, i) => (
                      <li key={i}><span className="mono">{r.code || 'NBC(AE) 2023'}{r.code_edition ? `, ${r.code_edition}` : ''}</span> <strong className="mono">{r.article}</strong>
                        {r.intent && <span className="sm"> Intent{r.intent_edition ? <span className="tag mono ed">{r.intent_edition}</span> : null}: {firstSentences(r.intent, 150)}</span>}</li>
                    ))}</ul>
                  </details>
                )}
                {s === 'D' && (app.section_d || []).length > 0 && (
                  <div className="docs">
                    <h3>Documents to attach</h3>
                    {proDocs.length > 0 && <p className="pronote">A registered professional will prepare the documents marked below. This tool leaves them for them.</p>}
                    <ul>
                      {app.section_d.map(r => (
                        <li key={r.id}>
                          <div className="dname">{r.document_name}{r.professional_required && <span className="tag pro">Prepared by a professional</span>}</div>
                          <label className="sr" htmlFor={'ds-' + r.id}>Status of {r.document_name.slice(0, 40)}</label>
                          <select id={'ds-' + r.id} value={r.status} onChange={e => setDocStatus(r, e.target.value as any)}>
                            <option value="missing">Missing</option><option value="to_be_prepared">To be prepared</option><option value="provided">Provided</option>
                          </select>
                          <EvidenceControl appId={app.id} row={r} onChange={() => void ctx.reload()} />
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {ok.length > 0 && (
                  <details className="okdet"><summary>{ok.length} completed</summary>
                    <ul>{ok.map(i => <li key={i.id}><StatusPill status="complete" /> {i.label}{FIXABLE[i.id] && <AiTag app={app} path={FIXABLE[i.id].path} />}</li>)}</ul>
                  </details>
                )}
              </section>
            )
          })}
          <JurisdictionPanel app={app} />
          <div className="extras">
            <BriefButton id={app.id} />
          </div>
        </div>
      )}
      {tab === 'map' && (
        <div id="p-map" role="tabpanel" aria-labelledby="t-map" className="mapgrid">
          <MindMap graph={graph} selectedId={sel?.id || null} onSelect={setSel} />
          <div className="mapside"><NodePanel node={sel} app={app} onClose={sel ? () => setSel(null) : undefined} /></div>
        </div>
      )}
      <CtaBar onBack={() => go(2)} hint={todo.length ? `${todo.length} still open. You can submit with gaps, but the reviewer will ask for them.` : 'Nothing left for you to fill in.'}>
        <button type="button" className="btn primary lg" onClick={() => go(4)}>Next: Submit<Icon name="arrow" /></button>
      </CtaBar>
    </Page>
  )
}

/* ---------------- Step 4: Submit ---------------- */

export function FormPreview({ app }: { app: AppData }) {
  const A = app.applicant, P = app.project, L = app.location, V = app.variance
  const v = (x: any) => (x == null || x === '' || (typeof x === 'string' && /^\[.*\]$/.test(x)) ? <em className="blank">Not provided</em> : String(x))
  const yn = (x: any) => (x == null ? v(null) : x ? 'Yes' : 'No')
  return (
    <div className="paper" aria-label="Filled variance form summary">
      <p className="ptitle">Request for Variance (Alternative Solution)</p>
      <h3>Section A. Applicant</h3>
      <dl className="pkv"><div><dt>Owner</dt><dd>{v(A.owner_name)}<AiTag app={app} path="applicant.owner_name" /></dd></div><div><dt>Representative</dt><dd>{v(A.owner_representative)}<AiTag app={app} path="applicant.owner_representative" /></dd></div><div><dt>Mailing address</dt><dd>{v(A.mailing_address)}<AiTag app={app} path="applicant.mailing_address" /></dd></div><div><dt>Email</dt><dd>{v(A.email)}<AiTag app={app} path="applicant.email" /></dd></div><div><dt>Date</dt><dd>{v(A.date_of_request)}</dd></div></dl>
      <h3>Section B. Project and location</h3>
      <dl className="pkv"><div><dt>Description</dt><dd>{v(P.description)}<AiTag app={app} path="project.description" /></dd></div><div><dt>Site address</dt><dd>{v(L.municipal_address)}<AiTag app={app} path="location.municipal_address" /></dd></div><div><dt>Permit number</dt><dd>{v(L.permit_number)}<AiTag app={app} path="location.permit_number" /></dd></div><div><dt>Use</dt><dd>{v(P.occupancy)}<AiTag app={app} path="project.occupancy" /></dd></div><div><dt>Storeys</dt><dd>{v(P.storeys)}<AiTag app={app} path="project.storeys" /></dd></div><div><dt>Area</dt><dd>{P.building_area_m2 ? `${P.building_area_m2} m²` : v(null)}</dd></div><div><dt>Sprinklered</dt><dd>{yn(P.sprinklered)}<AiTag app={app} path="project.sprinklered" /></dd></div></dl>
      <h3>Section C. Code requirements and alternative</h3>
      <dl className="pkv"><div><dt>Code</dt><dd>{v(V.code_or_standard)}</dd></div><div><dt>Acceptable solution</dt><dd>{V.acceptable_solution?.articles?.length ? V.acceptable_solution.articles.join(', ') : v(null)}</dd></div></dl>
      {(V.section_c || []).map((r, i) => (
        <div key={i} className="prow"><strong className="mono">{r.article}</strong> <span className="mono sm">{r.code}{r.code_edition ? `, ${r.code_edition}` : ''}</span>
          <ul className="bul tight">{splitList(r.objective).slice(0, 2).map((o, i) => <li key={i}>{stripCode(o)}</li>)}</ul>
          <span className="muted sm">{r.source?.doc ? `${r.source.doc}, page ${r.source.page ?? '?'}` : ''}</span></div>
      ))}
      <dl className="pkv"><div><dt>Proposed alternative</dt><dd>{v(V.proposed_alternative?.summary)}<AiTag app={app} path="variance.proposed_alternative.summary" /></dd></div></dl>
      {V.proposed_alternative?.mitigations?.length ? <ul className="bul">{V.proposed_alternative.mitigations.map(m => <li key={m.id}>{m.label}</li>)}</ul> : null}
      <h3>Section D. Supporting documents</h3>
      {app.section_d?.length ? <ul className="bul">{app.section_d.map(d => <li key={d.id}>{firstSentences(d.document_name, 120)} <span className="muted">({d.status.replace(/_/g, ' ')})</span></li>)}</ul> : <p><em className="blank">No documents listed</em></p>}
    </div>
  )
}

export function Step4({ ctx, go }: { ctx: Ctx; go: (n: number) => void }) {
  const { app, saveNow } = ctx
  const [view, setView] = useState<'summary' | 'pdf'>('summary')
  const [pkg, setPkg] = useState<any>(null)
  const [pkgUrl, setPkgUrl] = useState('')
  const [busy, setBusy] = useState(false)
  const [note, setNote] = useState('')
  const D = app.declarations
  const repName = String(app.applicant?.owner_representative ?? '').trim()
  const repNamed = repName !== '' && !/^\[.*\]$/.test(repName)
  const gaps = (app.completeness?.items || []).filter(i => i.section !== 'SIGN' && i.status !== 'complete' && i.status !== 'needs_professional').length
  const offline = app.id.startsWith('mock-')
  // Each box is the user's own click. The app never ticks or signs for anyone.
  const tick = (k: keyof AppData['declarations'], v: boolean) => saveNow({ declarations: { [k]: v } })
  const ready = D.privacy_consent && D.equal_or_better_ack && D.owner_signed && (!repNamed || D.rep_signed)
  const prepare = async () => {
    setBusy(true); setNote('')
    try {
      const r = await api.submissionPackage(app.id)
      setPkg(r); if (r instanceof Blob) setPkgUrl(URL.createObjectURL(r))
    } catch (e) { setNote(e instanceof Error ? e.message : String(e)) }
    setBusy(false)
  }
  const Box = ({ k, children }: { k: keyof AppData['declarations']; children: ReactNode }) => (
    <label className="check"><input type="checkbox" checked={!!D[k]} onChange={e => tick(k, e.target.checked)} /><span>{children}</span></label>
  )
  return (
    <Page title="Check, download and submit"
      lead="Check the filled form, download it, then confirm the declarations yourself. We prepare a package; you decide when to send it."
      aside={<AsideTip title="What happens next"><ol className="steps"><li>You download the filled official form.</li><li>You confirm the declarations below.</li><li>We bundle the form, attachments and a draft email.</li><li>You send it to the authority. Nothing is sent for you.</li></ol></AsideTip>}>
      {gaps > 0 && (
        <p className="notice"><strong>{gaps} {gaps === 1 ? 'item is' : 'items are'} still missing.</strong> <button type="button" className="linkbtn" onClick={() => go(3)}>Go back and fix them</button></p>
      )}
      <section className="blk">
        <div className="row between wrap">
          <div><h2>Your form</h2><p className="sub">Scroll to check it, or download the official PDF.</p></div>
          <div className="tabs" role="tablist" aria-label="Preview type">
            <button role="tab" aria-selected={view === 'summary'} onClick={() => setView('summary')}>Readable summary</button>
            <button role="tab" aria-selected={view === 'pdf'} onClick={() => setView('pdf')}>Official PDF</button>
          </div>
        </div>
        {view === 'summary' ? <FormPreview app={app} /> : offline
          ? <p className="notice"><strong>The server is offline, so the PDF is not available.</strong></p>
          : <iframe className="pdfframe" title="Filled official SCC form" src={api.pdfUrl(app.id) + '#toolbar=0&view=FitH'} />}
        <div className="dl">
          {offline ? <button className="btn lg" disabled>Download filled SCC form (PDF)</button>
            : <a className="btn lg" href={api.pdfUrl(app.id)} download="variance-request.pdf"><Icon name="download" />Download filled SCC form (PDF)</a>}
          {!offline && app.jurisdiction === 'calgary' && <a className="btn lg" href={api.calgaryPdfUrl(app.id)} download="calgary-variance-request.pdf"><Icon name="download" />Download Calgary request (PDF)</a>}
          {!offline && <BriefButton id={app.id} />}
        </div>
      </section>
      <section className="blk" aria-labelledby="sign-h">
        <h2 id="sign-h">Confirm and sign</h2>
        <p className="sub">Only you can do this. The tool never ticks these for the owner.</p>
        <div className="checks">
          <Box k="privacy_consent">The owner has read the privacy notice and consents to the use of this information.</Box>
          <Box k="equal_or_better_ack">The owner understands the alternative must be equal to or better than the Code requirement.</Box>
          <Box k="owner_signed">The owner has signed the declarations on the form.</Box>
          {repNamed && <Box k="rep_signed">The owner's representative has signed the declarations on the form.</Box>}
        </div>
        {note && <p className="errata" role="alert"><strong>Error</strong><span>{note}</span></p>}
        {pkg && (
          <div className="pkg" role="status">
            <h3>Your package is ready <span className="draft">Draft</span></h3>
            {pkg instanceof Blob
              ? <p><a className="btn" href={pkgUrl} download="submission-package.zip"><Icon name="download" />Download package (.zip)</a></p>
              : <p>{pkg.subject}</p>}
            <p className="sm">It contains the filled form, your attachments, a cover note and an email draft (submission.eml). Nothing was sent. You review and send it yourself.</p>
          </div>
        )}
      </section>
      <CtaBar onBack={() => go(3)} hint={ready ? 'Ready to prepare the package.' : 'Tick the confirmations above to continue.'}>
        <button type="button" className="btn primary lg" disabled={!ready || busy} onClick={prepare}>{busy ? 'Preparing...' : 'Prepare submission package'}</button>
      </CtaBar>
    </Page>
  )
}
