"""Closed-set citation verifier and deterministic attribution lookup.

All data comes from app/data/corpus/*.json (built by extract_nbc.py / build_intents.py).
Division B articles are keyed by bare number ("3.4.2.1"). Nothing is generated.

CLI (from app/backend):  python -m corpus.verifier 3.4.2.1
"""
import json
import re
import sys
from functools import lru_cache

from . import DATA, EDITION

SOURCE_DOC = "NBC_2023AE_2nd_printing.pdf"
RE_CITE = re.compile(r"(?<![\d.])(\d{1,2}\.\d{1,2}\.\d{1,2}\.\d{1,3})(?:\.?\s*\((\d+)\))?(?![\d])")


def _load(name, default):
    p = DATA / name
    if not p.exists():
        return default
    with open(p, encoding="utf8") as fh:
        return json.load(fh)


@lru_cache(maxsize=1)
def _articles():
    return _load("nbc_articles.json", {})


@lru_cache(maxsize=1)
def _objectives():
    return _load("objectives.json", {})


@lru_cache(maxsize=1)
def _functions():
    return _load("functions.json", {})


@lru_cache(maxsize=1)
def _intents():
    return _load("intents.json", {})


def _norm(num):
    num = (num or "").strip().rstrip(".")
    m = re.match(r"^(\d+\.\d+\.\d+\.\d+)(?:\.?\((\d+)\))?$", num)
    if not m:
        return num, None
    return m.group(1), (int(m.group(2)) if m.group(2) else None)


def article_exists(num):
    return _norm(num)[0] in _articles()


def get_article(num):
    return _articles().get(_norm(num)[0])


def _split(codes):
    objs, funcs = [], []
    for c in codes:
        f, _, o = c.partition("-")
        if f and f not in funcs:
            funcs.append(f)
        if o and o not in objs:
            objs.append(o)
    return objs, funcs


def lookup_attribution(num):
    """Deterministic lookup. Sentence form '3.4.2.1.(2)' is accepted.

    root_used: None when the article's own (or the cited sentence's) attributions were used;
    otherwise the article number whose statements were borrowed (root-article rule).
    """
    art_no, sent_no = _norm(num)
    a = _articles().get(art_no)
    res = {"article": art_no, "sentence": sent_no, "edition": EDITION, "objectives": [], "functions": [],
           "intent": None, "root_used": None, "source": None, "verified": False, "note": None}
    if a is None:
        res["note"] = "article not found in indexed NBC(AE) 2023 text"
        return res
    res["source"] = {"doc": SOURCE_DOC, "page": a["pdf_page"]}
    codes = a["attributions"]
    note = None
    if sent_no is not None:
        s = next((x for x in a["sentences"] if x["number"] == sent_no), None)
        if s is None:
            note = f"sentence ({sent_no}) not found in parsed article; article-level attributions used"
            res["root_used"] = art_no
        elif s["attributions"]:
            codes = s["attributions"]
        else:
            res["root_used"] = art_no
            note = "sentence has no attribution of its own; root article's attributions applied"
    if not codes:
        note = "no attributed objectives/functions found for this article in the Part's attribution table (unresolved)"
    objs, funcs = _split(codes)
    O, F = _objectives(), _functions()
    res["objectives"] = [{"code": c, "text": O[c]["text"] if c in O else None,
                          "page": O[c]["pdf_page"] if c in O else None} for c in objs]
    res["functions"] = [{"code": c, "text": F[c]["text"] if c in F else None,
                         "page": F[c]["pdf_page"] if c in F else None} for c in funcs]
    res["attribution_codes"] = codes
    it = _intents().get(art_no)
    if it and it.get("status") != "unresolved":
        res["intent"] = it
    elif it:
        res["intent"] = {"status": "unresolved", "intent_edition": it.get("intent_edition"), "note": it.get("note")}
    res["note"] = note
    res["verified"] = bool(codes) and all(
        x["text"] for x in res["objectives"] + res["functions"])
    return res


def find_citations(text):
    """Return article numbers (unique, in order) that look like NBC article citations."""
    out = []
    for m in RE_CITE.finditer(text or ""):
        if m.group(1) not in out:
            out.append(m.group(1))
    return out


def verify_text(text):
    cited, unverified = [], []
    for n in find_citations(text):
        (cited if article_exists(n) else unverified).append(n)
    return {"cited": cited, "unverified": unverified, "edition": EDITION}


def main(argv):
    if not argv:
        print("usage: python -m corpus.verifier 3.4.2.1")
        return 2
    for n in argv:
        a = get_article(n)
        print(f"== {n}: exists={article_exists(n)}")
        if a:
            print(f"   title: {a['title']}  (Division {a['division']}, pdf page {a['pdf_page']})")
            for s in a["sentences"][:2]:
                print(f"   ({s['number']}) {s['text'][:160]}")
        print(json.dumps(lookup_attribution(n), indent=1, ensure_ascii=False)[:3500])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
