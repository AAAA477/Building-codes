import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from corpus import precedents as P  # noqa: E402


def docs(q, k=6, **kw):
    return P.search_precedents(q, k=k, **kw)


def has(res, frag, top=None):
    rs = res if top is None else res[:top]
    return any(frag.lower() in (r["doc"] + " " + (r.get("label") or "") + " " + r["title"]).lower() for r in rs)


def test_wocd_policy_and_standata_distinct():
    r = docs("window opening control devices")
    assert has(r, "B23-02", 3) and has(r, "23-BCV-001", 3)
    assert len({x["doc"] for x in r}) == len(r)  # one chunk per document


def test_roof_truss():
    assert has(docs("roof truss engineering"), "B23-03", 5)


def test_secondary_suite_row_house():
    assert has(docs("secondary suite row house fire separation"), "B23-01", 4)


def test_small_building_access():
    assert has(docs("small building access fire department"), "B19-04", 2)


def test_calgary_exterior_egress():
    r = docs("exterior egress single family")
    assert r[0]["label"] == "Calgary Advisory A19-004"
    assert "no legal status" in r[0]["legal_status_note"]


@pytest.mark.parametrize("q", ["single exit stair", "point access block"])
def test_single_exit_stair_finds_ses_not_racking(q):
    r = docs(q)
    assert has(r, "23-BCI-026", 3)
    assert not has(r, "racking", 3)


def test_no_good_match_ev():
    assert docs("electric vehicle charging") == []


def test_snippet_is_verbatim_and_short():
    import json
    rows = {json.loads(l)["id"]: json.loads(l)["text"] for l in open(P.CHUNKS, encoding="utf8")}
    for q in ("window opening control devices", "single exit stair", "bathroom exhaust fan"):
        for r in docs(q):
            assert len(r["snippet"]) <= 300 and r["snippet"] in rows[r["id"]]


def test_article_number_boost():
    r = docs("9.8.8.1")
    assert r and "9.8.8.1" in r[0]["articles_cited"]
    assert any(h["articles_cited"] and "9.8.8.1" in h["articles_cited"] for h in P.by_article("9.8.8.1"))


def test_filters():
    r = docs("secondary suite", jurisdictions=["edmonton"])
    assert r and all(x["jurisdiction"] == "edmonton" for x in r)
    r = docs("secondary suite", source_types=["calgary_advisory"])
    assert r and all(x["source_type"] == "calgary_advisory" for x in r)


def test_users_guide_downranked():
    r = docs("bathroom exhaust fan")
    g = [x for x in r if x["source_type"] == "users_guide"]
    assert not g or r.index(g[0]) > 0


def test_citations_verified_only():
    from corpus import verifier
    for r in docs("window opening control devices"):
        assert all(verifier.article_exists(a) for a in r["articles_cited"])


def test_nbc_search_no_good_match():
    from corpus import nbc_search as N
    ev = N.apply_quality("electric vehicle charging", N.search_articles("electric vehicle charging", 8))
    assert ev["no_good_match"] is True and ev["results"] == [] and ev["message"]
    for q in ("stair width", "bathroom ventilation fan", "egress window bedroom", "handrail"):
        o = N.apply_quality(q, N.search_articles(q, 8))
        assert o["no_good_match"] is False and o["results"]
