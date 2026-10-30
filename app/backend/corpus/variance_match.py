"""Variance cards: loader, matcher and outcome state (no LLM).

match_cards(app) ranks the STANDATA variance cards against an application using the existing precedents retrieval.
It only proposes: "covered_candidate" (current-edition card, strong match) or "near_miss". The applicant's answers to
each condition turn a hint into a state with outcome_state(); nothing here says a design is compliant or safe.
"""
from __future__ import annotations
import json
from functools import lru_cache
from pathlib import Path

from . import ROOT
from . import precedents as P

CARDS_DIR = ROOT / "app" / "data" / "content" / "variance_cards"
CURRENT_EDITION = "NBC(AE) 2023"
ANSWERS = ("yes", "no", "unsure")


@lru_cache(maxsize=1)
def all_cards() -> list[dict]:
    if not CARDS_DIR.exists():
        return []
    return [json.load(open(p, encoding="utf8")) for p in sorted(CARDS_DIR.glob("*.json")) if not p.name.startswith("_")]


@lru_cache(maxsize=1)
def _by_pdf() -> dict:
    return {Path(c["pdf"]).name: c for c in all_cards()}


@lru_cache(maxsize=1)
def _by_id() -> dict:
    return {c["id"]: c for c in all_cards()}


def _latest(c: dict) -> dict:
    while c.get("superseded_by") and c["superseded_by"] in _by_id():
        c = _by_id()[c["superseded_by"]]
    return c


def get_card(number: str, include_review: bool = False) -> dict | None:
    """The current (latest revision) card for this STANDATA number or card id; an old revision's number resolves to its successor."""
    for c in all_cards():
        if number == c["id"] or number in c["numbers"] or number == c["number"]:
            c = _latest(c)
            return c if (include_review or not c["needs_review"]) else None
    return None


def _title_overlap(hit: dict, key_terms) -> bool:
    """The title shares at least two topic words (one if the topic has only one): a single generic word like 'devices' is not enough."""
    need = min(len(key_terms), 2)
    return bool(key_terms) and len(set(key_terms) & set(hit.get("_title_terms", []))) >= need


def _reason(hit: dict, key_terms, topic: str) -> str:
    parts = []
    arts = hit.get("_matched_articles") or []
    if arts:
        parts.append("Cites " + ", ".join(arts) + ", which your application also relies on.")
    if key_terms and _title_overlap(hit, key_terms):
        parts.append("Its title covers the same subject" + (f": {topic.replace('_', ' ')}." if topic else "."))
    return " ".join(parts) or "Matched by text similarity only; check whether it applies."


def _twin(a: dict, b: dict) -> bool:
    """Same variance in another edition: the two cards vary mostly the same articles, or carry the same title."""
    if P.normalise_title(a["title"]) == P.normalise_title(b["title"]):
        return True
    x, y = set(a["articles_varied"]), set(b["articles_varied"])
    return bool(x and y) and len(x & y) / len(x | y) >= 0.5


THIN_COVERED_SCORE = 1.5 * P.STRONG_SCORE   # an application with no topic and no articles: how strong the top hit must be
THIN_MARGIN = 1.5                           # ...and how far ahead of every different variance


def match_cards(app: dict, k: int = 3) -> list[dict]:
    """Best variance cards for an application: [{number, hint, reason, matched_articles, score}], best first."""
    try:
        hits = P.app_precedents(app, k=12)
    except Exception:
        return []
    kt = P._key_terms(app)
    topic = ((app.get("variance") or {}).get("topic") or "")
    best: dict[str, dict] = {}
    for h in hits:
        card = _by_pdf().get(Path(h.get("doc", "")).name)
        if card is None:
            continue
        card = _latest(card)
        if card["needs_review"]:
            continue
        arts = h.get("_matched_articles") or []
        strong = P.strong(h, kt)
        related = bool(arts) or _title_overlap(h, kt) or (not kt and h["score"] >= P.STRONG_SCORE)   # text-only matches only when the applicant has named no topic
        if not (strong or related):
            continue
        hint = "covered_candidate" if (strong and card["edition"] == CURRENT_EDITION and card["conditions"]) else "near_miss"
        cur = best.get(card["number"])
        if cur is None or h["score"] > cur["score"]:
            best[card["number"]] = {"number": card["number"], "hint": hint, "reason": _reason(h, kt, topic),
                                    "matched_articles": arts, "score": h["score"]}
    out = sorted(best.values(), key=lambda m: -m["score"])
    # an older-edition match also offers its current-edition successor (same variance, newer code)
    have = {m["number"] for m in out}
    for m in list(out):
        c = get_card(m["number"])
        if c["edition"] == CURRENT_EDITION:
            continue
        for succ in all_cards():
            if succ["current"] and not succ["needs_review"] and succ["edition"] == CURRENT_EDITION and succ["number"] not in have                     and _twin(c, succ):
                out.append({"number": succ["number"], "hint": "near_miss", "reason": f"Current-edition version of {m['number']}, which matched your description.",
                            "matched_articles": m["matched_articles"], "score": m["score"] + 0.01})   # ranks just above its older twin
                have.add(succ["number"])
    out.sort(key=lambda m: -m["score"])
    # thin application (no topic, no cited articles): a clear, isolated top hit may be a covered candidate
    if out and not kt and not any(m["matched_articles"] for m in out):
        top = out[0]
        tc = get_card(top["number"])
        others = [m["score"] for m in out[1:] if not _twin(tc, get_card(m["number"]))]
        if (tc["edition"] == CURRENT_EDITION and tc["conditions"] and top["score"] >= THIN_COVERED_SCORE
                and all(sc * THIN_MARGIN <= top["score"] for sc in others)):
            top["hint"] = "covered_candidate"
    covered = [get_card(m["number"]) for m in out if m["hint"] == "covered_candidate"]
    out = [m for m in out if m["hint"] == "covered_candidate" or not any(_twin(get_card(m["number"]), c) for c in covered)]
    return out[:k]


def _answer_map(answers) -> dict:
    return {a["index"]: a["answer"] for a in (answers or []) if a.get("answer") in ANSWERS}


def gaps(conditions: list[dict], answers) -> list[dict]:
    """Conditions not confirmed 'yes'. 'unsure' and unanswered count as unmet."""
    am = _answer_map(answers)
    return [{**c, "answer": am.get(c["index"], "unanswered")} for c in conditions if am.get(c["index"]) != "yes"]


def outcome_state(hint: str, conditions: list[dict], answers) -> str:
    """covered | conditional | near_miss. Covered only when every condition is answered yes."""
    if hint != "covered_candidate" or not conditions:
        return "near_miss"
    return "conditional" if gaps(conditions, answers) else "covered"


def no_match_state() -> str:
    return "none"
