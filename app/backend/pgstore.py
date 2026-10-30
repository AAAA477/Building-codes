"""Supabase Postgres persistence for applications (table `applications`, see supabase/migrations)."""
from __future__ import annotations
import json, os

_pool = None


def enabled() -> bool:
    return bool(os.environ.get("DATABASE_URL"))


def _conn():
    global _pool
    if _pool is None:
        from psycopg_pool import ConnectionPool
        # Supabase pooler (transaction mode) does not support prepared statements
        _pool = ConnectionPool(os.environ["DATABASE_URL"], min_size=1, max_size=5,
                               kwargs={"prepare_threshold": None, "autocommit": True}, open=True)
    return _pool.connection()


def put(app_id: str, app: dict) -> None:
    with _conn() as c:
        c.execute(
            "insert into applications (id, data, updated_at) values (%s, %s::jsonb, now()) "
            "on conflict (id) do update set data = excluded.data, updated_at = now()",
            (app_id, json.dumps(app)))


def get(app_id: str):
    with _conn() as c:
        row = c.execute("select data from applications where id = %s", (app_id,)).fetchone()
    return row[0] if row else None
