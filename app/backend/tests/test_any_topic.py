"""Any-NBC-topic support: full search, topics, section-c add/delete, classify modes, lookup completeness.
Real articles only."""
import json, sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
import main  # noqa: E402

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def _offline_llm(monkeypatch):
    """Deterministic tests: never call a hosted LLM (a .env may configure one)."""
    from llm import OfflineLLM
    off = OfflineLLM()
    monkeypatch.setattr(main, "get_llm", lambda: off)

# (plain-language query, article that is a plausible top-3 hit) - checked against the real NBC titles
QUERIES = [
    ("window guard height", {"3.4.6.6", "3.3.4.8", "9.8.8.1", "9.8.8.3"}),
    ("stair width", {"9.8.2.1", "3.4.3.2"}),
    ("insulation vapour barrier", {"9.25.4.1", "9.25.4.2", "9.25.4.3"}),
    ("handrail", {"9.8.7.4", "3.4.6.5", "9.8.7.3"}),
    ("smoke alarm", {"9.10.19.1", "9.10.19.3", "9.10.19.5", "3.2.4.20"}),
    ("egress window bedroom", {"9.9.10.1"}),
    ("guard height for deck", {"9.8.8.3", "3.3.2.9", "3.4.6.6"}),
    ("bathroom ventilation fan", {"9.32.3.7", "9.32.3.3", "9.32.3.10"}),
    ("radon rough-in", {"9.13.4.3", "9.13.4.2"}),
    ("fire alarm system", {"3.2.4.5", "9.10.18.2", "10.6.3.1"}),
]


@pytest.mark.parametrize("q,ok", QUERIES)
def test_search_realistic(q, ok):
    r = client.post("/api/search/articles", json={"query": q, "k": 3}).json()["results"]
    assert r and {x["article"] for x in r} & ok, [x["article"] for x in r]
    top = r[0]
    for key in ("code", "article", "title", "part", "pdf_page", "snippet", "objectives", "has_attribution", "has_intent", "score"):
        assert key in top
    assert top["code"] == "NBC" and top["code_edition"] == "NBC(AE) 2023"


def test_search_parts_filter_and_validation():
    r = client.post("/api/search/articles", json={"query": "stair width", "k": 5, "parts": ["3"]}).json()["results"]
    assert r and all(x["part"] == "3" for x in r)
    assert client.post("/api/search/articles", json={"query": " "}).status_code == 422


def test_topics_and_browse():
    j = client.get("/api/topics").json()
    ids = {t["id"]: t for t in j["topics"]}
    assert ids["single_exit_stair"]["mode"] == "guided" and ids["other_nbc"]["mode"] == "lookup"
    parts = {p["part"]: p for p in j["browse"]}
    assert parts["9"]["title"] == "Housing and Small Buildings"
    assert sum(s["articles"] for p in j["browse"] for s in p["sections"]) == 2078
    sec = {s["section"]: s for s in parts["9"]["sections"]}
    assert sec["9.8"]["articles"] > 10 and sec["9.8"]["title"]


def mk(body=None):
    return client.post("/api/applications", json=body or {}).json()


def test_section_c_add_real_fake_dup_delete():
    a = mk({"variance": {"topic": "other_nbc"}})
    base = f"/api/applications/{a['id']}/section-c"
    r = client.post(base + "/add", json={"article": "9.9.10.1"})
    assert r.status_code == 200
    j = r.json()
    row = j["variance"]["section_c"][0]
    assert row["article"] == "9.9.10.1" and row["verified"] is True and row["objective"] != "unresolved"
    assert row["source"]["page"] and j["provenance"]["variance.section_c.0.explainer"]["source"] == "ai_draft"
    assert "9.9.10.1" in j["variance"]["acceptable_solution"]["articles"]
    f = client.post(base + "/add", json={"article": "9.99.99.99"})
    assert f.status_code == 404 and "not found" in f.json()["detail"]
    assert client.post(base + "/add", json={"article": "9.9.10.1"}).status_code == 409
    r2 = client.post(base + "/add", json={"article": "C:2.3.1.1"})
    assert r2.status_code == 200
    row2 = r2.json()["variance"]["section_c"][1]
    assert row2["objective"] == "unresolved" and row2["verified"] is True and "Root-article" in row2["note"]
    d = client.delete(f"{base}/0")
    assert d.status_code == 200 and [x["article"] for x in d.json()["variance"]["section_c"]] == ["C:2.3.1.1"]
    assert "variance.section_c.0.explainer" in d.json()["provenance"]
    assert client.delete(f"{base}/5").status_code == 404


