"""Generic article-index extractor for NFC(AE) 2023, NPC 2020 and NECB 2020 (same method as extract_nbc.py).

Per code it writes (app/data/corpus):
  <code>_articles.json   articles keyed "2.4.1.1" (Division B) / "A:1.4.1.2" (Division A) / "C:..." (Division C)
  <code>_intents.json    intent statements from the code's Intent Supplement
and, once for all three codes:
  other_codes_objectives.json   Division A objective / functional statements (+ NECB's own)
  extract_codes_report.json     counts, text-check failure rates, attribution coverage, honest failures
and in app/backend/corpus:
  chunks_codes.jsonl            text chunks for the three codes and the NECB User's Guide

Attributions are not inline; they are in the per-Part tables "Objectives and Functional Statements
Attributed to the Acceptable Solutions". Those are two-column ruled tables (article rows span the full
column width, sentence rows have a narrow "(n)" cell), parsed with word coordinates and the horizontal rules.

Run (from app/backend):  python -X utf8 -m corpus.extract_codes nfc|npc|necb|all
"""
import json
import re
import sys
from collections import defaultdict

import pymupdf

from . import DATA, FILES

HERE = DATA.parent.parent / "backend" / "corpus"

CODES = {
    "nfc": {"code": "NFC(AE) 2023", "pdf": "NFC_2023AE.pdf", "intent_pdf": "NFC_Intent_Supplement.pdf",
            "intent_edition": "NFC Intent Supplement (National Fire Code of Canada 2020 / AE 2023 intent text)"},
    "npc": {"code": "NPC 2020", "pdf": "NPC_2020.pdf", "intent_pdf": "NPC_Intent_Supplement.pdf",
            "intent_edition": "NPC 2020 Intent Supplement"},
    "necb": {"code": "NECB 2020", "pdf": "NECB_2020_2nd_printing.pdf", "intent_pdf": "NECB_2020_Intent_Supplement.pdf",
             "intent_edition": "NECB 2020 Intent Supplement"},
}
GUIDE_PDF = FILES / "guides" / "NECB_2020_Users_Guide.pdf"
HDR_Y, FTR_Y = 55, 765

RE_ART = re.compile(r"^(\d+\.\d+\.\d+\.\d+)\.$")
RE_ART_ROW = re.compile(r"^(\d+\.\d+\.\d+\.\d+)\.(?:\s+(.*))?$")
RE_SUB = re.compile(r"^(\d+\.\d+\.\d+)\.$")
RE_SEC = re.compile(r"^Section (\d+\.\d+)\.")
RE_PART = re.compile(r"^Part (\d+)$")
RE_SENT = re.compile(r"^(\d+)\)(?:\s+(.*))?$")
RE_SENT_ONLY = re.compile(r"^(\d+)\)$")
RE_CLAUSE = re.compile(r"^([a-z]|[ivx]+|[A-Z])\)(?:\s+|$)")
RE_DIV = re.compile(r"Division ([ABC])\b")
RE_TABLE_LABEL = re.compile(r"^Table [0-9][0-9.]*[0-9.]?(?:-[A-Z])?\.?(?: \(Continued\))?$|^Table [0-9][0-9.]*(?:-[A-Z])?\. ")
RE_ATTR = re.compile(r"(?P<cl>(?:\([a-z0-9]+\)\s*,?\s*)+)?\[(?P<codes>[^\]]+)\]")


def norm(s):
    return re.sub(r"\s+", " ", s.replace("­", "").replace("​", "")).strip()


# ------------------------------------------------------------ page helpers
def page_blocks(page):
    out = []
    for b in page.get_text("blocks"):
        x0, y0, x1, y1, txt = b[:5]
        if y0 < HDR_Y or y1 > FTR_Y or x0 < 30:
            continue
        out.append((y0, x0, txt))
    out.sort()
    return out


def page_division(page):
    for b in page.get_text("blocks"):
        if b[1] < HDR_Y and b[0] > 30:
            m = RE_DIV.search(b[4])
            if m:
                return m.group(1)
    return None


def is_attr_table_page(page):
    t = page.get_text()
    return "Functional Statements and Objectives" in t or "Functional Statements and\nObjectives" in t


def expand_codes(raw):
    raw = raw.replace(" ", "")
    if "-" not in raw:
        return [raw]
    left, right = raw.split("-", 1)
    fs = [x for x in left.split(",") if x]
    os_ = [x for x in right.split(",") if x]
    return [f"{f}-{o}" for f in fs for o in os_]


