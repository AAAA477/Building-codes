import { useId, type ReactNode } from 'react'

/* ---------- icons (inline, decorative; meaning is always carried by text too) ---------- */
const P: Record<string, ReactNode> = {
  check: <path d="M5 12.5l4.2 4.2L19 7" />,
  checkc: <><circle cx="12" cy="12" r="9" /><path d="M8 12.5l3 3 5-6" /></>,
  x: <path d="M6 6l12 12M18 6L6 18" />,
  alert: <><circle cx="12" cy="12" r="9" /><path d="M12 7.5v5.5M12 16.2v.3" /></>,
  question: <><circle cx="12" cy="12" r="9" /><path d="M9.8 9.6a2.3 2.3 0 014.4.8c0 1.5-2.2 1.8-2.2 3.2M12 16.5v.3" /></>,
  pro: <><circle cx="12" cy="9" r="3" /><path d="M6 19c.6-3 3-4.5 6-4.5s5.4 1.5 6 4.5" /></>,
  book: <path d="M5 5.5A1.5 1.5 0 016.5 4H19v14H6.5A1.5 1.5 0 005 19.5zM5 19.5A1.5 1.5 0 006.5 21H19" />,
  arrow: <path d="M5 12h14M13 6l6 6-6 6" />,
  back: <path d="M19 12H5M11 6l-6 6 6 6" />,
  plus: <path d="M12 5v14M5 12h14" />,
  search: <><circle cx="11" cy="11" r="6" /><path d="M16 16l4 4" /></>,
  download: <path d="M12 4v11M7 11l5 5 5-5M5 20h14" />,
  info: <><circle cx="12" cy="12" r="9" /><path d="M12 11v5M12 8v.01" /></>,
  map: <path d="M4 6l5-2 6 2 5-2v14l-5 2-6-2-5 2zM9 4v14M15 6v14" />,
  list: <path d="M9 6h11M9 12h11M9 18h11M4.5 6h.01M4.5 12h.01M4.5 18h.01" />,
  doc: <path d="M7 3h7l4 4v14H7zM14 3v4h4M9.5 12h5M9.5 16h5" />,
  home: <path d="M4 11l8-7 8 7M6 10v10h12V10" />,
  mail: <path d="M4 6h16v12H4zM4 7l8 6 8-6" />,
}
export function Icon({ name, size = 18 }: { name: string; size?: number }) {
  return (
    <svg className="icon" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
      {P[name]}
    </svg>
  )
}

/* ---------- status ---------- */
export const STATUS_TEXT: Record<string, string> = {
  complete: 'Complete', missing: 'Missing', uncertain: 'Please confirm', needs_professional: 'Professional needed', lookup: 'From code lookup',
}
const STATUS_ICON: Record<string, string> = { complete: 'checkc', missing: 'alert', uncertain: 'question', needs_professional: 'pro', lookup: 'book' }
export function StatusPill({ status }: { status: string }) {
  const k = STATUS_TEXT[status] ? status : 'uncertain'
  return <span className={`pill st-${k}`}><Icon name={STATUS_ICON[k]} size={16} />{STATUS_TEXT[k]}</span>
}

export const PROV_TEXT: Record<string, string> = {
  applicant: 'Entered by you', lookup: 'From the code text', ai_draft: 'AI draft, please check', needs_professional: 'For a professional',
}
export function ProvTag({ source }: { source?: string }) {
  if (!source) return null
  const key = source === 'code lookup' ? 'lookup' : source
  return <span className="tag">{PROV_TEXT[key] || source}</span>
}

/* ---------- plain-language glossary ---------- */
export const GLOSS: Record<string, string> = {
  objective: 'An objective is the goal a code rule serves, for example protecting people from fire. It comes straight from the code text.',
  function: 'A function describes how a building feature helps meet an objective, for example by limiting the spread of fire.',
  'intent statement': 'An intent statement is a short description, taken from the code supplement, of what a rule is trying to achieve.',
  variance: 'A variance (also called an alternative solution) is a request to meet the intent of the Code in a different way than the prescribed one.',
  'acceptable solution': 'An acceptable solution is the prescriptive route the Code already sets out. Your request explains how yours differs.',
  'Part 3 or Part 9': 'Part 9 covers smaller, simpler buildings. Part 3 covers larger or more complex buildings. If unsure, leave it and a professional can confirm.',
  sprinklered: 'Sprinklered means the building has an automatic sprinkler system installed.',
}
export function Term({ word, children }: { word: string; children?: ReactNode }) {
  const id = useId()
  return (
    <span className="term" tabIndex={0} aria-describedby={id}>
      {children ?? word}
      <span className="tip" role="tooltip" id={id}>{GLOSS[word] || word}</span>
    </span>
  )
}

