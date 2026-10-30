import sys
from pathlib import Path
from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
import main  # noqa: E402
from corpus import variance_match as V  # noqa: E402

client = TestClient(main.app)


def mk(sample=None):
    r = client.post("/api/applications", json={"sample": sample} if sample else {})
    assert r.status_code == 200, r.text
    return r.json()


def match(app_id):
    r = client.get(f"/api/applications/{app_id}/variance-match")
    assert r.status_code == 200, r.text
    return r.json()


def put(app_id, number, answers):
    return client.put(f"/api/applications/{app_id}/variance/relied-on", json={"number": number, "condition_answers": answers})


def all_yes(number):
    return [{"index": c["index"], "answer": "yes"} for c in V.get_card(number)["conditions"]]


def test_match_wocd_sample_candidate():
    a = mk("standata_23_bcv_001_wocd")
    j = match(a["id"])
    it = j["items"][0]
    assert it["number"] == "23-BCV-001" and it["hint"] == "covered_candidate" and it["edition"] == "NBC(AE) 2023"
    assert it["conditions"] and all(c["answer"] == "unanswered" for c in it["conditions"])
    assert it["source"]["doc"] and it["source"]["page"] >= 1
    assert j["outcome"] == "conditional"   # nothing confirmed yet: never "covered" without answers


def test_put_all_yes_gives_covered_state():
    a = mk("standata_23_bcv_001_wocd")
    r = put(a["id"], "23-BCV-001", all_yes("23-BCV-001"))
    assert r.status_code == 200 and r.json()["state"] == "covered" and r.json()["gaps"] == []
    j = match(a["id"])
    assert j["outcome"] == "covered" and "authority" in j["items"][0]["message"].lower()
    assert client.get(f"/api/applications/{a['id']}").json()["variance"]["relied_on"]["number"] == "23-BCV-001"


def test_put_one_no_gives_conditional_with_gap_and_message():
    a = mk("standata_23_bcv_004_sprinkler_glazing")
    ans = all_yes("23-BCV-004")
    ans[1] = {"index": ans[1]["index"], "answer": "no"}
    r = put(a["id"], "23-BCV-004", ans)
    j = r.json()
    assert j["state"] == "conditional" and [g["index"] for g in j["gaps"]] == [ans[1]["index"]]
    assert "adjust the design" in j["message"].lower() and "own variance request" in j["message"].lower()
    for bad in ("safe", "compliant", "approved"):
        assert bad not in j["message"].lower()


def test_put_unknown_number_404_and_unchanged():
    a = mk("standata_23_bcv_001_wocd")
    before = client.get(f"/api/applications/{a['id']}").json()
    assert put(a["id"], "99-BCV-999", []).status_code == 404
    assert client.get(f"/api/applications/{a['id']}").json() == before


def test_put_bad_index_and_bad_answer_422():
    a = mk("standata_23_bcv_001_wocd")
    before = client.get(f"/api/applications/{a['id']}").json()
    assert put(a["id"], "23-BCV-001", [{"index": 99, "answer": "yes"}]).status_code == 422
    assert put(a["id"], "23-BCV-001", [{"index": 1, "answer": "maybe"}]).status_code == 422
    assert put(a["id"], "23-BCV-001", "nope").status_code == 422
    assert client.get(f"/api/applications/{a['id']}").json() == before


def test_answers_for_other_number_not_applied():
    a = mk("standata_23_bcv_001_wocd")
    assert put(a["id"], "23-BCV-004", all_yes("23-BCV-004")).status_code == 200
    j = match(a["id"])
    assert j["items"][0]["number"] == "23-BCV-001"
    assert all(c["answer"] == "unanswered" for c in j["items"][0]["conditions"])
    assert j["outcome"] == "conditional"


def test_starting_point_only_for_near_miss():
    a = mk("standata_23_bcv_001_wocd")
    assert client.get(f"/api/applications/{a['id']}/variance/starting-point", params={"number": "23-BCV-001"}).json()["items"] == []
    n = mk()
    r = client.get(f"/api/applications/{n['id']}/variance/starting-point", params={"number": "19-BCV-020"})
    assert r.status_code == 200
    items = r.json()["items"]
    assert items and all(i["kind"] == "precedent" and "19-BCV-020" in i["label"] for i in items)
    assert client.get(f"/api/applications/{n['id']}/variance/starting-point", params={"number": "00-BCV-000"}).status_code == 404


def test_accept_precedent_sets_provenance_precedent():
    n = mk()
    item = client.get(f"/api/applications/{n['id']}/variance/starting-point", params={"number": "19-BCV-020"}).json()["items"][0]
    r = client.post(f"/api/applications/{n['id']}/suggest/accept",
                    json={"field_path": item["field_path"], "value": item["value"], "item_id": item["id"], "provenance": "precedent",
                          "append": item.get("append", False)})
    assert r.status_code == 200
    again = client.post(f"/api/applications/{n['id']}/suggest/accept",
                        json={"field_path": item["field_path"], "value": item["value"], "item_id": item["id"],
                              "provenance": "precedent", "append": item.get("append", False)}).json()
    assert str(again["variance"]).count(str(item["value"] if isinstance(item["value"], str) else item["value"]["id"])) ==         str(r.json()["variance"]).count(str(item["value"] if isinstance(item["value"], str) else item["value"]["id"]))  # no duplicate on re-accept
    assert r.json()["provenance"][item["field_path"]]["source"] == "precedent"
    bad = client.post(f"/api/applications/{n['id']}/suggest/accept",
                      json={"field_path": item["field_path"], "value": item["value"], "provenance": "applicant"})
    assert bad.status_code == 422


def test_accept_cannot_touch_declarations():
    n = mk()
    r = client.post(f"/api/applications/{n['id']}/suggest/accept",
                    json={"field_path": "declarations.owner_signed", "value": True, "provenance": "precedent"})
    assert r.status_code == 409


def test_empty_description_returns_none_outcome_200():
    n = mk()
    j = match(n["id"])
    assert j["outcome"] == "none" and j["items"] == [] and j["note"]


def test_unknown_application_404():
    assert client.get("/api/applications/zzzzzzzz/variance-match").status_code == 404


def test_starting_point_articles_are_division_b_only():
    from corpus import verifier
    n = mk()
    items = client.get(f"/api/applications/{n['id']}/variance/starting-point", params={"number": "19-BCV-020"}).json()["items"]
    for i in items:
        if i["field_path"] == "variance.acceptable_solution.articles":
            assert verifier.article_exists(i["value"])
