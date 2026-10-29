"""Parse NBC 2023 Alberta Edition (born-digital PDF) into JSON.

Outputs (app/data/corpus):
  nbc_articles.json  Division B articles keyed "3.4.2.1"; Division A / C keyed "A:3.2.1.1" / "C:2.3.1.1"
                     (the numbers collide with Division B, so non-B keys are prefixed).
  objectives.json    Division A Part 2 objective statements (OS1.2 ...)
  functions.json     Division A Part 3 functional statements (F03 ...)

Attributions are NOT printed inline in this edition: they live in the per-Part tables
"Objectives and Functional Statements Attributed to the Acceptable Solutions" (Table 3.10.1.1,
9.38.1.1 ...). Those tables are laid out with ruled cells, so they are parsed with word
coordinates and the table's horizontal rules (one cell per sentence).

Run (from app/backend):  python -m corpus.extract_nbc
"""
import json
import re
import sys
from collections import defaultdict

import pymupdf

from . import DATA, FILES

PDF = FILES / "codes" / "NBC_2023AE_2nd_printing.pdf"
HDR_Y, FTR_Y = 55, 765

RE_ART = re.compile(r"^(\d+\.\d+\.\d+\.\d+)\.$")
RE_SUB = re.compile(r"^(\d+\.\d+\.\d+)\.$")
RE_SEC = re.compile(r"^Section (\d+\.\d+)\.$")
RE_PART = re.compile(r"^Part (\d+)$")
RE_SENT = re.compile(r"^(\d+)\)$")
RE_CLAUSE = re.compile(r"^([a-z]|[ivx]+|[A-Z])\)$")
RE_DIV = re.compile(r"Division ([ABC])\b")


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


def expand_codes(raw):
    """'F02,F03,F06-OS1.2' -> ['F02-OS1.2','F03-OS1.2','F06-OS1.2']; 'F04-OS1.2,OS1.3' too."""
    raw = raw.replace(" ", "")
    if "-" not in raw:
        return [raw]
    left, right = raw.split("-", 1)
    fs = [x for x in left.split(",") if x]
    os_ = [x for x in right.split(",") if x]
    return [f"{f}-{o}" for f in fs for o in os_]


RE_ATTR = re.compile(r"(?P<cl>(?:\([a-z0-9]+\)\s*,?\s*)+)?\[(?P<codes>[^\]]+)\]")


def parse_attr_text(text):
    """Return list of {clauses, raw, codes, applies_to} from one attribution cell."""
    text = re.sub(r"\s+", " ", text).strip()
    ms = list(RE_ATTR.finditer(text))
    res = []
    for i, m in enumerate(ms):
        end = ms[i + 1].start() if i + 1 < len(ms) else len(text)
        applies = text[m.end():end].strip()
        res.append({
            "clauses": re.sub(r"\s+", "", m.group("cl") or "") or None,
            "raw": "[" + m.group("codes") + "]",
            "codes": expand_codes(m.group("codes")),
            "applies_to": applies or None,
        })
    return res


# ---------------------------------------------------------------- body text
def build_sentences(lines):
    """lines -> (preamble_notes, [ {number,text} ]) using the 1,2,3 ... sequence rule."""
    notes, sents = [], []
    cur, expected = None, 1
    for ln in lines:
        m = RE_SENT.match(ln)
        if m and int(m.group(1)) == expected:
            cur = {"number": expected, "parts": []}
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
                txt += "\n" + p + " "
            elif txt.endswith(" ") or not txt:
                txt += p
            else:
                txt += " " + p
        out.append({"number": s["number"], "text": txt.strip()})
    return notes, out


