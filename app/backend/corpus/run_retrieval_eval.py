"""Run the retrieval variants on the eval set. From app/backend:
    .venv/Scripts/python.exe -X utf8 -m corpus.run_retrieval_eval a      # BM25 variants + tuning on the 70% tune split
    .venv/Scripts/python.exe -X utf8 -m corpus.run_retrieval_eval b      # dense, LLM expansion, LLM rerank, classify path, 18 realistic
Results go to app/data/corpus/retrieval_results_{a,b}.json (RETRIEVAL_EVAL.md is written from them)."""
from __future__ import annotations
import itertools, json, sys, time

from . import DATA
from . import nbc_search as N
from . import retrieval_eval as R

S = R.load_set()
TUNE = [i for i in S["items"] if i["split"] == "tune"]
HELD = [i for i in S["items"] if i["split"] == "heldout"]


def truth(i):
    return {(t["code"], t["article"]) for t in i["truth"]}


def make_search(cfg, idx=None):
    cfg = {**N.load_cfg(), **cfg}
    idx = idx or N.build(cfg, write=False)

    def fn(q, k=10):
        return [(idx["docs"][i]["code"], idx["docs"][i]["key"]) for s, i in N.rank(q, idx, cfg, limit=k)]
    fn.idx, fn.cfg = idx, cfg
    return fn


def evaluate(fn, items):
    return R.metrics([(fn(i["query"]), truth(i)) for i in items])


def objective(m):
    return m["MRR"] + m["recall@5"] + m["hit@5"]


def phase_a():
    out = {"n_tune": len(TUNE), "n_heldout": len(HELD)}
    base_cfg = {**N.DEFAULT_CFG, "noise_filter": False}
    base = make_search(base_cfg)
    out["V0 current BM25 (no noise filter)"] = {"tune": evaluate(base, TUNE), "heldout": evaluate(base, HELD)}
    nf = make_search({**N.DEFAULT_CFG, "noise_filter": True}, base.idx)
    out["V1 + noise filter"] = {"tune": evaluate(nf, TUNE), "heldout": evaluate(nf, HELD)}
    # ---- tuning on TUNE only
    log, best, best_cfg = [], -1, dict(N.DEFAULT_CFG)
    for wt, ws, st in itertools.product((2.0, 4.0, 6.0, 8.0), (0.5, 1.5, 3.0), (True, False)):
        cfg = {**N.DEFAULT_CFG, "w_title": wt, "w_sect": ws, "stem": st}
        fn = make_search(cfg)
        m = evaluate(fn, TUNE)
        log.append({"w_title": wt, "w_sect": ws, "stem": st, **m})
        if objective(m) > best:
            best, best_cfg, best_idx = objective(m), cfg, fn.idx
    for k1, b, pb in itertools.product((0.9, 1.3, 1.8, 2.4), (0.3, 0.6, 0.8), (0.0, 1.0, 3.0)):
        cfg = {**best_cfg, "k1": k1, "b": b, "phrase_boost": pb}
        fn = make_search(cfg, best_idx)
        m = evaluate(fn, TUNE)
        log.append({"k1": k1, "b": b, "phrase_boost": pb, **m})
        if objective(m) > best:
            best = objective(m)
            best_cfg = cfg
    out["tuned_config"] = {k: best_cfg[k] for k in N.DEFAULT_CFG}
    tuned = make_search(best_cfg)
    out["V2 + tuned weights/stemming/phrase (tuned on 70%)"] = {"tune": evaluate(tuned, TUNE), "heldout": evaluate(tuned, HELD)}
    out["grid_size"] = len(log)
    out["grid_top5_by_tune"] = sorted(log, key=lambda r: -objective(r))[:5]
    # per-query failures (held-out, tuned)
    fails = []
    for i in HELD:
        r = tuned(i["query"], 10)
        t = truth(i)
        pos = [n for n, x in enumerate(r) if x in t]
        if not pos or pos[0] >= 5:
            fails.append({"doc": i["doc"].split("/")[-1], "title": i["title"], "query": i["query"][:160], "truth_n": len(t),
                          "first_hit_rank": (pos[0] + 1) if pos else None, "top3": [f"{c} {a}" for c, a in r[:3]],
                          "truth_sample": [f"{c} {a}" for c, a in sorted(t)[:4]]})
    out["heldout_failures_tuned"] = fails
    json.dump(out, open(DATA / "retrieval_results_a.json", "w", encoding="utf8"), indent=1)
    print(json.dumps({k: v for k, v in out.items() if k.startswith("V") or k == "tuned_config"}, indent=1))


if __name__ == "__main__":
    if sys.argv[1:] == ["a"]:
        phase_a()


# ---------------------------------------------------------------- phase b: dense, LLM expansion, LLM re-rank, classify path, realistic
def _label(code, art):
    rec = N.articles_of(code).get(art, {})
    return f"{code} {art} {rec.get('title', '')}".strip()


