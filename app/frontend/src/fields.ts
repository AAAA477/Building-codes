import type { AppData } from './types'

export type FieldType = 'text' | 'textarea' | 'number' | 'date' | 'select' | 'email'
export interface FieldDef {
  path: string; label: string; type: FieldType; help?: string; options?: [string, string][]; placeholder?: string; unit?: string
}

export const get = (o: any, path: string) => path.split('.').reduce((c, k) => (c == null ? undefined : c[k]), o)
export function nest(path: string, value: any): any {
  const keys = path.split('.'); const root: any = {}; let c = root
  keys.slice(0, -1).forEach(k => { c[k] = {}; c = c[k] })
  c[keys[keys.length - 1]] = value
  return root
}
export function mergeInto(t: any, s: any) {
  for (const k of Object.keys(s)) {
    if (s[k] && typeof s[k] === 'object' && !Array.isArray(s[k])) { t[k] = t[k] || {}; mergeInto(t[k], s[k]) } else t[k] = s[k]
  }
  return t
}

const YN: [string, string][] = [['', 'Choose...'], ['yes', 'Yes'], ['no', 'No']]

export const PEOPLE: FieldDef[] = [
  { path: 'applicant.owner_name', label: 'Owner name', type: 'text', help: 'The legal owner of the property (a person or a company). This is who signs the form.' },
  { path: 'applicant.owner_representative', label: 'Owner representative (optional)', type: 'text', help: 'Only if someone applies on the owner\'s behalf, such as a contractor or designer.' },
  { path: 'applicant.mailing_address', label: 'Mailing address', type: 'text' },
  { path: 'applicant.email', label: 'Email', type: 'email' },
  { path: 'applicant.date_of_request', label: 'Date of request', type: 'date' },
]
export const BUILDING: FieldDef[] = [
  { path: 'location.municipal_address', label: 'Site address', type: 'text', help: 'Street address of the building. If the request covers a whole municipality, say so in the description.' },
  { path: 'location.permit_number', label: 'Permit number (if you have one)', type: 'text' },
  { path: 'project.occupancy', label: 'What is the building used for?', type: 'select', help: 'Occupancy: the main use of the building.',
    options: [['', 'Choose...'], ['Residential', 'Homes or apartments (residential)'], ['Business and personal services', 'Offices and services'], ['Mercantile', 'Shops and stores'], ['Assembly', 'Gathering places'], ['Care or detention', 'Care or detention'], ['Industrial', 'Industrial'], ['Other', 'Something else']] },
  { path: 'project.new_or_renovation', label: 'New building or renovation?', type: 'select', options: [['', 'Choose...'], ['new', 'New building'], ['renovation', 'Renovation of an existing building']] },
  { path: 'project.storeys', label: 'Number of storeys', type: 'number' },
  { path: 'project.building_area_m2', label: 'Building area', type: 'number', unit: 'm²', help: 'Footprint of the largest floor, in square metres.' },
  { path: 'project.units_per_floor', label: 'Dwelling units per floor', type: 'number', help: 'Leave blank if the building has no dwelling units.' },
  { path: 'project.sprinklered', label: 'Is the building sprinklered?', type: 'select', options: YN, help: 'Sprinklered means an automatic sprinkler system is installed.' },
  { path: 'project.part', label: 'Code Part (if you know it)', type: 'select', options: [['', 'Not sure'], ['3', 'Part 3 (larger or complex buildings)'], ['9', 'Part 9 (houses and small buildings)']], help: 'A professional can confirm this later.' },
]

/** Fixes offered inline on the to-do list, keyed by completeness item id. */
export const FIXABLE: Record<string, FieldDef> = {
  'A.owner_name': PEOPLE[0], 'A.mailing_address': PEOPLE[2], 'A.email': PEOPLE[3], 'A.date_of_request': PEOPLE[4],
  'B.location': BUILDING[0], 'B.permit_number': BUILDING[1], 'B.occupancy': BUILDING[2], 'B.new_or_renovation': BUILDING[3],
  'B.storeys': BUILDING[4], 'B.building_area_m2': BUILDING[5], 'B.units_per_floor': BUILDING[6], 'B.sprinklered': BUILDING[7], 'B.part': BUILDING[8],
  'B.description': { path: 'project.description', label: 'Project description', type: 'textarea' },
  'C.code_or_standard': { path: 'variance.code_or_standard', label: 'Code and edition', type: 'text', placeholder: 'NBC(AE) 2023 Division B' },
  'C.explanation': { path: 'variance.acceptable_solution.explanation', label: 'How the acceptable solution is not met', type: 'textarea', help: 'In your own words: which prescribed rule does your design depart from?' },
  'C.alternative': { path: 'variance.proposed_alternative.summary', label: 'Proposed alternative', type: 'textarea', help: 'In your own words: what you propose instead. The detailed analysis is for your registered professional.' },
}

/** Read the value of a field as the string an input needs. */
export function readField(a: AppData, f: FieldDef): string {
  const v = get(a, f.path)
  if (v == null) return ''
  if (typeof v === 'boolean') return v ? 'yes' : 'no'
  const s = String(v)
  return /^\[.*\]$/.test(s.trim()) ? '' : s
}
/** Convert an input string to the value the backend expects. */
export function toValue(f: FieldDef, s: string): any {
  if (f.type === 'number') return s.trim() === '' ? null : Number(s)
  if (f.path === 'project.sprinklered') return s === '' ? null : s === 'yes'
  if (f.path === 'project.part') return s === '' ? null : s
  if (f.path === 'project.new_or_renovation') return s === '' ? null : s
  return s
}
