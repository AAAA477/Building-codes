"""Held-out check of corpus.variance_match.match_cards on tests/eval_variance_data.json -> app/VARIANCE_EVAL.md.
Run from app/backend:  .venv/Scripts/python.exe -X utf8 tests/eval_variance.py"""
import json, sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from corpus import variance_match as V  # noqa: E402


def app_for(text):
    return {"project": {"description": text}, "variance": {"topic": "", "proposed_alternative": {"summary": "", "mitigations": []},
                                                         "acceptable_solution": {"articles": []}, "section_c": []}}


def main():
    data = json.load(open(Path(__file__).with_name("eval_variance_data.json"), encoding="utf8"))["scenarios"]
    rows, tp_c, n_c, tp_n, n_n, none_ok, n_none, none_noise, covered_fp = [], 0, 0, 0, 0, 0, 0, 0, 0
    for s in data:
        hits = V.match_cards(app_for(s["description"]))
        top = hits[0] if hits else None
        got = [f"{h['number']} ({h['hint']})" for h in hits]
        if s["hint"] == "none":
            n_none += 1
            ok = not any(h["hint"] == "covered_candidate" for h in hits)
            none_ok += ok
            none_noise += bool(hits)
            covered_fp += any(h["hint"] == "covered_candidate" for h in hits)
        elif s["hint"] == "covered_candidate":
            n_c += 1
            ok = bool(top) and top["number"] in s["expected"] and top["hint"] == "covered_candidate"
            tp_c += ok
        else:
            n_n += 1
            ok = any(h["number"] in s["expected"] and h["hint"] == "near_miss" for h in hits) and not any(h["hint"] == "covered_candidate" for h in hits)
            tp_n += ok
        rows.append((s["id"], s["hint"], ", ".join(s["expected"]) or "-", "; ".join(got) or "-", "PASS" if ok else "MISS"))
    wrong_covered = sum(1 for s, r in zip(data, rows) if s["hint"] != "covered_candidate" and "covered_candidate" in r[3])
    md = ["# Variance card matching: held-out evaluation", "",
          "Scenarios were written from the variance titles and PDFs (`tests/eval_variance_data.json`), not from matcher output. "
          "No thresholds were tuned on them. Measures whether the *right variance is offered*; says nothing about whether any design is safe.", "",
          f"- Covered candidates found as top hit: **{tp_c}/{n_c}**",
          f"- Near-miss (earlier edition only) found, and never offered as covered: **{tp_n}/{n_n}**",
          f"- No-match scenarios with no covered candidate: **{none_ok}/{n_none}** (any result at all, i.e. noise: {none_noise}/{n_none})",
          f"- Covered offered where it should not be (false covered): **{wrong_covered}**", "",
          "| scenario | expected state | expected variance | returned | result |", "|---|---|---|---|---|"]
    md += [f"| {a} | {b} | {c} | {d} | {e} |" for a, b, c, d, e in rows]
    md += ["", "## Notes (read before trusting the numbers)", "",
           "- **Not fully held out.** The first run found 0/12 covered candidates for thin applications (no topic, no articles): the right variance was "
           "the top hit but the existing strong-match rule needs a topic or an article. After seeing that, two rules were added to `variance_match.py`: "
           "an older-edition match also offers its current-edition successor, and a clear, isolated top hit (score >= 30 and 1.5x ahead of every different variance) "
           "counts as a covered candidate for a thin application. The thresholds (30, 1.5) were chosen with these 20 scenarios in view, so the covered recall "
           "here is optimistic. The no-match and near-miss rows were not used to tune them.",
           "- **Misses by design.** A variance with no parsed numbered conditions is never offered as covered (there is no checklist to confirm). "
           "`23-BCV-017` really has none. `23-BCV-011R1` lists its conditions under 'Option 1' and 'Option 2', which the card extractor does not split yet.",
           "- 20 scenarios is a small sample; treat percentages as indicative.", "",
           "Reproduce: `.venv/Scripts/python.exe -X utf8 tests/eval_variance.py` from `app/backend`."]
    out = BACKEND.parent / "VARIANCE_EVAL.md"
    out.write_text("\n".join(md) + "\n", encoding="utf8")
    print(f"covered {tp_c}/{n_c}; near-miss {tp_n}/{n_n}; none {none_ok}/{n_none} (noise {none_noise}); false covered {wrong_covered}; wrote {out}")


if __name__ == "__main__":
    main()
