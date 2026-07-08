-- 0009: 1E-b — job-identity playlist coordinate + worker columns/RPCs.
-- jobs is created fresh by 0008 on every `db reset` (empty at this point) → safe re-key.

alter table jobs add column playlist_id uuid not null;
alter table jobs add constraint jobs_playlist_owner_fk
  foreign key (playlist_id, owner_id) references playlists(id, owner_id) on delete cascade;
alter table jobs add column progress_phase text
  check (progress_phase in ('transcribing','summarizing','writing'));

drop index jobs_idem_active;
create unique index jobs_idem_active
  on jobs (owner_id, playlist_id, video_id, section_id, job_kind, job_version)
  where status in ('queued','active','completed');

drop function enqueue_job(text,int,text,text,jsonb);
create function enqueue_job(
  p_playlist_id uuid, p_video_id text, p_section_id int, p_job_kind text, p_job_version text, p_payload jsonb
) returns table(job_id uuid, status text, joined boolean)
  language plpgsql security invoker set search_path = public as $$
declare v_id uuid; v_status text; v_payload jsonb; v_tries int := 0;
begin
  if auth.uid() is null then raise exception 'not authenticated'; end if;
  loop
    v_tries := v_tries + 1;
    if v_tries > 8 then raise exception 'enqueue_job: retry limit exceeded'; end if;
    insert into jobs as j (owner_id, playlist_id, video_id, section_id, job_kind, job_version, payload)
    values (auth.uid(), p_playlist_id, p_video_id, p_section_id, p_job_kind, p_job_version, p_payload)
    on conflict (owner_id, playlist_id, video_id, section_id, job_kind, job_version)
      where j.status in ('queued','active','completed')
      do nothing
    returning id into v_id;
    if v_id is not null then return query select v_id, 'queued'::text, false; return; end if;
    select j.id, j.status, j.payload into v_id, v_status, v_payload from jobs j
      where j.owner_id = auth.uid() and j.playlist_id = p_playlist_id and j.video_id = p_video_id
        and j.section_id = p_section_id and j.job_kind = p_job_kind and j.job_version = p_job_version
        and j.status in ('queued','active','completed')
      limit 1;
    if v_id is not null then
      if v_payload is distinct from p_payload then
        raise log 'enqueue_job: joined % with a divergent payload (kept existing)', v_id; end if;
      return query select v_id, v_status, true; return;
    end if;
  end loop;
end $$;
revoke all on function enqueue_job(uuid,text,int,text,text,jsonb) from public;
grant execute on function enqueue_job(uuid,text,int,text,text,jsonb) to anon, authenticated, service_role;

-- set_progress_phase: lease-fenced advisory phase write (keeps lifecycle writes RPC-only).
create function set_progress_phase(p_job_id uuid, p_worker_id text, p_lease_token uuid, p_phase text)
  returns boolean language plpgsql security invoker set search_path = public as $$
declare v_ok boolean;
begin
  if auth.role() <> 'service_role' then raise exception 'workers only'; end if;
  update jobs set progress_phase = p_phase, updated_at = now()
    where id = p_job_id and locked_by = p_worker_id and lease_token = p_lease_token and status = 'active';
  get diagnostics v_ok = row_count;
  return v_ok > 0;
end $$;
revoke all on function set_progress_phase(uuid,text,uuid,text) from public;
grant execute on function set_progress_phase(uuid,text,uuid,text) to service_role;

-- crash-reclaim now backs off (resolves 1E-a deferred Minor #2), mirroring fail_job.
create or replace function sweep_expired_leases() returns int
  language plpgsql security invoker set search_path = public as $$
declare v_count int;
begin
  if auth.role() <> 'service_role' then raise exception 'workers only'; end if;
  with expired as (select id from jobs where status = 'active' and lease_expires_at < now() for update skip locked)
  update jobs j set
    status = case when j.cancel_requested then 'cancelled'
                  when j.attempts >= j.max_attempts then 'dead_letter' else 'queued' end,
    run_after = case when j.cancel_requested or j.attempts >= j.max_attempts then j.run_after
                     else now() + make_interval(secs => (10 * power(4, least(greatest(j.attempts - 1, 0), 15)))::bigint) end,
    locked_by = null, lease_token = null, lease_expires_at = null, updated_at = now()
  from expired e where j.id = e.id;
  get diagnostics v_count = row_count; return v_count;
end $$;
