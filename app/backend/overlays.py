"""Jurisdiction overlay: Edmonton / Calgary / SCC checks computed from the application.

Content lives in app/data/content/overlays/<jurisdiction>.json (every check cites doc + page).
Completeness only: nothing here says a design is safe or equivalent. Unanswered questions are
'uncertain', never 'missing'; nothing is 'complete' unless the application shows it.
"""
from __future__ import annotations
import json
import re
from pathlib import Path

OVERLAY_DIR = Path(__file__).resolve().parent.parent / "data" / "content" / "overlays"
TRIGGER_FUNCS = ("F06", "F12", "F13")
ES_QUESTIONS = ("ES1", "ES2", "ES3", "ES4")
# document checks matched against Section D rows (document_name)
DOC_PATTERNS = {
    "CONSULTANT": r"fire protection|life safety code consultant",
    "FIREFLOW": r"fire ?flow|available fire flow",
    "ITM": r"\bITM\b|inspection, testing|commissioning",
    "EVIDENCE": r"assumptions|limiting or restricting|demonstrat",
    "SWEPT": r"swept path",
    "SEALED": None,
}
_cache: dict = {}


def load(jur: str) -> dict:
    jur = jur if jur in ("scc", "calgary", "edmonton") else "scc"
    if jur not in _cache:
        _cache[jur] = json.loads((OVERLAY_DIR / f"{jur}.json").read_text(encoding="utf-8"))
    return _cache[jur]


def real(v) -> bool:
    """True only for real content (placeholders such as '[to be completed by applicant]' do not count)."""
    if v is None:
        return False
    s = str(v).strip()
    return bool(s) and not s.startswith("[")


def answers(app: dict) -> dict:
    return ((app.get("overlay") or {}).get("answers")) or {}


def section_c_functions(app: dict) -> set:
    out = set()
    for r in ((app.get("variance") or {}).get("section_c")) or []:
        out.update(re.findall(r"\bF\d{2}\b", str(r.get("function") or "")))
    return out


def screen_triggered(app: dict) -> bool:
    a = answers(app)
    return bool(section_c_functions(app) & set(TRIGGER_FUNCS)) or any(a.get(q) == "yes" for q in ES_QUESTIONS) \
        or a.get("BOUNDARY") == "yes"


def _doc_status(app: dict, key: str):
    pat = DOC_PATTERNS.get(key)
    rows = [r for r in (app.get("section_d") or []) if pat and re.search(pat, str(r.get("document_name") or ""), re.I)]
    if not rows:
        return None
    if any(r.get("status") == "provided" for r in rows):
        return "provided", rows
    return "pending", rows


