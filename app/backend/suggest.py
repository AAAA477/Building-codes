"""AI suggestions for an inexperienced applicant, with automatic accuracy checks.

Principles (see app/SUGGEST_EVAL.md for measured numbers):
- extract_facts: every fact must literally appear in the applicant's text; anything else is dropped.
- improve_text: the model may only restructure the applicant's own words; output is checked for
  unsupported numbers, safety/equivalence claims and unknown/unsupported article numbers. One stricter retry, then 'rejected'.
- mitigations / precedents are RETRIEVED (never generated) and carry a verbatim source quote.
- offline fallback is deterministic. Nothing here says a design is safe, equivalent or approved.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

BACKEND = Path(__file__).resolve().parent
APP = BACKEND.parent
FILES = APP.parent / "files"
CONTENT = APP / "data" / "content"

DISCLAIMER = ("AI suggestions are drafts. They can be wrong. Check them against the sources shown. "
              "Only a person (and your registered professional where required) can confirm accuracy.")
OPTION_LABEL = ("Options others have used. Whether they achieve equivalent performance is for your registered "
                "professional.")

# --------------------------------------------------------------------------- numbers / text helpers
WORDNUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
           "ten": 10, "eleven": 11, "twelve": 12}
_WORDS = "|".join(WORDNUM)
ART_RE = re.compile(r"(?<![\d.])(\d{1,2}\.\d{1,2}\.\d{1,2}\.\d{1,3})(?![\d])")
NUM_RE = re.compile(r"(?<![\w.])(\d[\d,]*(?:\.\d+)?)(?![\d])")


def _ws(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()


def _fnum(tok: str) -> Optional[float]:
    try:
        return float(tok.replace(",", ""))
    except ValueError:
        return None


def numbers_in(text: str) -> set:
    """All numeric values in `text` (digits and number words); dotted article numbers are excluded."""
    t = ART_RE.sub(" ", text or "")
    t = re.sub(r"\b\d+(?:\.\d+){2,}\b", " ", t)  # any other dotted clause numbers
    out = set()
    for m in NUM_RE.finditer(t):
        v = _fnum(m.group(1).rstrip(","))
        if v is not None:
            out.add(v)
    for w, v in WORDNUM.items():
        if re.search(rf"\b{w}\b", t, re.I):
            out.add(float(v))
    return out


def articles_in(text: str) -> list:
    return list(dict.fromkeys(ART_RE.findall(text or "")))


def _flatten(x: Any) -> str:
    if isinstance(x, dict):
        return " ".join(_flatten(v) for k, v in x.items() if k not in ("provenance", "completeness"))
    if isinstance(x, (list, tuple)):
        return " ".join(_flatten(v) for v in x)
    if x is None or isinstance(x, bool):
        return ""
    return str(x)


# --------------------------------------------------------------------------- fact extraction
FACT_FIELDS = ["storeys", "building_area_m2", "units_per_floor", "occupancy", "sprinklered", "new_or_renovation"]

_N = rf"(\d{{1,3}}|{_WORDS})"
RX = {
    "storeys": re.compile(rf"\b{_N}[\s-]*(?:storeys?|stories|story|floors?)\b", re.I),
    "building_area_m2": re.compile(r"(\d[\d,]*(?:\.\d+)?)\s*(?:m2|m²|m\s*\^?2|sq\.?\s*m\b|square\s+met(?:er|re)s?)", re.I),
    "units_per_floor": re.compile(
        rf"\b{_N}\s*(?:dwelling\s+)?(?:units?|suites?|apartments?)\s*(?:per|each|on\s+each|on\s+every|/)\s*(?:floor|storey|level)", re.I),
    "occupancy": re.compile(r"\b(Group\s+[A-F](?:\s*,?\s*Division\s+\d)?|residential|apartment|office|assembly|"
                            r"care|mercantile|industrial|hotel|dormitor(?:y|ies)|mixed[- ]use)\b", re.I),
    "sp_neg": re.compile(r"\b(?:not\s+sprinklered|unsprinklered|non-sprinklered|no\s+sprinklers?|"
                         r"not\s+(?:equipped|protected)\s+with\s+(?:an?\s+)?(?:automatic\s+)?sprinkler)", re.I),
    "sp_pos": re.compile(r"\b(?:sprinklered|sprinkler\s+system|sprinklers)\b", re.I),
    "renov": re.compile(r"\b(?:renovat\w*|retrofit\w*|conversion|alteration|existing\s+building)\b", re.I),
    "new": re.compile(r"\b(?:new\s+construction|new\s+building|newly\s+constructed|new\s+build)\b", re.I),
}


def _numval(tok: str) -> Optional[float]:
    tok = tok.strip().lower()
    return float(WORDNUM[tok]) if tok in WORDNUM else _fnum(tok)


def extract_facts_regex(text: str) -> dict:
    """{field: {value, quote, conf}} from explicit patterns only."""
    t = text or ""
    out: dict = {}
    m = RX["storeys"].search(t)
    if m:
        v = _numval(m.group(1))
        if v is not None:
            out["storeys"] = {"value": int(v), "quote": m.group(0), "conf": 0.8}
    m = RX["building_area_m2"].search(t)
    if m:
        v = _fnum(m.group(1))
        if v is not None:
            out["building_area_m2"] = {"value": int(v) if v == int(v) else v, "quote": m.group(0), "conf": 0.8}
    m = RX["units_per_floor"].search(t)
    if m:
        v = _numval(m.group(1))
        if v is not None:
            out["units_per_floor"] = {"value": int(v), "quote": m.group(0), "conf": 0.8}
    m = RX["occupancy"].search(t)
    if m:
        out["occupancy"] = {"value": m.group(0), "quote": m.group(0), "conf": 0.6}
    m = RX["sp_neg"].search(t)
    if m:
        out["sprinklered"] = {"value": False, "quote": m.group(0), "conf": 0.7}
    else:
        m = RX["sp_pos"].search(t)
        if m:
            out["sprinklered"] = {"value": True, "quote": m.group(0), "conf": 0.55}
    m = RX["renov"].search(t)
    if m:
        out["new_or_renovation"] = {"value": "renovation", "quote": m.group(0), "conf": 0.55}
    else:
        m = RX["new"].search(t)
        if m:
            out["new_or_renovation"] = {"value": "new", "quote": m.group(0), "conf": 0.55}
    return out


def fact_in_text(field: str, value: Any, text: str, quote: str = "") -> bool:
    """The literal-appearance test applied to every fact (regex or LLM). Unmatched facts are dropped."""
    t = text or ""
    if quote and _ws(quote).lower() not in _ws(t).lower():
        return False
    if field in ("storeys", "building_area_m2", "units_per_floor"):
        try:
            v = float(value)
        except (TypeError, ValueError):
            return False
        scope = quote or t
        return v in numbers_in(scope) and v in numbers_in(t)
    if field == "occupancy":
        return isinstance(value, str) and len(value) > 2 and _ws(value).lower() in _ws(t).lower()
    if field == "sprinklered":
        if value is False:
            return bool(RX["sp_neg"].search(t))
        return value is True and bool(RX["sp_pos"].search(t)) and not RX["sp_neg"].search(t)
    if field == "new_or_renovation":
        if value == "renovation":
            return bool(RX["renov"].search(t))
        return value == "new" and bool(RX["new"].search(t))
    return False


def _coerce(field: str, value: Any):
    if field in ("storeys", "units_per_floor"):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None
    if field == "building_area_m2":
        try:
            v = float(str(value).replace(",", ""))
            return int(v) if v == int(v) else v
        except (TypeError, ValueError):
            return None
    if field == "sprinklered":
        if isinstance(value, bool):
            return value
        s = str(value).strip().lower()
        return True if s in ("true", "yes") else False if s in ("false", "no") else None
    if field == "new_or_renovation":
        s = str(value).strip().lower()
        return s if s in ("new", "renovation") else None
    if field == "occupancy":
        return str(value).strip() if value else None
    return None


LABELS = {"storeys": "Number of storeys", "building_area_m2": "Building area (m2)",
          "units_per_floor": "Units per floor", "occupancy": "Occupancy",
          "sprinklered": "Sprinklered", "new_or_renovation": "New construction or renovation"}


def extract_facts(text: str, llm=None) -> tuple:
    """Returns (facts, dropped, mode). facts: {field: {value, quote, conf}} all verified literally in `text`."""
    regex = extract_facts_regex(text)
    raw = None
    if llm is not None and getattr(llm, "name", "offline") != "offline":
        prompt = ("Read this applicant's project description. Extract ONLY facts that are explicitly written. "
                  "For each field give the value and the EXACT words copied from the text as quote. "
                  "If a field is not stated, use null. Never infer or calculate.\n"
                  "Fields: storeys (integer), building_area_m2 (number), units_per_floor (integer), "
                  "occupancy (words from the text), sprinklered (true/false only if stated), "
                  "new_or_renovation ('new' or 'renovation' only if stated).\n"
                  f"Text: \"\"\"{text}\"\"\"")
        hint = '{"storeys":{"value":null,"quote":null},"building_area_m2":{...},"units_per_floor":{...},"occupancy":{...},"sprinklered":{...},"new_or_renovation":{...}}'
        try:
            raw = llm.chat_json(prompt, hint)
        except Exception:
            raw = None
        if not isinstance(raw, dict):
            raw = None
    facts, dropped = {}, []
    if raw is not None:
        for f in FACT_FIELDS:
            e = raw.get(f)
            if not isinstance(e, dict) or e.get("value") in (None, "", "null"):
                continue
            v = _coerce(f, e.get("value"))
            q = _ws(str(e.get("quote") or ""))
            if v is None or not fact_in_text(f, v, text, q):
                dropped.append({"field": f, "value": e.get("value"), "reason": "not found literally in your text"})
                continue
            agree = f in regex and regex[f]["value"] == v
            facts[f] = {"value": v, "quote": q or regex.get(f, {}).get("quote", ""), "conf": 0.95 if agree else 0.85}
        return facts, dropped, "azure-openai"
    for f, e in regex.items():
        if fact_in_text(f, e["value"], text, e["quote"]):
            facts[f] = e
        else:
            dropped.append({"field": f, "value": e["value"], "reason": "not found literally in your text"})
    return facts, dropped, "offline"


# --------------------------------------------------------------------------- checks
SAFETY_RX = re.compile(
    r"\b(is|are|will be|would be|remains?|deemed|considered|proven|ensures?|guarantees?)\s+(?:\w+\s+){0,2}?(safe|safer|compliant)\b"
    r"|\bequivalent\s+(?:or|to|level|performance)|\bequal\s+(?:or|to)\s+better\b|\bor\s+better\b"
    r"|\bwill\s+comply|\bcomplies\s+with|\bmeets?\s+(?:or\s+exceeds?\s+)?(?:the\s+)?(?:code|requirements?|intent|objectives?)"
    r"|\bsatisf(?:y|ies)\s+the\s+(?:code|intent)|\bapproved\b|\bacceptable\s+to\s+the\s+authority|\bno\s+(?:added\s+)?risk\b"
    r"|\bachieves?\s+(?:the\s+)?(?:same|equivalent)|\bsafe\s+and\b|\bsafe\s+for\b|\bis\s+safe\b|\bwill\s+be\s+approved",
    re.I)


@lru_cache(maxsize=1)
def _verifiers():
    mods = {}
    try:
        from corpus import verifier as v
        mods["nbc"] = v
    except Exception:
        mods["nbc"] = None
    try:
        from corpus import verifier_codes as vc
        mods["other"] = vc
    except Exception:
        mods["other"] = None
    return mods


def article_exists_any(num: str) -> bool:
    m = _verifiers()
    try:
        if m["nbc"] and m["nbc"].article_exists(num):
            return True
    except Exception:
        pass
    try:
        if m["other"]:
            return any(m["other"].article_exists(k, num) for k in ("nfc", "npc", "necb"))
    except Exception:
        pass
    return False


def check_text(output: str, user_text: str = "", app: Optional[dict] = None, source_texts=()) -> dict:
    """Automatic checks for model-written text. grounded = no number or article that is absent from the
    applicant's text, the application fields and the retrieved sources."""
    context = " ".join([user_text or "", _flatten(app or {}), " ".join(source_texts or ())])
    allowed = numbers_in(context)
    ctx_arts = set(articles_in(context))
    out_nums = sorted(numbers_in(output))
    unsupported = [(int(n) if n == int(n) else n) for n in out_nums if n not in allowed]
    arts = articles_in(output)
    unknown = [a for a in arts if not article_exists_any(a)]
    foreign = [a for a in arts if a not in ctx_arts]
    claims = bool(SAFETY_RX.search(output or ""))
    notes = []
    if unsupported:
        notes.append("Numbers not in your text, your application or the sources: " + ", ".join(map(str, unsupported)))
    if unknown:
        notes.append("Article numbers not found in the indexed codes: " + ", ".join(unknown))
    if foreign and not unknown:
        notes.append("Article numbers you did not cite and that are not in the sources: " + ", ".join(foreign))
    if claims:
        notes.append("Contains a safety / equivalence / approval claim: " + (SAFETY_RX.search(output).group(0)))
    return {"grounded": not unsupported and not foreign and not unknown,
            "citations_verified": not unknown and not foreign,
            "unsupported_numbers": unsupported, "claims_safety": claims, "notes": notes}


