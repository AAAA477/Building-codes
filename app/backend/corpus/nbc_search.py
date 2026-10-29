"""Full-code BM25 search over every NBC(AE) 2023 article in app/data/corpus/nbc_articles.json.

search_articles(query, k=8, parts=None, codes=None) -> [{code, article, title, part, division, pdf_page,
    snippet, objectives:[codes], has_attribution, has_intent, score}]

Index is persisted to app/data/corpus/nbc_index.json and loaded lazily. Rebuild (from app/backend):
    python -m corpus.nbc_search --rebuild
Other codes (NFC/NPC/NECB) are not indexed here; to add one, register a loader in LOADERS that yields
(code_label, key, record) like _nbc_records() and rebuild.
"""
from __future__ import annotations
import json, math, re, sys
from collections import Counter, defaultdict
from functools import lru_cache

from . import DATA, EDITION

INDEX_FILE = DATA / "search_index.json"

CODES = {  # short label -> (edition label, articles file, intents file)
    "NBC": ("NBC(AE) 2023", "nbc_articles.json", "intents.json"),
    "NFC": ("NFC(AE) 2023", "nfc_articles.json", "nfc_intents.json"),
    "NPC": ("NPC 2020", "npc_articles.json", "npc_intents.json"),
    "NECB": ("NECB 2020", "necb_articles.json", "necb_intents.json"),
}


def code_label(c) -> str:
    """Accept 'NFC', 'nfc', 'NFC(AE) 2023' ... and return the short label (or None)."""
    c = (c or "NBC").strip().upper()
    for k in CODES:
        if c.startswith(k):
            return k
    return None

# ---------------------------------------------------------------- retrieval config (tuned on the 70% tune split)
CONFIG_FILE = DATA / "retrieval_config.json"
DEFAULT_CFG = {"k1": 1.3, "b": 0.6, "w_title": 4.0, "w_sect": 1.5, "w_body": 1.0, "stem": True,
               "phrase_boost": 0.0, "noise_filter": True, "cross_code_factor": 1.3}
INDEX_KEYS = ("w_title", "w_sect", "w_body", "stem")   # config values baked into the persisted index


@lru_cache(maxsize=1)
def load_cfg() -> dict:
    cfg = dict(DEFAULT_CFG)
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, encoding="utf8") as fh:
                cfg.update({k: v for k, v in json.load(fh).items() if k in DEFAULT_CFG})
        except Exception:
            pass
    return cfg


K1, B = 1.3, 0.6  # kept for importers; runtime values come from load_cfg()
STOP = set("a an and are as at be by for from has have in is it its of on or that the to was were will with this these "
           "shall not than any all each where which who their there into other such may must when if do does what how "
           "can i we my our should need use using".split())


def stem(w: str) -> str:
    if w.isdigit() or len(w) <= 3:
        return w
    for suf, rep in (("ies", "y"), ("sses", "ss"), ("ing", ""), ("ed", ""), ("es", ""), ("s", "")):
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            if suf == "s" and w.endswith(("ss", "us", "is")):
                continue
            w = w[: len(w) - len(suf)] + rep
            break
    if w.endswith("e") and len(w) > 4:
        w = w[:-1]
    return w


def tokenize(s: str, stem_on: bool = True) -> list:
    return [(stem(t) if stem_on else t) for t in re.findall(r"[a-z0-9]+", (s or "").lower()) if t not in STOP]


@lru_cache(maxsize=None)
def articles_of(label: str) -> dict:
    f = DATA / CODES[label][1]
    return json.load(open(f, encoding="utf8")) if f.exists() else {}


@lru_cache(maxsize=None)
def intents_of(label: str) -> dict:
    f = DATA / CODES[label][2]
    return json.load(open(f, encoding="utf8")) if f.exists() else {}


def _records(label):
    def loader():
        for key, a in articles_of(label).items():
            yield label, key, a
    return loader


# To add another code: add it to CODES and append its loader here, then rebuild.
LOADERS = [_records(k) for k in CODES]


def _fields(a: dict):
    body = " ".join(s.get("text", "") for s in a.get("sentences", []))
    tabs = " ".join(t.get("title", "") for t in a.get("tables", []))
    return a.get("title", ""), " ".join([a.get("section_title") or "", a.get("subsection_title") or "", tabs]), body


