"""Build the precedents corpus (issued variances, interpretations, policies, advisories, guides).

Run from app/backend:  .venv/Scripts/python.exe -X utf8 -I -m corpus.build_precedents
Reads files/ (Calgary advisories, Edmonton policies, background, pages, Act, users guide) and reuses the
existing STANDATA chunks in app/data/corpus/chunks.jsonl. Writes app/data/corpus/precedents_chunks.jsonl and
precedents_report.json. Real text only: titles come from the documents; when a document has no recognisable
heading the title is derived from the file name and title_from_filename is true.
"""
from __future__ import annotations
import hashlib, json, re, sys
from collections import Counter
from html.parser import HTMLParser

from . import DATA, FILES
from . import verifier

OUT = DATA / "precedents_chunks.jsonl"
REPORT = DATA / "precedents_report.json"
STANDATA_INDEX = DATA.parent / "content" / "standata_index.json"

CITE = re.compile(r"(?<![\d.])(\d{1,2}\.\d{1,2}\.\d{1,2}\.\d{1,3})(?![\d])")
BIDI = dict.fromkeys(map(ord, "‪‫‬‭‮‎‏⁦⁧⁨⁩﻿"))
LEGAL = re.compile(r"[^.]*\bno legal status\b[^.]*\.", re.I)
MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
DATE = re.compile(rf"\b((?:{MONTHS})\.?\s+\d{{1,2}},?\s+\d{{4}}|(?:{MONTHS})\s+\d{{4}})", re.I)


def clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").translate(BIDI)).strip()


def chunk_words(text: str, lo=200, hi=400, target=300):
    w = text.split()
    if len(w) < 25:
        return []
    if len(w) <= hi:
        return [" ".join(w)]
    n = -(-len(w) // target)
    size = -(-len(w) // n)
    return [" ".join(w[i:i + size]) for i in range(0, len(w), size)]


def cites(text: str):
    seen, ok, bad = set(), [], []
    for m in CITE.finditer(text):
        a = m.group(1)
        if a in seen:
            continue
        seen.add(a)
        (ok if verifier.article_exists(a) else bad).append(a)
    return ok, bad


def stem_title(fn: str) -> str:
    t = re.sub(r"\.(pdf|html?)$", "", fn)
    return re.sub(r"[-_]+", " ", t).strip()


def pdf_pages(path):
    import pymupdf
    d = pymupdf.open(str(path))
    try:
        return [clean(p.get_text()) for p in d]
    finally:
        d.close()


def raw_first_lines(path, n=40):
    import pymupdf
    d = pymupdf.open(str(path))
    try:
        t = d[0].get_text().translate(BIDI) if len(d) else ""
    finally:
        d.close()
    return [l.strip() for l in t.splitlines() if l.strip()][:n]


def find_title(lines, kind):
    """Document's own heading, else None."""
    if kind == "calgary":
        for i, l in enumerate(lines):
            if re.match(r"^(Subject|Title)\s*:", l, re.I):
                rest = l.split(":", 1)[1].strip()
                j = i + 1
                while not rest and j < len(lines):
                    rest, j = lines[j].strip(), j + 1
                if rest and j < len(lines) and not re.match(r"^(Background|Purpose|Issue|Date|Scope)\b", lines[j], re.I) \
                        and len(rest) < 60 and not rest.endswith((".", ":")) and lines[j][:1].islower():
                    rest += " " + lines[j]
                return rest
        for l in lines:
            if re.match(r"^(Building|Plumbing|Gas|Electrical|Fire)?\s*Advisory\s+[A-Z]?\d", l):
                return l
        return None
    for l in lines:
        if re.match(r"^B\d\d-\d\d\w?\s+\S", l):
            return l
    skip = re.compile(r"(^(PROCEDURE|INTENT|POLICY|DISCUSSION|SCOPE|SUMMARY|PURPOSE)|archived|Edmonton|Development Services|URBAN PLANNING|Floor|Avenue|AB\s+T\d|^Policy\b.*\d$|^POLICY$|^DISCUSSION$|^Page)", re.I)
    for i, l in enumerate(lines):
        if "edmonton.ca" in l.lower() and i + 1 < len(lines) and len(lines[i + 1]) > 12                 and not skip.search(lines[i + 1]):
            return lines[i + 1]
    for l in lines:
        if len(l) > 8 and l.upper() == l and not skip.search(l):
            return l
    return None


class _H(HTMLParser):
    def __init__(self):
        super().__init__()
        self.skip = 0
        self.parts, self.title, self._in_title, self.h1 = [], "", False, ""
        self._in_h1 = False

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "svg", "nav", "footer", "header"):
            self.skip += 1
        if tag == "title":
            self._in_title = True
        if tag == "h1":
            self._in_h1 = True
        if tag in ("p", "li", "div", "br", "tr", "h1", "h2", "h3", "h4"):
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "svg", "nav", "footer", "header") and self.skip:
            self.skip -= 1
        if tag == "title":
            self._in_title = False
        if tag == "h1":
            self._in_h1 = False

    def handle_data(self, d):
        if self._in_title:
            self.title += d
        if self._in_h1 and not self.h1:
            self.h1 += d
        if not self.skip:
            self.parts.append(d)


