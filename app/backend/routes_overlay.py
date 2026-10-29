"""Jurisdiction overlay endpoints (mounted automatically by main.py)."""
from __future__ import annotations
import copy
import tempfile
from pathlib import Path
from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import FileResponse

import models
import overlays

router = APIRouter(prefix="/api")


def _get(app_id: str) -> dict:
    a = models.load(app_id)
    if a is None:
        raise HTTPException(404, f"application {app_id} not found")
    return a


@router.get("/applications/{app_id}/overlay")
def get_overlay(app_id: str):
    return overlays.view(_get(app_id))


@router.post("/applications/{app_id}/overlay/answer")
def post_answer(app_id: str, body: dict = Body(...)):
    a = _get(app_id)
    qid, ans = body.get("question_id"), body.get("answer")
    if qid not in overlays.question_ids(a.get("jurisdiction") or "scc"):
        raise HTTPException(422, f"unknown question_id for jurisdiction {a.get('jurisdiction')}: {qid}")
    if ans not in ("yes", "no", "unsure"):
        raise HTTPException(422, "answer must be yes, no or unsure")
    a.setdefault("overlay", {}).setdefault("answers", {})[qid] = ans
    try:
        import main
        main.refresh(a)
    except Exception:
        pass
    models.save(a)
    return overlays.view(a)


def _blankfill(app: dict) -> dict:
    """Copy where placeholder text becomes '[not provided]' (never presented as a fact)."""
    def walk(x):
        if isinstance(x, dict):
            return {k: walk(v) for k, v in x.items()}
        if isinstance(x, list):
            return [walk(v) for v in x]
        if isinstance(x, str) and x.strip().startswith("[to be completed"):
            return "[not provided]"
        return x
    b = walk(copy.deepcopy(app))
    loc = b.setdefault("location", {})
    if not overlays.real(loc.get("permit_number")):
        loc["permit_number"] = "[not provided]"
    b["declarations"] = {"privacy_consent": False, "equal_or_better_ack": False, "owner_signed": False, "rep_signed": False}
    return b


@router.get("/applications/{app_id}/export/calgary-pdf")
def export_calgary(app_id: str):
    a = _get(app_id)
    import export
    out = Path(tempfile.mkdtemp()) / f"calgary_variance_{app_id}.pdf"
    try:
        export.fill_calgary(_blankfill(a), str(out))
    except Exception as e:
        raise HTTPException(500, f"export failed: {e}")
    return FileResponse(str(out), media_type="application/pdf", filename=out.name)


@router.get("/applications/{app_id}/pre-application-brief")
def pre_app_brief(app_id: str):
    return overlays.brief(_get(app_id))
