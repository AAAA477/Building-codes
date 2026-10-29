"""Evidence file storage and readability checks for Section D documents.

Checks cover readability and completeness only (can it be opened, searched, printed; is there any sign of a
signature field or seal text). They never say a document is correct, compliant, or that a seal is valid.
"""
from __future__ import annotations
import hashlib
import json
import re
import uuid
from pathlib import Path
from typing import Optional

from models import STORE_DIR

EVIDENCE_DIR = STORE_DIR / "evidence"
MAX_BYTES = 25 * 1024 * 1024
BIG_BYTES = 10 * 1024 * 1024
BIG_PAGES = 150
ALLOWED = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
           ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
           ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
           ".dwg": "application/acad"}
SEAL_RE = re.compile(r"P\.\s?Eng|\bPEng\b|permit to practice|\bAPEGA\b|\bAAA\b|\bseal(ed)?\b|\bstamp(ed)?\b|"
                     r"registered architect|\bP\.\s?Geo|\bAIBC\b", re.I)
GENERIC_NAME_RE = re.compile(r"^(img[_-]?\d*|image\d*|scan\d*|screenshot.*|untitled\d*|document\d*|new document.*|copy of.*|doc\d*)$", re.I)
# coarse categories used only to flag a filename that clearly names a different kind of document
CATEGORIES = {
    "site plan": r"site[ _-]?plan|survey",
    "drawing": r"drawing|floor[ _-]?plan|elevation|section|plans?\b",
    "report": r"report|analysis|study|memo",
    "letter": r"letter|assurance|commitment",
    "invoice": r"invoice|receipt|quote|resume|cv\b|photo|vacation|holiday",
}


def safe_name(name: Optional[str]) -> str:
    """Keep only the final path component and a conservative character set."""
    n = (name or "").replace("\\", "/").split("/")[-1].replace("\x00", "")
    n = re.sub(r"[^A-Za-z0-9._ \-()]", "_", n).strip(" .")
    n = re.sub(r"\.{2,}", ".", n)
    return (n or "file")[:120]


def safe_id(x: str) -> str:
    s = re.sub(r"[^A-Za-z0-9_\-]", "", str(x or ""))
    if not s or s != str(x):
        raise ValueError("invalid id")
    return s[:60]


def app_dir(app_id: str) -> Path:
    return EVIDENCE_DIR / safe_id(app_id)


def _index_file(app_id: str) -> Path:
    return app_dir(app_id) / "index.json"