def parse_body(doc, log):
    arts = {}
    ctx = {"part": None, "part_title": None, "section": None, "section_title": None,
           "sub": None, "sub_title": None}
    cur = None
    in_table = False
    for pi, page in enumerate(doc):
        div = page_division(page)
        if div is None:
            continue
        blocks = page_blocks(page)
        if sum(1 for _, _, t in blocks if "......" in t) >= 3:      # table of contents
            continue
        for y0, x0, txt in blocks:
            lines = [l.strip() for l in txt.split("\n") if l.strip()]
            if not lines:
                continue
            first = lines[0]
            is_head = x0 <= 80 and len(lines) <= 6
            if is_head and RE_PART.match(first) and len(lines) <= 3:
                ctx.update(part=RE_PART.match(first).group(1), part_title=" ".join(lines[1:]),
                           section=None, sub=None)
                cur = None
                continue
            if is_head and RE_SEC.match(first):
                ctx.update(section=RE_SEC.match(first).group(1), section_title=" ".join(lines[1:]), sub=None)
                cur = None
                continue
            if is_head and RE_ART.match(first) and len(lines) >= 2 and not RE_SENT.match(lines[1]):
                num = RE_ART.match(first).group(1)
                ti = []
                rest = []
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
                       "subsection": ".".join(parts[:3]),
                       "subsection_title": ctx["sub_title"],
                       "pdf_page": pi + 1, "pdf_pages": [pi + 1], "_lines": list(rest), "tables": []}
                arts[key] = cur
                in_table = False
                continue
            if is_head and RE_SUB.match(first) and len(lines) >= 2 and not RE_SENT.match(lines[1]):
                ctx.update(sub=RE_SUB.match(first).group(1), sub_title=" ".join(lines[1:]))
                cur = None
                continue
            if cur is None:
                continue
            if pi + 1 not in cur["pdf_pages"]:
                cur["pdf_pages"].append(pi + 1)
            if first.startswith("Table ") and x0 < 240:
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
    for key, a in arts.items():
        notes, sents = build_sentences(a.pop("_lines"))
        a["notes"] = notes
        a["sentences"] = sents
        a["tables"] = [t for t in a["tables"]
                       if not any("Functional Statements and Objectives" in l for l in t["lines"])]
        a["attributions"] = []
        for s in sents:
            s["attributions"] = []
            s["attribution_detail"] = []
    return arts


# ------------------------------------------------------- attribution tables
def hrules(page):
    out = []
    for d in page.get_drawings():
        r = d["rect"]
        if r.height <= 2 and r.width >= 20:
            out.append((round(r.x0), round(r.x1), (r.y0 + r.y1) / 2))
    return out


def parse_attr_tables(doc, arts):
    stats = {"pages": 0, "rows": 0, "sentence_rows": 0, "rows_before_any_article": 0,
             "attributed_sentences": 0, "unmatched": []}
    cur_art = None
    rows_out = []
    for pi, page in enumerate(doc):
        t = page.get_text()
        if "Functional Statements and Objectives" not in t:
            continue
        if page_division(page) != "B":
            continue
        stats["pages"] += 1
        words = [w for w in page.get_text("words") if w[0] > 30 and HDR_Y < w[1] < FTR_Y]
        rules = hrules(page)
        wide = [r for r in rules if r[1] - r[0] > 150]
        cols = sorted(set(r[0] for r in wide))
        merged = []
        for c in cols:
            if not merged or c - merged[-1] > 40:
                merged.append(c)
        for cl in merged:
            ys = sorted(set(round(r[2], 1) for r in wide if abs(r[0] - cl) <= 3))
            width = max(r[1] - r[0] for r in wide if abs(r[0] - cl) <= 3)
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
                if ltxt[0].startswith("Provision") or ltxt[0].startswith("Functional Statements and Objectives"):
                    continue
                first_tok = ltxt[0].split(" ")[0]
                if first_tok.startswith("Table") or first_tok in ("Forming", "Acceptable", "Objectives"):
                    continue
                stats["rows"] += 1
                if RE_ART.match(first_tok):
                    cur_art = RE_ART.match(first_tok).group(1)
                    rest = [" ".join(ltxt[0].split(" ")[1:])] + ltxt[1:]
                    attr_txt = " ".join(l for l in rest if "[" in l)
                    if attr_txt:
                        rows_out.append((cur_art, None, attr_txt, pi + 1))
                    continue
                num = None
                keep = []
                for _, ws in lines:
                    ws = sorted(ws, key=lambda w: w[0])
                    out = []
                    for w in ws:
                        if num is None and w[0] < cl + 20 and re.match(r"^\(\d+\)$", w[4]):
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
        a = arts.get(art)
        entries = parse_attr_text(attr_txt)
        if not entries:
            continue
        if a is None:
            stats["unmatched"].append(f"{art}({num}) p{pg}: article not in body parse")
            continue
        for e in entries:
            e["table_pdf_page"] = pg
        if num is None:
            a.setdefault("article_level_attributions", []).extend(entries)
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