def test_classify_modes_and_suggestions():
    s = mk({"variance": {"topic": "single_exit_stair"}, "project": {"description": "single exit stair in a 6 storey building"}})
    c = client.post(f"/api/applications/{s['id']}/classify").json()
    assert c["mode"] == "guided" and c["topic"] == "single_exit_stair" and c["supported"] is True
    o = mk({"variance": {"topic": "other"}, "project": {"description": "window opening control device on bedroom egress windows"}})
    c = client.post(f"/api/applications/{o['id']}/classify").json()
    assert c["mode"] == "lookup" and c["topic"] == "other_nbc" and c["supported"] is True
    sug = c["suggested_articles"]
    assert sug and "9.9.10.1" in {x["article"] for x in sug} and "Matched" in sug[0]["reason"]


def test_lookup_completeness_non_blocking_professional():
    a = mk({"variance": {"topic": "other_nbc"}})
    comp = client.get(f"/api/applications/{a['id']}/completeness").json()
    pf = comp["professional_flags"]
    assert len(pf) == 1 and pf[0]["stop"] is False and "C:2.4.1.1" in pf[0]["article_refs"]
    ids = {i["id"] for i in comp["items"]}
    assert "B.units_per_floor" not in ids and "D.professional_named" not in ids
    assert not any(i["status"] == "needs_professional" for i in comp["items"])
    st = mk({"variance": {"topic": "single_exit_stair"}})
    cs = client.get(f"/api/applications/{st['id']}/completeness").json()
    assert cs["professional_flags"][0]["stop"] is True and "B.units_per_floor" in {i["id"] for i in cs["items"]}


def test_section_d_templates_generic_for_lookup():
    g = client.get("/api/section-d/templates", params={"topic": "other_nbc"}).json()["items"]
    s = client.get("/api/section-d/templates", params={"topic": "single_exit_stair"}).json()["items"]
    assert 0 < len(g) < len(s)
    assert all("Div C" in i["code_ref"] or "NFC" in i["code_ref"] for i in g)
    assert not any(i["group"] == "single_exit_stair" for i in g)


# ---- other codes (NFC / NPC / NECB) ----
OTHER = [
    ("fire extinguisher inspection", "NFC", {"6.2.1.1", "C:2.2.4.2"}),
    ("sprinkler system maintenance", "NFC", {"4.5.10.7", "C:2.2.4.4", "C:2.2.4.6", "6.4.1.1"}),
    ("fire alarm testing", "NFC", {"6.3.1.2", "6.7.1.1"}),
    ("backflow prevention", "NPC", {"2.6.2.3", "2.6.2.4", "2.6.2.12"}),
    ("water heater temperature", "NPC", {"2.6.1.12"}),
    ("lighting power density office", "NECB", {"4.3.3.2", "4.3.2.2"}),
]


@pytest.mark.parametrize("q,code,ok", OTHER)
def test_search_other_codes(q, code, ok):
    r = client.post("/api/search/articles", json={"query": q, "k": 3}).json()["results"]
    assert any(x["code"] == code and x["article"] in ok for x in r), [(x["code"], x["article"]) for x in r]
    only = client.post("/api/search/articles", json={"query": q, "k": 3, "codes": [code]}).json()["results"]
    assert only and all(x["code"] == code for x in only)
    assert client.post("/api/search/articles", json={"query": q, "codes": ["XYZ"]}).status_code == 422


