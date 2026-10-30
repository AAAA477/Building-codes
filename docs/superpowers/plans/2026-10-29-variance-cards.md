# Variance Cards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn each Alberta STANDATA variance into a structured card and give applicants three outcomes (covered / near-miss / none) with a condition checklist and gap list.

**Architecture:** An offline extractor parses the STANDATA PDFs into cards under `app/data/content/variance_cards/`. A matcher ranks cards against an application (reusing `corpus/precedents.py` retrieval) and a pure function turns checklist answers into an outcome state. A new `routes_variance.py` (auto-mounted by `main.py`) exposes match, answer and starting-point endpoints; completeness, reviewer and export read the stored answers; the React applicant step replaces `PrecedentPanel`.

**Tech Stack:** Python 3 / FastAPI / pytest (`app/backend/.venv`), PyMuPDF (`fitz`, already installed), React + TypeScript (Vite).

**Spec:** `docs/superpowers/specs/2026-10-29-variance-cards-design.md`

## Global Constraints

- Run Python from `app/backend` with `.venv/Scripts/python.exe -X utf8`; tests with `.venv/Scripts/python.exe -m pytest tests/<file> -v`.
- Condition text and `discussion` are stored **verbatim** from the PDF (whitespace-normalised only); never paraphrased by code or LLM.
- Every `articles_varied` entry passes `corpus.verifier.article_exists`; failures are listed in `articles_unverified`, never shown as fact.
- Outcome states are exactly `covered | conditional | near_miss | none`. `covered` only when every condition is answered `yes`; `no` and `unsure` and unanswered all count as unmet.
- Only `NBC(AE) 2023` cards can be `covered`/`conditional`; 2014/2019 cards are `near_miss` only, labelled "issued under an earlier code edition; confirm it still applies".
- All 19 NBC(AE) 2023 variances must end with a verified card (parsed or via `_overrides.json`); older cards are best-effort, failures get `needs_review: true` and are excluded from outcomes.
- Wording never says the design is safe, compliant or approved; the decision is the authority's. The tool never ticks `declarations`.
- Borrowed content gets provenance `precedent` and is only written after the applicant accepts it.
- No LLM needed anywhere in this feature (offline fallback must work).
- The working tree has the user's uncommitted edits (`frontend/src/aftersubmit.css`, `evidence.css`, `.playwright-mcp/*`, `tests/conftest.py`). `git add` only the files each task names; commit only when the user permits it.

## Review Focus

- Application with an empty or placeholder description (`[to be completed by applicant]`) and no articles: expect outcome `none` and no error.
- Card that parsed zero conditions: never `covered`; shown as `near_miss`/`needs_review`, not an empty checklist that reads as "nothing required".
- Original and revision of one variance (`23-BCV-008` and `23-BCV-008R1`, `19-BCV-018` / `R1` / `R2`): only the latest revision is matched; the older one is not offered alongside it.
- Applicant answered the checklist, then edits the description so a different variance matches: stored answers for the old number are kept but not applied to the new card.
- Imported draft that is a scanned image, not the SCC form, or has the consent/signature boxes already ticked: clear message, no fabricated fields, declarations always imported as unticked (Task 4 tests).
- `PUT` with an unknown card number, an out-of-range condition index, or an answer other than `yes|no|unsure`: 4xx, application unchanged.

---

### Task 1: Card extractor, overrides and data

**Files:**
- Create: `app/backend/corpus/build_variance_cards.py`
- Create: `app/data/content/variance_cards/_overrides.json` (starts as `{}`)
- Create (generated): `app/data/content/variance_cards/<number>.json`, `_report.json`
- Test: `app/backend/tests/test_variance_cards.py`

