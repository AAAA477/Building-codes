import { useEffect, useRef, useState } from 'react'
import { api } from './api'
import { get } from './fields'
import type { Suggestion, SuggestResponse } from './types'
import type { Ctx } from './page'
import { AiNotice, RefusalNote } from './privacy'
import { Disclaimer, ErrorSlip, FactChip, Rejected, Why, useSuggest } from './suggest'

/** Step 1: What we understood (fact chips) and Improve my wording. Nothing is applied without a click. */
export function Understanding({ ctx, desc, onApplied }: { ctx: Ctx; desc: string; onApplied: (path: string, value: unknown) => void }) {
  const { app, setApp } = ctx
  const s = useSuggest(app.id)
  const [facts, setFacts] = useState<SuggestResponse | null>(null)
  const [improve, setImprove] = useState<SuggestResponse | null>(null)
  const [gone, setGone] = useState<Set<string>>(new Set())
  const [busyId, setBusyId] = useState('')
  const [err, setErr] = useState('')
  const [edit, setEdit] = useState<string | null>(null)
  const last = useRef('')
  const timer = useRef<number | undefined>()

  const check = async (text: string) => {
    last.current = text
    const r = await s.run({ kind: 'extract_facts', text })
    if (r) { setFacts(r); setGone(new Set()) }
  }
  useEffect(() => {
    window.clearTimeout(timer.current)
    const t = desc.trim()
    if (t.length < 25 || t === last.current) return
    timer.current = window.setTimeout(() => { void check(t) }, 1000)
    return () => window.clearTimeout(timer.current)
  }, [desc]) // eslint-disable-line react-hooks/exhaustive-deps

  const accept = async (item: Suggestion, value: unknown) => {
    if (!item.field_path) return
    setBusyId(item.id); setErr('')
    try { setApp(await api.suggestAccept(app.id, { field_path: item.field_path, value, item_id: item.id })); onApplied(item.field_path, value); setGone(g => new Set(g).add(item.id)) }
    catch (e) { setErr(e instanceof Error ? e.message : String(e)) }
    setBusyId('')
  }
  const dismiss = (id: string) => setGone(g => new Set(g).add(id))
  const shown = (facts?.items || []).filter(i => !gone.has(i.id) && i.status !== 'rejected' && i.field_path && String(get(app, i.field_path) ?? '') !== String(i.value ?? ''))
  const rejectedFacts = (facts?.items || []).filter(i => i.status === 'rejected' && !gone.has(i.id))
  const imp = improve?.items.find(i => i.kind === 'text')
  const impUsable = imp && imp.status !== 'rejected' && imp.value
  const ready = desc.trim().length >= 10

  return (
    <section className="aipanel" aria-labelledby="und-h">
      <AiNotice app={app} setApp={setApp} />
      <RefusalNote r={improve?.refusal || facts?.refusal} />
      <h2 id="und-h">What we understood</h2>
      <p className="sub">AI reads your description and proposes values for the form. Nothing is filled in until you accept it.</p>
      <div className="aiact">
        <button type="button" className="btn sm" disabled={!ready || s.busy} onClick={() => void check(desc.trim())}>{s.busy ? 'Checking...' : 'Check my description'}</button>
        <button type="button" className="btn sm" disabled={!ready || s.busy} onClick={async () => { const r = await s.run({ kind: 'improve_text', text: desc.trim(), field_path: 'project.description' }); if (r) { setImprove(r); setEdit(null) } }}>Improve my wording</button>
      </div>
      {s.err && <ErrorSlip>We could not get suggestions just now. {s.err}</ErrorSlip>}
      {err && <ErrorSlip>{err}</ErrorSlip>}
      {facts && shown.length === 0 && rejectedFacts.length === 0 && <p className="sub" role="status">Nothing new to suggest from your words. Everything we found is already filled in, or your description has no figures yet.</p>}
      {shown.length > 0 && <ul className="facts-list" aria-label="Facts we understood">{shown.map(i => <FactChip key={i.id} item={i} busy={busyId === i.id} onAccept={v => void accept(i, v)} onDismiss={() => dismiss(i.id)} />)}</ul>}
      {rejectedFacts.map(i => <Rejected key={i.id} item={i} />)}
      {improve && (
        <div className="improve">
          <h3>Improve my wording</h3>
          {!imp || !impUsable ? (imp ? <Rejected item={imp} /> : <div className="rejected"><strong>We could not produce a reliable suggestion.</strong><span>No rewrite came back.</span></div>) : (
            <>
              <div className="twocol">
                <div><h3>Your text</h3><div className="box">{desc}</div></div>
                <div><h3>Suggested text <span className="draft">Draft</span></h3>
                  {edit === null ? <div className="box sug">{String(imp.value)}</div> : <textarea aria-label="Edit suggested text" value={edit} onChange={e => setEdit(e.target.value)} />}</div>
              </div>
              <div className="aiact">
                <button type="button" className="btn sm primary" disabled={busyId === imp.id} onClick={() => void accept({ ...imp, field_path: imp.field_path || 'project.description' }, edit ?? imp.value).then(() => { setImprove(null); setEdit(null) })}>Accept</button>
                <button type="button" className="btn sm" onClick={() => setEdit(e => (e === null ? String(imp.value) : null))}>{edit === null ? 'Edit' : 'Cancel edit'}</button>
                <button type="button" className="btn sm ghost" onClick={() => { setImprove(null); setEdit(null) }}>Dismiss</button>
              </div>
              <Why item={imp} />
            </>
          )}
        </div>
      )}
      {(facts || improve) && <Disclaimer res={(improve || facts)!} />}
    </section>
  )
}
