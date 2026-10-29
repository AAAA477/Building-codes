import { useCallback, useEffect, useRef, useState } from 'react'
import { api, ApiError } from './api'
import type { AppData, MapGraph, Precedent, PrecedentResult, SectionCRow } from './types'
import { BUILDING, PEOPLE, mergeInto, nest, readField, toValue, type FieldDef } from './fields'
import { CODE_FILTERS, CodeBadge, Field, Icon, ProvTag, STEPS, Term, clean } from './ui'
import { firstSentences, splitList, stripCode } from './components'
import { Binder, type Hue, type TabDef } from './rail'
import { AfterSubmitPanel } from './aftersubmit'
import { AsideTip, CtaBar, FieldInput, JURISDICTIONS, Page, type Ctx, type SaveState } from './page'
import { Step3, Step4, FormPreview } from './step34'
import { Understanding } from './understand'
import { RefusalNote } from './privacy'

export type { Ctx, SaveState }
export { FormPreview }

/** Debounced autosave: patches are merged and sent together. The backend persists every PATCH. */
export function useAutosave(app: AppData | null, setApp: (a: AppData) => void, setState: (s: SaveState) => void) {
  const pending = useRef<any>({})
  const timer = useRef<number | undefined>()
  const id = app?.id
  const run = useCallback(async () => {
    if (!id || !Object.keys(pending.current).length) return
    const body = pending.current; pending.current = {}
    setState('saving')
    try { setApp(await api.patch(id, body)); setState('saved') } catch { setState('error') }
  }, [id, setApp, setState])
  const save = useCallback((patch: any) => {
    mergeInto(pending.current, patch)
    window.clearTimeout(timer.current)
    timer.current = window.setTimeout(run, 700)
  }, [run])
  const flush = useCallback(async () => { window.clearTimeout(timer.current); await run() }, [run])
  const saveNow = useCallback(async (patch: any) => {
    if (!id) return null
    window.clearTimeout(timer.current)
    mergeInto(pending.current, patch)
    const body = pending.current; pending.current = {}
    setState('saving')
    try { const a = await api.patch(id, body); setApp(a); setState('saved'); return a } catch { setState('error'); return null }
  }, [id, setApp, setState])
  useEffect(() => () => window.clearTimeout(timer.current), [])
  return { save, flush, saveNow }
}

/* ---------------- Step 1: Describe ---------------- */

