import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pytest
from fastapi.testclient import TestClient

FAKE_KEY = "FAKEKEY1234567890abcdefSECRET"
FAKE_EP = "https://fake-resource-xyz.openai.azure.com/"


@pytest.fixture()
def env(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", FAKE_KEY)
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", FAKE_EP)
    import ratelimit
    ratelimit.LIMITER.reset()
    yield ratelimit
    ratelimit.LIMITER.reset()


@pytest.fixture()
def client(env):
    import main
    return TestClient(main.app)


def test_general_limit_429_retry_after(client, monkeypatch):
    monkeypatch.setenv("RL_GENERAL_PER_MIN", "5")
    codes = [client.get("/api/health").status_code for _ in range(7)]
    assert codes[:5] == [200] * 5 and codes[-1] == 429
    r = client.get("/api/health")
    assert r.status_code == 429 and int(r.headers["retry-after"]) >= 1
    assert "detail" in r.json()


def test_llm_endpoint_limit(client, monkeypatch):
    monkeypatch.setenv("RL_LLM_PER_MIN", "3")
    codes = [client.post("/api/applications/nope/suggest", json={}).status_code for _ in range(5)]
    assert 429 not in codes[:3] and codes[3] == 429 and codes[4] == 429


def test_daily_cap_and_per_app_cap_fall_back_offline(env, monkeypatch):
    monkeypatch.setenv("LLM_DAILY_CALL_CAP", "2")
    ok = [env.llm_gate("x")[0] for _ in range(4)]
    assert ok == [True, True, False, False]
    env.LIMITER.reset()
    monkeypatch.setenv("LLM_DAILY_CALL_CAP", "1000")
    monkeypatch.setenv("LLM_PER_APP_CAP", "2")
    tok = env.current_app_id.set("app-1")
    try:
        assert [env.llm_gate("x")[0] for _ in range(3)] == [True, True, False]
        env.current_app_id.set("app-2")
        assert env.llm_gate("x")[0] is True
    finally:
        env.current_app_id.reset(tok)


def test_azure_ask_falls_back_when_budget_gone(env, monkeypatch):
    import llm
    calls = []

    class FakeClient:
        class chat:
            class completions:
                @staticmethod
                def create(**kw):
                    calls.append(kw)
                    raise AssertionError("must not be called")
    obj = llm.AzureOpenAILLM.__new__(llm.AzureOpenAILLM)
    obj.client, obj.deployment, obj.last_error = FakeClient, "d", ""
    monkeypatch.setenv("LLM_DAILY_CALL_CAP", "0")
    assert obj._ask("hello", "OFFLINE") == "OFFLINE" and not calls


def test_prompt_truncated(env, monkeypatch):
    monkeypatch.setenv("LLM_MAX_PROMPT_CHARS", "100")
    ok, p = env.llm_gate("a" * 5000)
    assert ok and len(p) < 200


def test_scrub_removes_key_and_endpoint(env):
    s = env.scrub(f"Connection error to {FAKE_EP} key={FAKE_KEY} host fake-resource-xyz.openai.azure.com")
    assert FAKE_KEY not in s and "fake-resource-xyz" not in s


def test_no_secret_in_responses(client):
    for path in ("/api/health", "/api/applications/missing", "/api/nonexistent"):
        r = client.get(path)
        blob = r.text + str(dict(r.headers))
        assert FAKE_KEY not in blob and "fake-resource-xyz" not in blob
    assert set(client.get("/api/health").json()) >= {"ok", "llm"}


def test_cors_rejects_unlisted_origin(client):
    bad = client.options("/api/health", headers={"Origin": "http://evil.example",
                                                 "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in bad.headers
    good = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert good.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_security_headers_and_body_cap(client, monkeypatch):
    r = client.get("/api/health")
    assert r.headers["x-content-type-options"] == "nosniff" and r.headers["x-frame-options"] == "DENY"
    monkeypatch.setenv("MAX_BODY_MB", "1")
    big = client.post("/api/search/articles", content=b"x" * (2 * 1024 * 1024),
                      headers={"content-type": "application/json"})
    assert big.status_code == 413


def test_x_forwarded_for_only_when_trusted(client, monkeypatch):
    monkeypatch.setenv("RL_GENERAL_PER_MIN", "2")
    for i in range(4):
        r = client.get("/api/health", headers={"X-Forwarded-For": f"9.9.9.{i}"})
    assert r.status_code == 429          # header ignored: same client IP
    import ratelimit
    ratelimit.LIMITER.reset()
    monkeypatch.setenv("TRUST_PROXY", "1")
    for i in range(4):
        r = client.get("/api/health", headers={"X-Forwarded-For": f"9.9.9.{i}"})
    assert r.status_code == 200