def phase_b():
    import numpy as np
    sys.path.insert(0, str(DATA.parents[1] / "backend"))
    import envload
    envload.load_env()
    import main
    import llm as llm_mod
    cfg = N.load_cfg()
    out = {"shipped_config": {k: cfg[k] for k in N.DEFAULT_CFG}, "llm": llm_mod.get_llm().name}
    idx = N.build(cfg, write=False)
    docs = idx["docs"]
    shipped = make_search(cfg, idx)
    base = make_search({**N.DEFAULT_CFG, "noise_filter": False})

    dense = None
    try:
        d = np.load(DATA / "dense_index.npz")
        from fastembed import TextEmbedding
        emb = TextEmbedding(str(d["model"]))
        vecs = d["vecs"]
        assert len(vecs) == len(docs)

        def dense_rank(q, n=60):
            qv = np.array(next(iter(emb.query_embed([q]))), dtype=np.float32)
            qv /= np.linalg.norm(qv) + 1e-9
            sims = vecs @ qv
            order = np.argsort(-sims)[:n]
            return [(float(sims[i]), int(i)) for i in order]

        def dense_only(q, k=10):
            return [(docs[i]["code"], docs[i]["key"]) for s, i in N._noise_filter(q, dense_rank(q), docs, cfg, False)[:k]]

        def hybrid(q, k=10):
            a = N.rank(q, idx, {**cfg, "noise_filter": False}, limit=60)
            b = dense_rank(q)
            sc = {}
            for lst in (a, b):
                for r, (s, i) in enumerate(lst):
                    sc[i] = sc.get(i, 0) + 1.0 / (60 + r)
            fused = sorted(((v, i) for i, v in sc.items()), reverse=True)
            return [(docs[i]["code"], docs[i]["key"]) for s, i in N._noise_filter(q, fused, docs, cfg, False)[:k]]
        dense = (dense_only, hybrid)
        out["dense"] = {"model": str(d["model"]), "installed": True}
    except Exception as e:
        out["dense"] = {"installed": False, "error": f"{type(e).__name__}: {e}"}

    cache_file = DATA / "retrieval_llm_cache.json"
    cache = json.load(open(cache_file, encoding="utf8")) if cache_file.exists() else {}

    def cached(key, fn):
        if key not in cache:
            cache[key] = fn()
            json.dump(cache, open(cache_file, "w", encoding="utf8"))
        return [tuple(x) for x in cache[key]]

    def expansion(q, k=10):
        return cached("exp|" + q, lambda: [(r["code"], r["article"]) for r in main._expanded_search(q, k)[0]])

    def exp_rerank(q, k=10):
        def go():
            res = main._expanded_search(q, 30)[0]
            res = N.llm_rerank(q, res)
            return [(r["code"], r["article"]) for r in res[:k]]
        return cached("rr|" + q, go)

    variants = {"V0 current BM25": base, "V1+V2 shipped (tuned + noise filter)": shipped}
    if dense:
        variants["V3 dense only (bge-small, local CPU)"] = dense[0]
        variants["V4 hybrid BM25+dense (RRF)"] = dense[1]
    variants["V5 shipped + LLM query expansion"] = expansion
    variants["V6 expansion + LLM re-rank (top 30)"] = exp_rerank
    out["heldout"], out["tune"] = {}, {}
    for name, fn in variants.items():
        t0 = time.time()
        out["heldout"][name] = {**evaluate(fn, HELD), "sec": round(time.time() - t0, 1)}
        print(name, out["heldout"][name], flush=True)
    # classify path (suggested_articles): description = query, k=6
    def suggested(q, k=6):
        a = {"project": {"description": q}, "variance": {}}
        return [(h["code"], h["article"]) for h in main._suggest(a, k)]
    out["heldout"]["classify suggested_articles (shipped, k=6)"] = evaluate(suggested, HELD)
    print("classify", out["heldout"]["classify suggested_articles (shipped, k=6)"], flush=True)

    # ---- 18 realistic
    rows = []
    for q, fam in R.REALISTIC:
        row = {"query": q, "family": fam}
        for name, fn in variants.items():
            top = fn(q, 5)
            rel = [x for x in top if R.in_family(x[0], x[1], fam)]
            row[name] = {"p@5": round(len(rel) / len(top), 2) if top else None, "n": len(top),
                         "irrelevant": [_label(c, a) for c, a in top if not R.in_family(c, a, fam)]}
        res = N.search_articles(q, 8)
        row["no_good_match"] = N.apply_quality(q, res)["no_good_match"]
        rows.append(row)
    out["realistic"] = rows
    scored = [r for r in rows if r["family"]]
    out["realistic_mean_p@5"] = {n: round(sum(r[n]["p@5"] or 0 for r in scored) / len(scored), 3) for n in variants}
    json.dump(out, open(DATA / "retrieval_results_b.json", "w", encoding="utf8"), indent=1)
    print(json.dumps(out["realistic_mean_p@5"], indent=1))


if __name__ == "__main__" and sys.argv[1:] == ["b"]:
    phase_b()
