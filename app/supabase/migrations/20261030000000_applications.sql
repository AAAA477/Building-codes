create table if not exists public.applications (
  id text primary key,
  data jsonb not null,
  updated_at timestamptz not null default now()
);
-- Only the backend (direct Postgres connection) touches this table; block the public API.
alter table public.applications enable row level security;
