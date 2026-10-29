"""Agentic route-then-read search endpoints (auto-mounted by main.py).

POST /api/deep-search                    {query, codes?, cheap?}
POST /api/applications/{id}/deep-search  {cheap?}
Retrieval aid only; says nothing about safety or equivalence.
"""
from __future__ import annotations
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import agentic
import models

router = APIRouter()


class DeepIn(BaseModel):
    query: str
    codes: Optional[List[str]] = None
    cheap: bool = False


class DeepAppIn(BaseModel):
    cheap: bool = False


@router.post("/api/deep-search")
def deep_search(body: DeepIn):
    if not body.query.strip():
        raise HTTPException(422, "query is empty")
    import guardrails
    out = agentic.deep_search(body.query, body.codes, cheap=body.cheap)
    ref = guardrails.check(body.query)
    if ref:
        out["refusal"] = ref
    return out


@router.post("/api/applications/{app_id}/deep-search")
def deep_search_app(app_id: str, body: Optional[DeepAppIn] = None):
    app = models.load(app_id)
    if app is None:
        raise HTTPException(404, f"application {app_id} not found")
    q = agentic.application_query(app)
    if not q:
        raise HTTPException(422, "application has no description to search with")
    out = agentic.deep_search(q, None, cheap=bool(body and body.cheap))
    try:
        from llm import get_llm
        out["review_flags"] = agentic.review_flags(app, q, get_llm())
    except Exception:
        out["review_flags"] = agentic.review_flags(app, q, None)
    return out
