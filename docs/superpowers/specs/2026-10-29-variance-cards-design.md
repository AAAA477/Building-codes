# Variance Cards: using Alberta STANDATA variances to build alternative solutions

Status: DRAFT for approval · 2026-10-29 · Extends `docs/PRD.md` (F16 "does a variance already exist?")

## 1. Intent and why

Someone applying for an alternative solution in Alberta (builder, manufacturer, contractor, owner's representative, or their professional) has to prove "approximately equivalent or greater safety performance" to a Safety Codes Officer (SCO). They mostly do this alone and do not know that the province has already pre-approved many alternatives as numbered STANDATA variances (e.g. `23-BCV-001`, window opening control devices).

Today the app finds related STANDATA text by search and shows quotes ([applicant.tsx](../../../app/frontend/src/applicant.tsx), `PrecedentPanel`), telling the user to "read each one yourself". It does not know what a variance *is*: the articles it varies, its conditions, its edition, or its scope. So it cannot say whether a variance applies, turn its conditions into a checklist, or reuse its reasoning.

**This work makes each variance a structured "card" and builds three applicant outcomes on top of it:**

1. **Covered.** A variance already covers the situation. The applicant may not need an application. They get the conditions as a checklist they confirm, and the variance to cite.
2. **Near-miss.** A variance is close. Its articles, conditions and reasoning are offered as *suggestions* for the applicant's own request, labelled as borrowed from that variance.
3. **Nothing covers it.** The existing from-scratch flow (e.g. single-exit stair) is unchanged.

## 2. Goals, non-goals, anti-goals

**Goals**
- G1. Every in-scope STANDATA variance has a card: number, title, edition, date, purpose, articles varied, conditions (verbatim), scope/who it applies to, source page.
- G2. The applicant sees which outcome (1/2/3) their situation falls into, with the reason.
- G3. For outcomes 1 and 2, each condition is shown as a checklist item the applicant confirms they can meet. Conditions they cannot meet appear as a **gap list** with the plain message: *to rely on this variance your design must meet these conditions; either adjust the design to meet them, or file your own variance request*.
- G4. In outcome 2, borrowed content is inserted as `precedent_suggestion` entries the applicant must accept (same pattern as the existing suggest/accept flow).
- G5. Edition is always visible; out-of-edition variances are handled per section 5.

**Non-goals**
- Judging whether the applicant's design is safe or equivalent. Predicting approval. (PRD line: completeness, not correctness.)
- Deciding that a variance "applies" for the applicant. The tool says "may apply, here is what it requires"; the SCO or authority decides.
- Variances outside STANDATA (municipal specific variances, SPV documents) in v1, except what the precedents index already holds.
- Interpretations and bulletins as cards in v1 (they stay as search results).

**Anti-goals (failure even if it "works")**
- A condition paraphrased so it changes meaning (store verbatim; show verbatim).
- Presenting a 2014/2019-edition variance as current without saying so.
- Silently dropping unmet conditions or hiding a near-miss because the applicant cannot meet it fully.
- Any wording that implies approval or compliance.
- Writing borrowed text into the application as the applicant's own fact.

## 3. Constraints (from the existing project)

- Citations must resolve against the indexed NBC(AE) 2023 text via the existing verifier; failures are flagged `[UNVERIFIED]`, not shown as fact.
- Provenance on every field (`applicant said | code lookup | AI draft | needs professional`); borrowed content uses a new provenance value `precedent` and requires acceptance. Tool never ticks declarations or signatures.
- Source data already in repo: `files/standata/**` (PDFs), `app/data/content/standata_index.json` (127 STANDATA + named refs), `app/data/corpus/precedents_chunks.jsonl`. Index breakdown: variances NBC(AE) 2023: 19, 2019: 32, 2014: 23; interpretations 2023: 40; bulletins 12.
- Existing stack: FastAPI backend, React/TS frontend, offline LLM fallback when no key (so extraction must work without an LLM; LLM may only assist and is verified against source text).
- Jurisdiction differences stay configuration (overlays), not code.

## 4. Design

### 4.1 Variance card (data)
One JSON record per STANDATA variance under `app/data/content/variance_cards/`, produced by a script in `app/backend/corpus/` (like the other `build_*` scripts), with a validation script and tests.

Fields: `number`, `title`, `kind`, `edition`, `date_issued`, `supersedes/superseded_by` (when stated), `purpose`, `discussion` (verbatim), `articles_varied[]` (each verified), `conditions[]` (verbatim, numbered, each with `source.page`), `applies_to` (scope text verbatim, plus optional parsed hints such as occupancy/Part), `pdf` path, `extraction_confidence`.

Extraction is deterministic first (these documents share a template: Purpose / Discussion / Code references / Conditions / Application). Anything that does not parse cleanly is marked `needs_review` and is excluded from outcomes 1/2 until reviewed; it remains searchable as today.

### 4.2 Matching (which outcome)
Reuse `precedents.app_precedents` / `strong()` for retrieval, then rank on cards: article overlap with the application's `acceptable_solution.articles`, topic terms, edition. Output: `{outcome: covered|near_miss|none, card, reason, matched_articles, edition_status}`.
- *Covered* requires strong article + topic match and an in-edition card.
- *Near-miss* is a weaker or partial match, or in-edition card with different scope.
- Thresholds are the builder's call, tuned on held-out checks (see section 7).

### 4.3 Applicant experience
Replace the collapsed "may this already be covered?" panel with an outcome card at the existing step: outcome label, why, the variance (number, edition, date, link to page), the conditions checklist (yes / no / not sure per condition), and the gap list with the "adjust or file your own request" message. Outcome 2 offers "use as starting point", producing `precedent_suggestion` items to accept into Sections B/C and mitigations. Honest empty state for outcome 3 ("no earlier decision found; that does not mean none exists; ask your authority").

### 4.4 Reviewer experience
Reviewer summary shows which variance the applicant relied on, the condition checklist with the applicant's answers, and unmet conditions as an RFI line. Never states the design is safe.

### 4.5 Export
Outcome 1: cover note names the variance and conditions confirmed. Outcome 2: the borrowed, accepted text is exported with a visible "based on STANDATA 23-BCV-###" attribution. Outcome 3: unchanged.

### 4.6 Import a started draft (added after approval at the user's request)
An applicant who has already begun a variance request elsewhere can bring it in and get the same completeness review, plus the variance-card outcome.
- **Inputs (v1):** (a) the official SCC variance form PDF, filled in whole or part (87 named fields; read by field name, the inverse of `export/fill_scc.py`); (b) pasted text of any draft. A PDF with no form fields is read as text; a scanned image with no text layer is refused with a plain message.
- **Result:** a new application record, an import report (fields filled, content found but not mapped, citations that failed verification), then the existing `/completeness`, reviewer summary and the variance-match above run unchanged.
- **Rules:** nothing is invented; text-derived facts must appear literally in the draft (existing `suggest.extract_facts` rule) and arrive as `ai_draft` for the applicant to confirm; citations pass the verifier or are flagged. **Declarations and signatures are never imported as ticked**: if the file shows them ticked, the report says so and the applicant ticks them in the app. Unmapped content is listed, not dropped silently. Uploads use the existing upload rate limit and size cap and stay scoped to the application (privacy rules).

## 5. Edition handling (decided)
Only 19 of 74 variances are NBC(AE) 2023 (current code in force since 1 May 2024); 55 are 2014/2019. Older cards are **not** offered as covering. They may appear in outcome 2 only, labelled "issued under an earlier code edition; confirm it still applies". Any supersession or bridge note on the card (as `19-BCV-024(REV1)` bridges to the 2023 schedules) is displayed, not interpreted.

## 6. Decisions made with the user
- All three outcomes are in scope.
- Unmet conditions are shown as a gap list and the applicant is told to adjust the design to meet them (or file their own request). The variance is not hidden.

## 6b. Author's calls (from the builder check; change freely)
1. **Outcome states and the checklist.** The applicant answers each condition yes / no / not sure. "Covered" is shown only when *every* condition is answered yes; even then the wording is "may be covered; the authority decides". Any no or not sure moves the card to **conditional**: it stays visible with a gap list ("not sure" counts as unmet) and the message *adjust the design to meet these, or file your own request*. It never silently drops to "none" and never reads as compliance. Reviewer summary and export list unmet conditions as RFI lines; the cover note names a variance as relied on only when all conditions are yes.
2. **Storage.** Per application, under `variance.relied_on = {number, edition, condition_answers[{index, answer}]}` in the existing application record. Accepted suggestions land in the existing Section B/C and `proposed_alternative.mitigations` fields with provenance `precedent`. Schema is additive (missing key = no variance relied on), so no migration. Exact route wiring follows the existing suggest/accept routes.
3. **Matching input.** Whatever the application already holds: free-text description, topic, proposed-alternative summary, and any articles already chosen (this is what `precedents._app_query` already uses). Articles are optional; matching works on free text alone.
4. **Editions.** Cards from 2014/2019 variances are near-miss only, always labelled as an earlier edition. No "carried forward" exception in v1; a parsed superseded-by/bridge note is just displayed. Near-miss from an older card is allowed when it is the only match.
5. **Extraction bar.** All 19 NBC(AE) 2023 variances must end with a verified card (parsed or hand-corrected through a small override file kept beside the cards). 2014/2019 cards are best-effort; failures are `needs_review`, listed in the report, excluded from outcomes 1/2 and still searchable.
6. **Joint variances** (e.g. 19-BCV-014 / 19-FCV-019) are one card carrying both numbers. The count of 74 comes from the index and is re-derived by the extractor report.

## 7. Verification
- Card extraction: every condition string appears verbatim in the source PDF text; every article passes the verifier; report counts and `needs_review` list.
- Held-out outcome checks: hand-written scenarios with known answers (e.g. WOCD in a dwelling to `23-BCV-001` covered; sprinkler-protected glazing to `23-BCV-004`; single-exit stair to none). Report precision/recall honestly, as in `RETRIEVAL_EVAL.md`.
- Tests alongside existing suites; `npm run build` passes; browser check of the applicant flow.

## 8. Left to the builder
Card extractor implementation, scoring thresholds, UI layout within the existing design system, new endpoint names, how `precedent_suggestion` slots into the existing suggest/accept routes, handling of joint variances (e.g. `19-BCV-014 / 19-FCV-019`) and revisions (`R1`, `REV1`).

## 9. Open items (author's calls, change freely)
- The `precedent` provenance label.
- Interpretations/bulletins excluded from cards in v1.
- Municipal variances (Calgary SPV) excluded in v1.
