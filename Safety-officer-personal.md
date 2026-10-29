# Safety Officer — Personal Notes on Alternative Solutions (Variances)

*Written in the first person, as a Safety Codes Officer (SCO) in the building discipline in Alberta. Everything below comes from the source PDFs in `files/`. Where I checked the actual code text I say **[verified]**. Where I am inferring or could not check, I say **[inference]** or **[unverified]**.*

---

## 0. The one-paragraph version

The NBC(AE) lets you comply in two ways: follow the **acceptable solutions** in Division B, or prove an **alternative solution** performs *at least as well as* the acceptable solution it replaces. In Alberta, the Safety Codes Act calls this a **variance**. Only an SCO, an Administrator or the Safety Codes Council can issue one, and only if it gives "approximately equivalent or greater safety performance". The applicant carries the burden of proof. I check that the application is **complete, correctly referenced and supported by the right professional**. The applicant's engineer or architect owns technical correctness. If the file doesn't let me decide, I ask for more information or refuse.

---

## 1. The legal chain (what authorizes what)

| Layer | Provision | What it does |
|---|---|---|
| **Act** | *Safety Codes Act* RSA 2000 c S-1, **s.38(1)** | An Administrator or SCO **may** issue a written variance if they're of the opinion it gives "approximately equivalent or greater safety performance with respect to persons and property". **[verified]** |
| | s.38(2) | Terms and conditions may be attached. |
| | s.38(3) | An SCO who issues a variance **must notify an Administrator**. |
| | s.38(5) | A decision by an Administrator is final and not appealable. |
| | s.38(6)–(7) | A refusal needs **written notice**. The applicant has **30 days** to appeal to the Council. |
| | s.10 | Owners, contractors, designers and others must comply with the variance's terms. **Compliance with a variance is deemed compliance with the Act.** |
| | s.51–52 (esp. 52(2)(b.1)) | The Council can confirm a refusal, or revoke it and issue the variance itself on terms it sets. |
| | s.62 | An Administrator may enter a variance in the **variance register** (information system). |
| **Code** | NBC(AE) 2023 **Div A 1.2.1.1** | Defines the two compliance routes (see §3). |
| | NBC(AE) **Div B 1.1.2.1** | Says where objectives and functional statements are attributed (the tables). |
| | NBC(AE) **Div C 2.3.1.1** | Tells the applicant what documentation an alternative solution must carry. |
| | NBC(AE) **Div C 2.4** | Professional involvement and design review. |
| **Form** | Safety Codes Council *Variance Form for Proposed Alternative Solution* | The standard application (Parts 1, 2a, 2b, 3). |
| **Local** | City guides and policies | Calgary and Edmonton add process and policy on top of the form (§9). |

**Terminology note:** Calgary's guide says SCC policy calls "alternative solutions" **"variances"**, and uses "variance" for both. The code says "alternative solution". The Act says "variance". They are the same thing. **[verified, Calgary guide p.1]**

**Not in my package:** the Building Code Regulation (AR 5/2024), Exemption Regulation (AR 351/2003) and Permit Regulation (AR 204/2007). open.alberta.ca only links to King's Printer order pages. I cannot quote them from these files **[unverified]**.

---

## 2. The three Divisions of the NBC(AE)

| Division | Contains | How I use it in a variance |
|---|---|---|
| **A** — Compliance, Objectives and Functional Statements | Scope, the compliance rule (1.2.1.1), definitions (1.4), **Part 2 = Objectives**, **Part 3 = Functional Statements** | The *yardstick*: what the code is trying to achieve. |
| **B** — Acceptable Solutions | The technical requirements (Parts 3–11), e.g. Part 3 fire/egress, Part 9 housing, Part 6 HVAC. At the end of each Part, an **attribution table** links each provision to objectives and functional statements. | The *benchmark*: what the applicant is departing from. |
| **C** — Administrative Provisions | Permits, documents, **2.3 Alternative Solutions**, **2.4 Professional Design**, Appendix B schedules | The *paperwork rules*. |

Key rule from the Code's own preface: objectives and functional statements are **entirely qualitative and are not meant to be used on their own** in design or approval. **Division B supplies the quantitative target.** **[verified, NBC(AE) front matter + Note A-1.2.1.1.(1)(b)]**

---

## 3. The central sentence — Div A 1.2.1.1

