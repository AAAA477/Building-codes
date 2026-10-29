"""Dump completeness results for every real-derived sample next to its seeded defects.

Run from app/backend:  .venv/Scripts/python.exe -X utf8 tests/eval_dump.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

from fastapi.testclient import TestClient  # noqa: E402
from main import app  # noqa: E402

SAMPLES = os.path.join(HERE, "..", "..", "data", "samples")
client = TestClient(app)
truth = json.load(open(os.path.join(SAMPLES, "seeded_defects.json"), encoding="utf8"))["samples"]

names = sorted(
    f[:-5] for f in os.listdir(SAMPLES)
    if f.endswith(".json") and f not in ("seeded_defects.json", "application.example.json")
)
for name in names:
    body = json.load(open(os.path.join(SAMPLES, name + ".json"), encoding="utf8"))
    r = client.post("/api/applications", json=body)
    app_id = r.json()["id"]
    c = client.get(f"/api/applications/{app_id}/completeness").json()
    bad = [i for i in c["items"] if i["status"] != "complete"]
    print(f"\n## {name}: {c['percent']}% | items={len(c['items'])} | not complete={len(bad)}")
    for d in truth.get(name, {}).get("defects", []):
        print(f"   SEEDED {d['id']}: {d['path']} ({d['kind']})")
    for i in bad:
        print(f"   - [{i['status']}] {i['section']} {i['id']}: {i['message'][:110]}")
