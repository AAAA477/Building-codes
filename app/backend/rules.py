"""Hand-coded Part 3 vs Part 9 determination and topic classification.

Rule text read from NBC 2023 AE (files/codes/NBC_2023AE_2nd_printing.pdf):
 - Div A 1.3.3.3.(1), pdf p.40: Part 9 applies to buildings of 3 storeys or less in
   building height, building area not exceeding 600 m2, used for major occupancies
   B-4 (home-type care), C, D, E, F-2/F-3.
 - Div A 1.3.3.2.(1), pdf p.39-40: Part 3 applies to post-disaster buildings; Group A;
   Group B (care, treatment or detention); Group F-1; and Group C, D, E, F-2/F-3
   exceeding 600 m2 in building area or exceeding 3 storeys in building height.
"""
from __future__ import annotations
import re

PDF = "NBC_2023AE_2nd_printing.pdf"
CITE_P9 = {"article": "1.3.3.3.(1)", "doc": PDF, "page": 40, "division": "A"}
CITE_P3 = {"article": "1.3.3.2.(1)", "doc": PDF, "page": 39, "division": "A"}
MAX_STOREYS_P9 = 3
MAX_AREA_P9 = 600.0
SUPPORTED_TOPIC = "single_exit_stair"
EDMONTON_PAB = {"doc": "11_Edmonton_Point_Access_Block.pdf", "pages": [4, 8]}

# Candidate acceptable-solution articles (all present in the NBC(AE) 2023 table of contents).
# Objectives/functions/intent text for Section C comes ONLY from corpus lookup.
CANDIDATES = {
    "3": ["3.4.2.1", "3.4.2.3", "3.4.2.4"],  # minimum number of exits; distance between exits; travel distance
    "9": ["9.9.8.2"],                         # number of required exits
}

_KEYWORDS = [
    "single exit", "single-exit", "one exit", "single stair", "single egress", "one stair",
    "point access block", "second exit", "two exits", "egress stair", "exit stair",
    "number of exits",
]


def parse_occupancy(text):
    """Return (group letter, division int|None) or (None, None)."""
    if not text:
        return None, None
    t = text.strip().lower()
    m = re.search(r"\bgroup\s*([a-f])\b[\s,\-]*(?:div(?:ision)?\.?\s*|-)?(\d)?|^\s*([a-f])\b[\s,\-]*(?:div(?:ision)?\.?\s*|-)?(\d)?", t)
    kw = [("residential", "C"), ("apartment", "C"), ("dwelling", "C"), ("assembly", "A"),
          ("care", "B"), ("detention", "B"), ("business", "D"), ("office", "D"),
          ("mercantile", "E"), ("retail", "E"), ("industrial", "F")]
    letter = div = None
    if m:
        letter = (m.group(1) or m.group(3)).upper()
        d = m.group(2) or m.group(4)
        div = int(d) if d else None
    else:
        for w, l in kw:
            if w in t:
                letter = l
                break
    if letter == "B" and re.search(r"home[- ]type", t):
        div = 4
    return letter, div


def determine_part(project: dict) -> dict:
    """Return {part:'3'|'9'|None, confidence, basis, missing, message}."""
    letter, div = parse_occupancy(project.get("occupancy"))
    storeys, area = project.get("storeys"), project.get("building_area_m2")
    missing = []
    if letter is None:
        missing.append("project.occupancy")
    if storeys is None:
        missing.append("project.storeys")
    if area is None:
        missing.append("project.building_area_m2")

    def out(part, conf, cite, msg):
        return {"part": part, "confidence": conf, "basis": [cite] if cite else [],
                "missing": missing, "message": msg}

    if letter == "A":
        return out("3", 0.95, CITE_P3, "Group A (assembly) is Part 3 (1.3.3.2.).")
    if letter == "B" and div != 4:
        if div is None:
            return out("3", 0.7, CITE_P3, "Group B other than Division 4 is Part 3; give the Division to confirm (B-4 home-type care can be Part 9).")
        return out("3", 0.95, CITE_P3, "Group B care, treatment or detention is Part 3 (1.3.3.2.).")
    if letter == "F" and div == 1:
        return out("3", 0.95, CITE_P3, "Group F-1 high-hazard industrial is Part 3 (1.3.3.2.).")
    if letter is None:
        return out(None, 0.0, None, "Occupancy not provided; cannot determine Part 3 or Part 9.")
    over = (storeys is not None and storeys > MAX_STOREYS_P9) or (area is not None and area > MAX_AREA_P9)
    f_unknown = letter == "F" and div is None
    if over:
        return out("3", 0.6 if f_unknown else 0.9, CITE_P3,
                   f"Group {letter} exceeds {MAX_AREA_P9:.0f} m2 or {MAX_STOREYS_P9} storeys: Part 3 (1.3.3.2.(1)(c)).")
    if storeys is None or area is None:
        return out(None, 0.3, None, "Storeys and building area are needed to decide between Part 3 and Part 9.")
    if f_unknown:
        missing.append("project.occupancy (Group F division)")
        return out(None, 0.3, None, "Group F division needed (F-1 is Part 3; F-2/F-3 can be Part 9).")
    return out("9", 0.9, CITE_P9,
               f"Group {letter}, {storeys} storey(s), {area:g} m2: within Part 9 limits "
               f"({MAX_STOREYS_P9} storeys, {MAX_AREA_P9:.0f} m2) per 1.3.3.3.(1). Post-disaster status not assessed.")


