"""Retrieval evaluation against ground truth taken from real documents.

Eval set: every STANDATA variance/interpretation/bulletin, Edmonton policy and Calgary advisory that cites at least
one verified NBC article. Query = the document's title + its Purpose/Application/Discussion sentences with article
numbers and code references stripped. Truth = the document's verified cited articles. Split by title group
(so revisions stay together) 70/30 with a fixed seed; only the held-out 30% is reported.

Run from app/backend:  .venv/Scripts/python.exe -X utf8 -m corpus.retrieval_eval build
"""
from __future__ import annotations
import json, random, re, sys
from collections import defaultdict

from . import DATA

SET_FILE = DATA / "retrieval_eval_set.json"
SEED = 20261029
TYPES = {"standata_variance", "standata_interpretation", "standata_bulletin", "edmonton_policy", "calgary_advisory"}

HEAD = re.compile(r"\b(Purpose|Application|Discussion|Background|Summary|Scope|Problem|Issue|Rationale)\b\s*[:.]?\s+", re.I)
JUNK = re.compile(r"©|alberta\.ca|Government of Alberta|Municipal Affairs|Published:|Page \d+ of \d+|Development Services|"
                  r"Edmonton Tower|Safety Codes, Permits|www\.|@", re.I)
ART = re.compile(r"\b\d{1,2}\.\d{1,2}(?:\.\d{1,2}){0,2}\.?(?:\(\d+\))?(?:\([a-z]\))?")


def strip_refs(t: str) -> str:
    t = re.sub(r"NBC\s*\(?\s*AE\s*\)?(?:\s*20\d\d)?|\bNBC\b|\bNFC\b|\bNPC\b|\bNECB\b|\bABC\b\s*20\d\d", " ", t)
    t = re.sub(r"\b(Division\s+[ABC]|Code References?|Sentences?|Articles?|Clauses?|Subsections?|Sections?|Items?)\b\s*(?=[\d(])", " ", t, flags=re.I)
    t = re.sub(r"\b(Division\s+[ABC])\b", " ", t, flags=re.I)
    t = ART.sub(" ", t)
    t = re.sub(r"\(\s*\)|\[\s*\]", " ", t)
    t = re.sub(r"\s+", " ", t).strip(" .,;:-")
    return t


def purpose_text(chunks: list) -> str:
    text = " ".join(c["text"] for c in sorted(chunks, key=lambda c: (c["page"], c["id"])) if c["page"] <= 2)
    m = HEAD.search(text)
    seg = text[m.end():] if m else text
    sents = re.split(r"(?<=[.!?])\s+", seg)
    out, n = [], 0
    for s in sents:
        if JUNK.search(s) or len(s.split()) < 8:
            continue
        out.append(s)
        n += len(s)
        if len(out) >= 2 or n > 350:
            break
    return " ".join(out)[:420]


def build_set() -> dict:
    from . import verifier
    by = defaultdict(list)
    for line in open(DATA / "precedents_chunks.jsonl", encoding="utf8"):
        c = json.loads(line)
        if c["source_type"] in TYPES:
            by[c["doc"]].append(c)
    items = []
    for doc, cs in sorted(by.items()):
        truth = sorted({a for c in cs for a in c["articles_cited"] if verifier.article_exists(a)})
        if not truth:
            continue
        title = cs[0]["title"]
        q = strip_refs(f"{title}. {purpose_text(cs)}")
        if len(q.split()) < 4:
            continue
        key = re.sub(r"[^a-z]+", " ", title.lower()).strip()
        items.append({"doc": doc, "source_type": cs[0]["source_type"], "title": title, "group": key, "query": q,
                      "truth": [{"code": "NBC", "article": a} for a in truth]})
    groups = sorted({i["group"] for i in items})
    rnd = random.Random(SEED)
    rnd.shuffle(groups)
    cut = int(round(0.7 * len(groups)))
    tune = set(groups[:cut])
    for i in items:
        i["split"] = "tune" if i["group"] in tune else "heldout"
    out = {"seed": SEED, "split_unit": "title group (revisions stay together)", "n": len(items),
           "n_tune": sum(i["split"] == "tune" for i in items), "n_heldout": sum(i["split"] == "heldout" for i in items),
           "items": items}
    json.dump(out, open(SET_FILE, "w", encoding="utf8"), indent=1, ensure_ascii=False)
    return out


def load_set() -> dict:
    return json.load(open(SET_FILE, encoding="utf8"))


