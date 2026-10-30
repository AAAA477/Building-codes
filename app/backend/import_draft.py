"""Bring in a variance request the applicant has already started (spec 4.6).

from_scc_pdf(bytes)  - the official SCC variance form, filled in whole or part, read by field name (inverse of export/fill_scc.py)
from_text(str)       - any pasted draft; facts must appear literally in the text (suggest.extract_facts rule)
Both return (application, report). The application is not saved here. No hosted model is ever called (the draft may hold
personal information). Declarations and signatures are never imported as ticked.
"""
from __future__ import annotations
import re

import pymupdf

import models
import suggest
from export.fill_scc import C_ROWS, D_ROWS, ATS, FILLED_NEVER

ART_RE = re.compile(r"(?<![\d.])(\d{1,2}\.\d{1,2}\.\d{1,2}\.\d{1,3})(?:\.?\s*\((\d+)\))?(?![\d])")
MAPPED_TEXT = {"Owner", "Owner Rep", "Mailing Address", "Date of Reqeuest", "Permit", "Municipal Address", "Code or Standard",
               "Owner Print", "Owner Rep Print", *ATS.values(),
               *[n for row in C_ROWS for n in row], *[n for row in D_ROWS for n in row]}
SIGN_WATCH = ("Signature1", "Signature2", "Date1", "Date2")
MIN_TEXT_CHARS = 20


class DraftError(ValueError):
    """The draft cannot be read; the message is shown to the applicant."""


def _clean(s) -> str:
    return re.sub(r"\s+", " ", str(s or "")).strip()


def _report(source: str) -> dict:
    return {"source": source, "filled": [], "unmapped": [], "unverified_citations": [], "declarations_seen_ticked": [], "warnings": []}


def _blank() -> dict:
    return models.new_application()


def _mark(app: dict, rep: dict, path: str, source: str = "applicant", conf: float = 1.0) -> None:
    app.setdefault("provenance", {})[path] = {"source": source, "confidence": conf}
    rep["filled"].append(path)


def _verified(number: str):
    """(exists, code) for a bare article number, checked against NBC then NFC/NPC/NECB."""
    import main
    for code in ("NBC", "NFC", "NPC", "NECB"):
        try:
            if main.corpus_verify(number, code).get("exists") is True:
                return True, code
        except Exception:
            continue
    return False, "NBC"


def _row_from_cells(article: str, objective: str, function: str, intent: str, rep: dict) -> dict:
    art = re.sub(r"^\[UNVERIFIED\]\s*", "", _clean(article))
    m = ART_RE.search(art)
    ok = False
    if m:
        ok, _ = _verified(m.group(1))
        if not ok and m.group(1) not in rep["unverified_citations"]:
            rep["unverified_citations"].append(m.group(1))
    else:
        rep["warnings"].append(f"Section C article cell '{art}' has no article number to verify.")
    return {"article": art, "objective": _clean(objective), "function": _clean(function), "intent": _clean(intent),
            "explainer": "", "source": {}, "verified": ok, "provenance": "applicant"}


