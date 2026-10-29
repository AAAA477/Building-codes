"""Precedent endpoints (mounted automatically by main.py).

GET  /api/applications/{id}/precedents  - issued variances / interpretations / policies that may already cover the application
POST /api/precedents/search             - free-text search over the same corpus
Nothing here says a precedent applies; every text field is retrieved or built from matched article numbers and terms.
"""
from __future__ import annotations
from typing import Optional

from fastapi import APIRouter, Body, HTTPException

import models
from corpus import precedents as P

router = APIRouter()


def _phrase(topic: str) -> str:
    return (topic or "").replace("_", " ").strip()


def _item(r: dict, why: Optional[str] = None, qstems=()) -> dict:
    cd = P.card(r, qstems, why)
    out = {"id": r["id"], "source_type": r["source_type"], "jurisdiction": r["jurisdiction"], "title": cd["title"],
           "citation": cd["citation"], "label": r.get("label"), "doc": r["doc"], "page": r["page"],
           "issue_date": r.get("issue_date"), "articles_cited": r["articles_cited"], "quote": cd["quote"],
           "quote_truncated_start": cd["quote_truncated_start"], "quote_truncated_end": cd["quote_truncated_end"],
           "score": r["score"]}
    if why is not None:
        out["why_relevant"] = cd["why_relevant"]
    if r.get("legal_status_note"):
        out["legal_status_note"] = r["legal_status_note"]
    if r.get("other_versions"):
        out["other_versions"] = r["other_versions"]
    return out


def _join(xs):
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


def _why(r: dict, topic: str = "", key_terms=()) -> str:
    parts = []
    arts = r.get("_matched_articles") or []
    if arts:
        parts.append(f"Cites {_join(arts)}, which your application also relies on.")
    title_terms = set(r.get("_title_terms", []))
    if topic and key_terms and set(key_terms) <= title_terms:
        parts.append(f"Covers the same subject: {_phrase(topic)}.")
    elif key_terms and title_terms & set(key_terms):
        words = [w for w in r.get("_matched_words", []) if (P._tok(w) or [""])[0] in set(key_terms) & title_terms]
        if words:
            parts.append(f"Its title mentions {_join(list(dict.fromkeys(words)))}.")
    return " ".join(parts) or "Matched by text similarity only; check whether it applies."


@router.get("/api/applications/{app_id}/precedents")
def application_precedents(app_id: str):
    a = models.load(app_id)
    if a is None:
        raise HTTPException(404, f"application {app_id} not found")
    if not P.available():
        return {"coverage": "none", "items": [], "note": P.NOTE}
    kt = P._key_terms(a)
    hits = P.app_precedents(a, k=12)
    strong_ids = {h["id"] for h in hits if P.strong(h, kt)}
    # strong hits first, then the next best, max 6 (already one best passage per document)
    hits = sorted(hits, key=lambda h: (h["id"] not in strong_ids, -h["score"]))[:6]
    topic = (a.get("variance") or {}).get("topic") or ""
    items = [_item(h, _why(h, topic, kt), set(h.get("_matched_terms", []))) for h in hits if h["id"] in strong_ids or (h.get("_matched_articles") or (set(kt) & set(h.get("_title_terms", [])))) and h["score"] >= P.STRONG_SCORE * 0.5]
    return {"coverage": "possible" if strong_ids else "none", "items": items, "note": P.NOTE}


@router.post("/api/precedents/search")
def precedents_search(body: dict = Body(...)):
    q = str(body.get("query") or "").strip()
    if not q:
        raise HTTPException(422, "query is required")
    try:
        k = max(1, min(int(body.get("k", 6)), 20))
    except (TypeError, ValueError):
        raise HTTPException(422, "k must be an integer")
    res = P.search_precedents(q, k=k, jurisdictions=body.get("jurisdictions"), source_types=body.get("source_types"))
    stems = set(P._terms(q)[1])
    out = {"query": q, "results": [{**r, **{kk: v for kk, v in P.card(r, stems).items()}} for r in res]}
    if not res:
        out["no_good_match"] = True
        out["message"] = "No good match in the indexed variances, interpretations, policies and advisories."
    return out
