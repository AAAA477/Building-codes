import sys
from pathlib import Path
import pymupdf
from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
import main  # noqa: E402
import overlays  # noqa: E402

client = TestClient(main.app)
PREVIEW = BACKEND.parent / "data" / "forms" / "preview"


def mk(body=None):
    r = client.post("/api/applications", json={"sample": "good_stair_edmonton", **(body or {})})
    assert r.status_code == 200, r.text
    return r.json()


def ov(a):
    return client.get(f"/api/applications/{a['id']}/overlay").json()


def ids(a):
    return {i["id"]: i for i in overlays.items(a)}


def test_edmonton_overlay_questions_and_preapp():
    a = mk()
    j = ov(a)
    assert j["jurisdiction"] == "edmonton"
    qids = [q["id"] for q in j["questions"]]
    assert qids[:1] == ["PREAPP"] and all(f"ES{i}" in qids for i in range(1, 5))
    assert all(q["options"] == ["yes", "no", "unsure"] and q["source"]["page"] for q in j["questions"])
    assert "No separate Edmonton variance form" in j["note"]
    for s in j["sections"]:
        for c in s["checks"]:
            assert c["source"]["doc"] and c["source"]["page"]


def test_answer_yes_is_uncertain_and_persisted():
    a = mk()
    r = client.post(f"/api/applications/{a['id']}/overlay/answer", json={"question_id": "ES2", "answer": "yes"})
    assert r.status_code == 200
    q = [q for q in r.json()["questions"] if q["id"] == "ES2"][0]
    assert q["answer"] == "yes"
    got = client.get(f"/api/applications/{a['id']}").json()
    assert got["overlay"]["answers"]["ES2"] == "yes"
    it = [i for i in got["completeness"]["items"] if i["id"] == "OV.edmonton.ES2"][0]
    assert it["status"] == "uncertain" and "documentation" in it["message"]
    assert client.post(f"/api/applications/{a['id']}/overlay/answer", json={"question_id": "ES2", "answer": "maybe"}).status_code == 422
    assert client.post(f"/api/applications/{a['id']}/overlay/answer", json={"question_id": "NOPE", "answer": "no"}).status_code == 422


def test_unanswered_not_missing():
    a = mk()
    it = ids(a)
    for q in ("ES1", "ES2", "ES3", "ES4", "BOUNDARY", "PREAPP"):
        assert it[f"OV.edmonton.{q}"]["status"] == "uncertain"


def test_function_trigger_changes_with_section_c():
    a = mk()
    for r in a["variance"]["section_c"]:
        r["function"] = "F10: To facilitate the timely movement of persons to a safe place in an emergency"
    a["overlay"] = {"answers": {q: "no" for q in ("ES1", "ES2", "ES3", "ES4")}}
    it = ids(a)
    assert it["OV.edmonton.FSTMT"]["status"] == "complete"
    assert "OV.edmonton.FIREFLOW" not in it
    a["variance"]["section_c"][0]["function"] = "F12: To facilitate emergency response"
    it = ids(a)
    assert it["OV.edmonton.FSTMT"]["status"] == "uncertain"
    assert it["OV.edmonton.FIREFLOW"]["status"] == "missing"
    assert it["OV.edmonton.ITM"]["status"] in ("missing", "needs_professional")


def test_calgary_permit_missing_and_filled():
    a = mk({"jurisdiction": "calgary", "location": {"permit_number": ""}})
    assert ids(a)["OV.calgary.PERMIT"]["status"] == "missing"
    assert ov(a)["jurisdiction"] == "calgary"
    a2 = mk({"jurisdiction": "calgary", "location": {"permit_number": "BP-TEST-1"}})
    assert ids(a2)["OV.calgary.PERMIT"]["status"] == "complete"
    assert ids(a2)["OV.calgary.ONEISSUE"]["status"] == "uncertain"


def test_calgary_pdf_export(tmp_path):
    a = mk({"jurisdiction": "calgary", "location": {"permit_number": "BP-TEST-1"}})
    r = client.get(f"/api/applications/{a['id']}/export/calgary-pdf")
    assert r.status_code == 200 and r.content[:4] == b"%PDF"
    f = tmp_path / "c.pdf"
    f.write_bytes(r.content)
    doc = pymupdf.open(f)
    w = {x.field_name: x.field_value for p in doc for x in p.widgets()}
    assert w["Permit Number"] == "BP-TEST-1"
    assert not w.get("Variance Number office use only")
    PREVIEW.mkdir(parents=True, exist_ok=True)
    doc[0].get_pixmap(dpi=90).save(str(PREVIEW / "calgary_overlay_p1.png"))
    b = mk({"jurisdiction": "calgary", "location": {"permit_number": ""}})
    r = client.get(f"/api/applications/{b['id']}/export/calgary-pdf")
    f.write_bytes(r.content)
    w = {x.field_name: x.field_value for p in pymupdf.open(f) for x in p.widgets()}
    assert w["Permit Number"] == "[not provided]"


def test_brief_no_placeholders_as_facts():
    for jur in ("edmonton", "calgary", "scc"):
        a = mk({"jurisdiction": jur})
        r = client.get(f"/api/applications/{a['id']}/pre-application-brief")
        assert r.status_code == 200
        t = r.json()["text"]
        assert "to be completed" not in t.lower() and "to be described" not in t.lower() and "not provided yet" in t
        if jur != "scc":
            assert "QUESTIONS TO ASK" in t and "source:" in t
