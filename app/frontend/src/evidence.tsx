import { useEffect, useRef, useState } from 'react'
import { api } from './api'
import type { EvidenceFile, EvidenceFinding, EvidenceLevel, SectionDRow } from './types'
import './evidence.css'

const LEVEL_WORD: Record<EvidenceLevel, string> = { block: 'Fix before sending', warn: 'Check', info: 'Note' }

function size(n: number): string {
  return n >= 1048576 ? `${(n / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1024))} KB`
}

function Finding({ f }: { f: EvidenceFinding }) {
  return (
    <li className={`evf ${f.level}`}>
      <span className="evtag">{LEVEL_WORD[f.level]}</span>
      <span className="evmsg">{f.message}</span>
    </li>
  )
}

/** Attach files to one Section D item and show what the readability checks found. Checks cover reading and
 *  completeness only; they never say a document is correct or that a seal is valid. */
export function EvidenceControl({ appId, row, onChange }: { appId: string; row: SectionDRow; onChange?: () => void }) {
  const [files, setFiles] = useState<EvidenceFile[]>([])
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const input = useRef<HTMLInputElement>(null)
  const offline = appId.startsWith('mock-')

  useEffect(() => {
    if (offline) return
    let live = true
    api.evidenceList(appId).then(r => { if (live) setFiles(r.files.filter(f => f.doc_id === row.id)) }).catch(() => { /* older server: control stays quiet */ })
    return () => { live = false }
  }, [appId, row.id, offline])

  if (offline) return null

  const pick = async (list: FileList | null) => {
    const file = list?.[0]
    if (input.current) input.current.value = ''
    if (!file) return
    setBusy(true); setErr('')
    try {
      const rec = await api.evidenceUpload(appId, row.id, file)
      setFiles(f => [...f, rec])
      onChange?.()
    } catch (e) { setErr(e instanceof Error ? e.message : String(e)) }
    setBusy(false)
  }
  const remove = async (f: EvidenceFile) => {
    setErr('')
    try { await api.evidenceDelete(appId, row.id, f.id); setFiles(x => x.filter(y => y.id !== f.id)); onChange?.() }
    catch (e) { setErr(e instanceof Error ? e.message : String(e)) }
  }
  const inputId = 'ev-' + row.id

  return (
    <div className="evd">
      <div className="evbar">
        <input ref={input} id={inputId} className="evinput" type="file" accept=".pdf,.png,.jpg,.jpeg,.docx,.xlsx,.dwg" onChange={e => void pick(e.target.files)} />
        <label htmlFor={inputId} className={`btn sm ${busy ? 'busy' : ''}`}>{busy ? 'Checking...' : files.length ? 'Attach another file' : 'Attach file'}</label>
        <span className="evhint">PDF, PNG, JPG, DOCX, XLSX or DWG, up to 25 MB</span>
      </div>
      {err && <p className="errata" role="alert"><strong>Error</strong><span>{err}</span></p>}
      {files.length > 0 && (
        <ul className="evfiles">
          {files.map(f => (
            <li key={f.id} className={`evfile ${f.worst}`}>
              <div className="evhead">
                <a className="evname mono" href={api.evidenceUrl(appId, row.id, f.id)} target="_blank" rel="noreferrer">{f.filename}</a>
                <span className="evsize">{size(f.size)}</span>
                <button type="button" className="linkbtn" onClick={() => void remove(f)} aria-label={`Remove ${f.filename}`}>Remove</button>
              </div>
              {f.checks.length > 0
                ? <ul className="evfinds" aria-label={`Checks for ${f.filename}`}>{f.checks.map((c, i) => <Finding key={c.code + i} f={c} />)}</ul>
                : <p className="evok">No readability problems found. This does not mean the content is correct.</p>}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
