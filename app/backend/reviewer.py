"""Reviewer summary and RFI draft: deterministic, completeness-only, no safety judgment.
Items are ranked the way a Safety Codes Officer checks them (see completeness.GROUP_ORDER)."""
from __future__ import annotations
import re

import completeness as cp

RECIPIENTS = {
    "scc": "accreditation@safetycodes.ab.ca",
    "calgary": None,   # assigned Safety Codes Officer (email on the permit file)
    "edmonton": None,  # plans examiner on the permit file (unconfirmed)
}
DISCLAIMER = "Completeness check only; no statement is made about safety, equivalence or approval."
RFI_HEADINGS = ["Code articles and citations", "Proposed alternative and evidence",
                "Supporting documents and professional", "Administrative details",
                "Signatures and declarations"]
_BRACKET = re.compile(r"\s*\[[^\]]*\]")


def _clean(t) -> str:
    return re.sub(r"\s{2,}", " ", _BRACKET.sub("", t or "")).strip()


def _real(v) -> str:
    return v.strip() if cp._txt(v) else ""


def _gaps(comp):
    return [i for i in comp["items"] if i["status"] != "complete"]


def _ranked(comp):
    gi = {g: n for n, g in enumerate(cp.GROUP_ORDER)}
    return sorted(_gaps(comp), key=lambda i: (i.get("priority", 4), gi.get(i.get("group"), 9)))


def _topic(app):
    return (app.get("variance", {}).get("topic") or "variance").replace("_", " ")


def _ref(app):
    loc = app.get("location", {})
    pn, ad = _real(loc.get("permit_number")), _real(loc.get("municipal_address"))
    if pn:
        return f"permit {pn}"
    if ad:
        return ad
    return f"the {_topic(app)} variance application"


def summary(app: dict, comp: dict) -> dict:
    gaps = _gaps(comp)
    n = {s: sum(1 for g in gaps if g["status"] == s) for s in ("missing", "uncertain", "needs_professional")}
    top = comp.get("top_issues") or []
    headline = comp.get("headline") or "No open items found."
    m = comp.get("meters", {})
    a = m.get("admin", {})
    parts = [_clean(comp.get("detail", ""))]
    if top:
        parts.append((f"Check first: {_clean(top[0]['label'])}. {_clean(top[0]['why'])}").rstrip(".") + ".")
    parts.append(DISCLAIMER)
    words = " ".join(p for p in parts if p).split()
    text = " ".join(words[:79]) + "." if len(words) > 80 else " ".join(words)
    return {"headline": headline, "top_issues": top, "summary": text, "word_count": len(text.split()),
            "counts": n, "percent": comp["percent"], "meters": m, "signatures": comp.get("signatures"),
            "ai_assisted": __import__("privacy").disclosure(app)}


def _article_of(label):
    m = re.search(r"(\d+\.\d+\.\d+\.\d+(?:\.\(\d+\))?)", label or "")
    return m.group(1) if m else None


def _item_text(it):
    i, lab, msg = it["id"], _clean(it["label"]), _clean(it.get("message"))
    art = _article_of(lab)
    if i.startswith("C.article.") and art:
        return f"Section C: article {art} was not found in NBC(AE) 2023; please correct it.", art
    if i.startswith("C.row."):
        cite = lab.split(": ", 1)[-1]
        if "no objectives" in msg:
            return (f"Section C: {cite} exists but the NBC attributes no objectives to it; "
                    "please confirm the root-article objectives apply."), art
        return f"Section C: the citation {cite} could not be verified against NBC(AE) 2023; please confirm it.", art
    if i == "C.articles":
        return "Section C: no acceptable-solution articles are cited; please list the articles being varied.", None
    if i == "C.table":
        return "Section C: the table of articles, objectives, functions and intents is not completed; please complete it.", None
    if i == "C.code_or_standard":
        return "Section C: please state the code or standard and edition being varied.", None
    if i == "C.explanation":
        return "Section C: please explain the acceptable solution that is being varied.", None
    if i == "C.alternative":
        return "Section C: please describe the proposed alternative.", None
    if i == "C.mitigations":
        return "Section C: please list the mitigating features of the proposed alternative.", None
    if i.startswith("C.mitigation."):
        what = lab.replace("Evidence for: ", "", 1)
        return f"Section C: \"{what}\" has no evidence document referenced; please identify one.", None
    if i == "D.documents":
        return "Section D: no supporting documents are listed; please list each document and who is responsible for it.", None
    if i == "D.professional_named":
        return ("Section D: no registered professional is named as responsible for any document; "
                "please name the professional (Edmonton PAB guide p.8)."), "Edmonton PAB guide p.8"
    if i == "D.professional":
        if it["status"] == "needs_professional":
            return cp.PRO_STOP + ". Please confirm who the professional is.", "Edmonton PAB guide p.8"
        return cp.PRO_CONFIRM + ".", "NBC Division C 2.4.1.1"
    if i.startswith("D.doc."):
        return f"Section D: {lab.replace('Document: ', '', 1)}: {msg or it['status']}.", None
    if i.startswith("A."):
        return f"Section A: please provide {lab[:1].lower() + lab[1:]}.", None
    if i.startswith("B."):
        if not msg or msg.lower() == f"{lab.lower()} not provided":
            return f"Section B: please provide {lab[:1].lower() + lab[1:]}.", None
        return f"Section B: {lab}: {msg.rstrip('.')}.", None
    if i.startswith("SIGN."):
        return f"{lab}: to be completed by the owner or representative; this office cannot complete it.", None
    return f"{lab}: {msg or it['status']}.", None


def _group_title(g):
    return cp.GROUP_TITLE.get(g, "Administrative details")


def rfi_draft(app: dict, comp: dict) -> dict:
    juris = app.get("jurisdiction", "scc")
    owner = _real(app.get("applicant", {}).get("owner_name"))
    ref = _ref(app)
    items = []
    for it in _ranked(comp):
        text, code_ref = _item_text(it)
        items.append({"id": it["id"], "label": _clean(it["label"]), "group": _group_title(it.get("group")),
                      "code_ref": code_ref, "text": _clean(text).replace("..", ".")})
    groups = [h for h in RFI_HEADINGS if any(x["group"] == h for x in items)]
    lines = ["DRAFT - request for information (for the reviewer to edit and send; not sent by this tool)", "",
             f"Re: Variance application, {ref}", f"Dear {owner or 'applicant'},", "",
             "Thank you for your application. To continue our completeness review, please address the following:", ""]
    n = 0
    for h in groups:
        lines.append(h)
        for x in (x for x in items if x["group"] == h):
            n += 1
            lines.append(f"{n}. {x['text']}")
        lines.append("")
    if not items:
        lines += ["No outstanding items were found in the completeness check.", ""]
    lines += [DISCLAIMER, "", "Regards,", "Safety Codes Officer (name to be added by the reviewer)"]
    return {"status": "DRAFT", "to": _real(app.get("applicant", {}).get("email")) or None,
            "reviewer_recipient_hint": RECIPIENTS.get(juris),
            "subject": f"DRAFT: Request for information - {ref}",
            "body": "\n".join(lines), "items": items, "groups": groups}
