import { useCallback, useEffect, useState } from 'react'
import { api } from './api'
import type { AppData, ChangeRow, ChangesView, OfficerQuestion, QStatus, QuestionsView } from './types'
import './aftersubmit.css'

const STATUS_TEXT: Record<QStatus, string> = { open: 'Open', answered: 'Answered', needs_professional: 'Needs a professional' }
const SECS: [string, string][] = [['', 'No particular section'], ['A', 'A  Applicant'], ['B', 'B  Project'], ['C', 'C  Code'], ['D', 'D  Documents'], ['SIGN', 'Signatures']]

const show = (v: unknown): string => {
  if (v === null || v === undefined || v === '') return '(blank)'
  if (Array.isArray(v)) return v.length ? v.join(', ') : '(none)'
  return String(v)
}
const when = (iso?: string | null) => { if (!iso) return ''; const d = new Date(iso); return isNaN(+d) ? iso : d.toLocaleString('en-CA', { dateStyle: 'medium', timeStyle: 'short' }) }

export function ChangesList({ ch }: { ch: ChangesView | null }) {
  if (!ch) return null
  if (!ch.has_snapshot) return <p className="muted sm">Not marked as submitted yet, so there is nothing to compare against.</p>
  return (
    <div className="qchanges">
      <p className="sm muted">Compared with {when(ch.marked_at)}, when it was marked as submitted. {ch.changes.length === 0 ? 'No tracked fields differ.' : `${ch.changes.length} ${ch.changes.length === 1 ? 'field differs' : 'fields differ'}.`}</p>
      {ch.changes.length > 0 && (
        <table className="qdiff">
          <thead><tr><th scope="col">Field</th><th scope="col">Before</th><th scope="col">Now</th></tr></thead>
          <tbody>
            {ch.changes.map((c: ChangeRow) => (
              <tr key={c.path}><th scope="row" className="mono">{c.path}</th><td>{show(c.old)}</td><td>{show(c.new)}</td></tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

function QItem({ q, appId, onView, busy }: { q: OfficerQuestion; appId: string; onView: (v: QuestionsView) => void; busy: boolean }) {
  const [ans, setAns] = useState(q.answer)
  useEffect(() => setAns(q.answer), [q.answer])
  const patch = async (body: { answer?: string; status?: string }) => { onView(await api.patchQuestion(appId, q.id, body)) }
  return (
    <li className={`qitem q-${q.status}`}>
      <div className="qtop">
        <p className="qtext">{q.text}</p>
        <span className={`qstat qs-${q.status}`}>{STATUS_TEXT[q.status]}</span>
      </div>
      {q.link?.section && <p className="qlink sm muted">Linked to section {q.link.section}{q.link.field ? `, ${q.link.field}` : ''}</p>}
      <div className="field">
        <label htmlFor={`qa-${q.id}`}>Your answer</label>
        <textarea id={`qa-${q.id}`} value={ans} rows={3} onChange={e => setAns(e.target.value)} onBlur={() => { if (ans !== q.answer) void patch({ answer: ans }) }} placeholder="Write your answer here. You send it to the officer yourself." />
      </div>
      <div className="qact">
        <label className="qsel">Status
          <select value={q.status} disabled={busy} onChange={e => void patch({ answer: ans, status: e.target.value })}>
            {(Object.keys(STATUS_TEXT) as QStatus[]).map(s => <option key={s} value={s}>{STATUS_TEXT[s]}</option>)}
          </select>
        </label>
        <button type="button" className="btn ghost sm" onClick={async () => onView(await api.deleteQuestion(appId, q.id))}>Remove</button>
      </div>
    </li>
  )
}

export function OfficerQuestions({ app, reload }: { app: AppData; reload: () => void }) {
  const [v, setV] = useState<QuestionsView | null>(null)
  const [ch, setCh] = useState<ChangesView | null>(null)
  const [text, setText] = useState('')
  const [sec, setSec] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  const [marked, setMarked] = useState('')
  const loadAll = useCallback(async () => {
    try { setV(await api.questions(app.id)); setCh(await api.changes(app.id)); setErr('') } catch (e) { setErr(e instanceof Error ? e.message : String(e)) }
  }, [app.id])
  useEffect(() => { void loadAll() }, [loadAll])
  const onView = async (nv: QuestionsView) => { setV(nv); reload(); setCh(await api.changes(app.id).catch(() => null)) }
  const add = async () => {
    if (!text.trim()) return
    setBusy(true)
    try { await onView(await api.addQuestions(app.id, text, sec ? { section: sec } : undefined)); setText('') } catch (e) { setErr(e instanceof Error ? e.message : String(e)) }
    setBusy(false)
  }
  const mark = async () => {
    setBusy(true)
    try { const r = await api.markSubmitted(app.id); setMarked(r.note); setCh(await api.changes(app.id)); setV(await api.questions(app.id)) } catch (e) { setErr(e instanceof Error ? e.message : String(e)) }
    setBusy(false)
  }
  const items = v?.items || []
  return (
    <section className="oq" aria-labelledby="oq-h">
      <h2 id="oq-h">Questions from the officer</h2>
      <p className="sub">If the officer emails you questions, paste them here. Each one becomes an item you can answer, hand to your professional, and see counted in your to-do list. This is for tracking; the answers are yours to send.</p>
      {err && <p className="muted" role="alert">{err}</p>}
      <div className="oq-add">
        <div className="field">
          <label htmlFor="oq-text">Paste the officer's questions</label>
          <textarea id="oq-text" rows={4} value={text} onChange={e => setText(e.target.value)} placeholder={'1. Please confirm ...\n2. Provide ...'} />
        </div>
        <div className="oq-row">
          <label className="qsel">Relates to
            <select value={sec} onChange={e => setSec(e.target.value)}>{SECS.map(([k, l]) => <option key={k} value={k}>{l}</option>)}</select>
          </label>
          <button type="button" className="btn" onClick={add} disabled={busy || !text.trim()}>Add as tracked questions</button>
        </div>
      </div>
      {items.length > 0
        ? <ul className="qlist">{items.map(q => <QItem key={q.id} q={q} appId={app.id} onView={nv => void onView(nv)} busy={busy} />)}</ul>
        : <p className="muted sm">No officer questions tracked yet.</p>}

      <h2 id="oq-ch" className="oq-h2">Changes since you last submitted</h2>
      <p className="sub">When you send your application yourself, come back and mark it here. This records a snapshot of key fields so you and the reviewer can see what changed before you send an updated version. Marking it does not send anything.</p>
      <div className="oq-mark">
        <button type="button" className="btn" onClick={mark} disabled={busy}>{ch?.has_snapshot ? 'I sent an updated version: reset the comparison' : 'I have sent my application: mark as submitted'}</button>
        {marked && <span className="sm muted" role="status">{marked}</span>}
      </div>
      <ChangesList ch={ch} />
    </section>
  )
}

/** Read-only view for the reviewer: open questions and changes since the last marked submission. */
export function QuestionsReview({ app }: { app: AppData }) {
  const [v, setV] = useState<QuestionsView | null>(null)
  const [ch, setCh] = useState<ChangesView | null>(null)
  useEffect(() => { api.questions(app.id).then(setV).catch(() => setV(null)); api.changes(app.id).then(setCh).catch(() => setCh(null)) }, [app.id, app.completeness?.percent])
  const open = (v?.items || []).filter(i => i.status !== 'answered')
  if (!v && !ch) return null
  return (
    <section className="oq rvq" aria-labelledby="rq-h">
      <h2 id="rq-h">Officer questions and changes</h2>
      <div className="rvq-cols">
        <div>
          <h3>Open questions ({open.length})</h3>
          {open.length === 0 ? <p className="muted sm">No open officer questions are tracked.</p> : (
            <ul className="qlist compact">
              {open.map(q => (
                <li key={q.id} className={`qitem q-${q.status}`}>
                  <div className="qtop"><p className="qtext">{q.text}</p><span className={`qstat qs-${q.status}`}>{STATUS_TEXT[q.status]}</span></div>
                  {q.answer && <p className="sm"><b>Applicant draft answer:</b> {q.answer}</p>}
                </li>
              ))}
            </ul>
          )}
        </div>
        <div>
          <h3>Changes since last submission</h3>
          <ChangesList ch={ch} />
        </div>
      </div>
    </section>
  )
}
