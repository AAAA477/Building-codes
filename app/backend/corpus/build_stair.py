"""Build stair_articles.json and intents.json (single-exit-stair candidate set).

The candidate list below is curated from what the source documents say:
  G10 = files/direct/10_Edmonton_Emergency_Services_Guideline.pdf
  G11 = files/direct/11_Edmonton_Point_Access_Block.pdf
  NBC = the NBC(AE) 2023 article text/title itself (basis "nbc_text")
Every article number is checked against nbc_articles.json; attributions come from the parsed
Part attribution tables; intents come from the NBC 2020 Intent Supplement (earlier edition).

Run (from app/backend):  python -m corpus.build_stair
"""
import json
import re
import sys

import pymupdf

from . import DATA, FILES

INTENT_TXT = FILES.parent / "app" / "data" / "content" / "_work" / "txt" / "intent2020.txt"
INTENT_PDF = FILES / "codes" / "NBC_2020_Intent_Supplement.pdf"
EDITION_NOTE = ("NBC 2020 Intent Supplement is an earlier edition than NBC 2023 AE; article/sentence numbers and "
                "attributions may have been renumbered or changed. Match is by article+sentence number only; "
                "attribution_match compares the 2020 attribution codes with the 2023 AE table.")

G10 = "10_Edmonton_Emergency_Services_Guideline.pdf"
G11 = "11_Edmonton_Point_Access_Block.pdf"

# (article, group, basis, reason, [(doc,page)])
C = []


def add(arts, group, basis, reason, srcs):
    for a in arts:
        C.append((a, group, basis, reason, srcs))


add(["3.4.2.1", "9.9.8.2"], "number_of_exits", "guide",
    "Guide 11 states codes 'prescriptively enforced a minimum of two means of egress' and that a Point Access "
    "Block proposal contemplates 'a code variance for the number of exits'; these are the Part 3 / Part 9 "
    "minimum-number-of-exits provisions.", [(G11, 2), (G11, 4)])
add(["3.3.1.3", "3.3.4.4", "3.3.1.5", "3.4.1.2", "3.4.2.3", "9.9.9.2"], "number_of_exits", "nbc_text",
    "Egress/number-of-exits provision that interacts with Sentence 3.4.2.1.(2) (single-exit allowance) in the "
    "NBC(AE) text; Guide 11 p.8: single stair must perform equal to or better than two egress stairs.",
    [(G11, 8)])
add(["3.4.2.4", "3.4.2.5", "3.3.1.6", "9.9.8.4", "9.9.9.1"], "exit_location_travel", "nbc_text",
    "Exit location / travel distance provision; travel distance and area limits are the conditions attached to "
    "the single-exit allowance in Table 3.4.2.1.-A/-B.", [(G11, 4)])
add(["3.4.4.1", "3.4.4.2", "3.4.4.4", "3.4.3.1", "3.4.3.2", "3.4.6.3", "3.4.6.4", "3.4.6.5", "3.4.6.8", "9.9.4.2"],
    "exit_stair_construction", "nbc_text",
    "Exit stair / exit separation construction provision (fire-resistance of exit separation, integrity, width, "
    "stair geometry). Guide 11 p.5: stair failure modes relate to compartmentation and smoke management.",
    [(G11, 5)])
add(["3.1.8.5", "3.1.8.13", "3.1.8.14"], "fire_separations_of_exits", "nbc_text",
    "Closure / self-closing / hold-open provision for doors in fire separations around the exit stair "
    "(compartmentation, Guide 11 p.5).", [(G11, 5)])
add(["3.2.4.1", "3.2.4.7", "3.2.4.11", "3.2.4.20", "3.2.6.1", "3.2.6.2", "9.10.18.2", "9.10.19.1"],
    "smoke_control_alarm", "guide",
    "Fire alarm / smoke alarm / smoke movement provision. Guide 11 p.5 identifies smoke management as a main "
    "component of stair failure and mitigation; Guide 10 p.8 notes automatic smoke control may impact fire "
    "department procedures.", [(G11, 5), (G10, 8)])
add(["3.2.5.12", "3.2.2.47", "3.2.2.48", "3.2.2.49", "3.2.2.51", "3.2.2.52", "3.2.2.55"],
    "sprinklers", "nbc_text",
    "Sprinkler requirement / Group C (residential) building-size and construction provision relevant to the "
    "limits of the single-exit allowance and any sprinkler mitigation. Guide 10 p.12 lists sprinkler systems "
    "among prescribed firefighting provisions.", [(G10, 11), (G10, 12)])
add(["3.2.5.1", "3.2.5.2", "3.2.5.3", "3.2.5.4", "3.2.5.5", "3.2.5.6"], "firefighting_access", "guide",
    "Guide 10 p.8 Q1 and p.11: Division B Subsection 3.2.5 (Provisions for Firefighting) access requirements; any "
    "variance of them must be communicated for emergency-services review (F06/F12/F13 trigger).", [(G10, 8), (G10, 11)])