def parse_attr_text(text):
    text = re.sub(r"\s+", " ", text).strip()
    ms = list(RE_ATTR.finditer(text))
    res = []
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(text)
        applies = text[m.end():end].strip()
        res.append({"clauses": re.sub(r"\s+", "", m.group("cl") or "") or None,
                    "raw": "[" + m.group("codes") + "]",
                    "codes": expand_codes(m.group("codes")),
                    "applies_to": applies or None})
    return res


# ---------------------------------------------------------------- body text
def build_sentences(lines):
    """lines -> (preamble_notes, [{number,text}]) using the 1,2,3 ... sequence rule.
    Sentence numbers may be alone on a line ("1)") or lead the text ("1) text")."""
    notes, sents = [], []
    cur, expected = None, 1
    for ln in lines:
        m = RE_SENT.match(ln)
        if m and int(m.group(1)) == expected:
            cur = {"number": expected, "parts": []}
            if m.group(2):
                cur["parts"].append(m.group(2))
            sents.append(cur)
            expected += 1
            continue
        if cur is None:
            notes.append(ln)
        else:
            cur["parts"].append(ln)
    out = []
    for s in sents:
        txt = ""
        for p in s["parts"]:
            if RE_CLAUSE.match(p):
                txt += "\n" + RE_CLAUSE.sub(lambda mm: mm.group(1) + ") ", p, count=1)
            elif txt.endswith(" ") or not txt or txt.endswith("\n"):
                txt += p
            else:
                txt += " " + p
        out.append({"number": s["number"], "text": txt.strip()})
    return notes, out


def parse_body(doc, log):
    arts = {}
    ctx = {"part_title": None, "section_title": None, "sub_title": None}
    cur = None
    in_table = False
    for pi, page in enumerate(doc):
        div = page_division(page)
        if div is None:
            continue
        blocks = page_blocks(page)
        if sum(1 for _, _, t in blocks if "......" in t) >= 3:      # table of contents
            continue
        rot = [b for b in page.get_text("blocks")
               if b[0] > 30 and (b[3] - b[1]) > 3 * (b[2] - b[0]) and RE_TABLE_LABEL.match(norm(b[4]))]
        if rot and not is_attr_table_page(page):
            # landscape (rotated) table page: block order is not reading order, keep as raw page text
            if cur is not None:
                if pi + 1 not in cur["pdf_pages"]:
                    cur["pdf_pages"].append(pi + 1)
                cur["tables"].append({"title": norm(rot[0][4]), "rotated_page": pi + 1, "lines":
                                      [l.strip() for l in page.get_text().split(chr(10)) if l.strip()][:400]})
                in_table = True
            continue
        if is_attr_table_page(page):
            # mixed page: body text may precede the attribution table; cut at the table title block
            cut = None
            for y0, x0, txt in blocks:
                t = norm(txt)
                if re.match(r"^Table \d+\.\d+\.\d+\.\d+\.", t) and ("Attributed to" in t or "(Continued)" in t):
                    cut = y0
                    break
            if cut is None:
                cur = None
                continue
            blocks = [b for b in blocks if b[0] < cut - 1]
        for y0, x0, txt in blocks:
            lines = [l.strip() for l in txt.split("\n") if l.strip()]
            if not lines:
                continue
            first = lines[0]
            is_head = x0 <= 80 and len(lines) <= 6
            if is_head and RE_PART.match(first) and len(lines) <= 3:
                ctx["part_title"] = " ".join(lines[1:])
                cur = None
                continue
            if is_head and RE_SEC.match(first):
                ctx["section_title"] = re.sub(r"^Section \d+\.\d+\.\s*", "", " ".join(lines)).strip()
                cur = None
                continue
            if is_head and RE_ART.match(first) and len(lines) >= 2 and not RE_SENT.match(lines[1]):
                num = RE_ART.match(first).group(1)
                ti, rest = [], []
                for j, l in enumerate(lines[1:], 1):
                    if RE_SENT.match(l) or l.startswith("(See"):
                        rest = lines[j:]
                        break
                    ti.append(l)
                key = num if div == "B" else f"{div}:{num}"
                if key in arts:
                    log.append(f"duplicate heading {key} on pdf page {pi+1} (kept first, page {arts[key]['pdf_page']})")
                    cur = None
                    continue
                parts = num.split(".")
                cur = {"number": num, "title": " ".join(ti), "division": div,
                       "part": parts[0], "part_title": ctx["part_title"],
                       "section": ".".join(parts[:2]), "section_title": ctx.get("section_title"),
                       "subsection": ".".join(parts[:3]), "subsection_title": ctx["sub_title"],
                       "pdf_page": pi + 1, "pdf_pages": [pi + 1], "_lines": list(rest), "tables": []}
                arts[key] = cur
                in_table = False
                continue
            if is_head and RE_SUB.match(first) and len(lines) >= 2 and not RE_SENT.match(lines[1]):
                ctx["sub_title"] = " ".join(lines[1:])
                cur = None
                continue
            if cur is None:
                continue
            if re.match(r"^A-\d", first) or first.startswith("Notes to Part"):     # appendix notes: stop
                cur = None
                continue
            if pi + 1 not in cur["pdf_pages"]:
                cur["pdf_pages"].append(pi + 1)
            if RE_TABLE_LABEL.match(first) and (x0 < 240 or len(lines) <= 3):
                in_table = True
                cur["tables"].append({"title": " ".join(lines[:2]), "lines": []})
                continue
            if in_table:
                m = RE_SENT.match(first)
                nxt = len([l for l in cur["_lines"] if RE_SENT.match(l)]) + 1
                if m and int(m.group(1)) == nxt and x0 >= 100:
                    in_table = False
                else:
                    if cur["tables"]:
                        cur["tables"][-1]["lines"].append(" | ".join(lines))
                    continue
            cur["_lines"].extend(lines)
    return arts


