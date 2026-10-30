"""Build structured cards from the STANDATA variance PDFs.

Run from app/backend:  .venv/Scripts/python.exe -X utf8 -I -m corpus.build_variance_cards
Reads app/data/content/standata_index.json (kind == "variance") and the PDFs it points to; writes one JSON per
variance to app/data/content/variance_cards/<id>.json plus _report.json. Purpose, discussion, conditions and the
variance text are copied verbatim (glyph/whitespace normalised only); nothing is paraphrased. Hand corrections live in
variance_cards/_overrides.json as {id: {field: value}} and are applied after parsing.
"""
from __future__ import annotations
import json, re, sys, unicodedata
import warnings
from collections import Counter
from pathlib import Path

from . import ROOT
from . import verifier, verifier_codes

warnings.filterwarnings("ignore", category=FutureWarning)
import fitz  # noqa: E402

CONTENT = ROOT / "app" / "data" / "content"
INDEX = CONTENT / "standata_index.json"
OUT = CONTENT / "variance_cards"
OVERRIDES = OUT / "_overrides.json"

BIDI = dict.fromkeys(map(ord, "‪‫‬‭‮‎‏⁦⁧⁨⁩﻿"))
ART_RE = re.compile(r"(?<![\d.])(\d{1,2}\.\d{1,2}\.\d{1,2}\.\d{1,3})(?![\d])")
FOOTER = re.compile(
    r"^(Page \d+ of \d+|Building STANDATA \| Alberta\.ca.*|©\s*\d{4} Government of Alberta.*|STANDATA(?: variance)? [\dA-Z/()\-]+(?:REV\d)?|Archived|"
    r"\d\d-[BF]CV-\d+[A-Z0-9()/\-]*)$", re.I)
HEADING = re.compile(r"^(purpose|introduction|discussion|code references?|application|variance|conditions?|background information)$", re.I)
NUMBERED = re.compile(r"^\s*(\d{1,2})[.)]\s+(\S.*)$")
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
REV = re.compile(r"(R\d+|REV\d*|R)$", re.I)