def build(cfg: dict = None, write: bool = True) -> dict:
    cfg = {**load_cfg(), **(cfg or {})}
    st = bool(cfg["stem"])
    docs, post, lens = [], defaultdict(list), []
    for loader in LOADERS:
        for code, key, a in loader():
            title, mid, body = _fields(a)
            intents = intents_of(code)
            tf = Counter()
            for txt, w in ((title, cfg["w_title"]), (mid, cfg["w_sect"]), (body, cfg["w_body"])):
                for t in tokenize(txt, st):
                    tf[t] += w
            i = len(docs)
            docs.append({"code": code, "key": key, "edition": CODES[code][0], "title": title, "part": a.get("part"), "division": a.get("division"),
                         "pdf_page": a.get("pdf_page"), "section": a.get("section"),
                         "section_title": a.get("section_title"),
                         "attr": bool(a.get("attributions")),
                         "intent": bool(intents.get(key) and intents[key].get("status") != "unresolved")})
            lens.append(sum(tf.values()))
            for t, f in tf.items():
                post[t].append([i, round(f, 2)])
    n = len(docs)
    idf = {t: round(math.log(1 + (n - len(p) + 0.5) / (len(p) + 0.5)), 4) for t, p in post.items()}
    idx = {"edition": EDITION, "codes": {k: v[0] for k, v in CODES.items()}, "n": n, "avg": sum(lens) / max(1, n), "lens": lens, "docs": docs,
           "idf": idf, "post": post, "cfg_index": {k: cfg[k] for k in INDEX_KEYS}}
    if write:
        with open(INDEX_FILE, "w", encoding="utf8") as fh:
            json.dump(idx, fh, separators=(",", ":"))
    return idx


@lru_cache(maxsize=1)
def _index() -> dict:
    want = {k: load_cfg()[k] for k in INDEX_KEYS}
    if INDEX_FILE.exists():
        with open(INDEX_FILE, encoding="utf8") as fh:
            idx = json.load(fh)
        if idx.get("cfg_index", {"w_title": 4.0, "w_sect": 1.5, "w_body": 1.0, "stem": True}) == want:
            return idx
    return build(load_cfg())


def _objs(a: dict) -> list:
    out = []
    for c in a.get("attributions", []):
        o = c.partition("-")[2]
        if o and o not in out:
            out.append(o)
    return out


def _snippet(a: dict, qt: set, width=240) -> str:
    best, bs = "", -1
    for s in a.get("sentences", []):
        t = s.get("text", "")
        sc = sum(1 for w in tokenize(t, bool(load_cfg()['stem'])) if w in qt)
        if sc > bs:
            best, bs = f"({s.get('number')}) {t}", sc
    return (best[:width] + "...") if len(best) > width else best


def matched_terms(query: str, rec: dict) -> list:
    qt = []
    for raw in re.findall(r"[a-z0-9]+", query.lower()):
        if raw not in STOP and stem(raw) not in qt:
            qt.append(stem(raw))
    title, mid, body = _fields(rec)
    have = set(tokenize(" ".join([title, mid, body])))
    raws = {}
    for raw in re.findall(r"[a-z0-9]+", query.lower()):
        raws.setdefault(stem(raw), raw)
    return [raws[t] for t in qt if t in have]


# ---------------------------------------------------------------- noise filter
ADMIN_ASK = re.compile(r"division\s+[ac]\b|administrat|objective|functional statement|alternative solution|equivalent|"
                       r"definition|intent statement|\bscope\b", re.I)
DOMAIN = {
    "NFC": re.compile(r"fire|sprinkl|alarm|extinguish|flammable|combustible|hazard|explosi|smok|hot work|evacuat|"
                      r"standpipe|hydrant|grease|cooking|kitchen exhaust|storage of|dangerous goods|fire department", re.I),
    "NPC": re.compile(r"plumb|drain|sewer|pipe|backflow|fixture|\btrap|sump|water heater|hot water|potable|valve|"
                      r"toilet|sink|interceptor|cross.connection|hose|sanitary|water supply|dwv", re.I),
    "NECB": re.compile(r"energy|lighting|insulat|envelope|thermal|u.value|r.value|efficien|power density|hvac|"
                       r"window.to.wall|solar|heat pump|air leakage|necb", re.I),
}


def _noise_filter(query, ranked, docs, cfg, codes_given):
    """ranked: [(score, i)] best first. Drops Division A/C administrative articles and unrelated cross-code hits."""
    ask_admin = bool(ADMIN_ASK.search(query))
    kept = [(s, i) for s, i in ranked if ask_admin or not docs[i]["key"].startswith(("A:", "C:"))]
    if codes_given:
        return kept
    top_nbc = max([s for s, i in kept if docs[i]["code"] == "NBC"] or [0.0])
    out = []
    for s, i in kept:
        c = docs[i]["code"]
        if c == "NBC" or DOMAIN.get(c, re.compile("$^")).search(query) or s >= cfg["cross_code_factor"] * top_nbc:
            out.append((s, i))
    return out


