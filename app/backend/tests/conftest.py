import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pytest

# Suites share one TestClient IP; keep the limiter from tripping unrelated tests.
for _k in ("RL_GENERAL_PER_MIN", "RL_LLM_PER_MIN", "RL_LLM_PER_HOUR", "RL_UPLOAD_PER_MIN", "RL_EXPORT_PER_MIN"):
    os.environ.setdefault(_k, "100000")


@pytest.fixture(autouse=True)
def _reset_limiter():
    import ratelimit
    ratelimit.LIMITER.reset()
    yield
