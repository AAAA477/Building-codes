import { useEffect, useState } from 'react'
import { api } from './api'
import type { AfterSubmit, AppData } from './types'
import { OfficerQuestions } from './questions'
import './aftersubmit.css'

const JUR: Record<string, string> = { scc: 'Safety Codes Council form', edmonton: 'City of Edmonton', calgary: 'City of Calgary' }

export function SourceTag({ doc, page, refText }: { doc: string; page: number | string; refText?: string }) {
  return <span className="srctag mono">{doc.replace(/\.pdf$/, '')} · p.{page}{refText ? ` · ${refText}` : ''}</span>
}

export function AfterSubmitPanel({ app, reload }: { app: AppData; reload: () => void }) {
  const [d, setD] = useState<AfterSubmit | null>(null)
  const [err, setErr] = useState('')
  useEffect(() => { setErr(''); api.afterSubmit(app.id).then(setD).catch(e => setErr(e instanceof Error ? e.message : String(e))) }, [app.id, app.jurisdiction])
  return (
    <div className="as">
      <header className="as-head">
        <h1>After you submit</h1>
        <p className="lead">{d?.intro || 'What the official documents say happens once a variance request reaches the authority.'}</p>
        <p className="as-juris">Showing facts for <strong>{JUR[app.jurisdiction] || app.jurisdiction}</strong>. Every line names the document and page it comes from.</p>
      </header>
      {err && <p className="muted" role="alert">{err}</p>}
      {!d && !err && <p className="muted">Loading...</p>}
      {d && (
        <div className="as-grid">
          {d.sections.map(s => (
            <section key={s.id} className="as-sec" aria-labelledby={`as-${s.id}`}>
              <h2 id={`as-${s.id}`}>{s.title}</h2>
              <ul className="as-facts">
                {s.facts.map((f, i) => (
                  <li key={i}><p>{f.text}</p><SourceTag doc={f.source.doc} page={f.source.page} refText={f.source.ref} /></li>
                ))}
              </ul>
              {s.unknown.length > 0 && (
                <div className="as-unk">
                  <h3>{d.unknown_text}</h3>
                  <ul>{s.unknown.map((u, i) => <li key={i}>{u}</li>)}</ul>
                </div>
              )}
            </section>
          ))}
        </div>
      )}
      <OfficerQuestions app={app} reload={reload} />
    </div>
  )
}
