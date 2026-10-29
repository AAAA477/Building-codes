# Consistency and trap checks: evaluation

Module: `app/backend/consistency.py` (hooked into `completeness.compute` after the Section D / signature items, before overlays). Item ids start with `X.`; all are status `uncertain` (severity `confirm`); none are blockers. Wording is about completeness and consistency only, never safety, equivalence or approval. Text is stripped of `[bracketed]` placeholders before analysis.

## Checks
- `X.storeys.*`, `X.units.*`, `X.area.*`: number in description, alternative summary, explanation or mitigation detail differs from the structured field (digits or words; sq ft converted to m2 with 2% tolerance). Limits such as "up to 6 storeys", "6 storeys or less", "not more than 4 units per floor" are ignored. Only runs when the field is filled.
- `X.units_mixed.*`: imperial units (ft, feet, inches, sq ft, psi, mph, gpm, cfm, lb, degF) with no metric value in the same text.
- `X.edition.*`: NBC / National Building Code / Alberta Building Code with a year other than 2023 (NBC 2020 allowed near the word "intent"); also checked in `code_or_standard`.
- `X.place.*`: Ontario/BC building codes, OBC, BCBC, or non-Alberta places (street names like "Saskatchewan Drive" are skipped).
- `X.article.<n>`: article number cited in free text that the verifier cannot find (other codes such as NFC/NPC nearby are skipped).
- `X.owner_title`: reminder that the owner name must match the land title (shown only when a real name is entered; the tool never checks the title).
- `X.date`: date of request in the future, before 2023, or unreadable.

## Measured
- Tests: `app/backend/tests/test_consistency.py` (10 tests, positive and negative cases).
- False-alarm rate: all 10 sample files in `app/data/samples` produce 0 `X.` items (0 / 10). The good sample stays clean because placeholders and empty fields are ignored. Initial run had 1 false alarm (a `"` after a digit in an ASTM title read as inches); the inch/foot quote-mark patterns were removed.
- `tests/eval_samples.py`: unchanged; seeded-defect recall and Section C false alarms are not affected (see report for the run).

## Known limits
Regex based: odd phrasing ("twelve-floor", "G+5") is not read. An area in text that refers to one floor will be flagged for confirmation (message says so). Dates are read as YYYY-MM-DD (or any text containing a 4-digit year).
