"""Knowledge-graph endpoints (auto-mounted by main.py)."""
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import kg

router = APIRouter(prefix="/api/graph", tags=["graph"])


class ArtRef(BaseModel):
    code: str = "NBC"
    article: str


class ExpandReq(BaseModel):
    articles: List[ArtRef]
    hops: int = 1
    via: Optional[List[str]] = None
    limit: int = 30
    include_admin: bool = False


@router.get("/stats")
def stats():
    return kg.stats()


@router.get("/article/{code}/{number}")
def article(code: str, number: str):
    n = kg.node(code, number)
    if not n:
        raise HTTPException(404, f"{code} {number} not in graph")
    nb = kg.neighbors(code, number)
    groups, counts = {}, {}
    for r in nb:
        et = r["edge"]["type"]
        nt = r["node"]["type"]
        key = "attributed_to" if et == "attributed_to" else et
        if et == "parent_of":
            key = "parent_of" if r["direction"] == "in" else "children"
        elif et == "xref":
            key = "xref_out" if r["direction"] == "out" else "xref_in"
        counts[key] = counts.get(key, 0) + 1
        item = {"id": r["id"], "type": nt, "number": r["node"].get("number"), "code": r["node"].get("code"),
                "title": r["node"].get("title") or r["node"].get("citation"),
                "text": r["node"].get("text") if nt in ("objective", "function") else None,
                "evidence": r["edge"]["evidence"]}
        if nt == "article":
            item["pdf_page"] = r["node"].get("pdf_page")
        groups.setdefault(key, []).append(item)
    for k in groups:
        groups[k] = groups[k][:10]
    sib = kg.siblings(code, number)
    counts["siblings"] = len(sib)
    groups["siblings"] = [{"code": s["code"], "number": s["number"], "title": s["title"]} for s in sib[:10]]
    return {"node": n, "counts": counts, "neighbors": groups}


@router.post("/expand")
def expand(req: ExpandReq):
    via = tuple(req.via) if req.via else ("xref", "objective", "precedent")
    res = kg.expand([{"code": a.code, "article": a.article} for a in req.articles],
                    hops=max(1, min(req.hops, 3)), via=via, limit=max(1, min(req.limit, 200)),
                    include_admin=req.include_admin)
    return {"results": res}
