"""Pure-Python BM25 over app/data/corpus/chunks.jsonl.

search(query, k=5) -> [{id, doc, page, score, text}]
"""
import json
import math
import re
from collections import Counter
from functools import lru_cache

from . import DATA

K1, B = 1.5, 0.75
STOP = set("a an and are as at be by for from has in is it of on or that the to was were will with this these".split())


def tokenize(s):
    return [t for t in re.findall(r"[a-z0-9]+(?:\.[0-9]+)*", s.lower()) if t not in STOP]


@lru_cache(maxsize=1)
def _index():
    docs = []
    with open(DATA / "chunks.jsonl", encoding="utf8") as fh:
        for line in fh:
            if line.strip():
                docs.append(json.loads(line))
    tfs = [Counter(tokenize(d["text"])) for d in docs]
    lens = [sum(t.values()) for t in tfs]
    avg = sum(lens) / max(1, len(lens))
    df = Counter()
    for t in tfs:
        df.update(t.keys())
    n = len(docs)
    idf = {w: math.log(1 + (n - c + 0.5) / (c + 0.5)) for w, c in df.items()}
    return docs, tfs, lens, avg, idf


def search(query, k=5):
    docs, tfs, lens, avg, idf = _index()
    q = tokenize(query)
    scores = []
    for i, tf in enumerate(tfs):
        s = 0.0
        for w in q:
            f = tf.get(w)
            if f:
                s += idf[w] * f * (K1 + 1) / (f + K1 * (1 - B + B * lens[i] / avg))
        if s > 0:
            scores.append((s, i))
    scores.sort(reverse=True)
    return [{"id": docs[i]["id"], "doc": docs[i]["doc"], "page": docs[i]["page"],
             "score": round(s, 4), "text": docs[i]["text"]} for s, i in scores[:k]]


if __name__ == "__main__":
    import sys
    for r in search(" ".join(sys.argv[1:]) or "single exit stair", 5):
        print(r["score"], r["id"], r["doc"], "p", r["page"], "|", r["text"][:120])
