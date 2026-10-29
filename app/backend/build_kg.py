"""Build the knowledge graph (app/data/corpus/kg.json) from real corpus files only.
Run: .venv/Scripts/python.exe -X utf8 build_kg.py
"""
import json, re, time, collections
from pathlib import Path

CORPUS = Path(__file__).resolve().parent.parent / "data" / "corpus"
CONTENT = Path(__file__).resolve().parent.parent / "data" / "content"
CODES = {"NBC": "nbc_articles.json", "NFC": "nfc_articles.json",
         "NPC": "npc_articles.json", "NECB": "necb_articles.json"}
OBJ_KEY = {"NFC": "NFC(AE) 2023", "NPC": "NPC 2020", "NECB": "NECB 2020"}


def _load(name):
    return json.loads((CORPUS / name).read_text(encoding="utf8"))


def akey(div, num):
    return num if div == "B" else f"{div}:{num}"


def aid(code, div, num):
    return f"{code}|{akey(div, num)}"


NUM = re.compile(r"\d+(?:\.\d+)+")
LIST_TAIL = re.compile(
    r"\b(Articles?|Subsections?|Sections?|Sentences?)\s+"
    r"((?:(?:\d+\.){1,4}\d*\.?(?:\(\d+\))?(?:\s*(?:,|and|or|to)\s*)?)+)"
    r"(?:\s+of\s+Division\s+([ABC]))?")
CODE_TAIL = re.compile(r"\s*of\s+the\s+(NBC|NFC|NPC|NECB)\b")


