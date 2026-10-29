import { useCallback, useEffect, useState } from 'react'
import { api, onOffline } from './api'
import { MOCK_NOTE } from './fixtures/mock'
import type { AppData, MapGraph } from './types'
import { Applicant, useAutosave, type Ctx, type SaveState } from './applicant'
import { Reviewer } from './reviewer'
import { Icon, prettySample } from './ui'

type Route =
  | { kind: 'home' }
  | { kind: 'app'; id: string; step: number }
  | { kind: 'review'; id?: string }
  | { kind: 'boot'; role: 'applicant' | 'reviewer'; step: number; sample?: string; fresh?: boolean }

function parse(hash: string): Route {
  const [path, qs = ''] = hash.replace(/^#/, '').split('?')
  const q = new URLSearchParams(qs)
  const seg = path.split('/').filter(Boolean)
  if (seg[0] === 'a' && seg[1]) return { kind: 'app', id: seg[1], step: Math.min(5, Math.max(1, Number(seg[2]) || 1)) }
  if (seg[0] === 'review' && seg[1]) return { kind: 'review', id: seg[1] }
  if (seg[0] === 'review') return q.get('sample') ? { kind: 'boot', role: 'reviewer', step: 1, sample: q.get('sample')! } : { kind: 'review' }
  if (seg[0] === 'step') return { kind: 'boot', role: 'applicant', step: Math.min(4, Math.max(1, Number(seg[1]) || 1)), sample: q.get('sample') || undefined, fresh: q.get('new') === '1' }
  return { kind: 'home' }
}
const go = (h: string, replace = false) => { if (replace) location.replace(h); else location.hash = h }
const LAST = 'vw.last'
const remember = (id?: string) => { try { if (id) localStorage.setItem(LAST, id); else localStorage.removeItem(LAST) } catch { /* storage unavailable */ } }
const recall = () => { try { return localStorage.getItem(LAST) } catch { return null } }

export default function App() {
  const [route, setRoute] = useState<Route>(() => parse(location.hash))
  const [app, setApp] = useState<AppData | null>(null)
  const [graph, setGraph] = useState<MapGraph | null>(null)
  const [offline, setOffline] = useState(false)
  const [err, setErr] = useState('')
  const [saveState, setSaveState] = useState<SaveState>('idle')
  const [samples, setSamples] = useState<any[]>([])
  const [busy, setBusy] = useState(false)

  useEffect(() => onOffline(setOffline), [])
  useEffect(() => { const f = () => setRoute(parse(location.hash)); addEventListener('hashchange', f); return () => removeEventListener('hashchange', f) }, [])
  useEffect(() => { api.samples().then(s => setSamples(Array.isArray(s) ? s : s?.samples || [])).catch(() => setSamples([])) }, [])

  const loadGraph = useCallback(async () => { if (app) { try { setGraph(await api.map(app.id)) } catch { /* map is optional */ } } }, [app?.id]) // eslint-disable-line react-hooks/exhaustive-deps
  const { save, flush, saveNow } = useAutosave(app, setApp, setSaveState)

  /* resolve the route to an application */
  const routeId = route.kind === 'app' || route.kind === 'review' ? route.id : undefined
  useEffect(() => {
    (async () => {
      try {
        if (route.kind === 'boot') {
          setBusy(true)
          const a = route.sample ? await api.loadSample(route.sample) : await api.createApplication({})
          remember(a.id); setApp(a); setGraph(null)
          go(route.role === 'reviewer' ? `#/review/${a.id}` : `#/a/${a.id}/${route.step}`, true)
          setRoute(parse(location.hash)); setBusy(false)
        } else if (routeId && app?.id !== routeId) {
          setBusy(true)
          const a = await api.getApplication(routeId)
          setApp(a); setGraph(null); remember(a.id); setBusy(false)
        }
      } catch (e) { setBusy(false); setErr('We could not open that application. ' + (e instanceof Error ? e.message : '')); go('#/') }
    })()
  }, [route.kind, routeId]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { if (route.kind === 'review' && app) loadGraph() }, [route.kind, app?.id, app?.completeness?.percent]) // eslint-disable-line react-hooks/exhaustive-deps

  const start = async (sample?: string) => {
    setBusy(true); setErr('')
    try {
      const a = sample ? await api.loadSample(sample) : await api.createApplication({})
      remember(a.id); setApp(a); setGraph(null); go(`#/a/${a.id}/1`)
    } catch (e) { setErr(String(e instanceof Error ? e.message : e)) }
    setBusy(false)
  }
  const reload = useCallback(async () => { if (!app) return null; const a = await api.getApplication(app.id); setApp(a); return a }, [app?.id]) // eslint-disable-line react-hooks/exhaustive-deps
  const ctx: Ctx | null = app ? { app, setApp, save, flush, saveNow, reload } : null

  const role = route.kind === 'review' ? 'reviewer' : 'applicant'
  const switchRole = async (r: 'applicant' | 'reviewer') => {
    if (r === role) return
    await flush()
    if (r === 'reviewer') go(app ? `#/review/${app.id}` : '#/review')
    else go(app ? `#/a/${app.id}/1` : '#/')
  }

  return (
    <div className="shell">
      <a className="skip" href="#main">Skip to main content</a>
      <header className="top">
        <div className="topin">
          <a className="brand" href="#/" onClick={() => { void flush() }} aria-label="Variance Workspace, home">
            <span className="bname">Variance Workspace</span><span className="bsub">Alberta building code variances</span>
          </a>
          <div className="topright">
            {app && route.kind === 'app' && <span className={`savestate ss-${saveState}`} role="status" aria-live="polite">{saveState === 'saving' ? 'Saving...' : saveState === 'saved' ? 'All changes saved' : saveState === 'error' ? 'Could not save. Retrying on your next change.' : 'Saved automatically'}</span>}
            {offline && <span className="offline">{MOCK_NOTE}</span>}
            <div className="seg" role="group" aria-label="View as">
              <button type="button" aria-pressed={role === 'applicant'} onClick={() => switchRole('applicant')}>Applicant</button>
              <button type="button" aria-pressed={role === 'reviewer'} onClick={() => switchRole('reviewer')}>Reviewer</button>
            </div>
          </div>
        </div>
      </header>
      <main id="main" tabIndex={-1}>
        {err && <div className="errata" role="alert"><strong>Error</strong><span>{err}</span><button type="button" className="linkbtn" onClick={() => setErr('')}>Dismiss</button></div>}
        {busy && <div className="binder norail"><div className="board cover hue-ultra"><div className="stripline" /><div className="leaf"><p className="muted loadline"><span className="spin" aria-hidden="true" />Opening your application...</p></div></div></div>}
        {!busy && route.kind === 'home' && <Home samples={samples} onStart={start} resumeId={recall()} />}
        {!busy && route.kind === 'review' && !app && <ReviewerHome samples={samples} onOpen={async n => { setBusy(true); try { const a = await api.loadSample(n); remember(a.id); setApp(a); go(`#/review/${a.id}`) } catch (e) { setErr(String(e)) } setBusy(false) }} />}
        {!busy && route.kind === 'review' && app && <Reviewer app={app} graph={graph} />}
        {!busy && route.kind === 'app' && ctx && app?.id === route.id && (
          <Applicant ctx={ctx} step={route.step} go={n => go(`#/a/${route.id}/${n}`)} graph={graph} loadGraph={loadGraph} />
        )}
      </main>
      <footer className="foot" role="contentinfo">
        <span>Checks completeness only. It does not assess whether a design is safe or equivalent.</span>
        <span>Approval stays with registered professionals and the Authority Having Jurisdiction.</span>
      </footer>
    </div>
  )
}

const INDEX: [string, string, string, string][] = [
  ['1', 'Describe', 'orange', 'Say in plain words what you want to build or do differently.'],
  ['2', 'Rules', 'yellow', 'Check whether it is already covered, then confirm the code articles that apply.'],
  ['3', 'Fill and review', 'grass', 'Close the gaps on a to-do list grouped by form section A to D.'],
  ['4', 'Submit', 'ultra', 'Read the filled form, download it, confirm the declarations yourself and prepare a package.'],
]

function Home({ samples, onStart, resumeId }: { samples: any[]; onStart: (sample?: string) => void; resumeId: string | null }) {
  return (
    <div className="binder norail">
      <div className="board cover hue-ultra">
        <div className="stripline" />
        <div className="leaf home">
          <div className="hcol">
          <h1>Prepare a building code variance request</h1>
          <p className="lead">A variance lets you propose a different way to meet the Building Code. This workbook takes you through it in plain language, finds the code articles, shows what is still missing and fills in the official form. You review and sign. It never signs for you.</p>
          <div className="hero-act">
            <button type="button" className="btn primary lg" onClick={() => onStart()}>Start a new application<Icon name="arrow" /></button>
            {resumeId && <a className="btn lg" href={`#/a/${resumeId}/1`}>Continue my last application</a>}
          </div>
          <section aria-labelledby="how-h" className="how">
            <h2 id="how-h">Contents</h2>
            <ol className="contents">
              {INDEX.map(([n, t, hue, d]) => (
                <li key={n}><span className={`ctab tab-${hue}`}><span className="mono">{n}</span></span><div><strong>{t}</strong><span>{d}</span></div></li>
              ))}
            </ol>
          </section>
          </div>
          <section aria-labelledby="sam-h" className="hcol hside">
            <h2 id="sam-h">Or open a sample</h2>
            <p className="sub">Samples are based on real Alberta documents, with names and addresses left blank. They are a quick way to see how the tool works.</p>
            <SampleList samples={samples} onPick={onStart} cta="Open sample" />
          </section>
        </div>
      </div>
    </div>
  )
}

function SampleList({ samples, onPick, cta }: { samples: any[]; onPick: (n: string) => void; cta: string }) {
  if (!samples.length) return <p className="muted">No samples available.</p>
  return (
    <ul className="samples">
      {samples.map((s, i) => {
        const n = typeof s === 'string' ? s : s.name || s.id
        const p = prettySample(n)
        return (
          <li key={i} className="scard">
            <div><h3>{p.title}</h3><p>{p.blurb}</p></div>
            <button type="button" className="btn sm" onClick={() => onPick(n)} aria-label={`${cta}: ${p.title}`}>{cta}</button>
          </li>
        )
      })}
    </ul>
  )
}

function ReviewerHome({ samples, onOpen }: { samples: any[]; onOpen: (n: string) => void }) {
  return (
    <div className="binder norail">
      <div className="board cover hue-violet">
        <div className="stripline" />
        <div className="leaf home">
          <div className="hcol">
          <h1>Review an application for completeness</h1>
          <p className="lead">Open an application to see what is missing first, a map of how it fits together and the evidence behind each item. You can then draft a request for information.</p>
          <section aria-labelledby="rsam-h" className="how">
            <h2 id="rsam-h">Choose an application to review</h2>
            <SampleList samples={samples} onPick={onOpen} cta="Review" />
          </section>
          </div>
        </div>
      </div>
    </div>
  )
}
