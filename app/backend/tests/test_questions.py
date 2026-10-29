import sys
from pathlib import Path
from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
import main  # noqa: E402
import questions  # noqa: E402

client = TestClient(main.app)


def mk(sample="good_stair_edmonton"):
    r = client.post("/api/applications", json={"sample": sample})
    assert r.status_code == 200, r.text
    return r.json()


def test_add_split_patch_list():
    a = mk()
    base = f"/api/applications/{a['id']}"
    r = client.post(f"{base}/questions", json={"text": "1. Please confirm the stair width.\n2. Provide the fire flow report.", "link": {"section": "D"}})
    assert r.status_code == 200
    items = r.json()["items"]
    assert [i["text"] for i in items] == ["Please confirm the stair width.", "Provide the fire flow report."]
    assert items[0]["link"] == {"section": "D", "field": None} and items[0]["status"] == "open"
    qid = items[0]["id"]
    r = client.patch(f"{base}/questions/{qid}", json={"answer": "Width is on sheet A-2.", "status": "answered"})
    assert r.status_code == 200 and r.json()["open"] == 1
    assert client.patch(f"{base}/questions/{qid}", json={"status": "bogus"}).status_code == 422
    assert client.patch(f"{base}/questions/nope", json={"status": "open"}).status_code == 404
    assert client.post(f"{base}/questions", json={"text": "  "}).status_code == 422
    assert len(client.get(f"{base}/questions").json()["items"]) == 2


def test_persisted_and_completeness_items():
    a = mk()
    base = f"/api/applications/{a['id']}"
    before = client.get(f"{base}/completeness").json()
    client.post(f"{base}/questions", json={"questions": ["Who is the registered professional?"], "link": {"section": "D"}})
    comp = client.get(f"{base}/completeness").json()
    qs = [i for i in comp["items"] if i["id"].startswith("Q.")]
    assert len(qs) == 1 and qs[0]["status"] == "uncertain" and qs[0]["section"] == "D"
    assert len(comp["items"]) == len(before["items"]) + 1
    qid = qs[0]["id"][2:]
    client.patch(f"{base}/questions/{qid}", json={"status": "needs_professional"})
    comp = client.get(f"{base}/completeness").json()
    assert [i["status"] for i in comp["items"] if i["id"].startswith("Q.")] == ["needs_professional"]
    client.patch(f"{base}/questions/{qid}", json={"status": "answered", "answer": "x"})
    comp = client.get(f"{base}/completeness").json()
    assert not [i for i in comp["items"] if i["id"].startswith("Q.")]
    assert client.get(f"{base}").json()["officer_questions"]["items"][0]["answer"] == "x"


def test_changes_diff_is_exact():
    a = mk()
    base = f"/api/applications/{a['id']}"
    assert client.get(f"{base}/changes").json()["has_snapshot"] is False
    r = client.post(f"{base}/mark-submitted", json={})
    assert r.status_code == 200 and "does not send" in r.json()["note"]
    assert client.get(f"{base}/changes").json()["changes"] == []
    old_desc = client.get(base).json()["project"]["description"]
    client.patch(base, json={"project": {"description": "Changed description"}, "location": {"lot": "99"}})
    ch = client.get(f"{base}/changes").json()
    by = {c["path"]: c for c in ch["changes"]}
    assert by["project.description"] == {"path": "project.description", "kind": "changed", "old": old_desc, "new": "Changed description"}
    assert by["location.lot"]["new"] == "99"
    assert set(by) == {"project.description", "location.lot"}
    client.post(f"{base}/mark-submitted", json={})  # re-marking resets the baseline
    assert client.get(f"{base}/changes").json()["changes"] == []


def test_diff_added_removed_lists():
    app = {"applicant": {}, "project": {}, "location": {}, "variance": {"acceptable_solution": {"articles": ["3.4.2.1"]}},
           "section_d": [{"id": "d1", "document_name": "Report", "status": "missing"}]}
    questions.mark_submitted(app)
    app["variance"]["acceptable_solution"]["articles"] = ["3.4.2.1", "3.3.1.1"]
    app["section_d"] = [{"id": "d2", "document_name": "Plan", "status": "provided"}]
    kinds = {c["path"]: c["kind"] for c in questions.diff(app)["changes"]}
    assert kinds["variance.acceptable_solution.articles"] == "changed"
    assert kinds["section_d.d1.status"] == "removed" and kinds["section_d.d2.status"] == "added"


def test_after_submit_sources_and_jurisdiction():
    for j in ("scc", "edmonton", "calgary"):
        d = client.get(f"/api/after-submit?jurisdiction={j}").json()
        assert d["sections"]
        for s in d["sections"]:
            for f in s["facts"]:
                assert f["source"]["doc"] and f["source"]["page"]
    cal = client.get("/api/after-submit?jurisdiction=calgary").json()
    assert any("$500" in f["text"] for s in cal["sections"] for f in s["facts"])
    edm = client.get("/api/after-submit?jurisdiction=edmonton").json()
    assert not any("$500" in f["text"] for s in edm["sections"] for f in s["facts"])
    assert any(s["unknown"] for s in edm["sections"])
    a = mk()
    assert client.get(f"/api/applications/{a['id']}/after-submit").json()["jurisdiction"] == "edmonton"