**Interfaces:**
- Produces: `parse_variance_text(text: str, doc: str) -> dict` returning the card fields from spec 4.1 (`number`, `numbers` (list, joint variances), `title`, `kind`, `edition`, `date_issued`, `revision`, `purpose`, `discussion`, `articles_varied`, `articles_unverified`, `conditions` (list of `{index:int, text:str, page:int}`), `applies_to`, `doc`, `pdf`, `needs_review:bool`, `extraction_confidence:float`).
- Produces: `build_all() -> dict` writes one JSON per card plus `_report.json` (`total`, `by_edition`, `parsed`, `needs_review[]`, `unverified_articles[]`) and applies `_overrides.json` (`{number: {field: value}}`) after parsing.

- [ ] **Step 1: Write failing tests** in `tests/test_variance_cards.py`: `test_wocd_card_fields` (parse `files/standata/variances_2023/ma-standata-variance-building-23-bcv-001-2024-04.pdf`; assert `number == "23-BCV-001"`, `edition == "NBC(AE) 2023"`, `"9.8.8.1" in " ".join(articles_varied)`, a condition containing "not permitted for use in adaptable or barrier-free dwelling units", every condition has `page >= 1`); `test_conditions_are_verbatim` (for every generated card, each condition `text` occurs in the whitespace-normalised PDF text); `test_all_2023_variances_have_verified_cards` (the 19 `variance`/`NBC(AE) 2023` items in `standata_index.json` each have a card with `needs_review is False` and `articles_unverified == []`); `test_joint_variance_is_one_card` (`19-BCV-014`/`19-FCV-019` produce one card whose `numbers` has both); `test_report_counts_match_index` (`_report.json total` equals the number of `variance` items in the index).
- [ ] **Step 2: Run** `pytest tests/test_variance_cards.py -v`. Expected: FAIL (module/files missing).
- [ ] **Step 3: Implement** `parse_variance_text` and `build_all` in `corpus/build_variance_cards.py`. Read PDFs with `fitz`, normalise whitespace and the bidi characters like `build_precedents.clean`, split on the template headings (Purpose / Discussion / Code references / Conditions / Application — inspect 3–4 real PDFs first, including 2014 and 2019 templates, since headings differ), take the file list and `kind`/`edition` from `app/data/content/standata_index.json` instead of re-deriving, collapse revisions so only the highest revision per base number is `current: true` (field `superseded_by` set on the others), verify articles with `verifier.article_exists`.
- [ ] **Step 4: Run** `.venv/Scripts/python.exe -X utf8 -I -m corpus.build_variance_cards`, read `_report.json`, fix the parser or add `_overrides.json` entries until all 19 2023 variances pass. Record the final parsed / needs_review counts in the report.
- [ ] **Step 5: Run** `pytest tests/test_variance_cards.py -v`. Expected: PASS.
- [ ] **Step 6: Commit** `git add app/backend/corpus/build_variance_cards.py app/backend/tests/test_variance_cards.py app/data/content/variance_cards` — `feat: structured STANDATA variance cards`.

### Task 2: Card loader, matcher and outcome state

**Files:**
- Create: `app/backend/corpus/variance_match.py`
- Test: `app/backend/tests/test_variance_match.py`

**Interfaces:**
- Consumes: card JSON from Task 1; `corpus.precedents.app_precedents(app, k, min_score)` and `precedents._app_query(app)`.
- Produces: `all_cards() -> list[dict]`, `get_card(number: str) -> dict | None` (only `current` and not `needs_review` unless `include_review=True`).
- Produces: `match_cards(app: dict, k: int = 3) -> list[dict]`, each `{number, hint: "covered_candidate" | "near_miss", reason: str, matched_articles: list[str], score: float}`; `covered_candidate` requires an NBC(AE) 2023 card with article overlap and topic match (reuse `precedents.strong`), everything else that scores above `MIN_SCORE` is `near_miss`; older-edition cards are always `near_miss`.
- Produces: `outcome_state(hint: str, conditions: list[dict], answers: list[dict]) -> str` where `answers` is `[{"index": int, "answer": "yes"|"no"|"unsure"}]`, returning `covered | conditional | near_miss`; `no_match_state() -> "none"`. `gaps(conditions, answers) -> list[dict]` returns the unmet conditions.

