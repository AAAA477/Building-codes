import sys
from pathlib import Path
from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
import main  # noqa: E402
import llm as llm_mod  # noqa: E402
import privacy  # noqa: E402
import reviewer  # noqa: E402

client = TestClient(main.app)
TXT = "We propose a 6 storey apartment building, not sprinklered, with 4 units per floor and a building area of 1,250 m2."


def _boom(*a, **k):
    raise AssertionError("LLM called while AI is off")


class Boom(llm_mod.OfflineLLM):
    """Hosted-model stand-in that fails the test if used."""
    name = "azure-openai"
    chat_text = chat_json = expand_query = explain_article = extract_facts = _boom


def _new(ai=None):
    aid = client.post("/api/applications", json={}).json()["id"]
    if ai is not None:
        assert client.put(f"/api/applications/{aid}/ai-setting", json={"ai_enabled": ai}).json()["ai_enabled"] is ai
    return aid


def _fake_azure():
    seen = {}

    class Client:
        class chat:
            class completions:
                @staticmethod
                def create(**k):
                    seen["p"] = k["messages"][0]["content"]
                    raise RuntimeError("stop")
    l = llm_mod.AzureOpenAILLM.__new__(llm_mod.AzureOpenAILLM)
    l.client, l.deployment, l.last_error = Client(), "x", ""
    return l, seen


def test_setting_default_and_roundtrip():
    aid = _new()
    assert client.get(f"/api/applications/{aid}/ai-setting").json()["ai_enabled"] is True
    client.put(f"/api/applications/{aid}/ai-setting", json={"ai_enabled": False})
    assert client.get(f"/api/applications/{aid}/ai-setting").json()["ai_enabled"] is False
    assert client.put(f"/api/applications/{aid}/ai-setting", json={"ai_enabled": "x"}).status_code == 422


def test_off_never_calls_llm(monkeypatch):
    monkeypatch.setattr(llm_mod, "_llm", Boom())
    aid = _new(False)
    for kind in ("extract_facts", "improve_text", "mitigations", "missing_info", "similar_precedents"):
        r = client.post(f"/api/applications/{aid}/suggest", json={"kind": kind, "text": TXT})
        assert r.status_code == 200, (kind, r.text)
        assert r.json()["llm"] == "offline"
    assert llm_mod.get_llm().name != "azure-openai" or privacy.ai_allowed()
    client.post(f"/api/applications/{aid}/section-c/generate", json={})
    client.post(f"/api/applications/{aid}/deep-search", json={"cheap": True})
    client.post("/api/search/articles", json={"query": "guard height", "k": 3}, headers={"X-AI-Enabled": "0"})
    r = client.post(f"/api/applications/{aid}/answer", json={"answer": TXT, "question_id": "project.description"})
    assert r.status_code in (200, 404, 422)


def test_off_blocks_direct_client():
    l, seen = _fake_azure()
    with privacy.scope(False):
        assert l.chat_text("hello") is None
        assert llm_mod.get_llm().name == "offline"
    with privacy.scope(True, {"ai_enabled": False}):
        assert l.chat_text("hello") is None
    assert "p" not in seen


def test_on_sends_redacted_prompt():
    l, seen = _fake_azure()
    app = {"applicant": {"owner_name": "Jane Q Doe", "email": "jane@ex.com"},
           "location": {"municipal_address": "12 Elm Road NW"}}
    with privacy.scope(True, app):
        l.chat_text("Owner Jane Q Doe lives at 12 Elm Road NW, call 403-555-1234, jane@ex.com. 6 storey, 1,250 m2")
    p = seen["p"]
    for bad in ("Jane", "Doe", "403-555", "jane@", "Elm"):
        assert bad not in p, p
    assert "6 storey" in p and "1,250 m2" in p


def test_redact_helper():
    t = "Contact bob@site.ca or (403) 555-0199; 4521 Maple Drive SW, T2P 1J9. Article 9.10.14.2 allows 1,250.5 m2, 3 exits."
    r = privacy.redact(t)
    assert "bob@" not in r and "555" not in r and "Maple" not in r and "T2P" not in r
    assert "9.10.14.2" in r and "1,250.5 m2" in r and "3 exits" in r
    assert privacy.redact("Floor area 120 m2 and 10 storeys") == "Floor area 120 m2 and 10 storeys"
    assert "Smith" not in privacy.redact("Dana Smith asked", ["Dana Smith"])


def test_ai_fields_disclosure():
    app = {"provenance": {"project.description": {"source": "ai_draft"}, "project.storeys": {"source": "applicant"},
                          "variance.section_c.0.explainer": {"source": "ai_draft"}}}
    d = privacy.disclosure(app)
    assert d["count"] == 2 and "drafted with AI assistance" in d["statement"]
    assert privacy.disclosure({})["count"] == 0
    s = reviewer.summary(app, {"percent": 0, "meters": {}, "top_issues": [], "headline": "", "items": []})
    assert s["ai_assisted"]["count"] == 2


def test_cover_note_lists_ai_fields():
    from export import package
    app = {"id": "x", "provenance": {"project.description": {"source": "ai_draft"}}}
    note = package._cover_note(app, ["a.pdf"], "scc", "to@x", "n", [])
    assert "drafted with AI assistance and edited/accepted by the applicant: Description (project)" in note
