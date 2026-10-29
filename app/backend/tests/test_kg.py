import time
import kg
from fastapi import FastAPI
from fastapi.testclient import TestClient
import routes_graph

app = FastAPI()
app.include_router(routes_graph.router)
client = TestClient(app)


def test_stats_nonempty():
    s = kg.stats()
    for t in ("article", "objective", "function", "precedent"):
        assert s["nodes"][t] > 0
    for t in ("parent_of", "xref", "attributed_to", "cites"):
        assert s["edges"][t] > 0


def test_xref_edges_have_real_targets_and_evidence():
    g = kg.graph()
    n = 0
    for s, lst in g.out.items():
        for d, t, ev in lst:
            if t == "xref":
                assert d in g.nodes and ev["text"]
                n += 1
    assert n > 1000


def test_expand_3_4_2_1_finds_xref_and_excludes_admin():
    r = kg.expand([("NBC", "3.4.2.1")], limit=30)
    arts = {x["article"] for x in r}
    assert "3.3.1.3" in arts
    assert all(x["division"] == "B" for x in r)
    assert all(x["edge"]["type"] and x["edge"]["via"] for x in r)


def test_precedents_and_why_path():
    p = kg.precedents_for("NBC", "9.9.10.1")
    assert p and all(x["citation"] for x in p)
    path = kg.why_path(("NBC", "3.4.2.1"), ("NBC", "3.3.1.3"))
    assert path and path[0]["edge"]["type"] == "xref"


def test_latency():
    kg.graph()
    best = 1
    for _ in range(5):
        t = time.perf_counter()
        kg.expand([("NBC", "9.9.10.1"), ("NBC", "9.8.8.1")], limit=30)
        best = min(best, time.perf_counter() - t)
    assert best < 0.05


def test_endpoints():
    r = client.get("/api/graph/article/NBC/3.4.2.1")
    assert r.status_code == 200
    j = r.json()
    assert j["node"]["number"] == "3.4.2.1" and "xref_out" in j["counts"]
    assert all(len(v) <= 10 for v in j["neighbors"].values())
    assert client.get("/api/graph/article/NBC/0.0.0.0").status_code == 404
    r = client.post("/api/graph/expand", json={"articles": [{"code": "NBC", "article": "9.8.8.1"}], "limit": 5})
    assert r.status_code == 200 and 0 < len(r.json()["results"]) <= 5
    assert client.get("/api/graph/stats").json()["total_nodes"] > 0