def _status_for(jur: str, c: dict, app: dict):
    """Return (status, message) or None to omit the item."""
    cid, kind = c["id"], c["kind"]
    a = answers(app)
    var = app.get("variance") or {}
    pr, loc = app.get("project") or {}, app.get("location") or {}
    alt = var.get("proposed_alternative") or {}
    acc = var.get("acceptable_solution") or {}
    sc = var.get("section_c") or []
    d_rows = app.get("section_d") or []
    if kind == "info":
        return None
    when = c.get("applies_when") or ""
    if when.startswith("topic:") and var.get("topic") != when[6:]:
        return None
    ans = a.get(cid)

    if jur == "edmonton":
        if cid in ES_QUESTIONS:
            if ans == "no":
                return "complete", "Answered no."
            if ans == "yes":
                return "uncertain", "Answered yes: documentation of the impact on emergency services is required (guideline pp.8-9)."
            return "uncertain", "Not answered yet" if ans is None else "Answered unsure: confirm with your professional."
        if cid == "FSTMT":
            fs = section_c_functions(app) & set(TRIGGER_FUNCS)
            if fs:
                return "uncertain", ("Section C references " + ", ".join(sorted(fs)) +
                                     ": likely impacts emergency services; documentation of the impact is required (guideline p.8).")
            if not sc:
                return "uncertain", "Section C not generated yet, so F06/F12/F13 cannot be checked."
            return "complete", "Section C does not reference F06, F12 or F13."
        if cid == "BOUNDARY":
            if ans == "no":
                return "complete", "Answered no (inside the 10-minute boundary)."
            if ans == "yes":
                return "uncertain", "Outside the boundary: address spatial separation and delayed emergency response (guideline p.15)."
            return "uncertain", "Not answered yet" if ans is None else "Answered unsure: check the map on maps.edmonton.ca."
        if cid == "PREAPP":
            if ans == "yes":
                return "complete", "Pre-application meeting booked or held (applicant statement)."
            return "uncertain", "Recommended before submission; not mandatory."
        if cid == "SWEPT":
            if ans == "no":
                return "complete", "Fire apparatus access is not varied (applicant statement)."
            if ans in ("yes",):
                ds = _doc_status(app, "SWEPT")
                if ds and ds[0] == "provided":
                    return "complete", "Swept path analysis listed as provided in Section D."
                return "needs_professional", "Fire apparatus access varied: a swept path analysis is needed and is prepared by a professional."
            return "uncertain", "Not answered yet" if ans is None else "Answered unsure."
        if when == "screen:triggered":
            if not screen_triggered(app):
                if all(a.get(q) == "no" for q in ES_QUESTIONS) and sc:
                    return None
                return "uncertain", "Needed only if the emergency-services screen is triggered; screen not complete."
            ds = _doc_status(app, cid) if cid in DOC_PATTERNS else None
            if ds and ds[0] == "provided":
                return "complete", "Listed as provided in Section D."
            if ds:
                return "needs_professional", "Listed in Section D but not yet provided."
            return "missing", "Screen triggered and no matching document is listed in Section D."
        if cid == "CONSULTANT":
            ds = _doc_status(app, "CONSULTANT")
            if ds and ds[0] == "provided":
                return "complete", "Consultant-prepared Alternative Solution listed as provided in Section D."
            if ds:
                return "needs_professional", "Consultant-prepared Alternative Solution listed but not yet provided."
            return "missing", "No Section D entry for a Fire Protection or Life Safety Code Consultant Alternative Solution."

    if jur == "calgary":
        if cid == "PERMIT":
            if real(loc.get("permit_number")):
                return "complete", ""
            return "missing", "Permit number required: a variance can only be accepted if a building permit has been applied for (guide p.2)."
        if kind in ("question", "meeting"):
            if ans == "yes":
                return "complete", "Answered yes (applicant statement)."
            if ans == "no":
                if cid == "ONEISSUE":
                    return "missing", "More than one issue: submit a separate form for each issue (guide p.2)."
                return "uncertain", "Answered no."
            return "uncertain", "Not answered yet" if ans is None else "Answered unsure."
        if cid == "CODEQUOTE":
            ok = real(var.get("code_or_standard")) and bool(acc.get("articles"))
            return ("complete", "") if ok else ("missing", "Code/standard and article numbers are needed.")
        if cid == "PROJDESC":
            return ("complete", "") if real(pr.get("description")) else ("missing", "Project description not provided.")
        if cid == "WORK":
            return ("complete", "") if real(alt.get("summary")) else ("missing", "Description of the work (proposed alternative) not provided.")
        if cid == "FUNCOBJ":
            rows = [r for r in sc if real(r.get("function")) and real(r.get("objective"))]
            if not rows:
                return "missing", "No Section C rows with objective and function."
            if any(r.get("verified") is not True for r in rows):
                return "uncertain", "Some Section C rows are not verified against the code."
            return "complete", ""
        if cid == "RATIONALE":
            return ("complete", "") if alt.get("mitigations") else ("missing", "No rationale (mitigations) entered.")
        if cid == "EVID":
            mits = alt.get("mitigations") or []
            if any(m.get("evidence_ids") for m in mits):
                return "complete", ""
            return ("uncertain", "Documents are planned in Section D but no evidence is linked to the rationale.") if d_rows \
                else ("missing", "No supporting evidence listed.")
        if cid == "SEALED":
            prof = [r for r in d_rows if r.get("professional_required")]
            if not prof and not app.get("professional_flags"):
                return "uncertain", "No professional is indicated; confirm whether one is required."
            if prof and all(r.get("status") == "provided" for r in prof):
                return "complete", "Professional documents listed as provided; confirm they are stamped and sealed."
            return "needs_professional", "Documents prepared by a professional must be stamped and sealed."
    return "uncertain", "Not assessed."


def items(app: dict) -> list:
    jur = app.get("jurisdiction") or "scc"
    out = []
    ov = load(jur)
    for c in ov.get("checks", []):
        r = _status_for(jur, c, app)
        if r is None:
            continue
        st, msg = r
        iid = f"OV.{jur}.{c['id']}"
        out.append({"id": iid, "label": c["label"], "section": "OV", "status": st, "message": msg,
                    "node_id": iid, "group": "jurisdiction", "priority": c.get("priority", 3),
                    "source": c.get("source")})
    try:  # precedents stream; optional
        from corpus import precedents
        it = precedents.coverage_item(app)
        if it:
            out.append(it)
    except Exception:
        pass
    return out


