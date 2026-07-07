-- supabase/migrations/0008_jobs_queue.sql
create table jobs (
  id            uuid primary key default gen_random_uuid(),
  owner_id      uuid not null references profiles(id) on delete cascade,
  video_id      text not null,
  section_id    int  not null default -1,   -- dig: section start-second; -1 = whole-video (summary)
  job_kind      text not null,              -- 'summary' | 'dig'
  job_version   text not null,              -- target DocVersion 'major.minor'
  status        text not null default 'queued',
  payload       jsonb not null,
  result        jsonb,
  error         text,
  attempts      int  not null default 0,    -- executions started (bumped once at claim)
  max_attempts  int  not null default 5,
  locked_by         text,
  lease_token       uuid,
  lease_expires_at  timestamptz,
  run_after         timestamptz not null default now(),
  cancel_requested  boolean not null default false,
  created_at    timestamptz not null default now(),
  updated_at    timestamptz not null default now(),
  constraint jobs_status_chk check (status in ('queued','active','completed','failed','dead_letter','cancelled')),
  constraint jobs_kind_chk   check (job_kind in ('summary','dig'))
);

alter table jobs enable row level security;
alter table jobs force  row level security;

create unique index jobs_idem_active on jobs (owner_id, video_id, section_id, job_kind, job_version)
  where status in ('queued','active','completed');
create index jobs_claim on jobs (run_after, created_at, id) where status = 'queued';
create index jobs_sweep on jobs (lease_expires_at)          where status = 'active';
create index jobs_owner on jobs (owner_id, created_at);

create policy jobs_owner on jobs for all
  using (owner_id = auth.uid()) with check (owner_id = auth.uid());

-- producers: read + insert only (NEVER direct update/delete — lifecycle is RPC-only)
grant select, insert on public.jobs to anon, authenticated;
grant select, insert, update, delete on public.jobs to service_role;
