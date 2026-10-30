export type Status = 'complete' | 'uncertain' | 'missing' | 'needs_professional' | 'lookup'
export type Source = 'applicant' | 'lookup' | 'ai_draft' | 'needs_professional'

export interface SectionCRow {
  article?: string; code?: string; code_edition?: string; objective?: string; function?: string; intent?: string; intent_edition?: string; explainer?: string
  source?: { doc?: string; page?: number | string }; verified?: boolean; provenance?: string
}
export interface Mitigation { id: string; label: string; detail?: string; evidence_ids?: string[] }
export interface SectionDRow {
  id: string; document_name: string; responsible_party?: string; professional_required?: boolean
  status: 'provided' | 'missing' | 'to_be_prepared'; date?: string
}
export interface ProfFlag { id: string; reason: string; article_refs?: string[]; stop?: boolean }
export type Group = 'precedent' | 'citations' | 'alternative' | 'documents' | 'professional' | 'admin' | 'signature' | 'jurisdiction'
export interface CompItem { id: string; label: string; section: string; status: string; message?: string; node_id?: string; group?: Group; priority?: number }
export interface Meter2 { done: number; total: number }
export interface TopIssue { id: string; label: string; why?: string; group?: Group; priority?: number; severity?: 'blocker' | 'confirm' }
export interface Meters { admin: Meter2; technical: Meter2; signatures: Meter2 }
export interface Precedent { id: string; source_type: string; jurisdiction?: string; title: string; doc?: string; page?: number | string; issue_date?: string; articles_cited?: string[]; quote?: string; why_relevant?: string; legal_status_note?: string; citation?: string; quote_truncated_start?: boolean; quote_truncated_end?: boolean }
export interface PrecedentResult { coverage: 'possible' | 'none'; items: Precedent[]; note?: string }
export type VarianceState = 'covered' | 'conditional' | 'near_miss' | 'none'
export type ConditionAnswer = 'yes' | 'no' | 'unsure'
export interface VarianceCondition { index: number; label: string; text: string; page: number; answer: ConditionAnswer | 'unanswered' }
export interface VarianceItem {
  number: string; title: string; edition: string; date_issued: string; hint: 'covered_candidate' | 'near_miss'
  state: Exclude<VarianceState, 'none'>; reason: string; matched_articles: string[]; earlier_edition: boolean
  conditions: VarianceCondition[]; gaps: VarianceCondition[]; message: string; variance_text: string; source: { doc: string; page: number }
}
export interface VarianceMatch { outcome: VarianceState; items: VarianceItem[]; note?: string }
export interface StartingPointItem { id: string; kind: 'precedent'; field_path: string; label: string; value: unknown; append?: boolean; why?: string; source?: { doc: string; page: number } }
export interface ImportReport { source: 'form' | 'pdf_text' | 'text'; filled: string[]; unmapped: { label: string; text: string }[]; unverified_citations: string[]; declarations_seen_ticked: string[]; warnings: string[] }
export interface OverlayCheck { id: string; label: string; kind?: string; status: string; why?: string; source?: string; answer?: string }
export interface OverlayQuestion { id: string; prompt: string; help?: string; options: string[]; source?: string; answer?: string }
export interface Overlay { jurisdiction: string; label: string; note?: string; sections: { id: string; title: string; checks: OverlayCheck[] }[]; questions: OverlayQuestion[] }
export interface RfiItem { id: string; label: string; group?: string; code_ref?: string; text: string }
export interface Refusal { refused: true; kind: string; message: string; can_do: string[] }
export interface AppData {
  ai_enabled?: boolean
  id: string; jurisdiction: string; edition: string
  applicant: Record<string, string>
  project: Record<string, any>
  location: Record<string, any>
  variance: {
    topic?: string; code_or_standard?: string
    acceptable_solution?: { articles?: string[]; explanation?: string }
    proposed_alternative?: { summary?: string; mitigations?: Mitigation[] }
    section_c?: SectionCRow[]
  }
  section_d: SectionDRow[]
  professional_flags: ProfFlag[]
  declarations: { privacy_consent: boolean; equal_or_better_ack: boolean; owner_signed: boolean; rep_signed: boolean }
  provenance: Record<string, { source: Source; confidence: number }>
  completeness: { percent: number; items: CompItem[]; meters?: Meters; top_issues?: TopIssue[]; headline?: string }
}
export interface MapNode { id: string; label: string; section?: string; status: Status; provenance?: string; data?: any }
export interface MapGraph { nodes: MapNode[]; edges: { source: string; target: string }[] }
export interface IntakeResult {
  question: any | null
  extracted?: any
  confidence?: number
}

export interface SuggestSource { type: string; code?: string; article?: string; doc?: string; page?: number | string; quote?: string }
export interface Suggestion {
  id: string; kind: 'fact' | 'text' | 'option' | 'prompt' | 'precedent'; field_path?: string; label: string; value: unknown; confidence?: number; why?: string
  sources: SuggestSource[]
  checks?: { grounded: boolean; citations_verified?: boolean; unsupported_numbers: unknown[]; claims_safety: boolean; notes?: string[] }
  status: 'ready' | 'needs_review' | 'rejected'
}
export interface SuggestResponse { kind: string; llm: 'azure-openai' | 'offline'; disclaimer: string; items: Suggestion[]; refusal?: Refusal }

export interface AfterFact { text: string; source: { doc: string; page: number | string; ref?: string } }
export interface AfterSection { id: string; title: string; facts: AfterFact[]; unknown: string[] }
export interface AfterSubmit { jurisdiction: string; title: string; intro: string; unknown_text: string; sections: AfterSection[] }
export type QStatus = 'open' | 'answered' | 'needs_professional'
export interface OfficerQuestion { id: string; text: string; status: QStatus; answer: string; link: { section?: string | null; field?: string | null } | null; created_at: string; answered_at: string | null }
export interface QuestionsView { items: OfficerQuestion[]; open: number; submissions: { n: number; marked_at: string; note: string }[] }
export interface ChangeRow { path: string; kind: 'added' | 'removed' | 'changed'; old: unknown; new: unknown }
export interface ChangesView { has_snapshot: boolean; marked_at: string | null; changes: ChangeRow[]; note: string }

export type EvidenceLevel = 'block' | 'warn' | 'info'
export interface EvidenceFinding { level: EvidenceLevel; code: string; message: string }
export interface EvidenceFile { id: string; doc_id: string; filename: string; size: number; sha256: string; content_type: string; checks: EvidenceFinding[]; worst: EvidenceLevel }
