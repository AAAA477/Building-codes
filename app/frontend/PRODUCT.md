# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Primary: applicants preparing an alternative-solution (variance) application in Alberta: homebuilders, general contractors, manufacturers, and their architects and engineers. Most have never prepared a variance and have little code fluency. They work at a desktop browser and need to know what to do next at every moment.

Secondary: Safety Codes Officers (SCOs) and plans examiners in Edmonton, Calgary and smaller municipalities. They review files with about ten minutes each and need to see at once what is missing and where the evidence is.

## Product Purpose

Variance Workspace helps an applicant prepare a complete, code-referenced variance application before it reaches an SCO, and helps the SCO review it faster. The applicant describes a project in plain language, the tool finds the relevant code articles, fills the official Safety Codes Council variance form from verified sources, flags what is missing, and prepares a submission package. Success: fewer "more information" round trips, less repeated data entry, and faster evidence-finding in review.

The tool checks completeness, never technical correctness. Equivalent performance, engineering judgment and approval stay with registered professionals and the authority having jurisdiction.

## Positioning

Every code citation is verified against the real code text with its page number, and the official form is filled directly. A neighbouring generic AI form-filler could not truthfully claim that every article, objective and function it shows exists in the Alberta Edition, or stop where a registered professional must take over.

## Operating Context

Real Alberta documents: NBC Alberta Edition 2023 (second printing), NFC 2023 AE, NPC 2020, NECB 2020 with intent supplements; STANDATA variances, interpretations and bulletins; Safety Codes Council Variance Form (Part 1 Sections A-D, Part 2 for the officer); Calgary's Request for Specific Variance and variance guide; Edmonton's Point Access Block guide, emergency-services guideline and policy bulletins. Applications are one form per issue; Calgary ties a variance to a permit number; Edmonton routes some files to peer review with Fire Rescue Services.

## Capabilities and Constraints

- Guided four-step applicant flow; reviewer view with checklist, mind map and evidence panel; PDF export of the filled SCC form; submission package (zip with form, cover note, email draft) that a person sends.
- Any NBC, NFC, NPC or NECB article can be searched and added to Section C; the single-exit stair is the one guided topic with professional-stop rules.
- Hosted LLM (Azure OpenAI) drafts explainers and suggestions; offline fallback exists. All AI output is a draft, labelled, and never auto-applied.
- The tool never signs, ticks consent, or sets declarations for a user.
- NECB data tables are kept as text; NFC intent statements come from the 2020 supplement. Undecided: final product name, Edmonton's own form (none found).

## Brand Commitments

Independent product named "Variance Workspace" (working name). It uses no government, Safety Codes Council or event logos and must not imply official status. Identity should come from the subject (code documents, forms, inspection practice), not from borrowed government branding.

## Evidence on Hand

Real documents in `files/` (listed above), 127 STANDATA documents, 39 Calgary advisories, 9 Edmonton policy bulletins. No real past applications are available (confidential); samples are derived from STANDATA variances and the Edmonton guide with identity fields left blank. No real users have tested the product yet.

## Product Principles

1. Applicant first: every screen says what to do next, in plain language.
2. Show the source: any code claim shows its article, page and verbatim text.
3. Completeness, not correctness: never state that a design is safe, equivalent or approved.
4. Stop where a professional must take over, and say who and what.
5. Humans sign; AI only drafts, and every draft is visibly a draft.

## Accessibility & Inclusion

WCAG AA contrast, keyboard operable, state shown by text and icon not colour alone, plain language for non-experts, desktop browser (1280px and up) is the supported size.