def main():
    t0 = time.time()
    nodes, edges = {}, []
    arts = {}
    for code, fn in CODES.items():
        d = _load(fn)
        for k, a in d.items():
            div = a.get("division", "B")
            arts[aid(code, div, a["number"])] = (code, div, a["number"], a)
    seen = set()
    for i, (code, div, num, a) in arts.items():
        nodes[i] = {"type": "article", "code": code, "division": div, "number": num,
                    "title": a.get("title"), "part": a.get("part"), "section": a.get("section"),
                    "subsection": a.get("subsection"), "pdf_page": a.get("pdf_page")}
        pid = f"{code}|part:{div}:{a.get('part')}"
        sid = f"{code}|sec:{div}:{a.get('section')}"
        ssid = f"{code}|sub:{div}:{a.get('subsection')}"
        for nid, typ, n_, title in ((pid, "part", a.get("part"), a.get("part_title")),
                                    (sid, "section", a.get("section"), a.get("section_title")),
                                    (ssid, "subsection", a.get("subsection"), a.get("subsection_title"))):
            if nid not in nodes:
                nodes[nid] = {"type": typ, "code": code, "division": div, "number": n_, "title": title}
        for p, c in ((pid, sid), (sid, ssid), (ssid, i)):
            if (p, c) not in seen:
                seen.add((p, c))
                edges.append([p, c, "parent_of", None])

    obj_src = {"NBC": _load("objectives.json")}
    fn_src = {"NBC": _load("functions.json")}
    oc = _load("other_codes_objectives.json")
    for code, name in OBJ_KEY.items():
        obj_src[code] = oc[name]["objectives"]
        fn_src[code] = oc[name]["functions"]
    unresolved = collections.Counter()

    def mk(kind, src, code, o):
        nid = f"{code}|{kind}:{o}"
        if nid not in nodes:
            r = src[code].get(o)
            if r is None:
                unresolved[(code, o)] += 1
            nodes[nid] = {"type": "objective" if kind == "obj" else "function", "code": code, "number": o,
                          "title": r.get("title") if r else None,
                          "text": r.get("text") if r else "unresolved",
                          "pdf_page": r.get("pdf_page") if r else None}
        return nid

    for i, (code, div, num, a) in arts.items():
        by_o = collections.defaultdict(lambda: {"sentences": set(), "functions": set()})
        by_f = collections.defaultdict(lambda: {"sentences": set(), "objectives": set()})

        def add(pair, sent):
            if not re.match(r"^F[0-9]+-O", pair):
                return
            f, o = pair.split("-", 1)
            by_o[o]["sentences"].add(sent); by_o[o]["functions"].add(f)
            by_f[f]["sentences"].add(sent); by_f[f]["objectives"].add(o)
        sent_pairs = set()
        for s in a.get("sentences", []):
            for p in s.get("attributions", []):
                add(p, s["number"]); sent_pairs.add(p)
        for p in a.get("attributions", []):
            if p not in sent_pairs:
                add(p, None)
        for o, ev in by_o.items():
            edges.append([i, mk("obj", obj_src, code, o), "attributed_to",
                          {"sentences": sorted(x for x in ev["sentences"] if x is not None),
                           "functions": sorted(ev["functions"])}])
        for f, ev in by_f.items():
            edges.append([i, mk("fn", fn_src, code, f), "attributed_to",
                          {"sentences": sorted(x for x in ev["sentences"] if x is not None),
                           "objectives": sorted(ev["objectives"])}])
    for code in obj_src:
        for o, r in obj_src[code].items():
            nid = f"{code}|obj:{o}"
            par = r.get("parent")
            if nid in nodes and par and f"{code}|obj:{par}" in nodes:
                edges.append([f"{code}|obj:{par}", nid, "parent_of", None])

    xseen = set()
    for i, (code, div, num, a) in arts.items():
        for s in a.get("sentences", []):
            text = s["text"]
            for m in LIST_TAIL.finditer(text):
                kind = m.group(1).rstrip("s").lower()
                tdiv = m.group(3) or div
                tcode = code
                mm = CODE_TAIL.match(text[m.end(): m.end() + 40])
                if mm:
                    tcode = mm.group(1)
                for n in NUM.findall(m.group(2)):
                    n = n.rstrip(".")
                    parts = n.split(".")
                    if kind in ("article", "sentence"):
                        if len(parts) < 4:
                            continue
                        tgt = aid(tcode, tdiv, ".".join(parts[:4]))
                    elif kind == "subsection":
                        if len(parts) != 3:
                            continue
                        tgt = f"{tcode}|sub:{tdiv}:{n}"
                    else:
                        if len(parts) != 2:
                            continue
                        tgt = f"{tcode}|sec:{tdiv}:{n}"
                    if tgt not in nodes or tgt == i or (i, tgt) in xseen:
                        continue
                    xseen.add((i, tgt))
                    edges.append([i, tgt, "xref", {"sentence": s["number"], "kind": kind,
                                                   "text": text[max(0, m.start() - 60): m.end() + 20].strip()}])

    docs = {}
    for line in (CORPUS / "precedents_chunks.jsonl").open(encoding="utf8"):
        r = json.loads(line)
        d = docs.setdefault(r["doc"], {"title": r.get("title"), "source_type": r["source_type"],
                                       "jurisdiction": r.get("jurisdiction"), "issue_date": r.get("issue_date"),
                                       "cites": {}})
        for x in r.get("articles_cited", []):
            d["cites"].setdefault(x, []).append(r.get("page"))
    for doc, d in docs.items():
        if not d["cites"]:
            continue
        did = f"DOC|{doc}"
        nodes[did] = {"type": "precedent", "doc": doc, "title": d["title"], "source_type": d["source_type"],
                      "jurisdiction": d["jurisdiction"], "issue_date": d["issue_date"],
                      "citation": f"{d['title']} ({doc})"}
        for x, pages in d["cites"].items():
            t = f"NBC|{x}"
            if t in nodes:
                edges.append([did, t, "cites", {"pages": sorted({p for p in pages if p is not None})}])
    try:
        sidx = json.loads((CONTENT / "standata_index.json").read_text(encoding="utf8"))
        have = " ".join(docs.keys()).lower()
        for it in sidx.get("items", []):
            num = it.get("number")
            if not num or num.lower() in have:
                continue
            refs = [x for x in it.get("articles_referenced", []) if f"NBC|{x}" in nodes]
            if not refs:
                continue
            did = f"DOC|standata:{num}"
            nodes[did] = {"type": "precedent", "doc": f"standata:{num}", "title": it.get("title"),
                          "source_type": "standata_" + str(it.get("kind")), "jurisdiction": "alberta",
                          "issue_date": it.get("date_issued"), "citation": f"STANDATA {num}"}
            for x in refs:
                edges.append([did, f"NBC|{x}", "cites", {"pages": []}])
    except Exception as e:
        print("standata_index skipped:", e)

    out = {"meta": {"built": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "note": "Built only from *_articles.json, objectives/functions json, "
                            "precedents_chunks.jsonl articles_cited, standata_index.json"},
           "nodes": nodes, "edges": edges}
    p = CORPUS / "kg.json"
    p.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf8")
    nt = collections.Counter(n["type"] for n in nodes.values())
    et = collections.Counter(e[2] for e in edges)
    rep = {"build_seconds": round(time.time() - t0, 2), "size_bytes": p.stat().st_size,
           "nodes_by_type": dict(nt), "edges_by_type": dict(et),
           "unresolved_objective_or_function_codes": {f"{c}:{o}": n for (c, o), n in unresolved.items()}}
    (CORPUS / "kg_report.json").write_text(json.dumps(rep, indent=1), encoding="utf8")
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
