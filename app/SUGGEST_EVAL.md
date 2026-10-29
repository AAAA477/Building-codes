# AI suggestions: measured accuracy

Reproduce: `cd app/backend && .venv/Scripts/python.exe -X utf8 tests/eval_suggest.py` (writes `tests/eval_suggest_results.json`; Azure OpenAI used when configured). Unit tests: `tests/test_suggest.py`.

## What is guaranteed by construction (not by the model)
- Extracted facts are kept only if the value literally appears in the applicant's text (digits or number words, commas normalised) and, for model output, the quoted words are a real substring of that text. Everything else is dropped, never guessed.
- Model-written rewrites go through checks (numbers, safety claims, article numbers). One stricter retry, then `rejected` with reasons (value is null).
- Mitigations and precedents are retrieved, not generated. Each carries a quote that is checked to be a real substring of the source page/chunk.
- Nothing says a design is safe, equivalent or approved. Accepting a suggestion records provenance `ai_draft`; declarations/signatures/professional flags return 409.

## 1. Fact extraction on real text (26 passages, 25 labelled facts)
Passages: 520-character windows from real STANDATA variances/interpretations/bulletins, Edmonton policy and guides (`app/data/corpus/precedents_chunks.jsonl`; windows and hand-labelled truth in `tests/eval_suggest_data.json`). Truth = values literally stated in the passage for storeys, building area (m2), sprinklered, renovation (a set of acceptable values per field, because passages often state limits). 4 passages are deliberate negatives (no project fact stated). Labels were written by hand after reading the windows, before scoring.

| Mode | Precision | Recall | Fabricated (value not literally in text) |
|---|---|---|---|
| Offline regex | 24/25 = 0.96 | 24/25 = 0.96 | 0 of 25 = 0% |
| Azure OpenAI + literal filter | 23/23 = 1.00 | 23/25 = 0.92 | 0 of 23 = 0% |

Azure varies run to run (three runs: 20, 22, 23 correct of 25 labelled; precision 1.00 each time; recall 0.80, 0.88, 0.92). The 0.92 above is the last run; treat recall as roughly 0.8 to 0.9.

Failures (honest):
- Offline wrong: a passage about "a sprinkler system" in a building access policy was read as `sprinklered = true` (the words appear, but the passage is not saying the building is sprinklered). This is a literal-but-wrong-meaning error: the literal check cannot catch it, so the UI shows the quote and asks the applicant to confirm.
- Offline missed: "one (1) storey" (digit in brackets after the number word).
- Azure missed (varies by run): "6-storeys ... 12-storeys" window, a renovation mention, and a "0.4 m2 of net floor space" value. The model returns null when unsure, which costs recall, not precision.
- Caveat: the passages are code/variance prose, not applicant descriptions; applicant text is usually simpler, but this was not measured on real applicant text (none exists in the data package). Limits ("not more than 3 storeys") are indistinguishable from project facts by wording; the quote is shown so the applicant can see this.

## 2. Adversarial test (fake model returning invented content)
A fake LLM was fed an applicant text ("5 storey ... 4 units per floor ... one exit stair") and returned bad rewrites.

Rewrite checks: 13 bad outputs (invented floor count, area, distance, unit count; invented article NBC 3.4.2.9; invented 9.99.9.9; a real but uncited article 3.4.2.1; "this design is safe"; "equivalent or better"; "will comply"; "will be approved"; "meets the code"; a combined case). Result: **13/13 rejected (100%)**, after the one stricter retry. 2 faithful control rewrites (including number words "five"/"four") were accepted (0 false rejections).

Fact extraction: 7 invented model facts (wrong numbers, right number with a fabricated quote, invented sprinklered/renovation/units). Result: **7/7 dropped (100%)**.

Limit of this test: it is 20 hand-written cases. The safety-claim check is a regex and will miss paraphrases not in its list (for example "this arrangement poses no hazard"). It is a backstop, not proof; the UI also labels every suggestion as a draft and a person accepts it.

## 3. improve_text on 10 real passages (Azure)
Pass all checks first time: **8/10**. Pass after one regeneration: **2/10**. Rejected: **0/10** (earlier run: 7 / 3 / 0). Regeneration was triggered by the model adding a number or wording flagged by the checks; the stricter prompt fixed it both times. These are real code passages, not applicant prose; no claim is made that the rewrites are better than the original, only that they add no unsupported number, article or safety claim.

## 4. Other kinds
- `mitigations`: options come from `stair_module.json` (Edmonton PAB guide / emergency-services guideline); each quote is extracted from the source PDF page and checked as a real substring (unit test). No performance values or equivalence statements are offered for the single-exit stair.
- `similar_precedents`: BM25 retrieval over the precedents corpus; snippet is checked to be a substring of the indexed chunk. Relevance is not measured here; a precedent does not mean the application is accepted.
- `missing_info`: deterministic from the completeness items; the "why it matters" text is fixed wording per section (authored here, not code text).

## Known issues
- `tests/test_any_topic.py` has 3 failing search tests (`guard height for deck`, `backflow prevention`, `lighting power density office`) where search returns nothing; this is in the corpus search index, not in the suggestion code (those tests do not touch it). Other tests pass (67 passed); `eval_samples.py` 27/27.
