"""Abuse protection: in-memory sliding-window rate limits, body-size cap, security headers, secret scrubbing.
Pure python. State is per-process (restart resets it). Configure with env vars (names in .env.example)."""
from __future__ import annotations
import contextvars, json, os, re, threading, time
from collections import defaultdict, deque


def _i(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except ValueError:
        return default


class Limiter:
    """Sliding-window counter. hit() records and returns (allowed, retry_after_seconds)."""

    def __init__(self):
        self._h = defaultdict(deque)
        self._lock = threading.Lock()
        self._gc = 0

    def hit(self, key: str, limit: int, window: float, now=None):
        now = time.time() if now is None else now
        with self._lock:
            q = self._h[key]
            while q and q[0] <= now - window:
                q.popleft()
            if len(q) >= limit:
                return False, (max(1, int(q[0] + window - now) + 1) if q else int(window))
            q.append(now)
            self._gc += 1
            if self._gc > 5000:  # drop idle keys
                self._gc = 0
                for k in [k for k, v in self._h.items() if not v or v[-1] <= now - 90000]:
                    del self._h[k]
            return True, 0

    def reset(self):
        with self._lock:
            self._h.clear()


LIMITER = Limiter()
current_ip: contextvars.ContextVar = contextvars.ContextVar("client_ip", default="-")
current_app_id: contextvars.ContextVar = contextvars.ContextVar("app_id", default="")


# ---------------------------------------------------------------- central LLM budget (called from llm.py)
def llm_gate(prompt: str):
    """Return (allowed, prompt). Counts one LLM call against the global daily budget and the per-application cap.
    When refused the caller must use its offline fallback (never raise). Long prompts are truncated."""
    cap = _i("LLM_MAX_PROMPT_CHARS", 8000)
    if len(prompt) > cap:
        prompt = prompt[: cap // 2] + "\n...[truncated]...\n" + prompt[-(cap // 2):]
    ok, _ = LIMITER.hit("llm:daily", _i("LLM_DAILY_CALL_CAP", 2000), 86400)
    if not ok:
        return False, prompt
    aid = current_app_id.get()
    if aid:
        ok, _ = LIMITER.hit("llm:app:" + aid, _i("LLM_PER_APP_CAP", 60), 86400)
        if not ok:
            return False, prompt
    return True, prompt


# ---------------------------------------------------------------- secret scrubbing
_SECRET_ENV = ("AZURE_OPENAI_API_KEY", "AZURE_OPENAI_ENDPOINT", "ANTHROPIC_API_KEY")


def scrub(text) -> str:
    """Remove configured secret values, key-looking tokens and Azure/Anthropic endpoints from a string."""
    s = str(text)
    for n in _SECRET_ENV:
        v = os.environ.get(n, "")
        if len(v) >= 6:
            s = s.replace(v, "[redacted]")
            host = v.rstrip("/").replace("https://", "").replace("http://", "")
            if host:
                s = s.replace(host, "[redacted]")
    s = re.sub(r"https?://[A-Za-z0-9.\-]*(?:openai\.azure|cognitiveservices\.azure|anthropic)[A-Za-z0-9.\-/_?=&%]*",
               "[redacted-endpoint]", s)
    s = re.sub(r"\b(?:sk-[A-Za-z0-9_\-]{16,}|[A-Fa-f0-9]{32})\b", "[redacted]", s)
    s = re.sub(r"(?i)(api[-_ ]?key|authorization|bearer)\s*[:=]?\s*[A-Za-z0-9_\-\.]{12,}", r"\1=[redacted]", s)
    return s


# ---------------------------------------------------------------- middleware
_LLM_PATH = re.compile(r"^/api/(?:deep-search$|graph/expand$|applications/[^/]+/(?:suggest$|intake/next$|section-c/generate$|deep-search$))")
_APP_PATH = re.compile(r"^/api/applications/([^/]+)")
_UPLOAD = re.compile(r"^/api/.*evidence")
_EXPORT = re.compile(r"/export/|submission-package|/export$")

SECURITY_HEADERS = [
    (b"x-content-type-options", b"nosniff"),
    (b"x-frame-options", b"DENY"),
    (b"referrer-policy", b"no-referrer"),
    (b"cache-control", b"no-store"),
    (b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'"),
]


def allowed_origins() -> list:
    raw = os.environ.get("ALLOWED_ORIGINS", "")
    if raw.strip():
        return [o.strip() for o in raw.split(",") if o.strip()]
    return [f"http://{h}:{p}" for p in (5173, 5174, 5175, 5176, 5177) for h in ("localhost", "127.0.0.1")]


def client_ip(scope) -> str:
    if os.environ.get("TRUST_PROXY") == "1":
        for k, v in scope.get("headers", []):
            if k == b"x-forwarded-for":
                first = v.decode("latin-1").split(",")[0].strip()
                if first:
                    return first
    c = scope.get("client")
    return c[0] if c else "-"


class RateLimitMiddleware:
    def __init__(self, app):
        self.app = app

    async def _send_json(self, send, status, msg, extra=()):
        body = json.dumps({"detail": msg}).encode()
        hdrs = [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode()),
                *extra, *SECURITY_HEADERS]
        await send({"type": "http.response.start", "status": status, "headers": hdrs})
        await send({"type": "http.response.body", "body": body})

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        method, path = scope["method"], scope["path"]
        ip = client_ip(scope)
        current_ip.set(ip)
        m = _APP_PATH.match(path)
        current_app_id.set(m.group(1) if m else "")

        def with_headers(send_):
            async def s(message):
                if message["type"] == "http.response.start":
                    have = {k.lower() for k, _ in message.get("headers", [])}
                    message = dict(message)
                    message["headers"] = list(message.get("headers", [])) + [h for h in SECURITY_HEADERS if h[0] not in have]
                await send_(message)
            return s

        if method == "OPTIONS" or not path.startswith("/api"):
            return await self.app(scope, receive, with_headers(send))

        def deny(retry, what):
            return self._send_json(send, 429, f"Too many requests ({what}). Try again in {retry} seconds.",
                                   [(b"retry-after", str(retry).encode())])

        ok, r = LIMITER.hit(f"gen:{ip}", _i("RL_GENERAL_PER_MIN", 120), 60)
        if not ok:
            return await deny(r, "general limit")
        if method == "POST" and _UPLOAD.match(path):
            ok, r = LIMITER.hit(f"up:{ip}", _i("RL_UPLOAD_PER_MIN", 20), 60)
            if not ok:
                return await deny(r, "upload limit")
        if method in ("GET", "POST") and _EXPORT.search(path):
            ok, r = LIMITER.hit(f"exp:{ip}", _i("RL_EXPORT_PER_MIN", 10), 60)
            if not ok:
                return await deny(r, "export limit")
        if method == "POST" and _LLM_PATH.match(path):
            ok, r = LIMITER.hit(f"llm1m:{ip}", _i("RL_LLM_PER_MIN", 10), 60)
            if ok:
                ok, r = LIMITER.hit(f"llm1h:{ip}", _i("RL_LLM_PER_HOUR", 100), 3600)
            if not ok:
                return await deny(r, "AI request limit")

        max_body = _i("MAX_BODY_MB", 30) * 1024 * 1024
        for k, v in scope.get("headers", []):
            if k == b"content-length":
                try:
                    if int(v) > max_body:
                        return await self._send_json(send, 413, "Request body too large.")
                except ValueError:
                    return await self._send_json(send, 400, "Bad Content-Length.")
        seen = 0
        too_big = False
        started = False

        async def limited_receive():
            nonlocal seen, too_big
            msg = await receive()
            if msg["type"] == "http.request":
                seen += len(msg.get("body", b""))
                if seen > max_body:
                    too_big = True
                    return {"type": "http.request", "body": b"", "more_body": False}
            return msg

        async def guarded_send(message):
            nonlocal started
            if too_big:
                if not started:
                    started = True
                    await self._send_json(send, 413, "Request body too large.")
                return
            started = True
            await with_headers(send)(message)

        await self.app(scope, limited_receive, guarded_send)