def rank(query: str, idx: dict, cfg: dict, parts=None, codes=None, limit: int = 60):
    """Core BM25 over idx with cfg. Returns [(score, doc_index)] best first (noise filter applied if cfg says so)."""
    st = bool(cfg["stem"])
    q = tokenize(query, st)
    if not q:
        return []
    parts = {str(p) for p in parts} if parts else None
    codes_set = {code_label(c) for c in codes} if codes else None
    docs, lens, avg = idx["docs"], idx["lens"], idx["avg"]
    k1, b = cfg["k1"], cfg["b"]
    scores = defaultdict(float)
    for t in set(q):
        for i, f in idx["post"].get(t, ()):
            scores[i] += idx["idf"][t] * f * (k1 + 1) / (f + k1 * (1 - b + b * lens[i] / avg))
    ranked = []
    for i, s in scores.items():
        d = docs[i]
        if parts and str(d["part"]) not in parts:
            continue
        if codes_set and d["code"] not in codes_set:
            continue
        ranked.append((s, i))
    ranked.sort(reverse=True)
    pb = cfg.get("phrase_boost") or 0.0
    if pb and len(q) > 1:
        pairs = {(a, c) for a, c in zip(q, q[1:])}
        rescored = []
        for s, i in ranked[:80]:
            d = docs[i]
            rec = articles_of(d["code"]).get(d["key"], {})
            t, mid, body = _fields(rec)
            seq = tokenize(f"{t} {mid} {body}", st)
            have = {(a, c) for a, c in zip(seq, seq[1:])}
            tseq = tokenize(t, st)
            thave = {(a, c) for a, c in zip(tseq, tseq[1:])}
            rescored.append((s + pb * len(pairs & have) + 2 * pb * len(pairs & thave), i))
        rescored.sort(reverse=True)
        ranked = rescored + ranked[80:]
    if cfg.get("noise_filter", True):
        ranked = _noise_filter(query, ranked, docs, cfg, bool(codes_set))
    return ranked[:limit]


def _result(idx, s, i, qt):
    d = idx["docs"][i]
    a = articles_of(d["code"]).get(d["key"], {})
    return {"code": d["code"], "code_label": d["code"], "code_edition": d["edition"], "article": d["key"], "title": d["title"], "part": d["part"],
            "division": d["division"], "section": d["section"], "section_title": d["section_title"],
            "pdf_page": d["pdf_page"], "snippet": _snippet(a, qt), "objectives": _objs(a),
            "has_attribution": d["attr"], "has_intent": d["intent"], "score": round(s, 3)}


def search_articles(query: str, k: int = 8, parts=None, codes=None) -> list:
    idx, cfg = _index(), load_cfg()
    qt = set(tokenize(query, bool(cfg["stem"])))
    return [_result(idx, s, i, qt) for s, i in rank(query, idx, cfg, parts, codes, limit=k)]


if __name__ == "__main__":
    if "--rebuild" in sys.argv:
        ix = build()
        print("rebuilt", ix["n"], "articles,", len(ix["idf"]), "terms ->", INDEX_FILE)
    else:
        for r in search_articles(" ".join(sys.argv[1:]) or "window guard height", 8):
            print(r["score"], r["article"], r["title"], "| p", r["pdf_page"])


@lru_cache(maxsize=1)
def browse() -> list:
    """Part -> Section tree for Division B, titles taken verbatim from the parsed NBC text."""
    parts = {}
    for key, a in articles_of("NBC").items():
        if a.get("division") != "B":
            continue
        p = parts.setdefault(a["part"], {"part": a["part"], "title": a.get("part_title") or None, "sections": {}})
        s = p["sections"].setdefault(a["section"], {"section": a["section"], "title": a.get("section_title") or None, "articles": 0})
        s["articles"] += 1
    num = lambda x: [int(n) for n in x.split(".")]
    out = []
    for pk in sorted(parts, key=num):
        p = parts[pk]
        p["sections"] = [p["sections"][k] for k in sorted(p["sections"], key=num)]
        out.append(p)
    return out


@lru_cache(maxsize=1)
def code_counts() -> list:
    ix = _index()
    c = Counter(d["code"] for d in ix["docs"])
    return [{"code": k, "label": v[0], "articles": c.get(k, 0)} for k, v in CODES.items() if c.get(k)]


