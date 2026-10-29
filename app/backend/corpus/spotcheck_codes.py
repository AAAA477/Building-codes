"""Spot-check parsed articles of NFC/NPC/NECB against raw PDF page text (prints results).
Run (from app/backend): python -X utf8 -m corpus.spotcheck_codes"""
import json
import re
import sys

import pymupdf

from . import DATA, FILES
from .extract_codes import CODES, norm

PICK = {
    "nfc": ["2.4.1.1", "2.4.1.2", "3.2.2.1", "2.1.3.1", "2.7.1.1", "3.3.1.1", "4.1.1.1", "5.6.1.1", "6.1.1.1", "7.2.1.1",
            "2.8.2.1", "3.1.1.1"],
    "npc": ["2.1.2.1", "2.2.2.1", "2.3.1.1", "2.4.3.1", "2.4.6.4", "2.5.1.1", "2.6.1.1", "2.7.2.4", "2.2.10.1", "2.3.3.1",
            "2.4.7.1", "2.2.5.1"],
    "necb": ["3.2.1.1", "3.2.2.1", "3.2.3.1", "4.2.1.1", "5.2.2.1", "6.2.1.1", "7.2.1.1", "8.4.3.1", "3.2.1.2", "4.2.1.6",
             "5.2.1.1", "6.2.2.1"],
}


def main():
    bad = 0
    for k, picks in PICK.items():
        cfg = CODES[k]
        doc = pymupdf.open(str(FILES / "codes" / cfg["pdf"]))
        arts = json.load(open(DATA / f"{k}_articles.json", encoding="utf8"))
        print(f"=== {cfg['code']}")
        n = 0
        for num in picks:
            a = arts.get(num)
            if not a:
                print(f"  {num}: NOT IN INDEX")
                bad += 1
                continue
            blob = " ".join(norm(doc[p - 1].get_text()) for p in a["pdf_pages"])
            ok_s = sum(1 for s in a["sentences"] if norm(s["text"])[:40] in blob)
            ok_h = a["number"] in blob and norm(a["title"])[:30] in blob
            n += 1
            if ok_s != len(a["sentences"]) or not ok_h:
                bad += 1
            print(f"  {num} p{a['pdf_page']} '{a['title'][:42]}' sentences {ok_s}/{len(a['sentences'])} heading_in_page={ok_h} "
                  f"attr={a['attributions'][:4]}")
        print(f"  checked {n}")
    print("FAILURES:", bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
