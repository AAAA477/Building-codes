"""Closed-set citation verifier for NFC(AE) 2023, NPC 2020 and NECB 2020 (companion of verifier.py for the NBC).

Data: app/data/corpus/{nfc,npc,necb}_articles.json, *_intents.json, other_codes_objectives.json
(built by extract_codes.py). Division B articles are keyed by bare number ("2.4.1.1"); Division A / C
articles are keyed "A:1.4.1.2" / "C:1.2.3.4". Nothing is generated.

CLI (from app/backend):  python -m corpus.verifier_codes NFC 2.4.1.1
"""
import json
import re
import sys
from functools import lru_cache

from . import DATA

CODE_INFO = {
    "nfc": {"label": "NFC(AE) 2023", "doc": "NFC_2023AE.pdf"},
    "npc": {"label": "NPC 2020", "doc": "NPC_2020.pdf"},
    "necb": {"label": "NECB 2020", "doc": "NECB_2020_2nd_printing.pdf"},
}
NUM = r"(\d{1,2}\.\d{1,2}\.\d{1,2}\.\d{1,3})"
SENT = r"(?:\.?\s*\((\d+)\))?"
RE_PREFIX = re.compile(
    r"\b(NFC|NPC|NECB)(?:\s*\(AE\))?(?:\s+(?:20\d\d))?\s*[,:]?\s*(?:Article|Sentence|Clause|Subsection|Section)?\s*"
    + NUM + SENT, re.I)
RE_SUFFIX = re.compile(
    r"(?<![\d.])" + NUM + SENT + r"\s*(?:\([a-z]\))?\s*(?:,\s*)?(?:of|in)\s+(?:Division\s+[ABC]\s+of\s+)?(?:the\s+)?(NFC|NPC|NECB)\b",
    re.I)


def _key(code):
    c = (code or "").strip().lower()
    for k in CODE_INFO:
        if c.startswith(k):
            return k
    return None


def _load(name, default):
    p = DATA / name
    if not p.exists():
        return default
    with open(p, encoding="utf8") as fh:
        return json.load(fh)


@lru_cache(maxsize=None)
def _articles(k):
    return _load(f"{k}_articles.json", {})


@lru_cache(maxsize=None)
def _intents(k):
    return _load(f"{k}_intents.json", {})


@lru_cache(maxsize=1)
def _objectives():
    return _load("other_codes_objectives.json", {})


def _norm(num):
    num = (num or "").strip().rstrip(".")
    m = re.match(r"^([ABC]:)?(\d+\.\d+\.\d+\.\d+)(?:\.?\((\d+)\))?$", num)
    if not m:
        return num, None
    return (m.group(1) or "") + m.group(2), (int(m.group(3)) if m.group(3) else None)


def article_exists(code, num):
    k = _key(code)
    return bool(k) and _norm(num)[0] in _articles(k)


def get_article(code, num):
    k = _key(code)
    return _articles(k).get(_norm(num)[0]) if k else None


def _split(codes):
    objs, funcs = [], []
    for c in codes:
        f, _, o = c.partition("-")
        if f and f not in funcs:
            funcs.append(f)
        if o and o not in objs:
            objs.append(o)
    return objs, funcs


def lookup_attribution(code, num):
    """Same return shape as verifier.lookup_attribution (plus 'code'). Sentence form '2.4.1.1.(2)' accepted."""
    k = _key(code)
    art_no, sent_no = _norm(num)
    label = CODE_INFO[k]["label"] if k else (code or "")
    res = {"code": label, "article": art_no, "sentence": sent_no, "edition": label, "objectives": [], "functions": [],
           "intent": None, "root_used": None, "source": None, "verified": False, "note": None}
    if not k:
        res["note"] = f"unknown code '{code}' (expected NFC, NPC or NECB)"
        return res
    a = _articles(k).get(art_no)
    if a is None:
        res["note"] = f"article not found in indexed {label} text"
        return res
    res["source"] = {"doc": CODE_INFO[k]["doc"], "page": a["pdf_page"]}
    codes = a["attributions"]
    note = None
    if sent_no is not None:
        s = next((x for x in a["sentences"] if x["number"] == sent_no), None)
        if s is None:
            note = f"sentence ({sent_no}) not found in parsed article; article-level attributions used"
            res["root_used"] = art_no
        elif s["attributions"]:
            codes = s["attributions"]
        else:
            res["root_used"] = art_no
            note = "sentence has no attribution of its own; root article's attributions applied"
    if not codes:
        note = "no attributed objectives/functions found for this article in the Part's attribution table (unresolved)"
    objs, funcs = _split(codes)
    ref = _objectives().get(label, {})
    O, F = ref.get("objectives", {}), ref.get("functions", {})
    res["objectives"] = [{"code": c, "text": O[c]["text"] if c in O else None,
                          "page": O[c]["pdf_page"] if c in O else None} for c in objs]
    res["functions"] = [{"code": c, "text": F[c]["text"] if c in F else None,
                         "page": F[c]["pdf_page"] if c in F else None} for c in funcs]
    res["attribution_codes"] = codes
    it = _intents(k).get(a["number"]) if a["division"] == "B" else None
    if it and it.get("status") == "matched":
        res["intent"] = it
    elif it:
        res["intent"] = {"status": "unresolved", "intent_edition": it.get("intent_edition"), "note": it.get("note")}
    res["note"] = note
    res["verified"] = bool(codes) and all(x["text"] for x in res["objectives"] + res["functions"])
    return res


def find_citations(text):
    """Recognise 'NFC 2.4.1.1', 'NPC 2.2.5.1.(2)', 'NECB 3.2.1.1', 'NFC(AE) Article 2.4.1.1.', and
    'Sentence 3.2.1.1.(1) of the NECB'. Returns [{code, code_key, article, sentence, exists}] (unique, in order)."""
    out, seen = [], set()

    def add(ck, art, sent):
        ck = ck.lower()
        key = (ck, art, sent)
        if key in seen:
            return
        seen.add(key)
        out.append({"code": CODE_INFO[ck]["label"], "code_key": ck, "article": art,
                    "sentence": int(sent) if sent else None, "exists": article_exists(ck, art)})

    for m in RE_PREFIX.finditer(text or ""):
        add(m.group(1), m.group(2), m.group(3))
    for m in RE_SUFFIX.finditer(text or ""):
        add(m.group(3), m.group(1), m.group(2))
    return out


def main(argv):
    if len(argv) < 2:
        print("usage: python -m corpus.verifier_codes NFC 2.4.1.1")
        return 2
    code, n = argv[0], argv[1]
    a = get_article(code, n)
    print(f"== {code} {n}: exists={article_exists(code, n)}")
    if a:
        print(f"   title: {a['title']}  (Division {a['division']}, pdf page {a['pdf_page']})")
        for s in a["sentences"][:2]:
            print(f"   ({s['number']}) {s['text'][:160]}")
    print(json.dumps(lookup_attribution(code, n), indent=1, ensure_ascii=False)[:3500])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