def finish_body(arts, code_label, doc_name):
    for key, a in arts.items():
        notes, sents = build_sentences(a.pop("_lines"))
        a["key"] = key
        a["code"] = code_label
        a["notes"] = notes
        a["sentences"] = sents
        a["attributions"] = []
        a["source"] = {"doc": doc_name, "page": a["pdf_page"]}
        for s in sents:
            s["attributions"] = []
            s["attribution_detail"] = []


# ------------------------------------------------------- attribution tables
def hrules(page):
    out = []
    for d in page.get_drawings():
        r = d["rect"]
        if r.height <= 2 and r.width >= 20:
            out.append((round(r.x0), round(r.x1), (r.y0 + r.y1) / 2))
    return out


def parse_attr_tables(doc, arts, divisions=("B",)):
    """Two-column ruled tables. Row kinds: article row ("2.4.1.1. Title [optional article-level attribution]"),
    sentence row ("(n)" in the narrow left cell, attributions in the wide cell)."""
    stats = {"pages": 0, "rows": 0, "sentence_rows": 0, "article_level_rows": 0, "attributed_sentences": 0,
             "rows_before_any_article": 0, "unmatched": [], "pages_without_table_geometry": []}
    cur_art = None
    rows_out = []
    for pi, page in enumerate(doc):
        if not is_attr_table_page(page) or page_division(page) not in divisions:
            continue
        stats["pages"] += 1
        words = [w for w in page.get_text("words") if w[0] > 30 and HDR_Y < w[1] < FTR_Y]
        wide = [r for r in hrules(page) if 200 < r[1] - r[0] < 260]
        cols = sorted(set(r[0] for r in wide))
        merged = []
        for c in cols:
            if not merged or c - merged[-1] > 40:
                merged.append(c)
        if not merged:
            stats["pages_without_table_geometry"].append(pi + 1)
        for cl in merged:
            mine = [r for r in wide if abs(r[0] - cl) <= 3]
            ys = sorted(set(round(r[2], 1) for r in mine))
            width = max(r[1] - r[0] for r in mine)
            num_x = cl + 38
            cw = [w for w in words if cl - 3 <= w[0] < cl + width]
            for ya, yb in zip(ys, ys[1:]):
                if yb - ya < 5:
                    continue
                rw = [w for w in cw if ya < (w[1] + w[3]) / 2 < yb]
                if not rw:
                    continue
                rw.sort(key=lambda w: (round(w[1]), w[0]))
                lines = []
                for w in rw:
                    if lines and abs(lines[-1][0] - w[1]) < 3:
                        lines[-1][1].append(w)
                    else:
                        lines.append([w[1], [w]])
                ltxt = [" ".join(x[4] for x in sorted(ws, key=lambda w: w[0])) for _, ws in lines]
                if ltxt[0].startswith("Provision") or ltxt[0].startswith("Functional Statements"):
                    continue
                if ltxt[0].startswith("Table") or ltxt[0].split(" ")[0] in ("Forming", "Acceptable", "Objectives"):
                    continue
                stats["rows"] += 1
                m = RE_ART_ROW.match(ltxt[0])
                if m and rw[0][0] < cl + 8:
                    cur_art = m.group(1)
                    rest = [m.group(2) or ""] + ltxt[1:]
                    attr_txt = " ".join(l for l in rest if "[" in l)
                    if attr_txt:
                        rows_out.append((cur_art, None, attr_txt, pi + 1))
                    continue
                num = None
                keep = []
                for _, ws in lines:
                    out = []
                    for w in sorted(ws, key=lambda w: w[0]):
                        if num is None and w[0] < num_x and re.match(r"^\(\d+\)$", w[4]):
                            num = int(w[4][1:-1])
                        else:
                            out.append(w[4])
                    keep.append(" ".join(out))
                attr_txt = " ".join(keep)
                if cur_art is None:
                    stats["rows_before_any_article"] += 1
                    continue
                if num is None and "[" not in attr_txt:
                    continue
                rows_out.append((cur_art, num, attr_txt, pi + 1))
    for art, num, attr_txt, pg in rows_out:
        entries = parse_attr_text(attr_txt)
        if not entries:
            continue
        a = arts.get(art)
        if a is None:
            stats["unmatched"].append(f"{art}({num}) p{pg}: article not in body parse")
            continue
        for e in entries:
            e["table_pdf_page"] = pg
        if num is None:
            a.setdefault("article_level_attributions", []).extend(entries)
            stats["article_level_rows"] += 1
            continue
        stats["sentence_rows"] += 1
        tgt = [s for s in a["sentences"] if s["number"] == num]
        if not tgt:
            stats["unmatched"].append(f"{art}({num}) p{pg}: sentence not in body parse")
            continue
        s = tgt[0]
        s["attribution_detail"].extend(entries)
        for e in entries:
            for c in e["codes"]:
                if c not in s["attributions"]:
                    s["attributions"].append(c)
    for a in arts.values():
        u = []
        for s in a["sentences"]:
            for c in s["attributions"]:
                if c not in u:
                    u.append(c)
        for e in a.get("article_level_attributions", []):
            for c in e["codes"]:
                if c not in u:
                    u.append(c)
        a["attributions"] = u
        stats["attributed_sentences"] += sum(1 for s in a["sentences"] if s["attributions"])
    return stats


