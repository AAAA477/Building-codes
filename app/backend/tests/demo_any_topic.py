"""Real-data demo: a non-stair STANDATA sample through classify -> section-c/add -> completeness (TestClient)."""
import json, sys
from pathlib import Path
from fastapi.testclient import TestClient

B = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(B))
import main  # noqa

c = TestClient(main.app)
name = sys.argv[1] if len(sys.argv) > 1 else "standata_23_bcv_001_wocd"
s = json.loads((B.parent / "data" / "samples" / f"{name}.json").read_text(encoding="utf8"))
arts = s["variance"]["acceptable_solution"]["articles"]
# start with the sample's applicant/project/variance facts but WITHOUT its pre-built Section C
s["variance"]["section_c"] = []
a = c.post("/api/applications", json={k: v for k, v in s.items() if not k.startswith("_") and k != "id"}).json()
aid = a["id"]
cl = c.post(f"/api/applications/{aid}/classify").json()
print("CLASSIFY:", json.dumps({k: cl[k] for k in ("topic", "mode", "supported", "declared_topic", "part", "message")}, indent=1))
print("SUGGESTED:", [(x["article"], x["title"]) for x in cl["suggested_articles"]])
for art in arts:
    r = c.post(f"/api/applications/{aid}/section-c/add", json={"article": art})
    print("ADD", art, r.status_code, (r.json().get("detail") if r.status_code != 200 else ""))
a = c.get(f"/api/applications/{aid}").json()
for r in a["variance"]["section_c"]:
    print(" ROW", r["article"], "verified=", r["verified"], "|", r["objective"][:70], "| p", r["source"].get("page"), "|", (r.get("note") or "")[:90])
comp = c.get(f"/api/applications/{aid}/completeness").json()
print("COMPLETENESS", comp["percent"], "%; flags:", [(f["id"], f["stop"]) for f in comp["professional_flags"]])
for i in comp["items"]:
    if i["status"] != "complete":
        print(" ", i["status"], i["id"], "-", i["message"][:100])
