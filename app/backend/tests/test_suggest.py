import sys
from pathlib import Path
from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
import main  # noqa: E402
import suggest  # noqa: E402
from llm import OfflineLLM  # noqa: E402

client = TestClient(main.app)
TXT = "We propose a 6 storey apartment building, not sprinklered, with 4 units per floor and a building area of 1,250 m2. New construction."


class Fake:
    name = "azure-openai"

    def __init__(self, text=None, js=None):
        self.text, self.js = text, js

    def chat_text(self, p):
        return self.text

    def chat_json(self, p, h=""):
        return self.js


def mk(sample="good_stair_edmonton"):
    return client.post("/api/applications", json={"sample": sample}).json()


def test_regex_facts_literal():
    f, dropped, mode = suggest.extract_facts(TXT, OfflineLLM())
    assert mode == "offline"
    assert f["storeys"]["value"] == 6 and f["building_area_m2"]["value"] == 1250
    assert f["units_per_floor"]["value"] == 4 and f["sprinklered"]["value"] is False
    assert f["new_or_renovation"]["value"] == "new"


def test_unstated_fact_dropped():
    f, dropped, _ = suggest.extract_facts("A building near the river.", OfflineLLM())
    assert f == {}


def test_llm_invented_fact_dropped():
    js = {"storeys": {"value": 9, "quote": "9 storey"}, "sprinklered": {"value": True, "quote": "sprinklered"}}
    f, dropped, _ = suggest.extract_facts("A building near the river.", Fake(js=js))
    assert f == {} and len(dropped) == 2


def test_check_text_flags():
    app = {"project": {"storeys": 5}}
    assert not suggest.checks_ok(suggest.check_text("It has 7 storeys.", "5 storeys", app))
    assert suggest.check_text("See NBC 3.4.2.9.", "5 storeys", app)["citations_verified"] is False
    assert suggest.check_text("This design is safe.", "x", app)["claims_safety"]
    assert suggest.checks_ok(suggest.check_text("Five storeys.", "5 storeys", app))


def test_improve_rejects_after_one_retry():
    calls = []

    class L(Fake):
        def chat_text(self, p):
            calls.append(p)
            return "This design is safe with 11 storeys."
    r = suggest.do_improve_text({"project": {}}, "A 5 storey building.", None, L())
    it = r["items"][0]
    assert it["status"] == "rejected" and it["value"] is None and len(calls) == 2


def test_improve_regenerates_then_passes():
    outs = iter(["Has 99 storeys.", "A 5 storey building."])

    class L(Fake):
        def chat_text(self, p):
            return next(outs)
    it = suggest.do_improve_text({"project": {}}, "A 5 storey building.", None, L())["items"][0]
    assert it["status"] == "ready" and it["attempts"] == 2


def test_endpoints_and_accept():
    a = mk()
    for k in ("extract_facts", "missing_info", "mitigations", "similar_precedents", "improve_text"):
        r = client.post(f"/api/applications/{a['id']}/suggest", json={"kind": k, "text": TXT})
        assert r.status_code == 200, r.text
        j = r.json()
        assert j["disclaimer"].startswith("AI suggestions are drafts") and j["kind"] == k
        for it in j["items"]:
            assert it["status"] in ("ready", "needs_review", "rejected") and "checks" in it
    assert client.post(f"/api/applications/{a['id']}/suggest", json={"kind": "bogus"}).status_code == 422
    r = client.post(f"/api/applications/{a['id']}/suggest/accept", json={"field_path": "project.storeys", "value": 6})
    assert r.status_code == 200 and r.json()["provenance"]["project.storeys"]["source"] == "ai_draft"
    for p in ("declarations.owner_signed", "professional_flags", "declarations.privacy_consent"):
        assert client.post(f"/api/applications/{a['id']}/suggest/accept", json={"field_path": p, "value": True}).status_code == 409


def test_mitigations_from_catalogue_only():
    a = mk()
    j = client.post(f"/api/applications/{a['id']}/suggest", json={"kind": "mitigations"}).json()
    opts = [i for i in j["items"] if i["id"].startswith("opt-MIT")]
    assert opts, "catalogue options expected for the stair sample"
    for i in opts:
        for s in i["sources"]:
            if s["quote"]:
                assert suggest.quote_is_real(s["doc"], s["page"], s["quote"])
