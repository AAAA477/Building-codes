import json
import sys
from pathlib import Path
import pymupdf
from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
import main  # noqa: E402
import models  # noqa: E402
from export.fill_scc import fill_scc  # noqa: E402

client = TestClient(main.app)
SAMPLES = BACKEND.parent / "data" / "samples"


def sample(name="standata_23_bcv_001_wocd"):
    return json.load(open(SAMPLES / f"{name}.json", encoding="utf8"))


def filled_pdf(tmp_path, app, edit=None):
    out = tmp_path / "form.pdf"
    fill_scc(app, str(out))
    if edit:
        doc = pymupdf.open(str(out))
        for p in doc:
            for w in p.widgets():
                if w.field_name in edit:
                    w.field_value = edit[w.field_name]
                    w.update()
        doc.saveIncr()
    return out.read_bytes()


def post_pdf(data, name="draft.pdf"):
    return client.post("/api/applications/import", files={"file": (name, data, "application/pdf")})


def post_text(text):
    return client.post("/api/applications/import", json={"text": text})


def base_app():
    a = sample()
    a["applicant"].update({"owner_name": "Jane Builder", "owner_representative": "Sam Agent", "mailing_address": "12 Main St, Calgary"})
    a["location"].update({"permit_number": "BP-12345", "municipal_address": "12 Main St"})
    return a


def test_roundtrip_filled_scc_form(tmp_path):
    a = base_app()
    r = post_pdf(filled_pdf(tmp_path, a))
    assert r.status_code == 200, r.text
    j = r.json()
    imp = j["application"]
    assert j["report"]["source"] == "form"
    assert imp["applicant"]["owner_name"] == "Jane Builder" and imp["applicant"]["owner_representative"] == "Sam Agent"
    assert imp["location"]["permit_number"] == "BP-12345"
    assert [x["article"].replace("[UNVERIFIED] ", "") for x in imp["variance"]["section_c"]] == [x["article"] for x in a["variance"]["section_c"]]
    assert all(x["verified"] for x in imp["variance"]["section_c"])
    assert imp["section_d"][0]["document_name"] == a["section_d"][0]["document_name"]
    assert "applicant.owner_name" in j["report"]["filled"]
    assert client.get(f"/api/applications/{j['id']}").status_code == 200


def test_partial_form_reports_missing_not_invented(tmp_path):
    a = models.new_application()
    a["applicant"]["owner_name"] = "Only Name"
    j = post_pdf(filled_pdf(tmp_path, a)).json()
    imp = j["application"]
    assert imp["applicant"]["owner_name"] == "Only Name"
    assert imp["variance"]["section_c"] == [] and imp["section_d"] == [] and imp["location"]["permit_number"] == ""
    items = client.get(f"/api/applications/{j['id']}/completeness").json()["items"]
    assert any(i["status"] != "provided" for i in items)


def test_declarations_never_imported_ticked(tmp_path):
    j = post_pdf(filled_pdf(tmp_path, base_app(), edit={"Date1": "2026-10-01"})).json()
    assert all(v is False for v in j["application"]["declarations"].values())
    assert "Date1" in j["report"]["declarations_seen_ticked"]


def test_text_draft_facts_must_appear_literally():
    j = post_text("We propose a 4 storey wood-frame building with a single exit stair.").json()
    p = j["application"]["project"]
    assert p["storeys"] == 4 and p["building_area_m2"] is None and p["units_per_floor"] is None
    assert j["application"]["provenance"]["project.storeys"]["source"] == "ai_draft"
    assert j["report"]["source"] == "text"


def test_unverified_citation_flagged():
    j = post_text("The alternative departs from 9.8.8.1 and also from 9.99.99.99 of the code.").json()
    assert j["report"]["unverified_citations"] == ["9.99.99.99"]
    rows = [x["article"] for x in j["application"]["variance"]["section_c"]]
    assert any("9.8.8.1" in x for x in rows) and not any("9.99.99.99" in x for x in rows)


def test_image_only_pdf_rejected_422():
    doc = pymupdf.open()
    pg = doc.new_page()
    pg.draw_rect(pymupdf.Rect(50, 50, 300, 300), fill=(0.5, 0.5, 0.5))
    r = post_pdf(doc.tobytes())
    assert r.status_code == 422 and "no readable text" in r.json()["detail"].lower()


def test_non_form_pdf_falls_back_to_text_with_warning():
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), "We want a window opening control device on a 3 storey apartment building.")
    r = post_pdf(doc.tobytes())
    assert r.status_code == 200
    j = r.json()
    assert j["report"]["source"] == "pdf_text" and j["report"]["warnings"]
    assert j["application"]["project"]["storeys"] == 3


def test_unmapped_content_is_listed(tmp_path):
    j = post_pdf(filled_pdf(tmp_path, base_app(), edit={"Agency": "City of Calgary"})).json()
    assert any(u["label"] == "Agency" and "City of Calgary" in u["text"] for u in j["report"]["unmapped"])


def test_imported_draft_gets_variance_match():
    j = post_text("We want to use window opening control devices complying with ASTM F2090 on the openable windows of a "
                  "residential building, as an alternative to guards on windows under 9.8.8.1.").json()
    m = client.get(f"/api/applications/{j['id']}/variance-match").json()
    assert any(i["number"] == "23-BCV-001" for i in m["items"])


def test_empty_text_422():
    assert post_text("   ").status_code == 422
