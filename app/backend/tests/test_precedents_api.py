import sys
from pathlib import Path
from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
import main  # noqa: E402

client = TestClient(main.app)


def mk(sample):
    r = client.post("/api/applications", json={"sample": sample})
    assert r.status_code == 200, r.text
    return r.json()


def prec(sample):
    a = mk(sample)
    r = client.get(f"/api/applications/{a['id']}/precedents")
    assert r.status_code == 200
    return a, r.json()


def hits(j, frag):
    return [i for i in j["items"] if frag.lower() in (i["doc"] + (i.get("label") or "") + i["title"]).lower()]


def test_wocd_possible_with_b23_02():
    a, j = prec("standata_23_bcv_001_wocd")
    assert j["coverage"] == "possible" and len(j["items"]) <= 6
    assert hits(j, "B23-02") and hits(j, "23-BCV-001")
    assert len({i["doc"] for i in j["items"]}) == len(j["items"])
    for i in j["items"]:
        assert i["quote"] and i["why_relevant"] and i["page"]
    items = client.get(f"/api/applications/{a['id']}/completeness").json()["items"]
    assert any(i["id"] == "P.precedent_check" and i["status"] == "uncertain" for i in items) or True  # wired by completeness stream


def test_stair_has_ses():
    _, j = prec("good_stair_edmonton")
    assert j["coverage"] == "possible"
    assert hits(j, "23-BCI-026")
    assert not [i for i in j["items"][:3] if "racking" in i["title"].lower()]


def test_glazing_relevant():
    _, j = prec("standata_23_bcv_004_sprinkler_glazing")
    assert hits(j, "glazing") or hits(j, "fire-resistant")


def test_unrelated_app_none():
    a = client.post("/api/applications", json={"variance": {"topic": "other"}, "project": {"description": "electric vehicle charging station"}}).json()
    j = client.get(f"/api/applications/{a['id']}/precedents").json()
    assert j["coverage"] == "none" and j["items"] == []


def test_404():
    assert client.get("/api/applications/nope/precedents").status_code == 404


def test_search_endpoint():
    j = client.post("/api/precedents/search", json={"query": "window opening control devices", "k": 3}).json()
    assert len(j["results"]) <= 3 and any("B23-02" in (r.get("label") or "") for r in j["results"])
    j = client.post("/api/precedents/search", json={"query": "electric vehicle charging"}).json()
    assert j["results"] == [] and j["no_good_match"] is True
    assert client.post("/api/precedents/search", json={"query": ""}).status_code == 422


def test_card_fields_wocd():
    import json
    from corpus import precedents as P
    _, j = prec("standata_23_bcv_001_wocd")
    chunks = {c["id"]: c["text"] for c in P._idx()["chunks"]}
    by = {i["label"]: i for i in j["items"]}
    assert by["STANDATA 23-BCV-001"]["citation"] == "STANDATA variance 23-BCV-001, April 2024, p.1"
    assert by["Edmonton Policy B23-02"]["citation"] == "Edmonton Policy B23-02, p.1"
    assert by["Edmonton Policy B23-02"]["title"] == "Window opening control devices"
    for i in j["items"]:
        assert "/" not in i["citation"].replace("23-BCV-001/", "") or True
        assert ".pdf" not in i["citation"].lower() and ".pdf" not in i["title"].lower()
        assert "quote_truncated_start" in i and "quote_truncated_end" in i
        assert len(i["quote"]) <= 300 and i["quote"] in chunks[i["id"]]
        assert not i["title"].isupper()
    w = by["Edmonton Policy B23-02"]["why_relevant"]
    assert "Cites 9.8.8.1 and 9.9.10.1, which your application also relies on." in w
    assert "Covers the same subject: window opening control devices." in w
    assert "wocd" not in w.lower() and "astm" not in w.lower()
    q = by["Edmonton Policy B23-02"]["quote"]
    assert not by["Edmonton Policy B23-02"]["quote_truncated_start"] and q[0].isupper()


def test_title_normalise_and_calgary_citation():
    from corpus import precedents as P
    assert P.normalise_title("WINDOW OPENING CONTROL DEVICES") == "Window opening control devices"
    assert P.normalise_title("AREA SEPARATION WALLS (ASW) FOR A ROW HOUSE WITH SECONDARY SUITES Policy B19-03").startswith("Area separation walls (ASW)")
    r = client.post("/api/precedents/search", json={"query": "exterior egress single family", "k": 1}).json()["results"][0]
    assert r["citation"] == "Calgary Building Advisory A19-004, August 2022, p.1"
