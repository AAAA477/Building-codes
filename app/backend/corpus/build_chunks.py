"""Build chunks.jsonl: stair NBC articles + Edmonton/CWC/Calgary guides + STANDATA documents.

Guides and STANDATA are split into ~300-word windows (200-400; a document's last chunk may be shorter).
NBC articles are kept one chunk per article so a citation maps to one article (split only if >400 words;
short articles therefore may be under 200 words). Files that fail or have no text layer are listed in
app/data/corpus/chunks_skipped.json.

Run (from app/backend):  python -m corpus.build_chunks
"""
import json
import re
import zlib

import pymupdf

from . import DATA, FILES

DIRECT = ["00_Challenge_Scope.pdf", "08_CWC_Alt_Solutions_Guide.pdf", "09_Calgary_Alt_Solution_Guide.pdf",
          "10_Edmonton_Emergency_Services_Guideline.pdf", "11_Edmonton_Point_Access_Block.pdf"]
TARGET, MAXW = 300, 400


def clean(t):
    return re.sub(r"\s+", " ", t.replace("​", "")).strip()


def window(words_pages, doc, prefix, out):
    """words_pages: list of (word, page). Emit chunks of ~TARGET words; page = first word's page."""
    i, n = 0, 0
    total = len(words_pages)
    while i < total:
        j = min(i + TARGET, total)
        if total - j < 100:            # fold a small tail into this chunk (<=400)
            j = total
        seg = words_pages[i:j]
        out.append({"id": f"{prefix}-{n}", "doc": doc, "page": seg[0][1],
                    "text": " ".join(w for w, _ in seg)})
        n += 1
        i = j


def pdf_chunks(path, doc, prefix, out, skipped):
    try:
        d = pymupdf.open(str(path))
        wp = []
        for pi, pg in enumerate(d):
            for w in clean(pg.get_text()).split(" "):
                if w:
                    wp.append((w, pi + 1))
    except Exception as e:  # noqa
        skipped.append({"file": str(path), "reason": f"open/extract failed: {e}"})
        return
    if len(wp) < 30:
        skipped.append({"file": str(path), "reason": f"no usable text layer ({len(wp)} words)"})
        return
    window(wp, doc, prefix, out)


def main():
    out, skipped = [], []
    with open(DATA / "stair_articles.json", encoding="utf8") as fh:
        stair = json.load(fh)["articles"]
    with open(DATA / "nbc_articles.json", encoding="utf8") as fh:
        arts = json.load(fh)
    for e in stair:
        a = arts.get(e["article"])
        if not a:
            continue
        body = f"NBC(AE) 2023 Article {a['number']} {a['title']} (Division {a['division']}). "
        body += " ".join(f"({s['number']}) {clean(s['text'])}" for s in a["sentences"])
        words = body.split(" ")
        if len(words) <= MAXW:
            out.append({"id": f"nbc:{e['article']}", "doc": "NBC_2023AE_2nd_printing.pdf",
                        "page": a["pdf_page"], "text": body})
        else:
            wp = [(w, a["pdf_page"]) for w in words]
            window(wp, "NBC_2023AE_2nd_printing.pdf", f"nbc:{e['article']}", out)
    for f in DIRECT:
        pdf_chunks(FILES / "direct" / f, f, f"direct:{f[:2]}", out, skipped)
    n_std = 0
    for p in sorted((FILES / "standata").rglob("*")):
        if p.is_file() and ".pdf" in p.name.lower():
            rel = p.relative_to(FILES / "standata").as_posix()
            before = len(out)
            pdf_chunks(p, "standata/" + rel, "standata:" + re.sub(r"[^A-Za-z0-9]+", "_", rel)[:70] + "~" + format(zlib.crc32(rel.encode()), "08x"), out, skipped)
            n_std += 1 if len(out) > before else 0
    with open(DATA / "chunks.jsonl", "w", encoding="utf8") as fh:
        for c in out:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")
    with open(DATA / "chunks_skipped.json", "w", encoding="utf8") as fh:
        json.dump(skipped, fh, indent=1)
    wc = [len(c["text"].split()) for c in out if not c["id"].startswith("nbc:")]
    print(f"chunks: {len(out)} (nbc {sum(1 for c in out if c['id'].startswith('nbc:'))}, "
          f"standata files ok {n_std}); skipped files: {len(skipped)}")
    print("guide/standata chunk words min/median/max:", min(wc), sorted(wc)[len(wc) // 2], max(wc))
    for s in skipped:
        print("  skipped:", s)


if __name__ == "__main__":
    main()
