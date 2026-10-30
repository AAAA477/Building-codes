import { useState } from 'react'
import type { ImportReport } from './types'
import './variance.css'

/** Start screen box: bring in a variance request that was already started elsewhere. */
export function ImportBox({ onImport, busy }: { onImport: (input: { file?: File; text?: string }) => void; busy: boolean }) {
  const [text, setText] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const ready = !!file || text.trim().length > 0
  return (
    <section className="impbox" aria-labelledby="imp-h">
      <h2 id="imp-h">I have already started a request</h2>
      <p className="sub">Upload the official Safety Codes Council variance form (PDF), or paste what you have written. We check what is there and what is missing. We do not send your draft to any AI service.</p>
      <div className="row">
        <label>PDF of the form <input type="file" accept="application/pdf,.pdf" onChange={e => { setFile(e.target.files?.[0] || null) }} /></label>
      </div>
      <label htmlFor="imp-text" className="sm">Or paste your draft</label>
      <textarea id="imp-text" value={text} onChange={e => setText(e.target.value)} disabled={!!file} />
      <div className="row">
        <button type="button" className="btn primary" disabled={!ready || busy} onClick={() => onImport(file ? { file } : { text })}>Check my draft</button>
        {file && <button type="button" className="linkbtn" onClick={() => setFile(null)}>Remove {file.name}</button>}
      </div>
    </section>
  )
}

const SOURCE_WORD: Record<ImportReport['source'], string> = { form: 'the official form', pdf_text: 'the text of your PDF', text: 'the text you pasted' }

/** Shown above step 1 after an import: what was read, what was not, what to re-confirm. */
export function ImportReportBanner({ report, onClose }: { report: ImportReport; onClose: () => void }) {
  return (
    <section className="impreport" aria-labelledby="impr-h">
      <h2 id="impr-h">We read your draft from {SOURCE_WORD[report.source]}</h2>
      <p className="sm">{report.filled.length} part{report.filled.length === 1 ? '' : 's'} of the application were filled from it. Nothing was invented; check each one.</p>
      {report.unverified_citations.length > 0 && (
        <><strong>Code articles we could not find:</strong>
          <ul>{report.unverified_citations.map(c => <li key={c}><span className="mono">{c}</span> is not in the indexed codes. Check the number.</li>)}</ul></>
      )}
      {report.unmapped.length > 0 && (
        <><strong>Found in your file but not placed anywhere:</strong>
          <ul>{report.unmapped.map(u => <li key={u.label}>{u.label}: {u.text}</li>)}</ul></>
      )}
      {report.declarations_seen_ticked.length > 0 && <p className="sm"><strong>Signatures or dates were in the file.</strong> They were not copied. Confirm and sign in this application yourself.</p>}
      {report.warnings.map((w, i) => <p className="sm" key={i}>{w}</p>)}
      <button type="button" className="btn" onClick={onClose}>Got it</button>
    </section>
  )
}
