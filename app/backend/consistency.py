"""Consistency and trap checks (completeness only). Compares free text with structured fields and flags
common administrative rejection causes: number disagreements, mixed units, wrong code edition or place,
unverifiable article numbers, owner-name/land-title reminder, date sanity.
Never judges safety, equivalence or approval. Never verifies the land title. Never sets declarations.
Items use the completeness item shape (ids prefixed 'X.'); all are 'uncertain' (severity confirm)."""
from __future__ import annotations
import datetime as _dt
import re

from models import get_path

SQFT = 0.09290304
WORDS = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
         "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
         "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20}
_NUM = r"(\d{1,3}|" + "|".join(WORDS) + r")"
# a limit ("up to 6 storeys", "6 storeys or less") is not a statement of the project's own value
_LIMIT_BEFORE = re.compile(r"(up to|upto|max(?:imum)?(?: of)?|not (?:more|greater) than|no more than|over|under|"
                           r"exceed\w*|more than|fewer than|less than|at least|at most|below|above|than|to)\s*$", re.I)
_LIMIT_AFTER = re.compile(r"^\s*(or (?:less|fewer|more|greater|taller|higher)|and (?:under|over|below|above)|maximum|max\b)", re.I)

_BRACKET = re.compile(r"\[[^\]]*\]")


def _clean(s):
    return _BRACKET.sub(" ", s) if isinstance(s, str) else ""


def _n(tok):
    t = tok.lower()
    return WORDS[t] if t in WORDS else int(t)


def _texts(app):
    """(field label, node id, cleaned text) for each free-text field; [bracketed] placeholders removed."""
    p, v = app.get("project", {}), app.get("variance", {})
    out = [("Project description", "B.description", _clean(p.get("description"))),
           ("Proposed alternative summary", "C.alternative", _clean(get_path(v, "proposed_alternative.summary", ""))),
           ("Acceptable-solution explanation", "C.explanation", _clean(get_path(v, "acceptable_solution.explanation", "")))]
    for i, m in enumerate(get_path(v, "proposed_alternative.mitigations", []) or []):
        if isinstance(m, dict):
            out.append((f"Mitigating feature {m.get('label') or i + 1}", f"C.mitigation.{i}", _clean(m.get("detail"))))
    return [t for t in out if t[2].strip()]


def _num_matches(rx, text):
    vals = []
    for m in rx.finditer(text):
        if _LIMIT_BEFORE.search(text[max(0, m.start() - 22):m.start()]) or _LIMIT_AFTER.search(text[m.end():m.end() + 20]):
            continue
        vals.append(m)
    return vals


STOREY_RX = re.compile(r"\b" + _NUM + r"[\s-]+(?:storeys?|stories|story)\b", re.I)
UNITS_RX = re.compile(r"\b" + _NUM + r"\s+(?:dwelling\s+|residential\s+)?(?:units?|suites?)\s+(?:per|on each|on every|each)\s+(?:floor|storey|story)\b", re.I)
AREA_RX = re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(m2|m²|m\^2|sq\.?\s*m|square met(?:re|er)s?|sq\.?\s*ft\.?|sf|ft2|ft²|square f(?:ee|oo)t)(?![a-z])", re.I)

IMPERIAL_RX = re.compile(r"\d\s*(?:-\s*)?(?:feet|foot|ft\b|inch(?:es)?\b|sq\.?\s*ft|psi\b|mph\b|gpm\b|cfm\b|lbs?\b|pounds?\b|°\s*F\b)"
                         r"|\d\s*-\s*in\b", re.I)
METRIC_RX = re.compile(r"\d\s*(?:mm|cm|km|m|m2|m²|m3|kpa|mpa|kg|l|l/s|°\s*c)(?![a-z])", re.I)
METRIC_WORD_RX = re.compile(r"\b(?:metres?|meters?|millimet\w+|kilopascals?|litres?)\b", re.I)

EDITION_RX = re.compile(r"\b(?:NBC(?:\s*\(\s*AE\s*\))?|National\s+Building\s+Code(?:\s+of\s+Canada)?(?:\s*\(\s*Alberta\s+Edition\s*\))?"
                        r"|Alberta\s+Building\s+Code|ABC)\s*[,:-]?\s*(20\d\d)\b", re.I)
PLACE_RX = re.compile(r"\b(Ontario\s+Building\s+Code|OBC|B\.?C\.?\s+Building\s+Code|BCBC|British\s+Columbia\s+Building\s+Code|"
                      r"Ontario|Toronto|Vancouver|British\s+Columbia|Ottawa|Montreal|Quebec|Manitoba|Winnipeg|Saskatchewan|"
                      r"Nova\s+Scotia|Halifax)\b(?!\s+(?:Drive|Dr\b|Road|Rd\b|Avenue|Ave\b|Street|St\b|Trail|Crescent))", re.I)
OTHER_CODE_BEFORE = re.compile(r"(NFC|NPC|NECB|Fire Code|Plumbing Code|Energy Code)[^.]{0,25}$", re.I)


def _it(id_, label, msg, node, group="alternative", priority=3):
    return {"id": id_, "label": label, "section": "X", "status": "uncertain", "message": msg,
            "node_id": node, "group": group, "priority": priority, "severity": "confirm"}