# ------------------------------------------------------------- text check
def text_check(doc, arts):
    """First 50 / last 40 chars of the parsed text must appear (whitespace-normalised) in the article's PDF pages."""
    cache = {}

    def pt(p):
        if p not in cache:
            cache[p] = norm(doc[p - 1].get_text())
        return cache[p]

    checked, fails, empty = 0, [], []
    for k, a in arts.items():
        if not a["sentences"]:
            empty.append(k)
            continue
        checked += 1
        blob = " ".join(pt(p) for p in a["pdf_pages"])
        t_first = norm(a["sentences"][0]["text"])[:50]
        t_last = norm(a["sentences"][-1]["text"])[-40:]
        if t_first not in blob or t_last not in blob:
            fails.append(k)
    return {"checked": checked, "failed": len(fails), "failure_rate": round(len(fails) / max(checked, 1), 4),
            "failed_keys": fails, "articles_without_sentences": empty}


# ------------------------------------------------------ objectives / functions
RE_OBJ_TOP = re.compile(r"^(O[A-Z]\d*)(?:\s+(\S.*))?$")
RE_OBJ_SUB = re.compile(r"^(O[A-Z]\d+\.\d+)\s+[–—-]\s*(.*)$")
RE_NOISE = re.compile(r"^(Division [ABC]|National .* Code.*|\d+-\d+|\d+\.\d+\.\d+\.\d+\.|© .*)$")


def division_a_lines(doc, first, last):
    out = []
    for pn in range(first, last + 1):
        page = doc[pn - 1]
        if page_division(page) != "A":
            continue
        for y0, x0, txt in page_blocks(page):
            for l in txt.split("\n"):
                l = l.strip()
                if l and not RE_NOISE.match(l):
                    out.append((pn, l))
    return out