def test_topics_codes_list():
    j = client.get("/api/topics").json()
    c = {x["code"]: x["articles"] for x in j["codes"]}
    assert c == {"NBC": 2170, "NFC": 814, "NPC": 285, "NECB": 270}


def test_section_c_add_nfc_and_verify():
    a = mk({"variance": {"topic": "other_nbc"}})
    base = f"/api/applications/{a['id']}"
    r = client.post(base + "/section-c/add", json={"article": "6.2.1.1", "code": "NFC"})
    assert r.status_code == 200, r.text
    row = r.json()["variance"]["section_c"][0]
    assert row["code"] == "NFC" and row["code_edition"] == "NFC(AE) 2023" and row["article"] == "6.2.1.1"
    assert row["source"]["doc"] == "NFC_2023AE.pdf" and row["verified"] is True and row["objective"] != "unresolved"
    assert r.json()["variance"]["acceptable_solution"]["articles"] == ["NFC 6.2.1.1"]
    # the same bare number is a different NBC article: not a duplicate; prefix form works too
    assert client.post(base + "/section-c/add", json={"article": "NFC 6.2.1.1"}).status_code == 409
    assert client.post(base + "/section-c/add", json={"article": "2.6.2.3", "code": "NPC"}).status_code == 200
    f = client.post(base + "/section-c/add", json={"article": "9.9.9.9", "code": "NFC"})
    assert f.status_code == 404 and "NFC(AE) 2023" in f.json()["detail"]
    assert client.post(base + "/section-c/add", json={"article": "6.2.1.1", "code": "ZZZ"}).status_code == 422
    # completeness must not flag the NFC citation as an unknown NBC article
    comp = client.get(base + "/completeness").json()
    assert not any(i["id"].startswith("C.article.") for i in comp["items"]), comp["items"]
    v = client.get("/api/citations/verify", params={"article": "6.2.1.1", "code": "NFC"}).json()
    assert v["exists"] is True and v["code"] == "NFC"
    assert client.get("/api/citations/verify", params={"article": "NFC 6.2.1.1"}).json()["exists"] is True
    assert client.get("/api/citations/verify", params={"article": "6.2.1.1"}).json()["code"] == "NBC"
    # a bad NFC citation in the acceptable-solution list IS flagged
    client.patch(base, json={"variance": {"acceptable_solution": {"articles": ["NFC 9.9.9.9"]}}})
    comp = client.get(base + "/completeness").json()
    assert any(i["id"].startswith("C.article.") for i in comp["items"])


def test_export_prefixes_non_nbc_article():
    import importlib
    fill_scc = importlib.import_module("export.fill_scc")
    assert fill_scc._article_text({"article": "6.2.1.1", "code": "NFC", "verified": True}) == "NFC 6.2.1.1"
    assert fill_scc._article_text({"article": "9.9.10.1", "verified": True}) == "9.9.10.1"


def test_llm_expansion_union_and_fallback(monkeypatch):
    class Fake:
        name = "fake"
        def expand_query(self, q):
            return "kitchen hood clearance combustible 9.99.99.99"
    monkeypatch.setattr(main, "get_llm", lambda: Fake())
    j = client.post("/api/search/articles", json={"query": "exhaust fan clearance", "k": 5}).json()
    assert j["expansion"]["used"] is True and "9.99" not in j["expansion"]["keywords"]
    allowed = {(x["code"], x["article"]) for x in main._nbc_search().search_articles("kitchen hood clearance combustible", 200)} | \
              {(x["code"], x["article"]) for x in main._nbc_search().search_articles("exhaust fan clearance", 200)}
    assert all((x["code"], x["article"]) in allowed for x in j["results"])
    class Bad:
        name = "bad"
        def expand_query(self, q):
            raise RuntimeError("boom")
    monkeypatch.setattr(main, "get_llm", lambda: Bad())
    j = client.post("/api/search/articles", json={"query": "exhaust fan clearance", "k": 5}).json()
    assert j["expansion"]["used"] is False and j["results"]
