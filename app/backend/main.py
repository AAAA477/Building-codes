"""FastAPI backend: Alberta variance application workspace (completeness, not correctness)."""
from __future__ import annotations
import importlib, json, re, sys, tempfile
from pathlib import Path
from typing import Any, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fastapi import Body, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

import envload

envload.load_env()  # reads app/backend/.env (never overrides real environment variables)

import completeness as comp_mod
import mapgraph, models, reviewer, rules
from llm import get_llm
from models import CONTENT_DIR, SAMPLES_DIR, deep_merge, get_path, leaf_paths, set_path

app = FastAPI(title="Variance workspace backend")
import ratelimit
app.add_middleware(ratelimit.RateLimitMiddleware)   # rate limits, body-size cap, security headers
app.add_middleware(CORSMiddleware, allow_origins=ratelimit.allowed_origins(),   # env ALLOWED_ORIGINS
                   allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"], allow_headers=["*"])


@app.exception_handler(HTTPException)
async def _scrubbed_http_error(request, exc):   # never echo keys/endpoints inside error text
    from fastapi.responses import JSONResponse
    d = ratelimit.scrub(exc.detail) if isinstance(exc.detail, str) else exc.detail
    return JSONResponse({"detail": d}, status_code=exc.status_code, headers=getattr(exc, "headers", None))


@app.exception_handler(Exception)
async def _generic_error(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse({"detail": "Internal server error"}, status_code=500)

PROTECTED = {"id", "provenance", "completeness", "professional_flags"}


# ---------------------------------------------------------------- optional streams
def _mod(name: str):
    """Import a sibling stream's module lazily; None if not (yet) available."""
    try:
        return importlib.import_module(name)
    except Exception:
        return None


def split_code(article: str, code: Optional[str] = None) -> tuple:
    """(short code label, bare article). Accepts 'NFC 2.4.1.1' prefixes and a separate code argument."""
    art = (article or "").strip()
    m = re.match(r"^(NBC|NFC|NPC|NECB)(?:\(AE\))?(?:\s+20\d\d)?[\s:,]+(?:Article\s+)?([ABC]:)?(\d.*)$", art, re.I)
    if m:
        return m.group(1).upper(), (m.group(2) or "") + m.group(3)
    ns = _mod("corpus.nbc_search")
    lab = ns.code_label(code) if ns else "NBC"
    return lab, art


def corpus_lookup(article: str, code: str = "NBC") -> Optional[dict]:
    if (code or "NBC") != "NBC":
        vc = _mod("corpus.verifier_codes")
        try:
            return vc.lookup_attribution(code, article) if vc else None
        except Exception:
            return None
    v = _mod("corpus.verifier")
    if not v or not hasattr(v, "lookup_attribution"):
        return None
    try:
        return v.lookup_attribution(article)
    except Exception:
        return None


def corpus_verify(article: str, code: str = "NBC") -> dict:
    lab, bare = split_code(article, code)
    if lab is None:
        return {"article": article, "code": code, "exists": False, "unresolved": False,
                "message": f"Unknown code '{code}' (expected NBC, NFC, NPC or NECB)."}
    if lab != "NBC":
        vc, ns = _mod("corpus.verifier_codes"), _mod("corpus.nbc_search")
        ed = ns.CODES[lab][0]
        out = {"article": bare, "code": lab, "code_edition": ed, "exists": None, "edition": ed, "page": None,
               "text_excerpt": "", "unresolved": True}
        if not vc:
            out["message"] = "Citation verifier for other codes not available; result unresolved."
            return out
        a = vc.get_article(lab, bare) if vc.article_exists(lab, bare) else None
        out.update(exists=a is not None, unresolved=False)
        if a:
            out.update(page=a.get("pdf_page"), title=a.get("title"), source=a.get("source"))
            out["text_excerpt"] = " ".join(f"({x.get('number')}) {x.get('text', '')}" for x in a.get("sentences", []))[:600]
        else:
            out["message"] = f"Article not found in indexed {ed} text."
        return out
    article = bare
    v = _mod("corpus.verifier")
    out = {"article": article, "code": "NBC", "code_edition": "NBC(AE) 2023", "exists": None, "edition": "NBC(AE) 2023 2nd printing", "page": None,
           "text_excerpt": "", "unresolved": True}
    if not v or not hasattr(v, "article_exists"):
        out["message"] = "Citation verifier not available; result unresolved."
        return out
    try:
        exists = bool(v.article_exists(article))
        out.update(exists=exists, unresolved=False)
        if exists:
            a = v.get_article(article) or {}
            out["page"] = a.get("pdf_page")
            out["title"] = a.get("title")
            out["source"] = {"doc": v.SOURCE_DOC, "page": a.get("pdf_page")}
            txt = a.get("text")
            if not txt:
                txt = " ".join(f"({s.get('number')}) {s.get('text', '')}" for s in a.get("sentences", []))
            out["text_excerpt"] = txt[:600]
        else:
            out["message"] = "Article not found in indexed NBC(AE) 2023 text."
    except Exception as e:  # noqa
        out["message"] = f"Verifier error: {e}"
        out.update(exists=None, unresolved=True)
    return out


def search_corpus(q: str, k: int = 3) -> list:
    s = _mod("corpus.search")
    if not s:
        return []
    try:
        return s.search(q, k)
    except Exception:
        return []


def _coded(items) -> str:
    return "; ".join(f"{i.get('code')}: {i.get('text') or 'unresolved'}" for i in (items or []))


def _intent_text(it) -> tuple:
    """Flatten a structured intent record to (text, edition)."""
    if not it or it.get("status") == "unresolved":
        return "", (it or {}).get("intent_edition")
    seen, parts = set(), []
    for p in it.get("provisions", []):
        for r in p.get("records", []):
            for x in r.get("intents", []):
                t = x.get("text")
                if t and t not in seen:
                    seen.add(t)
                    parts.append(t)
    return " ".join(parts), it.get("intent_edition")


# ---------------------------------------------------------------- helpers
def get_app(app_id: str) -> dict:
    a = models.load(app_id)
    if a is None:
        raise HTTPException(404, f"application {app_id} not found")
    return a


def refresh(a: dict) -> dict:
    """Recompute completeness and professional flags (never touches declarations)."""
    c = comp_mod.compute(a)
    a["completeness"] = {"percent": c["percent"], "items": c["items"]}
    flags = c["professional_flags"]
    a["professional_flags"] = flags
    if flags:
        a.setdefault("provenance", {})["professional_flags"] = {"source": "needs_professional", "confidence": 1.0}
    return c


def _prov(a, path, source, conf=1.0):
    a.setdefault("provenance", {})[path] = {"source": source, "confidence": conf}


def load_samples() -> dict:
    out = {}
    if SAMPLES_DIR.exists():
        for f in sorted(SAMPLES_DIR.glob("*.json")):
            try:
                out[f.stem] = json.loads(f.read_text(encoding="utf-8"))
            except ValueError:
                pass
    return out


FALLBACK_QUESTIONS = [
    {"id": "q_owner", "section": "A", "prompt": "Who is the owner (name)?", "help": "Legal name of the building owner.", "field_path": "applicant.owner_name", "type": "text", "required": True},
    {"id": "q_addr", "section": "A", "prompt": "What is the owner's mailing address?", "help": "", "field_path": "applicant.mailing_address", "type": "text", "required": True},
    {"id": "q_email", "section": "A", "prompt": "What email should we use?", "help": "", "field_path": "applicant.email", "type": "text", "required": True},
    {"id": "q_site", "section": "B", "prompt": "What is the municipal address of the project?", "help": "", "field_path": "location.municipal_address", "type": "text", "required": True},
    {"id": "q_desc", "section": "B", "prompt": "Describe what you want to build or do differently.", "help": "Free text. Facts you mention are suggested, not saved, until you confirm them.", "field_path": "project.description", "type": "text", "required": True},
    {"id": "q_occ", "section": "B", "prompt": "What is the major occupancy (e.g. Group C residential)?", "help": "", "field_path": "project.occupancy", "type": "text", "required": True},
    {"id": "q_storeys", "section": "B", "prompt": "How many storeys (building height)?", "help": "", "field_path": "project.storeys", "type": "number", "required": True},
    {"id": "q_area", "section": "B", "prompt": "Building area in square metres?", "help": "", "field_path": "project.building_area_m2", "type": "number", "required": True},
    {"id": "q_units", "section": "B", "prompt": "How many dwelling units per floor?", "help": "", "field_path": "project.units_per_floor", "type": "number", "required": True},
    {"id": "q_spr", "section": "B", "prompt": "Is the building sprinklered?", "help": "", "field_path": "project.sprinklered", "type": "bool", "required": True},
    {"id": "q_new", "section": "B", "prompt": "Is this new construction or a renovation?", "help": "", "field_path": "project.new_or_renovation", "type": "choice", "choices": ["new", "renovation"], "required": True},
    {"id": "q_alt", "section": "C", "prompt": "Briefly, what alternative are you proposing?", "help": "", "field_path": "variance.proposed_alternative.summary", "type": "text", "required": True},
]


def questions() -> list:
    f = CONTENT_DIR / "intake_questions.json"
    if f.exists():
        try:
            q = json.loads(f.read_text(encoding="utf-8"))
            if isinstance(q, dict):
                q = q.get("questions", [])
            if isinstance(q, list) and q:
                return q
        except ValueError:
            pass
    return FALLBACK_QUESTIONS


def _cond(a: dict, when) -> bool:
    if not when:
        return True
    m = re.match(r"^\s*([\w\.]+)\s*(==|!=)?\s*(.*)$", str(when))
    path, op, val = m.group(1), m.group(2), (m.group(3) or "").strip().strip("'\"")
    cur = get_path(a, path)
    if not op:
        return bool(cur)
    s = str(cur).lower() if isinstance(cur, bool) else str(cur)
    return (s == val.lower() if isinstance(cur, bool) else s == val) == (op == "==")


def _blank(v) -> bool:
    return v is None or v == "" or v == []


def next_question(a: dict, skip: set = ()) -> Optional[dict]:
    for q in questions():
        if q.get("id") in skip or not q.get("required", True):
            continue
        if _cond(a, q.get("when")) and _blank(get_path(a, q["field_path"])):
            return q
    return None


def parse_answer(q: dict, ans: Any):
    """Return (value, confidence) or (None, 0) if it cannot be parsed. Never invents."""
    t = q.get("type", "text")
    if ans is None or (isinstance(ans, str) and not ans.strip()):
        return None, 0.0
    s = str(ans).strip()
    if t == "text" or t == "date":
        return s, 1.0 if t == "text" or re.match(r"^\d{4}-\d{2}-\d{2}$", s) else 0.8
    if t == "number":
        m = re.search(r"-?\d[\d,]*\.?\d*", s)
        if not m:
            return None, 0.0
        n = float(m.group(0).replace(",", ""))
        if q["field_path"].endswith(("storeys", "units_per_floor")):
            n = int(n)
        return n, 0.95 if s.replace(",", "") == m.group(0).replace(",", "") else 0.75
    if t == "bool":
        if isinstance(ans, bool):
            return ans, 1.0
        if re.search(r"\b(no|not|false|n)\b", s, re.I):
            return False, 0.9
        if re.search(r"\b(yes|true|y|sprinklered)\b", s, re.I):
            return True, 0.9
        return None, 0.0
    if t == "choice":
        for c in q.get("choices") or []:
            if s.lower() == str(c).lower():
                return c, 1.0
        for c in q.get("choices") or []:
            if str(c).lower() in s.lower():
                return c, 0.7
        return None, 0.0
    return s, 0.5


# ---------------------------------------------------------------- applications
@app.post("/api/applications")
def create_application(body: Optional[dict] = Body(default=None)):
    body = dict(body or {})
    sample = body.pop("sample", None)
    base = {}
    if sample:
        s = load_samples().get(sample)
        if s is None:
            raise HTTPException(404, f"sample {sample} not found")
        base = {k: v for k, v in s.items() if not k.startswith("_") and k != "id"}
    a = models.normalize({"id": models.uuid.uuid4().hex[:8], **models.deep_merge(base, {k: v for k, v in body.items() if k != "id"})})
    refresh(a)
    return models.save(a)


@app.get("/api/applications/{app_id}")
def read_application(app_id: str):
    return get_app(app_id)


@app.patch("/api/applications/{app_id}")
def patch_application(app_id: str, patch: dict = Body(...)):
    a = get_app(app_id)
    patch = {k: v for k, v in patch.items() if k not in PROTECTED}
    merged = models.normalize(deep_merge(a, patch))
    for p in leaf_paths(patch):
        _prov(merged, p, "applicant")
    refresh(merged)
    return models.save(merged)


@app.post("/api/applications/{app_id}/intake/next")
def intake_next(app_id: str, body: Optional[dict] = Body(default=None)):
    a = get_app(app_id)
    body = body or {}
    extracted, conf, suggested = {}, 0.0, {}
    qs = {q["id"]: q for q in questions()}
    cur = qs.get(body.get("question_id")) or next_question(a)
    skip = set()
    if "answer" in body and body["answer"] is not None and cur:
        val, conf = parse_answer(cur, body["answer"])
        if val is not None and conf >= 0.5:
            set_path(a, cur["field_path"], val)
            _prov(a, cur["field_path"], "applicant", conf)
            extracted[cur["field_path"]] = val
            a = models.normalize(a)
            if cur["field_path"] == "project.description":
                for fp, (v, c) in get_llm().extract_facts(str(val)).items():
                    if _blank(get_path(a, fp)) or fp == "project.new_or_renovation":
                        suggested[fp] = {"value": v, "confidence": c, "provenance": "ai_draft",
                                         "note": "Suggested from your text; not saved until you answer or patch it."}
        else:
            skip = set()  # re-ask the same question; nothing stored
            refresh(a)
            models.save(a)
            return {"question": cur, "extracted": {}, "confidence": 0.0, "suggested": {},
                    "message": "Could not read that answer; nothing was saved."}
    refresh(a)
    models.save(a)
    nq = next_question(a, skip)
    total = [q for q in questions() if q.get("required", True)]
    return {"question": nq, "extracted": extracted, "confidence": conf, "suggested": suggested,
            "remaining": sum(1 for q in total if _cond(a, q.get("when")) and _blank(get_path(a, q["field_path"])))}


def _nbc_search():
    s = _mod("corpus.nbc_search")
    if s is None:
        raise HTTPException(501, "Full NBC search index is not available.")
    return s


def _expanded_search(q: str, k: int, parts=None, codes=None) -> tuple:
    """BM25, plus (only when a hosted LLM is active) a union with a keyword-rewritten query.
    The LLM only rewrites vocabulary; every returned article comes from retrieval. Returns (results, expansion)."""
    s = _nbc_search()
    base = s.search_articles(q, max(k, 20), parts, codes)
    exp = {"used": False, "keywords": None, "llm": None}
    try:
        llm = get_llm()
        exp["llm"] = llm.name
        if llm.name != "offline":
            raw = llm.expand_query(q) or ""
            words = re.findall(r"[A-Za-z][A-Za-z\-]+", raw)[:8]  # letters only: no article numbers
            if words:
                kw = " ".join(words)
                extra = s.search_articles(kw, max(k, 20), parts, codes)
                # normalise each list by its own top score, then blend: plain query 1.0, expansion 0.7
                bt = max([r["score"] for r in base] or [1.0]) or 1.0
                et = max([r["score"] for r in extra] or [1.0]) or 1.0
                best = {}
                for r in base:
                    best[(r["code"], r["article"])] = dict(r, score=round(r["score"] / bt, 3), via_expansion=False)
                for r in extra:
                    key = (r["code"], r["article"])
                    add = 0.7 * r["score"] / et
                    if key in best:
                        best[key]["score"] = round(best[key]["score"] + add, 3)
                    else:
                        best[key] = dict(r, score=round(add, 3), via_expansion=True)
                base = sorted(best.values(), key=lambda r: -r["score"])
                exp.update(used=True, keywords=kw)
    except Exception:
        exp.update(used=False, keywords=None)
    return base[:k], exp


def _suggest(a: dict, k: int = 6) -> list:
    """Candidate articles from the project text; reasons quote only retrieved NBC text."""
    s = _nbc_search()
    var = a["variance"]
    q = " ".join([a["project"].get("description", ""), var.get("proposed_alternative", {}).get("summary", ""),
                  var.get("acceptable_solution", {}).get("explanation", "")]).strip()
    if not q:
        return []
    part = a["project"].get("part") or rules.determine_part(a["project"])["part"]
    out = []
    for h in _expanded_search(q, k)[0]:
        terms = s.matched_terms(q, s.articles_of(h["code"]).get(h["article"], {}))
        h = dict(h)
        h["in_project_part"] = (str(h["part"]) == str(part)) if (part and h["code"] == "NBC") else None
        h["reason"] = (f"Matched {', '.join(terms[:6])} in {h['code']} '{h['title']}' (Part {h['part']}, "
                       f"{h.get('section_title') or 'section'}; p.{h['pdf_page']}). Retrieved by text similarity; "
                       "confirm it is the requirement you are varying.")
        out.append(h)
    return out


@app.post("/api/applications/{app_id}/classify")
def classify(app_id: str):
    a = get_app(app_id)
    res = rules.classify(a, suggested=_suggest(a))
    # Persist the inferred topic when none was chosen, so completeness and the professional-stop rule
    # follow the project the applicant actually described (not a default).
    if not (a.get("variance", {}).get("topic") or "").strip():
        a.setdefault("variance", {})["topic"] = res["topic"]
        models.save(a)
    return res


@app.get("/api/topics")
def topics():
    s = _nbc_search()
    return {"topics": rules.TOPICS, "browse": s.browse(), "codes": s.code_counts(), "edition": "NBC(AE) 2023",
            "note": "browse lists NBC Division B (Parts 1 and 3 to 11). Search covers NBC, NFC, NPC and NECB (see codes). Titles are taken from the code text."}


@app.post("/api/search/articles")
def search_articles_ep(body: dict = Body(...)):
    q = str(body.get("query") or "").strip()
    if not q:
        raise HTTPException(422, "query is required")
    try:
        k = max(1, min(int(body.get("k", 8)), 50))
    except (TypeError, ValueError):
        raise HTTPException(422, "k must be an integer")
    bad = [c for c in (body.get("codes") or []) if _nbc_search().code_label(c) is None]
    if bad:
        raise HTTPException(422, f"unknown code(s) {bad}; expected NBC, NFC, NPC or NECB")
    res, exp = _expanded_search(q, k, body.get("parts"), body.get("codes"))
    import guardrails
    out = {"query": q, "expansion": exp, **_nbc_search().apply_quality(q, res, exp)}
    ref = guardrails.check(q)   # approval / verdict question: still show code text, plus the standard reply
    if ref:
        out["refusal"] = ref
    return out


@app.get("/api/section-d/templates")
def section_d_templates(topic: str = "other_nbc"):
    """Section D checklist items. Lookup topics get only the generic Division C / NFC items, not stair- or Edmonton-specific ones."""
    t = json.loads((CONTENT_DIR / "section_d_templates.json").read_text(encoding="utf-8"))
    items = t["items"]
    if topic != rules.SUPPORTED_TOPIC:
        items = [i for i in items if "Div C" in i.get("code_ref", "") or "NFC" in i.get("code_ref", "")]
    return {**{k: v for k, v in t.items() if k != "items"}, "topic": topic, "items": items}


def _build_row(art: str, llm, with_chunks: bool = True, accept_unattributed: bool = False, code: str = "NBC") -> tuple:
    """Return (row, resolved). Real lookup only; text never invented."""
    row, resolved = _build_row0(art, llm, with_chunks, accept_unattributed, code)
    ns = _mod("corpus.nbc_search")
    if ns and code in ns.CODES:
        row["code"], row["code_edition"] = code, ns.CODES[code][0]
    return row, resolved


def _build_row0(art, llm, with_chunks, accept_unattributed, code):
    disp = art if code == "NBC" else f"{code} {art}"
    r = corpus_lookup(art, code)
    if not r or (not r.get("objectives") and not r.get("functions") and not (_intent_text(r.get("intent"))[0] if accept_unattributed else r.get("intent"))):
        exists = bool(r and r.get("source"))
        row = {"article": art, "objective": "unresolved", "function": "unresolved", "intent": "unresolved",
               "explainer": "", "source": (r or {}).get("source") or {},
               "verified": bool(r and r.get("verified")) or (accept_unattributed and exists), "provenance": "lookup",
               "note": (r or {}).get("note") or "Corpus lookup unavailable; unresolved."}
        if accept_unattributed and exists:
            row["note"] = ((r or {}).get("note") or "") + " Root-article rule: use the objectives attributed to the root article; a person should confirm."
            row["explainer"] = llm.explain_article(disp, "", "", "")
        return row, False
    obj, fn = _coded(r["objectives"]), _coded(r["functions"])
    intent, ied = _intent_text(r.get("intent"))
    src = r.get("source") or {}
    art_rec = corpus_verify(art, code)
    retrieved = []
    if with_chunks:
        hits = search_corpus(f"{art} {art_rec.get('title') or ''}", 3)
        retrieved = [{"doc": h["doc"], "page": h["page"]} for h in hits]
    ex = llm.explain_article(disp, (intent + (f" [{ied}]" if intent and ied else "")), obj, fn)
    if retrieved:
        ex += " Retrieved context: " + "; ".join(f"{h['doc']} p.{h['page']}" for h in retrieved) + "."
    row = {"article": art, "objective": obj or "unresolved", "function": fn or "unresolved",
           "intent": intent or "unresolved", "intent_edition": ied,
           "objectives": r["objectives"], "functions": r["functions"],
           "explainer": ex, "retrieved": retrieved,
           "source": {"doc": src.get("doc"), "page": src.get("page")},
           "verified": bool(r.get("verified")), "provenance": "lookup"}
    if r.get("root_used"):
        row["root_used"] = r["root_used"]
    if r.get("note"):
        row["note"] = r["note"]
    return row, True


def _norm_art(x: str, code: str = "NBC") -> str:
    lab, bare = split_code(x, code)
    return f"{lab}|" + re.sub(r"\s+", "", bare).rstrip(".").replace(".(", "(")


def _row_key(r: dict) -> str:
    return _norm_art(r.get("article"), r.get("code") or "NBC")


@app.post("/api/applications/{app_id}/section-c/add")
def section_c_add(app_id: str, body: dict = Body(...)):
    a = get_app(app_id)
    raw = str(body.get("article") or "").strip()
    if not raw:
        raise HTTPException(422, "article is required")
    code, art = split_code(raw, body.get("code"))
    if code is None:
        raise HTTPException(422, f"unknown code '{body.get('code')}'; expected NBC, NFC, NPC or NECB")
    rec = corpus_verify(art, code)
    if rec.get("exists") is not True:
        raise HTTPException(404, f"Article {art} was not found in the indexed {rec.get('code_edition', code)} text; nothing was added.")
    rows = a["variance"].setdefault("section_c", [])
    if any(_row_key(r) == _norm_art(art, code) for r in rows):
        raise HTTPException(409, f"Article {art} ({code}) is already in Section C.")
    row, _ = _build_row(art, get_llm(), with_chunks=False, accept_unattributed=True, code=code)
    rows.append(row)
    i = len(rows) - 1
    if row.get("explainer"):
        _prov(a, f"variance.section_c.{i}.explainer", "ai_draft", 0.5)
    arts = a["variance"].setdefault("acceptable_solution", {}).setdefault("articles", [])
    cite = art if code == "NBC" else f"{code} {art}"
    if not any(_norm_art(x) == _norm_art(art, code) for x in arts):
        arts.append(cite)
        _prov(a, "variance.acceptable_solution.articles", "applicant", 1.0)
    refresh(a)
    return models.save(a)


@app.delete("/api/applications/{app_id}/section-c/{index}")
def section_c_delete(app_id: str, index: int):
    a = get_app(app_id)
    rows = a["variance"].get("section_c") or []
    if index < 0 or index >= len(rows):
        raise HTTPException(404, f"Section C row {index} does not exist.")
    removed = rows.pop(index)
    pv = a.setdefault("provenance", {})
    pre = "variance.section_c."
    moved = {}
    for k in [k for k in pv if k.startswith(pre)]:
        m = re.match(r"variance\.section_c\.(\d+)\.(.*)$", k)
        v = pv.pop(k)
        if not m:
            continue
        n = int(m.group(1))
        if n != index:
            moved[f"{pre}{n - 1 if n > index else n}.{m.group(2)}"] = v
    pv.update(moved)
    art = removed.get("article")
    asol = a["variance"].get("acceptable_solution", {})
    if art and not any(_row_key(r) == _row_key(removed) for r in rows):
        asol["articles"] = [x for x in asol.get("articles", []) if _norm_art(x) != _row_key(removed)]
    refresh(a)
    return models.save(a)


@app.post("/api/applications/{app_id}/section-c/generate")
def section_c_generate(app_id: str, scope: str = "core"):
    a = get_app(app_id)
    rows, unresolved, llm = [], [], get_llm()
    arts = rules.candidate_articles(a, scope)
    a["variance"].setdefault("acceptable_solution", {})
    if not a["variance"]["acceptable_solution"].get("articles"):
        a["variance"]["acceptable_solution"]["articles"] = arts
        _prov(a, "variance.acceptable_solution.articles", "lookup", 0.6)
    pv = a.setdefault("provenance", {})
    for k in [k for k in pv if k.startswith("variance.section_c")]:
        del pv[k]
    for i, art in enumerate(arts):
        r = corpus_lookup(art)
        if not r or (not r.get("objectives") and not r.get("functions") and not r.get("intent")):
            unresolved.append(art)
            rows.append({"article": art, "objective": "unresolved", "function": "unresolved", "intent": "unresolved",
                         "explainer": "", "source": (r or {}).get("source") or {},
                         "verified": bool(r and r.get("verified")), "provenance": "lookup",
                         "note": (r or {}).get("note") or "Corpus lookup unavailable; unresolved."})
            continue
        obj, fn = _coded(r["objectives"]), _coded(r["functions"])
        intent, ied = _intent_text(r.get("intent"))
        src = r.get("source") or {}
        art_rec = corpus_verify(art)
        hits = search_corpus(f"{art} {art_rec.get('title') or ''}", 3)
        retrieved = [{"doc": h["doc"], "page": h["page"]} for h in hits]
        ex = llm.explain_article(art, (intent + (f" [{ied}]" if intent and ied else "")), obj, fn)
        if retrieved:
            ex += " Retrieved context: " + "; ".join(f"{h['doc']} p.{h['page']}" for h in retrieved) + "."
        row = {"article": art, "objective": obj or "unresolved", "function": fn or "unresolved",
               "intent": intent or "unresolved", "intent_edition": ied,
               "objectives": r["objectives"], "functions": r["functions"],
               "explainer": ex, "retrieved": retrieved,
               "source": {"doc": src.get("doc"), "page": src.get("page")},
               "verified": bool(r.get("verified")), "provenance": "lookup"}
        if r.get("root_used"):
            row["root_used"] = r["root_used"]
        if r.get("note"):
            row["note"] = r["note"]
        rows.append(row)
        _prov(a, f"variance.section_c.{i}.explainer", "ai_draft", 0.5)
    a["variance"]["section_c"] = rows
    refresh(a)
    models.save(a)
    return {"section_c": rows, "unresolved": unresolved, "llm": llm.name,
            "message": ("Corpus lookup unavailable; rows are unresolved." if len(unresolved) == len(rows) and rows else "")}


@app.get("/api/applications/{app_id}/completeness")
def completeness(app_id: str):
    a = get_app(app_id)
    c = refresh(a)
    models.save(a)
    return c


@app.get("/api/applications/{app_id}/map")
def get_map(app_id: str):
    a = get_app(app_id)
    c = refresh(a)
    return mapgraph.build(a, c)


@app.get("/api/applications/{app_id}/reviewer-summary")
def reviewer_summary(app_id: str):
    a = get_app(app_id)
    return reviewer.summary(a, refresh(a))


@app.post("/api/applications/{app_id}/rfi-draft")
def rfi(app_id: str):
    a = get_app(app_id)
    return reviewer.rfi_draft(a, refresh(a))


@app.get("/api/applications/{app_id}/export/pdf")
def export_pdf(app_id: str):
    a = get_app(app_id)
    ex = _mod("export")
    if not ex or not hasattr(ex, "fill_scc"):
        raise HTTPException(501, "PDF export is not available: export stream (app/backend/export) not present.")
    refresh(a)
    out = Path(tempfile.mkdtemp()) / f"variance_{app_id}.pdf"
    try:
        ex.fill_scc(a, str(out))
    except Exception as e:
        raise HTTPException(500, f"export failed: {e}")
    return FileResponse(str(out), media_type="application/pdf", filename=out.name)


@app.post("/api/applications/{app_id}/submission-package")
def submission_package(app_id: str, body: Optional[dict] = Body(default=None)):
    a = get_app(app_id)
    d = a.get("declarations", {})
    if d.get("owner_signed") is not True:
        raise HTTPException(409, "Blocked: declarations.owner_signed is not true. The owner must sign; this tool never signs for them.")
    if comp_mod._txt(a.get("applicant", {}).get("owner_representative")) and d.get("rep_signed") is not True:
        raise HTTPException(409, "Blocked: a representative is named but declarations.rep_signed is not true.")
    ex = _mod("export")
    if not ex or not hasattr(ex, "build_package"):
        raise HTTPException(501, "Submission package is not available: export stream (app/backend/export) not present.")
    refresh(a)
    out = Path(tempfile.mkdtemp()) / f"package_{app_id}.zip"
    try:
        res = ex.build_package(a, (body or {}).get("attachments", []), str(out))
    except ValueError as e:
        raise HTTPException(409, str(e))
    except Exception as e:
        raise HTTPException(500, f"package failed: {e}")
    # The zip holds the filled form, attachments, cover_note.md and submission.eml (a DRAFT; never sent).
    return FileResponse(str(out), media_type="application/zip", filename=f"submission-package-{app_id}.zip")


# ---------------------------------------------------------------- global
@app.get("/api/applications/{app_id}/similar-standata")
def similar_standata(app_id: str, k: int = 5):
    a = get_app(app_id)
    q = " ".join([a["variance"].get("topic", "").replace("_", " "), a["project"].get("description", ""),
                  a["variance"]["proposed_alternative"].get("summary", "")])
    hits = [h for h in search_corpus(q, 40) if h["doc"].lower().startswith("standata")][:k]
    return {"query": q.strip(), "results": [{"doc": h["doc"], "page": h["page"], "score": h["score"],
                                             "excerpt": h["text"][:300]} for h in hits],
            "note": "Retrieved by text similarity for the applicant to read; not a determination that a variance applies."}


@app.get("/api/citations/verify")
def citations_verify(article: str, code: str = "NBC"):
    return corpus_verify(article.strip(), code)


@app.get("/api/samples")
def samples_list():
    skip = {"seeded_defects", "application.example"}  # ground truth and the shape-only template are not applications
    return [{"name": k, "id": v.get("id"), "note": v.get("_note", "")} for k, v in load_samples().items()
            if k not in skip]


@app.get("/api/samples/{name}")
def samples_get(name: str):
    s = load_samples().get(name)
    if s is None:
        raise HTTPException(404, f"sample {name} not found")
    return s


@app.get("/api/health")
def health():
    return {"ok": True, "llm": get_llm().name, "corpus": _mod("corpus.verifier") is not None,
            "export": _mod("export") is not None}


# Optional routers: any routes_*.py beside this file that exposes `router` is mounted automatically,
# so feature streams add endpoints without editing this file.
for _rp in sorted(Path(__file__).parent.glob("routes_*.py")):
    try:
        app.include_router(importlib.import_module(_rp.stem).router)
    except Exception as _e:  # a broken stream must not take the whole API down
        print(f"[routes] skipped {_rp.stem}: {_e}")


def _warm_indexes():
    """Load the search indexes once at startup so the first user request is not slow."""
    try:
        _nbc_search().search_articles("exit", 1)
        from corpus import precedents
        precedents.search_precedents("exit", 1)
    except Exception as _e:
        print(f"[warmup] skipped: {_e}")


import threading as _threading
_threading.Thread(target=_warm_indexes, daemon=True).start()