def find_page(doc, needle, start=1):
    for pn in range(start, len(doc) + 1):
        if page_division(doc[pn - 1]) == "A" and needle in norm(doc[pn - 1].get_text()):
            return pn
    return None


def parse_objectives(doc):
    p0 = find_page(doc, "The objectives of this Code are as follows")
    p1 = find_page(doc, "The objectives of this Code are achieved by measures", p0)
    lines = division_a_lines(doc, p0, p1)
    start = next(i for i, (_, l) in enumerate(lines) if "The objectives of this Code are as follows" in l)
    lines = lines[start + 1:]
    res, cur, i = {}, None, 0
    while i < len(lines):
        pn, l = lines[i]
        if l.startswith("Notes to Part") or re.match(r"^(Section )?2\.3\.", l) or l.startswith("Section 3."):
            break
        ms = RE_OBJ_SUB.match(l)
        if ms:
            code = ms.group(1)
            cur = {"code": code, "kind": "risk", "title": None, "text": ms.group(2).strip(), "pdf_page": pn,
                   "parent": re.match(r"^(O[A-Z]\d+)", code).group(1)}
            res[code] = cur
            i += 1
            continue
        mt = RE_OBJ_TOP.match(l)
        if mt and re.fullmatch(r"O[A-Z]\d*", mt.group(1)):
            code = mt.group(1)
            title, j = (mt.group(2) or ""), i + 1
            while j < len(lines) and not lines[j][1].startswith("An objective of this Code")                     and not re.match(r"^O[A-Z]\d*(\s|$)", lines[j][1]):
                title = (title + " " + lines[j][1]).strip()
                j += 1
            cur = {"code": code, "kind": "objective", "title": title, "text": "", "pdf_page": pn, "parent": None}
            res[code] = cur
            i = j
            continue
        if cur is not None:
            cur["text"] = (cur["text"] + " " + l).strip()
        i += 1
    for r in res.values():
        r["text"] = re.sub(r"\s+", " ", r["text"])
    for r in res.values():
        if r["kind"] == "risk":
            p = res.get(r["parent"])
            r["parent_title"] = p["title"] if p else None
            r["parent_statement"] = p["text"] if p else None
    return res


def parse_functions(doc):
    p0 = find_page(doc, "The objectives of this Code are achieved by measures")
    last = p0
    for pn in range(p0, min(p0 + 14, len(doc)) + 1):
        if page_division(doc[pn - 1]) == "A":
            last = pn
        if "Notes to Part 3" in doc[pn - 1].get_text():
            last = pn
            break
    lines = division_a_lines(doc, p0, last)
    s = next(i for i, (_, l) in enumerate(lines) if re.match(r"^F\d+(\s|$)", l))
    res, cur = {}, None
    for pn, l in lines[s:]:
        if l.startswith("Notes to Part") or re.match(r"^(Section )?3\.3\.", l) or l.startswith("Section 3.3"):
            break
        m = re.match(r"^(F\d+)(?:\s+(\S.*))?$", l)
        if m:
            cur = {"code": m.group(1), "text": (m.group(2) or "").strip(), "pdf_page": pn}
            res[m.group(1)] = cur
        elif cur is not None:
            cur["text"] = (cur["text"] + " " + l).strip()
    return res


# --------------------------------------------------------------- intents
RE_PROV = re.compile(r"^Provision:\s*(\d+\.\d+\.\d+\.\d+)\.\((\d+)\)\s*$")
RE_INTENT = re.compile(r"^Intent (\d+)\.\s*(.*)$")
RE_INT_NOISE = re.compile(r"^(Intent Statements:|NFC 2020|NPC 2020|NECB 2020|\d{1,3}|© .*)$")


def vocab_from(doc):
    v = set()
    for p in doc:
        for w in re.findall(r"[A-Za-z][A-Za-z\-]+", p.get_text()):
            v.add(w.lower())
    return v


def dehyphenate(text, vocab):
    """Join 'materi- als' (line-break hyphenation). The joined form is used when it is a word seen in the code PDF;
    the hyphenated form is kept when only that is seen; otherwise joined (heuristic)."""
    def fix(m):
        a, b = m.group(1), m.group(2)
        j, h = (a + b).lower(), (a + "-" + b).lower()
        if j in vocab:
            return a + b
        if h in vocab:
            return a + "-" + b
        return a + b
    return re.sub(r"([A-Za-z]+)- ([a-z]+)", fix, text)


