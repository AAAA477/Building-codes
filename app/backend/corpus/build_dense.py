"""Optional dense index (local CPU embeddings via fastembed). Writes app/data/corpus/dense_index.npz.
Run from app/backend:  .venv/Scripts/python.exe -X utf8 -m corpus.build_dense
Text per article = title + section titles + first 160 words of the sentences (same real text as the BM25 index)."""
import sys, time
import numpy as np

from . import DATA
from . import nbc_search as N

MODEL = "BAAI/bge-small-en-v1.5"
OUT = DATA / "dense_index.npz"


def article_text(rec):
    t, mid, body = N._fields(rec)
    return f"{t}. {mid}. " + " ".join(body.split()[:160])


def main():
    from fastembed import TextEmbedding
    idx = N._index()
    texts = [article_text(N.articles_of(d["code"]).get(d["key"], {})) for d in idx["docs"]]
    t0 = time.time()
    emb = TextEmbedding(MODEL)
    vecs = np.array(list(emb.embed(texts, batch_size=64)), dtype=np.float32)
    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-9
    np.savez_compressed(OUT, vecs=vecs, keys=np.array([f"{d['code']}|{d['key']}" for d in idx["docs"]]), model=MODEL)
    print("dense index", vecs.shape, f"{time.time() - t0:.0f}s ->", OUT)


if __name__ == "__main__":
    main()
