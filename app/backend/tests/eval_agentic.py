"""Evaluation of agentic route-then-read search. Usage (from app/backend):
   python -X utf8 tests/eval_agentic.py a|b|md     a: 18 descriptions; b: held-out STANDATA comparison; md: write AGENTIC_EVAL.md
Results are cached in tests/eval_agentic_results.json (so 'md' needs no LLM)."""
import json, re, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import envload
envload.load_env()
import agentic
from corpus import nbc_search as N

RES = HERE / "eval_agentic_results.json"
OUT = HERE.parents[1] / "AGENTIC_EVAL.md"

# expected article FAMILIES, 'CODE:prefix' (prefix match on article number); verified to exist at run time
Q = [
 ("wheelchair platform lift instead of ramp", "We propose a wheelchair platform lift instead of the required ramp because the existing building has too little space for a ramp.", ["NBC:3.8.3.5", "NBC:9.8.5.", "NBC:3.5."]),
 ("5-storey, one exit stair", "A 5-storey apartment building with one exit stair instead of two exit stairs.", ["NBC:3.4.2."]),
 ("window limiter instead of guard", "A fixed window opening limiter is proposed instead of a guard at the window.", ["NBC:9.8.8.", "NBC:3.3.1.18", "NBC:3.4.6.6"]),
 ("basement egress window < 0.35 m2", "A bedroom egress window in a basement is smaller than 0.35 m2.", ["NBC:9.9.10."]),
 ("spray foam vs polyethylene vapour barrier", "Closed cell spray foam insulation is proposed instead of a polyethylene vapour barrier.", ["NBC:9.25.4.", "NBC:9.25.2.5", "NBC:5.5.1."]),
 ("wireless interconnected smoke alarms", "Wireless interconnected smoke alarms in a renovated house instead of hard-wired alarms.", ["NBC:9.10.19."]),
 ("sprinkler-protected glass in rated wall", "Sprinkler-protected glass in a fire-resistant wall between suites.", ["NBC:3.1.8.", "NBC:9.10.13.", "NBC:3.2.3."]),
 ("combustible cladding, 6-storey wood", "Combustible cladding on a six storey wood frame building.", ["NBC:3.1.5.", "NBC:3.1.6.9", "NBC:3.2.3."]),
 ("kitchen exhaust duct near property line", "A kitchen exhaust duct terminates closer to the property line than required.", ["NBC:9.32.3.13", "NBC:6.3.2.10", "NBC:6.9.2.3", "NBC:9.10.9.20"]),
 ("handrail height too low, interior stair", "Handrail height lower than required on an interior stair.", ["NBC:9.8.7.", "NBC:3.4.6.5"]),
 ("zero lot line wall, unprotected openings", "Zero lot line wall with unprotected openings.", ["NBC:9.10.14.", "NBC:9.10.15.", "NBC:3.2.3."]),
 ("prefab roof trusses, no sealed drawing", "Prefabricated roof trusses without a sealed engineer's drawing.", ["NBC:9.23.14.11", "NBC:9.23.5.5", "NBC:4.3.1."]),
 ("EV charging stations in a parkade (expect none)", "EV charging stations in a parkade.", []),
 ("FD connection too far from street", "The fire department connection is farther from the street than allowed.", ["NBC:3.2.5.15"]),
 ("backflow preventer in restaurant", "A backflow preventer in a restaurant.", ["NPC:2.6.2.", "NPC:2.2.10.10"]),
 ("lighting power density above limit, office", "Lighting power density above the limit in an open plan office.", ["NECB:4.2.1.", "NECB:4.3."]),
 ("8-storey mass timber, exposed ceilings", "Eight storey mass timber building with exposed ceilings.", ["NBC:3.1.6.", "NBC:3.1.13.12"]),
 ("secondary suites in row house, reduced separation", "Secondary suites in a row house with reduced fire separation.", ["NBC:9.10.9.", "NBC:9.10.14.", "NBC:9.10.15.", "NBC:9.10.19."]),
]


def in_family(code, art, fam):
    return any(f"{code}:{art}".startswith(p) for p in fam)


def fam_exists(fam):
    bad = []
    for p in fam:
        c, pre = p.split(":")
        if not any(k.startswith(pre) for k in agentic._arts(c)):
            bad.append(p)
    return bad


def load():
    return json.load(open(RES, encoding="utf8")) if RES.exists() else {}


def save(d):
    json.dump(d, open(RES, "w", encoding="utf8"), indent=1, ensure_ascii=False)


def run_a():
    d = load()
    for name, q, fam in Q:
        assert not fam_exists(fam), (name, fam_exists(fam))

    def one(args):
        (name, q, fam), cheap = args
        r = agentic.deep_search(q, cheap=cheap, use_cache=False)
        return name, cheap, r
    jobs = [(x, c) for x in Q for c in (False, True)]
    with ThreadPoolExecutor(3) as ex:
        for name, cheap, r in ex.map(one, jobs):
            d.setdefault("a", {}).setdefault(name, {})["cheap" if cheap else "normal"] = r
    save(d)