function Step1({ ctx, go }: { ctx: Ctx; go: (n: number) => void }) {
  const { app, save, saveNow, flush } = ctx
  const all = [...PEOPLE, ...BUILDING]
  const [draft, setDraft] = useState<Record<string, string>>(() => {
    const d: Record<string, string> = { 'project.description': clean(app.project?.description) }
    all.forEach(f => { d[f.path] = readField(app, f) })
    return d
  })
  const set = (f: FieldDef, v: string) => { setDraft(d => ({ ...d, [f.path]: v })); save(nest(f.path, toValue(f, v))) }
  const desc = draft['project.description']
  const ready = desc.trim().length >= 10
  const next = async () => { await flush(); go(2) }
  const render = (list: FieldDef[]) => (
    <div className="fgrid">
      {list.map(f => (
        <Field key={f.path} label={f.label} help={f.help} htmlFor={'f-' + f.path} wide={f.type === 'textarea' || f.path.endsWith('address')}>
          <FieldInput f={f} id={'f-' + f.path} value={draft[f.path] ?? ''} onChange={v => set(f, v)} />
        </Field>
      ))}
    </div>
  )
  const jur = app.jurisdiction || 'scc'
  return (
    <Page title="Tell us what you want to build or do differently"
      lead="Write it the way you would explain it to a neighbour. Nothing here needs code language. We will find the matching code articles next."
      aside={<>
        <AsideTip title="What is a variance?">
          <p>A <Term word="variance" /> is a request to meet the intent of the Building Code in a different way than the prescribed one. A Safety Codes Officer reviews it.</p>
        </AsideTip>
        <AsideTip title="Good to know">
          <ul className="bul"><li>Your answers save automatically.</li><li>Skip anything you do not know. You can return to it in step 3.</li><li>You are never asked to sign until the last step.</li></ul>
        </AsideTip>
      </>}>
      <section className="blk">
        <Field label="What do you want to build or do differently?" htmlFor="f-project.description"
          help="Example: A 5-storey apartment building with one exit stair instead of two, because the lot is narrow.">
          <textarea id="f-project.description" aria-describedby="f-project.description-h" rows={6} value={desc}
            onChange={e => { setDraft(d => ({ ...d, 'project.description': e.target.value })); save({ project: { description: e.target.value } }) }} />
        </Field>
      </section>
      <Understanding ctx={ctx} desc={desc} onApplied={(path, value) => setDraft(d => ({ ...d, [path]: typeof value === 'boolean' ? (value ? 'yes' : 'no') : value == null ? '' : String(value) }))} />
      <fieldset className="blk jur">
        <legend><h2>Who will review it?</h2></legend>
        <p className="sub">This decides which extra checks appear in step 3.</p>
        <div className="jopts" role="radiogroup" aria-label="Jurisdiction">
          {JURISDICTIONS.map(([v, l, d]) => (
            <label key={v} className="jopt">
              <input type="radio" name="jurisdiction" value={v} checked={jur === v} onChange={() => { void saveNow({ jurisdiction: v }) }} />
              <span><strong>{l}</strong><span>{d}</span></span>
            </label>
          ))}
        </div>
      </fieldset>
      <section className="blk">
        <h2>The building</h2>
        <p className="sub">Approximate answers are fine. These help find the right code rules.</p>
        {render(BUILDING)}
      </section>
      <section className="blk">
        <h2>About you</h2>
        <p className="sub">This fills Section A of the official form.</p>
        {render(PEOPLE)}
      </section>
      <CtaBar hint={ready ? undefined : 'Describe your project to continue (at least a sentence).'}>
        <button type="button" className="btn primary lg" disabled={!ready} onClick={next}>Next: Rules<Icon name="arrow" /></button>
      </CtaBar>
    </Page>
  )
}

function TopicPicker({ app, ctx, onChanged }: { app: AppData; ctx: Ctx; onChanged: () => void }) {
  const [topics, setTopics] = useState<{ id: string; label: string; mode: string }[]>([
    { id: 'single_exit_stair', label: 'Single-exit stair (point access block)', mode: 'guided' },
    { id: 'other_nbc', label: 'Any other code requirement', mode: 'lookup' },
  ])
  useEffect(() => { api.topics().then(r => { if (r?.topics?.length) setTopics(r.topics) }).catch(() => { /* keep defaults */ }) }, [])
  const cur = app.variance.topic === 'single_exit_stair' ? 'single_exit_stair' : app.variance.topic ? 'other_nbc' : ''
  const pick = async (id: string) => {
    if (id === cur) return
    await ctx.saveNow({ variance: { topic: id === 'single_exit_stair' ? 'single_exit_stair' : 'other_nbc' } })
    onChanged()
  }
  return (
    <div className="field topicpick">
      <label htmlFor="topic-sel">What kind of variance is this?</label>
      <select id="topic-sel" value={cur} onChange={e => pick(e.target.value)}>
        {cur === '' && <option value="" disabled>Not chosen yet</option>}
        {topics.map(t => <option key={t.id} value={t.id}>{t.label}</option>)}
      </select>
    </div>
  )
}

/* ---------------- Step 2: Rules ---------------- */

const sentence = (t: string) => {
  const letters = t.replace(/[^A-Za-z]/g, '')
  const caps = letters.replace(/[^A-Z]/g, '').length
  if (letters.length > 6 && caps / letters.length > 0.6) { const l = t.toLowerCase(); return l.charAt(0).toUpperCase() + l.slice(1) }
  return t
}
const fileName = (d?: string) => (d ? d.split(/[\\/]/).pop()!.replace(/\.pdf$/i, '').replace(/[_]+/g, ' ') : '')
const citeOf = (p: Precedent) => p.citation || [fileName(p.doc), p.page != null ? `page ${p.page}` : '', p.issue_date].filter(Boolean).join(', ')