def normalise(s: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", (s or "")).translate(BIDI)).strip()


def read_pdf_pages(path) -> list[str]:
    """Cleaned text of each page: glyphs normalised, running headers/footers removed."""
    pages = []
    for pg in fitz.open(str(path)):
        keep = []
        for ln in unicodedata.normalize("NFKC", pg.get_text()).translate(BIDI).split("\n"):
            s = ln.strip()
            if s and FOOTER.match(s):
                continue
            keep.append(ln.rstrip())
        pages.append("\n".join(keep))
    return pages


def _sections(pages: list[str]) -> list[dict]:
    """Split on heading lines. Returns [{name, lines:[(page, text)]}]; a heading right after 'BUILDING CODE' is a page title."""
    secs, cur, prev = [], None, ""
    for pno, text in enumerate(pages, 1):
        for ln in text.split("\n"):
            s = ln.strip()
            if not s:
                continue
            if HEADING.match(s) and not prev.upper().endswith("CODE"):
                cur = {"name": s.lower().rstrip("s") if s.lower().startswith("condition") else s.lower(), "lines": []}
                secs.append(cur)
            elif cur is not None:
                cur["lines"].append((pno, s))
            prev = s
    return secs


def _join(lines) -> str:
    return normalise(" ".join(t for _, t in lines))


def _trim(text: str) -> str:
    """Cut the signature block / boilerplate that follows the last condition (the result stays a prefix of the source)."""
    m = TRAILER.search(text)
    return text[:m.start()].rstrip() if m else text


TRAILER = re.compile(r"\s*(To sign up for our List Subscription|\[Original signed\]|\[original signed\]|Issued by the|Classification: Public|Superseded in|"
                     r"This (?:variance|VARIANCE) (?:is applicable|applies))", re.I)
TWO_LEVEL = re.compile(r"^\s*(\d{1,2})\.(\d{1,2})\.\s+(\S.*)$")
ITEM_LABEL = re.compile(r"^\s*[\xad\u2022\-\u2013]?\s*\d{1,2}(?:\.\d{1,3})+\.?\s+")


def _conditions(lines) -> list[dict]:
    """Conditions of a variance. Two numbering styles occur: flat '1.', '2.', ... or sectioned items '1.1.', '1.2.', '2.1.'.
    Continuation lines (including deeper sub-items and bullets) join the item above; text is not altered."""
    items = [i for i, (_, s) in enumerate(lines) if TWO_LEVEL.match(s)]
    out = []
    if len(items) >= 3:
        for i, (pno, s) in enumerate(lines):
            m = TWO_LEVEL.match(s)
            if m:
                out.append({"label": f"{m.group(1)}.{m.group(2)}", "text": m.group(3), "page": pno})
            elif out and not re.match(r"^\s*\d{1,2}\.\s+\S", s):
                out[-1]["text"] += " " + s
    else:
        expect = 1
        for pno, s in lines:
            m = NUMBERED.match(s)
            if m and int(m.group(1)) == expect:
                out.append({"label": str(expect), "text": m.group(2), "page": pno})
                expect += 1
            elif out:
                out[-1]["text"] += " " + s
    for n, c in enumerate(out, 1):
        c["index"], c["text"] = n, normalise(c["text"])
    if out:
        out[-1]["text"] = _trim(out[-1]["text"])
    return [{"index": c["index"], "label": c["label"], "text": c["text"], "page": c["page"]} for c in out]


def _strip_labels(lines) -> str:
    """Variance text with its own item numbering removed so '5.3.4.1.' is not read as a code citation."""
    return normalise(" ".join(ITEM_LABEL.sub("", t) for _, t in lines))


def _article_code(a: str):
    if verifier.article_exists(a) or verifier.article_exists("C:" + a) or verifier.article_exists("A:" + a):
        return "NBC"
    for k in ("nfc", "npc", "necb"):
        if verifier_codes.article_exists(k, a):
            return k.upper()
    return None


def _articles(texts: list[str]) -> tuple[list[str], list[str], dict]:
    found = list(dict.fromkeys(a for t in texts for a in ART_RE.findall(t)))
    codes = {a: _article_code(a) for a in found}
    ok = [a for a in found if codes[a]]
    return ok, [a for a in found if not codes[a]], {a: codes[a] for a in ok}


def _numbers(item: dict) -> list[str]:
    return [n.strip() for n in re.split(r"/", item["number"]) if re.match(r"^\d\d-[A-Z]{3}-", n.strip())] or [item["number"]]


def _base(n: str) -> str:
    return REV.sub("", n)


def _date_key(d: str):
    m = re.match(r"([A-Za-z]+)\s+(\d{4})", d or "")
    return (int(m.group(2)), MONTHS.index(m.group(1).lower())) if m and m.group(1).lower() in MONTHS else (0, 0)


def parse_variance_text(pages: list[str], item: dict) -> dict:
    secs = _sections(pages)
    get = lambda *names: [s for s in secs if s["name"] in names]
    purpose = _join([l for s in get("purpose", "introduction") for l in s["lines"]])
    discussion = _join([l for s in get("discussion") for l in s["lines"]])
    application = _join([l for s in get("application") for l in s["lines"]])
    var_lines = [l for s in get("variance", "condition") for l in s["lines"]]
    variance_text = _trim(_join(var_lines))
    variance_parts = [_trim(_join(sec["lines"])) for sec in get("variance", "condition") if sec["lines"]]
    refs = _join([l for s in get("code reference", "code references") for l in s["lines"]])
    arts, bad, acodes = _articles([purpose, refs, _strip_labels(var_lines)])
    nums = _numbers(item)
    stem = Path(item["file_path"]).stem
    reasons = []
    if not purpose:
        reasons.append("no Purpose section found")
    if not variance_text:
        reasons.append("no Variance section found")
    return {
        "id": stem, "number": item["number"], "numbers": nums, "title": item["title"], "kind": "variance",
        "edition": item["edition"], "date_issued": item["date_issued"],
        "revision": (REV.search(nums[0]).group(0) if REV.search(nums[0]) else ""),
        "purpose": purpose, "discussion": discussion, "variance_text": variance_text, "variance_parts": variance_parts,
        "articles_varied": arts, "articles_unverified": bad, "article_codes": acodes,
        "conditions": _conditions(var_lines),
        "applies_to": application, "pdf": item["file_path"], "source": item.get("source"),
        "current": True, "superseded_by": None,
        "needs_review": bool(reasons), "review_reasons": reasons,
        "extraction_confidence": 1.0 if not reasons else 0.4,
    }


def parse_variance_file(path, item: dict) -> dict:
    return parse_variance_text(read_pdf_pages(path), item)


def _mark_current(cards: list[dict]) -> None:
    groups: dict[tuple, list[dict]] = {}
    for c in cards:
        groups.setdefault(tuple(sorted(_base(n) for n in c["numbers"])), []).append(c)
    for g in groups.values():
        g.sort(key=lambda c: _date_key(c["date_issued"]))
        for c in g[:-1]:
            c["current"], c["superseded_by"] = False, g[-1]["id"]


def build_all(write: bool = True) -> dict:
    idx = json.load(open(INDEX, encoding="utf8"))
    items = [i for i in idx["items"] if i["kind"] == "variance"]
    over = json.load(open(OVERRIDES, encoding="utf8")) if OVERRIDES.exists() else {}
    cards = [parse_variance_file(ROOT / i["file_path"], i) for i in items]
    _mark_current(cards)
    for c in cards:
        for k, v in (over.get(c["id"]) or {}).items():
            c[k] = v
        if c["id"] in over:
            c["needs_review"], c["review_reasons"] = False, []
    ids = Counter(c["id"] for c in cards)
    assert max(ids.values()) == 1, "duplicate card ids"
    report = {
        "total": len(cards), "by_edition": dict(Counter(c["edition"] for c in cards)),
        "parsed": sum(not c["needs_review"] for c in cards),
        "needs_review": [{"id": c["id"], "reasons": c["review_reasons"]} for c in cards if c["needs_review"]],
        "unverified_articles": {c["id"]: c["articles_unverified"] for c in cards if c["articles_unverified"]},
        "no_numbered_conditions": [c["id"] for c in cards if not c["conditions"]],
        "overridden": sorted(over),
    }
    if write:
        OUT.mkdir(parents=True, exist_ok=True)
        for p in OUT.glob("*.json"):
            if not p.name.startswith("_"):
                p.unlink()
        for c in cards:
            json.dump(c, open(OUT / f"{c['id']}.json", "w", encoding="utf8"), indent=1, ensure_ascii=False)
        json.dump(report, open(OUT / "_report.json", "w", encoding="utf8"), indent=1, ensure_ascii=False)
        if not OVERRIDES.exists():
            OVERRIDES.write_text("{}\n", encoding="utf8")
    return report


if __name__ == "__main__":
    r = build_all()
    print(json.dumps({k: (v if k in ("total", "by_edition", "parsed") else len(v)) for k, v in r.items()}, indent=1))
