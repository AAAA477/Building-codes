"""Fill the official Safety Codes Council 'Variance Form for Proposed Alternative Solution'.

Source form: app/data/forms/scc_variance_form.pdf (copy of files/direct/07_Variance_Form.pdf, 87 widgets).
Never touched: Signature1/2/6/9, Date1/Date2 (signature dates), all SCO/jurisdiction-use fields.
"""
import os
import pymupdf
from ._pdfutil import set_widget, Flow, clean

FORM = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "data", "forms", "scc_variance_form.pdf"))
SUPP = "SUPPLEMENT TO SCC VARIANCE FORM - continuation sheet (rows that did not fit the official fields)"

# Section C row widgets: row 0 has no suffix, rows 1-4 are suffixed (verified from widget dump)
C_ROWS = [("Article(s)", "Objective", "Function", "Intent statement")] + \
         [(f"Article(s){i}", f"Objective{i}", f"Function{i}", f"Intent statement{i}") for i in range(1, 5)]
D_ROWS = [("Supporting Doc", "Name Responsible")] + [(f"Supporting Doc{i}", f"Name Responsible{i}") for i in range(2, 6)]
FILLED_NEVER = {"Signature1", "Signature2", "Date1", "Date2", "Signature6", "Signature9"}
ATS = {"lot": "Lot", "block": "Block", "plan": "Plan", "qtr": "QTR", "sec": "SEC",
       "twp": "TWP", "rge": "RGE", "mer": "MER"}


def _article_text(row):
    a = clean(row.get("article") or "[article not provided]")
    c = row.get("code")
    if c and c != "NBC" and not a.upper().startswith(c.upper()):
        a = f"{c} {a}"  # non-NBC rows carry their code prefix, e.g. "NFC 2.4.1.1"
    return a if row.get("verified") is True else "[UNVERIFIED] " + a


def preparer_items(app):
    items = [d for d in app.get("section_d", []) if d.get("professional_required") and d.get("status") != "provided"]
    flags = app.get("professional_flags", []) or []
    return items, flags


