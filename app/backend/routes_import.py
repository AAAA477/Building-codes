"""Import a variance request the applicant has already started (mounted automatically by main.py).

POST /api/applications/import   multipart field 'file' (PDF) or JSON {"text": "..."}  ->  {id, application, report}
The draft is read without any hosted model. Declarations and signatures are never imported as ticked.
"""
from __future__ import annotations
from email import policy as email_policy
from email.parser import BytesParser

from fastapi import APIRouter, HTTPException, Request

import evidence
import import_draft
import models

router = APIRouter()


async def _read_file(request: Request) -> bytes:
    ct = request.headers.get("content-type", "")
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
    for p in msg.iter_parts() if msg.is_multipart() else []:
        if p.get_param("name", header="content-disposition") == "file":
            buf = p.get_payload(decode=True) or b""
            if not buf:
                raise HTTPException(422, "The file is empty.")
            if len(buf) > evidence.MAX_BYTES:
                raise HTTPException(413, "This file is larger than 25 MB. Compress it or split it.")
            return buf
    raise HTTPException(422, "No file was sent (field name 'file').")


@router.post("/api/applications/import")
async def import_application(request: Request):
    ct = request.headers.get("content-type", "").lower()
    try:
        if ct.startswith("application/json"):
            body = await request.json()
            text = body.get("text") if isinstance(body, dict) else None
            if not isinstance(text, str):
                raise HTTPException(422, "Send {\"text\": \"...\"} or a PDF in a multipart field named 'file'.")
            app, report = import_draft.from_text(text)
        elif ct.startswith("multipart/form-data"):
            app, report = import_draft.from_scc_pdf(await _read_file(request))
        else:
            raise HTTPException(422, "Send {\"text\": \"...\"} or a PDF in a multipart field named 'file'.")
    except import_draft.DraftError as e:
        raise HTTPException(422, str(e))
    app["id"] = models.uuid.uuid4().hex[:8]
    app = models.normalize(app)
    import main
    main.refresh(app)
    models.save(app)
    return {"id": app["id"], "application": app, "report": report}
