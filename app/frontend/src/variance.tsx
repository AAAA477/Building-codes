import { useEffect, useState } from 'react'
import { api } from './api'
import type { AppData, ConditionAnswer, StartingPointItem, VarianceItem, VarianceMatch } from './types'
import './variance.css'

const STATE_WORD: Record<VarianceItem['state'], string> = {
  covered: 'May be covered',
  conditional: 'Conditions to meet',
  near_miss: 'Close, but not a match as it stands',
}
const ANSWERS: [ConditionAnswer, string][] = [['yes', 'Yes, we meet it'], ['no', 'No'], ['unsure', 'Not sure']]
const OUTCOME_HEAD: Record<string, string> = {
  covered: 'An issued variance may already cover this',
  conditional: 'An issued variance may cover this, if you meet its conditions',
  near_miss: 'Your situation is close to an issued variance',
  none: 'No earlier decision found',
}

function Starting({ appId, item, onApp }: { appId: string; item: VarianceItem; onApp: (a: AppData) => void }) {
  const [items, setItems] = useState<StartingPointItem[] | null>(null)
  const [done, setDone] = useState<Record<string, boolean>>({})
  const [err, setErr] = useState('')
  const load = async () => { setErr(''); try { setItems((await api.startingPoint(appId, item.number)).items) } catch (e) { setErr(e instanceof Error ? e.message : String(e)) } }
  const accept = async (it: StartingPointItem) => {
    setErr('')
    try { onApp(await api.acceptPrecedent(appId, it)); setDone(d => ({ ...d, [it.id]: true })) } catch (e) { setErr(e instanceof Error ? e.message : String(e)) }
  }
  return (
    <div className="vstart">
      {items === null && <button type="button" className="btn" onClick={load}>Use as a starting point</button>}
      {err && <p className="sm" role="alert">{err}</p>}
      {items !== null && !items.length && <p className="sm muted">Nothing to borrow from this variance that is not already in your application.</p>}
      {items !== null && items.length > 0 && (
        <>
          <p className="sm">These come from {item.number}, not from you. Accept only what fits your project; each one is marked as borrowed.</p>
          <ul className="vstartlist">
            {items.map(it => (
              <li key={it.id}>
                <div><strong>{it.label}</strong>{typeof it.value === 'object' && it.value && 'detail' in (it.value as any) ? <p className="sm">{String((it.value as any).detail)}</p> : null}
                  {it.why && <p className="sm muted">{it.why}</p>}</div>
                <button type="button" className="btn" disabled={!!done[it.id]} onClick={() => accept(it)}>{done[it.id] ? 'Added' : 'Add to my request'}</button>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  )
}

function Card({ appId, item, onItem, onApp }: { appId: string; item: VarianceItem; onItem: (i: VarianceItem) => void; onApp: (a: AppData) => void }) {
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const answer = async (index: number, a: ConditionAnswer) => {
    const next = item.conditions.map(c => ({ index: c.index, answer: (c.index === index ? a : c.answer) as ConditionAnswer | 'unanswered' }))
      .filter((c): c is { index: number; answer: ConditionAnswer } => c.answer !== 'unanswered')
    setBusy(true); setErr('')
    try { onItem(await api.putReliedOn(appId, item.number, next)) } catch (e) { setErr(e instanceof Error ? e.message : String(e)) }
    setBusy(false)
  }
  const unmet = item.gaps.length
  return (
    <article className={`vcard vs-${item.state}`} aria-labelledby={`v-${item.number}`}>
      <div className="vhead">
        <span className="tag">{STATE_WORD[item.state]}</span>
        <h3 id={`v-${item.number}`}>STANDATA {item.number}: {item.title}</h3>
      </div>
      <p className="sm mono">{item.edition} · issued {item.date_issued} · {item.source.doc.replace(/\.pdf$/i, '')}, page {item.source.page}</p>
      {item.earlier_edition && <p className="notice sm">Issued under an earlier code edition ({item.edition}). Confirm with your authority that it still applies.</p>}
      <p className="sm">{item.reason}</p>
      {item.conditions.length > 0 ? (
        <fieldset className="vconds" disabled={busy}>
          <legend>Conditions in this variance. Tell us which you can meet.</legend>
          {item.conditions.map(c => (
            <div key={c.index} className={`vcond ans-${c.answer}`}>
              <p><span className="mono">{c.label}.</span> {c.text} <span className="sm muted">(page {c.page})</span></p>
              <div role="radiogroup" aria-label={`Condition ${c.label}`} className="vans">
                {ANSWERS.map(([v, w]) => (
                  <label key={v}><input type="radio" name={`${item.number}-${c.index}`} checked={c.answer === v} onChange={() => answer(c.index, v)} /> {w}</label>
                ))}
              </div>
            </div>
          ))}
        </fieldset>
      ) : (
        <p className="sm">This variance does not list numbered conditions. Read it in full before you rely on it.{item.variance_text ? ` It says: ${item.variance_text.slice(0, 400)}${item.variance_text.length > 400 ? '...' : ''}` : ''}</p>
      )}
      {err && <p className="sm" role="alert">{err}</p>}
      <div className={`vmsg ${unmet ? 'gap' : ''}`} role="status" aria-live="polite">
        {item.state !== 'covered' && unmet > 0 && item.conditions.length > 0 && (
          <>
            <strong>{unmet} of {item.conditions.length} conditions not confirmed.</strong>
            <ul>{item.gaps.map(g => <li key={g.index}><span className="mono">{g.label}.</span> {g.answer === 'no' ? 'You said no.' : g.answer === 'unsure' ? 'You are not sure.' : 'Not answered yet.'}</li>)}</ul>
          </>
        )}
        <p>{item.message}</p>
      </div>
      {item.state === 'near_miss' && <Starting appId={appId} item={item} onApp={onApp} />}
    </article>
  )
}

export function VarianceOutcomePanel({ appId, desc, onApp }: { appId: string; desc: string; onApp: (a: AppData) => void }) {
  const [res, setRes] = useState<VarianceMatch | null>(null)
  const [fail, setFail] = useState(false)
  useEffect(() => { setRes(null); setFail(false); api.varianceMatch(appId).then(setRes).catch(() => setFail(true)) }, [appId, desc])
  const items = res?.items || []
  const setItem = (i: VarianceItem) => setRes(r => r && ({ ...r, outcome: r.items.map(x => x.number === i.number ? i : x).sort((a, b) => ['covered', 'conditional', 'near_miss'].indexOf(a.state) - ['covered', 'conditional', 'near_miss'].indexOf(b.state))[0]?.state ?? r.outcome, items: r.items.map(x => x.number === i.number ? i : x) }))
  return (
    <details className="prec vpanel" open={items.length > 0} aria-labelledby="var-h">
      <summary>
        <h2 id="var-h">Before you file: may this already be covered?</h2>
        <span className="sm muted">
          {!res && !fail && 'Looking for issued variances...'}
          {fail && 'Not available just now'}
          {res && (items.length ? OUTCOME_HEAD[res.outcome] : OUTCOME_HEAD.none)}
        </span>
        <span className="tog">Show details</span>
      </summary>
      <div className="pbody">
        {fail && <p className="sub">We could not look for issued variances just now. You can continue.</p>}
        {res && !items.length && <p className="sub">{res.note}</p>}
        {items.length > 0 && <p className="sub">We found these by searching the Alberta STANDATA variances. Read each one yourself; the authority having jurisdiction decides whether it applies to your project.</p>}
        {items.map(it => <Card key={it.number} appId={appId} item={it} onItem={setItem} onApp={onApp} />)}
        {res?.note && items.length > 0 && <p className="sm muted">{res.note}</p>}
      </div>
    </details>
  )
}
