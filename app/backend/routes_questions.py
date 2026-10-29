"""Officer-questions loop, changes-since-submission and the 'after you submit' panel (auto-mounted by main.py)."""
from __future__ import annotations
import json
from fastapi import APIRouter, Body, HTTPException

import models
import questions

router = APIRouter(prefix="/api")
_FILE = models.CONTENT_DIR / "after_submit.json"
FALLBACK = {"edmonton": ["scc"]}  # Edmonton has no own form: the SCC form facts apply


def _get(app_id: str) -> dict:
    a = models.load(app_id)
    if a is None:
        raise HTTPException(404, f"application {app_id} not found")
    return a


def _refresh_save(a: dict) -> None:
    try:
        import main
        main.refresh(a)
    except Exception:
        pass
    models.save(a)


def after_submit_view(jurisdiction: str) -> dict:
    d = json.loads(_FILE.read_text(encoding="utf-8"))
    keys = FALLBACK.get(jurisdiction, []) + [jurisdiction]
    secs = []
    for s in d["sections"]:
        facts = list(s.get("common", []))
        unk = list((s.get("unknown") or {}).get("all", []))
        for k in keys:
            facts += (s.get("by_jurisdiction") or {}).get(k, [])
            unk += (s.get("unknown") or {}).get(k, [])
        unk = list(dict.fromkeys(unk))  # drop duplicates (Edmonton inherits SCC lines)
        secs.append({"id": s["id"], "title": s["title"], "facts": facts, "unknown": unk})
    return {"jurisdiction": jurisdiction, "title": d["title"], "intro": d["intro"],
            "unknown_text": d["unknown_text"], "sections": secs}


@router.get("/after-submit")
def after_submit(jurisdiction: str = "scc"):
    return after_submit_view(jurisdiction)


@router.get("/applications/{app_id}/after-submit")
def app_after_submit(app_id: str):
    return after_submit_view(_get(app_id).get("jurisdiction") or "scc")


def _view(a: dict) -> dict:
    items = questions.list_items(a)
    st = a.get(questions.KEY, {})
    return {"items": items, "open": sum(1 for i in items if i["status"] != "answered"),
            "submissions": st.get("submissions", [])}


@router.get("/applications/{app_id}/questions")
def list_questions(app_id: str):
    return _view(_get(app_id))


@router.post("/applications/{app_id}/questions")
def add_questions(app_id: str, body: dict = Body(...)):
    a = _get(app_id)
    texts = body.get("questions")
    if not isinstance(texts, list):
        texts = questions.split_text(body.get("text") or "")
    texts = [t for t in texts if isinstance(t, str) and t.strip()]
    if not texts:
        raise HTTPException(422, "provide 'text' (pasted from the officer) or a non-empty 'questions' list")
    questions.add(a, texts, body.get("link"))
    _refresh_save(a)
    return _view(a)


@router.patch("/applications/{app_id}/questions/{qid}")
def patch_question(app_id: str, qid: str, body: dict = Body(...)):
    a = _get(app_id)
    st = body.get("status")
    if st is not None and st not in questions.STATUSES:
        raise HTTPException(422, f"status must be one of {', '.join(questions.STATUSES)}")
    if questions.update(a, qid, body.get("answer"), st, body.get("link") if "link" in body else None) is None:
        raise HTTPException(404, f"question {qid} not found")
    _refresh_save(a)
    return _view(a)


@router.delete("/applications/{app_id}/questions/{qid}")
def delete_question(app_id: str, qid: str):
    a = _get(app_id)
    if not questions.remove(a, qid):
        raise HTTPException(404, f"question {qid} not found")
    _refresh_save(a)
    return _view(a)


@router.post("/applications/{app_id}/mark-submitted")
def mark_submitted(app_id: str, body: dict = Body(default={})):
    a = _get(app_id)
    snap = questions.mark_submitted(a, (body or {}).get("note", ""))
    models.save(a)
    return {"marked_at": snap["at"], "fields_recorded": len(snap["fields"]),
            "note": "Recorded by you. This tool does not send anything to the authority."}


@router.get("/applications/{app_id}/changes")
def changes(app_id: str):
    return questions.diff(_get(app_id))
