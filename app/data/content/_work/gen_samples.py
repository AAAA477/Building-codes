"""Build REAL-DERIVED samples. No invented identities, addresses, permit numbers or dates.
Sources: Edmonton PAB guide, Edmonton emergency guideline, STANDATA 23-BCI-026/23-FCI-014,
STANDATA 23-BCV-001/-004/-008R1, NBC(AE) 2023 2nd printing (via app/data/corpus), NBC 2020 intent supplement."""
import json, copy, os, re, sys
ROOT = r"C:\Users\aaaan\Downloads\Building codes"
os.chdir(ROOT)
sys.path.insert(0, os.path.join(ROOT, "app", "data", "content", "_work"))
os.chdir(os.path.join(ROOT, "app", "data", "content", "_work"))
import intentlib
os.chdir(ROOT)

TBC = "[to be completed by applicant]"
NBC = "NBC_2023AE_2nd_printing.pdf"
ART = json.load(open("app/data/corpus/nbc_articles.json", encoding="utf-8"))
OBJ = json.load(open("app/data/corpus/objectives.json", encoding="utf-8"))
FN = json.load(open("app/data/corpus/functions.json", encoding="utf-8"))


def fixhyph(s):
    return re.sub(r"(\w)- (\w)", r"\1\2", s)


def section_c_row(article, sent, explainer):
    a = ART[article]
    s = [x for x in a["sentences"] if x["number"] == sent][0]
    note = ""
    codes = s["attributions"]
    pages = [d.get("table_pdf_page") for d in s.get("attribution_detail", []) if d.get("table_pdf_page")]
    if not codes:  # root-article rule (F6)
        first = [x for x in reversed(a["sentences"]) if x["attributions"] and x["number"] < sent] or [x for x in a["sentences"] if x["attributions"]]
        if first:
            codes = first[0]["attributions"]
            pages = [d.get("table_pdf_page") for d in first[0].get("attribution_detail", []) if d.get("table_pdf_page")]
            note = f" No objectives are attributed to Sentence ({sent}) itself; the statements shown are those attributed to Sentence ({first[0]['number']}) of the same article, the nearest preceding attributed sentence (root-article rule)."
    objs, fns = {}, []
    for c in codes:
        f, o = c.split("-", 1)
        objs.setdefault(o, None)
        if f not in fns: fns.append(f)
    ol = []
    for o in objs:
        base = re.match(r"[A-Z]+\d", o).group(0)
        t = OBJ.get(base, {}).get("title") or ""
        risk = OBJ.get(o, {}).get("text")
        ol.append(f"{o} ({t}){': ' + risk if risk and o != base else ''}")
    fl = [f"{f}: {FN[f]['text'].rstrip('.')}" for f in fns]
    ints = intentlib.get(article, sent)
    if ints and ints["intents"]:
        seen, uniq = set(), []
        for i in ints["intents"]:
            i = fixhyph(i)
            if i not in seen: seen.add(i); uniq.append(i)
        intent = " ".join(uniq) + f" [NBC 2020 Intent Statements, p.{ints['page']}; edition caveat: NBC 2020 text, attributions as in NBC(AE) 2023]"
    else:
        intent = "unresolved (no intent statement found in the NBC 2020 Intent Supplement for this provision)"
    return {"article": f"{article}.({sent})", "objective": "; ".join(ol), "function": "; ".join(fl),
            "intent": intent, "explainer": explainer + note,
            "source": {"doc": NBC, "page": pages[0] if pages else a["pdf_page"]},
            "article_page": a["pdf_page"], "verified": True, "provenance": "lookup"}


def empty_app(id_, jurisdiction):
    return {"id": id_, "jurisdiction": jurisdiction, "edition": "NBC(AE) 2023 (2nd printing)",
            "applicant": {"owner_name": TBC, "owner_representative": TBC, "mailing_address": TBC, "email": TBC, "date_of_request": ""},
            "project": {"description": "", "occupancy": "", "storeys": None, "building_area_m2": None, "units_per_floor": None, "sprinklered": None, "new_or_renovation": None, "part": None},
            "location": {"jurisdiction_wide": False, "permit_number": TBC, "municipal_address": TBC, "lot": "", "block": "", "plan": "", "qtr": "", "sec": "", "twp": "", "rge": "", "mer": ""},
            "variance": {"topic": "", "code_or_standard": "NBC(AE) 2023 Division B", "acceptable_solution": {"articles": [], "explanation": ""},
                         "proposed_alternative": {"summary": "", "mitigations": []}, "section_c": []},
            "section_d": [], "professional_flags": [],
            "declarations": {"privacy_consent": False, "equal_or_better_ack": False, "owner_signed": False, "rep_signed": False},
            "provenance": {}, "completeness": {"percent": 0, "items": []}}