- [ ] **Step 1: Write failing tests**: `test_outcome_state_all_yes_is_covered`; `test_outcome_state_unsure_or_missing_is_conditional` (one `unsure`, then one missing answer: both `conditional`); `test_near_miss_stays_near_miss_regardless_of_answers`; `test_zero_conditions_never_covered`; `test_empty_application_matches_nothing` (sample `partial_intake`-style app with placeholder text returns `[]`); `test_wocd_sample_matches_23_bcv_001_as_covered_candidate`; `test_2019_card_is_never_covered_candidate` (build an app whose text matches a 2019-only variance such as insulation below heated floors, assert every hit for it is `near_miss`); `test_old_revision_not_matched` (`23-BCV-008` original absent when `R1` exists).
- [ ] **Step 2: Run** `pytest tests/test_variance_match.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** the signatures above. Matching: run `app_precedents`, map each chunk's STANDATA number to a card, dedupe by card keeping best score, apply edition rule.
- [ ] **Step 4: Run** the tests. Expected: PASS (use the real samples under `app/data/samples/` for the application dicts).
- [ ] **Step 5: Commit** `corpus/variance_match.py` and its test — `feat: variance card matcher and outcome state`.

### Task 3: API: match, answers, starting point, accept

**Files:**
- Create: `app/backend/routes_variance.py`
- Modify: `app/backend/routes_suggest.py` (accept endpoint, around line 33–45: allow an optional body field `provenance` limited to `"precedent"`, default stays `ai_draft`; BLOCKED fields unchanged)
- Modify: `app/backend/models.py` only if `normalize` drops the new `variance.relied_on` key
- Test: `app/backend/tests/test_variance_api.py`

**Interfaces:**
- Consumes: `variance_match.match_cards`, `get_card`, `outcome_state`, `gaps`; `models.load/save`.
- Produces: `GET /api/applications/{id}/variance-match` → `{outcome, items:[{number, title, edition, date_issued, hint, state, reason, conditions:[{index,text,page,answer}], gaps:[...], message, source:{doc,page}}], note}`; `message` for `conditional`/`near_miss` states: "To rely on this variance your design must meet these conditions. Either adjust the design to meet them, or file your own variance request."
- Produces: `PUT /api/applications/{id}/variance/relied-on` body `{number, condition_answers:[{index, answer}]}` → same item shape; stores `variance.relied_on = {number, edition, condition_answers}`; 404 unknown number, 422 bad index or answer.
- Produces: `GET /api/applications/{id}/variance/starting-point?number=` → `{items:[{id, kind:"precedent", field_path, label, value, source}]}` for `near_miss` cards only (borrowed condition text → `variance.proposed_alternative.mitigations` entries labelled "Based on STANDATA <number>", articles → `variance.acceptable_solution.articles` suggestions); accepted through the existing `/suggest/accept` with `provenance: "precedent"`.

- [ ] **Step 1: Write failing tests** with `TestClient` (same pattern as `tests/test_precedents_api.py`): `test_match_wocd_sample_candidate`; `test_put_all_yes_gives_covered_state`; `test_put_one_no_gives_conditional_with_gap_and_message`; `test_put_unknown_number_404_and_unchanged`; `test_put_bad_index_and_bad_answer_422`; `test_answers_for_other_number_not_applied` (store answers for card A, change description so B matches, GET shows B with no answers); `test_starting_point_only_for_near_miss`; `test_accept_precedent_sets_provenance_precedent`; `test_accept_cannot_touch_declarations` (still 409/blocked); `test_empty_description_returns_none_outcome_200`.
- [ ] **Step 2: Run** `pytest tests/test_variance_api.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** the router and the `provenance` option as specified. Rate-limit class stays the general one (no LLM).
- [ ] **Step 4: Run** `pytest tests/test_variance_api.py tests/test_suggest.py tests/test_precedents_api.py -v`. Expected: PASS, existing suites unaffected.
- [ ] **Step 5: Commit** the new route, test and the small edits — `feat: variance outcome endpoints`.

### Task 4: Import a started draft (spec 4.6)

