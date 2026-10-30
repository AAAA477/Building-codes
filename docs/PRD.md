# PRD: Alberta Variance Application Workspace

Status: DRAFT for team approval · Date: 2026-10-27 · Event: Built World Tech, Venture Pilots 2026 (Building Codes Challenge)

## 1. What this is, and why

An AI-assisted workspace that helps a builder, manufacturer or design professional prepare a complete, code-referenced **alternative solution (variance) application** in Alberta, and helps a Safety Codes Officer (SCO) review one fast.

**The problem.** Alberta's building codes are prescriptive. To build something different, an applicant must prove "approximately equivalent or greater" performance, which means naming the right code articles, objective/function/intent statements, evidence and professionals. Applicants mostly do this alone. Many submissions arrive incomplete, which causes weeks-to-months of "more information" back-and-forth, labour cost for SCOs and delay cost for applicants. There are 430+ jurisdictions in Alberta, each with its own forms and process.

**The promise.** The applicant describes the project in plain language; the tool asks only what it needs, maps it to the right code articles, fills what can be filled from what it already knows, flags what is missing, and exports the official form. The reviewer opens the result and sees an easy summary plus a visual map showing what is complete and what is missing.

**The line we never cross.** The tool checks **completeness, not technical correctness**. Equivalent performance, engineering judgment and approval stay with registered professionals and the authority having jurisdiction (AHJ). Application progress measures completeness, never likelihood of approval.

## 2. Users

| User | Need |
|---|---|
| Applicant: homebuilder, manufacturer, general contractor, owner's representative | A complete submission without prior variance experience or code fluency |
| Supporting professionals: architects, engineers, code consultants | Fast assembly of the administrative parts so their time goes to the analysis |
| Safety Codes Officer / plans examiner (Calgary, Edmonton first) | Rapid view of what is present, what is missing, and where the evidence is |

## 3. Goals, non-goals, anti-goals

**Goals**
- G1. Applicant reaches a complete Section A–D draft with minimal repeated data entry.
- G2. Every code citation resolves to a real article in the correct edition (NBC Alberta Edition 2023).
- G3. The tool signals its own confidence and never fills boxes regardless.
- G4. It flags where a registered professional is required and stops there.
- G5. A reviewer can see gaps and find evidence in seconds.
- G6. Jurisdiction differences (Calgary, Edmonton) are configuration, not code.

**Non-goals (v1)**
- Judging whether an alternative is safe or equivalent. Predicting approval. Replacing a professional.
- Categories other than the single-exit stair; codes beyond the NBC(AE) for the demo.
- Payment, e-signature, or direct integration with municipal permit systems. (Submission itself is in scope as a one-click package, see F21.)
- Jurisdictions outside Alberta.

**Anti-goals (failure even if it "works")**
- A fabricated or unverifiable citation.
- Invented facts in any field (see provenance rule, section 6).
- Language that implies compliance or approval (including from the cost comparison).
- A tool that only works for the demo case and cannot be extended.

## 4. Scope

**Demo scope (Alberta only, especially Edmonton and Calgary)**
- One category: **single-exit stair buildings** (Edmonton "Point Access Block": residential, up to 6 storeys, up to 4 units per floor per the Edmonton guide; in Alberta, over two storeys is only legal via an accepted alternative solution).
- Master output: the Safety Codes Council **Variance Form, Part 1, Sections A–D** (PDF export matching the form).
- Overlays: Calgary (Request for Specific Variance fields) and Edmonton (emergency-services screen and review process).
- Codes: NBC Alberta Edition 2023 plus intent supplements; NFC(AE) 2023 where relevant.

**Product shape beyond the demo:** more categories, more jurisdictions, more codes, added through templates and overlays.

## 5. Applicant workflow

