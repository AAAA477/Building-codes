# Knowledge graph evaluation

Files: `backend/kg.py` (API), `backend/build_kg.py` (builder), `data/corpus/kg.json` (+ `kg_report.json`), `backend/routes_graph.py`, `backend/tests/test_kg.py`, `backend/tests/eval_kg.py` (reproduces every number below; seed 7).
Everything is derived from the corpus files; no edge is hand-written.

## 1. Stats

| Nodes | n | Edges | n |
|---|---|---|---|
| article (NBC/NFC/NPC/NECB, all divisions) | 3539 | parent_of (Part>Section>Subsection>Article, objective tree) | 4670 |
| part / section / subsection | 47 / 245 / 886 | attributed_to (article -> objective or function, with sentence numbers) | 16551 |
| objective / function | 92 / 119 | xref (regex, target must exist, source sentence stored) | 3021 |
| precedent document | 173 | cites (document -> NBC article, with pages) | 1973 |

Xref breakdown: 2,135 NBC->NBC, 481 NFC->NFC, 268 NECB->NECB, 69 NPC->NPC, and 68 cross-code (mostly NFC->NBC "of Division B of the NBC(AE)"). 28% of xref targets (836) are subsection/section nodes (expanded to member articles at lower weight). Zero unresolved objective/function codes. Attribution string `noncombustible` (parser artifact in NBC data) is skipped.
Precedent docs: 144 PDFs have verified `articles_cited`; the rest are added from `standata_index.json` only when not already present (none duplicated).

## 2. Sanity (hand judged, HUB_MAX=30)

Edge type "objective" = same function+objective pair (weight higher) or same objective, only when attributed to <= 30 articles.

| Article | Verdict |
|---|---|
| NBC 3.4.2.1 min. exits | xref 3.3.1.3 Means of Egress, 3.3.4.4 Egress from Dwelling Units: relevant. Shared F06-OS3.7: 3.4.1.2 Separation of Exits, 3.4.1.5, 3.4.3.3 Exit Width Reduction: relevant. No precedents cite it. |
| NBC 9.9.10.1 egress windows | xref 9.5.1.2 Combination Rooms (relevant), 9.10.14.4 / 9.10.15.4 (cite it; weakly relevant). Precedents: 9.8.8.1 Guards, 9.9.9.1, 9.8.8.3 co-cited in Edmonton WOCD policy and STANDATA window variance: relevant (this is exactly the real co-citation). Objective neighbours: 10.6.6.1 Exit Door Hardware plausible. |
| NBC 9.8.8.1 guards | xref 4.1.5.14 Loads on Guards, 9.8.8.5 Openings in Guards, 9.8.8.6 Climbing: relevant. Precedent 9.9.10.1, 9.8.8.3: relevant. No objective neighbours (all its pairs are hubs). |
| NBC 3.2.5.15 FD connections | xref 3.2.5.5 Location of Access Routes: relevant; 9.10.1.3: weak. Objective F06-OS1.1: 3.2.5.9 Standpipe System Design, 3.2.6.2 Limits to Smoke Movement: plausible. |
| NFC 6.2.1.1 extinguisher ITM | Objective F82-OS3.2: NFC 6.4.1.1, 2.9.3.1, 6.5.1.1 (ITM of other systems): relevant on the shared maintenance function; 2.6.1.4 Chimneys: not relevant. |
| NPC 2.6.2.12 backflow preventers | All top results NPC 2.6.2.x (Back-Siphonage, Backflow from Fire Protection, Vacuum Breakers, Hose Bibb): relevant. |
| NECB 4.2.1.1 exit signs | xref 4.3.1.2: relevant. Objective results are the whole lighting-power articles (F94-OE1.1, 35 articles before hub cut): mostly relevant to lighting but generic. |
| NBC 3.3.1.5 egress doorways | xref 3.3.1.3, 3.3.1.6 Travel Distance, 3.4.2.2: relevant. Shared F10-OS1.5 (46 articles, now cut as hub) gave 10.6.5.x and 3.1.3.x: irrelevant noise; that is why HUB_MAX was lowered from 60 to 30. |
| NBC 9.10.14.4 exposing face | xref 3.2.5.12 sprinklers, 9.10.13.5/.7 closures, 9.9.10.1: relevant. |
| NBC 3.1.17.1 occupant load | No xref. Shared F72-OH2.1 gives 3.2.1.5 Fire Containment in Basements, 10.5.2.1 Number of Fixtures: weak/irrelevant (the attribution is genuinely shared but semantically distant). |

Failures found: (a) common objectives return arbitrary members (mitigated by hub cutoff and 1/log weighting, not eliminated); (b) ranges like "Articles 3.2.2.39. to 3.2.2.41." only link the endpoints; (c) the Notes ("A-" appendix notes) are not mined, so no defined_by / applies_with edges; (d) a "Subsection 1.1.3." mentioned in Division B text resolves within the same division, which can be wrong for Division A references without explicit "of Division A"; (e) co-citation in broad documents (errata, users guide, >40 articles) is ignored on purpose (DOC_MAX=40).

## 3. Held-out test (precedents)

101 documents have >= 2 verified cited articles. For each trial: hide one cited article at random, expand (hops=1, limit 10) from the remaining cited NBC articles, check whether the hidden one is in the top 10. The held-out document itself is excluded from the graph for the query (no leakage via its own `cites` edges).

| Method | 30-doc sample (type-stratified, 1 trial) | All 101 docs x 3 trials |
|---|---|---|
| random 10 NBC articles | 0.00 | 0.00 |
| same-subsection siblings only (random 10) | 0.10 | 0.18 |
| KG xref + shared objective only (no precedent edges) | 0.33 | 0.39 |
| KG all edges, held-out doc excluded | 0.40 | 0.70 |
| KG all edges, held-out doc and near-duplicate docs excluded (same title or Jaccard >= 0.5 of cited articles) | 0.43 | 0.51 |

Honest reading: the 0.70 is inflated by revisions and joint documents (e.g. STANDATA `bci-003` and `bci-003r1`, `variances_2014` series) that cite the same articles. The deduplicated 0.51 is the figure to trust for "an article cited in a precedent"; the code-only graph (0.39, no precedent data) is the figure for articles never cited by a precedent. By type (non-dedup, all-edge): standata_variance 0.88, standata_interpretation 0.83, edmonton_policy 0.44, standata_bulletin 0.37, calgary_advisory 0.33. Sample sizes by type are small (users_guide and nrc_background have one eligible document each, both 0).

HUB_MAX sweep (all 101 docs, dedup): 60 -> 0.485, 30 -> 0.508, 15 -> 0.528; 30 chosen as a recall/coverage compromise.

## 4. Build / size / latency

Build 2.8 s (8.3 s on the first, cold run), kg.json 3.5 MB; first-use load plus index build about 0.5 s. `expand` over the 101 real seed sets (up to 6 seeds, limit 30): median 2.8 ms, p95 10.7 ms, max 13.8 ms (< 50 ms target). Worst case measured earlier before the DOC_MAX cut, with two seeds touching a users-guide document: about 25 ms.

## Endpoints

`GET /api/graph/article/{code}/{number}`, `POST /api/graph/expand`, `GET /api/graph/stats` (routes_graph.py, mounted automatically). Division A/C articles are excluded from expansion unless `include_admin`.
