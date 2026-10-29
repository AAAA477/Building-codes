import json, sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
import main  # noqa: E402

client = TestClient(main.app)
SAMPLES = BACKEND.parent / "data" / "samples"


def sample_files():
    fs = sorted(p for p in SAMPLES.glob("*.json") if p.name != "application.example.json")
    return fs or [SAMPLES / "application.example.json"]


def mk(body=None):
    r = client.post("/api/applications", json=body or {})
    assert r.status_code == 200, r.text
    return r.json()


def test_create_patch_provenance():
    a = mk()
    r = client.patch(f"/api/applications/{a['id']}", json={"applicant": {"owner_name": "Test Owner"},
                                                            "project": {"storeys": 4}})
    assert r.status_code == 200
    j = r.json()
    assert j["applicant"]["owner_name"] == "Test Owner" and j["applicant"]["email"] == ""  # deep merge
    assert j["provenance"]["applicant.owner_name"]["source"] == "applicant"
    assert j["provenance"]["project.storeys"]["source"] == "applicant"
    assert client.get(f"/api/applications/{a['id']}").json()["project"]["storeys"] == 4


def test_classify_unsupported_topic():
    a = mk({"variance": {"topic": "fire_alarm"}})
    r = client.post(f"/api/applications/{a['id']}/classify").json()
    assert r["supported"] is True and r["topic"] == "other_nbc" and r["mode"] == "lookup" and r["declared_topic"] == "fire_alarm"
    b = mk({"variance": {"topic": "single_exit_stair"}})
    assert client.post(f"/api/applications/{b['id']}/classify").json()["supported"] is True


def test_part_rules():
    import rules
    assert rules.determine_part({"occupancy": "Group C residential", "storeys": 3, "building_area_m2": 500})["part"] == "9"
    assert rules.determine_part({"occupancy": "Group C", "storeys": 6, "building_area_m2": 500})["part"] == "3"
    assert rules.determine_part({"occupancy": "Group C", "storeys": 2, "building_area_m2": 601})["part"] == "3"
    assert rules.determine_part({"occupancy": "Group A", "storeys": 1, "building_area_m2": 50})["part"] == "3"
    assert rules.determine_part({})["part"] is None


def test_completeness_empty_vs_filled():
    a = mk()
    empty = client.get(f"/api/applications/{a['id']}/completeness").json()
    sample = json.loads(sample_files()[0].read_text(encoding="utf-8"))
    b = mk({k: v for k, v in sample.items() if not k.startswith("_") and k != "id"})
    filled = client.get(f"/api/applications/{b['id']}/completeness").json()
    assert empty["percent"] <= 5
    assert any(i["status"] == "missing" for i in empty["items"])
    # no topic chosen yet -> no stair-specific professional stop (it must not be assumed from a default)
    assert not any(f["stop"] for f in empty["professional_flags"])
    stair = mk({"variance": {"topic": "single_exit_stair"}})
    stair_c = client.get(f"/api/applications/{stair['id']}/completeness").json()
    assert any(f["stop"] for f in stair_c["professional_flags"])
    assert any(i["status"] == "needs_professional" for i in stair_c["items"])
    assert filled["percent"] >= empty["percent"]


def test_filled_application_is_complete_ish():
    body = {
        "applicant": {"owner_name": "O", "mailing_address": "1 St", "email": "o@x.ca", "date_of_request": "2026-01-01"},
        "location": {"municipal_address": "1 St, Edmonton"},
        "project": {"description": "d", "occupancy": "Group C", "storeys": 4, "building_area_m2": 500,
                    "units_per_floor": 4, "sprinklered": True, "part": "3"},
        "variance": {"code_or_standard": "NBC(AE) 2023", "acceptable_solution": {"articles": ["3.4.2.1"], "explanation": "e"},
                     "proposed_alternative": {"summary": "s", "mitigations": [{"id": "m1", "label": "L", "detail": "d", "evidence_ids": ["d1"]}]}},
        "section_d": [{"id": "d1", "document_name": "Report", "responsible_party": "FPE", "professional_required": True, "status": "to_be_prepared"}],
    }
    a = mk(body)
    c = client.get(f"/api/applications/{a['id']}/completeness").json()
    st = {i["id"]: i["status"] for i in c["items"]}
    assert st["A.owner_name"] == "complete" and st["D.doc.0"] == "needs_professional"
    assert st["SIGN.owner_signed"] == "missing"  # never set by us
    m = client.get(f"/api/applications/{a['id']}/map").json()
    assert m["nodes"][0]["id"] == "root" and any(n["id"] == "sec.C" for n in m["nodes"])
    ids = {n["id"] for n in m["nodes"]}
    assert all(e["source"] in ids and e["target"] in ids for e in m["edges"])


def test_submission_blocked_when_unsigned():
    a = mk()
    r = client.post(f"/api/applications/{a['id']}/submission-package")
    assert r.status_code == 409
    client.patch(f"/api/applications/{a['id']}", json={"applicant": {"owner_representative": "Rep"},
                                                       "declarations": {"owner_signed": True}})
    r = client.post(f"/api/applications/{a['id']}/submission-package")
    assert r.status_code == 409 and "rep_signed" in r.text


