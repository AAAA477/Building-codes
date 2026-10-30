# Variance card matching: held-out evaluation

Scenarios were written from the variance titles and PDFs (`tests/eval_variance_data.json`), not from matcher output. No thresholds were tuned on them. Measures whether the *right variance is offered*; says nothing about whether any design is safe.

- Covered candidates found as top hit: **10/12**
- Near-miss (earlier edition only) found, and never offered as covered: **4/4**
- No-match scenarios with no covered candidate: **4/4** (any result at all, i.e. noise: 0/4)
- Covered offered where it should not be (false covered): **0**

| scenario | expected state | expected variance | returned | result |
|---|---|---|---|---|
| wocd | covered_candidate | 23-BCV-001 | 23-BCV-001 (covered_candidate) | PASS |
| glazing | covered_candidate | 23-BCV-004 | 23-BCV-004 (covered_candidate) | PASS |
| exhaust | covered_candidate | 23-BCV-008 | 23-BCV-008 (covered_candidate) | PASS |
| slab | covered_candidate | 23-BCV-003 | 23-BCV-003 (covered_candidate) | PASS |
| unvented | covered_candidate | 23-BCV-017 | 23-BCV-017 (near_miss) | MISS |
| soffit | covered_candidate | 23-BCV-018 | 23-BCV-018 (covered_candidate) | PASS |
| racking | covered_candidate | 23-BCV-014 | 23-BCV-014 (covered_candidate) | PASS |
| greenhouse | covered_candidate | 23-BCV-011R1, 23-BCV-011 | 23-BCV-011R1 (near_miss) | MISS |
| pwf | covered_candidate | 23-BCV-012R1 | 23-BCV-012R1 (covered_candidate) | PASS |
| welding | covered_candidate | 23-BCV-010R1 | 23-BCV-010R1 (covered_candidate) | PASS |
| oilgas | covered_candidate | 23-BCV-005 | 23-BCV-005 (covered_candidate); 23-BCV-006 (near_miss); 19-BCV-009 (near_miss) | PASS |
| refrigeration | covered_candidate | 23-BCV-009 | 23-BCV-009 (covered_candidate) | PASS |
| sips | near_miss | 19-BCV-020R, 19-BCV-020 | 19-BCV-020R (near_miss) | PASS |
| tallwall | near_miss | 14-BCV-002R1, 14-BCV-002 | 14-BCV-002R1 (near_miss); 19-BCV-018R2 (near_miss) | PASS |
| masonry | near_miss | 19-BCV-018R2, 19-BCV-018R1, 19-BCV-018 | 19-BCV-018R2 (near_miss); 14-BCV-002R1 (near_miss) | PASS |
| garage | near_miss | 19-BCV-007, 18-BCV-007R1, 14-BCV-014 | 19-BCV-007 (near_miss) | PASS |
| stair | none | - | - | PASS |
| ev | none | - | - | PASS |
| solar | none | - | - | PASS |
| hottub | none | - | - | PASS |

## Notes (read before trusting the numbers)

- **Not fully held out.** The first run found 0/12 covered candidates for thin applications (no topic, no articles): the right variance was the top hit but the existing strong-match rule needs a topic or an article. After seeing that, two rules were added to `variance_match.py`: an older-edition match also offers its current-edition successor, and a clear, isolated top hit (score >= 30 and 1.5x ahead of every different variance) counts as a covered candidate for a thin application. The thresholds (30, 1.5) were chosen with these 20 scenarios in view, so the covered recall here is optimistic. The no-match and near-miss rows were not used to tune them.
- **Misses by design.** A variance with no parsed numbered conditions is never offered as covered (there is no checklist to confirm). `23-BCV-017` really has none. `23-BCV-011R1` lists its conditions under 'Option 1' and 'Option 2', which the card extractor does not split yet.
- 20 scenarios is a small sample; treat percentages as indicative.

Reproduce: `.venv/Scripts/python.exe -X utf8 tests/eval_variance.py` from `app/backend`.