> 1) Compliance with this Code shall be achieved by
> a) complying with the applicable acceptable solutions in Division B, **or**
> b) using alternative solutions that will achieve **at least the minimum level of performance required by Division B** in the areas defined by the **objectives and functional statements attributed to the applicable acceptable solutions**.
> 2) … the objectives and functional statements attributed to the acceptable solutions in Division B shall be those referred to in **Subsection 1.1.2. of Division B**.

**[verified]**. Read it as three tests:

1. **Which acceptable solution(s) is being replaced?** (the benchmark)
2. **What objectives and functional statements are attributed to it?** (the *areas of performance* in scope)
3. **Does the alternative perform *as well as* that benchmark in those areas?** The test is "as well as", not "well enough". (Note A-1.2.1.1.(1)(b))

### Four consequences from Note A-1.2.1.1.(1)(b) that I rely on
- **Lowest-performing option sets the bar.** If Division B offers several designs of unequal performance, the lowest-performing compliant design sets the minimum level for evaluating the alternative.
- **Several acceptable solutions replaced by one design?** Performance must be at least the overall level of all of them taken together.
- **Only the attributed areas count.** If the replaced provisions are attributed to OS1 but *not* OP1, the applicant doesn't have to show a benefit under OP1. (So I should check *which* objectives are attributed and not demand more.)
- **Intent statements are advisory.** They are "not a legal component of the Code" but "can help establish performance targets".

---

## 4. Decoder: what the codes and labels mean

### 4.1 Article numbering
`9.9.4.4.(2)(a)` = Part **9**, Section **9**, Subsection **4**, Article **4**, Sentence **(2)**, Clause **(a)**. Citations in Section C of the form are normally at **Article (and sentence)** level.

### 4.2 Objectives (Div A, Part 2, Article 2.2.1.1) — "what harm are we preventing?"
Top-level groups **[verified]**:

| Code | Objective | Sub-objectives (examples) |
|---|---|---|
| **OS** | Safety (injury to people) | **OS1 Fire safety** (OS1.1 fire occurring … OS1.2 spread beyond origin … OS1.3 collapse due to fire … OS1.4 fire safety systems failing … **OS1.5 persons delayed or impeded in moving to a safe place in a fire**) · **OS2 Structural safety** (OS2.1 overload … OS2.3 damage/deterioration … OS2.5 instability) · **OS3 Safety in use** (OS3.1 tripping/falling … OS3.7 persons delayed or impeded moving to a safe place in an emergency) · **OS4** Resistance to unwanted entry · **OS5** Safety at construction/demolition sites |
| **OH** | Health | OH1 Indoor conditions (air quality, thermal comfort, moisture contact) · OH2 Sanitation · OH3 Noise protection · OH4 Vibration/deflection · OH5 Hazardous substances containment · OH10–OH12 etc. |
| **OA** | Accessibility | OA1 barrier-free path of travel · OA2 barrier-free facilities |
| **OP** | Fire and structural protection **of the building** | **OP1** fire protection of the building (e.g. OP1.2) · OP2 structural sufficiency · OP3 protection of adjacent buildings from fire · OP4 … from structural damage |
| **OE** | Environment | OE1 Resources (energy etc.) |

The wording always contains **"limit the probability"** and **"unacceptable risk"**. Codes don't eliminate risk. They fix the *residual risk that Canadians have accepted* once Division B is followed.

### 4.3 Functional statements (Div A, Part 3, Article 3.2.1.1) — "what must the building do?"
Numbered **F01–F130**, grouped by tens. The groups I see most **[verified]**:

| Range | Theme | Examples |
|---|---|---|
| F01–F06 | Fire | F01 minimize accidental ignition · F02 limit severity/effects of fire · **F03** retard fire effects beyond origin · **F04** retard failure/collapse due to fire · F05 retard fire effects on egress facilities |
| F10–F13 | Egress / notification | **F10** facilitate timely movement of persons to a safe place · F11 notify persons · F12 facilitate emergency response |
| F20–F23 | Structure | **F20** support and withstand expected loads · F21 dimensional change · F22 limit movement |
| F30–F36 | Safety in use | F30 tripping/falling · F34 resist unwanted entry · F36 trapped in confined spaces |
| F40–F46 | Contaminants / sanitation | F40 limit contaminants · F46 potable water |
| F50–F56 | Indoor environment | F50 breathable air · F51 temperatures · F52 humidity · F55 air transfer through separators |
| F60–F63 | Water / moisture | F61 resist ingress of precipitation/water/moisture · F62 dissipate moisture · F63 limit condensation |
| F70–F74 | Facilities / access | F73 access and circulation · F74 persons with disabilities |
| F80–F82 | Durability / performance | F80 resist deterioration |
| F90–F100 | Energy | F90–F93 air leakage and thermal transfer · F95–F99 energy demand/efficiency |

