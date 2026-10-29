import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402

client = TestClient(app)
S = os.path.join(HERE, "..", "..", "data", "samples")
NAMES = ["flawed_missing_section_d", "flawed_no_professional", "flawed_unverified_citation", "good_stair_edmonton",
         "partial_intake", "standata_23_bcv_001_wocd", "standata_23_bcv_004_sprinkler_glazing",
         "standata_23_bcv_008r1_exhaust_clearance"]
LOOKUP = NAMES[5:]


def run(name):
    body = json.load(open(os.path.join(S, name + ".json"), encoding="utf8"))
    i = client.post("/api/applications", json=body).json()["id"]
    g = lambda p: client.get(f"/api/applications/{i}/{p}").json()
    return i, g("completeness"), g("reviewer-summary"), client.post(f"/api/applications/{i}/rfi-draft").json()


def test_shapes_and_no_leaks():
    for n in NAMES:
        i, c, s, r = run(n)
        assert all("group" in it and 1 <= it["priority"] <= 5 for it in c["items"])
        assert {"admin", "technical"} <= set(c["meters"]) and "signatures" in c
        assert s["word_count"] <= 80 and s["headline"] and "top_issues" in s
        for txt in (s["summary"], r["body"], r["subject"]):
            assert "[" not in txt and i not in txt, (n, txt)
        assert r["status"] == "DRAFT" and r["body"].startswith("DRAFT")
        assert "Dear applicant," in r["body"]
        assert "Main gaps: Owner name" not in s["summary"]


def test_missing_section_d_leads_with_documents():
    _, c, s, r = run("flawed_missing_section_d")
    assert c["top_issues"][0]["id"] == "D.documents"
    assert "supporting documents are missing" in s["summary"].lower()
    assert "Supporting documents and professional" in r["groups"]


def test_unverified_citation_names_article():
    _, c, s, r = run("flawed_unverified_citation")
    assert "3.4.2.9" in c["top_issues"][0]["label"] and c["top_issues"][0]["group"] == "citations"
    assert "3.4.2.9" in s["summary"]
    assert any("3.4.2.9" in x["text"] and "NBC(AE) 2023" in x["text"] for x in r["items"])
    assert r["groups"][0] == "Code articles and citations"


def test_no_professional_top_issue():
    _, c, s, r = run("flawed_no_professional")
    assert any(t["id"] == "D.professional_named" or t["group"] in ("professional", "documents")
               for t in c["top_issues"])


def test_professional_wording_follows_flag():
    for n in LOOKUP:
        _, c, s, r = run(n)
        blob = json.dumps([c, s, r]).replace("whether a registered professional is required", "")
        assert "A registered professional is required" not in blob, n
    _, c, s, r = run("good_stair_edmonton")
    assert "A registered professional is required (Edmonton PAB guide p.8)" in json.dumps(c)


def test_good_sample_top_not_admin():
    _, c, s, r = run("good_stair_edmonton")
    assert c["top_issues"][0]["group"] != "admin"


def test_short_headline_and_severity():
    for n in NAMES:
        _, c, s, r = run(n)
        assert len(c["headline"].split()) <= 16 and len(s["summary"].split()) <= 100
        assert "STOP" not in json.dumps(c)
        assert all(it["severity"] in ("blocker", "confirm") for it in c["items"])
        assert all(t["severity"] in ("blocker", "confirm") for t in c["top_issues"])
        nb = sum(1 for it in c["items"] if it["status"] != "complete" and it["severity"] == "blocker")
        assert (f"{nb} blocker" in c["headline"]) if nb else ("Not ready" not in c["headline"])
    _, c, _, _ = run("flawed_missing_section_d")
    assert c["headline"].startswith("Not ready")


def test_summary_does_not_repeat_headline():
    for n in NAMES:
        _, c, s, r = run(n)
        assert not s["summary"].startswith(s["headline"].split(":")[0])
        assert s["summary"].count("technical checks") <= 1