def test_backend_never_sets_declarations():
    a = mk()
    client.post(f"/api/applications/{a['id']}/section-c/generate")
    client.get(f"/api/applications/{a['id']}/completeness")
    d = client.get(f"/api/applications/{a['id']}").json()["declarations"]
    assert not any(d.values())


def test_intake_flow_never_invents():
    a = mk()
    r = client.post(f"/api/applications/{a['id']}/intake/next", json={}).json()
    assert r["question"] and r["extracted"] == {}
    q = r["question"]
    r2 = client.post(f"/api/applications/{a['id']}/intake/next", json={"question_id": q["id"], "answer": "Jane Doe"}).json()
    assert r2["extracted"] and r2["confidence"] > 0 and r2["question"]["id"] != q["id"]
    app_ = client.get(f"/api/applications/{a['id']}").json()
    assert app_["provenance"][q["field_path"]]["source"] == "applicant"
    # unparseable numeric answer is not stored
    nq = {"id": "x"}
    num = next(q for q in main.questions() if q["type"] == "number")
    bad = client.post(f"/api/applications/{a['id']}/intake/next", json={"question_id": num["id"], "answer": "lots"}).json()
    assert bad["extracted"] == {} and bad["question"]["id"] == num["id"]


def test_section_c_rows_flagged_when_unverified_or_unresolved():
    a = mk()
    r = client.post(f"/api/applications/{a['id']}/section-c/generate").json()
    assert r["section_c"]
    for row in r["section_c"]:
        assert row["provenance"] == "lookup"
        if row["objective"] == "unresolved":
            assert row["verified"] is False


def test_reviewer_summary_and_rfi():
    a = mk()
    s = client.get(f"/api/applications/{a['id']}/reviewer-summary").json()
    assert s["word_count"] <= 120 and "safety" in s["summary"].lower()
    r = client.post(f"/api/applications/{a['id']}/rfi-draft").json()
    assert r["status"] == "DRAFT" and "DRAFT" in r["body"]


def test_samples_endpoints():
    lst = client.get("/api/samples").json()
    names = {s["name"] for s in lst}
    # real-derived applications are listed; the shape-only template and the ground-truth file are not
    assert "good_stair_edmonton" in names
    assert "application.example" not in names and "seeded_defects" not in names
    assert client.get("/api/samples/good_stair_edmonton").status_code == 200
    assert client.get("/api/samples/application.example").status_code == 200  # still fetchable by name
    assert client.get("/api/samples/nope").status_code == 404


def _corpus():
    try:
        import corpus.verifier as v
        return v
    except Exception:
        return None


@pytest.mark.skipif(_corpus() is None, reason="corpus stream not present yet")
def test_citations_verify_real_article():
    r = client.get("/api/citations/verify", params={"article": "3.4.2.1"}).json()
    assert r["exists"] is True and not r["unresolved"]
    bad = client.get("/api/citations/verify", params={"article": "3.99.99.99"}).json()
    assert bad["exists"] is False


def test_citations_verify_shape():
    r = client.get("/api/citations/verify", params={"article": "3.4.2.1"}).json()
    assert {"exists", "edition", "page", "text_excerpt"} <= set(r)


def test_section_c_real_lookup():
    a = mk({"project": {"occupancy": "Group C", "storeys": 6, "building_area_m2": 900}})
    r = client.post(f"/api/applications/{a['id']}/section-c/generate").json()
    rows = {x["article"]: x for x in r["section_c"]}
    assert "3.4.2.1" in rows and not any(x.startswith("9.") for x in rows)
    row = rows["3.4.2.1"]
    assert row["verified"] is True and "OS3.7" in row["objective"] and "F10" in row["function"]
    assert row["intent_edition"] == "NBC 2020 Intent Supplement" and row["intent"] != "unresolved"
    assert row["source"]["doc"] == "NBC_2023AE_2nd_printing.pdf" and row["source"]["page"] == 269
    assert r["unresolved"] == [] or all(rows[u]["verified"] is False or rows[u]["objective"] == "unresolved" for u in r["unresolved"])


def test_citation_verify_real_and_fake():
    r = client.get("/api/citations/verify", params={"article": "3.4.2.1"}).json()
    assert r["exists"] is True and r["page"] == 269 and r["edition"] == "NBC(AE) 2023 2nd printing"
    assert "at least 2 exits" in r["text_excerpt"]
    assert client.get("/api/citations/verify", params={"article": "3.99.99.99"}).json()["exists"] is False


def test_similar_standata():
    a = mk({"project": {"description": "single egress stair"}})
    r = client.get(f"/api/applications/{a['id']}/similar-standata").json()
    assert r["results"] and all(x["doc"].lower().startswith("standata") for x in r["results"])


def test_submission_package_gate_on_real_sample():
    """Real-derived sample: blocked until the USER attests the signature; a placeholder representative is not a name."""
    body = client.get("/api/samples/good_stair_edmonton").json()
    aid = client.post("/api/applications", json=body).json()["id"]
    assert client.post(f"/api/applications/{aid}/submission-package", json={}).status_code == 409
    assert client.get(f"/api/applications/{aid}").json()["declarations"]["owner_signed"] is False  # never set by us
    assert client.patch(f"/api/applications/{aid}", json={"declarations": {"owner_signed": True}}).status_code == 200
    r = client.post(f"/api/applications/{aid}/submission-package", json={})
    assert r.status_code == 200 and r.headers["content-type"] == "application/zip"
