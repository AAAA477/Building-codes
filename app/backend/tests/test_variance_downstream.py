import copy
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
import completeness as cp  # noqa: E402
import models  # noqa: E402
import reviewer  # noqa: E402
from corpus import variance_match as V  # noqa: E402
from export import package  # noqa: E402

SAMPLES = BACKEND.parent / "data" / "samples"
NUM = "23-BCV-004"   # 11 conditions
CARD = V.get_card(NUM)


def sample(name="standata_23_bcv_004_sprinkler_glazing"):
    return models.normalize(json.load(open(SAMPLES / f"{name}.json", encoding="utf8")))


def with_answers(app, answers):
    a = copy.deepcopy(app)
    a["variance"]["relied_on"] = {"number": NUM, "edition": CARD["edition"], "condition_answers": answers}
    return a


def yes(n=None):
    return [{"index": c["index"], "answer": "yes"} for c in CARD["conditions"][:n]]


def comp(app):
    return cp.compute(app)


def test_completeness_lists_unmet_condition():
    ans = yes()
    ans[1] = {"index": ans[1]["index"], "answer": "no"}
    ans[2] = {"index": ans[2]["index"], "answer": "unsure"}
    items = [i for i in comp(with_answers(sample(), ans))["items"] if i["id"].startswith(f"V.cond.{NUM}.") and i["status"] != "complete"]
    assert len(items) == 2
    st = {i["id"].rsplit(".", 1)[1]: i["status"] for i in items}
    assert st[str(ans[1]["index"])] == "missing" and st[str(ans[2]["index"])] == "uncertain"
    assert all(i["group"] == "alternative" for i in items)


def test_completeness_unanswered_conditions_are_open():
    items = [i for i in comp(with_answers(sample(), []))["items"] if i["id"].startswith(f"V.cond.{NUM}.")]
    assert len(items) == len(CARD["conditions"]) and all(i["status"] == "uncertain" for i in items)


def test_completeness_unchanged_without_relied_on():
    assert not [i for i in comp(sample())["items"] if i["id"].startswith("V.")]


def test_completeness_all_yes_has_no_open_items():
    items = [i for i in comp(with_answers(sample(), yes()))["items"] if i["id"].startswith("V.")]
    assert items and all(i["status"] == "complete" for i in items)


def test_reviewer_rfi_has_line_per_unmet_condition():
    app = with_answers(sample(), yes()[:-2])
    c = comp(app)
    rfi = reviewer.rfi_draft(app, c)
    lines = [x for x in rfi["items"] if x["id"].startswith(f"V.cond.{NUM}.")]
    assert len(lines) == 2
    assert all(f"STANDATA {NUM}" in x["text"] and "own variance request" in x["text"] for x in lines)
    assert "STANDATA " + NUM in rfi["body"]


def test_reviewer_text_has_no_safety_or_approval_wording():
    app = with_answers(sample(), yes()[:-1])
    c = comp(app)
    for x in reviewer.rfi_draft(app, c)["items"]:
        if x["id"].startswith("V.cond."):
            cond = next(m for m in CARD["conditions"] if x["id"].endswith("." + str(m["index"])))
            wording = x["text"].replace(cond["text"], "").lower()
            for bad in ("safe", "compliant", "approved"):
                assert bad not in wording
    s = reviewer.summary(app, c)["summary"].lower()
    for bad in ("is safe", "compliant", "approved"):
        assert bad not in s


def test_reviewer_summary_counts_confirmed_conditions():
    app = with_answers(sample(), yes()[:-3])
    s = reviewer.summary(app, comp(app))
    assert f"{len(CARD['conditions']) - 3} of {len(CARD['conditions'])} conditions confirmed" in s["summary"]


def cover(app):
    return package._cover_note(app, ["form.pdf"], "scc", "accreditation@safetycodes.ab.ca", "SCC form", [])


def test_cover_note_names_variance_only_when_all_yes():
    assert f"Relies on STANDATA {NUM}" in cover(with_answers(sample(), yes()))
    assert "Relies on STANDATA" not in cover(with_answers(sample(), yes()[:-1]))
    assert "Relies on STANDATA" not in cover(sample())


def test_precedent_mitigation_export_has_attribution():
    a = sample()
    a["variance"]["proposed_alternative"]["mitigations"].append(
        {"id": "V-19-BCV-020-1", "label": "Based on STANDATA 19-BCV-020, condition 1", "detail": "x", "evidence_ids": []})
    note = cover(a)
    assert "Based on STANDATA 19-BCV-020, condition 1" in note