PROV = lambda *k: {x: {"source": "lookup", "confidence": 1.0} for x in k}
samples = {}

# ---------------------------------------------------------------- good stair (Edmonton PAB)
g = empty_app("sample-good-stair-edmonton", "edmonton")
g["derived_from"] = [
    {"doc": "11_Edmonton_Point_Access_Block.pdf", "page": 2}, {"doc": "11_Edmonton_Point_Access_Block.pdf", "page": 4},
    {"doc": "11_Edmonton_Point_Access_Block.pdf", "page": 5}, {"doc": "11_Edmonton_Point_Access_Block.pdf", "page": 8},
    {"doc": "10_Edmonton_Emergency_Services_Guideline.pdf", "page": 8}, {"doc": "10_Edmonton_Emergency_Services_Guideline.pdf", "page": 22},
    {"doc": "ma-standata-interpretation-joint-23bci026-23fci014-2026-10.pdf", "page": 7},
    {"doc": NBC, "page": 269}, {"doc": NBC, "page": 739}]
g["source"] = {"doc": "11_Edmonton_Point_Access_Block.pdf", "page": 2}
g["note"] = "Built from the real Edmonton Point Access Block guide and STANDATA 23-BCI-026/23-FCI-014. Identity, dates, permit and project measurements are intentionally blank placeholders. Not an application that was ever filed."
g["project"].update({"description": "Residential building within the Edmonton Point Access Block guide scope: residential occupancy, 6 storeys or less, not more than 4 dwelling units per floor, served by a single exit stair (guide p.2). Project-specific values to be completed by applicant.",
                     "occupancy": "Residential"})
g["variance"].update({"topic": "single_exit_stair"})
g["variance"]["acceptable_solution"] = {"articles": ["3.4.2.1.(1)", "3.4.2.3.(1)", "3.4.4.1.(1)"],
    "explanation": "Sentence 3.4.2.1.(1): every floor area intended for occupancy shall be served by at least 2 exits, except as permitted by Sentences (2) to (4) (NBC(AE) 2023 p.269). A single-exit-stair residential building taller than the exceptions allow does not comply and relies on the alternative solution path of Division A 1.2.1.1.(1)(b); STANDATA 23-BCI-026/23-FCI-014 confirms an AHJ may accept this route (p.7). Edmonton guide p.2: Point Access Blocks over two storeys can only be built with an accepted Alternative Solution."}
g["variance"]["proposed_alternative"] = {
    "summary": "A residential single-egress-stair building (Point Access Block) that demonstrates it will perform to an equivalent or enhanced level of resiliency as a development with two egress stairs (Edmonton PAB guide p.8). The specific design is to be described by the applicant and the qualified consultant.",
    "mitigations": [
        {"id": "M1", "label": "Compartmentation", "detail": "Edmonton PAB guide p.5: the exemplar assessment identifies the main components that could lead to stair failure as relating to compartmentation and smoke management, and outlines respective risk mitigation measures. Specific compartmentation measures: " + TBC, "evidence_ids": []},
        {"id": "M2", "label": "Smoke management", "detail": "Edmonton PAB guide p.5 (same passage as M1). Specific smoke management measures: " + TBC, "evidence_ids": []}]}
g["variance"]["section_c"] = [
    section_c_row("3.4.2.1", 1, "The prescriptive 'at least 2 exits' rule for every floor area intended for occupancy. A single exit stair varies this sentence, so its attributed objectives and functions define the performance areas the alternative is compared against."),
    section_c_row("3.4.2.3", 1, "Where two exits are required, this sets the minimum distance between them. A single exit stair removes the second route this sentence relies on, so it is shown as an affected article."),
    section_c_row("3.4.4.1", 1, "Fire-resistance rating of exit separations. The Edmonton guide identifies stair failure through compartmentation as a main component of the risk (p.5), so the exit separation requirement is a likely companion article.")]
