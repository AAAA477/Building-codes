"""Knowledge graph over the Alberta codes (articles, objectives, functions, precedents).

Pure python, lazy loaded from app/data/corpus/kg.json (built by build_kg.py).
Public API: graph(), node(), neighbors(), expand(), why_path(), precedents_for(), siblings(), stats().
Article ids are "<CODE>|<key>" where key is the number for Division B (e.g. "NBC|3.4.2.1") and
"A:<n>"/"C:<n>" for Division A/C.
"""
import json, math, collections
from pathlib import Path

KG_PATH = Path(__file__).resolve().parent.parent / "data" / "corpus" / "kg.json"
DOC_MAX = 40            # precedent docs citing more articles than this (errata, users guide) are not used for co-citation
HUB_MAX = 30            # objectives/pairs attributed to more articles than this are not used for expansion
W_XREF_OUT, W_XREF_IN, W_XREF_GROUP = 3.0, 2.0, 0.8
W_PAIR, W_OBJ, W_PREC = 3.0, 1.2, 2.0

_G = None


class Graph:
    def __init__(self, data):
        self.nodes = data["nodes"]
        self.meta = data.get("meta", {})
        self.out = collections.defaultdict(list)   # id -> [(dst, type, ev)]
        self.inn = collections.defaultdict(list)
        self.children = collections.defaultdict(list)
        self.parent = {}
        self.edge_counts = collections.Counter()
        for s, d, t, ev in data["edges"]:
            self.out[s].append((d, t, ev))
            self.inn[d].append((s, t, ev))
            self.edge_counts[t] += 1
            if t == "parent_of":
                self.children[s].append(d)
                self.parent[d] = s
        # attribution indexes (same code only: objective ids are code-scoped)
        self.art_obj = collections.defaultdict(dict)    # art -> {obj_id: evidence}
        self.art_pairs = collections.defaultdict(dict)  # art -> {(fn_id,obj_id): [sentences]}
        self.obj_arts = collections.defaultdict(set)
        self.pair_arts = collections.defaultdict(set)
        for s, d, t, ev in data["edges"]:
            if t != "attributed_to" or not d.split("|")[1].startswith("obj:"):
                continue
            self.art_obj[s][d] = ev
            self.obj_arts[d].add(s)
            code = s.split("|")[0]
            for f in ev.get("functions", []):
                p = (f"{code}|fn:{f}", d)
                self.art_pairs[s][p] = ev.get("sentences", [])
                self.pair_arts[p].add(s)
        self.doc_arts = collections.defaultdict(set)
        self.art_docs = collections.defaultdict(set)
        for s, d, t, ev in data["edges"]:
            if t == "cites":
                self.doc_arts[s].add(d)
                self.art_docs[d].add(s)


def graph():
    global _G
    if _G is None:
        _G = Graph(json.loads(KG_PATH.read_text(encoding="utf8")))
    return _G


def article_id(code, number):
    """Accepts 'NBC','3.4.2.1' or 'NBC','A:1.1.1.1' (Division A/C prefixed)."""
    return f"{(code or 'NBC').upper()}|{number}"


def _admin(nid):
    return nid.split("|", 1)[1][:2] in ("A:", "C:")


def _public(g, nid):
    n = g.nodes[nid]
    return {"id": nid, **n}


def node(code, number):
    g = graph()
    nid = article_id(code, number)
    return _public(g, nid) if nid in g.nodes else None


def _ev_summary(typ, ev):
    return ev


def neighbors(code, number, types=None):
    """All direct neighbours: [{id, type, direction, edge:{type, evidence}, node}]."""
    g = graph()
    nid = article_id(code, number)
    res = []
    if nid not in g.nodes:
        return res
    for d, t, ev in g.out[nid]:
        res.append({"id": d, "direction": "out", "edge": {"type": t, "evidence": ev}, "node": _public(g, d)})
    for s, t, ev in g.inn[nid]:
        res.append({"id": s, "direction": "in", "edge": {"type": t, "evidence": ev}, "node": _public(g, s)})
    if types:
        res = [r for r in res if r["edge"]["type"] in types]
    return res


