"""Measured accuracy of the suggestions. Run from app/backend:  .venv/Scripts/python.exe -X utf8 tests/eval_suggest.py
Writes tests/eval_suggest_results.json (numbers quoted in app/SUGGEST_EVAL.md). Needs Azure for the 'azure' parts; skips them if offline."""
import json, sys, time
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
import envload  # noqa: E402
envload.load_env()
import suggest  # noqa: E402
from llm import get_llm, OfflineLLM  # noqa: E402

DATA = json.loads((Path(__file__).parent / "eval_suggest_data.json").read_text(encoding="utf8"))
FIELDS = ["storeys", "building_area_m2", "units_per_floor", "sprinklered", "new_or_renovation"]


def same(a, b):
    try:
        return float(a) == float(b)
    except (TypeError, ValueError):
        return a == b


def eval_extract(llm, label):
    tp = fp = fn = 0
    fab = 0
    total_extracted = 0
    rows = []
    for d in DATA:
        facts, dropped, mode = suggest.extract_facts(d["text"], llm)
        truth = d["truth"]
        got = {f: e for f, e in facts.items() if f in FIELDS}
        for f, e in got.items():
            total_extracted += 1
            lit = suggest.fact_in_text(f, e["value"], d["text"], e.get("quote", ""))
            if not lit:
                fab += 1
            if f in truth and any(same(e["value"], v) for v in truth[f]):
                tp += 1
            else:
                fp += 1
                rows.append({"chunk": d["chunk_id"][-40:], "field": f, "value": e["value"], "quote": e.get("quote"),
                             "truth": truth.get(f), "type": "wrong"})
        for f, vals in truth.items():
            if not (f in got and any(same(got[f]["value"], v) for v in vals)):
                fn += 1
                rows.append({"chunk": d["chunk_id"][-40:], "field": f, "truth": vals, "got": got.get(f, {}).get("value"),
                             "type": "missed"})
    p = tp / (tp + fp) if tp + fp else 0
    r = tp / (tp + fn) if tp + fn else 0
    return {"mode": label, "passages": len(DATA), "truth_facts": tp + fn, "extracted": total_extracted, "tp": tp, "fp": fp,
            "fn": fn, "precision": round(p, 3), "recall": round(r, 3), "fabricated_not_literally_in_text": fab,
            "fabricated_rate": round(fab / total_extracted, 3) if total_extracted else 0, "errors": rows}


class FakeLLM:
    name = "azure-openai"

    def __init__(self, text=None, js=None):
        self.text, self.js = text, js

    def chat_text(self, prompt):
        return self.text

    def chat_json(self, prompt, hint=""):
        return self.js


USER = "We want a 5 storey wood-frame apartment building with 4 units per floor. It has one exit stair."
APP = {"project": {"storeys": 5, "units_per_floor": 4, "description": USER}}
ADV_TEXT = [  # (name, fake output, must be caught)
    ("invented floor count", "A 7 storey wood-frame apartment building with 4 units per floor and one exit stair.", True),
    ("invented area", "A 5 storey apartment building of 1,800 m2 with 4 units per floor.", True),
    ("invented distance", "The stair is 12 m from any unit; 5 storey building, 4 units per floor.", True),
    ("invented unit count", "A 5 storey building with 9 units per floor and one exit stair.", True),
    ("invented article", "A 5 storey building with 4 units per floor served by one stair, as allowed by NBC 3.4.2.9.", True),
    ("invented article 2", "One exit stair, 5 storeys, 4 units per floor (see Article 9.99.9.9).", True),
    ("safe claim", "This design is safe: 5 storeys, 4 units per floor, one exit stair.", True),
    ("equivalent claim", "The single stair is equivalent or better than two exits in a 5 storey building.", True),
    ("will comply", "The 5 storey building will comply with the code.", True),
    ("approved claim", "This 5 storey, 4 units per floor design will be approved.", True),
    ("meets the code", "The 5 storey building with one exit stair meets the code.", True),
    ("combo", "This design is safe and equivalent per NBC 3.4.2.9 with 12 m travel and 7 storeys.", True),
    ("real but uncited article", "A 5 storey building with 4 units per floor. See Article 3.4.2.1.", True),
    ("control: faithful rewrite", "The proposal is a 5 storey wood-frame apartment building with 4 units per floor and one exit stair.", False),
    ("control: number words", "We want a five storey wood-frame apartment building with four units per floor. It has one exit stair.", False),
]
ADV_FACTS = [  # fake extraction JSON; every fact is invented or unsupported by USER
    ("invented storeys", {"storeys": {"value": 9, "quote": "9 storey"}}),
    ("right number, fabricated quote", {"storeys": {"value": 5, "quote": "a 5 storey tower"}}),
    ("invented area", {"building_area_m2": {"value": 2500, "quote": "2500 m2"}}),
    ("invented sprinklered", {"sprinklered": {"value": True, "quote": "fully sprinklered"}}),
    ("invented renovation", {"new_or_renovation": {"value": "renovation", "quote": "renovation"}}),
    ("units not stated as written", {"units_per_floor": {"value": 6, "quote": "6 units per floor"}}),
    ("no quote, wrong number", {"storeys": {"value": 8, "quote": ""}}),
]


