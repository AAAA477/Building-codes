"""Variance-card endpoints (mounted automatically by main.py).

GET /api/applications/{id}/variance-match                 - outcome + matching STANDATA variance cards with their condition checklist
PUT /api/applications/{id}/variance/relied-on             - body {number, condition_answers:[{index, answer: yes|no|unsure}]}
GET /api/applications/{id}/variance/starting-point?number - borrowed conditions/articles from a near-miss variance, to be accepted
                                                            through /suggest/accept with provenance "precedent"
Nothing here says a design is safe, compliant or approved; the authority having jurisdiction decides.
"""
from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException, Query

import models
from corpus import variance_match as V, verifier

router = APIRouter()

GAP_MESSAGE = ("To rely on this variance your design must meet these conditions. Either adjust the design to meet them, "
               "or file your own variance request.")
COVERED_MESSAGE = "This variance may cover your situation. The authority having jurisdiction decides; confirm with them before relying on it."
NOTE = "Found by search; read the variance yourself. This does not confirm that your design is covered."
EMPTY_NOTE = "We found no earlier decision that looks like yours. That does not mean none exists; ask your authority if unsure."


def _app(app_id: str) -> dict:
    a = models.load(app_id)
    if a is None:
        raise HTTPException(404, f"application {app_id} not found")
    return a


def _answers_for(a: dict, number: str) -> list:
    r = (a.get("variance") or {}).get("relied_on") or {}
    return r.get("condition_answers", []) if r.get("number") == number else []


def _message(state: str, card: dict) -> str:
    if state == "covered":
        return COVERED_MESSAGE
    earlier = "" if card["edition"] == V.CURRENT_EDITION else \
        f"Issued under an earlier code edition ({card['edition']}); confirm it still applies. "
    if state == "near_miss":
        return earlier + "This variance is close to your situation but not a match you can rely on as it stands. " + GAP_MESSAGE
    return GAP_MESSAGE


def _item(card: dict, hint: str, reason: str, answers: list, matched_articles=()) -> dict:
    state = V.outcome_state(hint, card["conditions"], answers)
    am = V._answer_map(answers)
    return {
        "number": card["number"], "title": card["title"], "edition": card["edition"], "date_issued": card["date_issued"],
        "hint": hint, "state": state, "reason": reason, "matched_articles": list(matched_articles),
        "earlier_edition": card["edition"] != V.CURRENT_EDITION,
        "conditions": [{"index": c["index"], "label": c["label"], "text": c["text"], "page": c["page"],
                        "answer": am.get(c["index"], "unanswered")} for c in card["conditions"]],
        "gaps": V.gaps(card["conditions"], answers),
        "message": _message(state, card),
        "variance_text": card["variance_text"] if not card["conditions"] else "",
        "source": card.get("source") or {"doc": card["pdf"].split("/")[-1], "page": 1},
    }


@router.get("/api/applications/{app_id}/variance-match")
def variance_match(app_id: str):
    a = _app(app_id)
    items = []
    for m in V.match_cards(a):
        card = V.get_card(m["number"])
        items.append(_item(card, m["hint"], m["reason"], _answers_for(a, m["number"]), m["matched_articles"]))
    if not items:
        return {"outcome": "none", "items": [], "note": EMPTY_NOTE}
    rank = {"covered": 0, "conditional": 1, "near_miss": 2}
    relied = ((a.get("variance") or {}).get("relied_on") or {}).get("number")
    best = next((i for i in items if i["number"] == relied), None) or sorted(items, key=lambda i: rank[i["state"]])[0]
    return {"outcome": best["state"], "items": items, "note": NOTE}


def _validated(card: dict, answers) -> list:
    if not isinstance(answers, list):
        raise HTTPException(422, "condition_answers must be a list of {index, answer}")
    valid = {c["index"] for c in card["conditions"]}
    out = {}
    for x in answers:
        if not isinstance(x, dict) or x.get("index") not in valid:
            raise HTTPException(422, f"index must be one of {sorted(valid)}")
        if x.get("answer") not in V.ANSWERS:
            raise HTTPException(422, f"answer must be one of {list(V.ANSWERS)}")
        out[x["index"]] = x["answer"]
    return [{"index": i, "answer": v} for i, v in sorted(out.items())]


@router.put("/api/applications/{app_id}/variance/relied-on")
def put_relied_on(app_id: str, body: dict = Body(...)):
    a = _app(app_id)
    number = str((body or {}).get("number") or "")
    card = V.get_card(number)
    if card is None:
        raise HTTPException(404, f"no current variance card {number!r}")
    answers = _validated(card, (body or {}).get("condition_answers", []))
    a.setdefault("variance", {})["relied_on"] = {"number": card["number"], "edition": card["edition"], "condition_answers": answers}
    a = models.normalize(a)
    import main
    main.refresh(a)
    models.save(a)
    match = next((m for m in V.match_cards(a) if m["number"] == card["number"]), None)
    hint = match["hint"] if match else ("covered_candidate" if card["edition"] == V.CURRENT_EDITION and card["conditions"] else "near_miss")
    return _item(card, hint, match["reason"] if match else "Chosen by the applicant.", answers, match["matched_articles"] if match else ())


@router.get("/api/applications/{app_id}/variance/starting-point")
def starting_point(app_id: str, number: str = Query(...)):
    a = _app(app_id)
    card = V.get_card(number)
    if card is None:
        raise HTTPException(404, f"no current variance card {number!r}")
    match = next((m for m in V.match_cards(a) if m["number"] == card["number"]), None)
    if match and match["hint"] == "covered_candidate":
        return {"items": [], "note": "This variance may cover your situation as it stands; use its conditions as the checklist instead."}
    var = a.get("variance") or {}
    have_mit = {m.get("id") for m in (var.get("proposed_alternative") or {}).get("mitigations", [])}
    have_art = set((var.get("acceptable_solution") or {}).get("articles", []))
    items = []
    for c in card["conditions"]:
        mid = f"V-{card['number']}-{c['label']}"
        if mid in have_mit:
            continue
        items.append({"id": mid, "kind": "precedent", "field_path": "variance.proposed_alternative.mitigations", "append": True,
                      "label": f"Based on STANDATA {card['number']}, condition {c['label']}",
                      "value": {"id": mid, "label": f"Based on STANDATA {card['number']}, condition {c['label']}",
                                "detail": c["text"], "evidence_ids": []},
                      "why": f"Borrowed from {card['title']} ({card['edition']}). Confirm it applies to your project, or change it.",
                      "source": {"doc": card["pdf"].split("/")[-1], "page": c["page"]}})
    for art in card["articles_varied"][:8]:
        if art in have_art or card.get("article_codes", {}).get(art) != "NBC" or not verifier.article_exists(art):   # Division B articles only
            continue
        items.append({"id": f"V-{card['number']}-art-{art}", "kind": "precedent", "field_path": "variance.acceptable_solution.articles",
                      "append": True, "label": f"Code article {art} (varied by STANDATA {card['number']})", "value": art,
                      "why": f"Named in {card['number']}. Keep it only if your project varies the same requirement.",
                      "source": {"doc": card["pdf"].split("/")[-1], "page": (card.get("source") or {}).get("page", 1)}})
    return {"items": items, "note": NOTE}
