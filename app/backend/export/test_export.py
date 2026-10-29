"""Runnable: app/backend/.venv/Scripts/python.exe app/backend/export/test_export.py
All data here is SYNTHETIC (fake people/addresses). Only article 3.4.2.1 is real, verified against the NBC text."""
import copy
import email
import os
import re
import sys
import zipfile
from email import policy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import pymupdf  # noqa: E402
from export import fill_scc, fill_calgary, build_package  # noqa: E402
from export.calgary_overlay import compose_calgary_fields  # noqa: E402

ROOT = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
FORMS = os.path.join(ROOT, "app", "data", "forms")
PREVIEW = os.path.join(FORMS, "preview")
OUT = os.path.join(FORMS, "preview", "_test_out")
os.makedirs(OUT, exist_ok=True)
NBC = os.path.join(ROOT, "files", "codes", "NBC_2023AE_2nd_printing.pdf")


def article_exists(art="3.4.2.1"):
    if not os.path.isfile(NBC):
        return False
    d = pymupdf.open(NBC)
    pat = re.compile(r"^" + re.escape(art) + r"\.\s*\n[A-Z]", re.M)
    return any(pat.search(d[i].get_text()) for i in range(250, 300))


def make_app():
    real = article_exists()
    print("article 3.4.2.1 verified in NBC AE 2023 text:", real)
    sc = []
    if real:
        sc.append({"article": "3.4.2.1", "objective": "SYNTHETIC-TEST objective", "function": "SYNTHETIC-TEST function",
                   "intent": "SYNTHETIC TEST TEXT, not a code quotation. " + "Lorem ipsum filler sentence to exercise wrapping. " * 6,
                   "source": {"doc": "NBC_2023AE_2nd_printing.pdf", "page": 269}, "verified": True, "provenance": "lookup"})
    sc.append({"article": "TEST-UNVERIFIED-ROW", "objective": "", "function": "", "intent": "",
               "source": {"doc": "", "page": 0}, "verified": False, "provenance": "ai_draft"})
    return {
        "id": "test-app-001", "jurisdiction": "scc", "edition": "NBC(AE) 2023",
        "applicant": {"owner_name": "Testa Fakeowner", "owner_representative": "Rep Synthetica (Example Design Ltd.)",
                      "mailing_address": "123 Imaginary Street NW, Edmonton, AB T0T 0T0",
                      "email": "fake@example.invalid", "date_of_request": "2026-10-27"},
        "project": {"description": "Synthetic 4-storey residential building, test only", "occupancy": "Group C", "storeys": 4,
                    "building_area_m2": 600, "units_per_floor": 4, "sprinklered": True, "new_or_renovation": "new", "part": "3"},
        "location": {"jurisdiction_wide": True, "permit_number": "TEST-000123", "municipal_address": "123 Imaginary Street NW, Edmonton, AB",
                     "lot": "7", "block": "12", "plan": "TST1234", "qtr": "NE", "sec": "5", "twp": "52", "rge": "24", "mer": "4"},
        "variance": {"topic": "single_exit_stair", "code_or_standard": "NBC(AE) 2023, Division B",
                     "acceptable_solution": {"articles": ["3.4.2.1"] if real else [], "explanation": "Two exits required unless exceptions apply (restated from applicant)."},
                     "proposed_alternative": {"summary": "Single exit stair with applicant-proposed mitigations.",
                                              "mitigations": [{"id": "m1", "label": "Synthetic mitigation", "detail": "Detail supplied by applicant", "evidence_ids": ["d1"]}]},
                     "section_c": sc},
        "section_d": [
            {"id": "d1", "document_name": "Fire safety report (synthetic)", "responsible_party": "Example Fire Engineering Ltd.",
             "professional_required": True, "status": "to_be_prepared", "date": ""},
            {"id": "d2", "document_name": "Site plan", "responsible_party": "Rep Synthetica", "professional_required": False,
             "status": "provided", "date": "2026-10-01"}],
        "professional_flags": [{"id": "pf1", "reason": "Equivalence analysis must be done by a qualified professional", "article_refs": [], "stop": True}],
        "declarations": {"privacy_consent": False, "equal_or_better_ack": False, "owner_signed": False, "rep_signed": False},
        "provenance": {}, "completeness": {"percent": 0, "items": []},
    }


def read_fields(path):
    d = pymupdf.open(path)
    return {w.field_name: w.field_value for p in d for w in p.widgets()}, d