def from_scc_pdf(data: bytes) -> tuple[dict, dict]:
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception:
        raise DraftError("That file could not be opened as a PDF.")
    widgets = {w.field_name: w for p in doc for w in p.widgets()}
    if len({"Owner", "Code or Standard", "Section C Popup", "Supporting Doc"} & set(widgets)) < 3:
        text = "\n".join(p.get_text() for p in doc)
        app, rep = from_text(text, source="pdf_text")
        rep["warnings"].append("This PDF is not the fillable SCC variance form, so it was read as plain text. Check each section.")
        return app, rep
    val = lambda n: _clean(widgets[n].field_value) if n in widgets and widgets[n].field_type_string != "Signature" else ""
    app, rep = _blank(), _report("form")

    def put(path: str, name: str) -> None:
        v = val(name)
        if v:
            models.set_path(app, path, v)
            _mark(app, rep, path)

    put("applicant.owner_name", "Owner")
    put("applicant.owner_representative", "Owner Rep")
    put("applicant.mailing_address", "Mailing Address")
    put("applicant.date_of_request", "Date of Reqeuest")
    put("location.permit_number", "Permit")
    put("location.municipal_address", "Municipal Address")
    for k, name in {"lot": "Lot", "block": "Block", "plan": "Plan", "qtr": "QTR", "sec": "SEC", "twp": "TWP", "rge": "RGE", "mer": "MER"}.items():
        put(f"location.{k}", name)
    put("variance.code_or_standard", "Code or Standard")
    cb = widgets.get("Check Box")
    if cb is not None and cb.field_value not in (None, "", "Off", False):
        app["location"]["jurisdiction_wide"] = True
        _mark(app, rep, "location.jurisdiction_wide")

    rows = []
    for a, o, f, t in C_ROWS:
        if any(val(n) for n in (a, o, f, t)):
            rows.append(_row_from_cells(val(a), val(o), val(f), val(t), rep))
    if rows:
        app["variance"]["section_c"] = rows
        arts = [m.group(1) for r in rows for m in [ART_RE.search(r["article"])] if m]
        app["variance"]["acceptable_solution"]["articles"] = list(dict.fromkeys(arts))
        _mark(app, rep, "variance.section_c")
    drows = []
    for n, (a, b) in enumerate(D_ROWS, 1):
        if val(a) or val(b):
            drows.append({"id": f"D{n}", "document_name": val(a), "responsible_party": val(b), "professional_required": False,
                          "status": "to_be_prepared", "date": ""})
    if drows:
        app["section_d"] = drows
        _mark(app, rep, "section_d")

    for name in SIGN_WATCH:
        w = widgets.get(name)
        if w is not None and (_clean(w.field_value) or getattr(w, "is_signed", False)):
            rep["declarations_seen_ticked"].append(name)
    if rep["declarations_seen_ticked"]:
        rep["warnings"].append("Signatures or signing dates were found in the file. They were not imported; tick and sign in the app.")
    for name, w in widgets.items():
        if name in MAPPED_TEXT or name in FILLED_NEVER or name in SIGN_WATCH or "Popup" in name or w.field_type_string != "Text":
            continue
        if _clean(w.field_value):
            rep["unmapped"].append({"label": name, "text": _clean(w.field_value)})
    return app, rep


def from_text(text: str, source: str = "text") -> tuple[dict, dict]:
    text = (text or "").strip()
    if len(re.sub(r"\s", "", text)) < MIN_TEXT_CHARS:
        raise DraftError("This draft has no readable text; the PDF may be a scan. Paste the text of your draft or upload a fillable PDF of the form.")
    app, rep = _blank(), _report(source)
    app["project"]["description"] = text[:4000]
    _mark(app, rep, "project.description")
    facts, _dropped, _mode = suggest.extract_facts(text, llm=None)   # offline only: never sends the draft to a hosted model
    for field, e in facts.items():
        app["project"][field] = e["value"]
        _mark(app, rep, f"project.{field}", "ai_draft", float(e.get("conf", 0.6)))
    import main
    from llm import OfflineLLM
    seen, arts = set(), []
    for m in ART_RE.finditer(text):
        num = m.group(1)
        if num in seen:
            continue
        seen.add(num)
        ok, code = _verified(num)
        if not ok:
            rep["unverified_citations"].append(num)
            continue
        row, _ = main._build_row(num, OfflineLLM(), with_chunks=False, accept_unattributed=True, code=code)
        app["variance"]["section_c"].append(row)
        arts.append(num if code == "NBC" else f"{code} {num}")
    if arts:
        app["variance"]["acceptable_solution"]["articles"] = arts
        _mark(app, rep, "variance.section_c", "lookup")
    rep["warnings"].append("The draft was stored as the project description. Review Sections A to D; nothing else was filled from it except what is listed.")
    return app, rep