def parse_intents(code_key, arts, vocab):
    cfg = CODES[code_key]
    doc = pymupdf.open(str(FILES / "codes" / cfg["intent_pdf"]))
    provs = []
    cur = None
    mode = None
    for pi, page in enumerate(doc):
        for raw in page.get_text().split("\n"):
            l = raw.strip()
            if not l:
                continue
            m = RE_PROV.match(l)
            if m:
                cur = {"article": m.group(1), "sentence": int(m.group(2)), "pdf_page": pi + 1, "pdf_page_end": pi + 1,
                       "records": []}
                provs.append(cur)
                mode = None
                continue
            if cur is None or RE_INT_NOISE.match(l):
                continue
            cur["pdf_page_end"] = pi + 1
            if l == "Objective":
                cur["records"].append({"objective": "", "attrs_raw": "", "intents": []})
                mode = "obj"
                continue
            if l == "Attributions":
                mode = "attr"
                if not cur["records"]:
                    cur["records"].append({"objective": None, "attrs_raw": "", "intents": []})
                continue
            if l.startswith("Intent(s)"):
                mode = "intent"
                if not cur["records"]:
                    cur["records"].append({"objective": None, "attrs_raw": "", "intents": []})
                continue
            if mode is None or not cur["records"]:
                continue
            if mode == "obj":
                cur["records"][-1]["objective"] = ((cur["records"][-1]["objective"] or "") + " " + l).strip()
            elif mode == "attr":
                cur["records"][-1]["attrs_raw"] = (cur["records"][-1]["attrs_raw"] + " " + l).strip()
            elif mode == "intent":
                mi = RE_INTENT.match(l)
                rec = cur["records"][-1]
                if mi:
                    rec["intents"].append({"n": int(mi.group(1)), "text": mi.group(2)})
                elif rec["intents"]:
                    rec["intents"][-1]["text"] += " " + l
    out = {}
    stats = {"provisions": len(provs), "provisions_in_index": 0, "article_not_in_index": [], "sentence_not_in_index": [],
             "attribution_match_true": 0, "attribution_match_false": 0, "no_attribution_in_index": 0}
    for pv in provs:
        art = arts.get(pv["article"])
        for rec in pv["records"]:
            rec["attribution_codes_supplement"] = [c for e in parse_attr_text(rec["attrs_raw"]) for c in e["codes"]]
            rec["attributions_supplement"] = rec.pop("attrs_raw")
            for it in rec["intents"]:
                it["text"] = dehyphenate(re.sub(r"\s+", " ", it["text"]).strip(), vocab)
        e = out.setdefault(pv["article"], {"article": pv["article"], "code": cfg["code"],
                                           "intent_edition": cfg["intent_edition"],
                                           "source": {"doc": cfg["intent_pdf"], "page": pv["pdf_page"]},
                                           "status": "matched" if art else "unresolved", "provisions": []})
        if art is None:
            e["note"] = "article not found in the indexed " + cfg["code"] + " text"
            stats["article_not_in_index"].append(pv["article"])
        else:
            stats["provisions_in_index"] += 1
            s = next((x for x in art["sentences"] if x["number"] == pv["sentence"]), None)
            if s is None:
                pv["attribution_match_index"] = None
                stats["sentence_not_in_index"].append(f"{pv['article']}({pv['sentence']})")
            else:
                sc = set(c for r in pv["records"] for c in r["attribution_codes_supplement"])
                ic = set(s["attributions"])
                if not ic:
                    stats["no_attribution_in_index"] += 1
                    pv["attribution_match_index"] = None
                elif sc == ic:
                    pv["attribution_match_index"] = True
                    stats["attribution_match_true"] += 1
                else:
                    pv["attribution_match_index"] = False
                    stats["attribution_match_false"] += 1
        pv["provision"] = f"{pv['article']}.({pv['sentence']})"
        e["provisions"].append(pv)
    unresolved = []
    for k, a in arts.items():
        if a["division"] != "B" or a["number"] in out or not a["sentences"]:
            continue
        out[a["number"]] = {"article": a["number"], "code": cfg["code"], "intent_edition": cfg["intent_edition"],
                            "status": "unresolved", "provisions": [],
                            "note": "no Provision entry for this article in " + cfg["intent_pdf"]}
        unresolved.append(a["number"])
    stats["articles_with_intent"] = sum(1 for v in out.values() if v["status"] == "matched")
    stats["unresolved_articles"] = len(unresolved)
    stats["unresolved_articles_with_attributions"] = sum(1 for n in unresolved if arts[n]["attributions"])
    stats["unresolved_sample"] = unresolved[:25]
    return out, stats


