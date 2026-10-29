"""Write app/RETRIEVAL_EVAL.md from retrieval_results_a.json / _b.json (+ a hand-written shipped section passed in
app/data/corpus/retrieval_notes.md). Run from app/backend:  python -m corpus.render_retrieval_report"""
import json

from . import DATA

OUT = DATA.parents[1] / "RETRIEVAL_EVAL.md"
COLS = ("hit@1", "hit@5", "hit@10", "recall@5", "recall@10", "MRR")


def row(name, m):
    return f"| {name} | " + " | ".join(f"{m[c]:.3f}" for c in COLS) + f" | {m['n']} |"


def main():
    a = json.load(open(DATA / "retrieval_results_a.json", encoding="utf8"))
    try:
        b = json.load(open(DATA / "retrieval_results_b.json", encoding="utf8"))
    except FileNotFoundError:
        b = None
    notes = ""
    try:
        notes = open(DATA / "retrieval_notes.md", encoding="utf8").read()
    except FileNotFoundError:
        pass
    L = ["# Retrieval evaluation (held-out numbers only)", "",
         f"Eval set: {a['n_tune'] + a['n_heldout']} real documents (STANDATA variances/interpretations/bulletins, Edmonton policies, "
         f"Calgary advisories) that cite at least one verified NBC article. Query = document title + its Purpose/Application "
         "sentences with article numbers and code references stripped; truth = the document's verified cited articles. "
         f"Split by title group (revisions stay together), seed fixed: {a['n_tune']} tune / {a['n_heldout']} held-out. "
         "Weights were tuned on the tune split only; the tables below are the held-out split. "
         "recall@k = |truth in top k| / min(|truth|, k). Truth is NBC only, so cross-code hits count as misses here.", "",
         "## BM25 variants (no LLM)", "",
         "| variant | hit@1 | hit@5 | hit@10 | recall@5 | recall@10 | MRR | n |", "|---|---|---|---|---|---|---|---|"]
    for k, v in a.items():
        if k.startswith("V"):
            L.append(row(k, v["heldout"]))
    L += ["", f"Tuned config (chosen on tune only, {a['grid_size']} grid points): `{json.dumps(a['tuned_config'])}`", ""]
    if b:
        L += ["## All variants on the same held-out split", "",
              "| variant | hit@1 | hit@5 | hit@10 | recall@5 | recall@10 | MRR | n |", "|---|---|---|---|---|---|---|---|"]
        for k, v in b["heldout"].items():
            L.append(row(k, v))
        L += ["", f"Dense model: {json.dumps(b.get('dense'))}. LLM: {b.get('llm')}.", "",
              "## 18 realistic applicant descriptions (precision@5 against hand-written article families)", "",
              "Relevance = the hit lies in a hand-written expected family (code + section prefix, listed in corpus/retrieval_eval.py). "
              "A family is a judgement of which sections govern the topic; hits outside it are listed as irrelevant below, "
              "including some that a reviewer may consider borderline.", "",
              "| variant | mean precision@5 |", "|---|---|"]
        for k, v in b["realistic_mean_p@5"].items():
            L.append(f"| {k} | {v:.3f} |")
        shipped = "V1+V2 shipped (tuned + noise filter)"
        L += ["", f"### Per query, shipped variant (`{shipped}`) and baseline", "",
              "| query | expected | p@5 shipped | p@5 baseline | no_good_match | irrelevant hits (shipped) |", "|---|---|---|---|---|---|"]
        for r in b["realistic"]:
            fam = ", ".join(f"{c} {p}*" for c, p in r["family"]) if r["family"] else "none (expect no match)"
            s, bl = r[shipped], r["V0 current BM25"]
            L.append(f"| {r['query']} | {fam} | {s['p@5']} | {bl['p@5']} | {r['no_good_match']} | {'; '.join(s['irrelevant']) or '-'} |")
    L += ["", "## Held-out documents where the shipped BM25 misses the top 5", "",
          "| document | truth size | rank of first true hit | top 3 returned | sample of truth |", "|---|---|---|---|---|"]
    for f in a["heldout_failures_tuned"]:
        L.append(f"| {f['doc']} | {f['truth_n']} | {f['first_hit_rank']} | {', '.join(f['top3'])} | {', '.join(f['truth_sample'])} |")
    L += ["", notes]
    OUT.write_text("\n".join(L) + "\n", encoding="utf8")
    print("wrote", OUT)


if __name__ == "__main__":
    main()
