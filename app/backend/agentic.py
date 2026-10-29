"""Agentic 'route then read' retrieval over the real code text.

STAGE 1 ROUTE : pick up to 3 code areas (Part > Section) from a menu built from the real code structure.
STAGE 2 READ  : list the section's articles (number + title), pick candidates, READ full text of at most
                MAX_READ of them, judge relevance, keep only items whose quote is a verbatim substring.
Everything shown is verified against the article JSON; unverified items are dropped.
Nothing here says a design is safe or equivalent.
"""
from __future__ import annotations
import hashlib, json, math, re, threading, time
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parents[1] / "data" / "corpus"
FILES = {"NBC": "nbc_articles.json", "NFC": "nfc_articles.json", "NPC": "npc_articles.json", "NECB": "necb_articles.json"}

# ---- limits / cost (one place) ---------------------------------------------------------------
MAX_LLM_CALLS = 8
TIMEOUT_S = 45.0
MAX_READ = 6                    # full-text reads judged by the LLM
MAX_PICK = 12                   # candidates picked per area
MAX_PROMPT_TOKENS = 30000       # hard per-search budget (stop and return what we have)
MAX_XREF = 4                    # one-hop cross references added (not LLM-judged, quote = first sentence)
PRICE_PER_M_IN = 2.50           # USD per 1M prompt tokens  - gpt-4o, estimate, check your Azure price
PRICE_PER_M_OUT = 10.00         # USD per 1M completion tokens - estimate, check your Azure price

ADMIN_RE = re.compile(r"alternative solution|compliance alternative|equivalent|variance|administrat|"
                      r"safety codes act|permit|quality management|innovative", re.I)
_cache: dict = {}


class BudgetExceeded(Exception):
    pass


# ---- data ---------------------------------------------------------------------------------------
@lru_cache(maxsize=None)
def _arts(code: str) -> dict:
    f = DATA / FILES[code]
    return json.load(open(f, encoding="utf8")) if f.exists() else {}


def _norm(s: str) -> str:
    return " ".join((s or "").split())


@lru_cache(maxsize=None)
def _text(code: str, key: str) -> str:
    a = _arts(code).get(key) or {}
    return _norm(" ".join(s.get("text", "") for s in a.get("sentences", [])))


def get_article(code: str, key: str):
    a = _arts(code).get(key)
    return a


def find_article(code: str, number: str):
    """Look in `code` first, then NBC (cross-code references). Returns (code, key) or None."""
    for c in (code, "NBC", "NFC", "NPC", "NECB"):
        if c in FILES and number in _arts(c):
            return c, number
    return None


_STOP = set("a an and are as at be by for from has have in is it its of on or that the to was were will with this these "
            "shall not than any all each where which their there into other such may must when if do does what how can "
            "i we my our should need use using instead required require existing building".split())


def _tok(s: str) -> list:
    out = []
    for t in re.findall(r"[a-z0-9]+", (s or "").lower()):
        if t in _STOP or len(t) < 2:
            continue
        for suf in ("ing", "ed", "es", "s"):
            if len(t) > len(suf) + 3 and t.endswith(suf):
                t = t[: -len(suf)]
                break
        out.append(t)
    return out


class _BM25:
    def __init__(self, docs, k1=1.2, b=0.7):
        self.docs = [Counter(d) for d in docs]
        self.len = [sum(c.values()) for c in self.docs]
        self.avg = (sum(self.len) / len(self.len)) if self.len else 1.0
        df = Counter()
        for c in self.docs:
            df.update(c.keys())
        n = len(self.docs)
        self.idf = {t: math.log(1 + (n - v + 0.5) / (v + 0.5)) for t, v in df.items()}
        self.k1, self.b = k1, b

    def score(self, q: list) -> list:
        res = []
        for c, L in zip(self.docs, self.len):
            s = 0.0
            for t in set(q):
                f = c.get(t)
                if f:
                    s += self.idf.get(t, 0) * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * L / self.avg))
            res.append(s)
        return res


