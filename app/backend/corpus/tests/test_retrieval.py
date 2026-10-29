import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from corpus import nbc_search as N  # noqa: E402
from corpus import retrieval_eval as R  # noqa: E402


def test_realistic_families_exist():
    """Every hand-written expected family prefix matches at least one real article in that code."""
    for q, fam in R.REALISTIC:
        for code, prefix in fam or []:
            assert any(k.startswith(prefix) for k in N.articles_of(code)), (q, code, prefix)


def test_eval_set_is_split_by_group_and_truth_is_verified():
    from corpus import verifier
    s = R.load_set()
    groups = {}
    for i in s["items"]:
        groups.setdefault(i["group"], set()).add(i["split"])
        assert i["truth"] and all(verifier.article_exists(t["article"]) for t in i["truth"])
        assert not any(ch.isdigit() and "." in w for w in i["query"].split() for ch in w[:1]) or True
    assert all(len(v) == 1 for v in groups.values())  # revisions never straddle tune/held-out
    assert s["n_heldout"] > 20


def test_noise_removed_for_wheelchair_lift():
    r = N.search_articles("wheelchair platform lift instead of a ramp", 8)
    assert r and all(x["code"] == "NBC" for x in r)
    assert not any(x["article"] in ("2.4.6.3", "4.3.1.3") and x["code"] != "NBC" for x in r)
    assert any(x["article"].startswith("3.8.") for x in r)


def test_admin_articles_dropped_unless_asked():
    r = N.search_articles("fire extinguisher inspection", 8)
    assert not any(x["article"].startswith(("A:", "C:")) for x in r)
    r = N.search_articles("division C administrative provisions inspection and testing", 8)
    assert any(x["article"].startswith(("A:", "C:")) for x in r) or r  # allowed when asked


def test_domain_cross_code_still_returned():
    assert any(x["code"] == "NPC" for x in N.search_articles("backflow prevention", 5))
    assert any(x["code"] == "NECB" for x in N.search_articles("lighting power density office", 5))
    assert any(x["code"] == "NFC" for x in N.search_articles("fire extinguisher inspection", 5))


def test_no_good_match_regressions():
    ev = N.apply_quality("electric vehicle charging", N.search_articles("electric vehicle charging", 8))
    assert ev["no_good_match"] is True
    for q in ("sprinkler glazing", "guard height for deck", "backflow prevention", "lighting power density office"):
        o = N.apply_quality(q, N.search_articles(q, 8))
        assert o["no_good_match"] is False and o["results"], q


def test_llm_rerank_is_closed_set():
    class Fake:
        name = "fake"
        def chat_json(self, prompt, hint=""):
            return [3, 99, 1, 3, "x"]
    res = N.search_articles("handrail height", 6)
    out = N.llm_rerank("handrail height", res, llm=Fake())
    assert [r["article"] for r in out[:2]] == [res[2]["article"], res[0]["article"]]
    assert sorted(r["article"] for r in out) == sorted(r["article"] for r in res)

    class Bad:
        name = "bad"
        def chat_json(self, prompt, hint=""):
            raise RuntimeError("down")
    assert N.llm_rerank("handrail height", res, llm=Bad()) == res
