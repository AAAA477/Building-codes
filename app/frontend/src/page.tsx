import { Children, isValidElement, type ReactNode } from 'react'
import type { AppData } from './types'
import type { FieldDef } from './fields'
import { Icon } from './ui'

export type SaveState = 'idle' | 'saving' | 'saved' | 'error'
export interface Ctx {
  app: AppData
  setApp: (a: AppData) => void
  save: (patch: any) => void
  flush: () => Promise<void>
  saveNow: (patch: any) => Promise<AppData | null>
  reload: () => Promise<AppData | null>
}

export function Page({ title, lead, children, aside }: { title: string; lead: ReactNode; children: ReactNode; aside?: ReactNode }) {
  const kids = Children.toArray(children)
  const isBar = (k: any) => isValidElement(k) && k.type === CtaBar
  return (
    <div className="page">
      <div className={`pagegrid ${aside ? '' : 'solo'}`}>
        <div className="pcol">
          <div className="pagehead">
            <h1>{title}</h1>
            <p className="lead">{lead}</p>
          </div>
          <div className="pmain">{kids.filter(k => !isBar(k))}</div>
        </div>
        {aside && <aside className="paside">{aside}</aside>}
      </div>
      {kids.find(isBar)}
    </div>
  )
}

export function CtaBar({ back, onBack, children, hint }: { back?: string; onBack?: () => void; children: ReactNode; hint?: ReactNode }) {
  return (
    <div className="ctabar">
      {onBack ? <button type="button" className="btn" onClick={onBack}><Icon name="back" />{back || 'Back'}</button> : <span />}
      <div className="ctahint">{hint}</div>
      {children}
    </div>
  )
}

export function ProfCard({ app }: { app: AppData }) {
  const flags = app.professional_flags || []
  if (!flags.length) return null
  return (
    <section className="profcard" aria-labelledby="prof-h">
      <h2 id="prof-h">You need a registered professional for this part</h2>
      <p>Part of this request is engineering work. This tool does not write it for you and leaves those items blank on purpose. Your professional must address:</p>
      {flags.map(f => {
        const [, list] = f.reason.split(/must address:\s*/i)
        const items = list ? list.split(/;\s*/).map(x => x.replace(/\.$/, '')).filter(Boolean) : []
        return (
          <div key={f.id}>
            {!items.length && (f.reason.length > 260 ? <><p>{f.reason.slice(0, f.reason.lastIndexOf(' ', 240)).replace(/[;:,]$/, '')}...</p><details className="okdet"><summary>Read the full note</summary><p className="sm">{f.reason}</p></details></> : <p>{f.reason}</p>)}
            {items.length > 0 && <ul className="bul">{items.map((x, i) => <li key={i}>{x}</li>)}</ul>}
            {f.article_refs?.length ? <p className="sm">Related articles: <span className="mono">{f.article_refs.join(', ')}</span></p> : null}
          </div>
        )
      })}
    </section>
  )
}

export function AsideTip({ title, children }: { title: string; children: ReactNode }) {
  return <div className="tipcard"><h2>{title}</h2>{children}</div>
}

export function FieldInput({ f, value, onChange, id }: { f: FieldDef; value: string; onChange: (v: string) => void; id: string }) {
  const common = { id, 'aria-describedby': f.help ? id + '-h' : undefined }
  if (f.type === 'textarea') return <textarea {...common} rows={4} value={value} placeholder={f.placeholder} onChange={e => onChange(e.target.value)} />
  if (f.type === 'select') return <select {...common} value={value} onChange={e => onChange(e.target.value)}>{f.options!.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
  if (f.type === 'number') {
    return (
      <div className="withunit">
        <input {...common} type="number" inputMode="decimal" min={0} value={value} onChange={e => onChange(e.target.value)} />
        {f.unit && <span className="unit" aria-hidden="true">{f.unit}</span>}
      </div>
    )
  }
  return <input {...common} type={f.type} value={value} placeholder={f.placeholder} autoComplete={f.type === 'email' ? 'email' : 'off'} onChange={e => onChange(e.target.value)} />
}

export const JURISDICTIONS: [string, string, string][] = [
  ['scc', 'Safety Codes Council form', 'Any Alberta municipality or agency'],
  ['edmonton', 'Edmonton', 'Adds the emergency-services questions'],
  ['calgary', 'Calgary', 'Adds the permit rule and the Calgary request form'],
]
