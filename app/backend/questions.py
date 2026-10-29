"""Officer questions (requests for information) tracked as items, plus a snapshot/diff of key
fields taken when the applicant manually marks the application as submitted.

Tracking only: this module never sends anything and never claims a submission was received.
State lives in app["officer_questions"] = {"items": [...], "snapshot": {...}|None, "submissions": [...]}.
"""
from __future__ import annotations
import datetime as _dt
import uuid

KEY = "officer_questions"
STATUSES = ("open", "answered", "needs_professional")
SECTIONS = ("A", "B", "C", "D", "SIGN")

_SCALAR_ROOTS = ("applicant", "project", "location")


def _state(app: dict) -> dict:
    st = app.get(KEY)
    if not isinstance(st, dict):
        st = {}
    st.setdefault("items", [])
    st.setdefault("snapshot", None)
    st.setdefault("submissions", [])
    app[KEY] = st
    return st


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def list_items(app: dict) -> list:
    return list(_state(app)["items"])


def split_text(text: str) -> list:
    """Split pasted officer email text into one question per numbered/bulleted/blank-line block."""
    import re
    t = (text or "").replace("\r\n", "\n").strip()
    if not t:
        return []
    parts = re.split(r"\n\s*(?=(?:\d+[.)]|[-*\u2022])\s+)", t)
    if len(parts) == 1:
        parts = re.split(r"\n\s*\n", t)
    out = []
    for p in parts:
        p = re.sub(r"^\s*(?:\d+[.)]|[-*\u2022])\s+", "", p.strip())
        p = " ".join(p.split())
        if p:
            out.append(p)
    return out


def add(app: dict, texts: list, link: dict | None = None) -> list:
    st = _state(app)
    link = _clean_link(link)
    new = []
    for t in texts:
        t = (t or "").strip()
        if not t:
            continue
        it = {"id": uuid.uuid4().hex[:8], "text": t, "status": "open", "answer": "",
              "link": link, "created_at": _now(), "answered_at": None}
        st["items"].append(it)
        new.append(it)
    return new


def _clean_link(link) -> dict | None:
    if not isinstance(link, dict):
        return None
    sec = link.get("section")
    sec = sec if sec in SECTIONS else None
    field = (link.get("field") or "").strip() or None
    if not sec and not field:
        return None
    return {"section": sec, "field": field}


def update(app: dict, qid: str, answer=None, status=None, link=None) -> dict | None:
    for it in _state(app)["items"]:
        if it["id"] == qid:
            if answer is not None:
                it["answer"] = str(answer)
            if status is not None:
                it["status"] = status
                it["answered_at"] = _now() if status == "answered" else None
            if link is not None:
                it["link"] = _clean_link(link)
            return it
    return None


def remove(app: dict, qid: str) -> bool:
    st = _state(app)
    n = len(st["items"])
    st["items"] = [i for i in st["items"] if i["id"] != qid]
    return len(st["items"]) < n


# ---- snapshot and diff --------------------------------------------------
def key_fields(app: dict) -> dict:
    """Flat {path: value} of the fields a reviewer would compare between submissions."""
    out: dict = {}
    for root in _SCALAR_ROOTS:
        for k, v in (app.get(root) or {}).items():
            if isinstance(v, (str, int, float, bool)) or v is None:
                out[f"{root}.{k}"] = v
    v = app.get("variance") or {}
    out["variance.topic"] = v.get("topic")
    out["variance.code_or_standard"] = v.get("code_or_standard")
    a = v.get("acceptable_solution") or {}
    out["variance.acceptable_solution.articles"] = list(a.get("articles") or [])
    out["variance.acceptable_solution.explanation"] = a.get("explanation")
    p = v.get("proposed_alternative") or {}
    out["variance.proposed_alternative.summary"] = p.get("summary")
    for m in p.get("mitigations") or []:
        mid = m.get("id") or m.get("label") or "?"
        out[f"variance.mitigations.{mid}.label"] = m.get("label")
        out[f"variance.mitigations.{mid}.detail"] = m.get("detail")
        out[f"variance.mitigations.{mid}.evidence_ids"] = list(m.get("evidence_ids") or [])
    for r in v.get("section_c") or []:
        art = r.get("article") or "?"
        out[f"variance.section_c.{art}.objective"] = r.get("objective")
        out[f"variance.section_c.{art}.function"] = r.get("function")
    for d in app.get("section_d") or []:
        did = d.get("id") or d.get("document_name") or "?"
        out[f"section_d.{did}.document_name"] = d.get("document_name")
        out[f"section_d.{did}.responsible_party"] = d.get("responsible_party")
        out[f"section_d.{did}.status"] = d.get("status")
    return out


def mark_submitted(app: dict, note: str = "") -> dict:
    st = _state(app)
    at = _now()
    st["snapshot"] = {"at": at, "fields": key_fields(app)}
    st["submissions"].append({"n": len(st["submissions"]) + 1, "marked_at": at, "note": note or ""})
    return st["snapshot"]


def _norm(v):
    return "" if _empty(v) else v


def _empty(v):
    return v is None or v == "" or v == []


def diff(app: dict) -> dict:
    st = _state(app)
    snap = st["snapshot"]
    if not snap:
        return {"has_snapshot": False, "marked_at": None, "changes": [],
                "note": "Nothing has been marked as submitted yet."}
    old, cur = snap["fields"], key_fields(app)
    changes = []
    for path in sorted(set(old) | set(cur)):
        o, n = old.get(path), cur.get(path)
        if _norm(o) == _norm(n):
            continue  # also covers an absent key vs an empty value
        kind = "added" if _empty(o) else "removed" if _empty(n) else "changed"
        changes.append({"path": path, "kind": kind, "old": o, "new": n})
    return {"has_snapshot": True, "marked_at": snap["at"], "changes": changes,
            "note": "Compared with the fields as they were when you marked the application as submitted. "
                    "This tool does not send anything; you send it."}