g["section_d"] = [
    {"id": "D1", "document_name": "Alternative Solution prepared by a qualified Fire Protection or Life Safety Code Consultant, including Code analysis (applicable objectives, functional statements and acceptable solutions, assumptions, limiting or restricting factors, testing procedures, engineering studies) per Division C 2.3.1.1.(2)(a), (3)", "responsible_party": TBC, "professional_required": True, "status": "to_be_prepared", "date": ""},
    {"id": "D2", "document_name": "Risk assessment and problem definition for the single exit stair (structure per Edmonton PAB guide p.5: regulatory framework, problem definition, risk assessment, alternative solutions)", "responsible_party": TBC, "professional_required": True, "status": "to_be_prepared", "date": ""},
    {"id": "D3", "document_name": "Special maintenance or operational requirements, including commissioning and inspection, testing and maintenance (ITM) documentation for systems not regulated by the NFC(AE) (Division C 2.3.1.1.(2)(b); Emergency Services Guideline p.22)", "responsible_party": TBC, "professional_required": True, "status": "to_be_prepared", "date": ""},
    {"id": "D4", "document_name": "Qualifications, experience and background of the person or persons taking responsibility for the design (Division C 2.3.1.1.(4))", "responsible_party": TBC, "professional_required": True, "status": "to_be_prepared", "date": ""},
    {"id": "D5", "document_name": "Identification of a single person to co-ordinate the design, Code analysis and documentation (Division C 2.3.1.1.(6))", "responsible_party": TBC, "professional_required": True, "status": "to_be_prepared", "date": ""},
    {"id": "D6", "document_name": "Screening against the four emergency-services questions (Emergency Services Guideline p.8-9) and, if triggered, impact on emergency services", "responsible_party": TBC, "professional_required": True, "status": "to_be_prepared", "date": ""}]
g["professional_flags"] = [{"id": "PF1", "reason": "Edmonton PAB guide p.8: professional involvement is required (registered architect and/or engineers in design and field review and in preparing the Alternative Solution), and the Alternative Solution must be prepared by a qualified Fire Protection or Life Safety Code Consultant.", "article_refs": ["2.3.1.1", "2.4.1.1"], "stop": True}]
g["provenance"] = {**PROV("variance.section_c", "variance.acceptable_solution.articles"),
                   "variance.proposed_alternative.mitigations": {"source": "lookup", "confidence": 0.6},
                   "section_d": {"source": "needs_professional", "confidence": 1.0},
                   "professional_flags": {"source": "lookup", "confidence": 1.0}}
samples["good_stair_edmonton"] = g


# ---------------------------------------------------------------- STANDATA-derived
def standata_app(id_, number, file_, pages, title, articles, summary, conds, d_items, topic):
    a = empty_app(id_, "scc")
    a["location"]["jurisdiction_wide"] = True
    a["location"]["permit_number"] = ""
    a["location"]["municipal_address"] = ""
    a["derived_from"] = [{"doc": file_, "page": p} for p in pages]
    a["source"] = {"doc": file_, "page": 1, "standata": number}
    a["note"] = f"Application-shaped record derived from real STANDATA variance {number} ({title}). The STANDATA is issued by the Provincial Building Administrator, so applicant identity, dates and signatures are blank placeholders."
    a["variance"]["topic"] = topic
    a["variance"]["acceptable_solution"]["articles"] = [f"{x[0]}.({x[1]})" for x in articles]
    a["variance"]["proposed_alternative"]["summary"] = summary
    a["variance"]["proposed_alternative"]["mitigations"] = [{"id": f"C{i+1}", "label": f"Condition {i+1} (verbatim from {number})", "detail": c, "evidence_ids": []} for i, c in enumerate(conds)]
    a["variance"]["section_c"] = [section_c_row(x[0], x[1], x[2]) for x in articles]
    a["variance"]["acceptable_solution"]["explanation"] = "Articles named in the Code References of " + number + "."
    a["section_d"] = [{"id": f"D{i+1}", "document_name": d, "responsible_party": TBC, "professional_required": False, "status": "to_be_prepared", "date": ""} for i, d in enumerate(d_items)]
    a["provenance"] = {**PROV("variance.section_c", "variance.proposed_alternative.summary"), "variance.proposed_alternative.mitigations": {"source": "lookup", "confidence": 1.0}}
    a["professional_flags"] = []
    return a