### 4.4 The attribution tag: `[F10-OS3.7]`
A tag in a Division B attribution table is **[Functional statement – Objective]**, e.g.:
- `[F05-OS1.5]` = "retard the effects of fire on emergency egress facilities", serving "limit probability that persons are delayed moving to a safe place during a fire".
- `[F02,F04-OS1.2,OS1.3]` = *both* F02 and F04 serving *both* OS1.2 and OS1.3 (a combined tag, seen in CWC guide for Table 3.10.1.1).

**Where to find them:** each Part of Division B ends with an *Objectives and Functional Statements* section containing the table. Examples I found **[verified]**: Table **3.10.1.1** (Part 3), 4.5.1.1, 5.10.1.1, 6.10.1.1, 7.3, 8.3, **9.38.1.1** (Part 9), 10.8, 11.3. Div B **1.1.2.1.(1)** lists these sections.

**Gotchas:**
- Some provisions are *modifiers or pointers* and carry **no attribution**. Then use the attribution of the provision they point to (Note A-1.1.2.1.(1)).
- Some whole subsections have **no attributions** (CWC guide: most of 3.1.5). Practice there is to use the attribution of the lead sentence (3.1.5.1.(1)) as the "purpose" of the subsection. **[CWC guide p.6–7]**
- The table pages are column-interleaved in text extraction. **Read the PDF page itself** before relying on a row.

### 4.5 Intent statements — "why is this article here?"
- Published separately, not in the code: **Supplement to the NBC 2020: Intent Statements** (also NECB, NFC, NPC). **[verified]**
- Format per provision: `Provision: 9.9.4.3.(2)` → `Intent 1/2…` → `Objective OS1` → `Attributions [F05-OS1.5]` → intent text written as a causal chain ("to limit the probability of X, which could lead to Y, which could lead to harm to persons").
- Advisory only; they explain the *risk being avoided*, not the legal requirement.
- **Only Parts 2–9 of NBC Division B have intent statements.** Parts 10–11 and Division C do not. **[verified]**
- **No intent statements exist for requirements unique to the NBC(AE)** **[verified, NBC(AE) preface]**.
- **Edition mismatch risk:** the supplement is for **NBC 2020 (national)**, while we apply the **2023 Alberta Edition**. Numbering can differ. Example I checked: the supplement's `9.9.4.4.(1)` is about wired glass/glass block in exterior-wall openings, while in the AE, **9.9.4.4 is "Openings Near Unenclosed Exterior Exit Stairs and Ramps"** (Edmonton policy B23-05 and the AE attribution table agree). **Never copy an intent statement into a file without confirming the AE article means the same thing.** **[verified for this example; generalization is my inference]**

### 4.6 Acronyms I keep seeing
| Term | Meaning |
|---|---|
| **AHJ** | Authority having jurisdiction (municipality, accredited agency, etc.) |
| **SCO** | Safety codes officer (designated under the Act) |
| **SCC** | Safety Codes Council (appeals, form owner, publishes variances) |
| **NBC(AE)** | National Building Code – 2023 Alberta Edition (2nd printing is the edition to reference) |
| **STANDATA** | Alberta Municipal Affairs publications: variances (BCV), interpretations (BCI), bulletins (BCB), errata (BCE) |
| **Part 9 / Part 3** | Housing and small buildings / larger or higher-risk buildings (Part 3 = "Fire Protection, Occupant Safety and Accessibility") |
| **RSET / ASET** | Required / Available Safe Egress Time (used in the Edmonton rowhouse analysis) |
| **CCMC** | Canadian Construction Materials Centre (product evaluations) |
| **EFRS** | Edmonton Fire Rescue Services |

---

## 5. What a complete application must contain