def checks_ok(c: dict) -> bool:
    return bool(c["grounded"] and c["citations_verified"] and not c["unsupported_numbers"] and not c["claims_safety"])


# --------------------------------------------------------------------------- sources (verbatim quotes)
@lru_cache(maxsize=64)
def _page_text(doc: str, page: int) -> str:
    try:
        import pymupdf
    except Exception:
        return ""
    cands = list(FILES.rglob(Path(doc).name)) if FILES.exists() else []
    if not cands:
        return ""
    try:
        d = pymupdf.open(str(cands[0]))
        if 1 <= page <= len(d):
            return _ws(d[page - 1].get_text())
    except Exception:
        return ""
    return ""


def _best_sentence(page_text: str, terms: str) -> str:
    sents = re.split(r"(?<=[.;:])\s+", page_text)
    tw = {w for w in re.findall(r"[a-z]{4,}", terms.lower())}
    best, bs = "", 0
    for s in sents:
        if len(s) < 40:
            continue
        sc = len(tw & set(re.findall(r"[a-z]{4,}", s.lower()))) / (1 + len(s) / 400)
        if sc > bs:
            best, bs = s, sc
    return best[:400] if bs > 0 else ""


def quote_is_real(doc: str, page: int, quote: str) -> bool:
    return bool(quote) and _ws(quote) in _page_text(doc, page)