def fill_scc(app: dict, out_path: str) -> dict:
    warnings, filled = [], {}
    doc = pymupdf.open(FORM)
    pages = list(doc)  # keep page refs alive so widgets stay bound
    widgets = {w.field_name: w for p in pages for w in p.widgets()}

    def put(name, value, **kw):
        assert name not in FILLED_NEVER, f"refusing to fill human field {name}"
        value = clean(value)
        if value == "":
            return None
        ok = set_widget(widgets[name], value, **kw)
        filled[name] = widgets[name].field_value
        if not ok:
            warnings.append(f"Field '{name}' text was truncated to fit; full text is on a continuation page.")
        return ok

    ap, loc, var = app.get("applicant", {}), app.get("location", {}), app.get("variance", {})
    put("Owner", ap.get("owner_name"))
    put("Owner Rep", ap.get("owner_representative"))
    put("Mailing Address", ap.get("mailing_address"))
    put("Date of Reqeuest", ap.get("date_of_request"))   # sic: field name in the official PDF
    # 'Check Box' = "submitted to the Safety Codes Council for review for jurisdictional use" (Section B).
    # It is NOT the privacy consent; mapped from location.jurisdiction_wide.
    if loc.get("jurisdiction_wide") is True:
        w = widgets["Check Box"]
        w.field_value = w.on_state()
        w.update()
        filled["Check Box"] = w.field_value
    put("Permit", loc.get("permit_number"))
    put("Municipal Address", loc.get("municipal_address"))
    for k, name in ATS.items():
        put(name, loc.get(k))
    put("Code or Standard", var.get("code_or_standard"), max_fs=10)

    # Section C
    rows = var.get("section_c") or []
    cont_c = []
    for i, row in enumerate(rows):
        full = {"article": _article_text(row), "objective": clean(row.get("objective")),
                "function": clean(row.get("function")), "intent": clean(row.get("intent"))}
        if not row.get("verified"):
            warnings.append(f"Section C row {i + 1} ({row.get('article')}) is not verified; marked [UNVERIFIED].")
        if i < len(C_ROWS):
            a, o, f, t = C_ROWS[i]
            put(a, full["article"], max_fs=9, min_fs=5)
            put(o, full["objective"], max_fs=8, min_fs=5)
            put(f, full["function"], max_fs=8, min_fs=5)
            if put(t, full["intent"], max_fs=8, min_fs=5) is False:
                cont_c.append((i + 1, full, "intent text truncated in the official field"))
        else:
            cont_c.append((i + 1, full, "more than 5 rows; official form holds 5"))
    if len(rows) > len(C_ROWS):
        warnings.append(f"Section C has {len(rows)} rows but the form holds {len(C_ROWS)}; "
                        f"{len(rows) - len(C_ROWS)} row(s) moved to continuation page(s).")

    # Section D
    drows = app.get("section_d") or []
    cont_d = []
    for i, row in enumerate(drows):
        if i < len(D_ROWS):
            a, b = D_ROWS[i]
            ok1 = put(a, row.get("document_name"), max_fs=9, min_fs=5)
            ok2 = put(b, row.get("responsible_party"), max_fs=9, min_fs=5)
            if ok1 is False or ok2 is False:
                cont_d.append((i + 1, row, "text truncated in the official field"))
        else:
            cont_d.append((i + 1, row, "more than 5 rows; official form holds 5"))
    if len(drows) > len(D_ROWS):
        warnings.append(f"Section D has {len(drows)} rows but the form holds {len(D_ROWS)}; "
                        f"{len(drows) - len(D_ROWS)} row(s) moved to continuation page(s).")

    # Printed names (not signatures)
    put("Owner Print", ap.get("owner_name"), max_fs=12, min_fs=7)
    put("Owner Rep Print", ap.get("owner_representative"), max_fs=12, min_fs=7)

    # Continuation pages go after page 2 (index 1), before the SCO-use pages
    if cont_c or cont_d:
        fl = Flow(doc, 2, SUPP)
        fl.write("Application " + clean(app.get("id", "")) + " - owner: " + clean(ap.get("owner_name")), 9)
        if cont_c:
            fl.write("Section C continuation (Article / Objective / Function / Intent statements)", 11, bold=True, gap=6)
            for n, r, why in cont_c:
                fl.write(f"Row {n}  ({why})", 9, bold=True)
                fl.write("Article(s): " + r["article"], 9, indent=10, gap=1)
                fl.write("Objective: " + (r["objective"] or "[not provided]"), 9, indent=10, gap=1)
                fl.write("Function: " + (r["function"] or "[not provided]"), 9, indent=10, gap=1)
                fl.write("Intent statement: " + (r["intent"] or "[not provided]"), 9, indent=10, gap=8)
        if cont_d:
            fl.write("Section D continuation (Supporting Documentation)", 11, bold=True, gap=6)
            for n, r, why in cont_d:
                fl.write(f"Row {n}  ({why})", 9, bold=True)
                fl.write("Name of supporting documentation: " + clean(r.get("document_name") or "[not provided]"),
                         9, indent=10, gap=1)
                fl.write("Responsible individual/professional/organization: "
                         + clean(r.get("responsible_party") or "[not provided]"), 9, indent=10, gap=8)
        warnings.append(f"{fl.pages} continuation page(s) inserted after page 2 of the form.")

    # Preparer notes (final page, outside the official form)
    items, flags = preparer_items(app)
    if items or flags:
        fl = Flow(doc, doc.page_count, "Preparer notes (not part of the official form)")
        fl.write("Preparer notes (not part of the official form)", 14, bold=True, gap=8)
        names = [clean(d.get("document_name") or d.get("id")) + " (" + clean(d.get("responsible_party") or "responsible party not named")
                 + "; status: " + clean(d.get("status")) + ")" for d in items]
        fl.write("Completeness check only. Not a determination of safety or equivalence. Professional involvement required: "
                 + ("; ".join(names) if names else "see flags below") + ".", 10, gap=8)
        for f in flags:
            refs = ", ".join(f.get("article_refs") or [])
            fl.write("- " + clean(f.get("reason")) + (f" (articles: {refs})" if refs else ""), 9, indent=8, gap=2)
    warnings.append("Signature fields, signature dates and signing acknowledgements were left blank for the owner/representative.")

    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    doc.save(out_path, garbage=3, deflate=True)
    doc.close()
    return {"path": os.path.abspath(out_path), "warnings": warnings, "filled_fields": filled}
