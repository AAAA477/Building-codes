"""Administrative completeness only: present / consistent / cited / attached.
Never judges whether a design is safe or adequate. Never sets declarations."""
from __future__ import annotations
import re

from models import get_path
import rules

PROF_GUIDE = "files/direct/11_Edmonton_Point_Access_Block.pdf"

# what the registered professional must address (listed only; left blank for them)
PROFESSIONAL_ADDRESS = [
    "Code analysis of the acceptable solution being varied and the alternative proposed",
    "Assumptions and limits of the analysis",
    "Testing, studies or modelling relied upon",
    "Commissioning, inspection, testing and maintenance of mitigating features",
    "Qualifications of the responsible professional (single coordinating professional, Division C 2.3.1.1)",
    "Emergency-services (fire department) access and operations considerations",
]

PRO_STOP = "A registered professional is required (Edmonton PAB guide p.8)"
PRO_CONFIRM = ("Confirm with the Safety Codes Officer whether a registered professional is required "
               "(NBC Division C 2.4.1.1)")

GROUP_ORDER = ["precedent", "citations", "alternative", "documents", "professional", "admin", "signature"]
GROUP_TITLE = {"citations": "Code articles and citations", "alternative": "Proposed alternative and evidence",
               "documents": "Supporting documents and professional", "professional": "Supporting documents and professional",
               "admin": "Administrative details", "signature": "Signatures and declarations",
               "precedent": "Precedents and policies"}

A_FIELDS = [("owner_name", "Owner name"), ("mailing_address", "Mailing address"),
            ("email", "Email"), ("date_of_request", "Date of request")]


LOOKUP_ADDRESS = [
    "A Code analysis of the methods and rationales showing the alternative achieves at least the required level of performance (Div C 2.3.1.1.(2)(a))",
    "The applicable objectives, functional statements and acceptable solutions, with assumptions, limiting factors, testing, studies or performance parameters (Div C 2.3.1.1.(3))",
    "Special maintenance or operational requirements, including commissioning (Div C 2.3.1.1.(2)(b))",
    "Qualifications, experience and background of the person(s) taking responsibility for the design (Div C 2.3.1.1.(4))",
    "Enough detail to convey design intent and support validity, accuracy, relevance and precision (Div C 2.3.1.1.(5))",
    "A single person to co-ordinate the design, Code analysis and documentation where more than one person is responsible (Div C 2.3.1.1.(6))",
]


def professional_flags(app: dict) -> list:
    if rules.mode_of(app) == "lookup":
        # Not a stop: whether a registered professional is needed depends on the project; the SCO confirms.
        return [{
            "id": "pf-confirm-professional",
            "reason": ("Confirm with the Safety Codes Officer whether registered-professional involvement is required for this project. "
                       "NBC(AE) 2023 Division C 2.4.1.1.(1) lists buildings for which involvement of a registered professional is not required "
                       "(by occupancy, storeys and area); 2.4.1.1.(3) requires drawings and specifications for other buildings to be authenticated "
                       "by registered professionals; 2.4.1.1.(4) lets the authority having jurisdiction require professionals where size or complexity "
                       "may give rise to special safety concerns; 2.4.2.2.(1) has the owner retain a coordinating registered professional "
                       "for projects within 2.4.1.1.(3) (NBC_2023AE_2nd_printing.pdf pp.739-741). "
                       "Whatever the answer, the documentation for any alternative solution must address (Div C 2.3.1.1): "
                       + "; ".join(LOOKUP_ADDRESS) + ". This tool does not decide whether a professional is required and writes no analysis."),
            "article_refs": ["C:2.4.1.1", "C:2.4.2.2", "C:2.3.1.1"],
            "stop": False,
        }]
    if app.get("variance", {}).get("topic") != rules.SUPPORTED_TOPIC:
        return []
    return [{
        "id": "pf-single-exit-stair",
        "reason": ("A registered professional (qualified Fire Protection or Life Safety Code Consultant) must prepare "
                   "the Alternative Solution for a single-exit stair / Point Access Block "
                   f"(Edmonton PAB guide, {PROF_GUIDE}, pp.4 and 8). This tool stops here and does not produce "
                   "engineering analysis. The professional must address: " + "; ".join(PROFESSIONAL_ADDRESS) + "."),
        "article_refs": list(rules.candidate_articles(app)),
        "stop": True,
    }]