s1 = standata_app("sample-standata-23-bcv-001", "23-BCV-001", "ma-standata-variance-building-23-bcv-001-2024-04.pdf", [1, 2, 3],
    "Window opening control devices (WOCD)",
    [("9.8.8.1", 4, "Guards on openable windows in residential occupancy; the variance allows a WOCD mechanism complying with ASTM F2090."),
     ("9.8.8.1", 5, "Exception to Sentence (4) by window height. Named in the variance's Purpose; no objectives are attributed to it in the NBC(AE) table."),
     ("9.9.10.1", 1, "Egress window or door from each bedroom openable without keys, tools or special knowledge; the variance addresses the interaction with WOCD mechanisms.")],
    "A WOCD mechanism that complies with ASTM F2090 \"Standard Specification for Window Fall Prevention Devices with Emergency Escape (Egress) Release Mechanisms\" as a means of complying with the requirements of 9.8.8.1 (4) and 9.9.10.1 (1).",
    ["WOCD mechanisms are not permitted for use in adaptable or barrier-free dwelling units."],
    ["Evidence that the WOCD mechanism complies with ASTM F2090"], "window_opening_control_devices")
s1["project"]["occupancy"] = "Residential (Part 9), per STANDATA Application section"
s1["project"]["part"] = "9"

C004 = ["The assembly has been evaluated by a testing agency accredited by the Standards Council of Canada for conformance to CAN/ULC-S136:2021, \"Standard Method of Fire Test for Sprinkler Protected Window Systems\".",
        "The design, construction and installation of automatic sprinkler system conforms to NFPA 13.",
        "Sprinklers are listed as specific application window sprinklers.",
        "Glazing is heat-strengthened, tempered, or glass ceramic and fixed.",
        "Where the assembly is required to be protected from both sides, sprinklers to be installed on both sides of the glazing.",
        "If the assembly is located in a loadbearing assembly, all loadbearing components have a fire-resistance rating not less than that required for the supported assembly.",
        "The glazed assembly does not include any horizontal members interfering with uniform distribution of water over the surface of the glazing, and there are no obstructions between sprinklers and glazing that would obstruct water distribution.",
        "The fire-resistance rating of the sprinkler-protected glazing system is equal to or greater than the fire-resistance rating required for the wall assembly being installed within, and the sprinkler-protected glazed wall assemblies constructed according to the requirements of the listing of the window sprinkler.",
        "The assembly is not installed in: a firewall or within a door installed in a firewall, a building that contains a high hazard industrial occupancy, a location where there is a risk of explosion, or any part of a required exit serving: a floor area subjected to the additional requirements for high buildings as per Subsection 3.2.6., a care, treatment or detention occupancy, or a residential occupancy.",
        "Where the assembly is installed in exits not mentioned in criteria (9.) above, the exits do not comprise more than one half of the required number of exits from any floor area.",
        "The window sprinkler system: is identified at the isolation valve as supplying a window sprinkler system; is provided with a placard adjacent to the incoming water service with the following wording: \"SPECIAL WINDOW SPRINKLER HEADS ON THIS SYSTEM ARE AN INTEGRAL PART OF THE FIRE SEPARATIONS. THIS WATER SUPPLY MAY ONLY BE SHUT OFF AFTER ALL THE PROPER AUTHORITIES HAVE RECEIVED NOTICE IN WRITING\" (font 12 mm high, red with white lettering, mounted with anchors, adhesive not acceptable); provides a water supply duration for the design area that includes the window sprinklers but not less than the required fire resistance rating of the assembly."]
