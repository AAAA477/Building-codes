"""Completeness items for the STANDATA variance the applicant relies on (pattern of evidence_items.py / questions_items.py).

One item per condition of the variance in variance.relied_on. A condition counts as met only when answered 'yes';
'no' is missing, 'unsure' and unanswered are uncertain. Wording is about conditions, never about safety or approval.
"""
from __future__ import annotations


def items(app: dict) -> list:
    rel = (app.get("variance") or {}).get("relied_on") or {}
    if not rel.get("number"):
        return []
    try:
        from corpus import variance_match as V
        card = V.get_card(rel["number"])
    except Exception:
        return []
    if card is None:
        return []
    am = V._answer_map(rel.get("condition_answers"))
    out = []
    for c in card["conditions"]:
        a = am.get(c["index"], "unanswered")
        out.append({"id": f"V.cond.{card['number']}.{c['index']}", "label": f"STANDATA {card['number']} condition {c['label']}",
                    "section": "V", "group": "alternative", "priority": 2,
                    "status": "complete" if a == "yes" else ("missing" if a == "no" else "uncertain"),
                    "message": c["text"] if a != "yes" else "", "node_id": "alternative"})
    return out
