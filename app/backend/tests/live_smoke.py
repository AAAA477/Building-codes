"""Live smoke test against a RUNNING backend (uses the configured LLM, e.g. Azure OpenAI).

Run from app/backend:  .venv/Scripts/python.exe -X utf8 tests/live_smoke.py [base_url]
Default base_url: http://127.0.0.1:8010/api
Checks: provider in use, Section C from real code lookup, AI explainers are grounded and make no safety claims,
completeness, similar STANDATA, filled-PDF export. Exits 1 on any failure.
"""
import json
import re
import sys
import time
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8010/api"
FAILS = []


def call(method, path, body=None, raw=False):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            b = r.read()
            return r.status, (b if raw else json.loads(b))
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:200]


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (f" - {detail}" if detail else ""))
    if not ok:
        FAILS.append(name)


s, h = call("GET", "/health")
check("backend reachable", s == 200, str(h))
print("provider:", h.get("llm"))
check("hosted LLM active (not offline)", h.get("llm") not in (None, "offline"), "set keys in app/backend/.env")

s, sample = call("GET", "/samples/good_stair_edmonton")
s, a = call("POST", "/applications", sample)
aid = a["id"]
s, cl = call("POST", f"/applications/{aid}/classify", {})
check("classified as supported single-exit stair", s == 200 and cl.get("supported") is True, cl.get("message", ""))

t0 = time.time()
s, g = call("POST", f"/applications/{aid}/section-c/generate")
dt = time.time() - t0
s, app = call("GET", f"/applications/{aid}")
rows = app["variance"]["section_c"]
check("Section C generated from real lookup", s == 200 and len(rows) > 0, f"{len(rows)} rows in {dt:.1f}s")
check("every row verified against NBC text", all(r.get("verified") for r in rows),
      str([r.get("article") for r in rows if not r.get("verified")]))
unresolved = [r["article"] for r in rows if not str(r.get("objective", "")).strip() or r.get("objective") == "unresolved"]
print("rows with no attributed objective (root-article rule applies):", unresolved)

BAD = re.compile(r"\b(is safe|are safe|equivalent or better|is approved|will be approved|complies with|compliant)\b", re.I)
shown = 0
for r in rows:
    ex = r.get("explainer", "") or ""
    check(f"explainer present for {r['article']}", len(ex) > 40)
    check(f"explainer makes no safety/approval claim for {r['article']}", not BAD.search(ex), BAD.search(ex).group(0) if BAD.search(ex) else "")
    if shown < 2:
        print(f"   [{r['article']}] {r.get('objective','')[:90]}\n   explainer: {ex[:420]}\n")
        shown += 1

s, c = call("GET", f"/applications/{aid}/completeness")
check("completeness computed", s == 200, f"{c['percent']}% | professional stop={bool(c['professional_flags'])}")
s, sim = call("GET", f"/applications/{aid}/similar-standata")
check("similar STANDATA retrieved", s == 200 and len(sim.get("results", [])) > 0,
      "; ".join(str(r.get("doc") or r.get("title") or "")[:48] for r in sim.get("results", [])[:3]))
s, pdf = call("GET", f"/applications/{aid}/export/pdf", raw=True)
check("filled SCC form exported", s == 200 and pdf[:4] == b"%PDF", f"{len(pdf)} bytes")
s, _ = call("POST", f"/applications/{aid}/submission-package", {})
check("package blocked until the user signs", s == 409)

print("\nRESULT:", "ALL PASS" if not FAILS else f"{len(FAILS)} FAILED: {FAILS}")
sys.exit(1 if FAILS else 0)