s2 = standata_app("sample-standata-23-bcv-004", "23-BCV-004", "ma-standata-variance-building-23-bcv-004-2024-05.pdf", [1, 2, 3],
    "Sprinkler-protected glazing in fire-resistant wall assemblies",
    [("3.1.7.1", 1, "Fire-resistance rating must be determined by testing to CAN/ULC-S101; the variance accepts sprinkler-protected glazing tested to CAN/ULC-S136:2021 instead."),
     ("9.10.3.1", 1, "Part 9 counterpart: fire-resistance and fire-protection ratings determined by test, calculation or construction tables.")],
    "Glazing assemblies are permitted to be installed for interior or exterior fire rated assemblies that are required to have a fire-resistance rating without being tested to CAN/ULC-S101, \"Standard Method of Fire Endurance Tests of Building Construction and Materials\" as required by Sentences 3.1.7.1.(1) and 9.10.3.1.(1) provided they are protected by a fixed, automatic sprinkler system and the following criteria are met.",
    C004,
    ["Evaluation report from a Standards Council of Canada accredited testing agency to CAN/ULC-S136:2021",
     "Sprinkler system design and installation conforming to NFPA 13, with listed specific-application window sprinklers",
     "Placard and isolation-valve identification of the window sprinkler system",
     "Water supply duration for the design area (not less than the required fire-resistance rating)"],
    "sprinkler_protected_glazing")
s3 = standata_app("sample-standata-23-bcv-008r1", "23-BCV-008(REV1)", "ma-standata-variance-building-23-bcv-008-rev1-2024-10.pdf", [1, 2, 3],
    "Residential exhaust outlet clearance from air intakes",
    [("9.32.3.13", 4, "Minimum 1 800 mm clearance between moist-air exhaust outlets and air intakes/vented soffits; the variance permits the clearances of its Figure A.")],
    "The minimum clearances separating exhaust outlets that discharge air containing moisture from air intakes are permitted to comply with Figure A.",
    ["The minimum clearances separating exhaust outlets that discharge air containing moisture from air intakes are permitted to comply with Figure A."],
    ["Drawing showing exhaust outlet and air intake locations against Figure A of 23-BCV-008(REV1)"],
    "residential_exhaust_outlet_clearance")
s3["project"]["occupancy"] = "Individual dwelling unit or house with a secondary suite, per STANDATA Application section"
samples["standata_23_bcv_001_wocd"] = s1
samples["standata_23_bcv_004_sprinkler_glazing"] = s2
samples["standata_23_bcv_008r1_exhaust_clearance"] = s3

# ---------------------------------------------------------------- ablated (flawed) samples + ground truth
D = lambda i, p, d, kind: {"id": i, "path": p, "description": d, "kind": kind}
seed = {"note": "Ground truth for the completeness checker. 'defects' lists only what was removed or corrupted from a real-derived record (ablation). 'baseline_placeholders' are common to every sample (identity fields are deliberately blank).",
        "baseline_placeholders": ["applicant.owner_name", "applicant.owner_representative", "applicant.mailing_address", "applicant.email", "applicant.date_of_request", "location.permit_number (stair sample)", "location.municipal_address (stair sample)", "declarations.* (all false; humans sign)"],
        "samples": {}}

f1 = copy.deepcopy(s2); f1["id"] = "sample-flawed-missing-section-d"
f1["ablation"] = {"base": "standata_23_bcv_004_sprinkler_glazing", "removed": ["section_d"]}
f1["section_d"] = []
seed["samples"]["flawed_missing_section_d"] = {"base": "standata_23_bcv_004_sprinkler_glazing", "defects": [
    D("MSD-1", "section_d", "Section D emptied: the four supporting-documentation rows (test report, NFPA 13 design, placard/isolation valve, water supply duration) were removed", "removed")]}

f2 = copy.deepcopy(g); f2["id"] = "sample-flawed-unverified-citation"
f2["variance"]["acceptable_solution"]["articles"][0] = "3.4.2.9.(1)"
f2["variance"]["section_c"][0]["article"] = "3.4.2.9.(1)"
f2["variance"]["section_c"][0]["verified"] = False
f2["variance"]["section_c"][0]["provenance"] = "applicant"
f2["ablation"] = {"base": "good_stair_edmonton", "corrupted": ["article number 3.4.2.1.(1) replaced by 3.4.2.9.(1)"]}
seed["samples"]["flawed_unverified_citation"] = {"base": "good_stair_edmonton", "defects": [
    D("UC-1", "variance.section_c[0].article", "Article 3.4.2.9.(1) does not exist in NBC(AE) 2023 (original 3.4.2.1.(1) replaced)", "corrupted"),
    D("UC-2", "variance.acceptable_solution.articles[0]", "Acceptable-solution list cites non-existent article 3.4.2.9.(1)", "corrupted")]}

