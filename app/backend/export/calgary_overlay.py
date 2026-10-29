"""City of Calgary 'Request for Specific Variance' (revision R2014-06) overlay.

The Calgary PDF IS fillable (18 widgets, see app/data/forms/calgary_form_fields.json), so it is filled in place.
Narratives are composed only from structured application data; gaps are marked '[not provided]'.
The signature field and office-use Variance Number are never filled.
"""
import os
import re
import pymupdf
from ._pdfutil import set_widget, Flow, clean

FORM = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "forms",
                                     "calgary_request_for_specific_variance.pdf"))
NP = "[not provided]"
DISCLAIMER = "Completeness check only; this text restates applicant-supplied and code-lookup data and is not a determination of safety or equivalence."


def _v(x):
    x = clean(x).strip()
    return x if x else NP


def compose_calgary_fields(app: dict) -> dict:
    ap, pr, loc, var = (app.get(k) or {} for k in ("applicant", "project", "location", "variance"))
    alt = var.get("proposed_alternative") or {}
    acc = var.get("acceptable_solution") or {}
    arts = acc.get("articles") or []

    code = clean(var.get("code_or_standard")).strip() or NP
    if arts:
        code += " - Article(s) " + ", ".join(clean(a) for a in arts)
    else:
        code += " - Article(s) " + NP

    d = ["Project: " + _v(pr.get("description")) + "."]
    bits = []
    if pr.get("occupancy"):
        bits.append("occupancy " + clean(pr["occupancy"]))
    if pr.get("storeys") is not None:
        bits.append(f"{pr['storeys']} storey(s)")
    if pr.get("building_area_m2") is not None:
        bits.append(f"building area {pr['building_area_m2']} m2")
    if pr.get("units_per_floor") is not None:
        bits.append(f"{pr['units_per_floor']} unit(s) per floor")
    if pr.get("sprinklered") is not None:
        bits.append("sprinklered" if pr["sprinklered"] else "not sprinklered")
    if pr.get("new_or_renovation"):
        bits.append(clean(pr["new_or_renovation"]))
    d.append("Project data: " + ("; ".join(bits) if bits else NP) + ".")
    d.append("Provision to be varied: " + (", ".join(clean(a) for a in arts) if arts else NP)
             + ". Acceptable-solution explanation: " + _v(acc.get("explanation")))
    d.append("Work described / proposed alternative: " + _v(alt.get("summary")))
    details = "\n".join(d)

    r = []
    sc = var.get("section_c") or []
    if sc:
        r.append("Objectives, functions and intent of the provisions varied (code attribution):")
        for row in sc:
            tag = "" if row.get("verified") is True else " [UNVERIFIED]"
            r.append(f"- {_v(row.get('article'))}{tag}: objective {_v(row.get('objective'))}; function {_v(row.get('function'))}; "
                     f"intent: {_v(row.get('intent'))}")
    else:
        r.append("Objectives, functions and intent of the provisions varied: " + NP)
    mits = alt.get("mitigations") or []
    if mits:
        r.append("Mitigations proposed by the applicant:")
        for m in mits:
            ev = ", ".join(clean(e) for e in (m.get("evidence_ids") or [])) or NP
            r.append(f"- {_v(m.get('label'))}: {_v(m.get('detail'))} (evidence: {ev})")
    else:
        r.append("Mitigations proposed by the applicant: " + NP)
    r.append("Whether the alternative provides an equivalent level of safety is for the authority having jurisdiction and "
             "the applicant's design professional to determine. " + DISCLAIMER)
    reason = "\n".join(r)

    docs = []
    for row in app.get("section_d") or []:
        docs.append(f"{_v(row.get('document_name'))} (by {_v(row.get('responsible_party'))}; status: {_v(row.get('status'))})")
    support = "; ".join(docs) if docs else NP

    return {"code_or_standard": code, "details_of_variance": details,
            "reason_for_variance": reason, "supporting_documentation": support}


def _ymd(s):
    m = re.match(r"\s*(\d{4})-(\d{1,2})-(\d{1,2})", clean(s))
    return m.groups() if m else None


def fill_calgary(app: dict, out_path: str) -> dict:
    warnings, filled = [], {}
    doc = pymupdf.open(FORM)
    pages = list(doc)  # keep page refs alive so widgets stay bound
    widgets = {w.field_name: w for p in pages for w in p.widgets()}
    ap, loc = app.get("applicant") or {}, app.get("location") or {}
    nar = compose_calgary_fields(app)
    cont = []

    def put(name, value, max_fs=10, min_fs=5.5, long_title=None):
        value = clean(value).strip()
        if not value:
            return
        ok = set_widget(widgets[name], value, max_fs=max_fs, min_fs=min_fs)
        filled[name] = widgets[name].field_value
        if not ok:
            warnings.append(f"Calgary field '{name}' text too long for the box; truncated there, full text on attached sheet.")
            cont.append((long_title or name, value))

    put("Permit Number", loc.get("permit_number"), 12, 6)
    ymd = _ymd(ap.get("date_of_request"))
    if ymd:
        for k, v in zip(("Year", "Month", "Day"), ymd):
            put(k, v, 12, 6)
    elif ap.get("date_of_request"):
        warnings.append("date_of_request not in YYYY-MM-DD form; Year/Month/Day left blank.")
    owner = ap.get("owner_representative") or ap.get("owner_name")
    put("Name of owner or owners agent requesting variance", owner, 10, 6)
    put("Email address", ap.get("email"), 10, 6)
    put("Mailing Address", ap.get("mailing_address"), 10, 6)
    put("Code or Standard to be Varied", nar["code_or_standard"], 9, 5.5, "Code or Standard to be Varied")
    put("Details of Variance", nar["details_of_variance"], 8, 5.5, "Details of Variance")
    put("Reason for Variance", nar["reason_for_variance"], 8, 5.5, "Reason for Variance")
    put("Supporting Documentation", nar["supporting_documentation"], 8, 5.5, "Supporting Documentation")
    put("Municipal Address", loc.get("municipal_address"), 12, 6)
    put("Lot", loc.get("lot"), 12, 6)
    put("Block", loc.get("block"), 12, 6)
    put("Plan", loc.get("plan"), 12, 6)
    put("Printed Name of owner or owners agent", owner, 10, 6)

    if cont:
        fl = Flow(doc, doc.page_count, "ATTACHED SHEET to Calgary Request for Specific Variance (R2014-06)")
        fl.write("Full text of fields that did not fit the form boxes", 13, bold=True, gap=8)
        for title, text in cont:
            fl.write(title, 11, bold=True, gap=2)
            fl.write(text, 9, gap=8)
    warnings.append("Signature of owner/agent and office-use Variance Number left blank. Form revision R2014-06.")
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    doc.save(out_path, garbage=3, deflate=True)
    doc.close()
    return {"path": os.path.abspath(out_path), "warnings": warnings, "filled_fields": filled, "narratives": nar}
