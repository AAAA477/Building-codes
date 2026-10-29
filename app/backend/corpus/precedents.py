"""BM25 search over issued variances, interpretations, policies, advisories and guides.

Data: app/data/corpus/precedents_chunks.jsonl (build with corpus.build_precedents). Real text only; the snippet
returned is always a verbatim substring of the chunk. Nothing here says a precedent applies: results are leads to
confirm with the Safety Codes Officer.

search_precedents(query, k=6, jurisdictions=None, source_types=None, min_score=MIN_SCORE, articles=None)
by_article(article, k=6)
coverage_item(app) -> completeness-style item dict or None
"""
from __future__ import annotations
import json, math, re
from collections import Counter, defaultdict
from functools import lru_cache

from . import DATA
from .nbc_search import tokenize as _tok

CHUNKS = DATA / "precedents_chunks.jsonl"
K1, B = 1.3, 0.6
W_TITLE = 5
# Words that say little about which precedent applies (kept out of scoring on top of the normal stopwords).
GENERIC = {"multi", "level", "building", "code", "requirement", "alberta", "nbc", "article", "variance", "provide",
           "permit", "propos", "alternative", "solution", "applic", "applicant", "project", "design", "section", "nbc"}
# Retrieval vocabulary only (both words occur in real documents); weight < 1.
SYN = {"exit": ["egress"], "egress": ["exit"]}
PHRASE_SYN = {"point access block": "single egress stair"}  # Edmonton PAB guide is about single-egress-stair buildings
TOPIC_TERMS = {"single_exit_stair": "single egress stair point access block"}
TYPE_FACTOR = {"users_guide": 0.45, "web_page": 0.6, "nrc_background": 0.6, "act": 0.7}
MIN_SCORE = 5.0          # below this a hit is not returned
STRONG_SCORE = 20.0      # coverage_item threshold; validated on the real samples (see tests)
ART_RE = re.compile(r"(?<![\d.])(\d{1,2}\.\d{1,2}\.\d{1,2}\.\d{1,3})(?![\d])")
NOTE = "An issued variance, interpretation or policy may already cover your situation. Confirm with your Safety Codes Officer."


@lru_cache(maxsize=1)
def _idx():
    chunks = [json.loads(l) for l in open(CHUNKS, encoding="utf8")]
    post, lens, toks, bigr, tbigr, ttoks = defaultdict(list), [], [], [], [], []
    for i, c in enumerate(chunks):
        head = " ".join(filter(None, [c.get("title"), c.get("label"), c.get("number")]))
        t_text, t_head = _tok(c["text"]), _tok(head)
        tf = Counter(t_text)
        for t in t_head:
            tf[t] += W_TITLE
        for t, f in tf.items():
            post[t].append((i, f))
        lens.append(sum(tf.values()))
        toks.append(set(tf))
        seq = t_head + ["|"] + t_text
        ttoks.append(set(t_head))
        tbigr.append({(a, b) for a, b in zip(t_head, t_head[1:])})
        bigr.append({(a, b) for a, b in zip(seq, seq[1:]) if a != "|" and b != "|"})
    n = len(chunks)
    idf = {t: math.log(1 + (n - len(p) + 0.5) / (len(p) + 0.5)) for t, p in post.items()}
    return {"chunks": chunks, "post": post, "lens": lens, "avg": sum(lens) / max(1, n), "idf": idf, "bigr": bigr, "tbigr": tbigr, "ttoks": ttoks,
            "n": n, "toks": toks}


def available() -> bool:
    return CHUNKS.exists()


def _terms(query: str):
    toks = [t for t in _tok(query) if t not in GENERIC]
    uniq = list(dict.fromkeys(toks))
    w = {t: 1.0 for t in uniq}
    for t in list(uniq):
        for s in SYN.get(t, ()):
            s = _tok(s)[0]
            if s not in w:
                w[s] = 0.6
    return toks, w