# ------------------------------------------------------ objectives / functions
RE_OBJ_TOP = re.compile(r"^(O[A-Z]\d*)(?:\s+(\S.*))?$")
RE_OBJ_SUB = re.compile(r"^(O[A-Z]\d+\.\d+)\s+[–—]\s*(.*)$")


def division_a_lines(doc, pages):
    out = []
    for pn in pages:
        for y0, x0, txt in page_blocks(doc[pn - 1]):
            for l in txt.split("\n"):
                l = l.strip()
                if l:
                    out.append((pn, l))
    return out


def parse_objectives(doc):
    pages = [pn for pn in range(67, 76) if page_division(doc[pn - 1]) == "A"]
    lines = division_a_lines(doc, pages)
    start = next(i for i, (_, l) in enumerate(lines) if l.startswith("The objectives of this Code are as follows"))
    lines = lines[start + 1:]
    res = {}
    cur = None
    i = 0
    while i < len(lines):
        pn, l = lines[i]
        if l.startswith("Notes to Part") or l.startswith("Section 2.3"):
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
            if mt.group(2):
                title, j = mt.group(2), i + 1
            else:
                title, j = lines[i + 1][1], i + 2
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
    pages = [pn for pn in range(76, 86) if page_division(doc[pn - 1]) == "A"]
    lines = division_a_lines(doc, pages)
    s = next(i for i, (_, l) in enumerate(lines) if l == "F01")
    res = {}
    cur = None
    for pn, l in lines[s:]:
        if l.startswith("Notes to Part") or l.startswith("Section 3.3") or l.startswith("3.3."):
            break
        m = re.match(r"^(F\d+)(?:\s+(\S.*))?$", l)
        if m:
            cur = {"code": m.group(1), "text": (m.group(2) or "").strip(), "pdf_page": pn}
            res[m.group(1)] = cur
        elif cur is not None:
            cur["text"] = (cur["text"] + " " + l).strip()
    return res


# ------------------------------------------------------------------ main
def main():
    DATA.mkdir(parents=True, exist_ok=True)
    doc = pymupdf.open(str(PDF))
    log = []
    print("parsing body ...", file=sys.stderr)
    arts = parse_body(doc, log)
    print(f"{len(arts)} articles; parsing attribution tables ...", file=sys.stderr)
    stats = parse_attr_tables(doc, arts)
    objectives = parse_objectives(doc)
    functions = parse_functions(doc)
    for o in objectives.values():
        o["source"] = {"doc": "NBC_2023AE_2nd_printing.pdf", "page": o["pdf_page"], "division": "A", "part": 2}
    for f in functions.values():
        f["source"] = {"doc": "NBC_2023AE_2nd_printing.pdf", "page": f["pdf_page"], "division": "A", "part": 3}
    for k, a in arts.items():
        a["key"] = k
        a["source"] = {"doc": "NBC_2023AE_2nd_printing.pdf", "page": a["pdf_page"]}
    for name, obj in (("nbc_articles", arts), ("objectives", objectives), ("functions", functions)):
        with open(DATA / f"{name}.json", "w", encoding="utf8") as fh:
            json.dump(obj, fh, indent=1, ensure_ascii=False)
    with open(DATA / "extract_report.json", "w", encoding="utf8") as fh:
        json.dump({"attribution_stats": stats, "log": log}, fh, indent=1, ensure_ascii=False)
    by_div = defaultdict(int)
    for a in arts.values():
        by_div[a["division"]] += 1
    print("articles by division:", dict(by_div))
    print("objectives:", len(objectives), "functions:", len(functions))
    st = dict(stats)
    st["unmatched"] = len(st["unmatched"])
    print("attribution stats:", st)
    print("log entries:", len(log))


if __name__ == "__main__":
    main()
