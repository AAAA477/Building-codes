import pymupdf, glob, re, json, os
os.chdir(r"C:\Users\aaaan\Downloads\Building codes")
ART = re.compile(r"\b\d{1,2}\.\d{1,2}\.\d{1,2}\.\d{1,2}\b")
MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"


def clean(s):
    s = s.replace("\u2019", "'").replace("\ufb01", "fi").replace("\ufb02", "fl").replace("\u2013", "-").replace("\u2014", "-")
    return re.sub(r"\s+", " ", s).strip()


def number_from_name(fn):
    toks = re.findall(r"(\d{2})-?(bcv|bci|bcb|fcv|fci|fcb|ecv|eci|edb|edi|pcb|gcb|gci|ess|leg|bce)-?(\d{3}[a-z]?\d?)", fn.lower())
    toks = [f"{a}-{b.upper()}-{c.upper()}" for a, b, c in toks]
    seen = []
    for t in toks:
        if t not in seen:
            seen.append(t)
    return "/".join(seen) if seen else None


def kind_of(path, text):
    p = path.lower()
    if "errata" in p: return "errata"
    if "interpretation" in p: return "interpretation"
    if "bulletin" in p: return "bulletin"
    if "variance" in p: return "variance"
    m = re.search(r"STANDATA\s+(variance|interpretation|bulletin)", text, re.I)
    return m.group(1).lower() if m else "variance"


rows = []
for f in sorted(glob.glob("files/standata/**/*.pdf", recursive=True)):
    f = f.replace("\\", "/")
    d = pymupdf.open(f)
    pages = [p.get_text() for p in d]
    t0 = pages[0]
    full = "\n".join(pages)
    fn = os.path.basename(f)
    folder = f.split("/")[2]
    kind = kind_of(f, t0)
    m = re.search(r"STANDATA\s+(?:variance|interpretation|bulletin)\s+([0-9A-Z][0-9A-Z\-/]*(?:\s?[0-9A-Z\-/]+)?)", t0, re.I)
    num = number_from_name(fn)
    if not num and m: num = clean(m.group(1)).upper()
    if not num:
        num = "unresolved (" + fn + ")"
    lines = [clean(l) for l in t0.split("\n") if clean(l)]
    title, tsrc = None, "filename"
    for i, l in enumerate(lines):
        if re.fullmatch(r"(Building|Fire|Gas|Electrical|Plumbing|Elevating Devices)(/[A-Za-z ]+)*(\s*/\s*[A-Za-z ]+)*", l) and i + 1 < len(lines):
            nxt = lines[i + 1]
            if not re.match(r"(Date Issued|Page|STANDATA)", nxt):
                title, tsrc = nxt, "document"
                break
    if not title:
        for i,l in enumerate(lines):
            if re.fullmatch(r"(PURPOSE|INTRODUCTION|BACKGROUND)",l.strip(),re.I) and i>0 and lines[i-1].isupper() and len(lines[i-1])>6 and not lines[i-1].startswith("BUILDING CODE"):
                title,tsrc=lines[i-1].capitalize(),"document"; break
    if not title:
        base = re.sub(r"\.pdf(\.pdf)?$", "", fn)
        base = re.sub(r"^(ma-)?(standata-)?(building-|joint-|variance-|code-|fire-|electrical-|interpretation-|bulletin-)*", "", base)
        base = re.sub(r"\b\d{2}-?[a-z]{3}-?\d{3}[a-z0-9]*\b", "", base)
        title = clean(base.replace("-", " ")).capitalize()
    ed = {"variances_2014": "NBC(AE) 2014", "variances_2019": "NBC(AE) 2019"}.get(folder, "NBC(AE) 2023")
    mm = re.search(r"\b(" + MONTHS + r")\s+(20\d\d)\b", t0)
    issued = f"{mm.group(1)} {mm.group(2)}" if mm else None
    scope = None
    pm = re.search(r"(?:Purpose|PURPOSE|INTRODUCTION|Introduction)\s*\n(.*?)(?:\nDiscussion|\nDISCUSSION|\nCode References|\nCODE REFERENCES|\nApplication|\nAPPLICATION|\nBACKGROUND|\nVariance)", t0, re.S)
    if not pm:
        pm = re.search(r"(?:Purpose|PURPOSE|INTRODUCTION|Introduction)\s*\n(.{40,500}?\.)\s*\n", full, re.S)
    if pm: scope = clean(pm.group(1))
    if not scope:
        for key in ("INTRODUCTION", "Introduction", "Variance", "Discussion", "Purpose"):
            km = re.search(key + r"\s*\n(.{40,600}?)\n\s*\n", full, re.S)
            if km:
                scope = clean(km.group(1)); break
    if not scope:
        scope = "unresolved (no Purpose text extracted)"
    scope = scope[:400]
    arts = []
    for a in ART.findall(full):
        if a not in arts: arts.append(a)
    ex = len(re.findall(r"\b(exit|exits|stair|stairs|stairway|egress)\b", full, re.I))
    rows.append({"number": num, "kind": kind, "title": title, "title_source": tsrc, "edition": ed,
                 "date_issued": issued, "articles_referenced": arts[:25], "scope": scope,
                 "mentions_exit_or_stair_count": ex, "pages": len(d),
                 "file_path": f, "source": {"doc": fn, "page": 1}})

