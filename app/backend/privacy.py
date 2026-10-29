"""Privacy controls for the hosted model.

- Per-application switch: top-level key `ai_enabled` (default True) on the application.
- A request-scoped context (set by the middleware in routes_privacy.py, or with `scope()`) that
  llm.py and agentic.py consult before ANY hosted-model call. When off, no text leaves the server.
- `redact()` strips obvious personal data (email, phone, postal code, street address and the
  owner / representative / address values on the application) from text before it is sent.
"""
from __future__ import annotations
import contextlib
import contextvars
import re
from typing import Iterable, Optional

_enabled: contextvars.ContextVar = contextvars.ContextVar("ai_enabled", default=True)
_terms: contextvars.ContextVar = contextvars.ContextVar("redact_terms", default=())

NOTICE = ("When AI help is on, the text you type into a suggestion (for example your project description) and "
          "your plain-language search questions are sent to a hosted model (Azure OpenAI) so it can draft wording. "
          "Emails, phone numbers, the owner's name and street addresses are removed first. "
          "When AI help is off, nothing is sent: suggestions use only the built-in offline tools. "
          "Do not type personal information you do not need to; names and addresses are not needed for suggestions.")


def is_enabled(app: Optional[dict]) -> bool:
    return not (isinstance(app, dict) and app.get("ai_enabled") is False)


def ai_allowed() -> bool:
    return bool(_enabled.get())


def current_terms() -> tuple:
    return _terms.get()


@contextlib.contextmanager
def scope(enabled: bool = True, app: Optional[dict] = None):
    """Set the AI switch (and the personal values to redact) for the duration of a block."""
    t1 = _enabled.set(bool(enabled) and is_enabled(app))
    t2 = _terms.set(app_terms(app) if app else _terms.get())
    try:
        yield
    finally:
        _enabled.reset(t1)
        _terms.reset(t2)


# ---------------------------------------------------------------- redaction
_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_PHONE = re.compile(r"(?<![\d.])(?:\+?1[\s.\-]?)?(?:\(\d{3}\)\s?|\d{3}[\s.\-])\d{3}[\s.\-]\d{4}(?![\d])")
_POSTAL = re.compile(r"\b[ABCEGHJ-NPRSTVXY]\d[ABCEGHJ-NPRSTV-Z][\s\-]?\d[ABCEGHJ-NPRSTV-Z]\d\b", re.I)
_STREET_TYPES = (r"Street|St|Avenue|Ave|Road|Rd|Drive|Dr|Boulevard|Blvd|Way|Crescent|Cres|Close|Lane|Ln|Court|Ct|"
                 r"Place|Pl|Trail|Terrace|Terr|Gate|Link|Green|Heights|Common|Manor|Bay|Circle|Cir|Highway|Hwy")
_STREET = re.compile(
    r"\b(?:(?:Suite|Unit|#)\s*\d+[A-Za-z]?[\s,\-]+)?\d{1,6}[A-Za-z]?\s+(?:\d{1,3}(?:st|nd|rd|th)\s+|[A-Z][A-Za-z'\-]*\s+){1,3}?"
    rf"(?:{_STREET_TYPES})\b\.?(?:\s+(?:NW|NE|SW|SE|N|S|E|W)\b)?")


def app_terms(app: Optional[dict]) -> tuple:
    """Literal personal values on the application that must never be sent."""
    if not isinstance(app, dict):
        return ()
    ap, loc = app.get("applicant") or {}, app.get("location") or {}
    vals = [ap.get("owner_name"), ap.get("owner_representative"), ap.get("mailing_address"), ap.get("email"),
            ap.get("phone"), loc.get("municipal_address"), loc.get("legal_description")]
    out = []
    for v in vals:
        v = (v or "").strip() if isinstance(v, str) else ""
        if len(v) >= 4 and not (v.startswith("[") and v.endswith("]")):
            out.append(v)
    return tuple(sorted(set(out), key=len, reverse=True))


def redact(text: str, terms: Iterable[str] = ()) -> str:
    """Replace personal data with neutral placeholders. Technical content (areas, article numbers) is kept."""
    if not text:
        return text
    t = text
    for term in terms or ():
        if term:
            t = re.sub(re.escape(term), "[redacted]", t, flags=re.I)
            # also individual capitalised name parts of a person's name (two or more words, no digits)
            parts = term.split()
            if 2 <= len(parts) <= 4 and not re.search(r"\d", term):
                for p in parts:
                    if len(p) >= 4:
                        t = re.sub(rf"\b{re.escape(p)}\b", "[name]", t)
    t = _EMAIL.sub("[email]", t)
    t = _PHONE.sub("[phone]", t)
    t = _POSTAL.sub("[postal code]", t)
    t = _STREET.sub("[address]", t)
    return t


def redact_current(text: str) -> str:
    return redact(text, current_terms())


# ---------------------------------------------------------------- AI-assisted disclosure
def _label(path: str) -> str:
    m = re.match(r"variance\.section_c\.(\d+)\.(\w+)$", path)
    if m:
        return f"Section C row {int(m.group(1)) + 1}, {m.group(2).replace('_', ' ')}"
    return path.split(".")[-1].replace("_", " ").capitalize() + (f" ({path.split('.')[0]})" if "." in path else "")


def ai_fields(app: Optional[dict]) -> list:
    """Fields whose provenance is `ai_draft`: [{path, label}]. Never filtered or hidden."""
    prov = (app or {}).get("provenance") or {}
    return [{"path": p, "label": _label(p)} for p, v in sorted(prov.items())
            if isinstance(v, dict) and v.get("source") == "ai_draft"]


def disclosure(app: Optional[dict]) -> dict:
    fs = ai_fields(app)
    text = ("These fields were drafted with AI assistance and edited/accepted by the applicant: "
            + "; ".join(f["label"] for f in fs) + ". AI output is a draft and is labelled as such."
            if fs else "No fields were drafted with AI assistance.")
    return {"count": len(fs), "fields": fs, "statement": text}