0. **Before you start.** Check whether a province-wide variance (STANDATA) or interpretation already covers the situation. Offer a one-page brief for a pre-application meeting (Calgary starts there; Edmonton recommends it for single-exit stairs).
1. **Describe.** Free text: "what do you want to build or do differently?"
2. **Building facts.** Occupancy, storeys, area, units per floor, sprinklered or not, new or renovation. The tool computes whether Part 3 or Part 9 applies.
3. **Confirm topic.** AI proposes a topic bucket with a confidence level; user confirms.
4. **Topic questions.** Short, adaptive questions for the single-exit stair module (unit count, travel distance, sprinklers, compartmentation, smoke control, fire-department access).
5. **Mitigations and evidence.** What mitigating features, what evidence already exists (reports, listings, standards), who the professional is.
6. **Mind map workspace.** Nodes fill in as answers arrive (see section 7).
7. **Review and export.** Completeness check, checklist of unresolved items, PDF export of the form plus supporting-document list.
8. **Submit (accelerated).** One click builds the submission package: the form PDF, the named attachments, a cover note and a prefilled email to the right recipient, and hands the application to the in-app reviewer queue. A human reviews and sends; the package unlocks once the user confirms the owner has signed and consented (see F21).

## 6. Requirements

Priority: P0 = must work in the demo; P1 = should; P2 = stretch. "Rubric" = the judged criterion it serves.

Rubric weights (from the challenge brief): Intake 20% · Code identification 20% · Recommendations 10% · Review 10% · Implementation plan 10% · Business plan 10% · Usability and portability 10% · General applicability 5% · X factor 5%.

| ID | Requirement | Pri | Rubric |
|---|---|---|---|
| F1 | Adaptive intake that prompts for missing information and shows a confidence level per answer | P0 | Intake |
| F2 | Compute Part 3 vs Part 9 and topic bucket from building facts; user confirms | P0 | Intake |
| F3 | Rank candidate code articles by importance to the project, with rationale | P0 | Code ID |
| F4 | Recommend the most likely benchmark acceptable solution with an explanation | P0 | Code ID |
| F5 | Section C table (Article, Objective, Function, Intent) via **deterministic lookup**, not generation; one explainer paragraph per article | P0 | Code ID |
| F6 | Root-article rule: where an article has no attributed objectives (exceptions, some subsections), use the root article's statements and say so | P0 | Code ID |
| F7 | Citation verifier: every cited article is checked against the indexed NBC(AE) 2023 text; failures block export | P0 | Code ID |
| F8 | Professional flag: state when the work constitutes engineering or requires a registered professional (single-exit stair: fire-protection/life-safety consultant) and **stop**; never write the engineering analysis | P0 | Recommendations |
| F9 | Section D recommendations: list the technical issues and code sections the supporting documentation must address (code analysis, assumptions and limits, testing/studies, commissioning and maintenance, qualifications of the responsible person, single coordinating professional per Division C 2.3.1.1) | P0 | Recommendations |
| F10 | Completeness review of any completed application (generated here or uploaded as PDF) listing deficiencies | P0 | Review |
| F11 | Reviewer view: layout B (checklist, mind map, evidence panel), 30-second summary, draft "request for information" built from the gaps | P0 | Review, Usability |
| F12 | PDF export matching SCC Part 1 Sections A–D. Fill the official PDF: **confirmed fillable** (87 named fields, checked with PyMuPDF on `files/direct/07_Variance_Form.pdf`) | P0 | Design |
| F13 | Data model shaped like the SCC form; Calgary and Edmonton as overlays | P0 | Portability |
| F14 | Provenance on every field: *applicant said*, *code lookup*, *AI draft*, *needs professional* | P0 | Intake |
| F15 | Edmonton emergency-services screen (four questions from COE-IM-GUIDE-0040; F06/F12/F13 trigger) and ITM/commissioning documentation prompt | P1 | Recommendations |
| F16 | "Does a variance already exist?" search over STANDATA variances, bulletins and interpretations. Extended by structured variance cards, condition checklists and import of a started draft: see `docs/superpowers/specs/2026-10-29-variance-cards-design.md` | P1 | Code ID |
| F17 | Pre-application meeting brief (one page) | P1 | Applicability |
| F18 | Plain-language glossary for objective, function, intent, acceptable solution | P1 | Applicability |
| F19 | Baseline vs alternative cost comparison: two-stair baseline vs one stair plus mitigations, **sample data clearly labelled**, ranges and assumptions visible, safety checks shown separately from price | P2 | n/a (team add-on) |
| F20 | Progress indicator that measures completeness only | P0 | Usability |
| F21 | **Accelerated submission package.** One click bundles the signed form PDF, named attachments, a cover note, and a prefilled email draft. Recipient comes from the jurisdiction overlay (SCC form: accreditation@safetycodes.ab.ca; Calgary: the assigned SCO by email; Edmonton: the plans examiner on the permit file, unconfirmed). Also hands the application to the in-app reviewer queue. A human sends the email; the tool never sends on its own and never ticks consent or signatures. Blocked until the user confirms the declarations are signed | P0 | Usability, Business |

