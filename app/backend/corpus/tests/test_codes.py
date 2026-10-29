"""Tests for the NFC / NPC / NECB corpus. Runnable as a script (plain asserts) or with pytest.

Run (from app/backend):  python -X utf8 -m corpus.tests.test_codes
Every expected value below was checked by hand against the PDF page text (page numbers are 1-based PDF pages).
"""
import json
import sys

from corpus import DATA
from corpus import verifier_codes as V

N = {"count": 0}


def check(cond, msg):
    N["count"] += 1
    assert cond, msg


def test_nfc():
    check(V.article_exists("NFC", "2.4.1.1"), "NFC 2.4.1.1 exists")
    a = V.get_article("NFC", "2.4.1.1")
    check(a["title"] == "Accumulation of Combustible Materials", "NFC 2.4.1.1 title")
    check(a["pdf_page"] == 84 and len(a["sentences"]) == 6, "NFC 2.4.1.1 page 84, six sentences (6th continues on p85)")
    check(a["sentences"][0]["text"].startswith("Combustible waste materials in and around buildings"), "NFC 2.4.1.1(1) text")
    check(a["code"] == "NFC(AE) 2023" and a["division"] == "B", "NFC code/division tags")
    check(set(a["sentences"][0]["attributions"]) == {"F01-OS1.1", "F01-OS1.2", "F02-OS1.1", "F02-OS1.2",
                                                     "F01-OP1.1", "F01-OP1.2", "F02-OP1.1", "F02-OP1.2"},
          "NFC 2.4.1.1(1) attribution table [F01,F02-OS1.2,OS1.1] [F01,F02-OP1.2,OP1.1]")
    check(V.get_article("NFC", "2.4.1.2")["title"] == "Storage Rooms for Combustible Waste Materials", "NFC 2.4.1.2 title")
    check(not V.article_exists("NFC", "9.9.9.9"), "NFC 9.9.9.9 does not exist")
    r = V.lookup_attribution("NFC", "2.4.1.1.(1)")
    check(r["verified"] and {f["code"] for f in r["functions"]} == {"F01", "F02"}, "NFC 2.4.1.1(1) functions F01,F02")
    check(any(f["text"] == "To minimize the risk of accidental ignition." for f in r["functions"]), "NFC F01 text")
    check(any(o["code"] == "OS1.1" and o["text"] == "fire or explosion occurring" for o in r["objectives"]), "NFC OS1.1 text")
    check(r["intent"] and r["intent"]["status"] == "matched", "NFC 2.4.1.1 has an intent statement")


def test_npc():
    a = V.get_article("NPC", "2.4.6.4")
    check(a["title"] == "Protection from Backflow" and a["pdf_page"] == 105 and len(a["sentences"]) == 5, "NPC 2.4.6.4")
    check(V.get_article("NPC", "2.1.2.1")["title"] == "Sanitary Drainage Systems", "NPC 2.1.2.1 title")
    check(V.get_article("NPC", "2.1.2.1")["sentences"][1]["text"].startswith("A combined building drain shall not be installed."),
          "NPC 2.1.2.1(2) text")
    check(V.get_article("NPC", "2.1.2.1")["sentences"][0]["attributions"] == ["F72-OH2.1"], "NPC 2.1.2.1(1) [F72-OH2.1]")
    check(V.get_article("NPC", "2.1.2.1")["sentences"][1]["attributions"] == ["F72-OH2.1", "F72-OP5"], "NPC 2.1.2.1(2) two cells: OH2.1 and OP5")
    check(V.get_article("NPC", "2.7.2.4")["code"] == "NPC 2020" and len(V.get_article("NPC", "2.7.2.4")["sentences"]) == 10,
          "NPC 2.7.2.4 has 10 sentences")
    r = V.lookup_attribution("NPC", "2.1.2.1.(2)")
    check([o["code"] for o in r["objectives"]] == ["OH2.1", "OP5"] and r["functions"][0]["code"] == "F72", "NPC lookup 2.1.2.1(2)")
    check(r["objectives"][0]["text"] == "exposure to human or domestic waste" and r["functions"][0]["text"], "NPC OH2.1/F72 statement text resolved")
    check(not V.article_exists("NPC", "2.9.9.9"), "NPC 2.9.9.9 does not exist")