for r in rows:
    if not r["title"].strip():
        r["title"] = "unresolved (title not extracted; see scope)"
    if r["number"].startswith("unresolved (jointafc"):
        r["number"] = "14-BCV-001/AFC 5.6.1.3"  # read from first-page text of the file
    r["single_exit_stair_relevant"] = r["number"].startswith("23-BCI-026") or r["number"].startswith("23-BCI-026/")

named = [
    {"id": "cal-spv-backwater", "jurisdiction": "calgary", "name": "Calgary Standing Posted Variance: backwater valves", "kind": "standing_posted_variance", "link": "https://www.calgary.ca/development/permits/building-regulation-advisories.html"},
    {"id": "cal-spv-firewalls", "jurisdiction": "calgary", "name": "Calgary Standing Posted Variance: firewalls in rowhouses with secondary suites", "kind": "standing_posted_variance", "link": "https://www.calgary.ca/development/permits/building-regulation-advisories.html"},
    {"id": "cal-spv-ebf", "jurisdiction": "calgary", "name": "Calgary Standing Posted Variance: exposed building face construction", "kind": "standing_posted_variance", "link": "https://www.calgary.ca/development/permits/building-regulation-advisories.html"},
    {"id": "cal-spv-vent", "jurisdiction": "calgary", "name": "Calgary Standing Posted Variance: ventilation", "kind": "standing_posted_variance", "link": "https://www.calgary.ca/development/permits/building-regulation-advisories.html"},
    {"id": "cal-spv-zll", "jurisdiction": "calgary", "name": "Calgary Standing Posted Variance: zero lot line", "kind": "standing_posted_variance", "link": "https://www.calgary.ca/development/permits/building-regulation-advisories.html", "note": "Data package: 382 individual requests in eight months of 2017 led to the standing variance."},
    {"id": "edm-b23-01", "jurisdiction": "edmonton", "name": "Edmonton Policy B23-01: fire separation between row houses with more than two secondary suites", "kind": "policy_solution", "link": "https://www.edmonton.ca/residential_neighbourhoods/application-requirements-house-permits"},
    {"id": "edm-b23-02", "jurisdiction": "edmonton", "name": "Edmonton Policy B23-02: window opening control devices", "kind": "policy_solution", "link": "https://www.edmonton.ca/residential_neighbourhoods/application-requirements-house-permits"},
    {"id": "edm-b23-03", "jurisdiction": "edmonton", "name": "Edmonton Policy Bulletin B23-03: roof truss engineering", "kind": "policy_solution", "link": "https://www.edmonton.ca/residential_neighbourhoods/application-requirements-house-permits"},
    {"id": "edm-b23-05", "jurisdiction": "edmonton", "name": "Edmonton B23-05: policy interpretation on the application of Article 9.9.4.4", "kind": "policy_interpretation", "link": "https://www.edmonton.ca/residential_neighbourhoods/application-requirements-house-permits"},
    {"id": "edm-pab", "jurisdiction": "edmonton", "name": "Edmonton Point Access Block Alternative Solution Guide (2025), with 13 design studies (design studies not in files/)", "kind": "guide", "link": "https://www.edmonton.ca/sites/default/files/public-files/Point-Access-Block-Alternative-Solution-Guide.pdf"},
]
for n in named:
    n["source"] = "Data Package docx"
    n["in_files"] = False
    n["note_scope"] = n.get("note", "") or "not in files/, link only"
    n["status"] = "not in files/, link only"
    n.pop("note", None)
# in_files for edmonton policy docs that ARE present locally
local = {"edm-b23-01": "files/edmonton_policy_solutions/Policy-B23-01-Secondary-Suites-in-Row-houses.pdf",
         "edm-b23-02": "files/edmonton_policy_solutions/Policy-B23-02-Window-Opening-Control-Devices.pdf",
         "edm-b23-03": "files/edmonton_policy_solutions/PolicyBulletin-B23-03-Roof-Truss-Engineering-Requirements.pdf",
         "edm-b23-05": "files/edmonton_policy_solutions/coe-scpi-pol-int-0001-b23-05-application-of-9944.pdf",
         "edm-pab": "files/direct/11_Edmonton_Point_Access_Block.pdf (8 pages only; design studies not included)"}
for n in named:
    if n["id"] in local:
        n["local_file"] = local[n["id"]]; n["in_files"] = True
        n["status"] = "local copy exists in files/ (also linked)"
out = {"note": "Index of every STANDATA PDF under files/standata, extracted from the real text. Titles marked title_source=filename were derived from the file name because the older template has no title line. Used for the 'does a variance already exist?' check.",
       "edition_control": "NBC(AE) 2023 second printing",
       "licence": "Alberta STANDATA: Open Government Licence - Alberta",
       "items": rows, "named_references": named}
json.dump(out, open("app/data/content/standata_index.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(len(rows), "items;", sum(1 for r in rows if r["title_source"] == "filename"), "titles from filename;", sum(1 for r in rows if r["scope"].startswith("unresolved")), "scopes unresolved")
for r in rows:
    if r["single_exit_stair_relevant"] or r["number"].startswith("23-BCV-001"):
        print(json.dumps(r, ensure_ascii=False)[:700])
