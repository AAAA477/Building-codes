"""Deterministic detector for requests the tool must not answer: approval odds and safety /
compliance / equivalence verdicts. No LLM involved. Used by the suggest and search routes."""
from __future__ import annotations
import re
from typing import Optional

_W = r"(?:[\w'\-/,]+\s+){0,6}?"   # a few filler words between key terms
_SUBJ = r"(?:this|that|it|my|our|the|these|those|such|a|an|their)"
_ADJ = (r"(?:safe|unsafe|dangerous|compliant|non-?compliant|code[\s\-]?compliant|equivalent|equal|equally\s+safe|"
        r"acceptable|good\s+enough|adequate|sufficient|legal|ok|okay|fine|allowed|permitted|up\s+to\s+code|"
        r"in\s+compliance|within\s+code)")
_AHJ = (r"(?:officer|sco|inspector|examiner|reviewer|plans\s+examiner|authority|ahj|city|municipality|"
        r"accreditation|administrator|board|council|they|safety\s+codes)")
_OK = r"(?:approve[ds]?|accept(?:ed)?|grant(?:ed)?|allow(?:ed)?|permit(?:ted)?|agree|sign\s+off|pass(?:ed)?|go\s+for|buy)"

_PATTERNS = [
    # approval odds
    ("approval", rf"\bwill\s+{_W}{_AHJ}\s+{_W}{_OK}\b"),
    ("approval", rf"\bwill\s+(?:i|we|my\s+\w+|this|it|the\s+\w+(?:\s+\w+)?)\s+(?:be\s+|get\s+(?:\w+\s+)?)?{_OK}\b"),
    ("approval", rf"\b(?:would|do\s+you\s+think|think)\s+{_W}{_AHJ}\s+{_W}{_OK}\b"),
    ("approval", r"\b(?:chances?|odds|likelihood|probability|prospects?)\s+(?:of|that|for)\b[\w\s,'\-]{0,40}?\b(?:approv|accept|pass|grant)"),
    ("approval", r"\b(?:how\s+likely|what\s+are\s+the\s+chances)\b"),
    ("approval", rf"\bget\s+{_W}(?:variance|permit|alternative\s+solution|this)\s+approved\b"),
    ("approval", r"\b(?:guarantee[ds]?|ensure|promise|assure)\s+(?:me\s+)?(?:that\s+)?(?:\w+\s+){0,4}?(?:approv|accept|pass|compl|safe|equivalen|meets?|get)"),
    ("approval", r"\b(?:can|could|will|would)\s+you\s+(?:guarantee|promise|assure|confirm|certify|approve)\b"),
    ("approval", r"\b(?:is|are)\s+(?:this|it|my\s+\w+)\s+(?:likely|going|sure|certain)\s+to\s+(?:be\s+)?(?:approv|accept|pass)"),
    ("approval", r"\bsign\s*off\s+on\b|\bapprove\s+(?:this|my|our)\s+(?:\w+\s+)?(?:design|variance|application|proposal|plan|alternative|request|submission)\b"),
    # safety / compliance / equivalence verdicts
    ("verdict", rf"\b(?:is|are|would|will|could|can)\s+{_SUBJ}\s+{_W}{_ADJ}\b(?=\s*[\?\.!,]|\s*$|\s+(?:to|for|with|as|under|by|enough)\b)"),
    ("verdict", rf"\b(?:is|are)\s+{_SUBJ}\s+(?:\w+\s+){{0,4}}?(?:design|proposal|plan|building|alternative|solution|approach|system|assembly|arrangement)\s+{_ADJ}\b"),
    ("verdict", r"\bdo(?:es)?\s+(?:this|it|my|our|the|these|that)\b[\w\s,'\-]{0,60}?\b(?:meet|satisfy|comply|conform|pass|achieve)\b[\w\s,'\-]{0,30}?\b(?:code|nbc|nfc|npc|necb|requirements?|intent|objectives?|standard|regulations?)"),
    ("verdict", rf"\b(?:is|are)\s+(?:this|it|my\s+\w+|our\s+\w+)\s+(?:in\s+)?(?:compliance|conformity)\b"),
    ("verdict", rf"\b(?:tell|show|confirm|verify|certify|prove|check|determine|decide|judge|assess)\s+(?:me\s+)?(?:that\s+|if\s+|whether\s+|it\s+is\s+)?{_W}(?:safe|compliant|complies|equivalent|meets?\s+(?:the\s+)?code|conforms?|acceptable|good\s+enough)\b"),
    ("verdict", r"\b(?:is\s+it|would\s+it\s+be|is\s+that)\s+(?:ok|okay|fine|safe|legal|acceptable|allowed)\s+to\b"),
    ("verdict", r"\b(?:equivalent|equal|as\s+safe\s+as|better\s+than)\b[\w\s,'\-]{0,40}\b(?:acceptable\s+solution|prescriptive|code)\b[\w\s,'\-]{0,15}\?"),
    ("verdict", r"\bdoes\s+(?:this|it|my\s+\w+)\s+(?:provide|give|offer)\s+(?:an\s+)?equivalent\b"),
]
_COMPILED = [(k, re.compile(p, re.I)) for k, p in _PATTERNS]

MESSAGE = ("This tool cannot tell you whether a design will be approved, is safe, is equivalent to the code, or "
           "complies. Those judgements belong to the authority having jurisdiction and to the responsible "
           "professional (architect or engineer) who stands behind the design.")
CAN_DO = [
    "Check whether the application is complete and point out missing information.",
    "Find the relevant code text and show exactly where it comes from.",
    "Find similar variances and interpretations that are already published.",
    "Help word your own description more clearly, using only what you wrote.",
]


def check(text: Optional[str]) -> Optional[dict]:
    """Return a standard refusal dict if the text asks for approval odds or a safety / compliance /
    equivalence verdict; otherwise None. Pure function, no LLM."""
    t = " ".join((text or "").split())
    if len(t) < 6:
        return None
    for kind, rx in _COMPILED:
        m = rx.search(t)
        if m:
            return {"refused": True, "kind": kind, "matched": m.group(0)[:80], "message": MESSAGE, "can_do": list(CAN_DO)}
    return None