### 5.1 Div C 2.3.1.1 — the code's documentation requirements **[verified, matches the real code text]**
The person requesting the alternative solution provides documentation that:
1. includes a **Code analysis** of the methods and rationales showing the alternative achieves at least the Div A 1.2.1.1.(1)(b) level of performance;
2. includes **special maintenance or operational requirements**, including commissioning, needed for the solution to keep complying after construction;
3. in the Code analysis, **identifies applicable objectives, functional statements and acceptable solutions**, plus assumptions, limiting factors, test procedures, engineering studies or performance parameters;
4. includes the **qualifications, experience and background** of the person(s) responsible for the design;
5. is detailed enough to convey **design intent** and support the **validity, accuracy, relevance and precision** of the analysis;
6. names **one coordinating person** where more than one person is responsible for different aspects.

Why the code wants this on file long-term (Note A-2.3.1): maintenance obligations, future code-compliance assessments for sale, alteration design, and the risk that a later **alteration invalidates the alternative solution**. The documentation is the "paper trail" that a rational process led to equivalency.

### 5.2 The Safety Codes Council form — section by section
Source: `07_Variance_Form.pdf` (SCC form) and the challenge scope's version in Appendix 1.

| Form part | What's asked | What I check |
|---|---|---|
| **Part 1 §A — Applicant** | Owner, owner's representative, mailing address, date of request | Names and contact complete; representative authorised. |
| **Part 1 §B — Details** | Permit number (if applicable), **legal description** (Alberta Township System: QTR/SEC/TWP/RGE/MER; or Lot/Block/Plan), municipal address; a tick-box for "submitted to the SCC for **jurisdictional** use" (the scope's version says "for a Jurisdiction and **not site-specific**") | Permit linkage (Calgary will not issue a variance number without a permit number); legal description matches the permit; site-specific vs. jurisdiction-wide is clear. |
| **Part 1 §C — Justification** (table: *Applicable Code or Standard · Attributions to Acceptable Solutions: Article(s), Objective, Function, Intent statements*) | One row per code/standard article being varied, with its attributed objectives, functions and intents | Edition is correct (NBC(AE) 2023, 2nd printing). **Articles exist and mean what's claimed.** Objectives and functions match the attribution table for *that* article. Intent statements taken from the right edition. Every article touched by the departure is listed. |
| **Part 1 §D — Supporting Documentation** (name of document; **named professional or organisation responsible**) | The evidence list | Each document named, dated and attributed to a person or firm. Sealed where professional involvement is required. Documents actually support the claims in §C. |
| **Signatures and Disclosures** | Privacy notice (Protection of Privacy Act); owner/representative signatures | Signed and dated by owner and representative. Applicant understands some non-personal information may be published on the SCC website. |
| **Part 2(a) — Acceptance** (SCO) | Reviewer info, authority, SCO name, **certification and designation numbers**, statement of equivalent-or-greater performance, **conditions** | I complete this only if satisfied. List every condition. |
| **Part 2(b) — Refusal** (SCO) | Tick-boxes for the reasons for refusal + free text; served in writing | See §7. |
| **Part 3 — Appeal** | 30 days; to the SCC; written Notice of Appeal with copy of Part 1 and Part 2(b), grounds, contact details, **fee** | Make sure the refusal notice is clear enough to survive appeal. |

**Version differences I noticed:** the challenge scope's Appendix version of the form and the standalone SCC PDF word things differently. The SCC PDF says "**approximately equivalent or greater safety performance**" (matching the Act). The scope's appendix version says "**equal or better performance**". Under the Act, the legal test is *approximately equivalent or greater*. **Use the Act's wording.** Also, the scope's version adds a "Yes" acknowledgement that the alternative "provides equal or better performance". The SCC PDF's Part 1 doesn't have that line.

---

## 6. How an application moves — and where I fit

```
Applicant idea ──► Early meeting with SCO / AHJ ──► Is a variance the right path?
                                                       │
                      (permit applied for? file manager / inspector contacted)
                                                       ▼
                     Prepare: code analysis + supporting docs (professional if required)
                                                       ▼
          Submit completed form (Part 1) + all supporting docs to the SCO
                                                       ▼
        Review by SCO (+ internal specialists, e.g. fire dept in Edmonton for emergency-services issues)
                                                       ▼
   ┌────────────────────┬────────────────────────────┬─────────────────────────┐
   │ Request more info  │ ACCEPT: Part 2(a) +        │ REFUSE: Part 2(b) +     │
   │ (loop back)        │ conditions; notify         │ written notice served;  │
   │                    │ Administrator (s.38(3))    │ 30-day appeal (s.38(7)) │
   └────────────────────┴────────────────────────────┴─────────────────────────┘
```
Calgary-specific rules from its guide (Nov 2023) **[verified]**:
- A variance **must be tied to a building permit**. Pre-application discussion is fine, but no variance number without a permit number.
- Variances are **site-specific**. More than one permit or building needs a separate request each.
- **One form per issue.** Several articles for one issue (e.g. travel distance to an exit) can share a form. A different issue (e.g. roof rating) needs its own.
- Calgary appeal fee: **$500**, within 30 days of service.
- Professional-involved projects: supporting documents must be **stamped and sealed**.
- Some form wording is fixed and must not be altered.
- A variance is **not** for product approval, for approving untested products, or for waiving the required level of safety.

---

## 7. My review checklist (completeness first, not technical correctness)

**A. Gatekeeping**
- [ ] Is this actually a variance matter, or is it a **product evaluation** question (CCMC / approved organization) or an existing **STANDATA variance or policy** already covers it? (§8, §9)
- [ ] Permit number present or, if not site-specific, correctly flagged?
- [ ] One issue per form?
- [ ] Right edition: **NBC(AE) 2023, 2nd printing**.

**B. Part 1 §C — the attribution table**
- [ ] Each article cited **exists** in the AE and is the one being departed from.
- [ ] Objective and function columns match the **Part's attribution table** for that article, not guessed.
- [ ] If an article has no attribution, did the applicant explain which related article's attribution they used (and why)?
- [ ] Intent statements cited are from the supplement, for the right edition, and not claimed for AE-only provisions.
- [ ] Benchmark acceptable solution named, with the level of performance it provides.
- [ ] Effect on **other** NBC(AE) requirements addressed (Calgary guide asks for this).

**C. Div C 2.3.1.1 content**
- [ ] Code analysis present, with methods and rationale.
- [ ] Assumptions, limits, test procedures and engineering studies identified.
- [ ] Maintenance and operational conditions (including commissioning) stated.
- [ ] Designer qualifications present; single coordinator named if several designers.

**D. Professional involvement (Div C 2.4)**
- [ ] Is a **registered professional** required? (§8)
- [ ] If so, are the documents **authenticated** (sealed/stamped) per the Architects Act or Engineering and Geoscience Professions Act?
- [ ] Does the work itself require engineering judgement the applicant is trying to supply without a professional?

**E. Supporting documentation (§D)**
- [ ] Each document named, dated, with responsible person.
- [ ] Summary of any report included in the form, with outcomes stated.
- [ ] Documents referenced in the rationale are actually attached.

**F. Signatures and disclosures**
- [ ] Owner and representative signed and dated; privacy acknowledgement done.

### Refusal grounds on the form (check all that apply) **[verified]**
1. **Information in Part 1 is incorrect.**
2. **Information is not sufficient or complete** for me to decide.
3. **The alternative will not provide approximately equivalent or greater safety performance.**

Note for my own practice: grounds 1–2 are *administrative/completeness*, which is exactly where the challenge says most first-time failures happen. Ground 3 is the substantive judgement and I should be able to say *why* (which objective or function falls short). A written refusal must be **served** (Part 2(b) records date and format).

---

## 8. When must a professional be involved? (Div C Section 2.4)

**[verified in the AE text]**
- **2.4.1.1.(1)** — registered professional **not** required for (summarised): 
  - assembly/care/treatment/detention ≤3 storeys with small areas (≤300 m² one storey, ≤150 m² two, ≤100 m² three);
  - **single-family dwelling**, or **multiple-family dwelling with ≤4 dwelling units** (secondary suites are *not* counted as dwelling units, 2.4.1.1.(2));
  - residential/hotel ≤3 storeys with areas ≤400/200/130 m²;
  - business/mercantile/industrial ≤3 storeys with areas ≤500/250/165 m²;
  - farm buildings not for public use; relocatable industrial camp buildings.
- **2.4.1.1.(3)** — all other buildings: drawings and specifications **authenticated** by registered professional(s).
- **2.4.1.1.(4)** — **I** (the AHJ) may require professionals for "size or complexity … special safety concerns", even below the thresholds.
- **2.4.1.2** — Part 4 structural design must be by a registered professional.
- **2.4.1.3** — Automatic fire suppression system: owner must retain a professional to design, field-review and witness testing.
- Fire alarm designs follow (2.4.1.4).
- **2.4.2** — "Schedules of Professional Involvement" (Appendix B). I haven't read Appendix B yet **[unverified]**.
- The challenge scope also wants the tool to flag when **evaluating** an alternative solution constitutes the practice of engineering. The CWC guide says alternative solutions "should be prepared by a registered professional" and bear the seal (BC context, but the principle is shared). **[inference for Alberta]**

**Practical rule I'll use:** exemption from professional involvement under 2.4.1.1(1) concerns *the building's drawings*. It does **not** mean the alternative-solution analysis needs no expertise. If the supporting evidence involves engineering analysis (fire modelling, structural calculations, building-science evaluation), expect a sealed report whichever category the building falls in.

---

## 9. Reading precedent: STANDATA and local policy

### 9.1 STANDATA (Alberta Municipal Affairs) — 127 files in `standata/`
| Type | Code | What it is | How I use it |
|---|---|---|---|
| **Variance** | `23-BCV-xxx` | A pre-accepted variance issued by the **Provincial Building Administrator**, "applicable throughout the Province". | If the applicant's issue is already covered, I direct them to it instead of a custom variance. |
| **Interpretation** | `23-BCI-xxx` | Regulator's reading of a code requirement. | Helps resolve ambiguity *before* deciding it's a variance case. |
| **Bulletin** | `23-BCB-xxx` | Notices, transitions and practice guidance. | Context and procedure. |
| **Errata** | `23-BCE-xxx` | Corrections to the code text. | **Check before quoting an article.** |
| Joint documents | e.g. `23-BCV-013 / 19-EDB-002`, `23-BCI-012 / 20-PCB / 20-GCB / 24-ECB` | Cross-discipline (building + fire + plumbing + gas + electrical + elevating devices) | Remember my discipline isn't the only one that may be involved. |

**Anatomy of a STANDATA variance** (example: **23-BCV-017, unvented roof assemblies**, Sept 2025): **Purpose → Discussion → Code References (verbatim article and Note text) → Application (scope) → Variance (the accepted solution, with required documents) → "applicable throughout the Province" → signature by the Provincial Building Administrator.** The variance wording repeats the Act's test: "approximately equivalent or greater safety performance with respect to persons and property". The accepted solution there rests on a named evaluation report (RDH Building Science), supplied with the permit application.

**Correction to the data package's description:** the package says STANDATA variances show "the article, the objective, the functional statement and the scope of the accepted solution". In the example I read, I found the **article text, the Note and the scope**, but **no objective or functional-statement codes** printed. I only read one variance in full, so other variances may differ **[partially verified]**. Don't expect STANDATA to hand over the attributions. Look them up in the attribution tables.

Folders: variances 2023 (19), 2019 (33), 2014 (23); interpretations 2023 (40); bulletins 2023 (11); errata 2023 (1). Older variances (2014, 2019) are tied to older code editions. Their *logic* is useful, but the article numbers may not carry over to the 2023 AE.

### 9.2 Local procedure and policy
| Document | What it tells me |
|---|---|
| **Calgary — Guide to Applying for an Alternative Solution** | Process and form-completion rules (§6). |
| **Calgary — building advisories** (39 PDFs) | Calgary's published positions (e.g. B23-014 on new products, materials and systems; B23-010 on professional involvement based on complexity; B23-013 on fire-department access to Part 9 buildings that don't face a street). **Calgary's Standing Posted Variances are published separately and I did not download them.** |
| **Edmonton — Guideline for Alternative Solutions Affecting Emergency Services (COE-IM-GUIDE-0040)** | Emergency-services impacts (firefighting access, etc.) are **peer-reviewed by SCPI and EFRS**. Alternatives showing no *additional or unique* impact versus the acceptable solution need no extra analysis. Out of scope: "High Buildings" (3.2.6). |
| **Edmonton — Point Access Block (single-stair) guide** | A pre-defined shape of acceptable argument for a recurring innovation (13 design studies). |
| **Edmonton policies B23-01, B23-02, B23-03, B23-05, B19-03, B19-04, B14-01G** | **Policy solutions** for conditions that otherwise repeatedly need variances (row-house fire separation with >2 secondary suites; window opening control devices; roof truss engineering; area separation walls; small-building fire-service access; zero-lot-line garages). |
| **Edmonton — Alternative Solution for Secondary Suites in Rowhouses** | The best worked example: 7,000+ words, RSET/ASET egress-time analysis. |