function PrecedentPanel({ appId, desc }: { appId: string; desc: string }) {
  const [res, setRes] = useState<PrecedentResult | null>(null)
  const [fail, setFail] = useState(false)
  useEffect(() => { setRes(null); setFail(false); api.precedents(appId).then(setRes).catch(() => setFail(true)) }, [appId, desc])
  const items = res?.coverage === 'possible' ? res.items : []
  return (
    <details className="prec" aria-labelledby="prec-h">
      <summary>
        <h2 id="prec-h">Before you file: may this already be covered?</h2>
        <span className="sm muted">
          {!res && !fail && 'Looking for earlier decisions...'}
          {fail && 'Not available just now'}
          {res && (items.length ? `${items.length} possible ${items.length === 1 ? 'match' : 'matches'}` : 'No earlier decision found')}
        </span>
        <span className="tog">Show details</span>
        {items.length > 0 && (
        <ul className="ptitles" aria-label="Possible matches">{items.slice(0, 2).map(p => <li key={p.id}><span className="tag">{p.source_type.replace(/_/g, ' ')}</span> {sentence(p.title)}</li>)}</ul>
        )}
      </summary>
      <div className="pbody">
        {fail && <p className="sub">We could not look for earlier decisions just now. You can continue.</p>}
        {res && !items.length && <p className="sub">We found no earlier decision that looks like yours. That does not mean none exists; ask your authority if unsure.</p>}
        {items.length > 0 && (
          <>
            <p className="sub">These earlier documents may be related. We found them by search; read each one yourself. This does not confirm that your design is covered.</p>
            <ul className="plist">
              {items.map((p: Precedent) => (
                <li key={p.id} className="pitem">
                  <div className="phead"><span className="tag">{p.source_type.replace(/_/g, ' ')}</span><h3>{sentence(p.title)}</h3></div>
                  {p.quote && <blockquote className="quote">{p.quote_truncated_start ? '... ' : ''}{p.quote}{p.quote_truncated_end ? ' ...' : ''}</blockquote>}
                  <p className="pcite">{citeOf(p)}{!p.citation && p.jurisdiction ? `, ${p.jurisdiction}` : ''}</p>
                  {p.articles_cited?.length ? <p className="sm">Articles cited: <span className="mono">{p.articles_cited.join(', ')}</span></p> : null}
                  {p.why_relevant && <p className="sm">Why it may be related: {p.why_relevant}</p>}
                  {p.legal_status_note && <p className="sm note">Status note: {p.legal_status_note}</p>}
                </li>
              ))}
            </ul>
          </>
        )}
        {res?.note && <p className="sm muted">{res.note}</p>}
      </div>
    </details>
  )
}

interface Hit { code?: string; code_edition?: string; article: string; title?: string; part?: string; pdf_page?: number; snippet?: string; intent_edition?: string; objectives?: string[]; has_attribution?: boolean }

