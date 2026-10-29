"""Completeness hook: open officer questions become confirm items (see completeness.compute)."""
from __future__ import annotations
import questions

_STATUS = {"open": "uncertain", "needs_professional": "needs_professional"}


def items(app: dict) -> list:
    out = []
    for q in questions.list_items(app):
        st = _STATUS.get(q.get("status"))
        if not st:
            continue
        link = q.get("link") or {}
        sec = link.get("section") or "D"
        text = " ".join((q.get("text") or "").split())
        label = "Officer question: " + (text[:90] + ("..." if len(text) > 90 else ""))
        msg = ("Officer question marked as needing a registered professional; the applicant cannot answer it alone."
               if st == "needs_professional" else "Officer question not yet answered.")
        out.append({"id": f"Q.{q['id']}", "label": label, "section": sec, "status": st, "message": msg,
                    "node_id": "", "group": "admin", "priority": 2})
    return out