def view(app: dict) -> dict:
    """Shape for GET /overlay."""
    jur = app.get("jurisdiction") or "scc"
    ov = load(jur)
    st = {i["id"]: i for i in items(app)}
    a = answers(app)
    sections, order, questions = {}, [], []
    for c in ov["checks"]:
        it = st.get(f"OV.{jur}.{c['id']}")
        status = it["status"] if it else ("info" if c["kind"] == "info" else "not_applicable")
        chk = {"id": c["id"], "label": c["label"], "kind": c["kind"], "status": status, "why": c["why"],
               "source": c["source"], "message": it["message"] if it else ""}
        if c["id"] in a:
            chk["answer"] = a[c["id"]]
        g = c.get("group", "Checks")
        if g not in sections:
            sections[g] = {"id": re.sub(r"\W+", "-", g.lower()).strip("-"), "title": g, "checks": []}
            order.append(g)
        sections[g]["checks"].append(chk)
        if c.get("options"):
            q = {"id": c["id"], "prompt": c.get("prompt") or c["label"], "help": c["why"],
                 "options": c["options"], "source": c["source"]}
            if c["id"] in a:
                q["answer"] = a[c["id"]]
            questions.append(q)
    return {"jurisdiction": jur, "label": ov["label"], "note": ov["note"],
            "sections": [sections[g] for g in order], "questions": questions}


def question_ids(jur: str) -> set:
    return {c["id"] for c in load(jur)["checks"] if c.get("options")}


def brief(app: dict) -> dict:
    jur = app.get("jurisdiction") or "scc"
    ov = load(jur)
    pr, loc, var = app.get("project") or {}, app.get("location") or {}, app.get("variance") or {}
    NP = "not provided yet"

    def g(v):
        if not real(v):
            return NP
        parts = re.split(r"(?<=[.;])\s+", str(v).strip())
        kept = [x for x in parts if not re.search(r"to be (completed|described|determined)", x, re.I)]
        return " ".join(kept) if kept else NP
    L = [f"PRE-APPLICATION MEETING BRIEF - {ov['label']}", "", "PROJECT SUMMARY"]
    L.append(f"Description: {g(pr.get('description'))}")
    L.append(f"Occupancy: {g(pr.get('occupancy'))}; storeys: {pr.get('storeys') if pr.get('storeys') is not None else NP}; "
             f"building area (m2): {pr.get('building_area_m2') if pr.get('building_area_m2') is not None else NP}")
    L.append(f"Address: {g(loc.get('municipal_address'))}; permit number: {g(loc.get('permit_number'))}")
    L += ["", "PROVISIONS TO BE VARIED"]
    arts = (var.get("acceptable_solution") or {}).get("articles") or []
    L.append(f"{g(var.get('code_or_standard'))}, article(s): {', '.join(arts) if arts else NP}")
    summ = (var.get("proposed_alternative") or {}).get("summary")
    L.append(f"Proposed alternative: {g(summ)}")
    sc = var.get("section_c") or []
    if sc:
        L.append("Objectives/functions attributed (verify with your professional): " +
                 "; ".join(f"{r.get('article')}: {r.get('objective')} / {r.get('function')}" for r in sc))
    L += ["", "QUESTIONS TO ASK THE SAFETY CODES OFFICER"]
    n = 0
    for c in ov["checks"]:
        if c["kind"] in ("question", "meeting", "document") and not (c.get("applies_when", "").startswith("topic:")
                                                                     and var.get("topic") != c["applies_when"][6:]):
            n += 1
            L.append(f"{n}. {c.get('prompt') or c['label']} (source: {c['source']['doc']} p.{c['source']['page']})")
    if jur == "edmonton" and screen_triggered(app):
        L.append("Note: the emergency-services screen is triggered for this application; ask what documentation EFRS will expect.")
    if jur == "calgary":
        L.append(f"{n + 1}. Which building permit will this variance be tied to? (source: 09_Calgary_Alt_Solution_Guide.pdf p.2)")
    L += ["", "NOTE: " + ov["note"], "This brief is a completeness aid, not a determination of safety or equivalence."]
    return {"title": f"Pre-application brief ({ov['label']})", "text": "\n".join(L)}
