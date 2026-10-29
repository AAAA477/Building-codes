"""Corpus tests (plain asserts). Run: python -m corpus.tests.test_corpus   (from app/backend) or pytest."""
import json
import sys

from corpus import DATA
from corpus import verifier as v
from corpus.search import search


def test_article_exists():
    assert v.article_exists("3.4.2.1")
    assert v.article_exists("3.4.2.1.")
    assert v.article_exists("9.9.8.2")
    assert not v.article_exists("3.4.2.99")
    assert not v.article_exists("9.9.9.9")


def test_3421_text():
    a = v.get_article("3.4.2.1")
    assert a["title"] == "Minimum Number of Exits"
    assert a["division"] == "B" and a["pdf_page"] == 269
    assert len(a["sentences"]) == 5
    assert "at least 2 exits" in a["sentences"][0]["text"]
    assert "not more than 60" in a["sentences"][1]["text"]
    assert "Table 3.4.2.1.-A" in a["sentences"][1]["text"]


def test_3421_attribution():
    r = v.lookup_attribution("3.4.2.1")
    codes = {o["code"] for o in r["objectives"]}
    funcs = {f["code"] for f in r["functions"]}
    assert {"OS3.7", "OS1.2", "OP1.2"} <= codes
    assert {"F10", "F12", "F05", "F06"} <= funcs
    assert r["verified"] is True
    assert r["source"]["page"] == 269
    assert r["root_used"] is None


def test_root_rule_sentence_without_own_attribution():
    r = v.lookup_attribution("3.4.2.1.(2)")
    assert r["root_used"] == "3.4.2.1"
    assert r["objectives"], "root article's objectives must be applied"
    r3 = v.lookup_attribution("3.4.2.1.(3)")
    assert r3["root_used"] is None and [o["code"] for o in r3["objectives"]] == ["OS3.7"]


def test_objective_function_text():
    o = json.load(open(DATA / "objectives.json", encoding="utf8"))
    f = json.load(open(DATA / "functions.json", encoding="utf8"))
    assert o["OS1.2"]["text"] == "fire or explosion impacting areas beyond its point of origin"
    assert o["OS3.7"]["pdf_page"] == 69
    assert f["F03"]["text"].startswith("To")
    assert f["F12"]["text"] == "To facilitate emergency response."
    assert f["F10"]["text"] == "To facilitate the timely movement of persons to a safe place in an emergency."


def test_firefighting_water_supply():
    a = v.get_article("3.2.5.7")
    assert a["title"] == "Water Supply"
    assert v.lookup_attribution("3.2.5.7")["functions"]


def test_part9_exits():
    a = v.get_article("9.9.8.2")
    assert a["title"] == "Number of Required Exits"
    assert a["part"] == "9"


def test_division_prefix():
    assert v.get_article("A:1.2.1.1")["division"] == "A"
    assert v.get_article("C:2.3.1.1")["title"] == "Documentation"
    assert v.get_article("3.2.1.1")["division"] == "B"       # collides with Div A 3.2.1.1: B is the bare key


def test_find_and_verify_text():
    t = "Per Sentence 3.4.2.1.(2) and Article 3.2.5.7. but also 7.7.7.7 and 3.4.2.1."
    assert v.find_citations(t) == ["3.4.2.1", "3.2.5.7", "7.7.7.7"]
    res = v.verify_text(t)
    assert res["cited"] == ["3.4.2.1", "3.2.5.7"] and res["unverified"] == ["7.7.7.7"]


def test_unknown_article_not_verified():
    r = v.lookup_attribution("1.1.1.99")
    assert r["verified"] is False and r["objectives"] == [] and r["source"] is None


def test_intents_tagged():
    it = json.load(open(DATA / "intents.json", encoding="utf8"))
    assert all(x["intent_edition"] == "NBC 2020 Intent Supplement" for x in it.values())
    x = it["3.4.2.1"]
    assert x["status"] == "found" and x["source"]["page"] == 608
    assert it["C:2.3.1.1"]["status"] == "unresolved"
    r = v.lookup_attribution("3.4.2.1")
    assert r["intent"] and r["intent"]["intent_edition"] == "NBC 2020 Intent Supplement"


def test_stair_articles():
    s = json.load(open(DATA / "stair_articles.json", encoding="utf8"))["articles"]
    nums = {e["article"] for e in s}
    assert {"3.4.2.1", "9.9.8.2", "3.2.5.7", "3.2.5.12", "C:2.3.1.1"} <= nums
    assert all(e["exists_in_nbc_2023ae"] for e in s)
    e = next(e for e in s if e["article"] == "3.2.6.1")
    assert e["attribution_status"] == "unresolved"


def test_search():
    r = search("minimum number of exits", 3)
    assert r and r[0]["id"] == "nbc:3.4.2.1" and r[0]["page"] == 269
    r = search("point access block single egress stair", 3)
    assert any(x["doc"].startswith("11_") or x["doc"].startswith("10_") for x in r)


def test_chunk_ids_unique():
    ids = [json.loads(l)["id"] for l in open(DATA / "chunks.jsonl", encoding="utf8")]
    assert len(ids) == len(set(ids)) > 500


if __name__ == "__main__":
    fns = [(n, f) for n, f in sorted(globals().items()) if n.startswith("test_") and callable(f)]
    failed = 0
    for n, f in fns:
        try:
            f()
            print("PASS", n)
        except Exception as e:  # noqa
            failed += 1
            print("FAIL", n, repr(e))
    print(f"{len(fns) - failed}/{len(fns)} passed")
    sys.exit(1 if failed else 0)
