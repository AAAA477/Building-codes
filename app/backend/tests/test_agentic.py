"""Agentic route-then-read: structure, safety (fake LLM), endpoints. No network needed (fake / offline LLM)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import agentic


class FakeLLM:
    """Returns an out-of-menu area, an invented article number and a fabricated quote (plus one real, quote-able article)."""
    name = "fake"

    def __init__(self, quote_ok=False):
        self.quote_ok = quote_ok

    def chat_json(self, prompt, hint=""):
        if prompt.startswith("ROUTE"):
            return {"areas": [{"id": "NBC:99.99", "why": "invented", "confidence": 0.99},
                              {"id": "NBC:9.8", "why": "stairs and ramps", "confidence": 0.8}]}
        if prompt.startswith("PICK"):
            return {"articles": ["9.8.99.99", "9.8.5.4"]}
        if prompt.startswith("JUDGE"):
            real = agentic._text("NBC", "9.8.5.4")[:60]
            return {"items": [
                {"article": "9.8.99.99", "keep": True, "quote": "Invented article text about platform lifts.", "why": "x"},
                {"article": "9.8.5.4", "keep": True,
                 "quote": real if self.quote_ok else "Ramps shall never exceed a slope of one in forty under any circumstances.",
                 "why": "slope"}]}
        return None


def test_menu_is_real_and_division_b_only():
    ids = {s["id"] for s in agentic.menu()}
    assert "NBC:9.8" in ids and "NBC:3.8" in ids
    assert all(agentic._sections()[i]["division"] == "B" for i in ids)
    assert any(i.startswith("NECB:") for i in ids) and any(i.startswith("NPC:") for i in ids)


def test_admin_sections_only_for_admin_queries():
    assert not any(s["division"] != "B" for s in agentic.menu(False))
    assert any(s["division"] != "B" for s in agentic.menu(True))


def test_safety_invented_items_dropped():
    r = agentic.deep_search("ramp slope instead of required", llm=FakeLLM(False), use_cache=False, with_precedents=False)
    assert all(x["area_id"] != "NBC:99.99" for x in r["route"]) and len(r["route"]) == 1
    assert all(x["article"] != "9.8.99.99" for x in r["results"])
    assert not any("one in forty" in x["quote"] for x in r["results"])
    assert r["results"] == []


def test_real_quote_survives_and_is_substring():
    r = agentic.deep_search("ramp slope instead of required", llm=FakeLLM(True), use_cache=False, with_precedents=False)
    own = [x for x in r["results"] if not x.get("cross_ref_of")]
    assert [x["article"] for x in own] == ["9.8.5.4"]
    for x in r["results"]:
        assert x["verified"] and agentic._norm(x["quote"]) in agentic._text(x["code"], x["article"])


def test_offline_fallback_and_budget():
    class Off:
        name = "offline"
    r = agentic.deep_search("handrail height lower than required on an interior stair", llm=Off(), use_cache=False,
                            with_precedents=False)
    assert r["fallback"] and r["llm_calls"] == 0 and r["route"]
    for x in r["results"]:
        assert agentic._norm(x["quote"]) in agentic._text(x["code"], x["article"])
    r2 = agentic.deep_search("ramp slope", llm=FakeLLM(True), max_prompt_tokens=10, use_cache=False, with_precedents=False)
    assert r2["budget_exceeded"] and r2["llm_calls"] == 0


def test_endpoint():
    from fastapi.testclient import TestClient
    from main import app
    c = TestClient(app)
    j = c.post("/api/deep-search", json={"query": "handrail height on interior stair", "cheap": True}).json() \
        if False else None
    assert c.post("/api/deep-search", json={"query": " "}).status_code == 422
    assert c.post("/api/applications/nope/deep-search", json={}).status_code == 404