def _snippet(text: str, qterms: set, width=300) -> str:
    words = list(re.finditer(r"\S+", text))
    if len(text) <= width:
        return text
    hit = [m.start() for m in words if (_tok(m.group(0)) or [""])[0] in qterms]
    best = 0
    if hit:
        best = max(hit, key=lambda p: sum(1 for q in hit if p <= q < p + width))
        best = max(0, best - 40)
    s = next((m.start() for m in words if m.start() >= best), 0)
    e = s
    for m in words:
        if m.start() >= s and m.end() - s <= width:
            e = m.end()
    return text[s:e]


def _present(c, art, query_articles):
    return [a for a in query_articles if a in c["articles_cited"]]


def search_precedents(query: str, k: int = 6, jurisdictions=None, source_types=None, min_score: float = MIN_SCORE,
                      articles=None, article_boost: float = 12.0, with_meta: bool = False,
                      min_term_frac=None) -> list:
    if not available():
        return []
    ix = _idx()
    chunks, post, idf, lens, avg = ix["chunks"], ix["post"], ix["idf"], ix["lens"], ix["avg"]
    q_arts = list(dict.fromkeys(ART_RE.findall(query or "")))
    app_arts = [a for a in dict.fromkeys(articles or []) if a not in q_arts]
    qtext = ART_RE.sub(" ", query or "")
    for ph, rp in PHRASE_SYN.items():
        qtext = re.sub(ph, rp, qtext, flags=re.I)
    toks, w = _terms(qtext)
    base = list(dict.fromkeys(toks))
    if min_term_frac is None:
        min_term_frac = 1.0 if len(base) <= 2 else 0.75
    if not w and not q_arts and not app_arts:
        return []
    total = sum(idf.get(t, 0) * wt for t, wt in w.items() if t in idf) or 1.0
    bigrams = {(a, b) for a, b in zip(toks, toks[1:]) if a != b}
    jur = {j.lower() for j in jurisdictions} if jurisdictions else None
    typ = {t.lower() for t in source_types} if source_types else None
    scores = defaultdict(float)
    for t, wt in w.items():
        for i, f in post.get(t, ()):
            scores[i] += wt * idf[t] * f * (K1 + 1) / (f + K1 * (1 - B + B * lens[i] / avg))
    for i, c in enumerate(chunks):  # chunks reachable only through an article number
        if i not in scores and (q_arts or app_arts) and any(a in c["articles_cited"] for a in q_arts + app_arts):
            scores[i] = 0.0
    cand = {}
    for i, s in scores.items():
        c = chunks[i]
        if jur and c["jurisdiction"] not in jur:
            continue
        if typ and c["source_type"] not in typ:
            continue
        have = ix["toks"][i]
        cov = sum(idf[t] * wt for t, wt in w.items() if t in have) / total
        cov = min(1.0, cov)
        sc = s * (0.35 + 0.65 * cov)
        ph = [b for b in bigrams if b in ix["bigr"][i]]
        sc += 10.0 * sum(1 for t in base if t in ix["ttoks"][i]) / max(1, len(base)) if len(base) <= 6 else 0.0
        if len(base) >= 2 and not any(t in ix["ttoks"][i] for t in base):
            sc *= 0.35  # passage from a document whose own title shares none of the query words
        sc += 2.0 * len(ph) + 4.0 * sum(1 for b in bigrams if b in ix["tbigr"][i])
        hit_q = [a for a in q_arts if a in c["articles_cited"]]
        hit_a = [a for a in app_arts if a in c["articles_cited"]]
        sc += article_boost * min(2, len(hit_q)) + 3.0 * min(2, len(hit_a))
        sc *= TYPE_FACTOR.get(c["source_type"], 1.0) * (0.5 if c["title"].strip().lower() == "errata" else 1.0)
        if sc < min_score:
            continue
        if not (hit_q or hit_a) and sum(1 for t in base if t in have) < math.ceil(min_term_frac * len(base) - 1e-9):
            continue  # most of the query's content words are absent from this passage
        cand.setdefault(c["doc"], []).append((sc, i, cov, ph, hit_q + hit_a))
    best = {}
    for d, lst in cand.items():
        lst.sort(reverse=True)
        agg = lst[0][0] + sum(f * x[0] for f, x in zip((0.3, 0.15), lst[1:3]))  # corroboration across pages
        best[d] = (agg,) + lst[0][1:]
    out, seen_title, versions = [], {}, defaultdict(list)
    qset = set(w)
    for d, (sc, i, cov, ph, harts) in sorted(best.items(), key=lambda kv: -kv[1][0]):
        c = chunks[i]
        key = (c["source_type"], c["title"].lower())
        if key in seen_title:  # same-titled earlier/later revision of a document already listed
            versions[seen_title[key]].append(c.get("number") or c["doc"])
            continue
        if len(out) >= k:
            continue
        seen_title[key] = len(out)
        r = {"id": c["id"], "source_type": c["source_type"], "jurisdiction": c["jurisdiction"], "title": c["title"],
             "label": c.get("label"), "doc": c["doc"], "page": c["page"], "issue_date": c.get("issue_date"),
             "articles_cited": c["articles_cited"], "snippet": _snippet(c["text"], qset),
             "score": round(sc, 2)}
        if c.get("legal_status_note"):
            r["legal_status_note"] = c["legal_status_note"]
        if with_meta:
            r["_cover"] = round(cov, 2)
            r["_matched_articles"] = harts
            r["_title_terms"] = sorted(t for t in qset if t in ix["ttoks"][i])
            r["_matched_terms"] = sorted(t for t in qset if t in ix["toks"][i])
            raws = {}
            for rw in re.findall(r"[a-z0-9]+", qtext.lower()):
                if _tok(rw):
                    raws.setdefault(_tok(rw)[0], rw)
            r["_matched_words"] = [raws[t] for t in base if t in ix["toks"][i] and t in raws]
        out.append(r)
    for j, v in versions.items():
        out[j]["other_versions"] = v
    return out


