import json, os, re, glob, sys
import pymupdf
sys.path.insert(0, r"C:\Users\aaaan\Downloads\Building codes\app\data\content\_work")
ROOT = r"C:\Users\aaaan\Downloads\Building codes"
os.chdir(ROOT)
import nbcidx

CONTENT = {
    "intake_questions.json": None, "stair_module.json": ["scope", "topic_questions", "benchmark_acceptable_solution", "mitigation_catalogue"],
    "section_d_templates.json": ["items"], "professional_rules.json": ["stop_language", "rules"],
    "edmonton_emergency_screen.json": ["questions", "functional_statement_trigger", "response_time_boundary"],
    "glossary.json": ["terms"], "standata_index.json": ["items", "named_references"]}
rows = []  # (check, target, status, detail)


def rec(check, target, ok, detail=""):
    rows.append((check, target, "PASS" if ok else "FAIL", detail))


# --- pdf index
pdfs = {}
for f in glob.glob("files/**/*.pdf", recursive=True):
    pdfs.setdefault(os.path.basename(f), f.replace("\\", "/"))
page_cache = {}


def pages_of(doc):
    if doc not in page_cache:
        d = pymupdf.open(pdfs[doc])
        page_cache[doc] = d
    return page_cache[doc]


def norm(s):
    s = s.replace("\u2019", "'").replace("\u2018", "'").replace("\u201c", '"').replace("\u201d", '"').replace("\u2013", "-").replace("\u2014", "-").replace("\ufb01", "fi")
    return re.sub(r"[^a-z0-9]+", "", s.lower())


page_text = {}


def ptext(doc, page):
    k = (doc, page)
    if k not in page_text:
        page_text[k] = norm(pages_of(doc)[page - 1].get_text())
    return page_text[k]


def walk(o, path=""):
    yield path, o
    if isinstance(o, dict):
        for k, v in o.items(): yield from walk(v, f"{path}.{k}" if path else k)
    elif isinstance(o, list):
        for i, v in enumerate(o): yield from walk(v, f"{path}[{i}]")


# --- load
data = {}
for fn in CONTENT:
    p = f"app/data/content/{fn}"
    try:
        data[fn] = json.load(open(p, encoding="utf-8")); rec("load", fn, True, "")
    except Exception as e:
        rec("load", fn, False, str(e)[:80])
for fn in sorted(glob.glob("app/data/samples/*.json")):
    b = os.path.basename(fn)
    try:
        data["samples/" + b] = json.load(open(fn, encoding="utf-8")); rec("load", "samples/" + b, True)
    except Exception as e:
        rec("load", "samples/" + b, False, str(e)[:80])

# --- required keys
for fn, keys in CONTENT.items():
    d = data.get(fn)
    if d is None: continue
    if fn == "intake_questions.json":
        need = {"id", "section", "prompt", "help", "field_path", "type", "required", "source"}
        bad = [q["id"] for q in d if not need <= set(q)]
        bad += [q["id"] for q in d if q["section"] not in "ABCD" or q["type"] not in ("text", "number", "bool", "choice", "date")]
        rec("keys", fn, not bad, f"{len(d)} questions; bad={bad}")
        order = "".join(q["section"] for q in d)
        rec("order A->D", fn, order == "".join(sorted(order)), order)
    else:
        miss = [k for k in keys if k not in d]
        rec("keys", fn, not miss, f"missing={miss}")

SAMPLE_KEYS = ["id", "jurisdiction", "edition", "applicant", "project", "location", "variance", "section_d", "professional_flags", "declarations", "provenance", "completeness"]
for k, d in data.items():
    if not k.startswith("samples/") or k.endswith(("seeded_defects.json", "application.example.json")): continue
    miss = [x for x in SAMPLE_KEYS if x not in d]
    rec("sample keys", k, not miss, f"missing={miss}")
    rec("declarations all false", k, not any(d["declarations"].values()), "")
    rec("derived_from present", k, bool(d.get("derived_from")), str(len(d.get("derived_from", []))))
    ident = [d["applicant"][x] for x in ("owner_name", "owner_representative", "mailing_address", "email")]
    rec("identity placeholders only", k, all(v in ("", "[to be completed by applicant]") for v in ident) and d["applicant"]["date_of_request"] == "", "")

# --- source refs: doc exists, page in range
nsrc = 0; badsrc = []
for fn, d in data.items():
    for path, o in walk(d):
        if isinstance(o, dict) and "doc" in o and "page" in o and set(o) <= {"doc", "page", "standata"}:
            nsrc += 1
            doc, pg = o["doc"], o["page"]
            if doc not in pdfs: badsrc.append((fn, path, doc, "doc not found")); continue
            n = len(pages_of(doc))
            if not (1 <= pg <= n): badsrc.append((fn, path, doc, f"page {pg} outside 1..{n}"))
exp_bad = [b for b in badsrc if b[0] == "samples/flawed_unverified_citation.json" and b[3].startswith("page 0")]
other_bad = [b for b in badsrc if b not in exp_bad]
rec("source {doc,page} resolve", f"{nsrc} refs", not other_bad, f"unexpected={other_bad[:3]}; expected-bad(page 0 in flawed)={len(exp_bad)}")

# --- verbatim quote checks on the cited page
def check_quote(fn, label, text, src, strict=True):
    if src["doc"] not in pdfs: return None
    t = norm(text)
    return t in ptext(src["doc"], src["page"])

qf = []; qn = 0
es = data["edmonton_emergency_screen.json"]
for q in es["questions"]:
    for obj, src in [(q["text"], q["source"])] + [(s["text"], s["source"]) for s in q["sub_points"]]:
        qn += 1
        if not check_quote("es", q["id"], obj, src): qf.append((q["id"], obj[:50]))