def _item(items, id_, label, section, status, message, node=None):
    items.append({"id": id_, "label": label, "section": section, "status": status,
                  "message": message, "node_id": node or id_})


def _txt(v):
    """True only for real content: placeholders like '[to be completed by applicant]' do not count."""
    if not isinstance(v, str):
        return False
    s = v.strip()
    return s != "" and not re.fullmatch(r"\[[^\]]*\]", s)


_ART_RE = re.compile(r"^\d+\.\d+\.\d+\.\d+")


def _nbc_article_check(art: str):
    """None if the string is not an NBC Division B article we can check; else True/False (exists in indexed text)."""
    if not isinstance(art, str):
        return None
    if re.match(r"^(NFC|NPC|NECB)\b", art.strip(), re.I):  # other national codes: verify against that code's own index
        try:
            from corpus import verifier_codes
            hits = verifier_codes.find_citations(art)
            return bool(all(h["exists"] for h in hits)) if hits else None
        except Exception:
            return None
    if not _ART_RE.match(art.strip()):
        return None
    try:
        from corpus import verifier
        base = _ART_RE.match(art.strip()).group(0)  # drop any sentence suffix such as .(1)
        return bool(verifier.article_exists(base))
    except Exception:
        return None


def _classify(it: dict) -> None:
    """Add group + priority (1 = check first ... 5 = last) from the item id, unless already set (overlays)."""
    i = it["id"]
    if it.get("group") and it.get("priority"):
        it.setdefault("severity", "confirm")
        return
    if i.startswith("SIGN."):
        g, pr = "signature", 5
    elif i.startswith("A.") or i in ("B.location", "B.permit_number"):
        g, pr = "admin", 4
    elif i.startswith("C.row") and it["status"] == "uncertain" and it.get("message", "").startswith("Article exists"):
        g, pr = "citations", 3  # verified citation, objectives to confirm
    elif i.startswith("C.article") or i.startswith("C.row") or i == "C.table":
        g, pr = "citations", 1
    elif i == "C.code_or_standard":
        g, pr = "citations", 2
    elif i == "B.part":
        g, pr = "citations", 4
    elif i.startswith("C."):
        g, pr = "alternative", 2
    elif i in ("D.documents", "D.professional_named"):
        g, pr = ("documents" if i == "D.documents" else "professional"), 1
    elif i == "D.professional":
        g, pr = "professional", 2
    elif i.startswith("D.doc."):
        g, pr = "documents", 2
    elif i.startswith("B."):
        g, pr = "alternative", 4  # project facts
    else:
        g, pr = "admin", 4
    if it["status"] in ("uncertain", "needs_professional") and pr < 3 and not i.startswith("C.row"):
        pr += 1
    it.setdefault("group", g)
    it.setdefault("priority", pr)
    it["severity"] = ("blocker" if it["status"] == "missing" and it["priority"] <= 2 and
                      it["group"] in ("citations", "documents", "professional", "alternative") else "confirm")