f3 = copy.deepcopy(g); f3["id"] = "sample-flawed-no-professional"
f3["professional_flags"] = []
for d in f3["section_d"]: d["responsible_party"] = ""; d["professional_required"] = False
f3["ablation"] = {"base": "good_stair_edmonton", "removed": ["professional_flags", "section_d[*].responsible_party", "section_d[*].professional_required set false"]}
seed["samples"]["flawed_no_professional"] = {"base": "good_stair_edmonton", "defects": [
    D("NP-1", "professional_flags", "Professional flag removed although Edmonton requires professional involvement and a Fire Protection or Life Safety Code Consultant for a Point Access Block", "removed")] +
    [D(f"NP-{i+2}", f"section_d[{i}].responsible_party", f"No responsible professional or organisation for '{g['section_d'][i]['id']}'", "removed") for i in range(len(g["section_d"]))] +
    [D(f"NP-{i+2+len(g['section_d'])}", f"section_d[{i}].professional_required", f"professional_required flipped to false for '{g['section_d'][i]['id']}'", "corrupted") for i in range(len(g["section_d"]))]}

p = copy.deepcopy(g); p["id"] = "sample-partial-intake"
p["variance"]["section_c"] = []
p["variance"]["acceptable_solution"] = {"articles": [], "explanation": ""}
p["variance"]["proposed_alternative"] = {"summary": "", "mitigations": []}
p["section_d"] = []; p["professional_flags"] = []
p["project"]["description"] = "Residential building served by a single exit stair."
p["provenance"] = {}
p["ablation"] = {"base": "good_stair_edmonton", "removed": ["variance.acceptable_solution", "variance.proposed_alternative", "variance.section_c", "section_d", "professional_flags"]}
seed["samples"]["partial_intake"] = {"base": "good_stair_edmonton", "defects": [
    D("PI-1", "variance.acceptable_solution.articles", "No benchmark acceptable solution identified", "removed"),
    D("PI-2", "variance.proposed_alternative.summary", "Proposed alternative not described", "removed"),
    D("PI-3", "variance.proposed_alternative.mitigations", "No mitigations listed", "removed"),
    D("PI-4", "variance.section_c", "Section C empty", "removed"),
    D("PI-5", "section_d", "Section D empty", "removed"),
    D("PI-6", "professional_flags", "No professional flag", "removed"),
    D("PI-7", "project.storeys", "Storeys not answered", "baseline_blank"),
    D("PI-8", "project.units_per_floor", "Units per floor not answered", "baseline_blank"),
    D("PI-9", "project.sprinklered", "Sprinklered status not answered", "baseline_blank"),
    D("PI-10", "project.building_area_m2", "Building area not answered", "baseline_blank"),
    D("PI-11", "project.new_or_renovation", "New or renovation not answered", "baseline_blank")]}

samples.update({"flawed_missing_section_d": f1, "flawed_unverified_citation": f2, "flawed_no_professional": f3, "partial_intake": p})
seed["samples"]["good_stair_edmonton"] = {"base": None, "defects": [], "expected_notes": ["Blank identity placeholders and unsigned declarations are baseline, not injected defects.", "Section D rows are to_be_prepared; a checker should report them as needs_professional, not as injected defects.", "project.storeys/units_per_floor/sprinklered/new_or_renovation are blank in this sample as well (baseline_blank)."]}
for k in ("standata_23_bcv_001_wocd", "standata_23_bcv_004_sprinkler_glazing", "standata_23_bcv_008r1_exhaust_clearance"):
    seed["samples"][k] = {"base": None, "defects": [], "expected_notes": ["Real-derived reference record (accepted STANDATA variance). Applicant identity blank by design."]}

os.makedirs("app/data/samples", exist_ok=True)
for k, v in samples.items():
    json.dump(v, open(f"app/data/samples/{k}.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
json.dump(seed, open("app/data/samples/seeded_defects.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(sorted(os.listdir("app/data/samples")))
