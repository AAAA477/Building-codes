"""KG evaluation: sanity neighbours, held-out recall@10, latency. Run with the venv python (-X utf8)."""
import sys, json, random, time, statistics, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import kg

g = kg.graph()
SANITY = [("NBC", "3.4.2.1"), ("NBC", "9.9.10.1"), ("NBC", "9.8.8.1"), ("NBC", "3.2.5.15"), ("NFC", "6.2.1.1"),
          ("NPC", "2.6.2.12"), ("NECB", "4.2.1.1"), ("NBC", "3.3.1.5"), ("NBC", "9.10.14.4"), ("NBC", "3.1.17.1")]
print("## SANITY")
for code, a in SANITY:
    nid = kg.article_id(code, a)
    if nid not in g.nodes:
        print(code, a, "NOT IN GRAPH"); continue
    print(f"\n### {code} {a} {g.nodes[nid]['title']}")
    for typ in ("xref", "objective", "precedent"):
        r = kg.expand([(code, a)], via=(typ,), limit=5)
        print(f"  [{typ}]")
        for x in r:
            print(f"    {x['code']} {x['article']} {x['title']} | {x['edge']['via'][:90]} | {x['score']}")
import os
if os.environ.get("HUB_MAX"): kg.HUB_MAX = int(os.environ["HUB_MAX"])
if os.environ.get("DOC_MAX"): kg.DOC_MAX = int(os.environ["DOC_MAX"])
# held-out
print("\n## HELD-OUT")
docs = {d: sorted(a.split("|", 1)[1] for a in arts) for d, arts in g.doc_arts.items()}
docs = {d: a for d, a in docs.items() if len(a) >= 2 and not g.nodes[d]["doc"].startswith("standata:")}
rng = random.Random(7)
bytype = collections.defaultdict(list)
for d in sorted(docs):
    bytype[g.nodes[d]["source_type"]].append(d)
print({k: len(v) for k, v in bytype.items()})
picked = []
types = sorted(bytype)
while len(picked) < 30:
    for t in types:
        pool = [d for d in bytype[t] if d not in picked]
        if pool and len(picked) < 30:
            picked.append(rng.choice(pool))
all_b = [n for n, v in g.nodes.items() if v["type"] == "article" and v["division"] == "B" and v["code"] == "NBC"]
K = 10
hits = collections.Counter(); rr = collections.defaultdict(list)
def trial(d, mode):
    arts = docs[d]
    hid = rng.choice(arts)
    rest = [a for a in arts if a != hid]
    seeds = [("NBC", a) for a in rest]
    hidid = f"NBC|{hid}"
    if mode == "kg_all":
        r = kg.expand(seeds, limit=K, exclude_docs=[d])
    elif mode == "kg_dedup":
        # also hide near-duplicate documents (same title or >=50% Jaccard overlap of cited articles, e.g. revisions)
        A = set(arts)
        ex = [d]
        for d2, a2 in docs.items():
            if d2 != d and (g.nodes[d2]["title"] == g.nodes[d]["title"] or len(A & set(a2)) / len(A | set(a2)) >= 0.5):
                ex.append(d2)
        r = kg.expand(seeds, limit=K, exclude_docs=ex)
    elif mode == "kg_noprec":
        r = kg.expand(seeds, limit=K, via=("xref", "objective"))
    elif mode == "kg_xref_obj_prec_other":
        r = kg.expand(seeds, limit=K, exclude_docs=[d])
    elif mode == "random":
        r = [{"code": "NBC", "article": x.split("|")[1]} for x in rng.sample(all_b, K)]
    elif mode == "siblings":
        sib = []
        for a in rest:
            sib += [s["number"] for s in kg.siblings("NBC", a)]
        sib = list(dict.fromkeys(sib))
        rng.shuffle(sib)
        r = [{"code": "NBC", "article": s} for s in sib[:K]]
    return any(x["article"] == hid for x in r)
res = {}
for mode in ("kg_all", "kg_dedup", "kg_noprec", "random", "siblings"):
    ok = 0
    for d in picked:
        ok += trial(d, mode)
    res[mode] = ok / len(picked)
print("recall@10 (30 docs, 1 trial each):", res)
# larger: all 99 eligible docs, 3 trials each, averaged
big = {}
for mode in ("kg_all", "kg_dedup", "kg_noprec", "random", "siblings"):
    ok = n = 0
    for d in sorted(docs):
        for _ in range(3):
            ok += trial(d, mode); n += 1
    big[mode] = round(ok / n, 3)
print(f"recall@10 all {len(docs)} eligible docs x3 trials:", big)
# by source type for kg_all
for t in types:
    ok = n = 0
    for d in bytype[t]:
        for _ in range(3):
            ok += trial(d, "kg_all"); n += 1
    print("  kg_all", t, len(bytype[t]), "docs", round(ok / max(n, 1), 3))
print("picked:", [g.nodes[d]["doc"] for d in picked])
# latency
print("\n## LATENCY")
ts = []
t0 = time.perf_counter(); kg.graph(); 
lat = []
for d in sorted(docs):
    seeds = [("NBC", a) for a in docs[d][:6]]
    t = time.perf_counter(); kg.expand(seeds, limit=30); lat.append((time.perf_counter() - t) * 1000)
lat.sort()
print(f"expand over {len(lat)} real seed sets: median {statistics.median(lat):.1f} ms, p95 {lat[int(len(lat)*.95)]:.1f} ms, max {lat[-1]:.1f} ms")