@lru_cache(maxsize=1)
def _catalogue() -> dict:
    p = CONTENT / "stair_module.json"
    try:
        return json.loads(p.read_text(encoding="utf8")).get("mitigation_catalogue", {})
    except Exception:
        return {}


def _doc_type(doc: str) -> str:
    d = doc.lower()
    return "advisory" if "calgary" in d else "policy" if "edmonton" in d else "standata" if "standata" in d else "guide"


# --------------------------------------------------------------------------- item builders
def _item(id_, kind, label, value, why, sources, conf, checks=None, status="ready", field_path=None):
    it = {"id": id_, "kind": kind, "label": label, "value": value, "confidence": round(conf, 2), "why": why,
          "sources": sources,
          "checks": checks or {"grounded": True, "citations_verified": True, "unsupported_numbers": [],
                               "claims_safety": False, "notes": []},
          "status": status}
    if field_path:
        it["field_path"] = field_path
    return it


def _app_text(app: dict) -> str:
    p = app.get("project", {}) or {}
    v = (app.get("variance", {}) or {})
    return " ".join([p.get("description") or "", (v.get("proposed_alternative") or {}).get("summary") or ""])


def do_extract_facts(app: dict, text: Optional[str], llm) -> dict:
    text = text if text is not None else (app.get("project", {}) or {}).get("description") or ""
    if not text.strip():
        return {"items": [], "llm": "offline", "notes": ["Nothing to read: write a short project description first."]}
    facts, dropped, mode = extract_facts(text, llm)
    items = []
    for f, e in facts.items():
        items.append(_item(f"fact-{f}", "fact", LABELS[f], e["value"],
                           f"You wrote: \"{e['quote']}\". Check it is what you meant.",
                           [{"type": "user_text", "doc": "your description", "page": 0, "quote": e["quote"]}],
                           e["conf"], field_path=f"project.{f}"))
    notes = [f"Not stated clearly, so not filled: {LABELS[d['field']]}" for d in dropped]
    return {"items": items, "llm": mode, "notes": notes}