def build():
    chunks, failures, docs = [], [], Counter()
    seen_text = set()

    def add(source_type, jur, title, tfn, doc, page, text, issue_date=None, legal=None, extra=None):
        ok, bad = cites(text)
        n = sum(1 for c in chunks if c["doc"] == doc)
        rec = {"id": f"{source_type}:{re.sub(r'[^a-z0-9]+', '_', doc.lower()).strip('_')[-40:]}-{hashlib.md5(doc.encode()).hexdigest()[:6]}~{page}-{n}",
               "source_type": source_type, "jurisdiction": jur, "title": title, "title_from_filename": tfn,
               "doc": doc, "page": page, "issue_date": issue_date, "legal_status_note": legal,
               "articles_cited": ok, "articles_unverified": bad, "text": text}
        if extra:
            rec.update(extra)
        chunks.append(rec)

    def do_pdf(path, source_type, jur, kind, rel):
        try:
            pages = pdf_pages(path)
            if not any(len(p) > 40 for p in pages):
                raise ValueError("no extractable text")
            lines = raw_first_lines(path)
            t = find_title(lines, kind) if source_type in ("calgary_advisory", "edmonton_policy", "act") else None
            if source_type == "act":
                t = "SAFETY CODES ACT"
            tfn = not t
            title = clean(t) if t else stem_title(path.name)
            full = " ".join(pages)
            m = LEGAL.search(full)
            legal = clean(m.group(0)) if (m and jur == "calgary") else None
            dm = DATE.search(" ".join(lines[:25])) or DATE.search(full[:1500])
            date = clean(dm.group(1)) if dm else None
            lm = re.search(r"(?<![A-Za-z0-9])([ABGP]\d{2}[-_]\d{2,3}G?)(?![0-9])", path.name, re.I)                 if source_type in ("calgary_advisory", "edmonton_policy") else None
            num = lm.group(1).upper().replace("_", "-") if lm else None
            label = (("Calgary Advisory " if jur == "calgary" else "Edmonton Policy ") + num) if num else None
            ex = {"number": num, "label": label} if num else None
            for pno, ptxt in enumerate(pages, 1):
                for c in chunk_words(ptxt):
                    add(source_type, jur, title, tfn, rel, pno, c, date, legal, ex)
            docs[source_type] += 1
        except Exception as e:
            failures.append({"file": rel, "error": f"{type(e).__name__}: {e}"})

    for p in sorted((FILES / "calgary_advisories").glob("*.pdf")):
        do_pdf(p, "calgary_advisory", "calgary", "calgary", f"calgary_advisories/{p.name}")
    for p in sorted((FILES / "edmonton_policy_solutions").glob("*.pdf")):
        do_pdf(p, "edmonton_policy", "edmonton", "edmonton", f"edmonton_policy_solutions/{p.name}")
    for p in sorted((FILES / "background").glob("*.pdf")):
        do_pdf(p, "nrc_background", "national", "other", f"background/{p.name}")
    act = FILES / "direct" / "01_Safety_Codes_Act.pdf"
    if act.exists():
        do_pdf(act, "act", "alberta", "other", "direct/01_Safety_Codes_Act.pdf")
    else:
        failures.append({"file": "direct/01_Safety_Codes_Act.pdf", "error": "missing"})
    g = FILES / "guides" / "Illustrated_Users_Guide_NBC2020_Part9.pdf"
    if g.exists():
        do_pdf(g, "users_guide", "national", "other", "guides/Illustrated_Users_Guide_NBC2020_Part9.pdf")
    else:
        failures.append({"file": "guides/Illustrated_Users_Guide_NBC2020_Part9.pdf", "error": "missing"})

    for p in sorted((FILES / "pages").glob("*.html")):
        rel = f"pages/{p.name}"
        try:
            h = _H()
            h.feed(p.read_text(encoding="utf8", errors="replace"))
            text = clean(" ".join(h.parts))
            t = clean(h.h1) or clean(h.title)
            if t.lower() == "server error":
                raise ValueError("saved page is a 'Server Error' page, not content; skipped")
            for c in chunk_words(text):
                add("web_page", "alberta", t or stem_title(p.name), not t, rel, 1, c)
            if not chunk_words(text):
                raise ValueError("no extractable text")
            docs["web_page"] += 1
        except Exception as e:
            failures.append({"file": rel, "error": f"{type(e).__name__}: {e}"})

    # STANDATA: reuse existing chunks, titles from the index
    idx = {i["source"]["doc"]: i for i in json.load(open(STANDATA_INDEX, encoding="utf8"))["items"]}
    kinds = {"variance": "standata_variance", "interpretation": "standata_interpretation",
             "bulletin": "standata_bulletin", "errata": "standata_bulletin"}
    sd = set()
    for line in open(DATA / "chunks.jsonl", encoding="utf8"):
        c = json.loads(line)
        if not c["id"].startswith("standata:"):
            continue
        base = c["doc"].split("/")[-1]
        it = idx.get(base)
        if not it:
            failures.append({"file": c["doc"], "error": "chunk without standata_index entry"})
            continue
        sd.add(base)
        title = it["title"]
        text = clean(c["text"])
        add(kinds[it["kind"]], "alberta", title, it.get("title_source") == "filename", c["doc"], c["page"], text,
            it.get("date_issued"), None, {"number": it["number"], "label": f"STANDATA {it['number']}"})
    for b in sd:
        docs[kinds[idx[b]["kind"]]] += 1
    missing = [b for b in idx if b not in sd]
    for b in missing:
        failures.append({"file": b, "error": "no chunks in chunks.jsonl for this STANDATA document"})

    with open(OUT, "w", encoding="utf8") as fh:
        for c in chunks:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")
    per = Counter(c["source_type"] for c in chunks)
    with_c = sum(1 for c in chunks if c["articles_cited"])
    unver = sum(len(c["articles_unverified"]) for c in chunks)
    ver = sum(len(c["articles_cited"]) for c in chunks)
    rep = {"chunks": len(chunks), "documents_per_type": dict(docs), "chunks_per_type": dict(per),
           "failures": failures,
           "citation_coverage": {"chunks_with_verified_citation": with_c, "verified_refs": ver, "unverified_refs": unver,
                                 "unverified_note": "Refs matching the article pattern but absent from nbc_articles.json (other codes, table numbers or dates); kept in articles_unverified, never shown as citations."},
           "titles_from_filename": sorted({c["doc"] for c in chunks if c["title_from_filename"]})}
    json.dump(rep, open(REPORT, "w", encoding="utf8"), indent=1, ensure_ascii=False)
    return rep


if __name__ == "__main__":
    r = build()
    print(json.dumps({k: r[k] for k in ("chunks", "documents_per_type", "chunks_per_type", "failures")}, indent=1))
    print("titles from filename:", len(r["titles_from_filename"]))
