import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
from corpus import build_variance_cards as B  # noqa: E402

REPO = BACKEND.parents[1]
INDEX = json.load(open(REPO / "app" / "data" / "content" / "standata_index.json", encoding="utf8"))
VARIANCES = [i for i in INDEX["items"] if i["kind"] == "variance"]
CARDS_DIR = REPO / "app" / "data" / "content" / "variance_cards"


def cards():
    return [json.load(open(p, encoding="utf8")) for p in sorted(CARDS_DIR.glob("*.json")) if not p.name.startswith("_")]


def test_wocd_card_fields():
    rel = "files/standata/variances_2023/ma-standata-variance-building-23-bcv-001-2024-04.pdf"
    c = B.parse_variance_file(REPO / rel, [i for i in VARIANCES if i["file_path"] == rel][0])
    assert c["number"] == "23-BCV-001" and c["edition"] == "NBC(AE) 2023"
    assert "9.8.8.1" in " ".join(c["articles_varied"])
    assert any("not permitted for use in adaptable or barrier-free dwelling units" in x["text"] for x in c["conditions"])
    assert all(x["page"] >= 1 for x in c["conditions"])


def test_conditions_are_verbatim():
    assert cards()
    for c in cards():
        src = B.normalise("\n".join(B.read_pdf_pages(REPO / c["pdf"])))
        for x in c["conditions"]:
            assert B.normalise(x["text"]) in src, (c["id"], x["text"][:60])
        for part in c["variance_parts"]:
            assert B.normalise(part) in src, c["id"]


def test_all_2023_variances_have_verified_cards():
    by_pdf = {c["pdf"]: c for c in cards()}
    wanted = [i for i in VARIANCES if i["edition"] == "NBC(AE) 2023"]
    assert len(wanted) == 19
    for i in wanted:
        c = by_pdf.get(i["file_path"])
        assert c is not None, i["file_path"]
        assert c["needs_review"] is False, (c["id"], c.get("review_reasons"))
        assert c["articles_unverified"] == [], (c["id"], c["articles_unverified"])


def test_joint_variance_is_one_card():
    joint = [c for c in cards() if "19-BCV-014" in c["numbers"]]
    assert joint and all("19-FCV-019" in c["numbers"] for c in joint)
    assert len({c["pdf"] for c in joint}) == len(joint)


def test_latest_revision_is_current():
    r = {c["pdf"].split("/")[-1]: c for c in cards()}
    old = r["ma-standata-variance-building-23-bcv-008-2024-06.pdf"]
    new = r["ma-standata-variance-building-23-bcv-008-rev1-2024-10.pdf"]
    assert new["current"] is True and old["current"] is False and old["superseded_by"] == new["id"]


def test_report_counts_match_index():
    rep = json.load(open(CARDS_DIR / "_report.json", encoding="utf8"))
    assert rep["total"] == len(VARIANCES) == len(cards())
    assert rep["by_edition"]["NBC(AE) 2023"] == 19