# ---------------------------------------------------------------- "no good match" signal
LITERAL_MIN = 0.75   # a hit passes if it contains this share (idf-weighted) of the query's content words as literal words...
LITERAL_MIN_LONG = 0.35  # descriptive queries (5+ content words) carry filler words ('instead', 'taller') the code never uses
TITLE_MIN = 0.5      # ...or its own title does (a short query rarely appears in full in a body)


def _lit(w: str) -> str:
    w = w.lower()
    return w[:-1] if w.endswith("s") and not w.endswith("ss") and len(w) > 3 else w


def literal_coverage(query: str, rec: dict, title_only: bool = False) -> float:
    """idf-weighted share of the query's content words that occur as literal words (not stems) in the article.
    Stemming alone lets 'charging' match 'static electric charges'; literal words do not."""
    words = [w for w in dict.fromkeys(re.findall(r"[a-z0-9]+", (query or "").lower())) if w not in STOP]
    if not words:
        return 0.0
    idf = _index()["idf"]
    title, mid, body = _fields(rec)
    have = {_lit(x) for x in re.findall(r"[a-z0-9]+", (title if title_only else f"{title} {mid} {body}").lower())}
    st = bool(load_cfg()['stem'])
    wt = {w: idf.get(stem(w) if st else w, 0.1) for w in words}
    return sum(v for w, v in wt.items() if _lit(w) in have) / (sum(wt.values()) or 1.0)


def apply_quality(query: str, results: list, expansion=None) -> dict:
    """Wrap search results for the endpoint: {results, no_good_match, message}.
    no_good_match is true when no returned article contains enough of the query's own words (or of the
    LLM keyword rewrite, if one was used). Results are then withheld rather than shown as if relevant."""
    expansion = expansion or {}
    queries = [query] + ([expansion["keywords"]] if expansion.get("keywords") else [])
    best, ok = 0.0, False
    n_words = len([w for w in set(re.findall(r"[a-z0-9]+", (query or "").lower())) if w not in STOP])
    pool = list(results or []) + search_articles(query, 20)  # judge the corpus, not only the k rows the caller asked for
    for r in pool:
        rec = articles_of(r["code"]).get(r["article"], {})
        for q in queries:
            body, tit = literal_coverage(q, rec), literal_coverage(q, rec, title_only=True)
            best = max(best, body)
            ok = ok or body >= (LITERAL_MIN_LONG if n_words >= 5 else LITERAL_MIN) or tit >= TITLE_MIN
    if not results or not ok:
        return {"results": [], "no_good_match": True, "best_word_coverage": round(best, 2),
                "message": "No good match in the code text for these words. Try the term the code itself would use, "
                           "or check issued variances and policies in Similar issued."}
    return {"results": results, "no_good_match": False, "best_word_coverage": round(best, 2)}


# ---------------------------------------------------------------- optional closed-set LLM re-ranking
def llm_rerank(query: str, results: list, top: int = 30, llm=None) -> list:
    """Reorder the retrieved candidates with the chat model. CLOSED SET: only candidates already retrieved can appear,
    each at most once; anything the model returns that is not a candidate is ignored. Any failure returns `results`."""
    try:
        if llm is None:
            import llm as _llm_mod
            llm = _llm_mod.get_llm()
        if getattr(llm, "name", "offline") == "offline" or len(results) < 2:
            return results
        cands = results[:top]
        lines = "\n".join(f"{n + 1}. {r['code']} {r['article']} - {r['title']} ({r.get('section_title') or 'n/a'})"
                          for n, r in enumerate(cands))
        prompt = ("A builder described a situation. Rank the candidate code articles below by how directly they govern "
                  f"that situation, most relevant first. Situation: \"{query}\"\nCandidates:\n{lines}\n"
                  "Use only the candidate numbers. Leave out candidates that are clearly unrelated.")
        out = llm.chat_json(prompt, "a JSON list of candidate numbers, e.g. [3, 1, 7]")
        if isinstance(out, dict):
            out = next((v for v in out.values() if isinstance(v, list)), None)
        order = []
        for x in out or []:
            try:
                n = int(x) - 1
            except (TypeError, ValueError):
                continue
            if 0 <= n < len(cands) and n not in order:
                order.append(n)
        if not order:
            return results
        rest = [n for n in range(len(cands)) if n not in order]
        return [cands[n] for n in order] + [cands[n] for n in rest] + results[top:]
    except Exception:
        return results
