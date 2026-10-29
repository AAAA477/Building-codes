"""Evidence upload for Section D items: POST/GET/DELETE under /api/applications/{id}/evidence."""
from __future__ import annotations
from email import policy as email_policy
from email.parser import BytesParser
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

import evidence
import models

router = APIRouter(prefix="/api/applications/{app_id}/evidence", tags=["evidence"])


def _app(app_id: str) -> dict:
    try:
        evidence.safe_id(app_id)
    except ValueError:
        raise HTTPException(404, "application not found")
    a = models.load(app_id)
    if a is None:
        raise HTTPException(404, f"application {app_id} not found")
    return a


def _doc_id(x: str) -> str:
    try:
        return evidence.safe_id(x)
    except ValueError:
        raise HTTPException(422, "invalid document id")


def _public(r: dict) -> dict:
    return {k: v for k, v in r.items() if k != "stored"}


def _refresh(app_id: str) -> None:
    """Recompute completeness so evidence findings show up in the to-do list."""
    try:
        import main
        a = models.load(app_id)
        if a:
            main.refresh(a)
            models.save(a)
    except Exception:
        pass


@router.get("")
def list_all(app_id: str):
    _app(app_id)
    return {"files": [_public(r) for r in evidence.list_files(app_id)]}


@router.get("/{doc_id}")
def list_doc(app_id: str, doc_id: str):
    _app(app_id)
    return {"files": [_public(r) for r in evidence.list_files(app_id, _doc_id(doc_id))]}


@router.post("/{doc_id}")
async def upload(app_id: str, doc_id: str, request: Request):
    a = _app(app_id)
    doc_id = _doc_id(doc_id)
    row = next((d for d in a.get("section_d") or [] if d.get("id") == doc_id), None)
    if row is None:
        raise HTTPException(404, f"Section D item {doc_id} does not exist.")
    # python-multipart is not a dependency, so parse the (size-capped) body with the stdlib.
    ct = request.headers.get("content-type", "")
    if not ct.lower().startswith("multipart/form-data"):
        raise HTTPException(422, "Send the file as multipart form data in a field named 'file'.")
    try:
        if int(request.headers.get("content-length") or 0) > evidence.MAX_BYTES + 65536:
            raise HTTPException(413, "This file is larger than 25 MB. Compress it or split it.")
    except ValueError:
        pass
    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > evidence.MAX_BYTES + 65536:
            raise HTTPException(413, "This file is larger than 25 MB. Compress it or split it.")
    sep = bytes([13, 10, 13, 10])
    msg = BytesParser(policy=email_policy.HTTP).parsebytes(b"Content-Type: " + ct.encode("latin-1") + sep + bytes(body))
    part = None
    for p in msg.iter_parts() if msg.is_multipart() else []:
        if p.get_param("name", header="content-disposition") == "file":
            part = p
            break
    if part is None:
        raise HTTPException(422, "No file was sent (field name 'file').")
    name = evidence.safe_name(part.get_filename() or "")
    ext = Path(name).suffix.lower()
    if ext not in evidence.ALLOWED:
        raise HTTPException(415, "This file type is not accepted. Use PDF, PNG, JPG, DOCX, XLSX or DWG.")
    buf = part.get_payload(decode=True) or b""
    if len(buf) > evidence.MAX_BYTES:
        raise HTTPException(413, "This file is larger than 25 MB. Compress it or split it.")
    if not buf:
        raise HTTPException(422, "The file is empty.")
    rec = evidence.add_file(app_id, doc_id, name, bytes(buf), row.get("document_name") or "", bool(row.get("professional_required")))
    _refresh(app_id)
    return _public(rec)


@router.get("/{doc_id}/{file_id}")
def download(app_id: str, doc_id: str, file_id: str):
    _app(app_id)
    rec, p = evidence.get_file(app_id, _doc_id(doc_id), file_id)
    if not rec:
        raise HTTPException(404, "file not found")
    return FileResponse(str(p), media_type=rec["content_type"], filename=rec["filename"])


@router.delete("/{doc_id}/{file_id}")
def remove(app_id: str, doc_id: str, file_id: str):
    _app(app_id)
    if not evidence.delete_file(app_id, _doc_id(doc_id), file_id):
        raise HTTPException(404, "file not found")
    _refresh(app_id)
    return {"ok": True}
