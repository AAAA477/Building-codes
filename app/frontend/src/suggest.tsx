import { useState, type ReactNode } from 'react'
import type { AppData, Suggestion, SuggestResponse } from './types'
import { api } from './api'
import { Icon } from './ui'

export const DISCLAIMER_FALLBACK = 'AI suggestions are drafts. They can be wrong. Check them against the sources shown. Only a person (and your registered professional where required) can confirm accuracy.'

const STATUS_TEXT: Record<string, string> = { ready: 'Ready to review', needs_review: 'Needs your review', rejected: 'Not reliable' }
const SRC_TEXT: Record<string, string> = { user_text: 'Your words', code: 'Code text', standata: 'STANDATA', policy: 'Policy', advisory: 'Advisory', guide: 'Guide' }

export function AiTag({ app, path }: { app: AppData; path: string }) {
  return app.provenance?.[path]?.source === 'ai_draft' ? <span className="aitag" title="Suggested by AI and accepted by you. Please check it.">AI-assisted</span> : null
}

export function Disclaimer({ res }: { res: Pick<SuggestResponse, 'disclaimer' | 'llm'> }) {
  return (
    <p className="aidisc sm" role="note">
      <strong>Draft.</strong> {res.disclaimer || DISCLAIMER_FALLBACK}
      {res.llm === 'offline' && <> Suggestions are limited because AI is offline.</>}
    </p>
  )
}

/** One reusable disclosure shown on every suggestion. */
export function Why({ item }: { item: Suggestion }) {
  const c = item.checks
  const checks: [boolean, string][] = c ? [
    [c.grounded && (c.unsupported_numbers || []).length === 0, 'Every figure appears in your words or the sources'],
    [c.citations_verified !== false, 'Code articles found in the code text'],
    [!c.claims_safety, 'No safety or approval claims'],
  ] : []
  return (
    <details className="why">
      <summary><span className={`schip s-${item.status}`}>{STATUS_TEXT[item.status] || item.status}</span> Why this suggestion</summary>
      <div className="whybody">
        {item.why && <p className="sm">{item.why}</p>}
        {item.sources?.length > 0 && (
          <ul className="srcs">
            {item.sources.map((s, i) => (
              <li key={i}>
                <span className="tag">{s.type === 'user_text' ? 'Your words' : SRC_TEXT[s.type] || s.type}</span>
                {s.type !== 'user_text' && s.doc && <span className="src"> {s.doc}{Number(s.page) > 0 ? `, page ${s.page}` : ''}{s.article ? `, ${s.article}` : ''}</span>}
                {s.quote && <blockquote className="quote">{s.quote}</blockquote>}
              </li>
            ))}
          </ul>
        )}
        {checks.length > 0 && (
          <ul className="chk" aria-label="Checks">
            {checks.map(([ok, t]) => <li key={t} className={ok ? 'ok' : 'bad'}><Icon name={ok ? 'checkc' : 'alert'} size={16} />{ok ? t : `Not met: ${t}`}</li>)}
            {c?.unsupported_numbers?.length ? <li className="bad"><Icon name="alert" size={16} />Figures not found in the sources: {c.unsupported_numbers.join(', ')}</li> : null}
            {(c?.notes || []).map((n, i) => <li key={i} className="note2">{n}</li>)}
          </ul>
        )}
      </div>
    </details>
  )
}

export function fmtValue(v: unknown): string {
  if (v === true) return 'Yes'
  if (v === false) return 'No'
  if (v == null) return ''
  return String(v)
}

export function Rejected({ item }: { item: Suggestion }) {
  return (
    <div className="rejected" role="status">
      <strong>We could not produce a reliable suggestion.</strong>
      <span>{item.why || (item.checks?.notes || []).join(' ') || 'The result did not pass our checks, so it is not shown.'}</span>
      <Why item={item} />
    </div>
  )
}

/** Fact chip: What we understood. Accept, Edit, Dismiss. Never applied without a click. */
export function FactChip({ item, onAccept, onDismiss, busy }: { item: Suggestion; onAccept: (value: unknown) => void; onDismiss: () => void; busy: boolean }) {
  const [edit, setEdit] = useState(false)
  const [val, setVal] = useState(fmtValue(item.value))
  const quote = item.sources?.find(s => s.type === 'user_text')?.quote
  const coerce = (): unknown => (typeof item.value === 'number' ? (val.trim() === '' ? null : Number(val)) : typeof item.value === 'boolean' ? /^y/i.test(val) : val)
  return (
    <li className="fact">
      <div className="fhead">
        <span className="fval"><b>{item.label}</b>{' '}{edit
          ? <input aria-label={`Edit ${item.label}`} value={val} onChange={e => setVal(e.target.value)} />
          : <span>{fmtValue(item.value)}</span>}</span>
        <span className="fact-act">
          <button type="button" className="btn sm primary" disabled={busy} onClick={() => onAccept(edit ? coerce() : item.value)}>Accept</button>
          <button type="button" className="btn sm" onClick={() => setEdit(e => !e)}>{edit ? 'Cancel edit' : 'Edit'}</button>
          <button type="button" className="btn sm ghost" onClick={onDismiss}>Dismiss</button>
        </span>
      </div>
      {quote && <p className="sm fromyou">From your words: <q>{quote}</q></p>}
      <Why item={item} />
    </li>
  )
}

export function useSuggest(appId: string) {
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const run = async (body: { kind: string; text?: string; field_path?: string }): Promise<SuggestResponse | null> => {
    setBusy(true); setErr('')
    try { return await api.suggest(appId, body) } catch (e) { setErr(e instanceof Error ? e.message : String(e)); return null } finally { setBusy(false) }
  }
  return { run, busy, err }
}

export function ErrorSlip({ children }: { children: ReactNode }) {
  return <p className="errata" role="alert"><strong>Error</strong><span>{children}</span></p>
}
