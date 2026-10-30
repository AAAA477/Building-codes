import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from corpus import variance_match as V  # noqa: E402

SAMPLES = BACKEND.parents[0] / "data" / "samples"


def sample(name):
    return json.load(open(SAMPLES / f"{name}.json", encoding="utf8"))


def app_with(description, topic="", summary=""):
    return {"project": {"description": description},
            "variance": {"topic": topic, "proposed_alternative": {"summary": summary, "mitigations": []},
                         "acceptable_solution": {"articles": []}, "section_c": []}}


CONDS = [{"index": i, "label": str(i), "text": f"c{i}", "page": 1} for i in (1, 2, 3)]
YES = [{"index": i, "answer": "yes"} for i in (1, 2, 3)]


def test_outcome_state_all_yes_is_covered():
    assert V.outcome_state("covered_candidate", CONDS, YES) == "covered"


def test_outcome_state_unsure_or_missing_is_conditional():
    assert V.outcome_state("covered_candidate", CONDS, YES[:2] + [{"index": 3, "answer": "unsure"}]) == "conditional"
    assert V.outcome_state("covered_candidate", CONDS, YES[:2]) == "conditional"
    assert V.outcome_state("covered_candidate", CONDS, YES[:2] + [{"index": 3, "answer": "no"}]) == "conditional"


def test_gaps_lists_every_unmet_condition():
    g = V.gaps(CONDS, YES[:1] + [{"index": 2, "answer": "no"}])
    assert [x["index"] for x in g] == [2, 3]
    assert {x["index"]: x["answer"] for x in g} == {2: "no", 3: "unanswered"}


def test_near_miss_stays_near_miss_regardless_of_answers():
    assert V.outcome_state("near_miss", CONDS, YES) == "near_miss"
    assert V.outcome_state("near_miss", CONDS, []) == "near_miss"


def test_zero_conditions_never_covered():
    assert V.outcome_state("covered_candidate", [], []) == "near_miss"


def test_empty_application_matches_nothing():
    assert V.match_cards(app_with("[to be completed by applicant]")) == []
    assert V.match_cards(app_with("")) == []
    assert V.no_match_state() == "none"


def test_wocd_sample_matches_23_bcv_001_as_covered_candidate():
    hits = V.match_cards(sample("standata_23_bcv_001_wocd"))
    assert hits[0]["number"] == "23-BCV-001" and hits[0]["hint"] == "covered_candidate"
    assert "9.8.8.1" in hits[0]["matched_articles"] and hits[0]["reason"]


def test_sprinkler_glazing_sample_matches_23_bcv_004():
    hits = V.match_cards(sample("standata_23_bcv_004_sprinkler_glazing"))
    assert hits[0]["number"] == "23-BCV-004" and hits[0]["hint"] == "covered_candidate"
    assert all(h["number"] != "14-BCV-018R1" for h in hits)  # older twin of the same variance is not offered next to it


def test_2019_card_is_never_covered_candidate():
    hits = V.match_cards(app_with("We want to build walls using structural insulated panels (SIPs) instead of conventional framing.",
                                  summary="Structural insulated panels"))
    sip = [h for h in hits if V.get_card(h["number"]) and "structural insulated" in V.get_card(h["number"])["title"].lower()]
    assert sip, hits
    assert all(h["hint"] == "near_miss" for h in sip)
    assert all(V.get_card(h["number"])["edition"] != "NBC(AE) 2023" for h in sip)


def test_old_revision_not_matched():
    assert V.get_card("23-BCV-008")["id"].endswith("rev1-2024-10")
    hits = V.match_cards(sample("standata_23_bcv_008r1_exhaust_clearance"))
    assert [h["number"] for h in hits].count("23-BCV-008") == 1


def test_single_exit_stair_has_no_covered_candidate():
    hits = V.match_cards(sample("good_stair_edmonton"))
    assert all(h["hint"] != "covered_candidate" for h in hits)


def test_wocd_sample_does_not_offer_unrelated_variance_on_one_generic_word():
    nums = [h["number"] for h in V.match_cards(sample("standata_23_bcv_001_wocd"))]
    assert "23-BCV-013" not in nums   # elevator variance shares only the word "devices"


def test_topic_application_gets_no_text_similarity_only_matches():
    for name in ("standata_23_bcv_004_sprinkler_glazing", "standata_23_bcv_001_wocd"):
        for h in V.match_cards(sample(name)):
            assert h["reason"] != "Matched by text similarity only; check whether it applies.", (name, h)