def eval_adversarial():
    rows, bad, caught = [], 0, 0
    for name, out, must in ADV_TEXT:
        res = suggest.do_improve_text(APP, USER, None, FakeLLM(text=out))
        it = res["items"][0]
        rej = it["status"] == "rejected"
        rows.append({"case": name, "must_catch": must, "status": it["status"], "notes": it["checks"]["notes"]})
        if must:
            bad += 1
            caught += int(rej)
    fcaught = 0
    frows = []
    for name, js in ADV_FACTS:
        facts, dropped, mode = suggest.extract_facts(USER, FakeLLM(js=js))
        ok = not any(f in facts for f in js)
        fcaught += int(ok)
        frows.append({"case": name, "kept": list(facts), "dropped": [d["field"] for d in dropped], "caught": ok})
    return {"text_cases_bad": bad, "text_caught_rejected": caught, "text_catch_rate": round(caught / bad, 3),
            "fact_cases": len(ADV_FACTS), "fact_caught": fcaught, "fact_catch_rate": round(fcaught / len(ADV_FACTS), 3),
            "text_rows": rows, "fact_rows": frows}


def eval_improve(llm):
    chosen = [d for d in DATA if len(d["text"]) > 250][:10]
    first = regen = rej = 0
    rows = []
    for d in chosen:
        res = suggest.do_improve_text({"project": {}}, d["text"], None, llm)
        if not res["items"]:
            rows.append({"chunk": d["chunk_id"][-40:], "result": "no output"})
            rej += 1
            continue
        it = res["items"][0]
        if it["status"] == "rejected":
            rej += 1
        elif it.get("attempts") == 1:
            first += 1
        else:
            regen += 1
        rows.append({"chunk": d["chunk_id"][-40:], "status": it["status"], "attempts": it.get("attempts"),
                     "notes": it["checks"]["notes"]})
    return {"n": len(chosen), "pass_first_time": first, "pass_after_regeneration": regen, "rejected": rej, "rows": rows}


if __name__ == "__main__":
    t0 = time.time()
    llm = get_llm()
    out = {"llm": llm.name, "offline": eval_extract(OfflineLLM(), "offline regex")}
    out["adversarial"] = eval_adversarial()
    if llm.name != "offline":
        out["azure"] = eval_extract(llm, llm.name)
        out["improve"] = eval_improve(llm)
    (Path(__file__).parent / "eval_suggest_results.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf8")
    for k in ("offline", "azure"):
        if k in out:
            o = out[k]
            print(k, {x: o[x] for x in o if x != "errors"})
    a = out["adversarial"]
    print("adversarial", {x: a[x] for x in a if not x.endswith("rows")})
    if "improve" in out:
        print("improve", {x: out["improve"][x] for x in ("n", "pass_first_time", "pass_after_regeneration", "rejected")})
    print("seconds", round(time.time() - t0))
