import io
import sys
import zipfile
from pathlib import Path

import pymupdf
from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
import main  # noqa: E402
import evidence  # noqa: E402

client = TestClient(main.app)


def text_pdf(pages=2, extra=""):
    d = pymupdf.open()
    for i in range(pages):
        p = d.new_page()
        p.insert_text((72, 72), "Fire protection report. This page has plenty of searchable text. " + extra)
    b = d.tobytes()
    d.close()
    return b


def image_pdf():
    src = pymupdf.open()
    pg = src.new_page()
    pg.draw_rect(pymupdf.Rect(50, 50, 300, 300), fill=(0.5, 0.5, 0.5))
    pix = pg.get_pixmap()
    d = pymupdf.open()
    p = d.new_page()
    p.insert_image(p.rect, pixmap=pix)
    return d.tobytes()


def encrypted_pdf(user_pw="secret"):
    d = pymupdf.open()
    d.new_page().insert_text((72, 72), "locked text content here, long enough")
    return d.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw=user_pw, owner_pw="owner")


def restricted_pdf():
    d = pymupdf.open()
    d.new_page().insert_text((72, 72), "restricted text content here, long enough")
    return d.tobytes(encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="", owner_pw="owner", permissions=0)


def mk():
    r = client.post("/api/applications", json={"sample": "good_stair_edmonton"})
    assert r.status_code == 200, r.text
    a = r.json()
    assert a["section_d"], "sample must have Section D rows"
    return a


def up(a, doc_id, name, data, ctype="application/pdf"):
    return client.post(f"/api/applications/{a['id']}/evidence/{doc_id}", files={"file": (name, data, ctype)})


def codes(rec):
    return {(c["level"], c["code"]) for c in rec["checks"]}


def test_good_pdf_upload_list_download_delete():
    a = mk()
    d = a["section_d"][0]["id"]
    r = up(a, d, "report.pdf", text_pdf())
    assert r.status_code == 200, r.text
    rec = r.json()
    assert rec["worst"] in ("info", "warn") and "stored" not in rec
    assert not any(c["level"] == "block" for c in rec["checks"])
    lst = client.get(f"/api/applications/{a['id']}/evidence").json()["files"]
    assert [x["id"] for x in lst] == [rec["id"]]
    dl = client.get(f"/api/applications/{a['id']}/evidence/{d}/{rec['id']}")
    assert dl.status_code == 200 and dl.content.startswith(b"%PDF")
    assert client.delete(f"/api/applications/{a['id']}/evidence/{d}/{rec['id']}").status_code == 200
    assert client.get(f"/api/applications/{a['id']}/evidence/{d}").json()["files"] == []
    assert client.delete(f"/api/applications/{a['id']}/evidence/{d}/{rec['id']}").status_code == 404


def test_encrypted_and_restricted_block():
    a = mk()
    d = a["section_d"][0]["id"]
    assert ("block", "password") in codes(up(a, d, "locked.pdf", encrypted_pdf()).json())
    assert ("block", "restricted") in codes(up(a, d, "nocopy.pdf", restricted_pdf()).json())


def test_corrupt_and_type_mismatch_block():
    a = mk()
    d = a["section_d"][0]["id"]
    assert ("block", "type_mismatch") in codes(up(a, d, "x.pdf", b"not a pdf at all").json())
    assert ("block", "cannot_open") in codes(up(a, d, "y.pdf", b"%PDF-1.4\ngarbage").json())


def test_image_only_pdf_warns_no_text():
    a = mk()
    d = a["section_d"][0]["id"]
    assert ("warn", "no_text") in codes(up(a, d, "scan.pdf", image_pdf()).json())


def test_seal_never_confirmed():
    a = mk()
    pro = next((r for r in a["section_d"] if r.get("professional_required")), None)
    assert pro, "need a professional_required row"
    plain = codes(up(a, pro["id"], "letter.pdf", text_pdf()).json())
    assert ("warn", "no_seal_text") in plain
    sealed = up(a, pro["id"], "sealed.pdf", text_pdf(extra="P.Eng. Permit to Practice APEGA")).json()
    assert ("info", "seal_text_present") in codes(sealed)
    assert not any("valid seal" in c["message"] and "cannot" not in c["message"] for c in sealed["checks"])


def test_path_traversal_and_bad_ids():
    a = mk()
    d = a["section_d"][0]["id"]
    rec = up(a, d, "../../../evil.pdf", text_pdf()).json()
    assert ".." not in rec["filename"] and "/" not in rec["filename"]
    root = evidence.app_dir(a["id"]).resolve()
    assert all(root in p.resolve().parents for p in root.iterdir() if p.name != "index.json")
    assert not (BACKEND.parent / "evil.pdf").exists()
    assert up(a, "..%2F..", "a.pdf", text_pdf()).status_code in (404, 405, 422)
    assert client.get(f"/api/applications/{a['id']}/evidence/{d}/..%2Findex.json").status_code in (404, 405, 422)
    assert up({"id": "nope"}, d, "a.pdf", text_pdf()).status_code == 404
    assert up(a, "NOSUCHDOC", "a.pdf", text_pdf()).status_code == 404


def test_oversize_and_wrong_type_and_empty():
    a = mk()
    d = a["section_d"][0]["id"]
    big = b"%PDF-1.4\n" + b"0" * (evidence.MAX_BYTES + 10)
    assert up(a, d, "big.pdf", big).status_code == 413
    assert up(a, d, "run.exe", b"MZ....").status_code == 415
    assert up(a, d, "notes.txt", b"hello").status_code == 415
    assert up(a, d, "empty.pdf", b"").status_code == 422
    assert up(a, d, "plan.dwg", b"AC1027....").json()["worst"] == "warn"


def test_completeness_items_and_blocker():
    a = mk()
    rows = a["section_d"]
    tgt = rows[0]
    client.patch(f"/api/applications/{a['id']}", json={"section_d": [{**tgt, "status": "provided"}] + rows[1:]})
    c = client.get(f"/api/applications/{a['id']}/completeness").json()
    it = {i["id"]: i for i in c["items"]}
    assert it["D.evidence.0"]["status"] == "uncertain" and it["D.evidence.0"]["severity"] == "confirm"
    up(a, tgt["id"], "locked.pdf", encrypted_pdf())
    c = client.get(f"/api/applications/{a['id']}/completeness").json()
    it = {i["id"]: i for i in c["items"]}
    assert it["D.evidence.0"]["severity"] == "blocker"


def test_package_includes_evidence_with_manifest():
    a = mk()
    d = a["section_d"][0]["id"]
    up(a, d, "report.pdf", text_pdf())
    import export.package as pkg
    app = client.get(f"/api/applications/{a['id']}").json()
    app["declarations"].update(owner_signed=True)  # test fixture only; the app never ticks this
    app["applicant"]["owner_representative"] = ""
    out = BACKEND.parent / "data" / "store" / f"_test_pkg_{a['id']}.zip"
    try:
        res = pkg.build_package(app, [], str(out))
        with zipfile.ZipFile(out) as z:
            names = z.namelist()
            assert any(n.startswith("evidence/") and n.endswith("report.pdf") for n in names)
            man = z.read("evidence/MANIFEST.md").decode()
            assert "sha256" in man and "report.pdf" in man
        assert res["files"]
    finally:
        out.unlink(missing_ok=True)