/* ---------- stepper ---------- */
export const STEPS = [
  { n: 1, title: 'Describe', hint: 'Tell us what you plan' },
  { n: 2, title: 'Find the rules', hint: 'Confirm code articles' },
  { n: 3, title: 'Fill and review', hint: 'Close the gaps' },
  { n: 4, title: 'Export and submit', hint: 'Download and sign' },
]
/* ---------- form fields ---------- */
export function Field({ label, help, children, htmlFor, wide }: { label: string; help?: ReactNode; children: ReactNode; htmlFor: string; wide?: boolean }) {
  return (
    <div className={`field ${wide ? 'wide' : ''}`}>
      <label htmlFor={htmlFor}>{label}</label>
      {help && <p className="fhelp" id={htmlFor + '-h'}>{help}</p>}
      {children}
    </div>
  )
}

export function Meter({ done, total, label }: { done: number; total: number; label: string }) {
  const p = total ? Math.round((done / total) * 100) : 0
  return (
    <div className="meter" role="progressbar" aria-valuenow={p} aria-valuemin={0} aria-valuemax={100} aria-label={label}>
      <div style={{ transform: `scaleX(${p / 100})` }} />
    </div>
  )
}

export const isPlaceholder = (v: any) => typeof v === 'string' && /^\[.*\]$/.test(v.trim())
export const clean = (v: any) => (v == null || isPlaceholder(v) ? '' : String(v))

export function prettySample(name: string): { title: string; blurb: string } {
  const known: Record<string, [string, string]> = {
    good_stair_edmonton: ['Single-exit stair, Edmonton (well prepared)', 'A residential point-access-block example with its code articles and document list ready.'],
    partial_intake: ['Single-exit stair (just started)', 'An application with only a few answers filled in. Good for trying the guided steps.'],
    flawed_missing_section_d: ['Single-exit stair (documents missing)', 'Everything is filled in except the supporting documents list.'],
    flawed_no_professional: ['Single-exit stair (no professional named)', 'Shows what the tool flags when no registered professional is named.'],
    flawed_unverified_citation: ['Single-exit stair (unchecked article)', 'Includes a code article that could not be verified against the code text.'],
    standata_23_bcv_001_wocd: ['STANDATA variance: wall-mounted exhaust (23-BCV-001)', 'Based on a real Alberta STANDATA variance.'],
    standata_23_bcv_004_sprinkler_glazing: ['STANDATA variance: sprinkler and glazing (23-BCV-004)', 'Based on a real Alberta STANDATA variance.'],
    standata_23_bcv_008r1_exhaust_clearance: ['STANDATA variance: exhaust clearance (23-BCV-008R1)', 'Based on a real Alberta STANDATA variance.'],
  }
  if (known[name]) return { title: known[name][0], blurb: known[name][1] }
  const t = name.replace(/_/g, ' ')
  return { title: t.charAt(0).toUpperCase() + t.slice(1), blurb: 'Sample application.' }
}

export const CODE_FILTERS: [string, string, string[] | undefined][] = [
  ['all', 'All codes', undefined], ['nbc', 'Building', ['NBC(AE) 2023']], ['nfc', 'Fire', ['NFC(AE) 2023']],
  ['npc', 'Plumbing', ['NPC 2020']], ['necb', 'Energy', ['NECB 2020']],
]
export function shortCode(code?: string): string {
  const m = (code || 'NBC').match(/^[A-Z]+/)
  return m ? m[0] : 'NBC'
}
export function CodeBadge({ code }: { code?: string }) {
  const s = shortCode(code)
  return <span className={`cbadge cb-${s.toLowerCase()}`} title={code || 'NBC(AE) 2023'}>{s}</span>
}
