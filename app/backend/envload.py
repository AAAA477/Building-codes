"""Tiny .env loader (stdlib only). Real environment variables always win over the file."""
from __future__ import annotations

import os
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parent / ".env"


def load_env(path: Path | str = DEFAULT_PATH) -> list[str]:
    """Load KEY=VALUE lines from `path` into os.environ without overriding existing variables.
    Blank values are skipped, so an empty `ANTHROPIC_API_KEY=` keeps the offline fallback active.
    Returns the names that were set (never the values)."""
    p = Path(path)
    if not p.is_file():
        return []
    loaded = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        if key and val and key not in os.environ:
            os.environ[key] = val
            loaded.append(key)
    return loaded