IMPROVE_PROMPT = ("Rewrite the applicant's text below so it is clearer and better organised for a building "
                  "permit variance application. RULES: use only the applicant's own words and the listed application "
                  "facts; do NOT add any number, measurement, unit, article number, name or fact that is not in them; "
                  "do NOT say the design is safe, equivalent, better, compliant, approved or meets the code; do not "
                  "give advice. Output only the rewritten text.\n")


def do_improve_text(app: dict, text: Optional[str], field_path: Optional[str], llm) -> dict:
    src = text if text else _app_text(app)
    if not (src or "").strip():
        return {"items": [], "llm": "offline", "notes": ["Nothing to improve yet."]}
    fp = field_path or "project.description"
    if llm is None or getattr(llm, "name", "offline") == "offline":
        return {"items": [], "llm": "offline",
                "notes": ["Rewriting needs the AI service, which is not available. Your text is unchanged."]}
    facts = {k: (app.get("project", {}) or {}).get(k) for k in FACT_FIELDS if (app.get("project", {}) or {}).get(k) not in (None, "")}
    base = IMPROVE_PROMPT + f"Application facts: {json.dumps(facts)}\nApplicant text: \"\"\"{src}\"\"\""
    attempts, last_checks, out = 0, None, None
    prompt = base
    for attempts in (1, 2):
        out = None
        try:
            out = llm.chat_text(prompt)
        except Exception:
            out = None
        if not out:
            break
        last_checks = check_text(out, src, app)
        if checks_ok(last_checks):
            break
        prompt = (base + "\nYOUR PREVIOUS ANSWER WAS REJECTED because: " + "; ".join(last_checks["notes"]) +
                  "\nTry again. Copy numbers only from the applicant text. Remove all claims about safety, equivalence "
                  "or compliance. If unsure, change fewer words.")
    if not out:
        return {"items": [], "llm": llm.name, "notes": ["The AI service did not return text. Your text is unchanged."]}
    ok = checks_ok(last_checks)
    notes = list(last_checks["notes"])
    if attempts == 2 and ok:
        notes.append("First draft failed the checks and was regenerated once with stricter instructions.")
    it = _item("improve-text", "text", "Clearer wording of your text", out if ok else None,
               "Rewritten from your own words only. Compare it with what you wrote before accepting."
               if ok else "Rejected: " + "; ".join(notes),
               [{"type": "user_text", "doc": "your text", "page": 0, "quote": _ws(src)[:300]}],
               0.7 if ok else 0.0, dict(last_checks, notes=notes), "ready" if ok else "rejected", fp)
    it["attempts"] = attempts
    return {"items": [it], "llm": llm.name, "notes": []}


