import type { Refusal, AfterSubmit, ChangesView, QuestionsView, AppData, IntakeResult, MapGraph, Overlay, PrecedentResult, SuggestResponse, EvidenceFile } from './types'
import { MOCK_OVERLAY, MOCK_PRECEDENTS, MOCK_QUESTIONS, blankApp, computeCompleteness, computeMap, mockSample } from './fixtures/mock'

export const API_BASE: string = (import.meta as any).env?.VITE_API_BASE || 'http://localhost:8000/api'

let offline = false
const listeners = new Set<(v: boolean) => void>()
export const onOffline = (f: (v: boolean) => void) => { listeners.add(f); return () => { listeners.delete(f) } }
function setOffline(v: boolean) { if (offline !== v) { offline = v; listeners.forEach(f => f(v)) } }

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) { super(message); this.status = status }
}
/** Turns a backend error body into a short human message. */
function detailOf(text: string): string {
  try { const j = JSON.parse(text); if (typeof j.detail === 'string') return j.detail } catch { /* not json */ }
  return text
}
let aiOff = false
/** When AI help is off, tell the server on every call (covers searches that belong to no application). */
export const setAiHeader = (off: boolean) => { aiOff = off }
async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(API_BASE + path, { ...init, headers: { 'Content-Type': 'application/json', ...(aiOff ? { 'X-AI-Enabled': '0' } : {}), ...(init?.headers || {}) } })
  if (!r.ok) throw new ApiError(r.status, detailOf(await r.text()))
  setOffline(false)
  const ct = r.headers.get('content-type') || ''
  return (ct.includes('json') ? r.json() : r.blob()) as any
}

// ---- mock state (only used when the backend is unreachable) ----
const mockStore: Record<string, AppData> = {}
const mockQi: Record<string, number> = {}
function setPath(o: any, path: string, v: any) {
  const k = path.split('.'); let c = o
  k.slice(0, -1).forEach(p => { c[p] = c[p] ?? {}; c = c[p] })
  c[k[k.length - 1]] = v
}
function deepMerge(t: any, s: any) {
  for (const k of Object.keys(s)) {
    if (s[k] && typeof s[k] === 'object' && !Array.isArray(s[k])) { t[k] = t[k] && typeof t[k] === 'object' ? t[k] : {}; deepMerge(t[k], s[k]) } else t[k] = s[k]
  }
  return t
}
function mget(id: string): AppData {
  const a = mockStore[id] || (mockStore[id] = blankApp(id))
  a.completeness = computeCompleteness(a)
  return a
}

async function guard<T>(real: () => Promise<T>, mock: () => T | Promise<T>): Promise<T> {
  try { return await real() } catch (e) {
    if (e instanceof TypeError) { setOffline(true); return mock() }
    throw e
  }
}
const J = (b: unknown) => JSON.stringify(b)

export const NEEDS_LATEST = 'This feature needs the latest version of the server. Ask your administrator to update it.'
/** Wraps newer endpoints: a 404 with the router's generic body means the endpoint does not exist yet. */
async function newer<T>(real: () => Promise<T>): Promise<T> {
  try { return await real() } catch (e) {
    if (e instanceof ApiError && e.status === 404 && e.message === 'Not Found') throw new ApiError(404, NEEDS_LATEST)
    if (e instanceof ApiError && e.status === 405) throw new ApiError(405, NEEDS_LATEST)
    if (e instanceof TypeError) { setOffline(true); throw new ApiError(0, 'The server cannot be reached.') }
    throw e
  }
}