**What B23-05 teaches about the system** (Edmonton interpretation of **NBC(AE) 9.9.4.4**): the article had produced *inconsistent applications and inconsistent alternative solutions*. The city issued a policy interpretation stating the article **need not apply** where the exterior exit stair or ramp is ≤1.5 m above or ≤600 mm below adjacent grade. Result: the rule is applied consistently, and "alternative solutions have a clear threshold for application". Its Appendix A states the two compliance routes plainly: (1) comply with the prescriptive article, or (2) submit a **Request for Specific Variance** with an alternative-solution report showing how the alternative meets the objectives and functional statements of the prescriptive requirement and the minimum performance level.

**Policy vs. variance (my mental model):** if something recurs, the system tends to turn it into a **policy, standing variance, STANDATA variance or code change** rather than keep processing one-offs. Calgary's Standing Posted Variances cite 26 builders filing the same zero-lot-line request 382 times in eight months of 2017. **[from the data package narrative]**

---

## 10. Worked example — tracing one article end to end (9.9.4.4, AE)

1. **Article:** NBC(AE) Division B **9.9.4.4. Openings Near Unenclosed Exterior Exit Stairs and Ramps**. This one is **AE-specific [inference, supported by: no matching intent statement exists under that title in the national supplement]**.
2. **Attribution table** (Part 9, **Table 9.38.1.1**): the table rows are interleaved in the extract. The tags near this article read `[F05-OS1.5]` and `[F10-OS3.7]`. I would confirm the exact sentence-to-tag mapping on the PDF page before citing **[partially verified]**.
3. **Meaning of the tags:** F05 (retard fire effects on egress facilities) → OS1.5 (people delayed/impeded in fire); F10 (timely movement to a safe place) → OS3.7 (delayed/impeded in an emergency).
4. **Intent statement:** the national NBC 2020 supplement has nothing for this AE article under this number. The text it has at `9.9.4.4` is about wired glass. So for an applicant, the Section C "Intent statements" cell may legitimately be *"none published — AE-unique"* and the rationale must come from the attributions plus the municipal policy context.
5. **Local overlay:** Edmonton **B23-05** removes the need to apply the article below/above the height thresholds, so a variance isn't needed in those cases.
6. **Applicant's variance (if outside the thresholds):** states the departure; names the benchmark (e.g. protected openings per 9.10.13-type provisions); shows equal or better protection for the egress path (OS1.5 / OS3.7); attaches sealed analysis where appropriate.

