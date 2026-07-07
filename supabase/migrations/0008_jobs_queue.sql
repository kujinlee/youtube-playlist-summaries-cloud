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

-- enqueue: atomic insert-or-join over live+completed states (table aliased to avoid the
-- output-param `status` colliding with the column — plan review Codex-B2)
create function enqueue_job(
  p_video_id text, p_section_id int, p_job_kind text, p_job_version text, p_payload jsonb
) returns table(job_id uuid, status text, joined boolean)
  language plpgsql security invoker set search_path = public as $$
declare v_id uuid; v_status text; v_payload jsonb;
begin
  if auth.uid() is null then raise exception 'not authenticated'; end if;
  loop
    insert into jobs as j (owner_id, video_id, section_id, job_kind, job_version, payload)
    values (auth.uid(), p_video_id, p_section_id, p_job_kind, p_job_version, p_payload)
    on conflict (owner_id, video_id, section_id, job_kind, job_version)
      where j.status in ('queued','active','completed')
      do nothing
    returning id into v_id;
    if v_id is not null then
      return query select v_id, 'queued'::text, false; return;
    end if;
    select j.id, j.status, j.payload into v_id, v_status, v_payload from jobs j
      where j.owner_id = auth.uid() and j.video_id = p_video_id and j.section_id = p_section_id
        and j.job_kind = p_job_kind and j.job_version = p_job_version
        and j.status in ('queued','active','completed')
      limit 1;
    if v_id is not null then
      if v_payload is distinct from p_payload then
        raise log 'enqueue_job: joined % with a divergent payload (kept existing)', v_id;  -- spec §9.2
      end if;
      return query select v_id, v_status, true; return;
    end if;
    -- conflicting row went terminal (failed/cancelled) in the gap: retry the insert
  end loop;
end $$;
revoke all on function enqueue_job(text,int,text,text,jsonb) from public;
grant execute on function enqueue_job(text,int,text,text,jsonb) to anon, authenticated, service_role;

-- cancel: SECURITY DEFINER because producers have no direct update grant. Explicit owner guard.
create function request_cancel_job(p_job_id uuid) returns void
  language plpgsql security definer set search_path = public as $$
begin
  update jobs
    set cancel_requested = true,
        status = case when status = 'queued' then 'cancelled' else status end,
        updated_at = now()
  where id = p_job_id and owner_id = auth.uid();
  if not found then raise exception 'job not found or not owned'; end if;
end $$;
revoke all on function request_cancel_job(uuid) from public;
grant execute on function request_cancel_job(uuid) to anon, authenticated, service_role;