def _summarise(items: list) -> dict:
    def m(sel):
        sub = [i for i in items if sel(i)]
        return {"done": sum(1 for i in sub if i["status"] == "complete"), "total": len(sub)}
    admin = m(lambda i: i["group"] == "admin")
    sig = m(lambda i: i["group"] == "signature")
    tech = m(lambda i: i["group"] not in ("admin", "signature"))
    gi = {g: n for n, g in enumerate(GROUP_ORDER)}
    open_ = sorted((i for i in items if i["status"] != "complete"),
                   # an advisory "may already be covered" note ranks just behind hard defects at the same priority
                   key=lambda i: (i["priority"] + (1 if i["id"].startswith("P.") else 0), gi.get(i["group"], 9)))
    seen, uniq = set(), []
    for i in open_:
        fam = re.sub(r"\.\d+$", "", i["id"])
        if fam in ("C.mitigation", "D.doc", "C.row", "C.article") and fam in seen:
            continue
        seen.add(fam)
        uniq.append(i)
    open_top = uniq
    top = [{"id": i["id"], "label": i["label"], "why": i.get("message") or i["status"],
            "group": i["group"], "priority": i["priority"], "severity": i["severity"]} for i in open_top[:5]]
    ph = []
    def add(t):
        if t not in ph:
            ph.append(t)
    for i in open_:
        n, g = i["id"], i["group"]
        if g == "citations" and n != "B.part" and i["priority"] <= 2:
            add("Code citations need attention")
        elif n == "D.documents":
            add("supporting documents are missing")
        elif n == "D.professional_named":
            add("no professional is named")
        elif n == "D.professional":
            add("registered-professional involvement needs confirming")
        elif g == "documents":
            add("some supporting documents are incomplete")
        elif g == "alternative" and n.startswith("C."):
            add("the proposed alternative or its evidence is incomplete")
    def bad(group):
        return [i for i in open_ if i["group"] == group]
    if not ph and bad("admin"):
        ph.append("only administrative details remain")
    if not ph and bad("signature"):
        ph.append("only signatures remain")
    ph = ph[:3]
    if ph:
        txt = ph[0][0].upper() + ph[0][1:]
        if len(ph) > 1:
            txt += ", " + ", and ".join([", ".join(ph[1:-1])] * bool(ph[1:-1]) + [ph[-1]]) if len(ph) > 2 else " and " + ph[1]
        txt += "."
    else:
        txt = "No open items found."
    nb = sum(1 for i in open_ if i["severity"] == "blocker")
    nc = len(open_) - nb
    if nb:
        headline = f"Not ready: {nb} blocker{'s' * (nb != 1)}, {tech['done']} of {tech['total']} technical checks done."
    elif nc:
        headline = f"No blockers: {nc} item{'s' * (nc != 1)} to confirm, {tech['done']} of {tech['total']} technical checks done."
    else:
        headline = "Ready for review: 0 blockers."
    return {"detail": f"{txt} {tech['done']} of {tech['total']} technical checks done.", "blockers": nb,
            "meters": {"admin": admin, "technical": tech}, "signatures": sig,
            "top_issues": top, "headline": headline}