def _truth_docs(n=30):
    docs = {}
    for l in open(agentic.DATA / "precedents_chunks.jsonl", encoding="utf8"):
        c = json.loads(l)
        if c["source_type"] not in ("standata_variance", "standata_interpretation", "standata_bulletin"):
            continue
        d = docs.setdefault(c["doc"], {"doc": c["doc"], "title": c["title"], "texts": [], "cited": []})
        d["texts"].append(c["text"])
        for a in c["articles_cited"]:
            if a not in d["cited"] and a in agentic._arts("NBC"):
                d["cited"].append(a)
    ok = [d for d in sorted(docs.values(), key=lambda x: x["doc"]) if d["cited"]]
    step = max(1, len(ok) // n)
    return ok[::step][:n]


ART = re.compile(r"\b\d{1,2}\.\d{1,2}(?:\.\d{1,2}(?:\.\d{1,3})?)?\b(?:\.\(\d+\))?|\bArticles?\b|\bSentences?\b")


def doc_query(d):
    t = " ".join(d["texts"][:3])
    m = re.search(r"(Purpose|Discussion|Background|Issue)\b", t)
    t = t[m.start():] if m else t
    q = d["title"] + ". " + t[:700]
    q = ART.sub(" ", q)
    return " ".join(q.split())


def metrics(ranked, truth):
    ranked = ranked[:10]
    hit1 = 1.0 if ranked and ranked[0] in truth else 0.0
    rec5 = len(set(ranked[:5]) & set(truth)) / len(truth)
    mrr = next((1 / (i + 1) for i, a in enumerate(ranked) if a in truth), 0.0)
    return hit1, rec5, mrr


def _meta(r):
    m = {k: r[k] for k in ("llm_calls", "seconds", "fallback")}
    m.update(pt=r["cost"]["prompt_tokens"], ct=r["cost"]["completion_tokens"], usd=r["cost"]["est_cost_usd"])
    return m


def run_b():
    d = load()
    docs = _truth_docs(30)

    def one(doc):
        q = doc_query(doc)
        bm = [r["article"] for r in N.search_articles(q, k=10, codes=["NBC"])]
        r = agentic.deep_search(q, codes=None, use_cache=False, with_precedents=False)
        rc = agentic.deep_search(q, codes=None, cheap=True, use_cache=False, with_precedents=False)
        pick = lambda r: [x["article"] for x in r["results"] if x["code"] == "NBC"]
        return {"doc": doc["doc"], "title": doc["title"], "truth": doc["cited"], "query": q,
                "bm25": bm, "deep": pick(r), "cheap": pick(rc), "deep_meta": _meta(r), "cheap_meta": _meta(rc)}
    with ThreadPoolExecutor(3) as ex:
        d["b"] = list(ex.map(one, docs))
    save(d)


def run_md():
    d = load()
    L = ["# Agentic route-then-read evaluation", "",
         "Generated by `app/backend/tests/eval_agentic.py` from real runs (Azure OpenAI gpt-4o, temperature 0). "
         "Retrieval aid only: nothing here says a design is safe or equivalent. Dollar figures are estimates at "
         f"${agentic.PRICE_PER_M_IN}/1M input and ${agentic.PRICE_PER_M_OUT}/1M output tokens (estimate, check your Azure price).", ""]
    A = d.get("a", {})
    if A:
        L += ["## (a) 18 applicant descriptions", "",
              "Expected families are hand-labelled article prefixes, each verified to exist in the code JSON. P@5 = share of the first 5 returned "
              "articles inside the family (cross-referenced items included). 'family hit' = any returned article in the family. "
              "Cheap mode = BM25 routing, LLM only for the read/judge step.", "",
              "| # | description | mode | route (sections) | keepers | P@5 | family hit | calls | prompt tok | compl tok | est USD | s |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
        tot = {"normal": [0] * 7, "cheap": [0] * 7}
        for i, (name, q, fam) in enumerate(Q, 1):
            for mode in ("normal", "cheap"):
                r = A.get(name, {}).get(mode)
                if not r:
                    continue
                res = r["results"]
                top = res[:5]
                p5 = (sum(in_family(x["code"], x["article"], fam) for x in top) / len(top)) if top and fam else None
                hit = any(in_family(x["code"], x["article"], fam) for x in res) if fam else None
                route = ", ".join(f"{x['code']} {x['section']}" for x in r["route"])
                keepers = ", ".join(x["article"] for x in res) or "none"
                c = r["cost"]
                lab = ("n/a (expect none; returned %d)" % len(res)) if not fam else ("yes" if hit else "NO")
                L.append(f"| {i} | {name} | {mode}{' (fallback)' if r['fallback'] else ''} | {route} | {keepers} | {'' if p5 is None else '%.2f' % p5} | {lab} | {r['llm_calls']} | {c['prompt_tokens']} | {c['completion_tokens']} | {c['est_cost_usd']:.4f} | {r['seconds']} |")
                t = tot[mode]
                if fam:
                    t[0] += 1
                    t[1] += bool(hit)
                    t[2] += p5 or 0
                t[3] += r["llm_calls"]
                t[4] += c["est_cost_usd"]
                t[5] += r["seconds"]
                t[6] += 1
        L += ["", "### Summary of (a)", "", "| mode | family hit (17 with a family) | mean P@5 | mean calls | mean est USD / search | mean s |", "|---|---|---|---|---|---|"]
        for mode, t in tot.items():
            if t[6]:
                L.append(f"| {mode} | {t[1]}/{t[0]} | {t[2]/max(t[0],1):.2f} | {t[3]/t[6]:.1f} | {t[4]/t[6]:.4f} | {t[5]/t[6]:.1f} |")
        ev = [A[n]["normal"] for n, _, f in Q if not f and "normal" in A.get(n, {})]
        if ev:
            L += ["", f"EV charging (expected: nothing relevant): normal mode returned {len(ev[0]['results'])} item(s): "
                  + (", ".join(x["article"] for x in ev[0]["results"]) or "none") + f". Message: {ev[0].get('message')}"]
    B = d.get("b")
    if B:
        L += ["", "## (b) Held-out comparison on %d real STANDATA documents" % len(B), "",
              "Query = document title + Purpose/Discussion text (first 700 chars) with article numbers stripped. Truth = the document's verified `articles_cited` (NBC). "
              "Documents were chosen deterministically (every k-th of the sorted STANDATA variance/interpretation/bulletin documents that cite at least one NBC article); "
              "nothing was tuned on them. BM25 = `corpus.nbc_search.search_articles(codes=['NBC'])` top 10. Deep = NBC results in output order, top 10 "
              "(it returns at most 6 read + up to 4 cross-referenced articles, so its list is short by design).", "",
              "| method | hit@1 | recall@5 | MRR | mean s | mean LLM calls | mean prompt tok | mean est USD |", "|---|---|---|---|---|---|---|---|"]
        n = len(B)

        def agg(key):
            ms = [metrics(x[key], x["truth"]) for x in B]
            return [sum(m[i] for m in ms) / n for i in range(3)]
        for key, lab, meta in (("bm25", "BM25 keyword", None), ("deep", "Deep (LLM route+read)", "deep_meta"), ("cheap", "Deep cheap (BM25 route)", "cheap_meta")):
            h, r5, mrr = agg(key)
            if meta:
                s = sum(x[meta]["seconds"] for x in B) / n
                c = sum(x[meta]["llm_calls"] for x in B) / n
                pt = sum(x[meta]["pt"] for x in B) / n
                usd = sum(x[meta]["usd"] for x in B) / n
                L.append(f"| {lab} | {h:.2f} | {r5:.2f} | {mrr:.2f} | {s:.1f} | {c:.1f} | {pt:.0f} | {usd:.4f} |")
            else:
                L.append(f"| {lab} | {h:.2f} | {r5:.2f} | {mrr:.2f} | <0.1 | 0 | 0 | 0 |")
        L += ["", "Fallbacks (deep): %d of %d." % (sum(x["deep_meta"]["fallback"] for x in B), n), "",
              "### Per document", "", "| document | truth | BM25 top5 | deep |", "|---|---|---|---|"]
        for x in B:
            L.append(f"| {Path(x['doc']).name[:50]} | {', '.join(x['truth'][:6])} | {', '.join(x['bm25'][:5])} | {', '.join(x['deep'][:8]) or 'none'} |")
    L += ["", "## (c) Safety test (fake LLM)", "",
          "`tests/test_agentic.py::test_safety_invented_items_dropped` uses a fake LLM that returns an out-of-menu area (NBC:99.99), an invented article "
          "number (9.8.99.99) and a fabricated quote for a real article (9.8.5.4). Result: the area is dropped from the route, the invented article is "
          "dropped, the fabricated quote is dropped (zero results). `test_real_quote_survives_and_is_substring` shows a genuine quote is kept. "
          "Both pass.", "",
          "## Method notes and limits", "",
          "- Quotes are verified as substrings of the article text after whitespace normalisation; a quote that differs only in punctuation/case is "
          "re-anchored to the real span of the article text (still a substring), otherwise dropped.",
          "- Cross-referenced articles (parsed from 'Article X' text, or from kg.py when present) are added without an LLM call; their quote is the article's "
          "first sentence and they are labelled not separately judged.",
          "- Honesty note: in the first full run 2 of 36 (a) searches and 3 of 30 (b) searches fell back because the Azure client's one-time cold start (~45 s on this Windows box) was counted against the 45 s budget; agentic.py now excludes client start-up from search time and those searches were re-run once (no other searches were re-run or selected).",
          "- Read budget is 6 full articles per search (the judge sees at most 1800 chars of each); large articles may be judged on a truncated view.",
          "- The LLM routing menu has section titles only; a vague description can route to the wrong area.",
          ]
    OUT.write_text("\n".join(L) + "\n", encoding="utf8")
    print("wrote", OUT)


if __name__ == "__main__":
    {"a": run_a, "b": run_b, "md": run_md}[sys.argv[1]]()