def test_necb():
    a = V.get_article("NECB", "3.2.1.1")
    check(a["title"] == "Protection of Insulation Materials" and a["pdf_page"] == 74 and len(a["sentences"]) == 2, "NECB 3.2.1.1")
    check(a["sentences"][0]["attributions"] == ["F92-OE1.1"], "NECB 3.2.1.1(1) [F92-OE1.1]")
    r = V.lookup_attribution("NECB", "3.2.1.1.(1)")
    check(r["objectives"][0]["text"] == "excessive use of energy", "NECB OE1.1 text")
    check(r["functions"][0]["text"] == "To limit the amount of uncontrolled thermal transfer through the building envelope.",
          "NECB F92 text")
    check("overall thermal transmittance" in json.dumps(r["intent"]), "NECB 3.2.1.1 intent text")
    check(V.get_article("NECB", "3.2.2.1")["title"] == "Vestibules" and len(V.get_article("NECB", "3.2.2.1")["sentences"]) == 3,
          "NECB 3.2.2.1 vestibules, 3 sentences")
    check(V.get_article("NECB", "3.2.2.1")["sentences"][0]["attributions"] == ["F90-OE1.1"], "NECB 3.2.2.1(1) F90")
    check(V.get_article("NECB", "4.2.1.1")["title"] == "Exit Signs", "NECB 4.2.1.1 title")
    check(V.get_article("NECB", "4.2.1.6")["tables"], "NECB 4.2.1.6 keeps its (unparsed) tables")
    check(V.get_article("NECB", "5.2.2.1")["attributions"] == [], "NECB 5.2.2.1 has no attribution (intent: directs to NBC)")


def test_cross_code():
    # the same number exists in several codes with different content: no collisions
    check(V.get_article("NECB", "3.2.1.1")["title"] != V.get_article("NFC", "3.2.1.1")["title"], "3.2.1.1 differs NFC vs NECB")
    check(V.get_article("NFC", "3.2.1.1")["code"] == "NFC(AE) 2023" and V.get_article("NECB", "3.2.1.1")["code"] == "NECB 2020",
          "code tags")
    cites = V.find_citations("see NFC 2.4.1.1.(2), NPC Article 2.2.5.1 and Sentence 3.2.1.1.(1) of the NECB; also NECB 9.9.9.9")
    got = {(c["code_key"], c["article"], c["sentence"], c["exists"]) for c in cites}
    check(("nfc", "2.4.1.1", 2, True) in got and ("npc", "2.2.5.1", None, True) in got, "find_citations NFC/NPC prefix")
    check(("necb", "3.2.1.1", 1, True) in got and ("necb", "9.9.9.9", None, False) in got, "find_citations suffix form + unverified")
    check(V.find_citations("Article 3.2.1.1. of the NBC") == [], "NBC citations are not claimed by this module")
    check(V.lookup_attribution("XYZ", "1.1.1.1")["note"].startswith("unknown code"), "unknown code handled")


def test_files():
    for k, lo in (("nfc", 700), ("npc", 250), ("necb", 220)):
        arts = json.load(open(DATA / f"{k}_articles.json", encoding="utf8"))
        check(len(arts) >= lo, f"{k} article count >= {lo}")
    ob = json.load(open(DATA / "other_codes_objectives.json", encoding="utf8"))
    check({"NFC(AE) 2023", "NPC 2020", "NECB 2020"} <= set(ob), "objectives file has all three codes")
    check(set(ob["NECB 2020"]["functions"]) >= {"F90", "F100"}, "NECB F90..F100 present")
    check(ob["NECB 2020"]["functions"]["F100"]["text"] == "To limit the unnecessary rejection of reusable waste energy.",
          "NECB F100 text")


if __name__ == "__main__":
    for fn in (test_nfc, test_npc, test_necb, test_cross_code, test_files):
        fn()
        print("ok", fn.__name__)
    print(f"{N['count']} assertions passed")
    sys.exit(0)