## 7. Experience

**Applicant: guided mind map.** Root = the application. Branches = Sections A–D. The single-exit-stair issue is a sub-branch with this chain: *code varied → objectives and intent → proposed alternative → mitigating features → evidence → professional*. Node colours: from the applicant, from code lookup, suggested by AI (confirm), needs input, needs professional. Shows saved progress, next action, missing items and a live document preview. The map and the form share one data model.

**Reviewer: layout B (chosen by the team).** Left: checklist of sections with red/amber/green. Centre: mind map. Right: evidence panel showing why an item is flagged, the exact article, and the source passage. Above: a plain 30-second summary. The reviewer sees gaps and where evidence sits; it never states whether the design is safe.

## 8. Guardrails

- **Completeness, not correctness** is stated in the product and on every export.
- **No invention.** Facts come from the applicant, from lookup or from sourced text; AI drafts are labelled and must be confirmed.
- **Citations are verified or blocked.** Edition is tagged on every citation.
- **Professional stop.** Where engineering judgment is required the tool lists what the professional must address and leaves it blank.
- **Humans sign.** The tool never signs or ticks the consent and equal-or-better declarations for a user.
- **Privacy.** The SCC form carries a Protection of Privacy Act disclosure; handle personal data accordingly and keep uploaded documents scoped to the application.

## 9. Knowledge base (all in `files/`)

NBC 2023 AE; NBC/NECB 2020 intent supplements; NFC 2023 AE and its intent supplement; NECB 2020; Safety Codes Act and regulations; Calgary and CWC alternative-solution guides; Edmonton Point Access Block guide and emergency-services guideline; ~100 STANDATA variances, bulletins, interpretations; the SCC variance form.

Two retrieval paths: (1) a **structured attribution table** (article to objectives, functions, intent) extracted from the code, used for Section C; (2) **vector search** over code text, guides and past STANDATA documents, used for explainers, precedent and the existence check. Known limitation from the sources: intent statements exist only for Parts 3–9 of Division B, and some articles have no attributed objectives (hence F6).

## 10. Architecture (calls made by the author, change freely)

Python backend, local embeddings on GPU (indexing, not model training), a vector store, an LLM for drafting and extraction behind a thin interface, a React front end with a graph library for the map, server-side PDF generation. A form-definition file describes each form and overlay so a new jurisdiction is a new file.

## 11. Success measures

Preparation time; repeated fields avoided; missing items detected (measured on a **seeded-defects set**); time to find evidence during review; citation accuracy (target 100% verified); intake confidence calibration. Baselines come from timing 2 to 3 people on the current manual process.

## 12. Demo plan

One realistic single-exit-stair application built live, then one deliberately flawed application opened in the reviewer view to show gaps found in seconds. Include the professional-stop moment and the verified-citation moment.

## 13. Risks

| Risk | Mitigation |
|---|---|
| Wrong or wrong-edition citation | Lookup table plus verifier (F5, F7); CWC examples use BC code, so treat them as structure only |
| Extracting attribution tables from large PDFs | Do early; this is the critical path |
| Looking like it decides safety | Language rules (section 8) and reviewer view limited to completeness |
| Scope creep (cost comparison, extra categories) | Cost comparison is P2 |
| Edmonton has no separate form found | Use SCC form as baseline; confirm with Safety Codes, Permits and Inspections |
| Calgary form on file is revision R2014-06 | Check for a newer revision |
| The challenge brief's appendix misquotes some NBC articles (e.g. it labels 2.4.2.1 "Professional Design"; in the real NBC 2.4.2.1 is "Application" and the professional-design rules are in 2.4.1.1(3)-(4) and 2.4.2.2; its 1.2.1.2, 1.2.1.3 and 2.2.x quotes also differ) | Quote only from the NBC text itself; the verifier is the authority, never the brief. Flag this to the organizers |
| The Edmonton PAB technical report and its 13 design studies are not in `files/`, so the mitigation catalogue has only 5 items | Add them if the team can obtain them; otherwise the tool lists mitigation categories and leaves values to the professional |

