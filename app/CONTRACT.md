# Build contract (shared by all workstreams)

Product: Alberta variance application workspace. Read `docs/PRD.md` first (section 15b is the one-week cut). Demo topic: **single-exit stair** (Edmonton "Point Access Block"). Alberta only. NBC Alberta Edition 2023.

## Hard rules
1. **Real data only.** All code, article text, objectives, intents, forms and guidance come from the files under `files/` (NBC_2023AE, NBC/NECB 2020 intent supplement, NFC 2023AE, STANDATA, Edmonton and Calgary guides, `files/direct/07_Variance_Form.pdf`). Never invent an article number, objective, function code, or quote. If something cannot be found in the data, mark it `"unresolved"` and say so.
1a. **Samples and demo data come from the real data package, not invention** (per the user and `Building Codes Challenge Data Package.docx`): real STANDATA variances, the Edmonton PAB guide and its design studies, and the guides' worked examples. Identity fields (names, addresses, permit numbers, signatures, dates) stay blank or `[to be completed by applicant]`. Flawed test cases are made only by removing or corrupting fields of real-derived records. Reference the NBC(AE) 2023 **second printing**.
2. **Completeness, not correctness.** Nothing in the product says a design is safe, equivalent or approved.
3. **Provenance on every field:** `applicant` | `lookup` | `ai_draft` | `needs_professional`.
4. **Professional stop.** Never generate engineering analysis; list what the professional must address and leave it blank.
5. **Humans sign.** Never set the consent, declaration or signature fields to true on a user's behalf.
6. **Python:** use `app/backend/.venv/Scripts/python.exe` (PyMuPDF `pymupdf` and `pypdf` already installed). When running Python that reads files from `files/`, use `-I`. Do not commit anything to git. Do not modify files outside your owned paths.
7. **No LLM key is set** (ANTHROPIC_API_KEY absent). Any LLM call goes through `app/backend/llm.py` with an offline deterministic fallback so the demo runs without a key.

## Layout and ownership (disjoint, do not edit another stream's paths)
| Stream | Owns |
|---|---|
| corpus | `app/data/corpus/**`, `app/backend/corpus/**` |
| backend | `app/backend/*.py` (main, models, rules, completeness, mapgraph, llm, reviewer), `app/backend/tests/**`, `app/backend/requirements.txt` |
| export | `app/backend/export/**`, `app/data/forms/**` |
| frontend | `app/frontend/**` |
| content | `app/data/content/**`, `app/data/samples/**` |

`app/data/samples/application.example.json` already exists (shape only). Others may read it.

## Application data model (JSON, shaped like the SCC form)
```
{
  "id": str, "jurisdiction": "scc"|"calgary"|"edmonton", "edition": "NBC(AE) 2023",
  "applicant": {"owner_name","owner_representative","mailing_address","email","date_of_request"},
  "project": {"description","occupancy","storeys":int,"building_area_m2":num,"units_per_floor":int,
              "sprinklered":bool|null,"new_or_renovation":"new"|"renovation","part":"3"|"9"|null},
  "location": {"jurisdiction_wide":bool,"permit_number","municipal_address",
               "lot","block","plan","qtr","sec","twp","rge","mer"},
  "variance": {
    "topic": "single_exit_stair",
    "code_or_standard": str,
    "acceptable_solution": {"articles":[str],"explanation":str},
    "proposed_alternative": {"summary":str,"mitigations":[{"id","label","detail","evidence_ids":[str]}]},
    "section_c": [{"article","objective","function","intent","explainer",
                   "source":{"doc","page"},"verified":bool,"provenance"}]
  },
  "section_d": [{"id","document_name","responsible_party","professional_required":bool,
                 "status":"provided"|"missing"|"to_be_prepared","date"}],
  "professional_flags": [{"id","reason","article_refs":[str],"stop":true}],
  "declarations": {"privacy_consent":bool,"equal_or_better_ack":bool,"owner_signed":bool,"rep_signed":bool},
  "provenance": { "<dotted.path>": {"source":"applicant|lookup|ai_draft|needs_professional","confidence":0.0-1.0} },
  "completeness": {"percent":int,"items":[{"id","label","section":"A|B|C|D|SIGN","status":"complete|missing|uncertain|needs_professional","message","node_id"}]}
}
```

## API (FastAPI, prefix `/api`)
- `POST /applications` create · `GET /applications/{id}` · `PATCH /applications/{id}` (deep merge; sets provenance)
- `POST /applications/{id}/intake/next` body `{answer?}` → `{question|null, extracted, confidence}`
- `POST /applications/{id}/classify` → `{part, topic, confidence, supported:bool}`
- `POST /applications/{id}/section-c/generate` → fills `variance.section_c` from the verified lookup
- `GET /applications/{id}/completeness` · `GET /applications/{id}/map` → `{nodes:[{id,label,section,status,provenance,data}],edges:[{source,target}]}`
- `GET /applications/{id}/export/pdf` (fills official SCC form) · `POST /applications/{id}/submission-package` → zip + `.eml` draft
- `GET /applications/{id}/reviewer-summary` · `POST /applications/{id}/rfi-draft`
- `GET /citations/verify?article=3.4.2.1` → `{exists, edition, page, text_excerpt}`
- `GET /samples` · `GET /samples/{name}` (reads `app/data/samples/*.json`)

Node `status` colours for the map: `complete`=green, `uncertain`=amber, `missing`=red, `needs_professional`=purple, `lookup`=blue.

## Done means
Each stream ends with a short report: what exists, how it was verified against real data, what is unresolved. Add a one-line status to `app/STATUS.md` under your stream heading (create the file if absent; append only your own section).