function ArticleCard({ hit, selected, busy, onToggle, verified, provenance }: { hit: Hit; selected: boolean; busy: boolean; onToggle: () => void; verified?: boolean; provenance?: string }) {
  const [more, setMore] = useState(false)
  const objs = hit.objectives || []
  const shown = more ? objs : objs.slice(0, 2)
  const id = 'pick-' + hit.article
  const codeOnly = objs.every(o => /^[A-Z]{1,3}\d[\d.]*$/.test(o))
  return (
    <li className={`acard ${selected ? 'on' : ''}`}>
      <div className="ahead">
        <CodeBadge code={hit.code} />
        <span className="anum mono">{hit.article}</span>
        {hit.code_edition && <span className="tag mono">{hit.code_edition}</span>}
        {hit.title && <h3>{hit.title}</h3>}
        {verified && <span className="pill st-complete"><Icon name="check" size={14} />Verified in code text</span>}
        {provenance === 'ai_draft' && <ProvTag source="ai_draft" />}
      </div>
      {hit.snippet && <p className="reason"><span className="lab">Intent{hit.intent_edition ? <span className="tag mono ed">{hit.intent_edition}</span> : null}</span>{hit.snippet}</p>}
      {objs.length > 0 && (
        <div className="objs">
          <span className="lab"><Term word="objective">What it protects</Term></span>
          {codeOnly
            ? <p className="codes">{objs.map(o => <span key={o} className="tag mono">{o}</span>)}<span className="muted sm"> Objective codes from the code text</span></p>
            : <ul>{shown.map((o, i) => <li key={i}>{stripCode(o)}</li>)}</ul>}
          {objs.length > 2 && !codeOnly && <button type="button" className="linkbtn" onClick={() => setMore(!more)}>{more ? 'Show fewer' : `Show ${objs.length - 2} more`}</button>}
        </div>
      )}
      <div className="afoot">
        <span className="src mono">{`${hit.code || 'NBC(AE) 2023'}${hit.pdf_page ? `, page ${hit.pdf_page}` : ''}${hit.part ? `, Part ${hit.part}` : ''}`}</span>
        <label className="pick" htmlFor={id}>
          <input id={id} type="checkbox" checked={selected} disabled={busy} onChange={onToggle} />
          <span>{selected ? 'Included in my application' : 'Include in my application'}</span>
        </label>
      </div>
    </li>
  )
}

function rowToHit(r: SectionCRow): Hit {
  const objs = splitList(r.objective)
  return { code: r.code, code_edition: r.code_edition, article: r.article || 'unresolved', snippet: firstSentences(r.intent, 170), intent_edition: r.intent_edition, objectives: objs, pdf_page: r.source?.page != null ? Number(r.source.page) : undefined }
}