def siblings(code, number, include_admin=False):
    g = graph()
    nid = article_id(code, number)
    p = g.parent.get(nid)
    if not p:
        return []
    return [_public(g, c) for c in g.children[p] if c != nid and c in g.nodes and g.nodes[c]["type"] == "article"]


def precedents_for(code, number):
    g = graph()
    nid = article_id(code, number)
    out = []
    for d in g.art_docs.get(nid, ()):
        n = g.nodes[d]
        ev = next((e for _, t, e in g.out[d] if False), None)
        pages = next((e.get("pages") for x, t, e in g.out[d] if x == nid and t == "cites"), [])
        out.append({"id": d, "citation": n.get("citation"), "doc": n.get("doc"), "title": n.get("title"),
                    "source_type": n.get("source_type"), "jurisdiction": n.get("jurisdiction"),
                    "issue_date": n.get("issue_date"), "pages": pages})
    out.sort(key=lambda r: (r["source_type"] == "users_guide", r["doc"] or ""))
    return out


def _members(g, nid):
    if g.nodes[nid]["type"] == "article":
        return [nid]
    out = []
    for c in g.children.get(nid, ()):
        out.extend(_members(g, c))
    return out


def _fmt(b):
    t, v, frm, ev = b
    v = v() if callable(v) else v
    ev = ev() if callable(ev) else ev
    return {"type": t, "via": v, "from_article": frm.split("|", 1)[1], "evidence": ev}


def expand(articles, hops=1, via=("xref", "objective", "precedent"), limit=30,
           include_admin=False, exclude_docs=(), min_score=0.0):
    """articles: [(code, number)] or [{code, article}] or ids. Returns ranked candidates:
    [{code, article, title, pdf_page, edge:{type, via, from_article, evidence}, score, paths}]"""
    g = graph()
    seeds = []
    for a in articles:
        if isinstance(a, dict):
            a = (a.get("code", "NBC"), a.get("article") or a.get("number"))
        elif isinstance(a, str):
            a = tuple(a.split("|", 1)) if "|" in a else ("NBC", a)
        nid = article_id(*a)
        if nid in g.nodes:
            seeds.append(nid)
    seedset = set(seeds)
    excl = set(f"DOC|{d}" if not d.startswith("DOC|") else d for d in exclude_docs)
    cand = {}  # nid -> {score, paths, best:(w, edge)}

    def hit(nid, w, etype, viastr, frm, ev=None):
        if nid in seedset or nid not in g.nodes or g.nodes[nid]["type"] != "article":
            return
        if not include_admin and _admin(nid):
            return
        c = cand.setdefault(nid, {"score": 0.0, "paths": 0, "best": (0, None)})
        c["score"] += w
        c["paths"] += 1
        if w > c["best"][0]:
            c["best"] = (w, (etype, viastr, frm, ev))

    frontier = list(seeds)
    visited_x = set(seeds)
    for hop in range(max(1, hops)):
        decay = 0.5 ** hop
        nxt = []
        for s in frontier:
            if "xref" in via:
                for d, t, ev in g.out[s]:
                    if t != "xref":
                        continue
                    for m in _members(g, d):
                        w = (W_XREF_OUT if m == d else W_XREF_GROUP) * decay
                        hit(m, w, "xref", (lambda s=s, d=d, m=m: f"{s.split('|',1)[1]} text cites {d.split('|',1)[1]}"
                            if m == d else f"{s.split('|',1)[1]} cites {g.nodes[d]['type']} {g.nodes[d]['number']}"), s, ev)
                        if m not in visited_x and m == d:
                            visited_x.add(m); nxt.append(m)
                for sr, t, ev in g.inn[s]:
                    if t != "xref" or g.nodes[sr]["type"] != "article":
                        continue
                    hit(sr, W_XREF_IN * decay, "xref", (lambda sr=sr, s=s: f"{sr.split('|',1)[1]} text cites {s.split('|',1)[1]}"), s, ev)
                    if sr not in visited_x:
                        visited_x.add(sr); nxt.append(sr)
            if hop == 0:
                if "objective" in via:
                    pairs = g.art_pairs.get(s, {})
                    pair_hit = set()
                    for p, sents in pairs.items():
                        arts = g.pair_arts[p]
                        n = len(arts)
                        if n > HUB_MAX:
                            continue
                        w = W_PAIR / math.log2(2 + n)
                        for t in arts:
                            if t == s:
                                continue
                            pair_hit.add((s, t))
                            hit(t, w, "objective", (lambda p=p, n=n: f"shared {p[0].split(':')[1]}-{p[1].split(':')[1]} ({n} articles)"), s,
                                (lambda p=p: {"function": p[0].split(":")[1], "objective": p[1].split(":")[1]}))
                    for o, ev in g.art_obj.get(s, {}).items():
                        arts = g.obj_arts[o]
                        n = len(arts)
                        if n > HUB_MAX:
                            continue
                        w = W_OBJ / math.log2(2 + n)
                        for t in arts:
                            if t == s:
                                continue
                            hit(t, w, "objective", (lambda o=o, n=n: f"shared objective {o.split(':')[1]} ({n} articles)"), s,
                                (lambda o=o: {"objective": o.split(":")[1]}))
                if "precedent" in via:
                    for d in g.art_docs.get(s, ()):
                        if d in excl:
                            continue
                        arts = g.doc_arts[d]
                        if len(arts) > DOC_MAX:
                            continue
                        w = W_PREC / math.sqrt(len(arts))
                        for t in arts:
                            if t != s:
                                hit(t, w, "precedent", (lambda d=d: f"co-cited in {g.nodes[d].get('citation')}"), s, (lambda d=d: {"doc": d}))
        frontier = nxt
        if not frontier:
            break
    top = sorted(((nid, c) for nid, c in cand.items() if c["score"] >= min_score),
                 key=lambda x: (-x[1]["score"], x[0]))[:limit]
    res = []
    for nid, c in top:
        n = g.nodes[nid]
        res.append({"code": n["code"], "article": n["number"] if n["division"] == "B" else f"{n['division']}:{n['number']}",
                    "title": n["title"], "pdf_page": n["pdf_page"], "division": n["division"],
                    "edge": _fmt(c["best"][1]), "score": round(c["score"], 4), "paths": c["paths"]})
    return res