# ---- menu (real structure) ----------------------------------------------------------------------
@lru_cache(maxsize=1)
def _sections() -> dict:
    """{area_id: {id, code, division, part, part_title, section, title, keys:[...], toks:[...]}}"""
    secs: dict = {}
    for code in FILES:
        for key, a in _arts(code).items():
            div = a.get("division", "B")
            sid = f"{code}:{a['section']}" + (f"/{div}" if code == "NBC" and div != "B" else "")
            s = secs.setdefault(sid, {"id": sid, "code": code, "division": div, "part": a.get("part"),
                                      "part_title": a.get("part_title") or "", "section": a["section"],
                                      "title": a.get("section_title") or "", "keys": [], "sub": set(), "titles": [],
                                      "body": []})
            s["keys"].append(key)
            s["titles"].append(a.get("title", ""))
            if a.get("subsection_title"):
                s["sub"].add(a["subsection_title"])
            s["body"].append(_text(code, key)[:600])
    for s in secs.values():
        head = f"{s['part_title']} {s['title']} " + " ".join(s["sub"])
        s["toks"] = _tok(head) * 3 + _tok(" ".join(s["titles"])) * 2 + _tok(" ".join(s["body"]))
        s["head_toks"] = _tok(head) * 2 + _tok(" ".join(s["titles"]))
    return secs


def menu(include_admin: bool = False, codes=None) -> list:
    out = []
    for s in _sections().values():
        if s["division"] != "B" and not include_admin:
            continue
        if codes and s["code"] not in codes:
            continue
        out.append(s)
    key = lambda s: (s["code"], [int(x) for x in re.findall(r"\d+", s["section"])])
    return sorted(out, key=key)


def menu_text(items) -> str:
    lines, last = [], None
    for s in items:
        hdr = f"{s['code']} Part {s['part']} {s['part_title']}"
        if hdr != last:
            lines.append(hdr)
            last = hdr
        lines.append(f"  {s['id']}: {s['title']}")
    return "\n".join(lines)


def route_bm25(query: str, items, k: int = 3) -> list:
    if not items:
        return []
    bm = _BM25([s["toks"] for s in items])
    sc = bm.score(_tok(query))
    order = sorted(range(len(items)), key=lambda i: -sc[i])[:k]
    top = sc[order[0]] if order and sc[order[0]] > 0 else 0
    return [{"id": items[i]["id"], "why": "keyword match on section titles and text (no LLM)",
             "confidence": round(sc[i] / top, 2) if top else 0.0} for i in order if sc[i] > 0]