# ----------------------------------------------------------------- chunks
def words_windows(words_pages, prefix, code, doc_name, out, target=300):
    i, n, total = 0, 0, len(words_pages)
    while i < total:
        j = min(i + target, total)
        if total - j < 100:
            j = total
        seg = words_pages[i:j]
        out.append({"id": f"{prefix}-{n}", "code": code, "doc": doc_name, "page": seg[0][1],
                    "text": " ".join(w for w, _ in seg)})
        n += 1
        i = j


def article_chunks(arts, code, doc_name, tag, out):
    for k, a in arts.items():
        parts = [f"{code} Article {a['number']} {a['title']} (Division {a['division']})."]
        for s in a["sentences"]:
            parts.append(f"({s['number']}) {s['text']}")
        txt = norm(" ".join(parts))
        w = txt.split(" ")
        if len(w) <= 400:
            out.append({"id": f"{tag}:{k}", "code": code, "doc": doc_name, "page": a["pdf_page"], "text": txt})
        else:
            for n, i in enumerate(range(0, len(w), 300)):
                out.append({"id": f"{tag}:{k}#{n}", "code": code, "doc": doc_name, "page": a["pdf_page"],
                            "text": " ".join(w[i:i + 300])})


def build_chunks(all_arts):
    out = []
    for key, arts in all_arts.items():
        cfg = CODES[key]
        article_chunks(arts, cfg["code"], cfg["pdf"], key, out)
        doc = pymupdf.open(str(FILES / "codes" / cfg["intent_pdf"]))
        wp = [(w, pi + 1) for pi, p in enumerate(doc) for w in norm(p.get_text()).split(" ") if w]
        words_windows(wp, f"{key}-intent", cfg["code"], cfg["intent_pdf"], out)
    if "necb" in all_arts and GUIDE_PDF.exists():
        doc = pymupdf.open(str(GUIDE_PDF))
        wp = [(w, pi + 1) for pi, p in enumerate(doc) for w in norm(p.get_text()).split(" ") if w]
        words_windows(wp, "necb-guide", CODES["necb"]["code"], GUIDE_PDF.name, out)
    return out


# ------------------------------------------------------------------ main
def run_one(key):
    cfg = CODES[key]
    doc = pymupdf.open(str(FILES / "codes" / cfg["pdf"]))
    log = []
    arts = parse_body(doc, log)
    finish_body(arts, cfg["code"], cfg["pdf"])
    stats = parse_attr_tables(doc, arts)
    tc = text_check(doc, arts)
    objectives, functions = parse_objectives(doc), parse_functions(doc)
    for o in objectives.values():
        o["source"] = {"doc": cfg["pdf"], "page": o["pdf_page"], "division": "A", "part": 2}
        o["code_name"] = cfg["code"]
    for f in functions.values():
        f["source"] = {"doc": cfg["pdf"], "page": f["pdf_page"], "division": "A", "part": 3}
        f["code_name"] = cfg["code"]
    intents, istats = parse_intents(key, arts, vocab_from(doc))
    divb = [a for a in arts.values() if a["division"] == "B"]
    with_attr = [a for a in divb if a["attributions"]]
    sents_b = sum(len(a["sentences"]) for a in divb)
    sents_attr = sum(1 for a in divb for s in a["sentences"] if s["attributions"])
    all_codes = {c for a in arts.values() for c in a["attributions"]}
    unk_o = sorted({c.split("-", 1)[1] for c in all_codes if "-" in c} - set(objectives))
    unk_f = sorted({c.split("-", 1)[0] for c in all_codes if "-" in c} - set(functions))
    by_div = defaultdict(int)
    for a in arts.values():
        by_div[a["division"]] += 1
    st = dict(stats)
    unmatched = st.pop("unmatched")
    report = {
        "code": cfg["code"], "pdf": cfg["pdf"], "pdf_pages": len(doc), "articles_total": len(arts),
        "articles_by_division": dict(by_div), "articles_with_zero_sentences": tc["articles_without_sentences"],
        "text_check": {"checked": tc["checked"], "failed": tc["failed"], "failure_rate": tc["failure_rate"],
                       "failed_keys": tc["failed_keys"]},
        "attribution": {"division_b_articles": len(divb), "division_b_articles_with_attribution": len(with_attr),
                        "division_b_sentences": sents_b, "division_b_sentences_attributed": sents_attr,
                        "sentence_coverage": round(sents_attr / max(sents_b, 1), 4),
                        "table_parse": st, "unmatched_rows": unmatched,
                        "attribution_codes_with_unknown_objective": unk_o,
                        "attribution_codes_with_unknown_function": unk_f},
        "intents": istats, "objectives": len(objectives), "functions": len(functions), "log": log,
    }
    return arts, objectives, functions, intents, report


