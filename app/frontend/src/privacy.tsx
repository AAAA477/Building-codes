import { useEffect, useState } from 'react'
import './privacy.css'
import { api, setAiHeader } from './api'
import type { AppData, Refusal } from './types'

/** Plain-language statement of what leaves the computer. Kept short on purpose. */
export function AiNotice({ app, setApp }: { app: AppData; setApp: (a: AppData) => void }) {
  const on = app.ai_enabled !== false
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)
  useEffect(() => { setAiHeader(!on) }, [on])
  const flip = async () => {
    setBusy(true); setErr('')
    try { await api.setAiEnabled(app.id, !on); setApp({ ...app, ai_enabled: !on }) }
    catch (e) { setErr(e instanceof Error ? e.message : String(e)) }
    setBusy(false)
  }
  return (
    <section className="ainotice" aria-labelledby="ainotice-h">
      <div className="ainhead">
        <h3 id="ainotice-h">AI help and your information</h3>
        <button type="button" role="switch" aria-checked={on} className={`aiswitch${on ? ' on' : ''}`} disabled={busy} onClick={() => void flip()}>
          <span className="aiknob" aria-hidden="true" />
          <span>{on ? 'AI help is on' : 'AI help is off'}</span>
        </button>
      </div>
      {on ? (
        <ul className="ainlist">
          <li>The text you type for suggestions (such as your project description) and your search questions are sent to a hosted model, Azure OpenAI, so it can draft wording.</li>
          <li>Email addresses, phone numbers, the owner&rsquo;s name and street addresses are removed before anything is sent.</li>
          <li>Please do not type personal information you do not need to. Names and addresses are not needed for suggestions.</li>
        </ul>
      ) : (
        <p className="ainoff">Nothing you type is sent to the hosted model. Suggestions use only the built-in tools, so wording help is unavailable. You can turn it back on at any time.</p>
      )}
      {err && <p className="ainerr" role="alert">{err}</p>}
    </section>
  )
}

/** Standard reply when someone asks whether a design is safe, equivalent, compliant or will be approved. */
export function RefusalNote({ r }: { r?: Refusal | null }) {
  if (!r) return null
  return (
    <div className="refusal" role="note">
      <p><strong>This tool cannot answer that.</strong> {r.message}</p>
      <p className="rwhat">What it can do:</p>
      <ul>{r.can_do.map(c => <li key={c}>{c}</li>)}</ul>
    </div>
  )
}

export function aiFieldLabels(app: AppData, fromServer?: { fields?: { path: string; label: string }[] }): { path: string; label: string }[] {
  if (fromServer?.fields) return fromServer.fields
  return Object.entries(app.provenance || {}).filter(([, v]) => v?.source === 'ai_draft')
    .map(([p]) => ({ path: p, label: p.split('.').slice(-1)[0].replace(/_/g, ' ') }))
}

/** Reviewer-facing disclosure. Always shown, never hidden. */
export function AiFieldsList({ app, info }: { app: AppData; info?: { fields?: { path: string; label: string }[] } }) {
  const fs = aiFieldLabels(app, info)
  return (
    <div className="aifields" role="note">
      <h4>AI assistance</h4>
      {fs.length === 0
        ? <p>No fields were drafted with AI assistance.</p>
        : <>
            <p>These fields were drafted with AI assistance and edited/accepted by the applicant. AI output is a draft.</p>
            <ul>{fs.map(f => <li key={f.path}><span>{f.label}</span> <code>{f.path}</code></li>)}</ul>
          </>}
    </div>
  )
}
