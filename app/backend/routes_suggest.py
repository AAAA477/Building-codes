"""AI suggestion endpoints (auto-mounted by main.py).
POST /api/applications/{id}/suggest         body {kind, text?, field_path?}
POST /api/applications/{id}/suggest/accept  body {field_path, value, item_id?}  -> updated application, provenance 'ai_draft'
"""
from __future__ import annotations
from typing import Any, Optional

from fastapi import APIRouter, Body, HTTPException

import models
import suggest

router = APIRouter()
BLOCKED = ("declarations", "professional_flags", "provenance", "completeness", "id")


@router.post("/api/applications/{app_id}/suggest")
def suggest_ep(app_id: str, body: dict = Body(...)):
    a = models.load(app_id)
    if a is None:
        raise HTTPException(404, f"application {app_id} not found")
    kind = (body or {}).get("kind")
    if kind not in suggest.KINDS:
        raise HTTPException(422, f"kind must be one of {list(suggest.KINDS)}")
    import guardrails
    ref = guardrails.check(body.get("text"))
    if ref:   # approval / verdict request: standard reply, no model call, no items
        return {"kind": kind, "llm": "offline", "disclaimer": suggest.DISCLAIMER, "items": [],
                "notes": [ref["message"]], "refusal": ref}
    return suggest.run(a, kind, body.get("text"), body.get("field_path"))


@router.post("/api/applications/{app_id}/suggest/accept")
def suggest_accept(app_id: str, body: dict = Body(...)):
    import main  # lazy: main mounts this router
    import copy
    a = copy.deepcopy(main.get_app(app_id))   # a rejected value must not leave the stored application half-edited
    path = str((body or {}).get("field_path") or "").strip()
    if not path or "value" not in body:
        raise HTTPException(422, "field_path and value are required")
    if path.split(".")[0] in BLOCKED:
        raise HTTPException(409, f"{path} cannot be filled by a suggestion: declarations, signatures and professional flags are completed by people.")
    source = body.get("provenance")
    if source not in (None, "precedent"):
        raise HTTPException(422, "provenance may only be 'precedent'")
    if source == "precedent" and body.get("append"):
        cur = models.get_path(a, path, []) or []
        new = body["value"]
        dup = any((x.get("id") == new.get("id")) if isinstance(x, dict) and isinstance(new, dict) else x == new for x in cur)
        models.set_path(a, path, cur if dup else cur + [new])
    else:
        models.set_path(a, path, body["value"])
    prov = a.setdefault("provenance", {})
    if source == "precedent":
        prov[path] = {"source": "precedent", "confidence": 0.5, "item_id": body.get("item_id")}
    else:
        prov[path] = {"source": "ai_draft", "confidence": 0.6, "item_id": body.get("item_id")}
    try:
        a = models.normalize(a)
    except ValueError as e:   # pydantic.ValidationError is a ValueError
        raise HTTPException(422, f"{path} does not accept that value")
    main.refresh(a)
    return models.save(a)