def load_index(app_id: str) -> list:
    try:
        return json.loads(_index_file(app_id).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []


def _save_index(app_id: str, recs: list) -> None:
    d = app_dir(app_id)
    d.mkdir(parents=True, exist_ok=True)
    _index_file(app_id).write_text(json.dumps(recs, indent=2), encoding="utf-8")


def _f(level, code, message):
    return {"level": level, "code": code, "message": message}


def _magic_ok(ext: str, head: bytes) -> bool:
    if ext == ".pdf":
        return b"%PDF" in head[:1024]
    if ext == ".png":
        return head.startswith(b"\x89PNG")
    if ext in (".jpg", ".jpeg"):
        return head.startswith(b"\xff\xd8")
    if ext in (".docx", ".xlsx"):
        return head.startswith(b"PK")
    return True


def _name_findings(filename: str, doc_name: str) -> list:
    out = []
    stem = Path(filename).stem
    if GENERIC_NAME_RE.match(stem):
        out.append(_f("warn", "generic_filename", "The file name is generic, so a reviewer cannot tell what it is. Rename it to describe the document before attaching."))
    hit = [c for c, rx in CATEGORIES.items() if re.search(rx, stem, re.I)]
    want = [c for c, rx in CATEGORIES.items() if re.search(rx, doc_name or "", re.I)]
    if hit and want and not set(hit) & set(want):
        out.append(_f("warn", "filename_mismatch", f"The file name looks like a {hit[0]}, but this slot is for \"{(doc_name or '')[:60]}\". Check that you attached the right file."))
    elif hit == ["invoice"] and not want:
        out.append(_f("warn", "filename_mismatch", "The file name looks unrelated to a building document. Check that you attached the right file."))
    return out


def check_pdf(path: Path, size: int, professional_required: bool) -> list:
    import pymupdf
    out: list = []
    try:
        doc = pymupdf.open(str(path))
    except Exception:
        return [_f("block", "cannot_open", "This PDF could not be opened. It may be damaged. Export or print it to a new PDF and attach that.")]
    try:
        if doc.needs_pass:
            return [_f("block", "password", "This PDF needs a password to open. The reviewer cannot read it. Save an unprotected copy and attach that.")]
        if True:  # an owner-password PDF can report is_encrypted False yet still restrict permissions
            perms = doc.permissions
            lacking = []
            if not perms & pymupdf.PDF_PERM_PRINT:
                lacking.append("printing")
            if not perms & pymupdf.PDF_PERM_COPY:
                lacking.append("copying text")
            if lacking:
                out.append(_f("block", "restricted", "This PDF is locked against " + " and ".join(lacking) + ". Reviewers need to print and search it. Save an unrestricted copy and attach that."))
            elif doc.is_encrypted:
                out.append(_f("info", "encrypted_open", "This PDF is encrypted but opens without a password."))
        n = doc.page_count
        if n == 0:
            out.append(_f("block", "zero_pages", "This PDF has no pages."))
            return out
        sample = range(min(n, 40))
        with_text = 0
        seal_hit = False
        sig_field = False
        odd = False
        for i in sample:
            try:
                pg = doc[i]
                txt = pg.get_text("text") or ""
                if len(txt.strip()) >= 25:
                    with_text += 1
                if SEAL_RE.search(txt):
                    seal_hit = True
                w, h = pg.rect.width, pg.rect.height
                if max(w, h) > 2600 or min(w, h) < 150:
                    odd = True
                if not sig_field:
                    for wd in (pg.widgets() or []):
                        if wd.field_type == pymupdf.PDF_WIDGET_TYPE_SIGNATURE:
                            sig_field = True
                            break
            except Exception:
                continue
        if with_text == 0:
            out.append(_f("warn", "no_text", "No readable text found. This looks like a scan or images only, so reviewers cannot search it. Attach a text-based PDF if you can."))
        elif with_text < len(sample) * 0.5:
            out.append(_f("info", "some_no_text", f"Only {with_text} of the first {len(sample)} pages have readable text. Some pages may be scans."))
        if n > BIG_PAGES:
            out.append(_f("warn", "many_pages", f"This PDF has {n} pages. Consider attaching only the pages the reviewer needs."))
        if size > BIG_BYTES:
            out.append(_f("warn", "large_file", f"This file is {size / 1048576:.1f} MB. Large files may be rejected by email. Consider compressing it."))
        if odd:
            out.append(_f("info", "odd_page_size", "Some pages have an unusual size and may print poorly."))
        if professional_required:
            if not sig_field and not seal_hit:
                out.append(_f("warn", "no_seal_text", "We cannot confirm a professional's seal. No signature field or seal wording was found. Your professional must seal this document. This tool cannot check a seal."))
            elif not seal_hit:
                out.append(_f("info", "no_seal_text", "A signature field is present, but no seal wording was found. We cannot confirm a professional's seal. Your professional must seal this document."))
            else:
                out.append(_f("info", "seal_text_present", "Seal-like wording appears in the text. We cannot confirm it is a valid seal or signature; your professional and the reviewer do that."))
    finally:
        doc.close()
    return out


def run_checks(path: Path, filename: str, size: int, doc_name: str = "", professional_required: bool = False) -> list:
    ext = Path(filename).suffix.lower()
    try:
        head = path.read_bytes()[:2048]
    except OSError:
        return [_f("block", "cannot_open", "The saved file could not be read.")]
    out: list = []
    if not _magic_ok(ext, head):
        out.append(_f("block", "type_mismatch", f"The contents do not look like a {ext.lstrip('.').upper()} file, even though the name says so. Re-export the file in that format."))
        return out
    if ext == ".pdf":
        out += check_pdf(path, size, professional_required)
    elif ext in (".png", ".jpg", ".jpeg"):
        out.append(_f("info", "image_file", "Images cannot be searched by reviewers. A PDF is easier to review."))
    elif ext == ".dwg":
        out.append(_f("warn", "dwg_file", "Reviewers may not be able to open DWG files. Also attach a PDF of the drawing."))
    else:
        out.append(_f("info", "office_file", "Office files may display differently on the reviewer's computer. A PDF is safer."))
    if professional_required and ext != ".pdf":
        out.append(_f("warn", "no_seal_text", "We cannot confirm a professional's seal on this file type. Your professional must seal the document; a sealed PDF is usual."))
    out += _name_findings(filename, doc_name)
    return out


def worst(checks: list) -> str:
    lv = {c["level"] for c in checks}
    return "block" if "block" in lv else "warn" if "warn" in lv else "info"


def add_file(app_id: str, doc_id: str, filename: str, data: bytes, doc_name: str = "", professional_required: bool = False) -> dict:
    ext = Path(filename).suffix.lower()
    fid = uuid.uuid4().hex[:10]
    d = app_dir(app_id)
    d.mkdir(parents=True, exist_ok=True)
    stored = f"{safe_id(doc_id)}__{fid}__{safe_name(filename)}"
    p = (d / stored).resolve()
    if d.resolve() not in p.parents:
        raise ValueError("invalid path")
    p.write_bytes(data)
    checks = run_checks(p, filename, len(data), doc_name, professional_required)
    rec = {"id": fid, "doc_id": doc_id, "filename": safe_name(filename), "stored": stored, "size": len(data),
           "sha256": hashlib.sha256(data).hexdigest(), "content_type": ALLOWED.get(ext, "application/octet-stream"),
           "checks": checks, "worst": worst(checks)}
    recs = load_index(app_id)
    recs.append(rec)
    _save_index(app_id, recs)
    return rec


def list_files(app_id: str, doc_id: Optional[str] = None) -> list:
    return [r for r in load_index(app_id) if doc_id is None or r["doc_id"] == doc_id]


def get_file(app_id: str, doc_id: str, fid: str):
    for r in load_index(app_id):
        if r["doc_id"] == doc_id and r["id"] == fid:
            p = (app_dir(app_id) / r["stored"]).resolve()
            if app_dir(app_id).resolve() in p.parents and p.is_file():
                return r, p
    return None, None


def delete_file(app_id: str, doc_id: str, fid: str) -> bool:
    rec, p = get_file(app_id, doc_id, fid)
    if not rec:
        return False
    try:
        p.unlink()
    except OSError:
        pass
    _save_index(app_id, [r for r in load_index(app_id) if r["id"] != fid])
    return True


def package_entries(app_id: str) -> list:
    """[(zip name, path, record)] for the submission package, de-duplicated names."""
    out, used = [], set()
    for r in load_index(app_id):
        rec, p = get_file(app_id, r["doc_id"], r["id"])
        if not rec:
            continue
        name = f"{rec['doc_id']}_{rec['filename']}"
        while name in used:
            name = f"{rec['id']}_{name}"
        used.add(name)
        out.append(("evidence/" + name, str(p), rec))
    return out


def manifest_text(entries: list) -> str:
    L = ["# Evidence manifest", "",
         "Readability checks only. They do not show that a document is correct, compliant or validly sealed.", ""]
    for arc, _p, r in entries:
        L.append(f"- {arc}  (document {r['doc_id']})")
        L.append(f"  - original filename: {r['filename']}")
        L.append(f"  - sha256: {r['sha256']}")
        L.append(f"  - size: {r['size']} bytes")
        for c in r["checks"] or [{"level": "info", "code": "none", "message": "No findings."}]:
            L.append(f"  - [{c['level']}] {c['code']}: {c['message']}")
    return "\n".join(L) + "\n"