def compute(app: dict) -> dict:
    items: list = []
    a, p, loc, var = app.get("applicant", {}), app.get("project", {}), app.get("location", {}), app.get("variance", {})
    # Section A
    for k, lab in A_FIELDS:
        ok = _txt(a.get(k))
        _item(items, f"A.{k}", lab, "A", "complete" if ok else "missing", "" if ok else f"{lab} not provided")
    if _txt(a.get("owner_representative")):
        _item(items, "A.owner_representative", "Owner representative", "A", "complete", "")
    # Section B
    ok = bool(loc.get("jurisdiction_wide")) or _txt(loc.get("municipal_address")) or \
        all(_txt(loc.get(k)) for k in ("lot", "block", "plan"))
    _item(items, "B.location", "Project location", "B", "complete" if ok else "missing",
          "" if ok else "Municipal address or legal description (or jurisdiction-wide) required")
    _item(items, "B.permit_number", "Permit number", "B",
          "complete" if _txt(loc.get("permit_number")) or loc.get("jurisdiction_wide") else "uncertain",
          "" if _txt(loc.get("permit_number")) else "No permit number given; confirm if one exists")
    guided = rules.mode_of(app) == "guided"
    for k, lab in [("description", "Project description"), ("occupancy", "Occupancy"),
                   ("storeys", "Number of storeys"), ("building_area_m2", "Building area"),
                   ("units_per_floor", "Units per floor"), ("sprinklered", "Sprinklered (yes/no)"),
                   ("new_or_renovation", "New construction or renovation")]:
        if k == "units_per_floor" and not guided:
            continue  # stair-specific question
        v = p.get(k)
        ok = _txt(v) if isinstance(v, str) else v is not None
        _item(items, f"B.{k}", lab, "B", "complete" if ok else "missing", "" if ok else f"{lab} not provided")
    det = rules.determine_part(p)
    if p.get("part") and det["part"] and p["part"] != det["part"]:
        _item(items, "B.part", "Part 3 / Part 9", "B", "uncertain",
              f"Entered Part {p['part']} differs from rule-based Part {det['part']} ({det['basis'][0]['article']})")
    elif p.get("part") or det["part"]:
        _item(items, "B.part", "Part 3 / Part 9", "B", "complete" if p.get("part") else "uncertain",
              f"Rule-based result: Part {det['part']}; not yet confirmed by applicant" if not p.get("part") else "")
    else:
        _item(items, "B.part", "Part 3 / Part 9", "B", "missing", det["message"])
    # Section C
    _item(items, "C.code_or_standard", "Code or standard varied", "C",
          "complete" if _txt(var.get("code_or_standard")) else "missing",
          "" if _txt(var.get("code_or_standard")) else "Code/standard and edition not stated")
    arts = get_path(var, "acceptable_solution.articles", []) or []
    _item(items, "C.articles", "Acceptable-solution articles cited", "C", "complete" if arts else "missing",
          "" if arts else "No articles cited")
    for i, art in enumerate(arts):
        chk = _nbc_article_check(art)
        if chk is False:
            _item(items, f"C.article.{i}", f"Cited article {art}", "C", "missing",
                  f"Article {art} not found in the indexed NBC(AE) 2023 text; citation must be corrected", f"C.article.{i}")
    ok = _txt(get_path(var, "acceptable_solution.explanation", ""))
    _item(items, "C.explanation", "Acceptable-solution explanation", "C", "complete" if ok else "missing",
          "" if ok else "Explanation not provided")
    ok = _txt(get_path(var, "proposed_alternative.summary", ""))
    _item(items, "C.alternative", "Proposed alternative summary", "C", "complete" if ok else "missing",
          "" if ok else "Proposed alternative not described")
    mits = get_path(var, "proposed_alternative.mitigations", []) or []
    _item(items, "C.mitigations", "Mitigating features listed", "C", "complete" if mits else "missing",
          "" if mits else "No mitigating features listed")
    for i, m in enumerate(mits):
        ev = m.get("evidence_ids") or []
        _item(items, f"C.mitigation.{i}", f"Evidence for: {m.get('label') or m.get('id') or i + 1}", "C",
              "complete" if ev else "uncertain", "" if ev else "No evidence document referenced")
    rows = var.get("section_c") or []
    if not rows:
        _item(items, "C.table", "Section C table (article, objective, function, intent)", "C", "missing",
              "Section C not generated")
    for i, r in enumerate(rows):
        ver = bool(r.get("verified"))
        resolved = _txt(r.get("objective")) and r.get("objective") != "unresolved"
        msg = ("" if ver else "Citation not verified against indexed NBC(AE) 2023 text; blocks export")
        if ver and not resolved:
            msg = ("Article exists, but the NBC attributes no objectives to it here; the root-article rule applies "
                   "(use the objectives attributed to the root article) and a person should confirm")
        _item(items, f"C.row.{i}", f"Section C: {r.get('article') or i + 1}", "C",
              "complete" if ver and resolved else "uncertain", msg, f"C.row.{i}")
    # Professional (Section D)
    flags_all = professional_flags(app)
    flags = [f for f in flags_all if f.get("stop")]
    if flags_all and not flags:
        _item(items, "D.professional", "Registered professional involvement", "D", "uncertain",
              PRO_CONFIRM + " (Div C 2.4.2.2 also applies). The Div C 2.3.1.1 documentation is needed either way.")
    if flags:
        _item(items, "D.professional", "Registered professional involvement", "D", "needs_professional",
              PRO_STOP + ". They prepare the Alternative Solution and the analysis (fire protection / life safety code consultant); this tool writes none of it.")
    # Section D documents
    docs = app.get("section_d") or []
    if flags and not any(_txt(d.get("responsible_party")) for d in docs):
        _item(items, "D.professional_named", "Registered professional named in Section D", "D", "missing",
              "No registered professional or organisation is named as responsible for any supporting document "
              "(Edmonton PAB guide p.8 requires professional involvement)")
    if not docs:
        _item(items, "D.documents", "Supporting documents listed", "D", "missing", "No supporting documents listed")
    for i, d in enumerate(docs):
        nm = d.get("document_name") or d.get("id") or f"Document {i + 1}"
        st = d.get("status")
        problems = []
        if not _txt(d.get("document_name")):
            problems.append("No document name is given.")
        if not _txt(d.get("responsible_party")):
            problems.append("No responsible professional is named yet.")
        if flags and not d.get("professional_required") and st != "provided":
            problems.append("Not marked as needing a registered professional; please confirm (Edmonton PAB guide p.8).")
        if st == "provided":
            s = "complete" if not problems else "uncertain"
        elif d.get("professional_required"):
            s = "needs_professional"
            if not problems:
                problems.append("Not yet prepared.")
        elif st == "to_be_prepared":
            s = "uncertain"
            problems.append("Not yet prepared.")
        else:
            s = "missing"
            problems.append("Not provided.")
        _item(items, f"D.doc.{i}", f"Document: {nm}", "D", s, " ".join(problems), f"D.doc.{i}")
    # Declarations: present, never set by us
    dec = app.get("declarations", {})
    for k, lab in [("privacy_consent", "Privacy consent"), ("equal_or_better_ack", "Equal-or-better acknowledgement"),
                   ("owner_signed", "Owner signed")]:
        _item(items, f"SIGN.{k}", lab, "SIGN", "complete" if dec.get(k) else "missing",
              "" if dec.get(k) else "To be completed by the owner (not set by this tool)")
    if _txt(a.get("owner_representative")):
        _item(items, "SIGN.rep_signed", "Representative signed", "SIGN", "complete" if dec.get("rep_signed") else "missing",
              "" if dec.get("rep_signed") else "To be completed by the representative (not set by this tool)")
    try:  # attached-file readability findings (evidence_items.py)
        import evidence_items
        items.extend(evidence_items.items(app))
    except ImportError:
        pass
    try:  # consistency / trap checks (text vs fields, units, edition, date) live in consistency.py
        import consistency
        items.extend(consistency.items(app))
    except ImportError:
        pass
    try:  # conditions of the relied-on STANDATA variance (variance_items.py)
        import variance_items
        items.extend(variance_items.items(app))
    except ImportError:
        pass
    try:  # open officer questions (questions_items.py)
        import questions_items
        items.extend(questions_items.items(app))
    except ImportError:
        pass
    try:  # jurisdiction overlay checks (Edmonton, Calgary, SCC) live in overlays.py when present
        import overlays
        items.extend(overlays.items(app))
    except ImportError:
        pass
    pct = round(100 * sum(1 for i in items if i["status"] == "complete") / len(items)) if items else 0
    for it in items:
        _classify(it)
    extra = _summarise(items)
    return {"percent": pct, "items": items, "professional_flags": flags_all, **extra,
            "note": "Completeness only: this measures whether required items are present, not whether the design is safe or adequate.",
            "professional_must_address": PROFESSIONAL_ADDRESS if flags else (LOOKUP_ADDRESS if flags_all else [])}
