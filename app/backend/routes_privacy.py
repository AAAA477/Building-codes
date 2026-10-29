"""Privacy and guardrail endpoints (auto-mounted by main.py).
GET/PUT /api/applications/{id}/ai-setting   {ai_enabled: bool}
GET     /api/privacy/notice
POST    /api/guardrails/check               {text}
Also installs a small ASGI middleware that switches the hosted model off, for the whole request,
when the application in the URL has ai_enabled false (or the client sends header X-AI-Enabled: 0)."""
from __future__ import annotations
import re

from fastapi import APIRouter, Body, HTTPException

import guardrails
import models
import privacy

router = APIRouter()
_APP_PATH = re.compile(r"^/api/applications/([^/]+)")


@router.get("/api/privacy/notice")
def notice():
    return {"notice": privacy.NOTICE}


@router.get("/api/applications/{app_id}/ai-setting")
def get_setting(app_id: str):
    a = models.load(app_id)
    if a is None:
        raise HTTPException(404, f"application {app_id} not found")
    return {"ai_enabled": privacy.is_enabled(a), "notice": privacy.NOTICE}


@router.put("/api/applications/{app_id}/ai-setting")
def set_setting(app_id: str, body: dict = Body(...)):
    a = models.load(app_id)
    if a is None:
        raise HTTPException(404, f"application {app_id} not found")
    if not isinstance((body or {}).get("ai_enabled"), bool):
        raise HTTPException(422, "ai_enabled must be true or false")
    a["ai_enabled"] = body["ai_enabled"]
    models.save(a)
    return {"ai_enabled": a["ai_enabled"], "notice": privacy.NOTICE}


@router.post("/api/guardrails/check")
def guard_check(body: dict = Body(...)):
    r = guardrails.check((body or {}).get("text"))
    return r or {"refused": False}


class PrivacyMiddleware:
    """Pure ASGI (keeps the context variable in the request task)."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        enabled, app_obj = True, None
        for k, v in scope.get("headers") or []:
            if k == b"x-ai-enabled" and v.strip() in (b"0", b"false"):
                enabled = False
        m = _APP_PATH.match(scope.get("path", ""))
        if m:
            try:
                app_obj = models.load(m.group(1))
            except Exception:
                app_obj = None
        with privacy.scope(enabled, app_obj):
            return await self.app(scope, receive, send)


def _install():
    try:
        import main
        if not getattr(main.app, "_privacy_mw", False):
            main.app.add_middleware(PrivacyMiddleware)
            main.app._privacy_mw = True
    except Exception:
        pass


_install()
