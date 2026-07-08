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

create function reserve_video_slot(p_owner_id uuid, p_playlist_id uuid, p_video_id text)
  returns int language plpgsql security invoker set search_path = public as $$
declare v_serial int; v_pos int;
begin
  if not (p_owner_id = auth.uid() or auth.role() = 'service_role') then raise exception 'not authorized'; end if;
  perform 1 from playlists where id = p_playlist_id and owner_id = p_owner_id for update;
  if not found then raise exception 'playlist % not owned by %', p_playlist_id, p_owner_id; end if;
  select (v.data->>'serialNumber')::int into v_serial
    from videos v where v.playlist_id = p_playlist_id and v.video_id = p_video_id;
  if v_serial is not null then return v_serial; end if;
  if exists (select 1 from videos v where v.playlist_id = p_playlist_id and v.video_id = p_video_id) then
    raise exception 'reserve_video_slot: existing video %/% has no serialNumber (invariant)', p_playlist_id, p_video_id;
  end if;
  select coalesce(max(v.position) + 1, 0), coalesce(max((v.data->>'serialNumber')::int) + 1, 1)
    into v_pos, v_serial from videos v where v.playlist_id = p_playlist_id;
  insert into videos (playlist_id, owner_id, video_id, position, data)
    values (p_playlist_id, p_owner_id, p_video_id, v_pos, jsonb_build_object('id', p_video_id, 'serialNumber', v_serial))
    on conflict (playlist_id, video_id) do nothing;
  select (v.data->>'serialNumber')::int into v_serial
    from videos v where v.playlist_id = p_playlist_id and v.video_id = p_video_id;
  return v_serial;
end $$;
revoke all on function reserve_video_slot(uuid,uuid,text) from public;
grant execute on function reserve_video_slot(uuid,uuid,text) to authenticated, service_role;

create function persist_summary(p_owner_id uuid, p_playlist_id uuid, p_video_id text, p_video jsonb, p_artifact_status text)
  returns void language plpgsql security invoker set search_path = public as $$
declare v_count int;
begin
  if not (p_owner_id = auth.uid() or auth.role() = 'service_role') then raise exception 'not authorized'; end if;
  perform 1 from playlists where id = p_playlist_id and owner_id = p_owner_id;
  if not found then raise exception 'playlist % not owned by %', p_playlist_id, p_owner_id; end if;
  -- Whitelist: a summary persist writes ONLY summary-owned fields and preserves EVERYTHING else.
  -- Layering (right wins): (1) p_video defaults — used only for keys the existing row lacks, i.e. a
  -- first-time write off a bare reserve row; (2) the existing row's NON-summary fields win back over
  -- those defaults, so a possibly-stale job payload can never revert operational/membership/metadata/
  -- other-feature state (archived, removedFromPlaylist, playlistIndex, title, timestamps, dig
  -- artifacts, personal notes, …) that a concurrent writer (reconcile_membership / merge_video_data /
  -- upsertVideo) may have changed while this job ran; (3) the top-level summaryMd key resolved from
  -- payload-or-existing; (4) the artifacts.summaryMd merge with a lock-consistent, KEY-SCOPED
  -- monotonic status. The UPDATE's row lock serializes concurrent persists (Task-2 lost-update fix).
  update videos v set
    data = (p_video - 'artifacts')
      || (v.data - 'artifacts'
            - '{language,ratings,overallScore,summaryMd,processedAt,videoType,audience,tags,tldr,takeaways,docVersion}'::text[])
      || jsonb_strip_nulls(jsonb_build_object('summaryMd', coalesce(p_video->>'summaryMd', v.data->>'summaryMd')))
      || jsonb_build_object('artifacts',
           coalesce(v.data->'artifacts', '{}'::jsonb)
           || jsonb_build_object('summaryMd', jsonb_build_object(
                'key', coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key'),
                -- Monotonic status, KEY-SCOPED: preserve 'promoted' against a stale 'committed' write
                -- ONLY when the artifact key is unchanged. A different key is a genuinely new artifact
                -- that IS in committed state, so it must be allowed through (else the row would claim a
                -- promoted artifact for a blob that has not been promoted yet).
                'status', case
                            when v.data->'artifacts'->'summaryMd'->>'status' = 'promoted'
                                 and p_artifact_status = 'committed'
                                 and v.data->'artifacts'->'summaryMd'->>'key'
                                     = coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key')
                              then 'promoted'
                            else p_artifact_status end))),
    updated_at = now()
   where v.playlist_id = p_playlist_id and v.video_id = p_video_id and v.owner_id = p_owner_id;
  get diagnostics v_count = row_count;
  if v_count = 0 then raise exception 'persist_summary: no video row for %/%', p_playlist_id, p_video_id; end if;
end $$;
revoke all on function persist_summary(uuid,uuid,text,jsonb,text) from public;
grant execute on function persist_summary(uuid,uuid,text,jsonb,text) to authenticated, service_role;