function Step2({ ctx, go }: { ctx: Ctx; go: (n: number) => void }) {
  const { app, setApp, reload } = ctx
  const rows = app.variance.section_c || []
  const [topic, setTopic] = useState<{ mode?: string; message?: string; topic?: string } | null>(null)
  const [loading, setLoading] = useState(false)
  const [msg, setMsg] = useState('')
  const [refusal, setRefusal] = useState<import('./types').Refusal | null>(null)
  const [noMatch, setNoMatch] = useState<string | null>(null)
  const [q, setQ] = useState('')
  const [hits, setHits] = useState<Hit[] | null>(null)
  const [searching, setSearching] = useState(false)
  const [busy, setBusy] = useState('')
  const started = useRef('')
  const [tick, setTick] = useState(0)

  const [filter, setFilter] = useState('all')
  const filterRef = useRef('all')
  filterRef.current = filter
  const search = useCallback(async (query: string) => {
    if (!query.trim()) return
    setSearching(true); setMsg(''); setNoMatch(null); setRefusal(null)
    try {
      const r = await api.searchArticles(query.trim(), 8, CODE_FILTERS.find(f => f[0] === filterRef.current)?.[2])
      setRefusal(r.refusal || null)
      if (r.no_good_match) { setHits([]); setNoMatch(r.message || '') }
      else {
        setHits(r.results as Hit[])
        if (!r.results.length) setMsg('No articles matched. Try different words, or type an article number such as 3.4.2.1.')
      }
    } catch (e) { setHits(null); setMsg(e instanceof ApiError && e.status === 404 && /latest/.test(e.message) ? e.message : String(e instanceof Error ? e.message : e)) }
    setSearching(false)
  }, [])

  useEffect(() => {
    if (started.current === app.id) return
    started.current = app.id
    ;(async () => {
      setLoading(true)
      let cls: any = null
      try { cls = await api.classify(app.id); setTopic(cls) } catch { /* older backend: fall back below */ }
      const isStair = cls ? cls.topic === 'single_exit_stair' || cls.mode === 'guided' : /stair|exit/i.test(app.project?.description || '') || app.variance.topic === 'single_exit_stair'
      if (!(app.variance.section_c || []).length && isStair) {
        try { await api.generateSectionC(app.id); await reload() } catch (e) { setMsg(String(e)) }
      } else if (!(app.variance.section_c || []).length) {
        const d = clean(app.project?.description)
        if (d) { setQ(d.slice(0, 140)); await search(d.slice(0, 300)) }
      }
      setLoading(false)
    })()
  }, [app.id, tick]) // eslint-disable-line react-hooks/exhaustive-deps

  const toggle = async (hit: Hit) => {
    setBusy(hit.article); setMsg('')
    try {
      const idx = rows.findIndex(r => r.article === hit.article && (!r.code || !hit.code || r.code === hit.code))
      setApp(idx >= 0 ? await api.removeArticle(app.id, idx) : await api.addArticle(app.id, hit.article, hit.code))
    } catch (e) { setMsg(e instanceof Error ? e.message : String(e)) }
    setBusy('')
  }
  const addTyped = async () => {
    const a = q.trim()
    if (!/^\d+(\.\d+)+/.test(a)) return search(a)
    setBusy(a); setMsg('')
    try { setApp(await api.addArticle(app.id, a)); setQ('') } catch (e) { setMsg(e instanceof Error ? e.message : String(e)) }
    setBusy('')
  }
  const extra = (hits || []).filter(h => !rows.some(r => r.article === h.article && (!r.code || !h.code || r.code === h.code)))
  const guided = topic?.mode === 'guided' || topic?.topic === 'single_exit_stair'

  return (
    <Page title="Find the rules that apply"
      lead="These are the Building Code articles your request is measured against. Keep the ones that fit and remove any that do not."
      aside={<>
        <AsideTip title="Why this step?">
          <p>A variance explains how your design meets the <em>purpose</em> of each rule. Each article lists what it protects, taken word for word from the code supplement.</p>
        </AsideTip>
        <AsideTip title="Not sure?"><p>Keep the suggested articles. Your registered professional can adjust the list later.</p></AsideTip>
      </>}>
      <PrecedentPanel appId={app.id} desc={clean(app.project?.description)} />
      {topic?.message && (
        <p className="notice"><Icon name="info" />{guided ? 'We recognised this as a single-exit stair request. The matching articles are already selected for you. Remove any that do not fit.' : topic.message}</p>
      )}
      <section aria-labelledby="sel-h">
        <h2 id="sel-h" className="sec">In your application <span className="count">{rows.length}</span></h2>
        {loading && !rows.length && <p className="muted loadline"><span className="spin" aria-hidden="true" />Looking up the matching articles...</p>}
        {!loading && !rows.length && <div className="empty"><p>No articles selected yet. Search below to add the ones that apply.</p></div>}
        <ul className="alist">
          {rows.map((r, i) => <ArticleCard key={(r.article || '') + i} hit={rowToHit(r)} selected busy={busy === r.article} onToggle={() => toggle(rowToHit(r))} verified={r.verified} provenance={r.provenance} />)}
        </ul>
      </section>
      <section aria-labelledby="add-h" className="addbox">
        <h2 id="add-h" className="sec">Add another article</h2>
        <TopicPicker app={app} ctx={ctx} onChanged={() => { started.current = ''; setTopic(null); setHits(null); setTick(t => t + 1) }} />
        <form className="searchrow" role="search" onSubmit={e => { e.preventDefault(); addTyped() }}>
          <label htmlFor="art-q" className="sr">Search by words or article number</label>
          <input id="art-q" type="search" value={q} placeholder="Search by words, or type an article number like 3.4.2.1" onChange={e => setQ(e.target.value)} />
          <label htmlFor="art-code" className="sr">Search in</label>
          <select id="art-code" className="codesel" value={filter} onChange={e => setFilter(e.target.value)} aria-label="Search in">
            {CODE_FILTERS.map(f => <option key={f[0]} value={f[0]}>{f[0] === 'all' ? 'Search in: All codes' : f[1]}</option>)}
          </select>
          <button type="submit" className="btn" disabled={!q.trim() || searching}><Icon name="search" />{searching ? 'Searching...' : 'Search'}</button>
        </form>
        <RefusalNote r={refusal} />
        {msg && <p className="errata" role="status"><strong>Error</strong><span>{msg}</span></p>}
        {noMatch !== null ? (
          <div className="nomatch" role="status"><strong>We could not find a good match.</strong><span>{noMatch || 'Try other words, or type the article number if you know it.'}</span></div>
        ) : null}
        {hits && extra.length > 0 && (
          <>
            <p className="sub">{extra.length} suggested {extra.length === 1 ? 'article' : 'articles'}, best match first.</p>
            <ul className="alist">{extra.map(h => <ArticleCard key={h.article} hit={h} selected={false} busy={busy === h.article} onToggle={() => toggle(h)} />)}</ul>
          </>
        )}
      </section>
      <CtaBar onBack={() => go(1)} hint={rows.length ? `${rows.length} ${rows.length === 1 ? 'article' : 'articles'} selected` : 'You can continue and add articles later.'}>
        <button type="button" className="btn primary lg" onClick={() => go(3)}>Next: Fill and review<Icon name="arrow" /></button>
      </CtaBar>
    </Page>
  )
}