def by_article(article: str, k: int = 6) -> list:
    """Documents whose chunks cite this exact article number (verified citations only), one best chunk each."""
    if not available():
        return []
    m = ART_RE.search(article or "")
    if not m:
        return []
    a = m.group(1)
    best = {}
    for c in _idx()["chunks"]:
        if a in c["articles_cited"]:
            n = len(re.findall(re.escape(a), c["text"])) * TYPE_FACTOR.get(c["source_type"], 1.0)
            if c["doc"] not in best or n > best[c["doc"]][0]:
                best[c["doc"]] = (n, c)
    out = []
    for d, (n, c) in sorted(best.items(), key=lambda kv: -kv[1][0])[:k]:
        j = c["text"].find(a)
        s = max(0, j - 100)
        out.append({"id": c["id"], "source_type": c["source_type"], "jurisdiction": c["jurisdiction"],
                    "title": c["title"], "label": c.get("label"), "doc": c["doc"], "page": c["page"],
                    "issue_date": c.get("issue_date"), "articles_cited": c["articles_cited"],
                    "snippet": c["text"][s:s + 300], "score": round(n, 2),
                    **({"legal_status_note": c["legal_status_note"]} if c.get("legal_status_note") else {})})
    return out


def display(r: dict) -> str:
    return r.get("label") or r["title"]


def _app_query(app: dict):
    p, var = app.get("project", {}) or {}, app.get("variance", {}) or {}
    alt = var.get("proposed_alternative", {}) or {}
    acc = var.get("acceptable_solution", {}) or {}
    topic = var.get("topic") or ""
    parts = [(p.get("description") or "")[:400], TOPIC_TERMS.get(topic, topic.replace("_", " ")),
             (alt.get("summary") or "")[:400]]
    parts += [m.get("label", "") for m in alt.get("mitigations", []) if not str(m.get("label", "")).lower().startswith("condition")]
    parts = [x for x in parts if x and not re.fullmatch(r"\[[^\]]*\]", x.strip())]
    arts = list(dict.fromkeys(a for a in
                              [ART_RE.search(x).group(1) for x in (acc.get("articles") or []) if ART_RE.search(x or "")] +
                              [ART_RE.search(r.get("article", "")).group(1) for r in var.get("section_c", []) or []
                               if ART_RE.search(r.get("article", "") or "")]))
    # article numbers go in `articles`, not the free-text query
    return ART_RE.sub(" ", " ".join(parts)), arts