# ---------------------------------------------------------------- 18 realistic applicant descriptions
# Expected article FAMILIES: (code, key prefix). Written from the NBC/NFC/NPC/NECB section titles (verified to exist by
# test_retrieval_families), not from search output. None = the corpus has no article, expect no_good_match.
REALISTIC = [
    ("wheelchair platform lift instead of a ramp", [("NBC", "3.8.")]),
    ("single exit stair in a six storey residential building", [("NBC", "3.4.2."), ("NBC", "3.4.4."), ("NBC", "9.9.8.")]),
    ("window guard height where the window sill is low", [("NBC", "9.8.8."), ("NBC", "3.3.4."), ("NBC", "3.3.2.9"), ("NBC", "3.4.6.6")]),
    ("bedroom egress window size in a basement", [("NBC", "9.9.10.")]),
    ("spray foam insulation instead of a polyethylene vapour barrier", [("NBC", "9.25.")]),
    ("wireless interconnected smoke alarms", [("NBC", "9.10.19."), ("NBC", "3.2.4.20")]),
    ("sprinkler protected glass in a fire rated wall", [("NBC", "3.1.7."), ("NBC", "9.10.3."), ("NBC", "9.10.15."), ("NBC", "3.2.3.")]),
    ("combustible cladding on a building taller than three storeys", [("NBC", "3.1.5."), ("NBC", "3.2.3."), ("NBC", "9.10.14."), ("NBC", "9.10.15.")]),
    ("kitchen exhaust duct termination near a property line", [("NBC", "9.32.3."), ("NBC", "6.3.2."), ("NFC", "2.6.")]),
    ("handrail height on a stair", [("NBC", "9.8.7."), ("NBC", "3.4.6.")]),
    ("zero lot line side wall of a house", [("NBC", "9.10.14."), ("NBC", "9.10.15."), ("NBC", "3.2.3."), ("NBC", "9.10.9.")]),
    ("roof trusses without sealed engineered drawings", [("NBC", "4.3.1."), ("NBC", "9.23.13."), ("NBC", "9.4.1.")]),
    ("electric vehicle charging station in a parkade", None),
    ("fire department connection location for a sprinkler system", [("NBC", "3.2.5."), ("NFC", "2.5.")]),
    ("backflow preventer in a restaurant", [("NPC", "2.6.2."), ("NPC", "2.2.10.")]),
    ("lighting power density in an office", [("NECB", "4.")]),
    ("eight storey mass timber building", [("NBC", "3.2.2."), ("NBC", "3.1.4."), ("NBC", "3.1.5.")]),
    ("secondary suites in a row house", [("NBC", "9.10.9."), ("NBC", "9.10.8."), ("NBC", "9.9.8."), ("NBC", "9.10.19.")]),
]


def in_family(code: str, article: str, fam) -> bool:
    return bool(fam) and any(code == c and article.startswith(p) for c, p in fam)


# ---------------------------------------------------------------- metrics
def metrics(runs, k_caps=(1, 5, 10)):
    """runs: [(ranked [(code, article)], truth set of (code, article))]. recall@k = |truth in top-k| / min(|truth|, k)."""
    n = len(runs) or 1
    hit1 = hit5 = hit10 = rec5 = rec10 = mrr = 0.0
    for ranked, truth in runs:
        pos = [i for i, r in enumerate(ranked) if r in truth]
        if pos and pos[0] == 0:
            hit1 += 1
        if pos and pos[0] < 5:
            hit5 += 1
        if pos and pos[0] < 10:
            hit10 += 1
        top5, top10 = set(ranked[:5]), set(ranked[:10])
        rec5 += len(top5 & truth) / min(len(truth), 5)
        rec10 += len(top10 & truth) / min(len(truth), 10)
        mrr += 1 / (pos[0] + 1) if pos else 0.0
    return {"n": len(runs), "hit@1": round(hit1 / n, 3), "hit@5": round(hit5 / n, 3), "hit@10": round(hit10 / n, 3),
            "recall@5": round(rec5 / n, 3), "recall@10": round(rec10 / n, 3), "MRR": round(mrr / n, 3)}


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "build":
        s = build_set()
        print({k: s[k] for k in ("n", "n_tune", "n_heldout")})
        for i in s["items"][:6]:
            print(i["split"], i["source_type"], "|", i["query"][:200], "|", [t["article"] for t in i["truth"]][:6])
