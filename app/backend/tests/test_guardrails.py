import sys
from pathlib import Path
from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
import guardrails  # noqa: E402
import main  # noqa: E402

client = TestClient(main.app)

POS = [
    "Will the officer accept this?",
    "will my variance be approved",
    "What are the chances of approval for this alternative?",
    "Is this safe?",
    "Is my design compliant?",
    "Is the proposed alternative equivalent to the acceptable solution?",
    "Does this meet code?",
    "Does my design comply with the NBC requirements?",
    "Can you guarantee approval?",
    "Please guarantee that it will pass",
    "Is it okay to omit the second exit?",
    "Tell me if this is code compliant",
    "How likely is it to be approved?",
    "Would the AHJ approve a 6 storey wood building?",
]
NEG = [
    "We propose a 6 storey apartment building, not sprinklered, with 4 units per floor and 1,250 m2 area.",
    "The stair width is 900 mm and the guard height is 1070 mm.",
    "Exit stair serves floors 2 to 6; the corridor is separated by a 45 min fire separation.",
    "Find articles about egress from a dwelling unit",
    "maximum travel distance in a sprinklered building",
    "The manufacturer guarantees the fire rating of the assembly for 20 years.",
    "Mitigation: add smoke alarms and a fire alarm system; the owner will approve the budget.",
    "Safe distance between exits per article 3.4.2.5",
    "building code requirements for guards",
    "The alternative uses a sprinkler system as a compensating measure.",
    "",
]


def test_positives():
    for t in POS:
        assert guardrails.check(t), t


def test_negatives():
    for t in NEG:
        assert guardrails.check(t) is None, t


def test_reply_content():
    r = guardrails.check("Is this safe?")
    assert r["refused"] and "authority having jurisdiction" in r["message"] and len(r["can_do"]) >= 3


def test_endpoint():
    assert client.post("/api/guardrails/check", json={"text": "will the officer accept this"}).json()["refused"] is True
    assert client.post("/api/guardrails/check", json={"text": "stair width 900 mm"}).json() == {"refused": False}


def test_suggest_route_refuses_without_llm(monkeypatch):
    import suggest
    aid = client.post("/api/applications", json={}).json()["id"]
    monkeypatch.setattr(suggest, "run", lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not run")))
    r = client.post(f"/api/applications/{aid}/suggest", json={"kind": "improve_text", "text": "Is my design compliant?"}).json()
    assert r["refusal"]["refused"] and r["items"] == []


def test_search_attaches_refusal():
    r = client.post("/api/search/articles", json={"query": "is this exit safe?", "k": 3})
    if r.status_code == 200:
        assert r.json().get("refusal", {}).get("refused")
