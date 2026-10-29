import copy
import datetime
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
import consistency  # noqa: E402
import completeness  # noqa: E402

SAMPLES = BACKEND.parent / "data" / "samples"


def load(name):
    return json.load(open(SAMPLES / f"{name}.json", encoding="utf8"))


def ids(app):
    return [i["id"] for i in consistency.items(app)]


def has(app, prefix):
    return any(i.startswith(prefix) for i in ids(app))


def base(**project):
    a = load("good_stair_edmonton")
    a["project"].update(project)
    return a


def test_clean_samples_zero_items():
    for p in sorted(SAMPLES.glob("*.json")):
        a = json.load(open(p, encoding="utf8"))
        if "variance" not in a:
            continue
        assert consistency.items(a) == [], (p.name, ids(a))


def test_clean_flows_through_completeness_without_x_items():
    c = completeness.compute(load("good_stair_edmonton"))
    assert not [i for i in c["items"] if i["id"].startswith("X.")]


def test_storeys_mismatch_and_match():
    a = base(storeys=6, description="A 5-storey residential building.")
    assert has(a, "X.storeys")
    a = base(storeys=5, description="A five storeys residential building.")
    assert not has(a, "X.storeys")
    a = base(storeys=5, description="A five-storey building.")
    assert not has(a, "X.storeys")
    # a limit is not a project value
    a = base(storeys=4, description="Scope is 6 storeys or less; up to 6 storeys.")
    assert not has(a, "X.storeys")
    # placeholders are ignored
    a = base(storeys=4, description="[3 storeys to be completed]")
    assert not has(a, "X.storeys")


def test_area_and_units():
    a = base(building_area_m2=1000, description="Total area is 500 m2.")
    assert has(a, "X.area")
    a = base(building_area_m2=1000, description="Total area is 1,000 m2.")
    assert not has(a, "X.area")
    a = base(building_area_m2=929.03, description="About 10000 sq ft (929 m2).")
    assert not has(a, "X.area")
    a = base(building_area_m2=500, description="About 10,000 sq ft.")
    assert has(a, "X.area")
    a = base(units_per_floor=4, description="Six units per floor.")
    assert has(a, "X.units.")
    a = base(units_per_floor=4, description="not more than 4 dwelling units per floor")
    assert not has(a, "X.units.")


def test_mixed_units():
    a = base(description="Stair width of 44 inches and 12 ft travel.")
    assert has(a, "X.units_mixed")
    a = base(description="Stair width of 1100 mm (44 inches).")
    assert not has(a, "X.units_mixed")
    a = base(description="Floor to floor 3 m.")
    assert not has(a, "X.units_mixed")


def test_edition_and_place():
    a = base(description="Designed to NBC 2015 requirements.")
    assert has(a, "X.edition")
    a = base(description="Per NBC 2020 intent statements.")
    assert not has(a, "X.edition")
    a = base(description="Per NBC(AE) 2023.")
    assert not has(a, "X.edition")
    assert has(base(description="Complies with the Ontario Building Code."), "X.place")
    assert has(base(description="As accepted by OBC in Toronto."), "X.place")
    assert not has(base(description="Site on Saskatchewan Drive, Edmonton."), "X.place")
    a = load("good_stair_edmonton")
    a["variance"]["code_or_standard"] = "NBC 2019"
    assert has(a, "X.edition")


def test_unverifiable_article_in_text():
    a = base(description="See Sentence 3.4.2.1.(1) of the code.")
    assert not has(a, "X.article")
    a = base(description="See article 99.99.99.99 of the code.")
    assert has(a, "X.article")


def test_owner_reminder_only_when_name_given():
    a = load("good_stair_edmonton")
    assert not has(a, "X.owner_title")
    a["applicant"]["owner_name"] = "Jane Doe"
    its = [i for i in consistency.items(a) if i["id"] == "X.owner_title"]
    assert its and "does not check the land title" in its[0]["message"]
    assert its[0]["status"] == "uncertain" and its[0]["severity"] == "confirm"


def test_dates():
    a = load("good_stair_edmonton")
    a["applicant"]["date_of_request"] = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()
    assert has(a, "X.date")
    a["applicant"]["date_of_request"] = "2019-05-01"
    assert has(a, "X.date")
    a["applicant"]["date_of_request"] = datetime.date.today().isoformat()
    assert not has(a, "X.date")
    a["applicant"]["date_of_request"] = "[to be completed]"
    assert not has(a, "X.date")


def test_item_shape_and_never_blocker_or_safety_words():
    a = copy.deepcopy(load("good_stair_edmonton"))
    a["applicant"]["owner_name"] = "Jane"
    a["applicant"]["date_of_request"] = "2010-01-01"
    a["project"]["description"] = "Ontario Building Code, NBC 2015, 12 ft"
    c = completeness.compute(a)
    xs = [i for i in c["items"] if i["id"].startswith("X.")]
    assert xs
    for i in xs:
        assert {"id", "label", "section", "status", "message", "node_id", "group", "priority", "severity"} <= set(i)
        assert i["severity"] == "confirm"
        low = i["message"].lower()
        assert not any(w in low for w in ("safe", "equivalent", "approve", "compliant"))