# ---- LLM wrapper with token accounting ---------------------------------------------------------
class Ctx:
    def __init__(self, llm, deadline, max_prompt_tokens):
        self.llm, self.deadline, self.max_pt = llm, deadline, max_prompt_tokens
        self.calls = 0
        self.pt = 0
        self.ct = 0
        self.estimated = False
        self.log = []
        self.steps = 0
        self.errors = []

    def ask(self, stage: str, prompt: str, hint: str):
        if self.llm is None or getattr(self.llm, "name", "") == "offline":
            return None
        import privacy
        if not privacy.ai_allowed():
            return None
        prompt = privacy.redact_current(prompt)
        if self.calls >= MAX_LLM_CALLS:
            return None
        remaining = self.deadline - time.time()
        if remaining < 3:
            raise TimeoutError("deep-search time budget exhausted")
        est = len(prompt) // 4
        if self.pt + est > self.max_pt:
            raise BudgetExceeded(f"prompt budget {self.max_pt} tokens would be exceeded at stage {stage}")
        self.calls += 1
        self.steps += 1
        out, pt, ct = None, est, 0
        cl = getattr(self.llm, "client", None)
        if cl is not None and getattr(self.llm, "deployment", None):
            try:
                r = cl.with_options(timeout=min(remaining, 30)).chat.completions.create(
                    model=self.llm.deployment, temperature=0, response_format={"type": "json_object"},
                    messages=[{"role": "user", "content": prompt + "\nReply with JSON only. Shape: " + hint}])
                raw = (r.choices[0].message.content or "").strip()
                u = getattr(r, "usage", None)
                pt = getattr(u, "prompt_tokens", est) if u else est
                ct = getattr(u, "completion_tokens", len(raw) // 4) if u else len(raw) // 4
                out = json.loads(raw) if raw else None
            except Exception as e:
                self.errors.append(f"{stage}: {type(e).__name__}: {str(e)[:120]}")
                out = None
        else:
            self.estimated = True
            try:
                out = self.llm.chat_json(prompt, hint)
            except Exception as e:
                self.errors.append(f"{stage}: {type(e).__name__}")
            ct = len(json.dumps(out)) // 4 if out else 0
        self.pt += pt
        self.ct += ct
        self.log.append({"stage": stage, "prompt_tokens": pt, "completion_tokens": ct})
        return out

    def cost(self) -> dict:
        return {"prompt_tokens": self.pt, "completion_tokens": self.ct, "calls": self.calls,
                "estimated_tokens": self.estimated,
                "est_cost_usd": round(self.pt / 1e6 * PRICE_PER_M_IN + self.ct / 1e6 * PRICE_PER_M_OUT, 5),
                "rate_note": f"estimate at ${PRICE_PER_M_IN}/1M in, ${PRICE_PER_M_OUT}/1M out; check your Azure price"}


# ---- stage helpers ------------------------------------------------------------------------------
def _conf(x) -> float:
    try:
        return max(0.0, min(1.0, float(x)))
    except (TypeError, ValueError):
        return 0.5


def route_llm(ctx: Ctx, query: str, items) -> list:
    ids = {s["id"] for s in items}
    prompt = ("ROUTE. An applicant described a building-code variance. Choose up to 3 code areas (sections) from the MENU "
              "whose articles are most likely to hold the requirement being varied. Use only ids that appear in the menu.\n"
              f"DESCRIPTION: {query}\n\nMENU (id: section title):\n{menu_text(items)}")
    out = ctx.ask("route", prompt, '{"areas":[{"id":"NBC:9.8","why":"one line","confidence":0.0-1.0}]}')
    res, seen = [], set()
    for a in (out or {}).get("areas", []) if isinstance(out, dict) else []:
        if isinstance(a, dict) and a.get("id") in ids and a["id"] not in seen:
            seen.add(a["id"])
            res.append({"id": a["id"], "why": _norm(str(a.get("why", "")))[:200], "confidence": _conf(a.get("confidence"))})
    return res[:3]


def _section_keys(sid: str) -> list:
    s = _sections()[sid]
    return sorted(s["keys"], key=lambda k: [int(x) if x.isdigit() else 0 for x in re.findall(r"\d+", k)])


def pick_llm(ctx: Ctx, query: str, sid: str) -> list:
    s = _sections()[sid]
    keys = _section_keys(sid)
    lines = "\n".join(f"{k} {_arts(s['code'])[k].get('title','')}" for k in keys)
    prompt = (f"PICK. Section {s['code']} {s['section']} {s['title']}. From this list choose up to {MAX_PICK} article numbers "
              "most likely relevant to the description, most relevant first. Only numbers from the list.\n"
              f"DESCRIPTION: {query}\n\nARTICLES:\n{lines}")
    out = ctx.ask("pick:" + sid, prompt, '{"articles":["9.8.2.1"]}')
    ok = set(keys)
    res = []
    for n in (out or {}).get("articles", []) if isinstance(out, dict) else []:
        n = str(n).strip().rstrip(".")
        if n in ok and n not in res:
            res.append(n)
    return res[:MAX_PICK]


def pick_bm25(query: str, sid: str, k: int = MAX_PICK) -> list:
    s = _sections()[sid]
    keys = _section_keys(sid)
    bm = _BM25([_tok(_arts(s["code"])[x].get("title", "")) * 3 + _tok(_text(s["code"], x)) for x in keys])
    sc = bm.score(_tok(query))
    return [keys[i] for i in sorted(range(len(keys)), key=lambda i: -sc[i])[:k] if sc[i] > 0]


def best_sentence(code: str, key: str, query: str, width: int = 300) -> str:
    a = _arts(code).get(key) or {}
    q = set(_tok(query))
    best, bs = "", -1
    for s in a.get("sentences", []):
        t = _norm(s.get("text", ""))
        sc = len(q & set(_tok(t)))
        if t and sc > bs:
            best, bs = t, sc
    return best[:width]


_REF = re.compile(r"\b(\d{1,2}\.\d{1,2}\.\d{1,2}\.\d{1,3})\b")


def parse_xrefs(code: str, key: str) -> list:
    """Article numbers mentioned after 'Article(s)', 'Sentence(s)', 'Clause(s)', 'Subclause' in the text; must exist."""
    t = _text(code, key)
    found = []
    for m in re.finditer(r"\b(?:Articles?|Sentences?|Clauses?|Subclauses?)\s+([^;]{0,120})", t):
        for n in _REF.findall(m.group(1)):
            if n != key and n not in found:
                r = find_article(code, n)
                if r:
                    found.append(n)
    return found


def _kg():
    try:
        import kg  # type: ignore
        return kg
    except Exception:
        return None


def kg_neighbours(arts: list, via) -> list:
    """Defensive wrapper: [(article, edge_text)] from kg.expand, or [] if kg is missing/unusable."""
    k = _kg()
    if not k or not hasattr(k, "expand"):
        return []
    try:
        r = k.expand(list(arts), hops=1, via=tuple(via))
    except Exception:
        return []
    out = []
    if isinstance(r, dict):
        r = [dict(article=a, **(v if isinstance(v, dict) else {"edge": v})) for a, v in r.items()]
    for x in r or []:
        if isinstance(x, str):
            out.append((x, ""))
        elif isinstance(x, dict):
            n = x.get("article") or x.get("neighbour") or x.get("neighbor") or x.get("to") or x.get("number")
            if n:
                out.append((str(n), str(x.get("edge") or x.get("via") or x.get("why") or "")))
    return out


# ---- judge --------------------------------------------------------------------------------------
def _fix_quote(full: str, q: str):
    """Return a real substring of `full` equivalent to q (whitespace-normalised, case/curly-quote tolerant) or None."""
    q = _norm(q)
    if len(q) < 12:
        return None
    if q in full:
        return q[:300]
    # punctuation/case-insensitive match mapped back to the real span of the article text
    pos, chars = [], []
    for i, ch in enumerate(full):
        if ch.isalnum():
            pos.append(i)
            chars.append(ch.lower())
    fa = "".join(chars)
    qa = "".join(ch.lower() for ch in q if ch.isalnum())
    if len(qa) < 10:
        return None
    j = fa.find(qa)
    if j < 0:
        return None
    return full[pos[j]:pos[j + len(qa) - 1] + 1][:300]


def judge_llm(ctx: Ctx, query: str, cands: list) -> list:
    blocks = []
    for code, key in cands:
        a = _arts(code)[key]
        blocks.append(f"[{key}] {a.get('title','')}\n{_text(code, key)[:1800]}")
    prompt = ("JUDGE. Below is an applicant's description and the full text of candidate code articles. For each article decide "
              "whether it is part of the set of requirements an authority would check for this situation: the requirement the description proposes to vary, or a requirement on the same subject (for example the same building element, system or hazard) that the proposal would have to be compared with. For each "
              "KEEPER give a quote copied EXACTLY (verbatim, max 300 characters) from that article's text and one plain-English "
              "sentence of why it is relevant. Do not say the design is safe or equivalent. Non-keepers: keep=false.\n"
              f"DESCRIPTION: {query}\n\n" + "\n\n".join(blocks))
    out = ctx.ask("judge", prompt, '{"items":[{"article":"9.8.2.1","keep":true,"quote":"verbatim text","why":"one sentence"}]}')
    if not isinstance(out, dict):
        return None
    byk = {}
    for it in out.get("items", []):
        if isinstance(it, dict):
            byk[str(it.get("article", "")).strip().rstrip(".")] = it
    res = []
    for code, key in cands:
        it = byk.get(key)
        if not it or not it.get("keep"):
            continue
        q = _fix_quote(_text(code, key), str(it.get("quote", "")))
        if q:
            res.append({"code": code, "article": key, "quote": q, "why": _norm(str(it.get("why", "")))[:300]})
    return res


def _item(code, key, quote, why, extra=None) -> dict:
    a = _arts(code)[key]
    d = {"code": code, "article": key, "title": a.get("title", ""), "pdf_page": a.get("pdf_page"),
         "quote": quote, "why": why, "verified": True}
    d.update(extra or {})
    return d


def _verified(code, key, quote) -> bool:
    return bool(code in FILES and key in _arts(code) and quote and _norm(quote) in _text(code, key))


def attach_precedents(item: dict):
    try:
        from corpus import precedents as P
        rows = P.by_article(item["article"], k=8)
    except Exception:
        return
    out = []
    for r in rows:
        if r.get("source_type") in ("users_guide", "web_page", "nrc_background", "act"):
            continue
        try:
            cit = P.citation(r)
        except Exception:
            cit = r.get("title", "")
        out.append({"citation": cit, "doc": r["doc"], "page": r["page"], "source_type": r["source_type"]})
        if len(out) == 2:
            break
    item["precedents"] = out


# ---- main ---------------------------------------------------------------------------------------
def _bm25_fallback(query: str, codes, k=8) -> list:
    res = []
    try:
        from corpus import nbc_search as N
        for r in N.search_articles(query, k=k, codes=codes):
            c = N.code_label(r.get("code")) or "NBC"
            key = r["article"]
            if c in FILES and key in _arts(c):
                q = best_sentence(c, key, query)
                if q:
                    res.append(_item(c, key, q, "Keyword match (fallback); not read or judged by the LLM."))
    except Exception:
        pass
    return res


_llm_lock = threading.Lock()


def _resolve_llm():
    with _llm_lock:   # llm.get_llm() is not thread-safe on first use
        try:
            import envload
            envload.load_env()
            from llm import get_llm
            return get_llm()
        except Exception:
            return None


def deep_search(query: str, codes=None, cheap: bool = False, llm=None, max_prompt_tokens: int = MAX_PROMPT_TOKENS,
                use_cache: bool = True, with_precedents: bool = True) -> dict:
    query = _norm(query)
    if llm is None:
        llm = _resolve_llm()   # one-time client start-up (can take tens of seconds on Windows) is not search time
    t0 = time.time()
    lname = getattr(llm, "name", "offline") if llm else "offline"
    ck = hashlib.sha1(json.dumps([query, sorted(codes or []), cheap, lname, max_prompt_tokens]).encode()).hexdigest()
    if use_cache and ck in _cache and llm is not None and not getattr(llm, "_no_cache", False):
        d = dict(_cache[ck])
        d["cached"] = True
        d["seconds"] = round(time.time() - t0, 3)
        return d
    ctx = Ctx(llm, t0 + TIMEOUT_S, max_prompt_tokens)
    codes = [c.upper() for c in codes] if codes else None
    notes, fallback, budget_hit = [], False, False
    route, results = [], []
    try:
        items = menu(bool(ADMIN_RE.search(query)), codes)
        # STAGE 1
        picked = []
        if not cheap:
            try:
                picked = route_llm(ctx, query, items)
            except (BudgetExceeded, TimeoutError):
                raise
            if not picked and llm is not None and getattr(llm, "name", "offline") != "offline":
                notes.append("LLM routing returned no valid area; used keyword routing")
        if not picked:
            picked = route_bm25(query, items)
        picked = sorted(picked, key=lambda a: -a["confidence"])[:3]
        S = _sections()
        route = [{"code": S[a["id"]]["code"], "part": S[a["id"]]["part"], "section": S[a["id"]]["section"],
                  "area_id": a["id"], "title": S[a["id"]]["title"], "why": a["why"], "confidence": a["confidence"]}
                 for a in picked]
        # STAGE 2: candidates
        per_area = []
        for a in picked:
            kl = [] if cheap else pick_llm(ctx, query, a["id"])
            kb = pick_bm25(query, a["id"])
            # reciprocal-rank fusion of the LLM's title-based picks with keyword rank over the full text (zero LLM cost)
            sc = defaultdict(float)
            for lst in (kl, kb):
                for r_, kk in enumerate(lst):
                    sc[kk] += 1.0 / (10 + r_)
            ks = sorted(sc, key=lambda x: -sc[x])[:MAX_PICK]
            per_area.append((S[a["id"]]["code"], ks))
        order, i = [], 0
        weights = [2, 1, 1]
        while any(ks for _, ks in per_area):
            for ai, (code, ks) in enumerate(per_area):
                for _ in range(weights[ai] if ai < 3 else 1):
                    if ks:
                        c = (code, ks.pop(0))
                        if c not in order:
                            order.append(c)
        n_primary = MAX_READ - (1 if _kg() else 0)
        cands = order[:n_primary]
        # KG extras at zero LLM cost
        if _kg() and cands:
            for n, edge in kg_neighbours([k for _, k in cands[:3]], ("objective", "precedent")):
                r = find_article(cands[0][0], n)
                if r and r not in cands and len(cands) < MAX_READ:
                    cands.append(r)
        if len(cands) < MAX_READ:
            for c in order[n_primary:]:
                if c not in cands and len(cands) < MAX_READ:
                    cands.append(c)
        ctx.steps += len(cands)
        ctx.cands = list(cands)
        kept = judge_llm(ctx, query, cands) if cands else []
        if kept is None:
            fallback = True
            notes.append("LLM judge failed; showing keyword-ranked candidates with their best-matching sentence")
            kept = [{"code": c, "article": k, "quote": best_sentence(c, k, query),
                     "why": "Keyword match (fallback); not judged by the LLM."} for c, k in cands[:5]]
        elif llm is None or lname == "offline":
            fallback = True
        for k in kept:
            if _verified(k["code"], k["article"], k["quote"]):
                results.append(_item(k["code"], k["article"], k["quote"], k["why"]))
        # one-hop cross references (no LLM): KG if present, else parsed from text read
        have = {(r["code"], r["article"]) for r in results}
        xr = []
        for r in list(results):
            ns = [n for n, _ in kg_neighbours([r["article"]], ("xref",))] if _kg() else []
            ns = ns or parse_xrefs(r["code"], r["article"])
            for n in ns[:2]:
                f = find_article(r["code"], n)
                if f and f not in have and len(xr) < MAX_XREF and f not in [x[0] for x in xr]:
                    xr.append((f, r["article"]))
        for (c, k), parent in xr:
            q = (_arts(c)[k].get("sentences") or [{}])[0].get("text", "")
            q = _norm(q)[:300]
            if _verified(c, k, q):
                results.append(_item(c, k, q, f"Cross-referenced from Article {parent}; quote is this article's first sentence "
                                     "(not separately judged against the description).", {"cross_ref_of": parent}))
        ctx.steps += len(xr)
    except BudgetExceeded as e:
        budget_hit = True
        notes.append(str(e))
    except TimeoutError as e:
        notes.append(str(e))
        fallback = True
    except Exception as e:
        notes.append(f"{type(e).__name__}: {str(e)[:100]}")
        fallback = True
    if not results and (fallback or budget_hit or ctx.errors):
        results = _bm25_fallback(query, codes)
        fallback = True
    if with_precedents:
        for r in results:
            attach_precedents(r)
    out = {"query": query, "route": route, "results": results, "steps": ctx.steps, "llm_calls": ctx.calls,
           "seconds": round(time.time() - t0, 2), "fallback": fallback, "cheap": cheap, "llm": lname,
           "cost": ctx.cost(), "budget_exceeded": budget_hit, "notes": notes + ctx.errors[:3],
           "kg": bool(_kg()),
           "message": (None if results else "No article that clearly bears on this description was found in the routed code areas."), "disclaimer": "Retrieval aid only. Says nothing about whether any design is safe or equivalent."}
    if use_cache and not fallback and llm is not None:
        _cache[ck] = out
    return out


# ---- application helper -----------------------------------------------------------------------
def application_query(app: dict) -> str:
    v = app.get("variance") or {}
    parts = [(app.get("project") or {}).get("description") or "",
             (v.get("proposed_alternative") or {}).get("summary") or "",
             (v.get("acceptable_solution") or {}).get("explanation") or ""]
    for row in v.get("section_c") or []:
        n = row.get("article")
        if n:
            f = find_article("NBC", str(n))
            parts.append(f"Article {n} {(_arts(f[0])[n].get('title') if f else '')}")
    return _norm(" ".join(p for p in parts if p))[:1800]


def review_flags(app: dict, query: str, llm=None) -> list:
    """Section C rows that look unrelated to the description, with a reason based on the article text read."""
    rows = [str(r.get("article")) for r in (app.get("variance") or {}).get("section_c") or [] if r.get("article")]
    desc = _norm(" ".join([(app.get("project") or {}).get("description") or "",
                           ((app.get("variance") or {}).get("proposed_alternative") or {}).get("summary") or ""]))
    if not rows or not desc:
        return []
    flags, qt = [], set(_tok(desc))
    cand = []
    for n in rows:
        f = find_article("NBC", n)
        if not f:
            flags.append({"article": n, "reason": "Article number not found in the code text; check the citation."})
            continue
        cand.append((f, _text(*f)))
    ctx = Ctx(llm, time.time() + 20, 12000)
    out = None
    if cand and llm is not None:
        blocks = "\n\n".join(f"[{f[1]}] {_arts(f[0])[f[1]].get('title','')}\n{t[:700]}" for f, t in cand)
        out = ctx.ask("review", "REVIEW. For each article, decide whether its text appears unrelated to the applicant's description. "
                      "Flag only articles that look irrelevant, with a one-sentence reason based on the article text. Do not "
                      "state that the design is safe.\nDESCRIPTION: " + desc + "\n\n" + blocks,
                      '{"irrelevant":[{"article":"9.8.2.1","reason":"..."}]}')
    if isinstance(out, dict):
        have = {f[1] for f, _ in cand}
        for it in out.get("irrelevant", []):
            n = str(it.get("article", "")).strip().rstrip(".")
            if n in have:
                flags.append({"article": n, "reason": _norm(str(it.get("reason", "")))[:250]})
    else:
        for f, t in cand:
            if not (qt & set(_tok(t + " " + _arts(f[0])[f[1]].get("title", "")))):
                flags.append({"article": f[1], "reason": "No word of the description appears in this article's title or text "
                              "(keyword check only; the LLM review was not available)."})
    return flags
