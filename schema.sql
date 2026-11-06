-- Run once in Supabase: SQL Editor > New query > paste > Run
create table if not exists learners (
  username   text primary key,
  pin_hash   text not null,
  state      jsonb not null default '{}'::jsonb,
  updated_at timestamptz default now()
);
-- Only the app's server key (service_role) may read/write. No public access.
alter table learners enable row level security;
grant select, insert, update on table learners to service_role;