**Files:**
- Create: `app/backend/import_draft.py`, `app/backend/routes_import.py`
- Modify: `app/backend/export/fill_scc.py` only to expose its field mapping as data both directions can use (no behaviour change; `export/test_export.py` must still pass)
- Test: `app/backend/tests/test_import_draft.py`

**Interfaces:**
- Consumes: `fill_scc` field mapping and `app/data/forms/scc_form_fields.json`; `suggest.extract_facts(text, llm=None)`; `corpus.verifier`; `models.new_application/save`.
- Produces: `from_scc_pdf(data: bytes) -> tuple[dict, dict]` and `from_text(text: str) -> tuple[dict, dict]`, each returning `(application, report)`; `report = {source: "form"|"pdf_text"|"text", filled: [field_path], unmapped: [{label, text}], unverified_citations: [str], declarations_seen_ticked: [str], warnings: [str]}`.
- Produces: `POST /api/applications/import` (multipart `file` PDF, or JSON `{text}`) → `{id, application, report}`; 413 over the existing size cap, 422 for an image-only PDF ("no readable text; paste the text or use a fillable PDF"), upload rate limit class.

- [ ] **Step 1: Write failing tests**: `test_roundtrip_filled_scc_form` (fill a sample with `fill_scc`, import the PDF, assert owner name, permit number, `section_c` articles and Section D rows equal the originals); `test_partial_form_reports_missing_not_invented` (form with only Section A filled: other sections empty, `completeness` lists them as missing); `test_declarations_never_imported_ticked` (form exported with consent/signature boxes ticked: imported `declarations` all false and `declarations_seen_ticked` non-empty); `test_text_draft_facts_must_appear_literally` (text says "4 storeys"; a number not in the text never appears); `test_unverified_citation_flagged` (text cites `9.99.99.99`: in `unverified_citations`, not in verified `section_c`); `test_image_only_pdf_rejected_422`; `test_non_form_pdf_falls_back_to_text_with_warning`; `test_unmapped_content_is_listed`; `test_imported_draft_gets_variance_match` (text describing a WOCD window mechanism per ASTM F2090: `GET /variance-match` returns a `23-BCV-001` item).
- [ ] **Step 2: Run** `pytest tests/test_import_draft.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** `from_scc_pdf` (read widgets with `fitz`, invert the mapping), `from_text`, and the route; imported fields get provenance `applicant_said` for form widgets and `ai_draft` for text-derived facts; leave `declarations` and `professional_flags` untouched.
- [ ] **Step 4: Run** `pytest tests/test_import_draft.py export/test_export.py -v`. Expected: PASS.
- [ ] **Step 5: Commit** the new files and the small `fill_scc.py` edit — `feat: import a started variance draft`.

### Task 5: Completeness, reviewer and export

**Files:**
- Modify: `app/backend/completeness.py` (add an item per unmet condition when `variance.relied_on` is set; group `precedent`, status `uncertain`/`missing`, message names the variance number and condition)
- Modify: `app/backend/reviewer.py` (summary line "Relies on STANDATA <number>: N of M conditions confirmed" and one RFI line per unmet condition; no safety claim)
- Modify: `app/backend/export/` cover-note builder (find it via `build_package`): name the variance only when all conditions are `yes`; for accepted `precedent` mitigations add the visible attribution "based on STANDATA <number>"
- Test: `app/backend/tests/test_variance_downstream.py`

**Interfaces:**
- Consumes: `variance.relied_on` shape from Task 3 and `variance_match.gaps`.

- [ ] **Step 1: Write failing tests**: `test_completeness_lists_unmet_condition`; `test_completeness_unchanged_without_relied_on` (existing sample items identical); `test_reviewer_rfi_has_line_per_unmet_condition`; `test_reviewer_text_has_no_safety_or_approval_wording` (assert none of "safe", "compliant", "approved" appear in generated lines); `test_cover_note_names_variance_only_when_all_yes`; `test_precedent_mitigation_export_has_attribution`.
- [ ] **Step 2: Run** `pytest tests/test_variance_downstream.py -v`. Expected: FAIL.
- [ ] **Step 3: Implement** the three edits, following each file's existing item/line style.
- [ ] **Step 4: Run** `pytest -q` from `app/backend`; also `python tests/eval_samples.py` and confirm seeded-defect recall stays 27/27 with 0 false alarms.
- [ ] **Step 5: Commit** the touched files — `feat: variance conditions in completeness, reviewer and export`.

### Task 6: Applicant UI

**Files:**
- Modify: `app/frontend/src/types.ts` (add `VarianceMatch`, `VarianceItem`, `ConditionAnswer`)
- Modify: `app/frontend/src/api.ts` (add `varianceMatch(id)`, `putReliedOn(id, number, answers)`, `startingPoint(id, number)`; follow the existing `newer`/mock-fallback pattern)
- Modify: `app/frontend/src/applicant.tsx` (replace `PrecedentPanel` at ~line 152 with `VarianceOutcomePanel`: outcome label and reason, variance number/edition/date/source page, per-condition yes / no / not sure control, gap list with the spec's message, "Use as starting point" for `near_miss` which shows suggestions to accept, earlier-edition label, honest empty state)
- Modify: the app start screen to add "I've already started a request" (upload the SCC PDF or paste text) calling `POST /api/applications/import`, then showing the import report (filled, not mapped, unverified citations, ticked boxes to re-confirm) before landing on the existing completeness view; add `importDraft` to `api.ts` and types
- Modify: the stylesheet that already styles `.prec` (do not touch `aftersubmit.css`/`evidence.css`)

**Interfaces:**
- Consumes: Task 3 endpoints and response shapes.

- [ ] **Step 1: Add types and api functions**; degrade gracefully if endpoints 404 (existing convention).
- [ ] **Step 2: Build `VarianceOutcomePanel`** with the states `covered | conditional | near_miss | none`; copy never says "approved", "compliant" or "safe"; `covered` reads "may be covered; the authority decides".
- [ ] **Step 3: Verify** `npm run build` in `app/frontend` passes (tsc included).
- [ ] **Step 4: Browser check** with the Playwright MCP against `npm run dev` (backend on a free port, `VITE_API_BASE` set): WOCD sample shows the card and checklist; answering all yes shows "may be covered"; one "no" shows the gap list and message; a 2019-only topic shows the earlier-edition label; an empty app shows the empty state. Save screenshots under `app/frontend/_shots/`.
- [ ] **Step 5: Commit** the touched frontend files — `feat: variance outcome panel`.

### Task 7: Held-out evaluation, docs

**Files:**
- Create: `app/backend/tests/eval_variance_data.json`, `app/backend/tests/eval_variance.py`
- Create (generated): `app/VARIANCE_EVAL.md`
- Modify: `app/STATUS.md` (append a "variance cards" entry), `docs/PRD.md` (F16 line points to the spec)

- [ ] **Step 1: Write ≥12 scenarios** in `eval_variance_data.json`, each `{description, topic?, expected_number | null, expected_hint}`: at least one per 2023 variance topic (WOCD, sprinkler-protected glazing, exhaust clearance, schedules of professional involvement), three older-edition topics expected `near_miss`, and four no-match cases (single-exit stair, EV charging, etc.) expected `none`. Write them from the variance PDFs, not from the matcher output.
- [ ] **Step 2: Implement `eval_variance.py`** to run `match_cards` on each scenario and write `VARIANCE_EVAL.md` with precision, recall, every miss and false positive listed (same honesty standard as `RETRIEVAL_EVAL.md`).
- [ ] **Step 3: Run** it; if a 2023 scenario fails, tune thresholds in `variance_match.py` only on a train subset and report on the held-out remainder; do not edit expectations to fit.
- [ ] **Step 4: Run** `pytest -q` (backend), `npm run build` (frontend); update `STATUS.md` with the final numbers.
- [ ] **Step 5: Commit** — `docs: variance card evaluation and status`.