export const api = {
  topics: () => newer<any>(() => req('/topics')),
  searchArticles: (query: string, k = 8, codes?: string[]) => newer<{ results: any[]; no_good_match?: boolean; message?: string; refusal?: Refusal }>(() => req('/search/articles', { method: 'POST', body: J(codes?.length ? { query, k, codes } : { query, k }) })),
  addArticle: (id: string, article: string, code?: string) => newer<AppData>(() => req(`/applications/${id}/section-c/add`, { method: 'POST', body: J(code ? { article, code } : { article }) })),
  removeArticle: (id: string, index: number) => newer<AppData>(() => req(`/applications/${id}/section-c/${index}`, { method: 'DELETE' })),
  classify: (id: string) => newer<any>(() => req(`/applications/${id}/classify`, { method: 'POST', body: '{}' })),
  createApplication: (body: any = {}) => guard<AppData>(
    () => req('/applications', { method: 'POST', body: J(body) }),
    () => { const a = blankApp('mock-' + Date.now()); mockStore[a.id] = a; return mget(a.id) }),
  getApplication: (id: string) => guard<AppData>(() => req(`/applications/${id}`), () => mget(id)),
  patch: (id: string, patch: any) => guard<AppData>(
    () => req(`/applications/${id}`, { method: 'PATCH', body: J(patch) }),
    () => { deepMerge(mget(id), patch); return mget(id) }),
  intakeNext: (id: string, answer?: string) => guard<IntakeResult>(
    () => req(`/applications/${id}/intake/next`, { method: 'POST', body: J(answer === undefined ? {} : { answer }) }),
    () => {
      const i = mockQi[id] ?? 0
      if (answer !== undefined && i > 0) {
        const q = MOCK_QUESTIONS[i - 1]
        if (answer.trim()) setPath(mget(id), q.path, q.number ? Number(answer) : answer)
      }
      const q = MOCK_QUESTIONS[i]
      mockQi[id] = i + 1
      return { question: q || null, confidence: 0.5 }
    }),
  generateSectionC: (id: string) => guard<any>(
    () => req(`/applications/${id}/section-c/generate`, { method: 'POST', body: '{}' }),
    () => mget(id)),
  map: (id: string) => guard<MapGraph>(() => req(`/applications/${id}/map`), () => computeMap(mget(id))),
  reviewerSummary: (id: string) => guard<any>(() => req(`/applications/${id}/reviewer-summary`), () => {
    const c = computeCompleteness(mget(id))
    const miss = c.items.filter(i => i.status !== 'complete')
    return { summary: `Completeness ${c.percent}%. ${miss.length} item(s) still open: ${miss.map(m => m.label).join(', ') || 'none'}. (Demo summary generated offline. Checks completeness only.)` }
  }),
  rfiDraft: (id: string) => guard<any>(() => req(`/applications/${id}/rfi-draft`, { method: 'POST', body: '{}' }), () => {
    const c = computeCompleteness(mget(id))
    return { subject: 'DRAFT: Request for information', body: 'The following items are open:\n' + c.items.filter(i => i.status !== 'complete').map(i => `- ${i.label}: ${i.message}`).join('\n') }
  }),
  submissionPackage: (id: string) => guard<any>(
    () => req(`/applications/${id}/submission-package`, { method: 'POST', body: "{}" }),
    () => ({ subject: 'DRAFT: Variance application package (demo)', body: 'Backend offline: no package was built.' })),
  verifyCitation: (article: string) => guard<any>(() => req(`/citations/verify?article=${encodeURIComponent(article)}`), () => ({ exists: null, text_excerpt: 'Backend offline: cannot verify.' })),
  samples: () => guard<any>(() => req('/samples'), () => [{ name: 'mock-sample', title: 'Demo placeholder (offline)' }]),
  sample: (name: string) => guard<AppData>(() => req(`/samples/${name}`), () => mockSample()),
  suggest: (id: string, body: { kind: string; text?: string; field_path?: string }) => req<SuggestResponse>(`/applications/${id}/suggest`, { method: 'POST', body: J(body) }),
  setAiEnabled: (id: string, ai_enabled: boolean) => req<{ ai_enabled: boolean }>(`/applications/${id}/ai-setting`, { method: 'PUT', body: J({ ai_enabled }) }),
  suggestAccept: (id: string, body: { field_path: string; value: unknown; item_id?: string }) => req<AppData>(`/applications/${id}/suggest/accept`, { method: 'POST', body: J(body) }),
  precedents: (id: string) => newer<PrecedentResult>(() => req(`/applications/${id}/precedents`)).catch(() => MOCK_PRECEDENTS),
  overlay: (id: string, jurisdiction?: string) => newer<Overlay>(() => req(`/applications/${id}/overlay`)).catch(() => MOCK_OVERLAY(jurisdiction)),
  overlayAnswer: (id: string, question_id: string, answer: string) => newer<any>(() => req(`/applications/${id}/overlay/answer`, { method: 'POST', body: J({ question_id, answer }) })),
  preApplicationBrief: (id: string) => newer<{ title: string; text: string }>(() => req(`/applications/${id}/pre-application-brief`)),
  afterSubmit: (id: string) => newer<AfterSubmit>(() => req(`/applications/${id}/after-submit`)),
  questions: (id: string) => newer<QuestionsView>(() => req(`/applications/${id}/questions`)),
  addQuestions: (id: string, text: string, link?: { section?: string; field?: string }) => newer<QuestionsView>(() => req(`/applications/${id}/questions`, { method: 'POST', body: J({ text, link }) })),
  patchQuestion: (id: string, qid: string, body: { answer?: string; status?: string }) => newer<QuestionsView>(() => req(`/applications/${id}/questions/${qid}`, { method: 'PATCH', body: J(body) })),
  deleteQuestion: (id: string, qid: string) => newer<QuestionsView>(() => req(`/applications/${id}/questions/${qid}`, { method: 'DELETE' })),
  markSubmitted: (id: string) => newer<{ marked_at: string; note: string }>(() => req(`/applications/${id}/mark-submitted`, { method: 'POST', body: '{}' })),
  changes: (id: string) => newer<ChangesView>(() => req(`/applications/${id}/changes`)),
  calgaryPdfUrl: (id: string) => `${API_BASE}/applications/${id}/export/calgary-pdf`,
  pdfUrl: (id: string) => `${API_BASE}/applications/${id}/export/pdf`,
  evidenceList: (id: string) => newer<{ files: EvidenceFile[] }>(() => req(`/applications/${id}/evidence`)),
  evidenceUpload: async (id: string, docId: string, file: File): Promise<EvidenceFile> => {
    const fd = new FormData(); fd.append('file', file)
    // no Content-Type header: the browser sets the multipart boundary
    return newer<EvidenceFile>(async () => {
      const r = await fetch(`${API_BASE}/applications/${id}/evidence/${encodeURIComponent(docId)}`, { method: 'POST', body: fd })
      if (!r.ok) throw new ApiError(r.status, detailOf(await r.text()))
      return r.json()
    })
  },
  evidenceDelete: (id: string, docId: string, fileId: string) => newer<{ ok: boolean }>(() => req(`/applications/${id}/evidence/${encodeURIComponent(docId)}/${fileId}`, { method: 'DELETE' })),
  evidenceUrl: (id: string, docId: string, fileId: string) => `${API_BASE}/applications/${id}/evidence/${encodeURIComponent(docId)}/${fileId}`,
  /** Loads a sample into a fresh application (create, then patch). */
  async loadSample(name: string): Promise<AppData> {
    const s: any = await api.sample(name)
    const a = await api.createApplication({})
    if (a.id.startsWith('mock-')) { mockStore[a.id] = { ...s, id: a.id }; return mget(a.id) }
    const { id: _i, completeness: _c, ...rest } = s
    return api.patch(a.id, rest)
  },
}