def app_precedents(app: dict, k: int = 6, min_score: float = MIN_SCORE) -> list:
    q, arts = _app_query(app)
    if not q.strip() and not arts:
        return []
    return search_precedents(q, k=k, min_score=min_score, articles=arts, with_meta=True, min_term_frac=0.0)


def _key_terms(app: dict) -> list:
    topic = ((app.get("variance") or {}).get("topic") or "")
    if not topic or topic.startswith("other"):
        return []
    q = TOPIC_TERMS.get(topic, topic.replace("_", " "))
    for ph, rp in PHRASE_SYN.items():
        q = re.sub(ph, rp, q, flags=re.I)
    return [t for t in dict.fromkeys(_tok(q)) if t not in GENERIC]


def strong(r: dict, key_terms=()) -> bool:
    """A hit counts as 'may already cover this' when it scores well AND (every topic word is in the passage OR
    it cites an article the application relies on)."""
    if r.get("score", 0) < STRONG_SCORE:
        return False
    have = set(r.get("_matched_terms", []))
    if key_terms and all(t in have for t in key_terms):
        # the topic words must be in the document's own title, or the passage must also cite an application article
        return bool(set(key_terms) & set(r.get("_title_terms", []))) or bool(r.get("_matched_articles"))
    return bool(r.get("_matched_articles")) and not key_terms


def coverage_item(app: dict):
    try:
        kt = _key_terms(app)
        hits = [r for r in app_precedents(app) if strong(r, kt)]
    except Exception:
        return None
    if not hits:
        return None
    hits = [h for h in hits[:2] if h is hits[0] or h["score"] >= 0.6 * hits[0]["score"]]
    named = "; ".join(f"{display(r)} ({r['title']}) p.{r['page']}" if r.get("label") else f"{r['title']} p.{r['page']}"
                      for r in hits[:2])
    return {"id": "P.precedent_check", "label": "Existing variance, interpretation or policy", "section": "P",
            "group": "precedent", "priority": 1, "status": "uncertain",
            "message": f"A similar issued variance or policy may already cover this: {named}. Confirm it does not before filing.",
            "node_id": None}


# ---------------------------------------------------------------- presentation helpers (cards)
_ACRONYMS = {"nbc", "nfc", "npc", "necb", "wocd", "asw", "ses", "pab", "astm", "csa", "ulc", "nrc", "standata", "hvac",
             "epc", "rpr", "astc", "necb", "eifs", "ccmc", "scc"}
_PROPER = {"edmonton", "calgary", "alberta", "canada", "canadian", "alberta's"}
_MONTH = re.compile(r"^(January|February|March|April|May|June|July|August|September|October|November|December)\.?\s+(?:\d{1,2},?\s+)?(\d{4})$", re.I)


@lru_cache(maxsize=1)
def _by_id():
    return {c["id"]: c for c in _idx()["chunks"]}


def normalise_title(t: str) -> str:
    """Sentence case for ALL-CAPS titles; mixed-case titles are left as the document wrote them."""
    letters = [ch for ch in t if ch.isalpha()]
    if not letters or sum(ch.isupper() for ch in letters) / len(letters) < 0.6:
        return t
    out, depth, first = [], 0, True
    for w in t.split():
        core = re.sub(r"^[^A-Za-z0-9]+|[^A-Za-z0-9]+$", "", w)
        depth += w.count("(") - w.count(")")
        if not core:
            out.append(w); continue
        if any(ch.isdigit() for ch in core) or core.lower() in _ACRONYMS or (w.startswith("(") and len(core) <= 5):
            nw = w
        elif core.lower() in _PROPER:
            nw = w.replace(core, core.capitalize())
        else:
            nw = w.lower()
        if first:
            nw = re.sub(r"[a-z]", lambda m: m.group(0).upper(), nw, count=1)
            first = False
        out.append(nw)
    return " ".join(out)