def _numbers(app, texts):
    p = app.get("project", {})
    out = []
    st = p.get("storeys")
    if isinstance(st, (int, float)) and not isinstance(st, bool):
        for lab, node, t in texts:
            vals = [_n(m.group(1)) for m in _num_matches(STOREY_RX, t)]
            if vals and int(st) not in vals:
                out.append(_it("X.storeys." + node, "Storeys: text vs field",
                               f"{lab} mentions {sorted(set(vals))[0]} storeys but the Number of storeys field says {int(st)}. "
                               "Please make the text and the field agree.", node))
    u = p.get("units_per_floor")
    if isinstance(u, (int, float)) and not isinstance(u, bool):
        for lab, node, t in texts:
            vals = [_n(m.group(1)) for m in _num_matches(UNITS_RX, t)]
            if vals and int(u) not in vals:
                out.append(_it("X.units." + node, "Units per floor: text vs field",
                               f"{lab} mentions {sorted(set(vals))[0]} units per floor but the Units per floor field says {int(u)}. "
                               "Please make the text and the field agree.", node))
    a = p.get("building_area_m2")
    if isinstance(a, (int, float)) and not isinstance(a, bool) and a > 0:
        for lab, node, t in texts:
            vals = []
            for m in AREA_RX.finditer(t):
                try:
                    x = float(m.group(1).replace(",", ""))
                except ValueError:
                    continue
                vals.append(x * SQFT if re.search(r"ft|f(?:ee|oo)t|sf", m.group(2), re.I) else x)
            if vals and not any(abs(v - a) <= max(0.02 * a, 0.5) for v in vals):
                out.append(_it("X.area." + node, "Building area: text vs field",
                               f"{lab} states an area of about {vals[0]:.0f} m2 but the Building area field says {a:g} m2. "
                               "If the text refers to a different area (for example one floor), say so; otherwise make them agree.", node))
    return out


def _units(texts):
    out = []
    for lab, node, t in texts:
        if IMPERIAL_RX.search(t) and not (METRIC_RX.search(t) or METRIC_WORD_RX.search(t)):
            out.append(_it("X.units_mixed." + node, "Imperial units without metric",
                           f"{lab} uses imperial units (feet, inches, sq ft or psi) with no metric values. "
                           "Alberta codes use metric (SI); please state values in metric.", node, "admin", 4))
    return out


def _edition_place(app, texts):
    out = []
    code = _clean(get_path(app, "variance.code_or_standard", ""))
    allt = texts + ([("Code or standard varied", "C.code_or_standard", code)] if code.strip() else [])
    for lab, node, t in allt:
        for m in EDITION_RX.finditer(t):
            yr = m.group(1)
            if yr == "2023":
                continue
            ctx = t[max(0, m.start() - 60):m.end() + 60].lower()
            if yr == "2020" and "intent" in ctx:
                continue  # NBC 2020 is valid for intent statements only
            out.append(_it(f"X.edition.{node}.{yr}", "Code edition",
                           f"{lab} cites '{m.group(0).strip()}'. Alberta applications are made against NBC(AE) 2023; "
                           "the 2020 NBC text is used here only for intent statements. Please confirm the edition cited.",
                           node, "citations", 2))
            break
        m = PLACE_RX.search(t)
        if m:
            out.append(_it(f"X.place.{node}", "Non-Alberta reference",
                           f"{lab} mentions '{m.group(0)}', which is not an Alberta code or place. "
                           "Please confirm this reference belongs in an Alberta application.", node, "citations", 2))
    return out


def _articles(texts):
    out, seen = [], set()
    try:
        from corpus import verifier
    except Exception:
        return out
    for lab, node, t in texts:
        for m in verifier.RE_CITE.finditer(t):
            if OTHER_CODE_BEFORE.search(t[max(0, m.start() - 30):m.start()]):
                continue
            n = m.group(1)
            if n in seen:
                continue
            seen.add(n)
            try:
                ok = verifier.article_exists(n)
            except Exception:
                continue
            if not ok:
                out.append(_it("X.article." + n, f"Article {n} in text",
                               f"{lab} cites article {n}, which was not found in the indexed NBC(AE) 2023 text. "
                               "Please check the number (or name the code if it is a different one).", node, "citations", 2))
    return out


def _owner_date(app):
    out = []
    a = app.get("applicant", {})
    nm = a.get("owner_name")
    if isinstance(nm, str) and nm.strip() and not re.fullmatch(r"\[[^\]]*\]", nm.strip()):
        out.append(_it("X.owner_title", "Owner name and land title",
                       "Confirm the owner name is written exactly as it appears on the land title. "
                       "This tool does not check the land title.", "A.owner_name", "admin", 4))
    d = a.get("date_of_request")
    if isinstance(d, str) and d.strip() and not re.fullmatch(r"\[[^\]]*\]", d.strip()):
        dt = None
        m = re.match(r"^\s*(\d{4})[-/](\d{1,2})[-/](\d{1,2})\s*$", d)
        if m:
            try:
                dt = _dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            except ValueError:
                dt = None
        ym = re.search(r"(?<!\d)((?:19|20)\d\d)(?!\d)", d)
        yr = dt.year if dt else (int(ym.group(1)) if ym else None)
        today = _dt.date.today()
        if yr is None:
            out.append(_it("X.date", "Date of request", f"Date of request '{d.strip()}' could not be read; please use YYYY-MM-DD.",
                           "A.date_of_request", "admin", 4))
        elif (dt and dt > today) or (not dt and yr > today.year):
            out.append(_it("X.date", "Date of request", "Date of request is in the future; please confirm it.",
                           "A.date_of_request", "admin", 4))
        elif yr < 2023:
            out.append(_it("X.date", "Date of request",
                           "Date of request is before 2023 (the NBC(AE) 2023 edition); please confirm it.",
                           "A.date_of_request", "admin", 4))
    return out


def items(app: dict) -> list:
    texts = _texts(app)
    return (_numbers(app, texts) + _units(texts) + _edition_place(app, texts) + _articles(texts) + _owner_date(app))