rec("emergency screen text verbatim on cited page", "edmonton_emergency_screen.json", not qf, f"{qn} items; fails={qf}")
gf = []; gn = 0
for t in data["glossary.json"]["terms"]:
    segs = [s.strip() for s in re.split(r"\.\.\.", t["official"])]
    for s in segs:
        s = re.sub(r"\s*\((?:OS1 Fire Safety|Division A, Clause 1\.2\.1\.1\.\(1\)\(b\))\)\.?$", "", s).strip(" '.")
        if len(s) < 25: continue
        # glossary may combine two sentences from adjacent places; check each sentence separately
        for sub in re.split(r"(?<=\.)\s+(?=[A-Z])", s):
            if len(sub) < 25: continue
            gn += 1
            src = t["official_source"]
            ok = check_quote("g", t["id"], sub, src)
            if not ok: gf.append((t["id"], sub[:50]))
rec("glossary official quotes on cited page", "glossary.json", not gf, f"{gn} segments; fails={gf}")

# --- NBC articles
idx = nbcidx.build()
nfc_text = open("app/data/content/_work/txt/NFC.txt", encoding="utf-8").read()
ART = re.compile(r"\b\d{1,2}\.\d{1,2}\.\d{1,2}\.\d{1,2}\b")
for fn, d in data.items():
    if fn == "standata_index.json" or fn.endswith("seeded_defects.json"): continue
    found = {}
    for path, o in walk(d):
        if isinstance(o, str) and not path.startswith("source_conflicts"):
            for m in ART.findall(o): found.setdefault(m, path)
    missing = []
    nfc = []
    for a in found:
        if a in idx: continue
        if re.search(r"^" + re.escape(a) + r"\.\s*$", nfc_text, re.M) and a.startswith("2.3.1"):
            nfc.append(a)
        else:
            missing.append(a)
    exp = fn == "samples/flawed_unverified_citation.json"
    if exp:
        rec("articles exist in NBC", fn, missing == ["3.4.2.9"], f"{len(found)} cited; absent={missing} (expected: seeded defect)")
    else:
        rec("articles exist in NBC", fn, not missing, f"{len(found)} cited; absent={missing}; NFC-only={nfc}")
# standata index (info)
si = data["standata_index.json"]["items"]
inf = [r["number"] for r in si if r["edition"] == "NBC(AE) 2023" and any(a not in idx for a in r["articles_referenced"])]
rec("standata_index: 2023-edition articles in NBC (informational)", "standata_index.json", True, f"{len(si)} items; {len(inf)} 2023-edition items cite an article not found as a body heading: {inf[:6]}")
rec("standata_index covers all PDFs", "standata_index.json", len(si) == len(glob.glob("files/standata/**/*.pdf", recursive=True)), f"{len(si)} vs {len(glob.glob('files/standata/**/*.pdf', recursive=True))}")
rec("SES interpretation indexed", "standata_index.json", any(r["number"].startswith("23-BCI-026") for r in si), "")

# --- Section C rows in samples vs corpus
corp = json.load(open("app/data/corpus/nbc_articles.json", encoding="utf-8"))
for k, d in data.items():
    if not k.startswith("samples/") or "variance" not in d: continue
    bad = []
    for r in d["variance"]["section_c"]:
        a = r["article"].split(".(")[0]
        if a not in corp: bad.append(a)
    exp = k.endswith("flawed_unverified_citation.json")
    rec("section_c articles in corpus lookup", k, (bad == ["3.4.2.9"]) if exp else not bad, f"{len(d['variance']['section_c'])} rows; not found={bad}" + (" (expected)" if exp else ""))

# --- seeded defects ground truth
seed = data["samples/seeded_defects.json"]


def resolve(d, path):
    cur = [d]
    for part in re.findall(r"[^.\[\]]+|\[\d+\]|\[\*\]", path):
        nxt = []
        for c in cur:
            if part == "[*]":
                nxt += list(c) if isinstance(c, list) else []
            elif part.startswith("["):
                i = int(part[1:-1]); nxt.append(c[i]) if isinstance(c, list) and i < len(c) else None
            else:
                if isinstance(c, dict) and part in c: nxt.append(c[part])
        cur = nxt
    return cur


for name, s in seed["samples"].items():
    d = data.get("samples/" + name + ".json")
    if d is None: rec("seeded defects", name, False, "sample missing"); continue
    ok = True; det = []
    for df in s["defects"]:
        vals = resolve(d, df["path"])
        if df["kind"] in ("removed", "baseline_blank"):
            good = (not vals) or all(v in ("", [], None, {}, False) for v in vals)
        else:
            good = bool(vals)
            if df["id"] == "UC-1": good = vals == ["3.4.2.9.(1)"]
            if df["id"] == "UC-2": good = vals == ["3.4.2.9.(1)"]
            if df["id"].startswith("NP-") and "professional_required" in df["path"]: good = all(v is False for v in vals)
        if not good: ok = False; det.append(df["id"])
    rec("seeded defects present in sample", f"{name} ({len(s['defects'])} defects)", ok, f"not reproduced={det}")

# --- print table
w = max(len(r[1]) for r in rows) + 2
print(f"{'CHECK':58} {'TARGET':{w}} {'STATUS':6} DETAIL")
for c, t, st, de in rows:
    print(f"{c[:57]:58} {t:{w}} {st:6} {de[:150]}")
fails = [r for r in rows if r[2] == "FAIL"]
print(f"\n{len(rows)} checks, {len(fails)} FAIL")
sys.exit(1 if fails else 0)