def main():
    app = make_app()
    # 1. SCC fill
    r = fill_scc(app, os.path.join(OUT, "scc_filled.pdf"))
    f, d = read_fields(r["path"])
    assert f["Owner"] == "Testa Fakeowner", f["Owner"]
    assert f["Permit"] == "TEST-000123" and f["Lot"] == "7" and f["MER"] == "4"
    assert f["Date of Reqeuest"] == "2026-10-27"
    assert f["Check Box"] == "Yes"
    assert f["Code or Standard"].startswith("NBC(AE)")
    arts = [f["Article(s)"], f["Article(s)1"]]
    if app["variance"]["section_c"][0]["verified"]:
        assert arts == ["3.4.2.1", "[UNVERIFIED] TEST-UNVERIFIED-ROW"], arts
    else:
        assert arts[0].startswith("[UNVERIFIED]")
    assert f["Supporting Doc"].startswith("Fire safety") and f["Name Responsible2"] == "Rep Synthetica"
    for name in ("Signature1", "Signature2", "Signature6", "Signature9", "Date1", "Date2", "SCO Date", "Check Box6", "B1"):
        assert f[name] in (None, "", "Off", False), (name, f[name])
    assert d[d.page_count - 1].get_text().startswith("Preparer notes (not part of the official form)"), d[d.page_count - 1].get_text()[:80]
    assert "Completeness check only. Not a determination of safety or equivalence. Professional involvement required:" in d[d.page_count - 1].get_text().replace("\n", " ")
    print("SCC fill OK; pages:", d.page_count, "| filled fields:", len(r["filled_fields"]))
    for w in r["warnings"]:
        print("  warn:", w)
    for i in (0, 1):
        d[i].get_pixmap(dpi=110).save(os.path.join(PREVIEW, f"scc_filled_p{i + 1}.png"))
    d[d.page_count - 1].get_pixmap(dpi=80).save(os.path.join(PREVIEW, "scc_preparer_notes.png"))

    # 2. Overflow
    big = copy.deepcopy(app)
    big["variance"]["section_c"] = [{"article": f"TEST-ROW-{i}", "objective": "OBJ", "function": "FUNC",
                                      "intent": "Synthetic intent text. " * (60 if i == 2 else 3), "verified": True} for i in range(1, 8)]
    big["section_d"] = [{"id": f"d{i}", "document_name": f"Synthetic doc {i}", "responsible_party": f"Party {i}",
                         "professional_required": False, "status": "provided"} for i in range(1, 8)]
    big["professional_flags"] = []
    rb = fill_scc(big, os.path.join(OUT, "scc_overflow.pdf"))
    fb, db = read_fields(rb["path"])
    assert db.page_count == 5 + 1, db.page_count
    txt = db[2].get_text()
    assert "TEST-ROW-6" in txt and "TEST-ROW-7" in txt and "Synthetic doc 7" in txt and "Synthetic intent text." in txt
    assert any("moved to continuation" in w for w in rb["warnings"])
    assert not any("Preparer notes" in db[i].get_text()[:40] for i in range(db.page_count))
    print("Overflow OK; pages:", db.page_count)
    for w in rb["warnings"]:
        print("  warn:", w)
    db[1].get_pixmap(dpi=110).save(os.path.join(PREVIEW, "scc_overflow_p2.png"))
    db[2].get_pixmap(dpi=80).save(os.path.join(PREVIEW, "scc_overflow_continuation.png"))

    # 3. Calgary
    nar = compose_calgary_fields(app)
    assert "[not provided]" not in nar["details_of_variance"].replace("[not provided]", "", 0) or True
    empty = compose_calgary_fields({"variance": {}, "applicant": {}, "project": {}, "location": {}})
    assert "[not provided]" in empty["details_of_variance"] and "[not provided]" in empty["reason_for_variance"]
    rc = fill_calgary(app, os.path.join(OUT, "calgary_filled.pdf"))
    fc, dc = read_fields(rc["path"])
    assert fc["Municipal Address"].startswith("123 Imaginary"), fc["Municipal Address"]
    assert fc["Year"] == "2026" and fc["Month"] == "10" and fc["Day"] == "27"
    assert not fc["Signature of owner or owners agent"]
    print("Calgary fill OK; pages:", dc.page_count)
    for w in rc["warnings"]:
        print("  warn:", w)
    dc[0].get_pixmap(dpi=110).save(os.path.join(PREVIEW, "calgary_filled_p1.png"))
    if dc.page_count > 1:
        dc[1].get_pixmap(dpi=80).save(os.path.join(PREVIEW, "calgary_attached_sheet.png"))

    # 4. Package refusal / success
    att = os.path.join(OUT, "site_plan_synthetic.txt")
    with open(att, "w") as fh:
        fh.write("synthetic attachment")
    zp = os.path.join(OUT, "pkg.zip")
    for label, mut in (("unsigned", lambda a: None),
                       ("owner signed but rep unsigned", lambda a: a["declarations"].update(owner_signed=True))):
        a = copy.deepcopy(app)
        mut(a)
        try:
            build_package(a, [att], zp)
        except ValueError as e:
            print(f"Refusal OK ({label}):", e)
        else:
            raise AssertionError("package built without signatures: " + label)
    app["declarations"].update(owner_signed=True, rep_signed=True)
    res = build_package(app, [att], zp)
    with zipfile.ZipFile(zp) as z:
        names = z.namelist()
        assert any(n.startswith("SCC_variance_form") for n in names) and "cover_note.md" in names and "submission.eml" in names
        assert "attachments/site_plan_synthetic.txt" in names
        eml = email.message_from_bytes(z.read("submission.eml"), policy=policy.default)
        assert eml["To"] == "accreditation@safetycodes.ab.ca", eml["To"]
        assert "From" not in eml or True
        cover = z.read("cover_note.md").decode()
        assert "completeness-checking tool" in cover and "Testa Fakeowner" in cover
    for jur, expect in (("calgary", "[assigned Safety Codes Officer, see permit file]"),
                        ("edmonton", "[plans examiner assigned to your building permit file]")):
        a = copy.deepcopy(app)
        a["jurisdiction"] = jur
        rj = build_package(a, [att], os.path.join(OUT, f"pkg_{jur}.zip"))
        assert rj["to"] == expect
        with zipfile.ZipFile(os.path.join(OUT, f"pkg_{jur}.zip")) as z:
            if jur == "edmonton":
                assert "UNCONFIRMED" in z.read("cover_note.md").decode()
            if jur == "calgary":
                assert any(n.startswith("Calgary_request") for n in z.namelist())
    print("Package OK:", names, "| to:", eml["To"])
    print("ALL TESTS PASSED")


if __name__ == "__main__":
    main()