NOTES = {
    "nfc": ["Division A and C articles are keyed 'A:1.2.3.4' / 'C:1.2.3.4' because their numbers collide with Division B (as in nbc_articles.json).",
            "The Intent Supplement is for NFC 2020 (national edition); the AE 2023 attributions are compared with it per provision (attribution_match_index).",
            "Honest failures: 1.1.2.1 fails the text check only because a '(See Note ...)' line wraps across a page break in the PDF text stream (parsed text is complete); "
            "2.14.x (Industrial Relocatable Accommodation) is Alberta-specific, so 12 national intent provisions have no AE article (kept as unresolved) and 2.14.2.1(1) attributions differ from the national supplement (attribution_match_index=false); "
            "2.5.1.3 / 2.14.1.1 have intent attributions in the supplement but none in the AE table."],
    "npc": ["Division B Part 1 (referenced-standards tables) has no attributions by design.",
            "Honest failure: in Table 2.8.1.1 the printed rows for 2.4.6.4 omit the sentence-number text of one row, so the per-sentence attributions of 2.4.6.4(2)-(4) are shifted relative to the Intent Supplement (the article-level union is correct).",
            "Division A and C articles are keyed 'A:...' / 'C:...'."],
    "necb": ["NECB is table-heavy: large data tables (lighting power density, envelope U-values, equipment efficiencies, operating times) are NOT parsed into cells; "
             "portrait tables are kept as tables[].lines (block-wise text) and landscape tables as raw page text lines (capped at 400 per page, 'rotated_page'). "
             "Sentence text is complete; table cell values must be read from the PDF page.",
             "Articles titled 'Reserved' have no sentences.",
             "Division A and C articles are keyed 'A:...' / 'C:...'."],
}


def main(argv):
    keys = list(CODES) if (not argv or argv[0] == "all") else [argv[0]]
    if any(k not in CODES for k in keys):
        print("usage: python -m corpus.extract_codes nfc|npc|necb|all")
        return 2
    DATA.mkdir(parents=True, exist_ok=True)
    rep_path = DATA / "extract_codes_report.json"
    report = json.loads(rep_path.read_text(encoding="utf8")) if rep_path.exists() else {}
    obj_path = DATA / "other_codes_objectives.json"
    objs = json.loads(obj_path.read_text(encoding="utf8")) if obj_path.exists() else {}
    for key in keys:
        print(f"[{key}] extracting ...", file=sys.stderr)
        arts, objectives, functions, intents, rep = run_one(key)
        rep["limits"] = NOTES[key]
        report[key] = rep
        objs[CODES[key]["code"]] = {"objectives": objectives, "functions": functions}
        for name, obj in ((f"{key}_articles.json", arts), (f"{key}_intents.json", intents)):
            (DATA / name).write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding="utf8")
        print(key, rep["articles_total"], rep["articles_by_division"], "textcheck_failed", rep["text_check"]["failed"],
              "attr_sentence_coverage", rep["attribution"]["sentence_coverage"],
              "intents", rep["intents"]["articles_with_intent"], file=sys.stderr)
    objs["_meta"] = {"note": "Division A Part 2 objectives and Part 3 functional statements, extracted per code from its own PDF.",
                     "codes": sorted(k for k in objs if k != "_meta")}
    obj_path.write_text(json.dumps(objs, indent=1, ensure_ascii=False), encoding="utf8")
    rep_path.write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf8")
    all_arts = {}
    for k in CODES:
        p = DATA / f"{k}_articles.json"
        if p.exists():
            all_arts[k] = json.loads(p.read_text(encoding="utf8"))
    chunks = build_chunks(all_arts)
    with open(HERE / "chunks_codes.jsonl", "w", encoding="utf8") as fh:
        for c in chunks:
            fh.write(json.dumps(c, ensure_ascii=False) + "\n")
    print("chunks:", len(chunks), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