LOOKUP_TOPIC = "other_nbc"
TOPICS = [
    {"id": "single_exit_stair", "label": "Single-exit stair (point access block)", "mode": "guided",
     "description": "Guided intake, Section C pre-fill, Section D checklist and a professional stop for a single-exit stair / Point Access Block."},
    {"id": LOOKUP_TOPIC, "label": "Any other NBC requirement", "mode": "lookup",
     "description": "Search the NBC(AE) 2023 text, add the articles you are varying to Section C (objectives, functions and intent are looked up), "
                    "and use the generic Division C 2.3.1.1 checklist. Confirm with the Safety Codes Officer whether a registered professional is needed."},
]


def mode_of(app: dict) -> str:
    """'guided' only for the single-exit stair topic; every other topic is 'lookup'."""
    return "guided" if (app.get("variance", {}).get("topic") or "").strip() == SUPPORTED_TOPIC else "lookup"


def classify(app: dict, suggested=None) -> dict:
    proj = app.get("project", {})
    var = app.get("variance", {})
    pr = determine_part(proj)
    declared = (var.get("topic") or "").strip() or None
    text = " ".join([proj.get("description", ""),
                     var.get("proposed_alternative", {}).get("summary", ""),
                     var.get("acceptable_solution", {}).get("explanation", "")]).lower()
    hit = any(k in text for k in _KEYWORDS)
    if declared == SUPPORTED_TOPIC:
        guided, conf = True, (0.95 if hit else 0.7)
    elif declared:
        guided, conf = False, 0.6
    elif hit:
        guided, conf = True, 0.6
    else:
        guided, conf = False, 0.3 if text.strip() else 0.2
    topic = SUPPORTED_TOPIC if guided else LOOKUP_TOPIC
    if guided:
        msg = "Guided topic: single-exit stair."
        if not hit and text.strip():
            msg += " The description does not mention exits or stairs; if this is about something else, set the topic to other_nbc."
    else:
        msg = ("Lookup mode: any other NBC(AE) 2023 requirement. Search for the article(s) being varied and add them to Section C; "
               "Section C attribution is looked up from the code text. No guided stair module applies.")
    out = {"part": pr["part"], "topic": topic, "mode": "guided" if guided else "lookup", "confidence": round(conf, 2),
           "supported": True, "message": msg, "part_basis": pr["basis"], "part_missing": pr["missing"],
           "part_confidence": pr["confidence"], "part_message": pr["message"]}
    if declared and declared != topic:
        out["declared_topic"] = declared
    if suggested is not None:
        out["suggested_articles"] = suggested
    return out


def _stair_file():
    import json
    from models import DATA
    try:
        return json.loads((DATA / "corpus" / "stair_articles.json").read_text(encoding="utf-8")).get("articles", [])
    except (OSError, ValueError):
        return []


CORE_GROUPS = {"number_of_exits", "exit_location_travel"}


def candidate_articles(app: dict, scope: str = "core") -> list:
    given = app.get("variance", {}).get("acceptable_solution", {}).get("articles") or []
    if given:
        return list(given)
    part = app.get("project", {}).get("part") or determine_part(app.get("project", {}))["part"]
    cands = [a["article"] for a in _stair_file()
             if "article" in a and ":" not in a["article"] and (scope == "all" or a.get("group") in CORE_GROUPS)]
    if cands:
        if part == "9":
            return [c for c in cands if c.startswith("9.")] or CANDIDATES["9"]
        return [c for c in cands if not c.startswith("9.")]
    return CANDIDATES.get(part or "3", CANDIDATES["3"])