def _precedent_sources(r: dict) -> list:
    return [{"type": {"standata_variance": "standata", "standata_interpretation": "standata",
                      "standata_bulletin": "standata", "calgary_advisory": "advisory"}.get(
                          r.get("source_type"), _doc_type(r.get("doc", ""))),
             "doc": r["doc"], "page": r["page"], "quote": r["snippet"].strip(" .…")}]


def _prec_search(app: dict, k: int):
    try:
        from corpus import precedents as P
        if not P.available():
            return []
        q = _app_text(app).strip() or "single exit stair"
        arts = [a.get("article") if isinstance(a, dict) else a for a in (app.get("variance", {}).get("section_c") or [])]
        arts += (app.get("variance", {}).get("acceptable_solution") or {}).get("articles") or []
        arts = [x for x in (ART_RE.findall(" ".join(str(a) for a in arts if a))) if x]
        return P.search_precedents(q, k=k, articles=arts)
    except Exception:
        return []


def _snippet_real(r: dict) -> bool:
    try:
        from corpus import precedents as P
        for c in P._idx()["chunks"]:
            if c["id"] == r["id"]:
                return _ws(r["snippet"].strip(" .…")) in _ws(c["text"])
    except Exception:
        pass
    return False


def do_precedents(app: dict, k: int = 6) -> dict:
    items = []
    for r in _prec_search(app, k):
        real = _snippet_real(r)
        items.append(_item(f"prec-{r['id']}", "precedent", r.get("title") or r.get("label") or "Precedent",
                           r["snippet"].strip(),
                           "Retrieved by text and article match; not generated. A precedent does not mean yours is accepted.",
                           _precedent_sources(r), min(0.9, r["score"] / 60 + 0.2),
                           {"grounded": real, "citations_verified": True, "unsupported_numbers": [],
                            "claims_safety": False, "notes": [] if real else ["quote could not be matched in the source chunk"]},
                           "ready" if real else "needs_review"))
    return {"items": items, "llm": "offline", "notes": [OPTION_LABEL] if items else ["No similar documents found."]}