def _month_year(d):
    if not d:
        return None
    m = _MONTH.match(d.strip())
    return f"{m.group(1).capitalize()} {m.group(2)}" if m else d.strip()


def citation(c: dict) -> str:
    """Human citation from the document's own number/title, issue date and page; never a file path."""
    st, num, page = c["source_type"], c.get("number"), c.get("page")
    date = _month_year(c.get("issue_date"))
    title = normalise_title(c["title"])
    head = {"standata_variance": "STANDATA variance", "standata_interpretation": "STANDATA interpretation",
            "standata_bulletin": "STANDATA bulletin"}.get(st)
    if head:
        who = f"{head} {num}" if num else f"{head}: {title or 'untitled'}"
    elif st == "edmonton_policy":
        who = f"Edmonton Policy {num}" if num else f"Edmonton policy document: {title or 'untitled'}"
    elif st == "calgary_advisory":
        who = f"Calgary Building Advisory {num}" if num else f"Calgary advisory: {title or 'untitled'}"
    elif st == "act":
        who = "Safety Codes Act"
    elif st == "users_guide":
        who = "Illustrated Users Guide, NBC 2020 Part 9"
    elif st == "nrc_background":
        who = f"NRC background: {normalise_title(c['title'])}"
    else:
        who = f"Web page: {normalise_title(c['title'])}"
    return ", ".join(x for x in (who, date, f"p.{page}" if page else None) if x)


_SENT = re.compile(r"(?<=[.!?:])\s+(?=[A-Z“\"(\d])|(?<=[A-Z]{4})\s+(?=[A-Z][a-z])")


def best_quote(text: str, qstems, width: int = 300) -> dict:
    """Whole-sentence verbatim excerpt (<= width chars) around the densest query-term sentence."""
    starts, pos = [0], 0
    for m in _SENT.finditer(text):
        starts.append(m.end())
    ends = starts[1:] + [len(text)]
    sents = [(a, b) for a, b in zip(starts, ends)]
    def score(a, b):
        seg = text[a:b]
        n = sum(1 for w in re.findall(r"[A-Za-z0-9]+", seg) if (_tok(w) or [""])[0] in qstems)
        letters = [ch for ch in seg if ch.isalpha()]
        if letters and sum(ch.isupper() for ch in letters) / len(letters) > 0.25:
            n *= 0.3  # letterhead / heading text rather than a requirement sentence
        if len(seg.split()) < 6:
            n *= 0.5
        return n
    i = max(range(len(sents)), key=lambda k: (score(*sents[k]), -k))
    a = sents[i][0]
    b = sents[i][1]
    j = i
    while j + 1 < len(sents) and sents[j + 1][1] - a <= width:
        j += 1
        b = sents[j][1]
    # use leading sentences too when room is left and the chosen one is not the first
    while i > 0 and b - sents[i - 1][0] <= width and score(*sents[i - 1]) > 0:
        i -= 1
        a = sents[i][0]
    q = text[a:b].strip()
    cut_end = False
    if len(q) > width:
        q = q[:width]
        q = q[:q.rfind(" ")] if " " in q else q
        cut_end = True
    q = q.rstrip()
    start_trunc = bool(q) and (q[0].islower() or q[0] in ",;)")
    end_trunc = cut_end or not q.endswith((".", "!", "?", ":", ";", '"', "”", ")"))
    return {"quote": q, "quote_truncated_start": start_trunc, "quote_truncated_end": end_trunc}


def card(r: dict, qstems=(), why: str = None) -> dict:
    """Presentation fields for a search hit r (from search_precedents)."""
    c = _by_id()[r["id"]]
    out = {"title": normalise_title(c["title"]), "citation": citation(c)}
    out.update(best_quote(c["text"], set(qstems) or set()))
    if why is not None:
        out["why_relevant"] = why
    return out
