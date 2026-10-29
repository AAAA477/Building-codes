// MOCK FIXTURES: used only when the backend is unreachable.
// They contain NO building-code facts. Section C rows are intentionally unresolved.
import type { AppData, MapGraph, CompItem } from '../types'

export const MOCK_NOTE = 'Demo data: backend offline'

export function blankApp(id = 'mock-app'): AppData {
  return {
    id, jurisdiction: 'scc', edition: 'NBC(AE) 2023',
    applicant: { owner_name: '', owner_representative: '', mailing_address: '', email: '', date_of_request: '' },
    project: { description: '', occupancy: '', storeys: null, building_area_m2: null, units_per_floor: null, sprinklered: null, new_or_renovation: '', part: null },
    location: { jurisdiction_wide: false, permit_number: '', municipal_address: '' },
    variance: {
      topic: 'single_exit_stair', code_or_standard: '',
      acceptable_solution: { articles: [], explanation: '' },
      proposed_alternative: { summary: '', mitigations: [] },
      section_c: [],
    },
    section_d: [],
    professional_flags: [],
    declarations: { privacy_consent: false, equal_or_better_ack: false, owner_signed: false, rep_signed: false },
    provenance: {}, completeness: { percent: 0, items: [] },
  }
}

export function mockSample(): AppData {
  const a = blankApp('mock-sample')
  a.applicant.owner_name = 'Sample Owner (demo placeholder)'
  a.project.description = 'Placeholder description of a building with one exit stair. Demo only.'
  a.project.storeys = 4
  a.project.units_per_floor = 4
  a.project.sprinklered = true
  a.project.part = '3'
  a.variance.proposed_alternative = { summary: 'Placeholder alternative summary (demo).', mitigations: [{ id: 'm1', label: 'Placeholder mitigation', detail: 'Demo only' }] }
  a.variance.section_c = [{ article: undefined, provenance: 'lookup', verified: false, explainer: 'unresolved (needs corpus lookup)' }]
  a.section_d = [
    { id: 'd1', document_name: 'Professional engineering report', responsible_party: 'Registered professional', professional_required: true, status: 'to_be_prepared' },
    { id: 'd2', document_name: 'Floor plans', responsible_party: 'Applicant', status: 'provided' },
  ]
  a.professional_flags = [{ id: 'pf1', reason: 'Engineering judgment on equivalent performance is required.', stop: true }]
  return a
}

export function computeCompleteness(a: AppData): { percent: number; items: CompItem[] } {
  const items: CompItem[] = []
  const add = (id: string, label: string, section: string, ok: boolean, msg: string, status?: string) =>
    items.push({ id, label, section, status: status || (ok ? 'complete' : 'missing'), message: ok ? 'Provided' : msg, node_id: id })
  add('a_owner', 'Owner name', 'A', !!a.applicant.owner_name, 'Owner name is missing')
  add('a_email', 'Contact email', 'A', !!a.applicant.email, 'Contact email is missing')
  add('b_desc', 'Project description', 'B', !!a.project.description, 'Describe the project')
  add('b_storeys', 'Storeys', 'B', a.project.storeys != null, 'Number of storeys is missing')
  add('b_units', 'Units per floor', 'B', a.project.units_per_floor != null, 'Units per floor is missing')
  add('b_spr', 'Sprinklered?', 'B', a.project.sprinklered != null, 'Say whether the building is sprinklered')
  const c = a.variance.section_c || []
  const cOk = c.length > 0 && c.every(r => r.article && r.verified)
  add('c_rows', 'Code articles, objectives and intent', 'C', cOk, 'Needs corpus lookup (backend offline)', cOk ? 'complete' : 'lookup')
  add('c_alt', 'Proposed alternative', 'C', !!a.variance.proposed_alternative?.summary, 'Describe the proposed alternative')
  a.section_d.forEach(d => add('d_' + d.id, d.document_name, 'D', d.status === 'provided', d.status === 'to_be_prepared' ? 'To be prepared' : 'Document missing',
    d.status === 'provided' ? 'complete' : d.professional_required ? 'needs_professional' : 'missing'))
  items.push({ id: 'sign', label: 'Owner signature (done by the owner)', section: 'SIGN', status: a.declarations.owner_signed ? 'complete' : 'missing', message: a.declarations.owner_signed ? 'Signed' : 'Owner has not signed', node_id: 'sign' })
  const done = items.filter(i => i.status === 'complete').length
  return { percent: Math.round((100 * done) / items.length), items }
}

export function computeMap(a: AppData): MapGraph {
  const comp = computeCompleteness(a)
  const secs = [['A', 'Section A: Applicant'], ['B', 'Section B: Project'], ['C', 'Section C: Variance'], ['D', 'Section D: Documents'], ['SIGN', 'Signatures']]
  const nodes: MapGraph['nodes'] = [{ id: 'root', label: 'Application', status: 'uncertain' }]
  const edges: MapGraph['edges'] = []
  secs.forEach(([s, label]) => {
    const kids = comp.items.filter(i => i.section === s)
    const st = kids.some(k => k.status === 'missing') ? 'missing' : kids.some(k => k.status === 'needs_professional') ? 'needs_professional'
      : kids.some(k => k.status === 'lookup' || k.status === 'uncertain') ? 'uncertain' : 'complete'
    nodes.push({ id: 'sec_' + s, label, section: s, status: st as any })
    edges.push({ source: 'root', target: 'sec_' + s })
    kids.forEach(k => {
      nodes.push({ id: k.id, label: k.label, section: s, status: k.status as any, provenance: 'applicant', data: { message: k.message } })
      edges.push({ source: 'sec_' + s, target: k.id })
    })
  })
  return { nodes, edges }
}

export const MOCK_QUESTIONS = [
  { id: 'q1', path: 'applicant.owner_name', text: 'Who is the owner of the building?', help: 'The legal owner named on the permit application.' },
  { id: 'q2', path: 'project.description', text: 'In your own words, what do you want to build or do differently?', help: 'Plain language is fine. We will map it to code articles later.' },
  { id: 'q3', path: 'project.storeys', text: 'How many storeys does the building have?', help: 'Count storeys above grade.', number: true },
  { id: 'q4', path: 'project.units_per_floor', text: 'How many dwelling units are on each floor?', help: 'Used to check completeness of the single-exit-stair topic.', number: true },
  { id: 'q5', path: 'variance.proposed_alternative.summary', text: 'What are you proposing instead of the code solution?', help: 'A short summary. A registered professional will support the details.' },
]

// ---- demo data for endpoints the server may not provide yet. Contains no code facts. ----
import type { Overlay, PrecedentResult } from '../types'
export const MOCK_PRECEDENTS: PrecedentResult = { coverage: 'none', items: [], note: 'Demo data: the precedent lookup is not available on this server.' }
export const MOCK_OVERLAY = (jurisdiction = 'scc'): Overlay => ({
  jurisdiction, label: jurisdiction === 'calgary' ? 'Calgary (demo data)' : jurisdiction === 'edmonton' ? 'Edmonton (demo data)' : 'Safety Codes Council (demo data)',
  note: 'Demo data: jurisdiction checks are not available on this server.', sections: [], questions: [],
})