add(["3.2.5.7"], "firefighting_access", "guide",
    "Guide 10 p.12: 'Water supply for firefighting is prescribed by the NBC(AE) in Article 3.2.5.7.'", [(G10, 12)])
add(["3.2.5.8", "3.2.5.9", "3.2.5.10", "3.2.5.11", "3.2.5.15", "9.10.20.3"], "firefighting_access", "guide",
    "Guide 10 p.12: fire department connections, standpipes, hose connections and hose stations are prescribed "
    "by the NBC(AE); a variance must be assessed for impact on responders.", [(G10, 12)])
add(["A:1.2.1.1", "C:2.3.1.1"], "alternative_solution_process", "guide",
    "Guide 10 p.5: 'As detailed in NBC(AE) Division C, Article 2.3.1.1., documentation provided as part of an "
    "alternative solution must include' a code analysis; compliance path for alternative solutions is Division A "
    "Clause 1.2.1.1.(1)(b).", [(G10, 5)])

MULTI_NOTE = "Appears under several groups; first group shown, see also."


def load():
    with open(DATA / "nbc_articles.json", encoding="utf8") as fh:
        return json.load(fh)


# ----------------------------------------------------------------- intents
def clean_lines(txt_lines):
    """Yield (page, line) with page markers resolved and footers stripped."""
    out = []
    page = 0
    for i, l in enumerate(txt_lines):
        m = re.match(r"^=====PAGE (\d+)=====$", l)
        if m:
            page = int(m.group(1))
            continue
        if l.startswith("© His Majesty"):
            # drop printed page number just before the footer
            if out and re.fullmatch(r"\d+", out[-1][1]):
                out.pop()
            continue
        if l.strip() in ("Intent Statements:", "NBC 2020"):
            continue
        out.append((page, l.rstrip()))
    return out


def join_wrapped(parts, hy):
    txt = ""
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if txt.endswith("-"):
            left = re.search(r"([A-Za-z]+)-$", txt)
            right = re.match(r"([A-Za-z]+)", p)
            comp = (left.group(1) + "-" + right.group(1)).lower() if left and right else ""
            txt = txt + p if comp in hy else txt[:-1] + p
        else:
            txt = (txt + " " + p).strip()
    return txt


def parse_intents(wanted):
    raw = INTENT_TXT.read_text(encoding="utf8", errors="replace").split("\n")
    lines = clean_lines(raw)
    hy = set(m.group(0).lower() for l in raw for m in re.finditer(r"\b[A-Za-z]+-[A-Za-z]+\b", l))
    idx = [i for i, (_, l) in enumerate(lines) if l.startswith("Provision: ")]
    res = {}
    for n, i in enumerate(idx):
        m = re.match(r"^Provision: (\d+\.\d+\.\d+\.\d+)\.?(?:\((\d+)\))?(.*)$", lines[i][1])
        if not m or m.group(1) not in wanted:
            continue
        art, sent, rest = m.group(1), m.group(2), m.group(3).strip()
        end = idx[n + 1] if n + 1 < len(idx) else len(lines)
        block = lines[i + 1:end]
        recs = []
        cur = None
        mode = None
        for pg, l in block:
            s = l.strip()
            if s == "Objective":
                cur = {"objective": None, "attributions_2020": None, "intents": []}
                recs.append(cur)
                mode = "obj"
            elif s == "Attributions":
                mode = "attr"
                if cur is None:
                    cur = {"objective": None, "attributions_2020": None, "intents": []}
                    recs.append(cur)
            elif s == "Intent(s)":
                if cur is None:
                    cur = {"objective": None, "attributions_2020": None, "intents": []}
                    recs.append(cur)
                mode = "int"
            elif mode == "obj" and cur is not None:
                cur["objective"] = s
            elif mode == "attr" and cur is not None:
                cur["attributions_2020"] = (cur["attributions_2020"] or "") + s
            elif mode == "int" and cur is not None:
                mi = re.match(r"^Intent (\d+)\. (.*)$", s)
                if mi:
                    cur["intents"].append({"n": int(mi.group(1)), "parts": [mi.group(2)]})
                elif cur["intents"]:
                    cur["intents"][-1]["parts"].append(s)
        for r in recs:
            r["intents"] = [{"n": x["n"], "text": join_wrapped(x["parts"], hy)} for x in r["intents"]]
        key = (art, int(sent) if sent else None)
        res.setdefault(key, []).append({
            "provision": f"{art}.({sent})" + (rest if rest else "") if sent else art,
            "pdf_page": lines[i][0], "pdf_page_end": block[-1][0] if block else lines[i][0],
            "records": recs})
    return res


