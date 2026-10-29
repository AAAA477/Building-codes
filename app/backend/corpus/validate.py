"""Validate nbc_articles.json against raw PDF page text (independent get_text() path).

For every article: the first 50 and last 40 characters of the parsed text must appear (whitespace-normalised)
in the raw text of the article's PDF pages. Also prints spot-check detail for named articles and an
attribution cross-check (every parsed attribution code must appear in the raw text of its table page).

Run (from app/backend):  python -m corpus.validate
"""
import json
import random
import re
import sys

import pymupdf

from . import DATA, FILES

SPOT = ["3.4.2.1", "3.3.1.3", "3.3.1.5", "3.3.1.6", "3.2.5.12", "3.2.5.7", "3.2.5.1", "3.2.4.1", "3.2.4.20",
        "3.2.2.51", "3.2.2.47", "3.4.4.1", "3.4.2.4", "9.9.8.2", "9.9.4.2", "9.9.9.1", "9.10.19.1", "3.4.2.5"]


def norm(s):
    s = s.replace("­", "")
    return re.sub(r"\s+", "", s)


def main():
    arts = json.load(open(DATA / "nbc_articles.json", encoding="utf8"))
    doc = pymupdf.open(str(FILES / "codes" / "NBC_2023AE_2nd_printing.pdf"))
    cache = {}

    def raw(p):
        if p not in cache:
            cache[p] = norm(doc[p - 1].get_text())
        return cache[p]

    def check(a):
        if not a["sentences"]:
            return None  # nothing to check (reserved / table-only)
        pages = "".join(raw(p) for p in a["pdf_pages"])
        t_first = norm(a["sentences"][0]["text"])[:50]
        t_last = norm(a["sentences"][-1]["text"])[-40:]
        # sentences are rebuilt from lines; allow clause labels to differ by comparing without them
        return (t_first in pages, t_last in pages)

    total = ok = empty = 0
    fails = []
    for k, a in arts.items():
        r = check(a)
        if r is None:
            empty += 1
            continue
        total += 1
        if all(r):
            ok += 1
        else:
            fails.append((k, a["pdf_page"], r))
    print(f"articles parsed: {len(arts)}; with sentences: {total}; no sentences (reserved/table-only): {empty}")
    print(f"text check pass: {ok}/{total}; fail: {len(fails)} ({100*len(fails)/max(1,total):.2f}%)")
    print("first 25 failures:", fails[:25])

    print("\nSPOT CHECKS (explicit articles)")
    spot_ok = 0
    for k in SPOT:
        a = arts.get(k)
        if not a:
            print(f"  {k}: MISSING from parse")
            continue
        r = check(a)
        n_attr = sum(1 for s in a["sentences"] if s["attributions"])
        # attribution cross-check: all codes appear on some table page
        miss = []
        pages_txt = {}
        for s in a["sentences"]:
            for d in s["attribution_detail"]:
                pg = d["table_pdf_page"]
                pages_txt.setdefault(pg, norm(doc[pg - 1].get_text()))
                if norm(d["raw"]) not in pages_txt[pg]:
                    miss.append(d["raw"])
        good = r is not None and all(r) and not miss
        spot_ok += good
        print(f"  {k:10s} p{a['pdf_page']:<5d} sentences={len(a['sentences'])} attributed_sentences={n_attr} "
              f"text_match={r} attr_missing_in_raw={miss} -> {'PASS' if good else 'CHECK'}")
    print(f"spot checks passing: {spot_ok}/{len(SPOT)}")

    random.seed(7)
    sample = random.sample([k for k, a in arts.items() if a["sentences"]], 40)
    bad = [k for k in sample if not all(check(arts[k]))]
    print(f"\nrandom sample of 40 articles: fails={len(bad)} {bad}")

    # attribution coverage
    all_sent = [(k, s) for k, a in arts.items() if a["division"] == "B" for s in a["sentences"]]
    att = sum(1 for _, s in all_sent if s["attributions"])
    print(f"Division B sentences: {len(all_sent)}; with parsed attribution: {att}")
    rep = json.load(open(DATA / "extract_report.json", encoding="utf8"))["attribution_stats"]
    print("attribution rows:", rep["rows"], "sentence rows:", rep["sentence_rows"], "unmatched:", len(rep["unmatched"]))
    for u in rep["unmatched"]:
        print("   unmatched:", u)
    json.dump({"text_checked": total, "text_failures": len(fails), "failure_rate_pct": round(100 * len(fails) / max(1, total), 2),
               "failed": fails, "spot_pass": spot_ok, "spot_total": len(SPOT), "random40_failures": bad,
               "unmatched_attribution_rows": len(rep["unmatched"]), "attribution_rows": rep["rows"]},
              open(DATA / "validation_report.json", "w", encoding="utf8"), indent=1)


if __name__ == "__main__":
    sys.exit(main())