---

## 11. Things that would trip me — and the applicant — up

1. **Appendix 4 of the Challenge Scope is a paraphrase, not the code.** It presents "Division A 1.2.1.1.(3)", "1.2.1.2.(1)", "1.2.1.3.(1)", "Division C 2.2.1.2.(1) Variances", and a "Safety Codes Act 2.4.2.1.(1)". In the real NBC(AE) text I checked, **Div A 1.2.1.1 has only sentences (1) and (2)**, and the next provision is Subsection 1.2.2 (Materials, Appliances, Systems and Equipment). **Div C 2.3.1.1** *does* match the real text. The Act's variance power is in **s.38**, not a "2.4.2.1". The "approximately equivalent or greater safety performance" test is real, but it comes from **Act s.38(1)**. **Verify every citation against the source PDF before putting it in a form.** **[verified for the items named; I did not check every row]**
2. **Intent statements are for NBC 2020 and may not match AE numbering or exist for AE-only articles** (§4.5).
3. **Attribution tables are the authority for objectives/functions**. STANDATA and guides do not substitute for them.
4. **Some provisions lack attributions.** Need a reasoned fallback (§4.4).
5. **"Definitions" vs "guidance".** The CWC guide warns that AHJs often treat Appendix examples (e.g. occupancy classification examples in A-3.1.2.1.(1)) as definitions. That's a place where alternative solutions can still be argued.
6. **Edition drift.** Always: NBC(AE) 2023, **2nd printing**. Older STANDATA variances (2014, 2019) reference older articles.
7. **Variance ≠ product approval.** Product questions belong with CCMC evaluation or an approved organization (the AE's 1.2.2.2 refers to CCMC / NRC / approved organization evaluation reports). Calgary's guide says the same.
8. **Site-specificity.** A site-specific variance can't quietly cover a second permit or building.
9. **Alterations can invalidate the alternative** (Note A-2.3.1), so conditions about maintenance, operation and future change belong in the variance.
10. **Appeal asymmetry.** SCO refusals are appealable to the Council (30 days). An **Administrator's** decision is final (s.38(5)), and the form says the appeal route isn't available once an Administrator has refused in writing.
11. **Three statutes to keep distinct:** the *Act* (authority), the *code* (technical test), the *form* (evidence format). Each uses slightly different wording.
12. **Other disciplines.** Joint STANDATA items show building issues often touch fire, plumbing, gas or electrical codes. The challenge scope tells teams to start with the national building codes first.

---

## 12. What I have *not* been able to verify yet (open items)

- **Building Code Regulation (AR 5/2024)**, **Exemption Regulation**, **Permit Regulation** — not downloaded. These are where the Act's permit/variance machinery gets detail.
- **SCC "Guideline to the Variance Form"** — the link in the package returned a 404.
- **Div C Appendix B schedules of professional involvement** — not read.
- **Structural Commentaries** — named in the challenge scope, absent from the package.
- **Calgary Standing Posted Variances** — separate page, not downloaded.
- **CCMC Registry** — interactive; JSON API not queried.
- **The BTRboard worked example** — "details coming soon" in the package.
- **Whether other STANDATA variances cite objectives/functions** — I read only 23-BCV-017 in full.
- **Part 3 attribution tables** — I confirmed their existence and the tag format. I have not walked through a Part 3 article end-to-end.
- **The NECB / NFC / NPC routes** — the same objective-based logic is described in the supplements, but I focused on the NBC. The NFC and NPC apply to different disciplines and may have their own variance pathways.

---

## 13. Quick reference card

```
VARIANCE TEST   (Act s.38)  approximately equivalent OR greater safety performance
COMPLIANCE      (Div A 1.2.1.1) (a) acceptable solutions   OR   (b) alternative solution
BENCHMARK       the acceptable solution being replaced (lowest-performing compliant option sets the bar)
SCOPE OF PROOF  only the objectives + functional statements ATTRIBUTED to that solution
WHERE ATTRIBUTED  Div B, end of each Part: Table 3.10.1.1 | 4.5.1.1 | 5.10.1.1 | 6.10.1.1 | 9.38.1.1 …
TAG FORMAT      [F10-OS3.7] = [function – objective]
INTENT          separate supplement (NBC 2020); advisory; Parts 2–9 only; none for AE-unique rules
PAPERWORK       Div C 2.3.1.1: Code analysis + maintenance/operation + designer qualifications + single coordinator
PROFESSIONALS   Div C 2.4.1.1: exemptions by occupancy/size; AHJ may still require (2.4.1.1(4))
FORM            Part 1 A–D (applicant) → Part 2a accept / 2b refuse (SCO) → Part 3 appeal (30 days, SCC)
AFTER ISSUING   notify an Administrator (s.38(3)); register (s.62); compliance with variance = compliance with Act (s.10)
```

---

## 14. Where everything is on disk

`C:\Users\aaaan\Downloads\Building codes\files\`

| Folder | Contents |
|---|---|
| `direct/` | Challenge scope, Safety Codes Act, SCC variance form, CWC guide, Calgary guide, Edmonton emergency-services and point-access-block guides |
| `codes/` | NBC(AE) 2023 (2nd printing), NECB 2020, NFC(AE) 2023, NPC 2020, and the four Intent Statement supplements |
| `guides/` | Illustrated User's Guide NBC 2020 Part 9; NECB 2020 User's Guide |
| `background/` | Two NRC papers on objective-based codes and accepting alternate solutions |
| `standata/` | Variances (2014/2019/2023), interpretations, bulletins, errata |
| `calgary_advisories/`, `edmonton_policy_solutions/` | Local advisories and policy solutions |
| `pages/` | Saved HTML of web-only resources |
