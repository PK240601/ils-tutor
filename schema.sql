create table if not exists learners (
  username   text primary key,
  pin_hash   text not null,
  state      jsonb not null default '{}'::jsonb,
  updated_at timestamptz default now()
);
alter table learners enable row level security;
grant select, insert, update on table learners to service_role;