## 14. Decisions

**Made by the team:** Alberta only (Edmonton, Calgary first) · demo topic is the single-exit stair · applicant mind map and reviewer layout B · build everything ourselves · document set in section 15 · financial comparison stays as the team described it, as a small labelled sample.

**Author's calls:** all of section 10 · priorities in section 6 · the "does a variance already exist?" step · pre-application brief · provenance badges · docs location `docs/`, uncommitted.

## 15. Companion documents

2. Intake question bank and single-exit-stair modules · 3. Data model and form schema with overlays · 4. Knowledge base and RAG spec · 5. Eval plan · 6. UX spec · 7. Guardrails · 8. Demo script and samples · 9. Business and implementation plan · 10. Task split by owner (Ayaan: RAG, extraction, summary; Jeremy: front end; unowned: corpus prep, evals, pitch).

## 15a. Calls made after the builder check (author's calls, change freely)

| Question raised | Call |
|---|---|
| Is the corpus text-extractable, who owns extraction? | First build task is a text-extraction check of the NBC(AE) PDFs. Fallback: a hand-curated attribution table limited to the single-exit-stair articles, with the verifier index built from full text separately. Corpus prep is assigned to the RAG owner until the team says otherwise |
| What does "verified" mean (F7)? | Closed-set citations: the LLM may cite only articles supplied from the lookup or retrieval. Free-text paragraphs are post-checked by pattern against the index. Verified = the article exists in the indexed edition (NBC and NFC). Checking that the text supports the claim is P1 |
| How does F10 work on uploads? | Input is our own export or the official SCC PDF (read fields if fillable, else extract text). No scans or OCR in v1. F10 checks administrative completeness only (present, consistent, cited, attached). Section D topics are checked as "addressed or not", never "adequate" |
| Seeded-defects samples | The team writes 3 to 5 synthetic applications, some deliberately flawed. Owner unassigned (see open questions) |
| Part 3 vs Part 9 and topic bucket | Hand-coded rules checked against the code text, not inferred by the LLM. One supported topic plus an "unsupported" response that shows the general checklist |
| Does "stop" block export? | No. Export still works with Section D blank and carries a "professional required, Section D incomplete" banner. Section D recommendations are template lookup plus labelled AI draft |
| Persistence and accounts | Single-user local store; applicant and reviewer are two views switched in the demo; no auth in v1 |

## 15b. One-week cut (team answers: under 1 week, hosted LLM on synthetic data only, 3 people, package-plus-email submission)

**Team of three (author's reading of "1 more"):** RAG owner (extraction, code lookup, summaries) · front-end owner (mind map, reviewer view, export) · third person (corpus curation for the stair articles, 3 to 5 synthetic applications including flawed ones, eval checks, demo script, pitch and business plan).

**Keep in the demo (P0):** F1, F2 (simple rules), F3, F4, F5, F6, F7 (closed-set citations plus existence check), F8, F9, F10 (administrative checks on our own export), F11 (layout B), F12 (regenerated PDF unless the official form proves fillable in under an hour), F13 (SCC form plus a Calgary overlay; Edmonton is a config stub), F14, F20, F21.

**Cut to stretch:** F16 (search for existing variances; hand-list two or three relevant STANDATA items instead), F17 (pre-application brief), F18 (glossary beyond tooltips on the three terms), F19 (cost comparison), upload of external PDFs in F10, and the vector search over the full ~100 STANDATA documents.

**Scope shrinks to:** a **hand-curated attribution table for the single-exit-stair articles only**, built from the NBC(AE) and the intent supplement, with the verifier index built from the full code text. Synthetic data only; hosted LLM API; embeddings local; no auth.

**Still non-negotiable:** verified citations, the professional stop, provenance badges, and the "completeness not correctness" wording.

## 16. Left to the builder

Stack details in section 10; exact question wording; visual design; chunking and embedding choices; how the verifier indexes articles.