/* ---------------- container ---------------- */

const HUES: Hue[] = ['orange', 'yellow', 'grass', 'ultra']
const TAB_LABEL = ['Describe', 'Rules', 'Fill and review', 'Submit']

export function Applicant({ ctx, step, go, graph, loadGraph }: { ctx: Ctx; step: number; go: (n: number) => void; graph: MapGraph | null; loadGraph: () => void }) {
  const { app } = ctx
  const hasDesc = clean(app.project?.description).trim().length >= 10
  const maxStep = hasDesc ? 4 : 1
  const goto = (n: number) => { window.scrollTo({ top: 0 }); go(n) }
  const items = (app.completeness?.items || []).filter(i => i.section !== 'SIGN' && i.status !== 'complete' && i.status !== 'needs_professional')
  const D = app.declarations
  const repNamed = clean(app.applicant?.owner_representative).trim() !== ''
  const decl = [D.privacy_consent, D.equal_or_better_ack, D.owner_signed, ...(repNamed ? [D.rep_signed] : [])].filter(v => !v).length
  const open = [
    (hasDesc ? 0 : 1) + items.filter(i => i.section === 'A' || i.section === 'B').length,
    (app.variance.section_c || []).length ? items.filter(i => i.section === 'C' && i.id.startsWith('C.row')).length : 1,
    items.length,
    decl,
  ]
  const tabs: TabDef[] = STEPS.map((s, i) => ({ key: String(s.n), n: String(s.n), label: TAB_LABEL[i], hue: HUES[i], open: open[i], current: step === s.n, disabled: s.n > maxStep && s.n !== step, onClick: () => goto(s.n) }))
  const qOpen = ((app as any).officer_questions?.items || []).filter((q: any) => q.status !== 'answered').length
  tabs.push({ key: '5', n: '5', label: 'After submitting', hue: 'teal', open: qOpen, current: step === 5, disabled: !hasDesc, onClick: () => goto(5) })
  return (
    <Binder hue={step === 5 ? 'teal' : HUES[step - 1]} tabs={tabs} railLabel="Application steps" strip={step === 5 ? <>After submitting · what happens next</> : <>Step {step} of 4 · {TAB_LABEL[step - 1]}</>}>
      {step === 1 && <Step1 key={app.id} ctx={ctx} go={goto} />}
      {step === 2 && <Step2 key={app.id} ctx={ctx} go={goto} />}
      {step === 3 && <Step3 ctx={ctx} go={goto} graph={graph} loadGraph={loadGraph} />}
      {step === 4 && <Step4 ctx={ctx} go={goto} />}
      {step === 5 && <AfterSubmitPanel app={app} reload={() => { void ctx.reload() }} />}
    </Binder>
  )
}
export { STEPS }