def do_mitigations(app: dict, llm=None) -> dict:
    items = []
    topic = (app.get("variance") or {}).get("topic")
    stair = topic == "single_exit_stair"
    cat = _catalogue() if stair else {}
    chosen = {m.get("id") for m in (app.get("variance", {}).get("proposed_alternative") or {}).get("mitigations") or []}
    for m in cat.get("items", []):
        s = m.get("source") or {}
        pt = _page_text(s.get("doc", ""), s.get("page", 0))
        quote = _best_sentence(pt, f"{m.get('label')} {m.get('plain')} {m.get('basis')}")
        real = quote_is_real(s.get("doc", ""), s.get("page", 0), quote)
        srcs = [{"type": "guide", "doc": s.get("doc"), "page": s.get("page"), "quote": quote}]
        if m.get("also_source"):
            a = m["also_source"]
            srcs.append({"type": "guide", "doc": a.get("doc"), "page": a.get("page"),
                         "quote": _best_sentence(_page_text(a.get("doc", ""), a.get("page", 0)), f"{m.get('label')} {m.get('plain')}")})
        notes = [] if real else ["verbatim quote could not be extracted from the page; read the cited page"]
        why = m.get("basis") or m.get("plain")
        if m.get("professional_required"):
            why += " Needs your registered professional."
        items.append(_item(f"opt-{m['id']}", "option", m["label"], m.get("plain"),
                           ("Already in your application. " if m["id"] in chosen else "") + why, srcs, 0.7,
                           {"grounded": True, "citations_verified": True, "unsupported_numbers": [],
                            "claims_safety": False, "notes": notes}, "ready" if real else "needs_review"))
    for r in _prec_search(app, 4):
        real = _snippet_real(r)
        items.append(_item(f"opt-prec-{r['id']}", "option", "Used in: " + (r.get("title") or r.get("label") or "precedent"),
                           r["snippet"].strip(), "A document that handled a similar situation; not generated.",
                           _precedent_sources(r), 0.5,
                           {"grounded": real, "citations_verified": True, "unsupported_numbers": [], "claims_safety": False,
                            "notes": [] if real else ["quote not matched"]}, "ready" if real else "needs_review"))
    notes = [OPTION_LABEL]
    if stair:
        notes.append("This catalogue lists no performance values; the guide's technical report is not in the data package.")
    return {"items": items, "llm": "offline", "notes": notes}


WHY = {
    "A": "The authority must know who is applying and how to reach them.",
    "B": "The authority needs to identify the project and the site this applies to.",
    "C": "The authority reads this section to see which code requirement is being varied and its purpose.",
    "D": "Supporting documents let the reviewer check your proposal; missing ones are a common reason for a request for information.",
    "SIGN": "Declarations and signatures must be completed by the people responsible; the tool cannot do this for you.",
}


def do_missing_info(app: dict) -> dict:
    items = []
    try:
        import completeness
        comp = completeness.compute(app)
    except Exception:
        comp = app.get("completeness") or {}
    for it in (comp.get("items") or []):
        if it.get("status") == "complete":
            continue
        sec = it.get("section", "")
        srcs = []
        for art in articles_in(it.get("label", "") + " " + (it.get("message") or "")):
            try:
                from corpus import verifier
                a = verifier.get_article(art)
                if a and a.get("text"):
                    srcs.append({"type": "code", "code": "NBC", "article": art, "doc": verifier.SOURCE_DOC,
                                 "page": a.get("page", 0), "quote": _ws(a["text"])[:250]})
            except Exception:
                pass
        needs_pro = it.get("status") == "needs_professional"
        prompt_text = (it.get("message") or it.get("label")) + (
            " Your registered professional needs to prepare this; leave it for them." if needs_pro else "")
        items.append(_item(f"missing-{it['id']}", "prompt", it.get("label"), prompt_text, WHY.get(sec, "Needed to complete the application."),
                           srcs, 0.9, status="ready"))
    return {"items": items, "llm": "offline",
            "notes": [] if items else ["No open items found."]}


# --------------------------------------------------------------------------- dispatch
KINDS = ("extract_facts", "improve_text", "mitigations", "missing_info", "similar_precedents")


def run(app: dict, kind: str, text: Optional[str] = None, field_path: Optional[str] = None, llm=None) -> dict:
    if llm is None:
        try:
            from llm import get_llm
            llm = get_llm()
        except Exception:
            llm = None
    if app.get("ai_enabled") is False:   # per-application AI switch: never call the hosted model
        llm = None
    if kind == "extract_facts":
        r = do_extract_facts(app, text, llm)
    elif kind == "improve_text":
        r = do_improve_text(app, text, field_path, llm)
    elif kind == "mitigations":
        r = do_mitigations(app, llm)
    elif kind == "missing_info":
        r = do_missing_info(app)
    elif kind == "similar_precedents":
        r = do_precedents(app)
    else:
        raise ValueError(f"unknown kind {kind}")
    return {"kind": kind, "llm": r["llm"] if r["llm"] != "offline" else "offline",
            "disclaimer": DISCLAIMER, "items": r["items"], "notes": r.get("notes", [])}