def why_path(a, b, max_depth=6, include_admin=True):
    """Shortest path between two articles ((code, number) tuples) over xref/cites/attributed_to/parent_of edges
    (hub objectives with > HUB_MAX articles are skipped). Returns [{from, to, edge:{type, evidence}}] or None."""
    g = graph()
    s, t = article_id(*a), article_id(*b)
    if s not in g.nodes or t not in g.nodes:
        return None
    prev = {s: None}
    dq = collections.deque([(s, 0)])
    while dq:
        u, dpt = dq.popleft()
        if u == t:
            break
        if dpt >= max_depth:
            continue
        nb = [(d, ty, ev, "out") for d, ty, ev in g.out[u]] + [(x, ty, ev, "in") for x, ty, ev in g.inn[u]]
        for v, ty, ev, dr in nb:
            if v in prev:
                continue
            if g.nodes[v]["type"] in ("objective", "function") and len(g.obj_arts.get(v, ())) > HUB_MAX and \
                    g.nodes[v]["type"] == "objective":
                continue
            if g.nodes[v]["type"] == "function":
                continue
            if g.nodes[v]["type"] in ("part", "section") :
                continue
            prev[v] = (u, ty, ev, dr)
            dq.append((v, dpt + 1))
    if t not in prev:
        return None
    path, cur = [], t
    while prev[cur]:
        u, ty, ev, dr = prev[cur]
        path.append({"from": u, "to": cur, "direction": dr, "edge": {"type": ty, "evidence": ev}})
        cur = u
    return list(reversed(path))


def stats():
    g = graph()
    nt = collections.Counter(n["type"] for n in g.nodes.values())
    return {"nodes": dict(nt), "edges": dict(g.edge_counts), "total_nodes": len(g.nodes),
            "total_edges": sum(g.edge_counts.values()), "meta": g.meta}