def main():
    arts = load()
    seen, out_list = set(), []
    for art, group, basis, reason, srcs in C:
        if art in seen:
            for e in out_list:
                if e["article"] == art:
                    e.setdefault("also_in_groups", []).append(group)
            continue
        seen.add(art)
        a = arts.get(art)
        entry = {"article": art, "group": group, "basis": basis,
                 "why_relevant": reason, "why_source": [{"doc": d, "page": p} for d, p in srcs],
                 "exists_in_nbc_2023ae": a is not None}
        if a is None:
            entry["status"] = "unresolved: article not found in parsed NBC(AE) 2023 text"
            out_list.append(entry)
            continue
        entry.update({"title": a["title"], "division": a["division"],
                      "source": {"doc": "NBC_2023AE_2nd_printing.pdf", "page": a["pdf_page"]}})
        codes = a["attributions"]
        entry["attribution_codes"] = codes
        entry["objectives"] = sorted({c.split("-", 1)[1] for c in codes if "-" in c})
        entry["functions"] = sorted({c.split("-", 1)[0] for c in codes if "-" in c})
        own = [s["number"] for s in a["sentences"] if s["attributions"]]
        none = [s["number"] for s in a["sentences"] if not s["attributions"]]
        if codes:
            entry["root_used"] = None
            if none:
                entry["sentences_without_own_attribution"] = none
                entry["root_rule_note"] = ("Sentences listed have no attribution row of their own; per the root-article "
                                           f"rule the statements of root article {art} apply (union shown in attribution_codes).")
            entry["attribution_status"] = "attributed"
        else:
            entry["root_used"] = None
            entry["attribution_status"] = "unresolved"
            entry["root_rule_note"] = ("No attributions in this Part's attribution table for this article; no root "
                                       "article statements can be determined from the data. Do not assume.")
        out_list.append(entry)

    wanted = {e["article"] for e in out_list if e.get("exists_in_nbc_2023ae") and e["division"] == "B"}
    print("parsing intent supplement text ...", file=sys.stderr)
    it = parse_intents(wanted)

    intents = {}
    for e in out_list:
        art = e["article"]
        if art not in wanted:
            if e.get("exists_in_nbc_2023ae"):
                intents[art] = {"article": art, "status": "unresolved",
                                "intent_edition": "NBC 2020 Intent Supplement",
                                "note": "Intent Supplement covers Division B only; no intent statements for Division A/C provisions."}
                e["intent_exists"] = False
            continue
        provs = []
        for (a_, s_), lst in sorted(it.items(), key=lambda kv: (kv[0][0], kv[0][1] or 0)):
            if a_ != art:
                continue
            for p in lst:
                for r in p["records"]:
                    codes2020 = re.findall(r"\[([^\]]+)\]", r["attributions_2020"] or "")
                    exp = []
                    for c in codes2020:
                        f, _, o = c.replace(" ", "").partition("-")
                        exp += [f"{x}-{y}" for x in f.split(",") for y in o.split(",") if x and y]
                    r["attribution_codes_2020"] = exp
                    sent = next((x for x in arts[art]["sentences"] if x["number"] == s_), None)
                    now = sent["attributions"] if sent else []
                    r["attribution_match_2023ae"] = (set(exp) <= set(now)) if exp else None  # 2020 codes all present in 2023AE table
                provs.append({"sentence": s_, "provision": p["provision"], "pdf_page": p["pdf_page"],
                              "pdf_page_end": p["pdf_page_end"], "records": p["records"]})
        if provs:
            intents[art] = {"article": art, "intent_edition": "NBC 2020 Intent Supplement",
                            "source": {"doc": "NBC_2020_Intent_Supplement.pdf",
                                       "page": min(p["pdf_page"] for p in provs)},
                            "provisions": provs, "edition_note": EDITION_NOTE, "status": "found"}
            e["intent_exists"] = True
        else:
            intents[art] = {"article": art, "status": "unresolved", "intent_edition": "NBC 2020 Intent Supplement",
                            "note": "No 'Provision: " + art + ".(n)' entry found in the NBC 2020 Intent Supplement "
                                    "(possibly renumbered, reserved, or without intent statements)."}
            e["intent_exists"] = False

    with open(DATA / "intents.json", "w", encoding="utf8") as fh:
        json.dump(intents, fh, indent=1, ensure_ascii=False)
    with open(DATA / "stair_articles.json", "w", encoding="utf8") as fh:
        json.dump({"topic": "single_exit_stair", "edition": "NBC(AE) 2023",
                   "derivation": ("Candidate set curated from Edmonton guides 10 and 11 (topics, Subsection 3.2.5, "
                                  "Article 3.2.5.7, Division C 2.3.1.1, F06/F12/F13 trigger) and NBC(AE) 2023 article text; "
                                  "attributions are read from the NBC Part attribution tables."),
                   "articles": out_list}, fh, indent=1, ensure_ascii=False)
    n = len(out_list)
    print(f"stair articles: {n}; exist: {sum(1 for e in out_list if e['exists_in_nbc_2023ae'])}; "
          f"attributed: {sum(1 for e in out_list if e.get('attribution_status') == 'attributed')}; "
          f"intent found: {sum(1 for e in out_list if e.get('intent_exists'))}")
    print("no intent:", [e["article"] for e in out_list if not e.get("intent_exists")])
    print("unattributed:", [e["article"] for e in out_list if e.get("attribution_status") == "unresolved"])


if __name__ == "__main__":
    main()
