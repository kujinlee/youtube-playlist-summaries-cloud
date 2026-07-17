Reading additional input from stdin...
OpenAI Codex v0.142.5
--------
workdir: /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
model: gpt-5.5
provider: openai
approval: never
sandbox: workspace-write [workdir, /tmp, $TMPDIR]
reasoning effort: none
reasoning summaries: none
session id: 019f67a7-ffcf-7860-bef0-509b4f317fa3
--------
user
# Adversarial review — Reservation Release Lifecycle spec (money path)

You are an adversarial reviewer. This is a MONEY-PATH design spec: it changes how a global daily spend fuse (`spend_ledger`) reserves and releases budget. A defect here means either (a) a self-DoS (budget leaks, cap locks all users), or (b) real overspend (cap under-counts, lets more real money through than intended). Hunt for BOTH failure directions. Do NOT be agreeable — find what is wrong, missing, or underspecified.

## Read
- The spec: `docs/superpowers/specs/2026-07-15-reservation-release-lifecycle-design.md`
- The actual SQL it modifies (verify the spec's claims against real code — line numbers may have drifted, functions may do more than the spec assumes):
  - `supabase/migrations/0008_jobs_queue.sql` — jobs table, `complete_job`, `fail_job`, `claim_next_job`
  - `supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql` — `sweep_expired_leases`
  - `supabase/migrations/0010_cancel_job_rowcount.sql` — `request_cancel_job`
  - `supabase/migrations/0011_cost_guardrails.sql` — `spend_ledger`, `enqueue_job` (orig), `enqueue_preflight`, `guardrail_config`
  - `supabase/migrations/0018_enqueue_dig.sql` — `enqueue_job` (latest)
  - `supabase/migrations/0012_serve_model_charge.sql` + `0014_serve_owner_budget.sql` — serve reserve path
  - `lib/html-doc/serve-doc.ts` — the serve caller
  - `lib/job-queue/worker-runner.ts` — how handler outcomes map to complete/fail

## Hunt for (report Blocking / High / Medium / Low, each with a concrete failure scenario: inputs → wrong ledger state)
1. **Invariant violations.** Does the release logic actually preserve "reserved_cents = Σ estimates of reservations still in-flight OR converted to kept artifact"? Find any terminal path that releases when it shouldn't (double-spend budget back → overspend) or fails to release when it should (leak persists).
2. **Exactly-once.** Can any job be released twice (e.g., a retryable fail that later dead-letters; a reaper re-queue then a real fail; a lease reclaim racing a worker's own terminal write)? Trace the actual guards in fail_job/sweep_expired_leases/complete_job/claim_next_job. Is the "zero jobs.reserved_cents" idempotency actually written in the same transaction as every release?
3. **The cancel-after-success asymmetry (§5 note).** complete_job sets 'cancelled' when cancel_requested but the handler succeeded → spec says KEEP. fail_job 'cancelled' → RELEASE. Is this distinction actually detectable in the code paths? Can a cancel land in the WRONG function and mis-keep/mis-release?
4. **Day-boundary.** Is `created_at::date at utc` truly the reservation day for every reserve site? Could a job be re-queued across midnight and then reserved/released against mismatched day rows? What about the reaper crediting a job whose created_at day row was already rolled?
5. **Serve path.** Is the `serve_model_charge.reserved_cents` marker actually sufficient for idempotency given the lease reclaim + K-attempt increment logic in reserve_serve_model? Can a reserve+release+reserve sequence within a day corrupt the marker or the per-owner/global counters? Does the serve caller's try/catch actually cover BOTH generateMagazineModel AND the model write, and only release on the 'reserved' branch?
6. **Retry semantics.** Spec claims a retry reuses the one reservation and never re-reserves. Verify against claim_next_job/fail_job — is there ANY path where a retry re-enters enqueue_job or double-reserves?
7. **Concurrency.** Two workers, a worker + the reaper, a serve + a concurrent serve of the same doc — any interleaving that breaks the invariant or double-releases.
8. **Underflow / clamp.** Does `greatest(0, …)` ever MASK a real logic bug (silently swallowing a mis-accounted release) rather than being pure defense?
9. **Missing behaviors / test gaps.** Anything in the 17-row behaviors table that is wrong, or a real scenario with NO row.
10. **Migration mechanics.** create-or-replace preserving grants/ownership/definer attributes; the new serve column default; ordering vs existing migrations.

## Output
Group by severity. For each: the exact spec section or SQL file:line, the concrete failure scenario (inputs → wrong ledger/budget state), and a suggested fix. End with an explicit verdict: CONVERGED (0 Blocking, 0 High — mergeable spec) or a list of must-fix items. Do NOT edit files.
codex
I’ll read the spec and the referenced SQL paths first, then trace terminal state transitions against the ledger invariant. I’ll keep this in review mode only and won’t edit files.
exec
/bin/bash -lc 'nl -ba docs/superpowers/specs/2026-07-15-reservation-release-lifecycle-design.md' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
exec
/bin/bash -lc 'nl -ba supabase/migrations/0008_jobs_queue.sql' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
exec
/bin/bash -lc 'nl -ba supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	-- 0009: 1E-b — job-identity playlist coordinate + worker columns/RPCs.
     2	-- jobs is created fresh by 0008 on every `db reset` (empty at this point) → safe re-key.
     3	
     4	alter table jobs add column playlist_id uuid not null;
     5	alter table jobs add constraint jobs_playlist_owner_fk
     6	  foreign key (playlist_id, owner_id) references playlists(id, owner_id) on delete cascade;
     7	alter table jobs add column progress_phase text
     8	  check (progress_phase in ('transcribing','summarizing','writing'));
     9	
    10	drop index jobs_idem_active;
    11	create unique index jobs_idem_active
    12	  on jobs (owner_id, playlist_id, video_id, section_id, job_kind, job_version)
    13	  where status in ('queued','active','completed');
    14	
    15	drop function enqueue_job(text,int,text,text,jsonb);
    16	create function enqueue_job(
    17	  p_playlist_id uuid, p_video_id text, p_section_id int, p_job_kind text, p_job_version text, p_payload jsonb
    18	) returns table(job_id uuid, status text, joined boolean)
    19	  language plpgsql security invoker set search_path = public as $$
    20	declare v_id uuid; v_status text; v_payload jsonb; v_tries int := 0;
    21	begin
    22	  if auth.uid() is null then raise exception 'not authenticated'; end if;
    23	  loop
    24	    v_tries := v_tries + 1;
    25	    if v_tries > 8 then raise exception 'enqueue_job: retry limit exceeded'; end if;
    26	    insert into jobs as j (owner_id, playlist_id, video_id, section_id, job_kind, job_version, payload)
    27	    values (auth.uid(), p_playlist_id, p_video_id, p_section_id, p_job_kind, p_job_version, p_payload)
    28	    on conflict (owner_id, playlist_id, video_id, section_id, job_kind, job_version)
    29	      where j.status in ('queued','active','completed')
    30	      do nothing
    31	    returning id into v_id;
    32	    if v_id is not null then return query select v_id, 'queued'::text, false; return; end if;
    33	    select j.id, j.status, j.payload into v_id, v_status, v_payload from jobs j
    34	      where j.owner_id = auth.uid() and j.playlist_id = p_playlist_id and j.video_id = p_video_id
    35	        and j.section_id = p_section_id and j.job_kind = p_job_kind and j.job_version = p_job_version
    36	        and j.status in ('queued','active','completed')
    37	      limit 1;
    38	    if v_id is not null then
    39	      if v_payload is distinct from p_payload then
    40	        raise log 'enqueue_job: joined % with a divergent payload (kept existing)', v_id; end if;
    41	      return query select v_id, v_status, true; return;
    42	    end if;
    43	  end loop;
    44	end $$;
    45	revoke all on function enqueue_job(uuid,text,int,text,text,jsonb) from public;
    46	grant execute on function enqueue_job(uuid,text,int,text,text,jsonb) to anon, authenticated, service_role;
    47	
    48	-- set_progress_phase: lease-fenced advisory phase write (keeps lifecycle writes RPC-only).
    49	create function set_progress_phase(p_job_id uuid, p_worker_id text, p_lease_token uuid, p_phase text)
    50	  returns boolean language plpgsql security invoker set search_path = public as $$
    51	declare v_ok boolean;
    52	begin
    53	  if auth.role() <> 'service_role' then raise exception 'workers only'; end if;
    54	  update jobs set progress_phase = p_phase, updated_at = now()
    55	    where id = p_job_id and locked_by = p_worker_id and lease_token = p_lease_token and status = 'active';
    56	  get diagnostics v_ok = row_count;
    57	  return v_ok > 0;
    58	end $$;
    59	revoke all on function set_progress_phase(uuid,text,uuid,text) from public;
    60	grant execute on function set_progress_phase(uuid,text,uuid,text) to service_role;
    61	
    62	-- crash-reclaim now backs off (resolves 1E-a deferred Minor #2), mirroring fail_job.
    63	create or replace function sweep_expired_leases() returns int
    64	  language plpgsql security invoker set search_path = public as $$
    65	declare v_count int;
    66	begin
    67	  if auth.role() <> 'service_role' then raise exception 'workers only'; end if;
    68	  with expired as (select id from jobs where status = 'active' and lease_expires_at < now() for update skip locked)
    69	  update jobs j set
    70	    status = case when j.cancel_requested then 'cancelled'
    71	                  when j.attempts >= j.max_attempts then 'dead_letter' else 'queued' end,
    72	    run_after = case when j.cancel_requested or j.attempts >= j.max_attempts then j.run_after
    73	                     else now() + make_interval(secs => (10 * power(4, least(greatest(j.attempts - 1, 0), 15)))::bigint) end,
    74	    locked_by = null, lease_token = null, lease_expires_at = null, updated_at = now()
    75	  from expired e where j.id = e.id;
    76	  get diagnostics v_count = row_count; return v_count;
    77	end $$;
    78	
    79	create function reserve_video_slot(p_owner_id uuid, p_playlist_id uuid, p_video_id text)
    80	  returns int language plpgsql security invoker set search_path = public as $$
    81	declare v_serial int; v_pos int;
    82	begin
    83	  if not (p_owner_id = auth.uid() or auth.role() = 'service_role') then raise exception 'not authorized'; end if;
    84	  perform 1 from playlists where id = p_playlist_id and owner_id = p_owner_id for update;
    85	  if not found then raise exception 'playlist % not owned by %', p_playlist_id, p_owner_id; end if;
    86	  select (v.data->>'serialNumber')::int into v_serial
    87	    from videos v where v.playlist_id = p_playlist_id and v.video_id = p_video_id;
    88	  if v_serial is not null then return v_serial; end if;
    89	  if exists (select 1 from videos v where v.playlist_id = p_playlist_id and v.video_id = p_video_id) then
    90	    raise exception 'reserve_video_slot: existing video %/% has no serialNumber (invariant)', p_playlist_id, p_video_id;
    91	  end if;
    92	  select coalesce(max(v.position) + 1, 0), coalesce(max((v.data->>'serialNumber')::int) + 1, 1)
    93	    into v_pos, v_serial from videos v where v.playlist_id = p_playlist_id;
    94	  insert into videos (playlist_id, owner_id, video_id, position, data)
    95	    values (p_playlist_id, p_owner_id, p_video_id, v_pos, jsonb_build_object('id', p_video_id, 'serialNumber', v_serial))
    96	    on conflict (playlist_id, video_id) do nothing;
    97	  select (v.data->>'serialNumber')::int into v_serial
    98	    from videos v where v.playlist_id = p_playlist_id and v.video_id = p_video_id;
    99	  return v_serial;
   100	end $$;
   101	revoke all on function reserve_video_slot(uuid,uuid,text) from public;
   102	grant execute on function reserve_video_slot(uuid,uuid,text) to authenticated, service_role;
   103	
   104	create function persist_summary(p_owner_id uuid, p_playlist_id uuid, p_video_id text, p_video jsonb, p_artifact_status text)
   105	  returns void language plpgsql security invoker set search_path = public as $$
   106	declare v_count int;
   107	begin
   108	  if not (p_owner_id = auth.uid() or auth.role() = 'service_role') then raise exception 'not authorized'; end if;
   109	  perform 1 from playlists where id = p_playlist_id and owner_id = p_owner_id;
   110	  if not found then raise exception 'playlist % not owned by %', p_playlist_id, p_owner_id; end if;
   111	  -- Whitelist: a summary persist writes ONLY summary-owned fields and preserves EVERYTHING else.
   112	  -- Layering (right wins): (1) p_video defaults — used only for keys the existing row lacks, i.e. a
   113	  -- first-time write off a bare reserve row; (2) the existing row's NON-summary fields win back over
   114	  -- those defaults, so a possibly-stale job payload can never revert operational/membership/metadata/
   115	  -- other-feature state (archived, removedFromPlaylist, playlistIndex, title, timestamps, dig
   116	  -- artifacts, personal notes, …) that a concurrent writer (reconcile_membership / merge_video_data /
   117	  -- upsertVideo) may have changed while this job ran; (3) the top-level summaryMd key resolved from
   118	  -- payload-or-existing; (4) the artifacts.summaryMd merge with a lock-consistent, KEY-SCOPED
   119	  -- monotonic status. The UPDATE's row lock serializes concurrent persists (Task-2 lost-update fix).
   120	  update videos v set
   121	    data = (p_video - 'artifacts')                            -- (1) payload defaults — fill keys a first-time bare row lacks
   122	      || (v.data - 'artifacts')                               -- (2) ALL existing fields win back: never clobber non-summary
   123	                                                              --     state AND never drop existing summary fields on a
   124	                                                              --     status-only persist (p_video omits them)
   125	      || jsonb_strip_nulls(jsonb_build_object(                -- (3) re-apply ONLY the summary-owned fields p_video PROVIDES
   126	           'language', p_video->'language',                   --     (present ones win; absent → existing preserved by (2))
   127	           'ratings', p_video->'ratings',
   128	           'overallScore', p_video->'overallScore',
   129	           'processedAt', p_video->'processedAt',
   130	           'videoType', p_video->'videoType',
   131	           'audience', p_video->'audience',
   132	           'tags', p_video->'tags',
   133	           'tldr', p_video->'tldr',
   134	           'takeaways', p_video->'takeaways',
   135	           'docVersion', p_video->'docVersion'))
   136	      || jsonb_strip_nulls(jsonb_build_object('summaryMd', coalesce(p_video->>'summaryMd', v.data->>'summaryMd')))
   137	      || jsonb_build_object('artifacts',
   138	           coalesce(v.data->'artifacts', '{}'::jsonb)
   139	           || jsonb_build_object('summaryMd', jsonb_build_object(
   140	                'key', coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key'),
   141	                -- Monotonic status, KEY-SCOPED: preserve 'promoted' against a stale 'committed' write
   142	                -- ONLY when the artifact key is unchanged. A different key is a genuinely new artifact
   143	                -- that IS in committed state, so it must be allowed through (else the row would claim a
   144	                -- promoted artifact for a blob that has not been promoted yet).
   145	                'status', case
   146	                            when v.data->'artifacts'->'summaryMd'->>'status' = 'promoted'
   147	                                 and p_artifact_status = 'committed'
   148	                                 and v.data->'artifacts'->'summaryMd'->>'key'
   149	                                     = coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key')
   150	                              then 'promoted'
   151	                            else p_artifact_status end))),
   152	    updated_at = now()
   153	   where v.playlist_id = p_playlist_id and v.video_id = p_video_id and v.owner_id = p_owner_id;
   154	  get diagnostics v_count = row_count;
   155	  if v_count = 0 then raise exception 'persist_summary: no video row for %/%', p_playlist_id, p_video_id; end if;
   156	end $$;
   157	revoke all on function persist_summary(uuid,uuid,text,jsonb,text) from public;
   158	grant execute on function persist_summary(uuid,uuid,text,jsonb,text) to authenticated, service_role;

 succeeded in 0ms:
     1	-- supabase/migrations/0008_jobs_queue.sql
     2	create table jobs (
     3	  id            uuid primary key default gen_random_uuid(),
     4	  owner_id      uuid not null references profiles(id) on delete cascade,
     5	  video_id      text not null,
     6	  section_id    int  not null default -1,   -- dig: section start-second; -1 = whole-video (summary)
     7	  job_kind      text not null,              -- 'summary' | 'dig'
     8	  job_version   text not null,              -- target DocVersion 'major.minor'
     9	  status        text not null default 'queued',
    10	  payload       jsonb not null,
    11	  result        jsonb,
    12	  error         text,
    13	  attempts      int  not null default 0,    -- executions started (bumped once at claim)
    14	  max_attempts  int  not null default 5,
    15	  locked_by         text,
    16	  lease_token       uuid,
    17	  lease_expires_at  timestamptz,
    18	  run_after         timestamptz not null default now(),
    19	  cancel_requested  boolean not null default false,
    20	  created_at    timestamptz not null default now(),
    21	  updated_at    timestamptz not null default now(),
    22	  constraint jobs_status_chk check (status in ('queued','active','completed','failed','dead_letter','cancelled')),
    23	  constraint jobs_kind_chk   check (job_kind in ('summary','dig'))
    24	);
    25	
    26	alter table jobs enable row level security;
    27	alter table jobs force  row level security;
    28	
    29	create unique index jobs_idem_active on jobs (owner_id, video_id, section_id, job_kind, job_version)
    30	  where status in ('queued','active','completed');
    31	create index jobs_claim on jobs (run_after, created_at, id) where status = 'queued';
    32	create index jobs_sweep on jobs (lease_expires_at)          where status = 'active';
    33	create index jobs_owner on jobs (owner_id, created_at);
    34	
    35	create policy jobs_owner on jobs for all
    36	  using (owner_id = auth.uid()) with check (owner_id = auth.uid());
    37	
    38	-- producers: read + insert only (NEVER direct update/delete — lifecycle is RPC-only)
    39	grant select, insert on public.jobs to anon, authenticated;
    40	grant select, insert, update, delete on public.jobs to service_role;
    41	
    42	-- enqueue: atomic insert-or-join over live+completed states (table aliased to avoid the
    43	-- output-param `status` colliding with the column — plan review Codex-B2)
    44	create function enqueue_job(
    45	  p_video_id text, p_section_id int, p_job_kind text, p_job_version text, p_payload jsonb
    46	) returns table(job_id uuid, status text, joined boolean)
    47	  language plpgsql security invoker set search_path = public as $$
    48	declare v_id uuid; v_status text; v_payload jsonb; v_tries int := 0;
    49	begin
    50	  if auth.uid() is null then raise exception 'not authenticated'; end if;
    51	  loop
    52	    v_tries := v_tries + 1;
    53	    if v_tries > 8 then raise exception 'enqueue_job: retry limit exceeded'; end if;
    54	    insert into jobs as j (owner_id, video_id, section_id, job_kind, job_version, payload)
    55	    values (auth.uid(), p_video_id, p_section_id, p_job_kind, p_job_version, p_payload)
    56	    on conflict (owner_id, video_id, section_id, job_kind, job_version)
    57	      where j.status in ('queued','active','completed')
    58	      do nothing
    59	    returning id into v_id;
    60	    if v_id is not null then
    61	      return query select v_id, 'queued'::text, false; return;
    62	    end if;
    63	    select j.id, j.status, j.payload into v_id, v_status, v_payload from jobs j
    64	      where j.owner_id = auth.uid() and j.video_id = p_video_id and j.section_id = p_section_id
    65	        and j.job_kind = p_job_kind and j.job_version = p_job_version
    66	        and j.status in ('queued','active','completed')
    67	      limit 1;
    68	    if v_id is not null then
    69	      if v_payload is distinct from p_payload then
    70	        raise log 'enqueue_job: joined % with a divergent payload (kept existing)', v_id;  -- spec §9.2
    71	      end if;
    72	      return query select v_id, v_status, true; return;
    73	    end if;
    74	    -- conflicting row went terminal (failed/cancelled) in the gap: retry the insert
    75	  end loop;
    76	end $$;
    77	revoke all on function enqueue_job(text,int,text,text,jsonb) from public;
    78	grant execute on function enqueue_job(text,int,text,text,jsonb) to anon, authenticated, service_role;
    79	
    80	-- cancel: SECURITY DEFINER because producers have no direct update grant. Explicit owner guard.
    81	create function request_cancel_job(p_job_id uuid) returns void
    82	  language plpgsql security definer set search_path = public as $$
    83	begin
    84	  update jobs
    85	    set cancel_requested = true,
    86	        status = case when status = 'queued' then 'cancelled' else status end,
    87	        updated_at = now()
    88	  where id = p_job_id and owner_id = auth.uid();
    89	  if not found then raise exception 'job not found or not owned'; end if;
    90	end $$;
    91	revoke all on function request_cancel_job(uuid) from public;
    92	grant execute on function request_cancel_job(uuid) to anon, authenticated, service_role;
    93	
    94	-- worker RPCs (service_role only): lease fencing on locked_by + lease_token + status='active'
    95	
    96	create function claim_next_job(p_worker_id text, p_lease_seconds int, p_video_id text default null)
    97	  returns setof jobs language plpgsql security invoker set search_path = public as $$
    98	declare v_token uuid := gen_random_uuid();
    99	begin
   100	  if auth.role() <> 'service_role' then raise exception 'workers only'; end if;
   101	  return query
   102	  update jobs set status='active', locked_by=p_worker_id, lease_token=v_token,
   103	         lease_expires_at = now() + make_interval(secs => p_lease_seconds),
   104	         attempts = attempts + 1, updated_at = now()   -- one increment per execution (spec §5)
   105	  where id = (select id from jobs
   106	              where status='queued' and run_after <= now()
   107	                and (p_video_id is null or video_id = p_video_id)   -- test-isolation filter
   108	              order by created_at, id
   109	              for update skip locked limit 1)
   110	  returning *;
   111	end $$;
   112	revoke all on function claim_next_job(text,int,text) from public;
   113	grant execute on function claim_next_job(text,int,text) to service_role;
   114	
   115	create function heartbeat_job(p_job_id uuid, p_worker_id text, p_lease_token uuid, p_lease_seconds int)
   116	  returns boolean language plpgsql security invoker set search_path = public as $$
   117	declare v_rows int;
   118	begin
   119	  if auth.role() <> 'service_role' then raise exception 'workers only'; end if;
   120	  update jobs set lease_expires_at = now() + make_interval(secs => p_lease_seconds), updated_at = now()
   121	  where id = p_job_id and locked_by = p_worker_id and lease_token = p_lease_token and status = 'active';
   122	  get diagnostics v_rows = row_count;
   123	  return v_rows > 0;
   124	end $$;
   125	revoke all on function heartbeat_job(uuid,text,uuid,int) from public;
   126	grant execute on function heartbeat_job(uuid,text,uuid,int) to service_role;
   127	
   128	create function complete_job(p_job_id uuid, p_worker_id text, p_lease_token uuid, p_result jsonb)
   129	  returns boolean language plpgsql security invoker set search_path = public as $$
   130	declare v_rows int;
   131	begin
   132	  if auth.role() <> 'service_role' then raise exception 'workers only'; end if;
   133	  update jobs
   134	    set status = case when cancel_requested then 'cancelled' else 'completed' end,
   135	        result = p_result, locked_by = null, lease_token = null, lease_expires_at = null, updated_at = now()
   136	  where id = p_job_id and locked_by = p_worker_id and lease_token = p_lease_token and status = 'active';
   137	  get diagnostics v_rows = row_count;
   138	  return v_rows > 0;
   139	end $$;
   140	revoke all on function complete_job(uuid,text,uuid,jsonb) from public;
   141	grant execute on function complete_job(uuid,text,uuid,jsonb) to service_role;
   142	
   143	create function fail_job(p_job_id uuid, p_worker_id text, p_lease_token uuid, p_error text, p_retryable boolean)
   144	  returns text language plpgsql security invoker set search_path = public as $$
   145	declare v_attempts int; v_max int; v_cancel boolean; v_new text; v_backoff bigint;
   146	begin
   147	  if auth.role() <> 'service_role' then raise exception 'workers only'; end if;
   148	  select attempts, max_attempts, cancel_requested into v_attempts, v_max, v_cancel from jobs
   149	    where id = p_job_id and locked_by = p_worker_id and lease_token = p_lease_token and status = 'active'
   150	    for update;
   151	  if not found then return null; end if;            -- lost lease
   152	  if v_cancel then v_new := 'cancelled';
   153	  elsif not p_retryable then v_new := 'failed';
   154	  elsif v_attempts >= v_max then v_new := 'dead_letter';
   155	  else v_new := 'queued';
   156	  end if;
   157	  v_backoff := (10 * power(4, least(greatest(v_attempts - 1, 0), 15)))::bigint;   -- 10, 40, 160, ...; exponent capped so the interval stays bigint-safe at high max_attempts
   158	  update jobs set status = v_new, error = p_error,
   159	       run_after = case when v_new = 'queued' then now() + make_interval(secs => v_backoff) else run_after end,
   160	       locked_by = null, lease_token = null, lease_expires_at = null, updated_at = now()
   161	  where id = p_job_id and locked_by = p_worker_id and lease_token = p_lease_token and status = 'active';  -- fence the write (SELECT above already locked/confirmed; belt-and-suspenders)
   162	  return v_new;
   163	end $$;
   164	revoke all on function fail_job(uuid,text,uuid,text,boolean) from public;
   165	grant execute on function fail_job(uuid,text,uuid,text,boolean) to service_role;
   166	
   167	create function sweep_expired_leases() returns int
   168	  language plpgsql security invoker set search_path = public as $$
   169	declare v_count int;
   170	begin
   171	  if auth.role() <> 'service_role' then raise exception 'workers only'; end if;
   172	  with expired as (
   173	    select id from jobs where status = 'active' and lease_expires_at < now()
   174	    for update skip locked
   175	  )
   176	  -- a crash-reclaim requeues with NO backoff (immediately re-claimable) by design —
   177	  -- distinct from fail_job's exponential backoff on an explicit retryable failure
   178	  update jobs j set
   179	    status = case when j.cancel_requested then 'cancelled'
   180	                  when j.attempts >= j.max_attempts then 'dead_letter'
   181	                  else 'queued' end,
   182	    locked_by = null, lease_token = null, lease_expires_at = null, updated_at = now()
   183	  from expired e where j.id = e.id;
   184	  get diagnostics v_count = row_count;
   185	  return v_count;
   186	end $$;
   187	revoke all on function sweep_expired_leases() from public;
   188	grant execute on function sweep_expired_leases() to service_role;

 succeeded in 0ms:
     1	# Reservation Release Lifecycle — Design Spec
     2	
     3	**Date:** 2026-07-15
     4	**Status:** Draft (Phase 1 — pending dual adversarial review + user approval)
     5	**Scope class:** Money path (irreversible spend fuse) → requires **iterative dual adversarial review to convergence** per `docs/dev-process.md`.
     6	**Trigger:** Must land before the Fly.io deploy / before any real traffic.
     7	
     8	---
     9	
    10	## 1. Problem
    11	
    12	`spend_ledger` is a **reserve-only** daily spend fuse. Every generation and serve reserves worst-case cents against a global per-UTC-day cap, but **no code ever releases a reservation** and `actual_cents` is never written. Reservations only clear at UTC-midnight rollover (a fresh ledger row).
    13	
    14	Consequence: a reservation for work that produced **nothing** (a failed/cancelled generation, a serve whose Gemini call threw) permanently consumes the day's budget. With shipped defaults (`daily_cap_cents=500`, `summary_est_cents=150`), ~3 failed generations exhaust the *entire system's* budget until midnight. A Gemini outage or retry burst **self-DoSes all users at ~$0 real spend**. This is the acute blocker for real traffic.
    15	
    16	### Root cause (grounded in code)
    17	- `spend_ledger` (`supabase/migrations/0011_cost_guardrails.sql:12-18`): `day` PK, `reserved_cents`, `actual_cents` (declared but inert — "written by the deferred reconcile"), `updated_at`.
    18	- Reserve sites (increment-only, never released):
    19	  - **Generation:** `enqueue_job` (latest `0018_enqueue_dig.sql:60-64`) reserves `v_est` (= `summary_est_cents`/`dig_est_cents`), then stamps `jobs.reserved_cents` (`0018:67`).
    20	  - **Serve:** `reserve_serve_model` (latest `0014_serve_owner_budget.sql:74-85`) reserves `magazine_est_cents` in **both** `serve_owner_budget.spent_cents` (per-owner, `0014:74-78`) and `spend_ledger.reserved_cents` (global, `0014:81-85`).
    21	- No terminal transition touches the ledger: `complete_job` (`0008_jobs_queue.sql:128-141`), `fail_job` (`0008:143-165`), `sweep_expired_leases` (`0009:63-77`), `request_cancel_job` (`0010_cancel_job_rowcount.sql:7`) — none reference `spend_ledger`.
    22	- `jobs.reserved_cents` (added `0011:40`) is stamped at enqueue and today read only by tests — it is the ready-made hook for a release amount.
    23	- A retry does **not** re-enter `enqueue_job`; the same job row is re-claimed (`claim_next_job`, `0008:96`, bumps `attempts`). One `enqueue_job` = one reservation, regardless of attempts.
    24	
    25	---
    26	
    27	## 2. Decision Summary
    28	
    29	Three decisions taken during brainstorming (all confirmed with the user):
    30	
    31	1. **Accounting depth = release-only.** Credit the reservation back when work terminates without a kept artifact. Do **not** write `actual_cents`; do **not** read Gemini `usageMetadata`. Successful work keeps its worst-case charge. Fail-safe: over-counts real spend, never under-counts.
    32	2. **Scope = generation + serve.** Both reserve sites feed the same global fuse, so both get a release path.
    33	3. **Serve crash residual = accepted.** Handle the common in-request serve failure (Gemini throws → release). A hard process crash after reserve but before the release call leaks `magazine_est_cents` (6¢) until UTC midnight — bounded (≤ `per_owner_serve_daily_cents`=60¢/owner/day), fail-safe, self-heals. No serve-lease-expiry sweep in this slice.
    34	
    35	**Deferred (documented, not built here):** real-cost settle (`actual_cents` via `usageMetadata`); serve-lease-expiry sweep; backfill of already-leaked reservations (a fresh deploy starts clean; local dev can be reset).
    36	
    37	---
    38	
    39	## 3. The Money Invariant
    40	
    41	For each UTC day `d`:
    42	
    43	> `spend_ledger.reserved_cents[d]` = Σ estimates of all reservations made on day `d` that are **still in-flight OR converted to a kept artifact**.
    44	
    45	A reservation is **released** (credited back) **iff** it reaches a terminal state that produced **no kept artifact**. Because `actual_cents` stays 0, the cap predicate `reserved_cents + actual_cents + est ≤ daily_cap_cents` continues to bound real spend — conservatively (each success charged at worst-case `est`), never below true spend.
    46	
    47	**"Kept artifact" rule, by function** (this is the crisp decision boundary):
    48	- `complete_job` → the handler **succeeded** (the summary/dig blob was produced). **Always KEEP** — even when the final status is `cancelled` due to a `cancel_requested` race (the artifact still exists). complete_job never releases.
    49	- `fail_job` → the handler **did not** produce an artifact. **RELEASE** when the terminal status ∈ {`failed`, `dead_letter`, `cancelled`}; **do not release** when it re-`queued`s (reservation reused by the retry).
    50	- `sweep_expired_leases` → **RELEASE** when it gives up (→ `dead_letter`/`cancelled`); **do not release** when it re-`queued`s.
    51	- `request_cancel_job` → a `queued` job that **never ran**; no artifact. **RELEASE**.
    52	- Serve → **RELEASE** on materialization failure; **KEEP** on success (magazine cached).
    53	
    54	---
    55	
    56	## 4. Cross-Cutting Correctness Rules
    57	
    58	These three rules apply to every release site and are the primary review targets.
    59	
    60	1. **Atomic + exactly-once.** Each release executes **inside the same RPC** that performs the terminal state flip, within the same transaction, under the same guard predicate that already guarantees a single terminal write (`where ... and status = 'active'` for `complete_job`/`fail_job`; the `for update skip locked` expired-set for the reaper; the `status = 'queued'` guard for `request_cancel_job`). No new lock or race surface is introduced.
    61	
    62	2. **Idempotent by zeroing the source.** The generation release reads `jobs.reserved_cents`, credits it back, and sets `jobs.reserved_cents = 0` in the **same** statement/transaction. A re-entry (double terminal write attempt) therefore credits 0. Serve release is bounded by a `serve_model_charge.reserved_cents` marker (§6) that can never go negative.
    63	
    64	3. **Day-correct.** The release credits the ledger row for the reservation's **UTC day**, not the terminal day: `spend_ledger where day = (job.created_at at time zone 'utc')::date`. This handles a job enqueued at 23:59 UTC that fails at 00:01 the next day. If that row is absent (should not happen, but defensive), the release is a no-op.
    65	
    66	**Underflow guard.** Every decrement uses `reserved_cents = greatest(0, reserved_cents - amount)` (and likewise for `serve_owner_budget.spent_cents`) so a data inconsistency can never violate the `>= 0` CHECK constraint. With correct idempotency, the clamp should never actually fire — it is defense-in-depth.
    67	
    68	---
    69	
    70	## 5. Generation Path (jobs)
    71	
    72	Fold a release step into the existing terminal RPCs. New migration(s) `create or replace` these functions verbatim except for the added release, preserving signatures/grants/ownership.
    73	
    74	| Terminal transition | Function (migration) | Action |
    75	|---|---|---|
    76	| `completed` (or `cancelled` via cancel-after-success) | `complete_job` (`0008:128-141`) | **KEEP** — no ledger change |
    77	| `failed` / `dead_letter` / `cancelled` | `fail_job` (`0008:143-165`) | **RELEASE** |
    78	| re-`queued` (retryable) | `fail_job` | KEEP (reservation reused) |
    79	| `dead_letter` / `cancelled` via reaper | `sweep_expired_leases` (`0009:63-77`) | **RELEASE** |
    80	| re-`queued` via reaper | `sweep_expired_leases` | KEEP (reservation reused) |
    81	| `cancelled` while `queued` | `request_cancel_job` (`0010:7`) | **RELEASE** |
    82	
    83	**Release operation (generation):** given the job row `j` transitioning to a release-terminal status, in the same transaction:
    84	```sql
    85	update spend_ledger
    86	   set reserved_cents = greatest(0, reserved_cents - j.reserved_cents),
    87	       updated_at = now()
    88	 where day = (j.created_at at time zone 'utc')::date;
    89	-- and, in the same RPC, zero the per-job hook so re-entry is a no-op:
    90	--   j.reserved_cents := 0   (persisted on the jobs row update the RPC already performs)
    91	```
    92	`fail_job` and `sweep_expired_leases` already branch on the computed terminal status (`fail_job` `0008:152-156`); the release is gated on that same branch (only the non-`queued` terminals). `request_cancel_job` releases unconditionally on a successful `queued → cancelled` flip.
    93	
    94	**Note (cancel-after-success):** `complete_job` sets `cancelled` when `cancel_requested` is true (`0008:134`) but the handler had already succeeded — the artifact exists, so complete_job **keeps**. Only `fail_job`'s `cancelled` (handler did not succeed) releases. This asymmetry is intentional and is a required review checkpoint.
    95	
    96	---
    97	
    98	## 6. Serve Path (magazine materialization)
    99	
   100	The serve reserve is a **lease-per-attempt** model (`reserve_serve_model`, `0014:22-95`) deliberately built with "no release RPC" (charge-per-attempt is the abuse bound). We add a scoped release for the common in-request failure.
   101	
   102	**Schema change:** add an unsettled-reservation marker to `serve_model_charge` (`0012:7-15`):
   103	```sql
   104	alter table serve_model_charge
   105	  add column reserved_cents int not null default 0 check (reserved_cents >= 0);
   106	```
   107	- `reserve_serve_model` (the `'reserved'` branch, `0014:87`) additionally does `reserved_cents = reserved_cents + magazine_est_cents` on the `serve_model_charge` row.
   108	- New RPC **`release_serve_model(p_playlist_id uuid, p_video_id text)`** (SECURITY DEFINER, `auth.uid()`-derived owner, mirroring `reserve_serve_model`'s definer/search_path attributes verbatim; grants: `authenticated, anon`). It credits back **one** `magazine_est_cents` bounded by the marker:
   109	```sql
   110	-- only if there is an unsettled reservation to release (idempotent, can't over-release)
   111	update serve_model_charge
   112	   set reserved_cents = reserved_cents - v_cfg.magazine_est_cents
   113	 where owner_id = v_owner and doc_key = v_doc_key and day = v_day
   114	   and reserved_cents >= v_cfg.magazine_est_cents;
   115	if found then
   116	  update serve_owner_budget
   117	     set spent_cents = greatest(0, spent_cents - v_cfg.magazine_est_cents)
   118	   where owner_id = v_owner and day = v_day;
   119	  update spend_ledger
   120	     set reserved_cents = greatest(0, reserved_cents - v_cfg.magazine_est_cents),
   121	         updated_at = now()
   122	   where day = v_day;
   123	end if;
   124	```
   125	- `attempt_count` (the K-day bound) is **NOT** credited back — a failed materialization still burns an attempt, so release can never become an infinite retry loop.
   126	- **Reservation day for serve:** the serve reserve and release both happen in the same request within seconds, so `v_day = (now() at utc)::date` is correct for both. (A serve that spans midnight is out of scope; the marker simply won't match on the next day and release becomes a no-op — safe.)
   127	
   128	**Caller change (`lib/html-doc/serve-doc.ts`):** wrap the post-reserve materialization (`generateMagazineModel` at `serve-doc.ts:81` + the model write) in `try/catch`. On the `'reserved'` branch, if materialization or the write throws → call `release_serve_model(...)` then re-throw. On success → no release (keep). The `'in_flight'`/`'at_capacity'`/`'denied'` branches never reserved, so they never release.
   129	
   130	---
   131	
   132	## 7. Enumerated Behaviors (test contract)
   133	
   134	| # | Behavior | Trigger | Expected |
   135	|---|---|---|---|
   136	| 1 | Success keeps charge | Job handler returns; `complete_job` → `completed` | `spend_ledger.reserved_cents` unchanged; `jobs.reserved_cents` unchanged |
   137	| 2 | Non-retryable fail releases | Handler throws `NonRetryableError`; `fail_job` → `failed` | ledger `reserved_cents -= est` on reserve-day row; `jobs.reserved_cents → 0` |
   138	| 3 | Dead-letter releases | Retryable fail, `attempts ≥ max`; `fail_job` → `dead_letter` | ledger released; `jobs.reserved_cents → 0` |
   139	| 4 | Cancel-mid-run releases | `cancel_requested` + handler throws; `fail_job` → `cancelled` | ledger released |
   140	| 5 | Retry reuses one reservation | Retryable fail, `attempts < max`; `fail_job` → `queued` | **no** release; `jobs.reserved_cents` unchanged; next attempt does not re-reserve |
   141	| 6 | Reaper re-queue keeps | Lease expires, `attempts < max`; `sweep` → `queued` | **no** release |
   142	| 7 | Reaper give-up releases | Lease expires, `attempts ≥ max`; `sweep` → `dead_letter`/`cancelled` | ledger released |
   143	| 8 | Cancel queued releases | `request_cancel_job` on a `queued` job | ledger released; `jobs.reserved_cents → 0` |
   144	| 9 | Cancel-after-success keeps | `cancel_requested` but handler already succeeded; `complete_job` → `cancelled` | **no** release (artifact exists) |
   145	| 10 | Midnight-span day-correct | Job `created_at` day X, fails day Y | release credits day **X** ledger row, not day Y |
   146	| 11 | Double-terminal idempotent | Two terminal-write attempts for one job | second credits 0 (`jobs.reserved_cents` already 0) |
   147	| 12 | Cap re-opens after release | Reserve to cap, then a failure releases | subsequent `enqueue_job`/`enqueue_preflight` admits again |
   148	| 13 | Serve fail releases both | `generateMagazineModel` throws; catch → `release_serve_model` | `spend_ledger.reserved_cents` and `serve_owner_budget.spent_cents` each `-= 6`; `serve_model_charge.reserved_cents -= 6`; `attempt_count` unchanged |
   149	| 14 | Serve success keeps | Materialization + write succeed | no release |
   150	| 15 | Serve release idempotent | `release_serve_model` called twice for one reservation | second is a no-op (marker `< magazine_est_cents`) |
   151	| 16 | K-bound survives releases | K failed serves, each released | `attempt_count` reaches `max_serve_attempts` → `'attempts_exhausted'`; no infinite retry |
   152	| 17 | Serve crash residual (accepted) | Process dies after reserve, before catch | 6¢ remains reserved until midnight; documented, not a test failure |
   153	
   154	---
   155	
   156	## 8. Edge Cases
   157	
   158	- **Underflow:** all decrements clamped `greatest(0, …)`; correct idempotency means the clamp is never load-bearing.
   159	- **Missing ledger/budget row on release:** defensive no-op (the `where day = …` matches nothing). Cannot happen on the normal path (reserve created the row).
   160	- **Concurrency:** release lives inside the terminal RPC's existing single-writer guard; two workers cannot both terminal-write the same job (`where status='active'` + lease token). The reaper and a live worker cannot both release (the reaper only touches `status='active' and lease_expires_at < now()`, and flips status atomically).
   161	- **Serve double-fire:** the marker column makes `release_serve_model` self-bounding; a retry within the same day that reserved again would set the marker back up, and each release consumes exactly one `magazine_est_cents`.
   162	
   163	---
   164	
   165	## 9. Testing Strategy
   166	
   167	**Against real PostgREST + Postgres** — not mocks. (BUG-1 lesson: a mocked money test missed a real PostgREST param-drop that dead-lettered every job.) Integration tests exercise the real RPCs and assert exact ledger/budget/job-column deltas for behaviors 1–16; behavior 17 is asserted as documented-residual (reserve without release leaves the marker set). Include a concurrency test: two claimants race a terminal write → exactly one release. Include the midnight-span test (behavior 10) by inserting a job with a back-dated `created_at`.
   168	
   169	---
   170	
   171	## 10. Out of Scope / Deferred
   172	
   173	- **Real-cost settle (`actual_cents`).** Read `usageMetadata` at each `lib/gemini.ts` `generateContent` site, accumulate across a job's passes, price with the existing `lib/gemini-cost.ts` constants, and write `actual_cents` in an atomic settle. Efficiency win (~3–5× throughput per cap); safe-on-crash (falls back to the kept reservation). Its own slice, when the cap constrains real traffic.
   174	- **Serve-lease-expiry sweep.** Would close the accepted serve crash residual. Deferred (bounded, self-healing).
   175	- **Backfill.** Existing leaked reservations are not reconciled by this slice. A fresh deploy starts with an empty ledger; local dev resets today's row manually (already done this session).
   176	
   177	---
   178	
   179	## 11. Review Requirements
   180	
   181	Money path + concurrency + idempotency → **iterative dual adversarial review to convergence** (Codex + Claude, independent), re-reviewing the *revised* SQL each round until a round returns no new Blocking/High. Explicit review targets: the cancel-after-success asymmetry (§5 note), day-correctness (§4.3), exactly-once under concurrent workers/reaper (§4.1), serve marker idempotency (§6), and the underflow clamp never masking a real logic error.

codex
The first pass already shows the spec is mostly describing intended future migrations, not current implementation. I’m now checking the latest overriding migrations and caller code, because the highest-risk bugs here will be in function replacement ordering and in paths the spec assumes are single-purpose.
exec
/bin/bash -lc 'nl -ba supabase/migrations/0018_enqueue_dig.sql' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	-- 0018_enqueue_dig.sql
     2	-- Admit job_kind='dig' in enqueue_job. The dig quota (quota_allowance dig rows),
     3	-- dig_est_cents, and dig_max_attempts config, plus the section_id/job_kind/job_version
     4	-- idempotency index (jobs_idem_active), already exist (0008 + 0011). This migration only
     5	-- relaxes the one-line kind guard; the est/attempts dispatch (case p_job_kind ... 'dig' ...)
     6	-- is already present in the 0011 body and is preserved verbatim.
     7	create or replace function enqueue_job(
     8	  p_owner_id uuid, p_playlist_id uuid, p_video_id text, p_section_id int,
     9	  p_job_kind text, p_job_version text, p_payload jsonb, p_enqueue_ip inet
    10	) returns table(job_id uuid, status text, joined boolean)
    11	  language plpgsql security invoker set search_path = public as $$
    12	declare
    13	  v_id uuid; v_status text; v_payload jsonb; v_cfg guardrail_config;
    14	  v_est int; v_maxatt int; v_dur text; v_anon boolean; v_allow int;
    15	  v_period date; v_day date; v_tries int := 0;
    16	begin
    17	  -- 0. Auth + kind gate. Primary defense is the grant (service_role only); this is belt-and-suspenders.
    18	  if auth.role() <> 'service_role' then raise exception 'enqueue_job: server only'; end if;
    19	  if p_owner_id is null then raise exception 'owner required'; end if;
    20	  if p_job_kind not in ('summary','dig') then raise exception 'unsupported_job_kind'; end if;
    21	
    22	  select * into v_cfg from guardrail_config where id = true;                          -- singleton, once
    23	  v_est    := case p_job_kind when 'summary' then v_cfg.summary_est_cents    else v_cfg.dig_est_cents    end;
    24	  v_maxatt := case p_job_kind when 'summary' then v_cfg.summary_max_attempts else v_cfg.dig_max_attempts end;
    25	
    26	  loop
    27	    v_tries := v_tries + 1;
    28	    if v_tries > 8 then raise exception 'enqueue_job: retry limit exceeded'; end if;
    29	
    30	    -- 1. INSERT-or-JOIN. Aliased ON CONFLICT predicate MUST textually match jobs_idem_active
    31	    --    (0008/0009) so Postgres binds the partial unique index as the arbiter.
    32	    insert into jobs as j (owner_id, playlist_id, video_id, section_id, job_kind, job_version, payload, enqueue_ip, max_attempts)
    33	    values (p_owner_id, p_playlist_id, p_video_id, p_section_id, p_job_kind, p_job_version, p_payload, p_enqueue_ip, v_maxatt)
    34	    on conflict (owner_id, playlist_id, video_id, section_id, job_kind, job_version)
    35	      where j.status in ('queued','active','completed')
    36	      do nothing
    37	    returning id into v_id;
    38	
    39	    if v_id is not null then
    40	      -- NEW ROW → run the guardrails; any raise below rolls back this INSERT.
    41	      -- 2. Duration backstop (robust cast; reject-not-admit for missing/malformed/over-cap).
    42	      v_dur := (p_payload->>'durationSeconds');
    43	      if v_dur is null or v_dur !~ '^[0-9]{1,7}(\.[0-9]{1,6})?$'   -- missing/non-numeric/over-long ⇒ reject (length-bounded so ::numeric can't blow up)
    44	         or v_dur::numeric > v_cfg.max_duration_seconds            -- NUMERIC compare, no ::int / no floor: 1800.999999 > 1800 ⇒ PJ003
    45	      then
    46	        raise exception 'too_long' using errcode = 'PJ003';
    47	      end if;
    48	
    49	      -- 3. Atomic quota debit (per-owner, per-kind, per-UTC-month).
    50	      select p.is_anonymous into v_anon from profiles p where p.id = p_owner_id;
    51	      select qa.monthly into v_allow from quota_allowance qa where qa.is_anonymous = v_anon and qa.kind = p_job_kind;
    52	      v_period := date_trunc('month', now() at time zone 'utc')::date;
    53	      v_day    := (now() at time zone 'utc')::date;
    54	      insert into usage_counters (owner_id, kind, period_start, used)
    55	        values (p_owner_id, p_job_kind, v_period, 0) on conflict do nothing;
    56	      update usage_counters set used = used + 1
    57	        where owner_id = p_owner_id and kind = p_job_kind and period_start = v_period and used < v_allow;
    58	      if not found then raise exception 'quota_exceeded' using errcode = 'PJ001'; end if;
    59	
    60	      -- 4. Atomic daily reserve against the global cap (never released in 1D).
    61	      insert into spend_ledger (day) values (v_day) on conflict do nothing;
    62	      update spend_ledger set reserved_cents = reserved_cents + v_est, updated_at = now()
    63	        where day = v_day and reserved_cents + actual_cents + v_est <= v_cfg.daily_cap_cents;
    64	      if not found then raise exception 'daily_cap_exceeded' using errcode = 'PJ002'; end if;
    65	
    66	      -- 5. Stamp the reservation on the row and return.
    67	      update jobs set reserved_cents = v_est where id = v_id;
    68	      return query select v_id, 'queued'::text, false; return;
    69	    end if;
    70	
    71	    -- CONFLICT → JOIN the existing live/completed row: NO debit, NO reserve, NO duration check.
    72	    select j.id, j.status, j.payload into v_id, v_status, v_payload from jobs j
    73	      where j.owner_id = p_owner_id and j.playlist_id = p_playlist_id and j.video_id = p_video_id
    74	        and j.section_id = p_section_id and j.job_kind = p_job_kind and j.job_version = p_job_version
    75	        and j.status in ('queued','active','completed')
    76	      limit 1;
    77	    if v_id is not null then
    78	      if v_payload is distinct from p_payload then
    79	        raise log 'enqueue_job: joined % with a divergent payload (kept existing)', v_id;
    80	      end if;
    81	      return query select v_id, v_status, true; return;
    82	    end if;
    83	    -- conflicting row went terminal (failed/cancelled) in the gap: retry the insert
    84	  end loop;
    85	end $$;
    86	revoke all on function enqueue_job(uuid,uuid,text,int,text,text,jsonb,inet) from public, anon, authenticated;
    87	grant execute on function enqueue_job(uuid,uuid,text,int,text,text,jsonb,inet) to service_role;

exec
/bin/bash -lc 'nl -ba supabase/migrations/0011_cost_guardrails.sql' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	create table usage_counters (
     2	  owner_id uuid not null references profiles(id) on delete cascade,
     3	  kind text not null check (kind in ('summary','dig')),
     4	  period_start date not null,                     -- date_trunc('month', now() at time zone 'utc')::date
     5	  used int not null default 0 check (used >= 0),
     6	  primary key (owner_id, kind, period_start));
     7	alter table usage_counters enable row level security; alter table usage_counters force row level security;
     8	create policy usage_counters_owner_read on usage_counters for select using (owner_id = auth.uid());
     9	grant select on usage_counters to anon, authenticated;              -- read own "remaining"; NO client write
    10	grant select, insert, update, delete on usage_counters to service_role;
    11	
    12	create table spend_ledger (                                          -- global, one row per UTC day
    13	  day date primary key,
    14	  reserved_cents int not null default 0 check (reserved_cents >= 0),
    15	  actual_cents   int not null default 0 check (actual_cents   >= 0), -- inert in 1D; written by the deferred reconcile
    16	  updated_at timestamptz not null default now());
    17	alter table spend_ledger enable row level security; alter table spend_ledger force row level security;
    18	grant select, insert, update, delete on spend_ledger to service_role;   -- no client access (global infra)
    19	
    20	create table quota_allowance (is_anonymous boolean not null, kind text not null check (kind in ('summary','dig')),
    21	  monthly int not null check (monthly >= 0), primary key (is_anonymous, kind));
    22	insert into quota_allowance values (false,'summary',20),(false,'dig',5),(true,'summary',2),(true,'dig',0);
    23	alter table quota_allowance enable row level security; alter table quota_allowance force row level security;
    24	create policy quota_allowance_read on quota_allowance for select using (true);   -- allowances are not secret → UI shows "X of N" (Claude-L3)
    25	grant select on quota_allowance to anon, authenticated; grant select, insert, update, delete on quota_allowance to service_role;
    26	
    27	create table guardrail_config (id boolean primary key default true check (id),   -- singleton
    28	  daily_cap_cents int not null default 500 check (daily_cap_cents >= 0),            -- $5.00
    29	  summary_est_cents int not null default 150 check (summary_est_cents >= 1),        -- WORST-CASE one-run upper bound from ENFORCED token caps incl audio pricing (see below)
    30	  dig_est_cents int not null default 150 check (dig_est_cents >= 1),
    31	  summary_max_attempts int not null default 1 check (summary_max_attempts >= 1),    -- billable executions/row; enqueue_job sets jobs.max_attempts. ≥1: else the guard test (est≥worst×attempts) is tautological at 0 while claim_next_job still bills once (round-4 H2)
    32	  dig_max_attempts int not null default 1 check (dig_max_attempts >= 1),
    33	  max_duration_seconds int not null default 1800 check (max_duration_seconds >= 1),  -- 30 min hosted cap
    34	  max_free_users int not null default 100, max_queue_depth int not null default 200,
    35	  velocity_per_ip_hourly int not null default 15, captcha_soft_threshold int not null default 5);
    36	insert into guardrail_config default values;
    37	alter table guardrail_config enable row level security; alter table guardrail_config force row level security;
    38	grant select, insert, update, delete on guardrail_config to service_role;   -- no client access
    39	
    40	alter table jobs add column reserved_cents int not null default 0;   -- charged spend (never released in 1D)
    41	alter table jobs add column enqueue_ip inet;                         -- server-provided (trusted); per-IP velocity
    42	
    43	create index jobs_velocity on jobs (enqueue_ip, created_at);
    44	
    45	-- ============================================================================
    46	-- enqueue_job rework — server-mediated, atomic money kill-switch (spec §4).
    47	-- Drops the client-callable 0009 6-arg fn (removes its anon/authenticated grants)
    48	-- and replaces it with an 8-arg service_role-only RPC that adds trusted p_owner_id
    49	-- + p_enqueue_ip and folds in the atomic quota debit / daily reserve / duration
    50	-- backstop. Every `auth.uid()` becomes `p_owner_id` (under service_role auth.uid()
    51	-- is NULL — a leftover would break the idempotency JOIN → double-billing).
    52	-- ============================================================================
    53	
    54	drop function if exists enqueue_job(uuid,text,int,text,text,jsonb);   -- the LIVE 0009 6-arg signature
    55	
    56	revoke insert on public.jobs from anon, authenticated;                -- clients keep SELECT; no direct job creation
    57	
    58	create function enqueue_job(
    59	  p_owner_id uuid, p_playlist_id uuid, p_video_id text, p_section_id int,
    60	  p_job_kind text, p_job_version text, p_payload jsonb, p_enqueue_ip inet
    61	) returns table(job_id uuid, status text, joined boolean)
    62	  language plpgsql security invoker set search_path = public as $$
    63	declare
    64	  v_id uuid; v_status text; v_payload jsonb; v_cfg guardrail_config;
    65	  v_est int; v_maxatt int; v_dur text; v_anon boolean; v_allow int;
    66	  v_period date; v_day date; v_tries int := 0;
    67	begin
    68	  -- 0. Auth + kind gate. Primary defense is the grant (service_role only); this is belt-and-suspenders.
    69	  if auth.role() <> 'service_role' then raise exception 'enqueue_job: server only'; end if;
    70	  if p_owner_id is null then raise exception 'owner required'; end if;
    71	  if p_job_kind <> 'summary' then raise exception 'unsupported_job_kind'; end if;   -- dig rejected until 1E-b-2
    72	
    73	  select * into v_cfg from guardrail_config where id = true;                          -- singleton, once
    74	  v_est    := case p_job_kind when 'summary' then v_cfg.summary_est_cents    else v_cfg.dig_est_cents    end;
    75	  v_maxatt := case p_job_kind when 'summary' then v_cfg.summary_max_attempts else v_cfg.dig_max_attempts end;
    76	
    77	  loop
    78	    v_tries := v_tries + 1;
    79	    if v_tries > 8 then raise exception 'enqueue_job: retry limit exceeded'; end if;
    80	
    81	    -- 1. INSERT-or-JOIN. Aliased ON CONFLICT predicate MUST textually match jobs_idem_active
    82	    --    (0008/0009) so Postgres binds the partial unique index as the arbiter.
    83	    insert into jobs as j (owner_id, playlist_id, video_id, section_id, job_kind, job_version, payload, enqueue_ip, max_attempts)
    84	    values (p_owner_id, p_playlist_id, p_video_id, p_section_id, p_job_kind, p_job_version, p_payload, p_enqueue_ip, v_maxatt)
    85	    on conflict (owner_id, playlist_id, video_id, section_id, job_kind, job_version)
    86	      where j.status in ('queued','active','completed')
    87	      do nothing
    88	    returning id into v_id;
    89	
    90	    if v_id is not null then
    91	      -- NEW ROW → run the guardrails; any raise below rolls back this INSERT.
    92	      -- 2. Duration backstop (robust cast; reject-not-admit for missing/malformed/over-cap).
    93	      v_dur := (p_payload->>'durationSeconds');
    94	      if v_dur is null or v_dur !~ '^[0-9]{1,7}(\.[0-9]{1,6})?$'   -- missing/non-numeric/over-long ⇒ reject (length-bounded so ::numeric can't blow up)
    95	         or v_dur::numeric > v_cfg.max_duration_seconds            -- NUMERIC compare, no ::int / no floor: 1800.999999 > 1800 ⇒ PJ003
    96	      then
    97	        raise exception 'too_long' using errcode = 'PJ003';
    98	      end if;
    99	
   100	      -- 3. Atomic quota debit (per-owner, per-kind, per-UTC-month).
   101	      select p.is_anonymous into v_anon from profiles p where p.id = p_owner_id;
   102	      select qa.monthly into v_allow from quota_allowance qa where qa.is_anonymous = v_anon and qa.kind = p_job_kind;
   103	      v_period := date_trunc('month', now() at time zone 'utc')::date;
   104	      v_day    := (now() at time zone 'utc')::date;
   105	      insert into usage_counters (owner_id, kind, period_start, used)
   106	        values (p_owner_id, p_job_kind, v_period, 0) on conflict do nothing;
   107	      update usage_counters set used = used + 1
   108	        where owner_id = p_owner_id and kind = p_job_kind and period_start = v_period and used < v_allow;
   109	      if not found then raise exception 'quota_exceeded' using errcode = 'PJ001'; end if;
   110	
   111	      -- 4. Atomic daily reserve against the global cap (never released in 1D).
   112	      insert into spend_ledger (day) values (v_day) on conflict do nothing;
   113	      update spend_ledger set reserved_cents = reserved_cents + v_est, updated_at = now()
   114	        where day = v_day and reserved_cents + actual_cents + v_est <= v_cfg.daily_cap_cents;
   115	      if not found then raise exception 'daily_cap_exceeded' using errcode = 'PJ002'; end if;
   116	
   117	      -- 5. Stamp the reservation on the row and return.
   118	      update jobs set reserved_cents = v_est where id = v_id;
   119	      return query select v_id, 'queued'::text, false; return;
   120	    end if;
   121	
   122	    -- CONFLICT → JOIN the existing live/completed row: NO debit, NO reserve, NO duration check.
   123	    select j.id, j.status, j.payload into v_id, v_status, v_payload from jobs j
   124	      where j.owner_id = p_owner_id and j.playlist_id = p_playlist_id and j.video_id = p_video_id
   125	        and j.section_id = p_section_id and j.job_kind = p_job_kind and j.job_version = p_job_version
   126	        and j.status in ('queued','active','completed')
   127	      limit 1;
   128	    if v_id is not null then
   129	      if v_payload is distinct from p_payload then
   130	        raise log 'enqueue_job: joined % with a divergent payload (kept existing)', v_id;
   131	      end if;
   132	      return query select v_id, v_status, true; return;
   133	    end if;
   134	    -- conflicting row went terminal (failed/cancelled) in the gap: retry the insert
   135	  end loop;
   136	end $$;
   137	revoke all on function enqueue_job(uuid,uuid,text,int,text,text,jsonb,inet) from public, anon, authenticated;
   138	grant execute on function enqueue_job(uuid,uuid,text,int,text,text,jsonb,inet) to service_role;
   139	
   140	-- ============================================================================
   141	-- enqueue_preflight — ADVISORY, service_role-only gate (spec §5). Four
   142	-- booleans, no cross-tenant data. Coarse and non-atomic (round-3 M3-4): the
   143	-- real race-free bounds are the atomic quota debit + daily-cap reserve inside
   144	-- enqueue_job; this gate is abuse-hardening only (velocity/ceiling/queue-depth).
   145	-- ============================================================================
   146	
   147	create function enqueue_preflight(p_ip inet, p_owner_id uuid)
   148	  returns table(admitted boolean, at_capacity boolean, velocity_exceeded boolean, challenge_required boolean)
   149	  language plpgsql security invoker set search_path = public as $$
   150	declare
   151	  v_cfg guardrail_config;
   152	  v_anon boolean; v_owner_created timestamptz;
   153	  v_rank bigint; v_ip_hour_count bigint;
   154	  v_day date; v_ledger_spent int; v_queue_depth bigint;
   155	begin
   156	  if auth.role() <> 'service_role' then raise exception 'enqueue_preflight: server only'; end if;
   157	  if p_owner_id is null then raise exception 'owner required'; end if;
   158	
   159	  select * into v_cfg from guardrail_config where id = true;                 -- singleton, once
   160	
   161	  select p.is_anonymous, p.created_at into v_anon, v_owner_created from profiles p where p.id = p_owner_id;
   162	  if v_anon is null then raise exception 'unknown owner'; end if;
   163	
   164	  -- Per-IP hourly job count (uses the jobs_velocity index: enqueue_ip, created_at).
   165	  select count(*) into v_ip_hour_count from jobs
   166	    where enqueue_ip = p_ip and created_at > now() - interval '1 hour';
   167	
   168	  velocity_exceeded   := v_ip_hour_count >= v_cfg.velocity_per_ip_hourly;
   169	  challenge_required  := v_anon and v_ip_hour_count > v_cfg.captcha_soft_threshold;
   170	
   171	  -- Registered-rank free-user ceiling (round-2 H3): the max_free_users ceiling
   172	  -- applies ONLY to registered (non-anonymous) profiles, ranked by created_at
   173	  -- (id as a deterministic tie-break). An anonymous owner is ALWAYS admitted —
   174	  -- they are velocity-limited instead, never ceiling-capped.
   175	  if v_anon then
   176	    admitted := true;
   177	  else
   178	    select count(*) into v_rank from profiles p2
   179	      where p2.is_anonymous = false
   180	        and (p2.created_at < v_owner_created
   181	             or (p2.created_at = v_owner_created and p2.id <= p_owner_id));
   182	    admitted := v_rank <= v_cfg.max_free_users;
   183	  end if;
   184	
   185	  -- Daily spend cap (UTC day) OR queue-depth ceiling.
   186	  v_day := (now() at time zone 'utc')::date;
   187	  select coalesce(reserved_cents, 0) + coalesce(actual_cents, 0) into v_ledger_spent
   188	    from spend_ledger where day = v_day;
   189	  select count(*) into v_queue_depth from jobs where status in ('queued', 'active');
   190	
   191	  at_capacity := coalesce(v_ledger_spent, 0) >= v_cfg.daily_cap_cents or v_queue_depth >= v_cfg.max_queue_depth;
   192	
   193	  return next;
   194	end $$;
   195	revoke all on function enqueue_preflight(inet,uuid) from public, anon, authenticated;
   196	grant execute on function enqueue_preflight(inet,uuid) to service_role;

exec
/bin/bash -lc 'nl -ba supabase/migrations/0010_cancel_job_rowcount.sql' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	-- 1E-c: cancel returns the count of rows it flagged (0 = foreign/missing/terminal),
     2	-- touches only NON-TERMINAL owned rows, and never raises (no ownership oracle).
     3	-- The 0008 function returns void; a return-type change needs DROP first (same as 0009 did
     4	-- for enqueue_job). DROP also drops the old grants — re-issue them below.
     5	drop function if exists request_cancel_job(uuid);
     6	
     7	create function request_cancel_job(p_job_id uuid) returns int
     8	  language plpgsql security definer set search_path = public as $$
     9	declare n int;
    10	begin
    11	  update jobs
    12	     set cancel_requested = true,
    13	         status = case when status = 'queued' then 'cancelled' else status end,
    14	         updated_at = now()
    15	   where id = p_job_id
    16	     and owner_id = auth.uid()
    17	     and status in ('queued','active');
    18	  get diagnostics n = row_count;
    19	  return n;
    20	end $$;
    21	revoke all on function request_cancel_job(uuid) from public;
    22	grant execute on function request_cancel_job(uuid) to anon, authenticated, service_role;

exec
/bin/bash -lc 'nl -ba supabase/migrations/0012_serve_model_charge.sql' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	-- supabase/migrations/0012_serve_model_charge.sql
     2	-- Stage 1F-a serve-side spend governance (spec §4.2). One SECURITY DEFINER lease-reserve RPC
     3	-- (Option A+): lease single-flight + charge-per-attempt + K-attempt bound + no release RPC.
     4	
     5	-- 1. Lease/charge marker. force-RLS + service_role-only grants (mirrors spend_ledger, 0011):
     6	--    writable only inside the definer RPC; never by a session client.
     7	create table serve_model_charge (
     8	  owner_id uuid not null references profiles(id) on delete cascade,
     9	  doc_key text not null,                                   -- p_playlist_id::text || '/' || p_video_id
    10	  day date not null,                                       -- (now() at time zone 'utc')::date
    11	  lease_expires_at timestamptz not null,
    12	  attempt_count int not null default 0 check (attempt_count >= 0),
    13	  unique (owner_id, doc_key, day)
    14	);
    15	alter table serve_model_charge enable row level security;
    16	alter table serve_model_charge force row level security;  -- owner-exemption removed; only BYPASSRLS roles write
    17	grant select, insert, update, delete on serve_model_charge to service_role;  -- no anon/authenticated policy
    18	
    19	-- 2. Serve-side guardrail constants (singleton row already inserted in 0011).
    20	alter table guardrail_config add column magazine_est_cents int not null default 6  check (magazine_est_cents >= 1);
    21	alter table guardrail_config add column max_serve_attempts int not null default 5  check (max_serve_attempts  >= 1);  -- K
    22	alter table guardrail_config add column lease_ttl_seconds  int not null default 180 check (lease_ttl_seconds   >= 1);
    23	
    24	-- 3. The reserve RPC. SECURITY DEFINER (owner = postgres, BYPASSRLS) so it can write the
    25	--    service_role-only tables while being callable by a session client. auth.uid() is derived
    26	--    internally — owner is NEVER a parameter.
    27	create function reserve_serve_model(p_playlist_id uuid, p_video_id text)
    28	  returns text
    29	  language plpgsql security definer set search_path = public as $$
    30	declare
    31	  v_owner uuid := auth.uid();
    32	  v_cfg guardrail_config;
    33	  v_doc_key text;
    34	  v_day date;
    35	  v_promoted boolean;
    36	  v_claimed int;
    37	  v_existing int;
    38	  v_lease_live boolean;
    39	  v_result text;
    40	begin
    41	  if v_owner is null then raise exception 'reserve_serve_model: unauthenticated'; end if;
    42	
    43	  -- Verify (playlist, video) owned by v_owner AND summary promoted. Else coarse 'denied' (no leak).
    44	  select (v.data->'artifacts'->'summaryMd'->>'status') = 'promoted'
    45	    into v_promoted
    46	    from videos v join playlists p on p.id = v.playlist_id
    47	    where v.playlist_id = p_playlist_id and v.video_id = p_video_id and p.owner_id = v_owner;
    48	  if v_promoted is distinct from true then
    49	    return 'denied';
    50	  end if;
    51	
    52	  select * into v_cfg from guardrail_config where id = true;
    53	  v_doc_key := p_playlist_id::text || '/' || p_video_id;
    54	  v_day := (now() at time zone 'utc')::date;
    55	
    56	  -- Steps 4–5 in one sub-block: the implicit savepoint lets an at-capacity RAISE roll back the claim.
    57	  begin
    58	    -- 4. Claim/reclaim the lease atomically, bounded by K attempts/day.
    59	    insert into serve_model_charge (owner_id, doc_key, day, lease_expires_at, attempt_count)
    60	      values (v_owner, v_doc_key, v_day, now() + make_interval(secs => v_cfg.lease_ttl_seconds), 1)
    61	    on conflict (owner_id, doc_key, day) do update
    62	      set lease_expires_at = now() + make_interval(secs => v_cfg.lease_ttl_seconds),
    63	          attempt_count = serve_model_charge.attempt_count + 1
    64	      where serve_model_charge.lease_expires_at < now()
    65	        and serve_model_charge.attempt_count < v_cfg.max_serve_attempts;
    66	    get diagnostics v_claimed = row_count;   -- row-returned (fresh OR reclaim) is the generator signal, not xmax
    67	
    68	    if v_claimed = 0 then
    69	      -- No claim: either a live lease (in_flight) or all K attempts used AND the last lease expired
    70	      -- (attempts_exhausted). Derive from BOTH attempt_count AND lease_expires_at, so a concurrent
    71	      -- K-boundary reclaim (loser sees attempt_count = K while the winner's K-th lease is still LIVE)
    72	      -- reports `in_flight` (single-flight guard), NOT a spurious `attempts_exhausted` (M-1 status race).
    73	      -- No charge either way. (ON CONFLICT row-lock serialization makes this read see the committed row.)
    74	      select attempt_count, lease_expires_at > now()
    75	        into v_existing, v_lease_live
    76	        from serve_model_charge
    77	        where owner_id = v_owner and doc_key = v_doc_key and day = v_day;
    78	      v_result := case
    79	                    when v_lease_live then 'in_flight'                                   -- lease still held → single-flight
    80	                    when v_existing >= v_cfg.max_serve_attempts then 'attempts_exhausted' -- expired AND K used up
    81	                    else 'in_flight'                                                     -- expired but < K (transient; a reclaim will win next)
    82	                  end;
    83	    else
    84	      -- 5. Charge THIS attempt against the daily cap (conditional-UPDATE arbiter, as enqueue_job/0011).
    85	      insert into spend_ledger (day) values (v_day) on conflict do nothing;
    86	      update spend_ledger set reserved_cents = reserved_cents + v_cfg.magazine_est_cents, updated_at = now()
    87	        where day = v_day
    88	          and reserved_cents + actual_cents + v_cfg.magazine_est_cents <= v_cfg.daily_cap_cents;
    89	      if not found then raise exception 'serve_at_capacity' using errcode = 'PJ004'; end if;  -- rolls back the step-4 claim
    90	      v_result := 'reserved';
    91	    end if;
    92	  exception
    93	    when sqlstate 'PJ004' then
    94	      v_result := 'at_capacity';   -- claim (fresh insert OR reclaim) rolled back to prior state; doc not bricked
    95	  end;
    96	
    97	  return v_result;
    98	end $$;
    99	revoke all on function reserve_serve_model(uuid, text) from public;
   100	grant execute on function reserve_serve_model(uuid, text) to authenticated, anon;  -- owner derived internally

exec
/bin/bash -lc 'nl -ba supabase/migrations/0014_serve_owner_budget.sql' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	-- supabase/migrations/0014_serve_owner_budget.sql
     2	-- Stage 1G / G1: per-owner daily serve-spend cap. Adds a per-(owner,day) cents counter enforced by a
     3	-- second atomic arbiter in reserve_serve_model, checked BEFORE the global arbiter (spec D1/D2/D3).
     4	
     5	-- 1. Per-owner counter (analog of spend_ledger). force-RLS + service_role-only (no client policy).
     6	create table serve_owner_budget (
     7	  owner_id uuid not null references profiles(id) on delete cascade,
     8	  day date not null,
     9	  spent_cents int not null default 0 check (spent_cents >= 0),
    10	  primary key (owner_id, day));
    11	alter table serve_owner_budget enable row level security;
    12	alter table serve_owner_budget force row level security;
    13	grant select, insert, update, delete on serve_owner_budget to service_role;
    14	
    15	-- 2. Config column. CHECK guarantees >= one attempt always fits (spec D2).
    16	alter table guardrail_config add column per_owner_serve_daily_cents int not null
    17	  default 60 check (per_owner_serve_daily_cents >= magazine_est_cents);
    18	
    19	-- 3. Replace reserve_serve_model: per-owner arbiter (5a) FIRST, then global (5b). CREATE OR REPLACE with
    20	--    the UNCHANGED signature preserves ACL + ownership, but the definer/search_path attributes are part
    21	--    of the definition and MUST be restated verbatim (spec Blocking/H2). Do NOT drop the function.
    22	create or replace function reserve_serve_model(p_playlist_id uuid, p_video_id text)
    23	  returns text
    24	  language plpgsql security definer set search_path = public as $$
    25	declare
    26	  v_owner uuid := auth.uid();
    27	  v_cfg guardrail_config;
    28	  v_doc_key text;
    29	  v_day date;
    30	  v_promoted boolean;
    31	  v_claimed int;
    32	  v_existing int;
    33	  v_lease_live boolean;
    34	  v_result text;
    35	begin
    36	  if v_owner is null then raise exception 'reserve_serve_model: unauthenticated'; end if;
    37	
    38	  select (v.data->'artifacts'->'summaryMd'->>'status') = 'promoted'
    39	    into v_promoted
    40	    from videos v join playlists p on p.id = v.playlist_id
    41	    where v.playlist_id = p_playlist_id and v.video_id = p_video_id and p.owner_id = v_owner;
    42	  if v_promoted is distinct from true then
    43	    return 'denied';
    44	  end if;
    45	
    46	  select * into v_cfg from guardrail_config where id = true;
    47	  v_doc_key := p_playlist_id::text || '/' || p_video_id;
    48	  v_day := (now() at time zone 'utc')::date;
    49	
    50	  begin
    51	    -- 4. Claim/reclaim the lease atomically, bounded by K attempts/day (UNCHANGED from 0012).
    52	    insert into serve_model_charge (owner_id, doc_key, day, lease_expires_at, attempt_count)
    53	      values (v_owner, v_doc_key, v_day, now() + make_interval(secs => v_cfg.lease_ttl_seconds), 1)
    54	    on conflict (owner_id, doc_key, day) do update
    55	      set lease_expires_at = now() + make_interval(secs => v_cfg.lease_ttl_seconds),
    56	          attempt_count = serve_model_charge.attempt_count + 1
    57	      where serve_model_charge.lease_expires_at < now()
    58	        and serve_model_charge.attempt_count < v_cfg.max_serve_attempts;
    59	    get diagnostics v_claimed = row_count;
    60	
    61	    if v_claimed = 0 then
    62	      select attempt_count, lease_expires_at > now()
    63	        into v_existing, v_lease_live
    64	        from serve_model_charge
    65	        where owner_id = v_owner and doc_key = v_doc_key and day = v_day;
    66	      v_result := case
    67	                    when v_lease_live then 'in_flight'
    68	                    when v_existing >= v_cfg.max_serve_attempts then 'attempts_exhausted'
    69	                    else 'in_flight'
    70	                  end;
    71	    else
    72	      -- 5a. PER-OWNER daily cap (checked FIRST) → PJ005 → 'owner_over_budget'.
    73	      --     Over-budget owners fail here without ever locking the global spend_ledger money row.
    74	      insert into serve_owner_budget (owner_id, day) values (v_owner, v_day) on conflict do nothing;
    75	      update serve_owner_budget set spent_cents = spent_cents + v_cfg.magazine_est_cents
    76	        where owner_id = v_owner and day = v_day
    77	          and spent_cents + v_cfg.magazine_est_cents <= v_cfg.per_owner_serve_daily_cents;
    78	      if not found then raise exception 'serve_owner_over_budget' using errcode = 'PJ005'; end if;
    79	
    80	      -- 5b. GLOBAL daily cap (unchanged logic) → PJ004 → 'at_capacity'.
    81	      insert into spend_ledger (day) values (v_day) on conflict do nothing;
    82	      update spend_ledger set reserved_cents = reserved_cents + v_cfg.magazine_est_cents, updated_at = now()
    83	        where day = v_day
    84	          and reserved_cents + actual_cents + v_cfg.magazine_est_cents <= v_cfg.daily_cap_cents;
    85	      if not found then raise exception 'serve_at_capacity' using errcode = 'PJ004'; end if;
    86	
    87	      v_result := 'reserved';
    88	    end if;
    89	  exception
    90	    when sqlstate 'PJ005' then v_result := 'owner_over_budget';  -- 5a claim + any 5a state rolled back
    91	    when sqlstate 'PJ004' then v_result := 'at_capacity';        -- 5a increment + step-4 claim rolled back
    92	  end;
    93	
    94	  return v_result;
    95	end $$;
    96	
    97	-- Same signature → grants/ownership preserved; restate for auditability (spec §6).
    98	revoke all on function reserve_serve_model(uuid, text) from public;
    99	grant execute on function reserve_serve_model(uuid, text) to authenticated, anon;
   100	
   101	-- P17 catalog probe helper (read-only; lets the test assert definer preservation without admin catalog access).
   102	create function reserve_serve_model_meta()
   103	  returns table(secdef boolean, cfg text[])
   104	  language sql security definer set search_path = public as $$
   105	    select p.prosecdef, p.proconfig
   106	    from pg_proc p
   107	    where p.oid = 'public.reserve_serve_model(uuid,text)'::regprocedure  -- exact overload, not proname match
   108	  $$;
   109	revoke all on function reserve_serve_model_meta() from public;
   110	grant execute on function reserve_serve_model_meta() to authenticated, anon, service_role;

exec
/bin/bash -lc 'nl -ba lib/html-doc/serve-doc.ts' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	import type { SupabaseClient } from '@supabase/supabase-js';
     2	import type { BlobStore } from '@/lib/storage/blob-store';
     3	import type { Principal } from '@/lib/storage/principal';
     4	import type { ParsedSummary, MagazineModel } from './types';
     5	import { GENERATOR_VERSION } from './constants';
     6	import { writeModelEnvelope } from './model-store';
     7	import { readFreshMagazineModel, readTitleStableModel } from './read-model';
     8	import { generateMagazineModel } from '@/lib/gemini';
     9	import type { CloudGeminiCaps } from '@/lib/gemini-cost';
    10	import {
    11	  MAX_TRANSCRIBE_INPUT_TOKENS, MAX_TRANSCRIBE_OUTPUT_TOKENS, MAX_TRANSCRIPT_INPUT_BYTES,
    12	  MAX_SUMMARY_OUTPUT_TOKENS, MAX_MAGAZINE_INPUT_TOKENS, MAX_MAGAZINE_OUTPUT_TOKENS,
    13	} from '@/lib/gemini-cost';
    14	
    15	/** Serve-side caps for the paid magazine transform (only the magazine fields are load-bearing;
    16	 *  the rest satisfy the CloudGeminiCaps type). */
    17	const SERVE_CAPS: CloudGeminiCaps = {
    18	  transcribeInputTokens: MAX_TRANSCRIBE_INPUT_TOKENS,
    19	  transcribeOutputTokens: MAX_TRANSCRIBE_OUTPUT_TOKENS,
    20	  transcriptInputBytes: MAX_TRANSCRIPT_INPUT_BYTES,
    21	  summaryOutputTokens: MAX_SUMMARY_OUTPUT_TOKENS,
    22	  magazineInputTokens: MAX_MAGAZINE_INPUT_TOKENS,
    23	  magazineOutputTokens: MAX_MAGAZINE_OUTPUT_TOKENS,
    24	};
    25	
    26	export type ResolveResult =
    27	  | { status: 'ok'; model: MagazineModel; stale?: boolean }
    28	  | { status: 'busy' }
    29	  | { status: 'attempts_exhausted' }
    30	  | { status: 'at_capacity' }
    31	  | { status: 'over_budget' }
    32	  | { status: 'denied' };
    33	
    34	export async function resolveMagazineModel(args: {
    35	  supabaseClient: SupabaseClient;
    36	  blobStore: BlobStore;
    37	  principal: Principal;
    38	  playlistId: string;
    39	  videoId: string;
    40	  base: string;
    41	  parsed: ParsedSummary;
    42	  language: 'en' | 'ko';
    43	  signal?: AbortSignal;
    44	}): Promise<ResolveResult> {
    45	  const { supabaseClient, blobStore, principal, playlistId, videoId, base, parsed, language, signal } = args;
    46	  const titles = parsed.sections.map((s) => s.title);
    47	
    48	  const fresh = await readFreshMagazineModel({ blobStore, principal, base, titles });
    49	  if (fresh.status === 'ok') return { status: 'ok', model: fresh.model }; // B1 — no Gemini, no reserve
    50	
    51	  // Absent / drifted / stale-version → materialize under the reserve RPC.
    52	  const { data: reserveStatus, error } = await supabaseClient.rpc('reserve_serve_model', {
    53	    p_playlist_id: playlistId, p_video_id: videoId,
    54	  });
    55	  if (error) throw error;
    56	  switch (reserveStatus) {
    57	    case 'denied': return { status: 'denied' };
    58	    case 'in_flight': {
    59	      // Single-flight: another attempt holds the lease. Serve the model if it landed meanwhile, else busy.
    60	      const now = await readFreshMagazineModel({ blobStore, principal, base, titles });
    61	      return now.status === 'ok' ? now : { status: 'busy' };
    62	    }
    63	    case 'attempts_exhausted': return { status: 'attempts_exhausted' };
    64	    case 'at_capacity': return { status: 'at_capacity' };
    65	    case 'owner_over_budget': {
    66	      // Spec D5: serve the title-stable stale rendering instead of failing; else 503.
    67	      const staleRead = await readTitleStableModel({ blobStore, principal, base, titles });
    68	      return staleRead.status === 'ok'
    69	        ? { status: 'ok', model: staleRead.model, stale: true }
    70	        : { status: 'over_budget' };
    71	    }
    72	    case 'reserved': break;
    73	    default: throw new Error(`reserve_serve_model: unexpected status ${String(reserveStatus)}`);
    74	  }
    75	
    76	  // We hold the lease and this attempt was charged. Generate → upsert (overwrite) → serve.
    77	  // The model uses writeModelEnvelope (plain `put` → `upload(upsert:true)`), NOT staged→promote: a
    78	  // regenerated model on drift / version-bump must OVERWRITE the stale blob so the doc self-heals
    79	  // (create-if-absent promote could never replace it → re-reserve + re-charge every view until K, then 503).
    80	  // On failure/abort do NOTHING (no release RPC): the lease expires and the next view reclaims (≤ K).
    81	  const model = await generateMagazineModel(
    82	    parsed.sections.map((s) => ({ title: s.title, prose: s.prose })),
    83	    language,
    84	    { caps: SERVE_CAPS, signal },
    85	  );
    86	  await writeModelEnvelope(principal, base, {
    87	    sourceMd: parsed.sourceMd ?? `${base}.md`,
    88	    generatedAt: new Date().toISOString(),
    89	    sourceSections: titles,
    90	    generatorVersion: GENERATOR_VERSION,
    91	    model,
    92	  }, blobStore);
    93	  return { status: 'ok', model };
    94	}

exec
/bin/bash -lc 'nl -ba lib/job-queue/worker-runner.ts' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	import type { JobQueue } from '@/lib/storage/job-queue';
     2	import type { HandlerCtx, JobHandler } from './handler-context';
     3	import { NonRetryableError } from './errors';
     4	
     5	export type { JobHandler } from './handler-context';
     6	
     7	export interface RunnerOpts {
     8	  workerId: string;
     9	  leaseSeconds?: number;
    10	  videoFilter?: string | null;
    11	  shutdownSignal?: AbortSignal;
    12	  wallClockMs?: number;
    13	}
    14	
    15	export const echoHandler: JobHandler = async (job) => ({ echoed: job.payload });
    16	
    17	// Long-running-safe job runner: heartbeats the lease while the handler runs, composes a
    18	// single AbortSignal from wall-clock/lease-loss/shutdown sources, and guarantees exactly
    19	// one terminal write (complete or fail) with clean timer teardown on every exit path.
    20	export async function runOnce(
    21	  queue: JobQueue, handler: JobHandler, opts: RunnerOpts,
    22	): Promise<'idle' | 'done' | 'failed' | 'cancelled' | 'lost'> {
    23	  await queue.sweepExpired();
    24	  const job = await queue.claim(opts.workerId, opts.leaseSeconds ?? 120, opts.videoFilter ?? null);
    25	  if (!job) return 'idle';
    26	
    27	  const leaseSeconds = opts.leaseSeconds ?? 120;
    28	  const wallClock = new AbortController();
    29	  const leaseLost = new AbortController();
    30	  const signal = AbortSignal.any(
    31	    [wallClock.signal, leaseLost.signal, opts.shutdownSignal].filter((s): s is AbortSignal => Boolean(s)),
    32	  );
    33	
    34	  const ctx: HandlerCtx = {
    35	    isCancelled: async () => (await queue.getStatus(job.id))?.cancelRequested ?? false,
    36	    signal,
    37	    // Phase writes are ADVISORY (progress hints only) — swallow a transient failure so it can
    38	    // never fail an otherwise-succeeding job. Second .then handler consumes any rejection.
    39	    setPhase: (p) => queue.setProgressPhase(job.id, opts.workerId, job.leaseToken, p).then(() => {}, () => {}),
    40	  };
    41	
    42	  const wct = setTimeout(() => wallClock.abort(), opts.wallClockMs ?? 600_000);
    43	  wct.unref?.();
    44	
    45	  const hb = setInterval(() => {
    46	    queue.heartbeat(job.id, opts.workerId, job.leaseToken, leaseSeconds)
    47	      .then(r => { if (!r.ok) leaseLost.abort(); })
    48	      .catch(() => leaseLost.abort()); // a throwing heartbeat ⇒ treat as lease-loss, never an unhandled rejection
    49	  }, Math.floor((leaseSeconds * 1000) / 3));
    50	
    51	  let settled = false;
    52	  try {
    53	    const result = await handler(job, ctx);
    54	    if (settled) return 'lost';
    55	    settled = true;
    56	    const { ok } = await queue.complete(job.id, opts.workerId, job.leaseToken, result);
    57	    return ok ? 'done' : 'lost';
    58	  } catch (e) {
    59	    if (settled) return 'lost';
    60	    settled = true;
    61	    try {
    62	      const { ok, status } = await queue.fail(
    63	        job.id, opts.workerId, job.leaseToken, e instanceof Error ? e.message : String(e),
    64	        { retryable: !(e instanceof NonRetryableError) });
    65	      if (!ok) return 'lost';
    66	      return status === 'cancelled' ? 'cancelled' : 'failed';
    67	    } catch {
    68	      // The terminal fail RPC itself threw (e.g. transient DB error). Resolve to 'lost' rather than
    69	      // rejecting out of runOnce — the declared outcome contract must be uniform so the long-lived
    70	      // worker loop (Task 8) never sees an unhandled rejection from runOnce.
    71	      return 'lost';
    72	    }
    73	  } finally {
    74	    clearInterval(hb);
    75	    clearTimeout(wct);
    76	  }
    77	}

codex
The serve caller currently still has the old “no release RPC” behavior, so I’m treating the spec as a proposed change and checking whether the proposed mechanics are sufficient. One important pattern emerging: generation can be made idempotent with the job row marker, but the serve marker as written is not tied to lease identity or materialization success.
exec
/bin/bash -lc "rg -n \"interface JobQueue|class .*JobQueue|complete\\(|fail\\(\" lib/storage lib/job-queue -S" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
lib/storage/supabase/supabase-job-queue.ts:5:export class SupabaseJobQueue implements JobQueue {
lib/storage/supabase/supabase-job-queue.ts:74:  async complete(jobId: string, workerId: string, leaseToken: string, result: unknown): Promise<{ ok: boolean }> {
lib/storage/supabase/supabase-job-queue.ts:85:  async fail(
lib/job-queue/worker-runner.ts:56:    const { ok } = await queue.complete(job.id, opts.workerId, job.leaseToken, result);
lib/job-queue/worker-runner.ts:62:      const { ok, status } = await queue.fail(
lib/storage/job-queue.ts:22:export interface JobQueue {
lib/storage/job-queue.ts:34:  complete(jobId: string, workerId: string, leaseToken: string, result: unknown): Promise<{ ok: boolean }>;
lib/storage/job-queue.ts:35:  fail(jobId: string, workerId: string, leaseToken: string, error: string, opts: { retryable: boolean }):

exec
/bin/bash -lc "rg -n \"complete\\(|fail\\(|sweepExpired|claim\\(|reserve_serve_model|release_serve_model\" lib -S" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
lib/job-queue/worker-runner.ts:23:  await queue.sweepExpired();
lib/job-queue/worker-runner.ts:24:  const job = await queue.claim(opts.workerId, opts.leaseSeconds ?? 120, opts.videoFilter ?? null);
lib/job-queue/worker-runner.ts:56:    const { ok } = await queue.complete(job.id, opts.workerId, job.leaseToken, result);
lib/job-queue/worker-runner.ts:62:      const { ok, status } = await queue.fail(
lib/storage/job-queue.ts:32:  claim(workerId: string, leaseSeconds: number, videoId?: string | null): Promise<LeasedJob | null>;
lib/storage/job-queue.ts:34:  complete(jobId: string, workerId: string, leaseToken: string, result: unknown): Promise<{ ok: boolean }>;
lib/storage/job-queue.ts:35:  fail(jobId: string, workerId: string, leaseToken: string, error: string, opts: { retryable: boolean }):
lib/storage/job-queue.ts:37:  sweepExpired(): Promise<number>;
lib/storage/supabase/supabase-job-queue.ts:56:  async claim(workerId: string, leaseSeconds: number, videoId: string | null = null): Promise<LeasedJob | null> {
lib/storage/supabase/supabase-job-queue.ts:74:  async complete(jobId: string, workerId: string, leaseToken: string, result: unknown): Promise<{ ok: boolean }> {
lib/storage/supabase/supabase-job-queue.ts:85:  async fail(
lib/storage/supabase/supabase-job-queue.ts:94:  async sweepExpired(): Promise<number> {
lib/dig/cloud/load-dig-for-serve.ts:18: * resolveMagazineModel / reserve_serve_model (spec §2 money invariant).
lib/html-doc/serve-doc.ts:52:  const { data: reserveStatus, error } = await supabaseClient.rpc('reserve_serve_model', {
lib/html-doc/serve-doc.ts:73:    default: throw new Error(`reserve_serve_model: unexpected status ${String(reserveStatus)}`);

exec
/bin/bash -lc 'rg -n "create( or replace)? function (complete_job|fail_job|sweep_expired_leases|request_cancel_job|reserve_serve_model|enqueue_job|release_serve_model)|reserved_cents|serve_model_charge|serve_owner_budget|spend_ledger" supabase lib tests -S' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
supabase/migrations/0010_cancel_job_rowcount.sql:7:create function request_cancel_job(p_job_id uuid) returns int
supabase/migrations/0014_serve_owner_budget.sql:1:-- supabase/migrations/0014_serve_owner_budget.sql
supabase/migrations/0014_serve_owner_budget.sql:5:-- 1. Per-owner counter (analog of spend_ledger). force-RLS + service_role-only (no client policy).
supabase/migrations/0014_serve_owner_budget.sql:6:create table serve_owner_budget (
supabase/migrations/0014_serve_owner_budget.sql:11:alter table serve_owner_budget enable row level security;
supabase/migrations/0014_serve_owner_budget.sql:12:alter table serve_owner_budget force row level security;
supabase/migrations/0014_serve_owner_budget.sql:13:grant select, insert, update, delete on serve_owner_budget to service_role;
supabase/migrations/0014_serve_owner_budget.sql:22:create or replace function reserve_serve_model(p_playlist_id uuid, p_video_id text)
supabase/migrations/0014_serve_owner_budget.sql:52:    insert into serve_model_charge (owner_id, doc_key, day, lease_expires_at, attempt_count)
supabase/migrations/0014_serve_owner_budget.sql:56:          attempt_count = serve_model_charge.attempt_count + 1
supabase/migrations/0014_serve_owner_budget.sql:57:      where serve_model_charge.lease_expires_at < now()
supabase/migrations/0014_serve_owner_budget.sql:58:        and serve_model_charge.attempt_count < v_cfg.max_serve_attempts;
supabase/migrations/0014_serve_owner_budget.sql:64:        from serve_model_charge
supabase/migrations/0014_serve_owner_budget.sql:73:      --     Over-budget owners fail here without ever locking the global spend_ledger money row.
supabase/migrations/0014_serve_owner_budget.sql:74:      insert into serve_owner_budget (owner_id, day) values (v_owner, v_day) on conflict do nothing;
supabase/migrations/0014_serve_owner_budget.sql:75:      update serve_owner_budget set spent_cents = spent_cents + v_cfg.magazine_est_cents
supabase/migrations/0014_serve_owner_budget.sql:81:      insert into spend_ledger (day) values (v_day) on conflict do nothing;
supabase/migrations/0014_serve_owner_budget.sql:82:      update spend_ledger set reserved_cents = reserved_cents + v_cfg.magazine_est_cents, updated_at = now()
supabase/migrations/0014_serve_owner_budget.sql:84:          and reserved_cents + actual_cents + v_cfg.magazine_est_cents <= v_cfg.daily_cap_cents;
supabase/migrations/0014_serve_owner_budget.sql:102:create function reserve_serve_model_meta()
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:16:create function enqueue_job(
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:63:create or replace function sweep_expired_leases() returns int
supabase/migrations/0008_jobs_queue.sql:44:create function enqueue_job(
supabase/migrations/0008_jobs_queue.sql:81:create function request_cancel_job(p_job_id uuid) returns void
supabase/migrations/0008_jobs_queue.sql:128:create function complete_job(p_job_id uuid, p_worker_id text, p_lease_token uuid, p_result jsonb)
supabase/migrations/0008_jobs_queue.sql:143:create function fail_job(p_job_id uuid, p_worker_id text, p_lease_token uuid, p_error text, p_retryable boolean)
supabase/migrations/0008_jobs_queue.sql:167:create function sweep_expired_leases() returns int
supabase/migrations/0011_cost_guardrails.sql:12:create table spend_ledger (                                          -- global, one row per UTC day
supabase/migrations/0011_cost_guardrails.sql:14:  reserved_cents int not null default 0 check (reserved_cents >= 0),
supabase/migrations/0011_cost_guardrails.sql:17:alter table spend_ledger enable row level security; alter table spend_ledger force row level security;
supabase/migrations/0011_cost_guardrails.sql:18:grant select, insert, update, delete on spend_ledger to service_role;   -- no client access (global infra)
supabase/migrations/0011_cost_guardrails.sql:40:alter table jobs add column reserved_cents int not null default 0;   -- charged spend (never released in 1D)
supabase/migrations/0011_cost_guardrails.sql:58:create function enqueue_job(
supabase/migrations/0011_cost_guardrails.sql:112:      insert into spend_ledger (day) values (v_day) on conflict do nothing;
supabase/migrations/0011_cost_guardrails.sql:113:      update spend_ledger set reserved_cents = reserved_cents + v_est, updated_at = now()
supabase/migrations/0011_cost_guardrails.sql:114:        where day = v_day and reserved_cents + actual_cents + v_est <= v_cfg.daily_cap_cents;
supabase/migrations/0011_cost_guardrails.sql:118:      update jobs set reserved_cents = v_est where id = v_id;
supabase/migrations/0011_cost_guardrails.sql:187:  select coalesce(reserved_cents, 0) + coalesce(actual_cents, 0) into v_ledger_spent
supabase/migrations/0011_cost_guardrails.sql:188:    from spend_ledger where day = v_day;
supabase/migrations/0018_enqueue_dig.sql:7:create or replace function enqueue_job(
supabase/migrations/0018_enqueue_dig.sql:61:      insert into spend_ledger (day) values (v_day) on conflict do nothing;
supabase/migrations/0018_enqueue_dig.sql:62:      update spend_ledger set reserved_cents = reserved_cents + v_est, updated_at = now()
supabase/migrations/0018_enqueue_dig.sql:63:        where day = v_day and reserved_cents + actual_cents + v_est <= v_cfg.daily_cap_cents;
supabase/migrations/0018_enqueue_dig.sql:67:      update jobs set reserved_cents = v_est where id = v_id;
supabase/migrations/0012_serve_model_charge.sql:1:-- supabase/migrations/0012_serve_model_charge.sql
supabase/migrations/0012_serve_model_charge.sql:5:-- 1. Lease/charge marker. force-RLS + service_role-only grants (mirrors spend_ledger, 0011):
supabase/migrations/0012_serve_model_charge.sql:7:create table serve_model_charge (
supabase/migrations/0012_serve_model_charge.sql:15:alter table serve_model_charge enable row level security;
supabase/migrations/0012_serve_model_charge.sql:16:alter table serve_model_charge force row level security;  -- owner-exemption removed; only BYPASSRLS roles write
supabase/migrations/0012_serve_model_charge.sql:17:grant select, insert, update, delete on serve_model_charge to service_role;  -- no anon/authenticated policy
supabase/migrations/0012_serve_model_charge.sql:27:create function reserve_serve_model(p_playlist_id uuid, p_video_id text)
supabase/migrations/0012_serve_model_charge.sql:59:    insert into serve_model_charge (owner_id, doc_key, day, lease_expires_at, attempt_count)
supabase/migrations/0012_serve_model_charge.sql:63:          attempt_count = serve_model_charge.attempt_count + 1
supabase/migrations/0012_serve_model_charge.sql:64:      where serve_model_charge.lease_expires_at < now()
supabase/migrations/0012_serve_model_charge.sql:65:        and serve_model_charge.attempt_count < v_cfg.max_serve_attempts;
supabase/migrations/0012_serve_model_charge.sql:76:        from serve_model_charge
supabase/migrations/0012_serve_model_charge.sql:85:      insert into spend_ledger (day) values (v_day) on conflict do nothing;
supabase/migrations/0012_serve_model_charge.sql:86:      update spend_ledger set reserved_cents = reserved_cents + v_cfg.magazine_est_cents, updated_at = now()
supabase/migrations/0012_serve_model_charge.sql:88:          and reserved_cents + actual_cents + v_cfg.magazine_est_cents <= v_cfg.daily_cap_cents;
supabase/migrations/0013_share_tokens.sql:3:-- serve_model_charge, 0012); all writes go through SECURITY DEFINER RPCs that derive the
tests/integration/share-route.test.ts:107:    const { data: ledger } = await svc.from('spend_ledger').select('*').order('day');
tests/integration/share-route.test.ts:108:    const { data: charge } = await svc.from('serve_model_charge').select('*').order('owner_id').order('doc_key').order('day');
tests/integration/share-route.test.ts:109:    const { data: ownerBudget } = await svc.from('serve_owner_budget').select('*').order('owner_id').order('day');
tests/integration/share-route.test.ts:127:    const { data: ledgerAfter } = await svc.from('spend_ledger').select('*').order('day');
tests/integration/share-route.test.ts:128:    const { data: chargeAfter } = await svc.from('serve_model_charge').select('*').order('owner_id').order('doc_key').order('day');
tests/integration/share-route.test.ts:129:    const { data: ownerBudgetAfter } = await svc.from('serve_owner_budget').select('*').order('owner_id').order('day');
tests/integration/share-route.test.ts:134:    // afterEach below), no share owner should have gained/changed a serve_owner_budget row either.
tests/integration/serve-owner-budget.test.ts:3:// .superpowers/sdd/task-1-brief.md) for the new `serve_owner_budget` counter and the
tests/integration/serve-owner-budget.test.ts:16:  svc.from('serve_model_charge').update({ lease_expires_at: '2000-01-01T00:00:00Z' }).eq('doc_key', docKey);
tests/integration/serve-owner-budget.test.ts:19:  await svc.from('serve_model_charge').delete().neq('owner_id', '00000000-0000-0000-0000-000000000000');
tests/integration/serve-owner-budget.test.ts:20:  await svc.from('serve_owner_budget').delete().neq('owner_id', '00000000-0000-0000-0000-000000000000');
tests/integration/serve-owner-budget.test.ts:21:  await svc.from('spend_ledger').delete().neq('day', '1900-01-01');
tests/integration/serve-owner-budget.test.ts:30:// the CHECK). Instead keep cap >= 6 and PRE-SEED serve_owner_budget at the cap, so the next attempt's
tests/integration/serve-owner-budget.test.ts:36:  svc.from('serve_owner_budget').insert({ owner_id: ownerId, day, spent_cents: spent });
tests/integration/serve-owner-budget.test.ts:40:  ob: (await svc.from('serve_owner_budget').select('*').eq('owner_id', ownerId).order('day')).data ?? [],
tests/integration/serve-owner-budget.test.ts:41:  led: (await svc.from('spend_ledger').select('*').order('day')).data ?? [],
tests/integration/serve-owner-budget.test.ts:42:  smc: (await svc.from('serve_model_charge').select('*').eq('owner_id', ownerId).order('doc_key')).data ?? [],
tests/integration/serve-owner-budget.test.ts:56:  const { data: ob } = await svc.from('serve_owner_budget').select('spent_cents').eq('owner_id', u.user.id).single();
tests/integration/serve-owner-budget.test.ts:58:  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
tests/integration/serve-owner-budget.test.ts:59:  expect(led![0].reserved_cents).toBe(6);
tests/integration/serve-owner-budget.test.ts:96:  expect(after).toEqual(before); // 5a serve_owner_budget increment AND the step-4 claim rolled back by 5b PJ004
tests/integration/serve-owner-budget.test.ts:108:  const { data: today } = await svc.from('serve_owner_budget').select('spent_cents').eq('owner_id', u.user.id).eq('day', utcDay()).single();
tests/integration/serve-owner-budget.test.ts:146:  const { data: ob } = await svc.from('serve_owner_budget').select('spent_cents').eq('owner_id', u.user.id).single();
tests/integration/serve-owner-budget.test.ts:174:  const { data: ob } = await svc.from('serve_owner_budget').select('spent_cents').eq('owner_id', u.user.id).single();
tests/integration/serve-owner-budget.test.ts:175:  expect(ob!.spent_cents).toBe(6);                              // +6 not +12 — serve_owner_budget row lock serialized them
tests/integration/serve-owner-budget.test.ts:176:  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
tests/integration/serve-owner-budget.test.ts:177:  expect(led!.reduce((a, r) => a + r.reserved_cents, 0)).toBe(6); // global charged once (loser's 5a rolled back before 5b)
tests/integration/serve-owner-budget.test.ts:178:  const { data: smc } = await svc.from('serve_model_charge').select('doc_key').eq('owner_id', u.user.id);
tests/integration/serve-owner-budget.test.ts:188:  await svc.from('serve_model_charge').insert({
tests/integration/serve-owner-budget.test.ts:198:  // serve_owner_budget untouched by this call (the pre-seeded row is unchanged)
tests/integration/serve-owner-budget.test.ts:199:  const { data: ob } = await svc.from('serve_owner_budget').select('spent_cents').eq('owner_id', u.user.id).single();
tests/integration/serve-owner-budget.test.ts:204://      serve_owner_budget is service_role-only + force-RLS with no client policy; the RPC's internal
tests/integration/serve-owner-budget.test.ts:207:it('a session client CANNOT select/insert/update/delete serve_owner_budget directly', async () => {
tests/integration/serve-owner-budget.test.ts:217:  const { data: before } = await svc.from('serve_owner_budget')
tests/integration/serve-owner-budget.test.ts:223:  const sel = await client.from('serve_owner_budget').select('*');
tests/integration/serve-owner-budget.test.ts:225:  const ins = await client.from('serve_owner_budget')
tests/integration/serve-owner-budget.test.ts:231:  const upd = await client.from('serve_owner_budget')
tests/integration/serve-owner-budget.test.ts:234:  const del = await client.from('serve_owner_budget')
tests/integration/serve-owner-budget.test.ts:239:  const { data: after } = await svc.from('serve_owner_budget')
tests/integration/serve-owner-budget.test.ts:247:          where relname = 'serve_owner_budget' and relnamespace = 'public'::regnamespace and relkind = 'r'`,
tests/integration/serve-model-charge.test.ts:15:  await svc.from('serve_model_charge').delete().neq('owner_id', '00000000-0000-0000-0000-000000000000');
tests/integration/serve-model-charge.test.ts:16:  await svc.from('spend_ledger').delete().neq('day', '1900-01-01');
tests/integration/serve-model-charge.test.ts:34:  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
tests/integration/serve-model-charge.test.ts:35:  expect(led![0].reserved_cents).toBe(6);
tests/integration/serve-model-charge.test.ts:45:  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
tests/integration/serve-model-charge.test.ts:46:  expect(led![0].reserved_cents).toBe(6); // still one charge
tests/integration/serve-model-charge.test.ts:57:    await svc.from('serve_model_charge').update({ lease_expires_at: '2000-01-01T00:00:00Z' }).eq('doc_key', docKey); // expire the lease
tests/integration/serve-model-charge.test.ts:61:  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
tests/integration/serve-model-charge.test.ts:62:  expect(led![0].reserved_cents).toBe(30); // exactly K charges
tests/integration/serve-model-charge.test.ts:72:  const { data: rows } = await svc.from('serve_model_charge').select('*'); // claim rolled back → no marker
tests/integration/serve-model-charge.test.ts:84:  const { error: seedErr } = await svc.from('serve_model_charge').insert({
tests/integration/serve-model-charge.test.ts:89:  const { data: before } = await svc.from('serve_model_charge')
tests/integration/serve-model-charge.test.ts:101:  const { data: after } = await svc.from('serve_model_charge')
tests/integration/serve-model-charge.test.ts:104:  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
tests/integration/serve-model-charge.test.ts:105:  expect(led ?? []).toEqual([]); // the spend_ledger insert (step 5) rolled back with the claim — no row for the day
tests/integration/serve-model-charge.test.ts:121:  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
tests/integration/serve-model-charge.test.ts:134:it('a session client CANNOT select/insert/update/delete serve_model_charge directly', async () => {
tests/integration/serve-model-charge.test.ts:144:  const { data: before } = await svc.from('serve_model_charge')
tests/integration/serve-model-charge.test.ts:150:  const sel = await client.from('serve_model_charge').select('*');
tests/integration/serve-model-charge.test.ts:152:  const ins = await client.from('serve_model_charge')
tests/integration/serve-model-charge.test.ts:159:  const upd = await client.from('serve_model_charge')
tests/integration/serve-model-charge.test.ts:162:  const del = await client.from('serve_model_charge')
tests/integration/serve-model-charge.test.ts:167:  const { data: after } = await svc.from('serve_model_charge')
tests/integration/serve-model-charge.test.ts:175:          where relname = 'serve_model_charge' and relnamespace = 'public'::regnamespace and relkind = 'r'`,
tests/integration/serve-model-charge.test.ts:196:  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
tests/integration/serve-model-charge.test.ts:211:  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
tests/integration/serve-model-charge.test.ts:212:  expect(led![0].reserved_cents).toBe(6);                             // exactly one charge
tests/integration/serve-model-charge.test.ts:225:    await svc.from('serve_model_charge').update({ lease_expires_at: '2000-01-01T00:00:00Z' }).eq('doc_key', docKey);
tests/integration/serve-model-charge.test.ts:233:  const { data: row } = await svc.from('serve_model_charge').select('attempt_count').eq('doc_key', docKey).single();
tests/integration/serve-model-charge.test.ts:235:  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
tests/integration/serve-model-charge.test.ts:236:  expect(led![0].reserved_cents).toBe(30);                           // 5·6 — the loser added no 6th charge
tests/integration/serve-model-charge.test.ts:251:  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
tests/integration/serve-model-charge.test.ts:252:  expect(led![0].reserved_cents).toBe(6);                              // the cap is a hard ceiling
tests/integration/serve-model-charge.test.ts:256:  const { data: markers } = await svc.from('serve_model_charge').select('doc_key');
tests/integration/html-download.test.ts:50:  // Supabase stack persists across test runs, so a stale spend_ledger row from an earlier file/run
tests/integration/html-download.test.ts:52:  await svc.from('serve_model_charge').delete().neq('owner_id', '00000000-0000-0000-0000-000000000000');
tests/integration/html-download.test.ts:53:  await svc.from('serve_owner_budget').delete().neq('owner_id', '00000000-0000-0000-0000-000000000000');
tests/integration/html-download.test.ts:54:  await svc.from('spend_ledger').delete().neq('day', '1900-01-01');
tests/integration/html-download.test.ts:97:  svc.from('serve_owner_budget').insert({ owner_id: ownerId, day, spent_cents: spent });
tests/integration/html-download.test.ts:122:  it('C2: owner GET format=md&download=1 → 200 text/markdown, attachment filename="<base>.md"; no reserve_serve_model call; spend_ledger unchanged', async () => {
tests/integration/html-download.test.ts:125:    const { data: ledgerBefore } = await svc.from('spend_ledger').select('*').order('day');
tests/integration/html-download.test.ts:134:    const { data: ledgerAfter } = await svc.from('spend_ledger').select('*').order('day');
tests/integration/html-download.test.ts:143:    const { data: ledgerBefore } = await svc.from('spend_ledger').select('*').order('day');
tests/integration/html-download.test.ts:152:    const { data: ledgerAfter } = await svc.from('spend_ledger').select('*').order('day');
tests/integration/dig-serve-interactive.test.ts:81:    const { data: before } = await admin.from('spend_ledger').select('amount_cents');
tests/integration/dig-serve-interactive.test.ts:89:    const { data: after } = await admin.from('spend_ledger').select('amount_cents');
tests/integration/dig-cloud.test.ts:54:  await admin.from('spend_ledger').delete().neq('day', '1970-01-01');
tests/integration/dig-cloud.test.ts:114:    const { data: slBefore } = await admin.from('spend_ledger').select('*'); // spend_ledger is global-by-day
tests/integration/dig-cloud.test.ts:120:    // The dedup (200-ready) path must also leave the global spend_ledger untouched — a spurious
tests/integration/dig-cloud.test.ts:122:    const { data: slAfter } = await admin.from('spend_ledger').select('*');
tests/integration/pdf-cloud.test.ts:20://    and spend_ledger is unchanged — proven against a mutation control (same request shape, no
tests/integration/pdf-cloud.test.ts:212:  // Supabase stack persists across test runs, so a stale spend_ledger row from an earlier file/run
tests/integration/pdf-cloud.test.ts:214:  await svc.from('serve_model_charge').delete().neq('owner_id', '00000000-0000-0000-0000-000000000000');
tests/integration/pdf-cloud.test.ts:215:  await svc.from('serve_owner_budget').delete().neq('owner_id', '00000000-0000-0000-0000-000000000000');
tests/integration/pdf-cloud.test.ts:216:  await svc.from('spend_ledger').delete().neq('day', '1900-01-01');
tests/integration/pdf-cloud.test.ts:319:  it('money: fresh model -> PDF request makes NO reserve_serve_model RPC on EITHER a cache-MISS or a genuine cache-HIT; spend_ledger unchanged', async () => {
tests/integration/pdf-cloud.test.ts:323:    const { data: ledgerBefore } = await svc.from('spend_ledger').select('*').order('day');
tests/integration/pdf-cloud.test.ts:347:      const { data: ledgerAfter } = await svc.from('spend_ledger').select('*').order('day');
tests/integration/serve-doc-materialize.test.ts:38:  svc.from('serve_owner_budget').insert({ owner_id: ownerId, day, spent_cents: spent });
tests/integration/serve-doc-materialize.test.ts:40:  ob: (await svc.from('serve_owner_budget').select('*').eq('owner_id', ownerId).order('day')).data ?? [],
tests/integration/serve-doc-materialize.test.ts:41:  led: (await svc.from('spend_ledger').select('*').order('day')).data ?? [],
tests/integration/serve-doc-materialize.test.ts:42:  smc: (await svc.from('serve_model_charge').select('*').eq('owner_id', ownerId).order('doc_key')).data ?? [],
tests/integration/serve-doc-materialize.test.ts:46:  await svc.from('serve_model_charge').delete().neq('owner_id', '00000000-0000-0000-0000-000000000000');
tests/integration/serve-doc-materialize.test.ts:47:  await svc.from('serve_owner_budget').delete().neq('owner_id', '00000000-0000-0000-0000-000000000000');
tests/integration/serve-doc-materialize.test.ts:48:  await svc.from('spend_ledger').delete().neq('day', '1900-01-01');
tests/integration/serve-doc-materialize.test.ts:84:  await svc.from('serve_model_charge').update({ lease_expires_at: '2000-01-01T00:00:00Z' })
tests/integration/serve-doc-materialize.test.ts:89:  const { data: charge } = await svc.from('serve_model_charge').select('attempt_count')
tests/integration/serve-doc-materialize.test.ts:114:  await svc.from('serve_model_charge').delete().neq('owner_id', '00000000-0000-0000-0000-000000000000'); // fresh day room
tests/integration/serve-doc-materialize.test.ts:150:  // NO additional Gemini call and NO second reserve/charge. serve_model_charge still holds exactly the
tests/integration/serve-doc-materialize.test.ts:156:  const { data: charge } = await svc.from('serve_model_charge').select('attempt_count').eq('owner_id', u.user.id).single();
tests/integration/serve-doc-materialize.test.ts:261:  await svc.from('serve_owner_budget').delete().eq('owner_id', u.user.id);
tests/integration/cost-guardrails.test.ts:41:  await svc.from('spend_ledger').delete().neq('day', '1900-01-01'); // clear all ledger days
tests/integration/cost-guardrails.test.ts:70:it('lets an owner read only their own usage_counters and denies spend_ledger/guardrail_config reads', async () => {
tests/integration/cost-guardrails.test.ts:78:  const led = await sa.from('spend_ledger').select('*'); // no client grant → error, not []
tests/integration/cost-guardrails.test.ts:154:  const { data } = await svc.from('jobs').select('max_attempts,reserved_cents').eq('id', r.data![0].job_id).single();
tests/integration/cost-guardrails.test.ts:156:  expect(data!.reserved_cents).toBe(150); // reservation stamped on the row
tests/integration/cost-guardrails.test.ts:207:  const before = await svc.from('spend_ledger').select('day,reserved_cents').order('day');
tests/integration/cost-guardrails.test.ts:210:  const after = await svc.from('spend_ledger').select('day,reserved_cents').order('day');
tests/integration/schema.test.ts:11:                              'usage_counters','spend_ledger','quota_allowance','guardrail_config')
tests/integration/schema.test.ts:24:      { relname: 'spend_ledger', relrowsecurity: true, relforcerowsecurity: true },
tests/integration/schema.test.ts:65:  it('defines ZERO policies on the service-role-only tables spend_ledger and guardrail_config (1D-1)', async () => {
tests/integration/schema.test.ts:72:              and tablename in ('spend_ledger','guardrail_config')

exec
/bin/bash -lc 'nl -ba lib/storage/job-queue.ts' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	import type { DocVersion } from '@/lib/doc-version';
     2	import type { ProgressPhase } from '@/lib/job-queue/progress-phase';
     3	
     4	export type JobKind = 'summary' | 'dig';
     5	export type JobStatus = 'queued' | 'active' | 'completed' | 'failed' | 'dead_letter' | 'cancelled';
     6	
     7	export interface JobKey { playlistId: string; videoId: string; sectionId: number; kind: JobKind; version: string; }
     8	export interface EnqueueResult { jobId: string; status: JobStatus; joined: boolean; }
     9	export interface LeasedJob {
    10	  id: string; ownerId: string; playlistId: string; videoId: string; sectionId: number;
    11	  kind: JobKind; version: string; payload: unknown; attempts: number; leaseToken: string;
    12	}
    13	export interface JobRecord {
    14	  id: string; status: JobStatus; cancelRequested: boolean; result: unknown; error: string | null;
    15	  progressPhase: ProgressPhase | null; attempts: number; updatedAt: string;
    16	}
    17	export interface PlaylistJobRow {
    18	  jobId: string; videoId: string; status: JobStatus;
    19	  progressPhase: ProgressPhase | null; attempts: number; error: string | null;
    20	}
    21	
    22	export interface JobQueue {
    23	  getStatus(jobId: string): Promise<JobRecord | null>;
    24	  listByPlaylist(playlistId: string): Promise<PlaylistJobRow[]>;
    25	  requestCancel(jobId: string): Promise<{ requested: number }>;
    26	  /** Cancel every non-terminal (queued/active) job for a playlist (Task 8) by calling the
    27	   *  SECURITY DEFINER `request_cancel_playlist_jobs` RPC (0019), which self-guards on
    28	   *  `owner_id = auth.uid()` — a non-owner playlistId cancels 0 rows. Added to the
    29	   *  interface (not just the class) because T9's DELETE route consumes it through
    30	   *  `bundle.jobQueue` typed as `JobQueue`; `SupabaseJobQueue` is the sole implementer. */
    31	  requestCancelPlaylist(playlistId: string): Promise<{ cancelled: number }>;
    32	  claim(workerId: string, leaseSeconds: number, videoId?: string | null): Promise<LeasedJob | null>;
    33	  heartbeat(jobId: string, workerId: string, leaseToken: string, leaseSeconds: number): Promise<{ ok: boolean }>;
    34	  complete(jobId: string, workerId: string, leaseToken: string, result: unknown): Promise<{ ok: boolean }>;
    35	  fail(jobId: string, workerId: string, leaseToken: string, error: string, opts: { retryable: boolean }):
    36	    Promise<{ ok: boolean; status: JobStatus | null }>;
    37	  sweepExpired(): Promise<number>;
    38	  setProgressPhase(jobId: string, workerId: string, leaseToken: string, phase: ProgressPhase): Promise<{ ok: boolean }>;
    39	}
    40	
    41	export function docVersionKey(v: DocVersion): string { return `${v.major}.${v.minor}`; }

exec
/bin/bash -lc 'nl -ba lib/storage/supabase/supabase-job-queue.ts' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	import type { SupabaseClient } from '@supabase/supabase-js';
     2	import type { JobQueue, LeasedJob, JobRecord, JobStatus, PlaylistJobRow } from '@/lib/storage/job-queue';
     3	import type { ProgressPhase } from '@/lib/job-queue/progress-phase';
     4	
     5	export class SupabaseJobQueue implements JobQueue {
     6	  constructor(private client: SupabaseClient) {}
     7	
     8	  async getStatus(jobId: string): Promise<JobRecord | null> {
     9	    const { data, error } = await this.client
    10	      .from('jobs').select('id,status,cancel_requested,result,error,progress_phase,attempts,updated_at')
    11	      .eq('id', jobId).maybeSingle();
    12	    if (error) throw error;
    13	    if (!data) return null;
    14	    return { id: data.id, status: data.status, cancelRequested: data.cancel_requested,
    15	      result: data.result, error: data.error, progressPhase: data.progress_phase,
    16	      attempts: data.attempts, updatedAt: data.updated_at };
    17	  }
    18	
    19	  /**
    20	   * RLS-dependent: owner confinement (`owner_id = auth.uid()`) comes entirely from Postgres RLS
    21	   * on the caller's session client — this method MUST NOT be called on a service_role-constructed
    22	   * SupabaseJobQueue (service_role bypasses RLS and would leak cross-owner rows).
    23	   */
    24	  async listByPlaylist(playlistId: string): Promise<PlaylistJobRow[]> {
    25	    const { data, error } = await this.client
    26	      .from('jobs')
    27	      .select('id,video_id,status,progress_phase,attempts,error,created_at')
    28	      .eq('playlist_id', playlistId).eq('job_kind', 'summary')
    29	      .order('created_at', { ascending: true }).order('video_id', { ascending: true });
    30	    if (error) throw error;
    31	    // The idempotency index (`jobs_idem_active`) excludes failed/cancelled/dead_letter, so
    32	    // re-submitting a partially-failed playlist creates a SECOND row for the same videoId (a
    33	    // stale terminal row plus a fresh queued one). Dedupe to the latest row per videoId: iterate
    34	    // in ascending created_at order and let a later row overwrite an earlier one in the Map, so
    35	    // callers (rollup, the polling client) never see a phantom duplicate or a stale `failed`.
    36	    const latestByVideo = new Map<string, PlaylistJobRow>();
    37	    for (const r of data ?? []) {
    38	      latestByVideo.set(r.video_id, { jobId: r.id, videoId: r.video_id, status: r.status,
    39	        progressPhase: r.progress_phase, attempts: r.attempts, error: r.error });
    40	    }
    41	    return Array.from(latestByVideo.values());
    42	  }
    43	
    44	  async requestCancel(jobId: string): Promise<{ requested: number }> {
    45	    const { data, error } = await this.client.rpc('request_cancel_job', { p_job_id: jobId });
    46	    if (error) throw error;
    47	    return { requested: (data as number) ?? 0 };
    48	  }
    49	
    50	  async requestCancelPlaylist(playlistId: string): Promise<{ cancelled: number }> {
    51	    const { data, error } = await this.client.rpc('request_cancel_playlist_jobs', { p_playlist_id: playlistId });
    52	    if (error) throw error;
    53	    return { cancelled: (data as number) ?? 0 };
    54	  }
    55	
    56	  async claim(workerId: string, leaseSeconds: number, videoId: string | null = null): Promise<LeasedJob | null> {
    57	    const { data, error } = await this.client.rpc('claim_next_job', {
    58	      p_worker_id: workerId, p_lease_seconds: leaseSeconds, p_video_id: videoId });
    59	    if (error) throw error;
    60	    if (!data || data.length === 0) return null;
    61	    const r = data[0];
    62	    return {
    63	      id: r.id, ownerId: r.owner_id, playlistId: r.playlist_id, videoId: r.video_id, sectionId: r.section_id,
    64	      kind: r.job_kind, version: r.job_version, payload: r.payload, attempts: r.attempts, leaseToken: r.lease_token };
    65	  }
    66	
    67	  async heartbeat(jobId: string, workerId: string, leaseToken: string, leaseSeconds: number): Promise<{ ok: boolean }> {
    68	    const { data, error } = await this.client.rpc('heartbeat_job', {
    69	      p_job_id: jobId, p_worker_id: workerId, p_lease_token: leaseToken, p_lease_seconds: leaseSeconds });
    70	    if (error) throw error;
    71	    return { ok: data === true };
    72	  }
    73	
    74	  async complete(jobId: string, workerId: string, leaseToken: string, result: unknown): Promise<{ ok: boolean }> {
    75	    // p_result MUST be JSON-serializable-present: a handler that returns nothing gives
    76	    // result === undefined, and supabase-js sends params via JSON.stringify, which drops
    77	    // undefined-valued keys — dropping p_result makes PostgREST 404 the 4-arg complete_job
    78	    // (PGRST202). Coalesce to null so the param always reaches the RPC.
    79	    const { data, error } = await this.client.rpc('complete_job', {
    80	      p_job_id: jobId, p_worker_id: workerId, p_lease_token: leaseToken, p_result: result ?? null });
    81	    if (error) throw error;
    82	    return { ok: data === true };
    83	  }
    84	
    85	  async fail(
    86	    jobId: string, workerId: string, leaseToken: string, err: string, opts: { retryable: boolean },
    87	  ): Promise<{ ok: boolean; status: JobStatus | null }> {
    88	    const { data, error } = await this.client.rpc('fail_job', {
    89	      p_job_id: jobId, p_worker_id: workerId, p_lease_token: leaseToken, p_error: err, p_retryable: opts.retryable });
    90	    if (error) throw error;
    91	    return { ok: data !== null, status: data };
    92	  }
    93	
    94	  async sweepExpired(): Promise<number> {
    95	    const { data, error } = await this.client.rpc('sweep_expired_leases');
    96	    if (error) throw error;
    97	    return data as number;
    98	  }
    99	
   100	  async setProgressPhase(
   101	    jobId: string, workerId: string, leaseToken: string, phase: ProgressPhase,
   102	  ): Promise<{ ok: boolean }> {
   103	    const { data, error } = await this.client.rpc('set_progress_phase', {
   104	      p_job_id: jobId, p_worker_id: workerId, p_lease_token: leaseToken, p_phase: phase });
   105	    if (error) throw error;
   106	    return { ok: data === true };
   107	  }
   108	}

exec
/bin/bash -lc "nl -ba tests/integration/serve-doc-materialize.test.ts | sed -n '70,180p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
    70	it('serves the cached model without a second Gemini call OR a second reserve/charge (B1)', async () => {
    71	  const u = await newUser(); const { playlistId, playlist_key, videoId } = await seed(u.user.id);
    72	  const { client } = await signInAs(u.email, u.password);
    73	  const principal = { id: u.user.id, indexKey: playlist_key };
    74	  const blob = new SupabaseBlobStore(client, ARTIFACTS_BUCKET);
    75	  await resolveMagazineModel({ supabaseClient: client, blobStore: blob, principal, playlistId, videoId, base: videoId, parsed: parsed(), language: 'en' });
    76	  (generateMagazineModel as jest.Mock).mockClear();
    77	  const doc_key = `${playlistId}/${videoId}`; // reserve_serve_model's v_doc_key formula (0012, line 53)
    78	  // Force the materialize call's lease to look EXPIRED. Without this, a spurious reserve on the
    79	  // fresh-cache path would hit the RPC's own single-flight guard (lease still live → no-op, no
    80	  // charge) and the assertion below would pass EVEN IF resolveMagazineModel's isFresh() short-circuit
    81	  // were removed — a false negative. With the lease forced expired, any reserve call would take the
    82	  // reclaim branch: bump attempt_count, charge, and call generateMagazineModel — so this test
    83	  // genuinely fails if the fresh-cache path ever calls reserve_serve_model.
    84	  await svc.from('serve_model_charge').update({ lease_expires_at: '2000-01-01T00:00:00Z' })
    85	    .eq('owner_id', u.user.id).eq('doc_key', doc_key);
    86	  const res2 = await resolveMagazineModel({ supabaseClient: client, blobStore: blob, principal, playlistId, videoId, base: videoId, parsed: parsed(), language: 'en' });
    87	  expect(res2.status).toBe('ok');
    88	  expect(generateMagazineModel).not.toHaveBeenCalled();
    89	  const { data: charge } = await svc.from('serve_model_charge').select('attempt_count')
    90	    .eq('owner_id', u.user.id).eq('doc_key', doc_key).single();
    91	  expect(charge?.attempt_count).toBe(1); // unchanged — fresh-cache path never reserved/charged again
    92	});
    93	
    94	it('at_capacity when the day is over budget — no Gemini call, no promote (B6)', async () => {
    95	  const u = await newUser(); const { playlistId, playlist_key, videoId } = await seed(u.user.id);
    96	  await svc.from('guardrail_config').update({ daily_cap_cents: 3 }).eq('id', true);
    97	  const { client } = await signInAs(u.email, u.password);
    98	  const principal = { id: u.user.id, indexKey: playlist_key };
    99	  const blob = new SupabaseBlobStore(client, ARTIFACTS_BUCKET);
   100	  const res = await resolveMagazineModel({ supabaseClient: client, blobStore: blob, principal, playlistId, videoId, base: videoId, parsed: parsed(), language: 'en' });
   101	  expect(res.status).toBe('at_capacity');
   102	  expect(generateMagazineModel).not.toHaveBeenCalled();
   103	  expect(await readModelEnvelope(principal, videoId, blob)).toBeNull();
   104	});
   105	
   106	it('re-materializes on drift (sourceSections mismatch) — B3', async () => {
   107	  const u = await newUser(); const { playlistId, playlist_key, videoId } = await seed(u.user.id);
   108	  const { client } = await signInAs(u.email, u.password);
   109	  const principal = { id: u.user.id, indexKey: playlist_key };
   110	  const blob = new SupabaseBlobStore(client, ARTIFACTS_BUCKET);
   111	  await resolveMagazineModel({ supabaseClient: client, blobStore: blob, principal, playlistId, videoId, base: videoId, parsed: parsed(), language: 'en' });
   112	  (generateMagazineModel as jest.Mock).mockClear();
   113	  const drifted = parsed(); drifted.sections[0].title = 'Renamed'; // titles now differ from the cached sourceSections
   114	  await svc.from('serve_model_charge').delete().neq('owner_id', '00000000-0000-0000-0000-000000000000'); // fresh day room
   115	  const res = await resolveMagazineModel({ supabaseClient: client, blobStore: blob, principal, playlistId, videoId, base: videoId, parsed: drifted, language: 'en' });
   116	  expect(res.status).toBe('ok');
   117	  expect(generateMagazineModel).toHaveBeenCalledTimes(1); // regenerated
   118	});
   119	
   120	it('re-materializes on a STALE generatorVersion even when sourceSections match (F6 — version gate)', async () => {
   121	  const u = await newUser(); const { playlistId, playlist_key, videoId } = await seed(u.user.id);
   122	  const { client } = await signInAs(u.email, u.password);
   123	  const principal = { id: u.user.id, indexKey: playlist_key };
   124	  const blob = new SupabaseBlobStore(client, ARTIFACTS_BUCKET);
   125	  const p = parsed();
   126	  // Seed a cached envelope whose sourceSections MATCH the current parse (NO title drift) but whose
   127	  // generatorVersion is stale (guaranteed ≠ current via the `-STALE` suffix). ONLY the version check can
   128	  // trigger regeneration here — this test goes red if a future edit drops that check, since title-drift
   129	  // alone would keep serving the cache (that is the exact regression F6 guards).
   130	  await writeModelEnvelope(principal, videoId, {
   131	    sourceMd: p.sourceMd!,
   132	    generatedAt: '2026-01-01T00:00:00.000Z',
   133	    sourceSections: p.sections.map((s) => s.title),
   134	    generatorVersion: `${GENERATOR_VERSION}-STALE`,
   135	    model: { sections: [{ lead: 'old', bullets: [{ label: 'a', text: 'x' }, { label: 'b', text: 'y' }, { label: 'c', text: 'z' }] }] },
   136	  }, blob);
   137	  const res = await resolveMagazineModel({ supabaseClient: client, blobStore: blob, principal, playlistId, videoId, base: videoId, parsed: p, language: 'en' });
   138	  expect(res.status).toBe('ok');
   139	  expect(generateMagazineModel).toHaveBeenCalledTimes(1);         // stale version → REGENERATED, not served from cache
   140	  // The returned model is the freshly-generated one (mock lead 'L'), NOT the seeded stale model (lead 'old').
   141	  if (res.status === 'ok') expect(res.model.sections[0].lead).toBe('L');
   142	  // Persistence proof (Option A): writeModelEnvelope upserts (plain `put`), so the stale blob was
   143	  // OVERWRITTEN in place. Re-read the persisted envelope and assert it now carries the CURRENT version
   144	  // and the fresh model — this is the on-disk half of the money-path heal (a create-if-absent promote
   145	  // could NOT have replaced it).
   146	  const persisted = await readModelEnvelope(principal, videoId, blob);
   147	  expect(persisted?.generatorVersion).toBe(GENERATOR_VERSION);
   148	  expect(persisted?.model.sections[0].lead).toBe('L');
   149	  // Self-heal proof: a SECOND view with the same fresh parse now serves from the overwritten cache —
   150	  // NO additional Gemini call and NO second reserve/charge. serve_model_charge still holds exactly the
   151	  // ONE attempt from the regen above (attempt_count === 1), so the doc does not re-charge every view.
   152	  (generateMagazineModel as jest.Mock).mockClear();
   153	  const res2 = await resolveMagazineModel({ supabaseClient: client, blobStore: blob, principal, playlistId, videoId, base: videoId, parsed: p, language: 'en' });
   154	  expect(res2.status).toBe('ok');
   155	  expect(generateMagazineModel).not.toHaveBeenCalled();
   156	  const { data: charge } = await svc.from('serve_model_charge').select('attempt_count').eq('owner_id', u.user.id).single();
   157	  expect(charge?.attempt_count).toBe(1);
   158	});
   159	
   160	it('degrades a corrupt cached model file (malformed JSON) to a regenerate, never a throw (B4)', async () => {
   161	  const u = await newUser(); const { playlistId, playlist_key, videoId } = await seed(u.user.id);
   162	  const { client } = await signInAs(u.email, u.password);
   163	  const principal = { id: u.user.id, indexKey: playlist_key };
   164	  const blob = new SupabaseBlobStore(client, ARTIFACTS_BUCKET);
   165	  // Seed a CORRUPT models/<base>.json directly via the blob store (bypassing writeModelEnvelope's
   166	  // zod validation, which would refuse to persist invalid JSON) — simulates a hand-corrupted or
   167	  // partially-written blob. readModelEnvelope must swallow the JSON.parse failure and return null
   168	  // (model-store.ts:58-63), so resolveMagazineModel treats it as a cache MISS, not a thrown error.
   169	  await blob.put(principal, `models/${videoId}.json`, Buffer.from('{ not valid json', 'utf-8'), 'application/json');
   170	  const res = await resolveMagazineModel({ supabaseClient: client, blobStore: blob, principal, playlistId, videoId, base: videoId, parsed: parsed(), language: 'en' });
   171	  expect(res.status).toBe('ok');
   172	  expect(generateMagazineModel).toHaveBeenCalledTimes(1); // corrupt cache treated as absent → regenerated, not thrown
   173	  const persisted = await readModelEnvelope(principal, videoId, blob);
   174	  expect(persisted?.generatorVersion).toBe(GENERATOR_VERSION); // valid envelope now persisted, overwriting the corrupt blob
   175	  expect(persisted?.model.sections[0].lead).toBe('L'); // freshly-generated (mock) model, not a leftover of the corrupt file
   176	});
   177	
   178	// ── Stage 1G / G1 Task 2: owner_over_budget → title-stable serve-stale (spec D5) ──
   179	const staleModel = { sections: [{ lead: 'old', bullets: [{ label: 'a', text: 'x' }, { label: 'b', text: 'y' }, { label: 'c', text: 'z' }] }] };
   180	

exec
/bin/bash -lc 'nl -ba supabase/migrations/0019_delete_playlist_cancel_jobs.sql' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 exited 1 in 0ms:
nl: supabase/migrations/0019_delete_playlist_cancel_jobs.sql: No such file or directory

exec
/bin/bash -lc 'rg -n "request_cancel_playlist_jobs|requestCancelPlaylist|delete playlist|DELETE" app lib supabase/migrations -S' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
lib/client/api.ts:260:  const res = await fetch(`/api/playlists/${encodeURIComponent(id)}`, { method: 'DELETE' });
supabase/migrations/0019_share_tokens_cascade.sql:5:--       `DELETE playlists` cascades ALL DB state atomically (one transaction, no RPC).
supabase/migrations/0019_share_tokens_cascade.sql:6:--   (b) the playlist HARD-DELETE flow (plan Task 9 / spec §B4) needs a CANCEL-FIRST step:
supabase/migrations/0019_share_tokens_cascade.sql:45:create or replace function request_cancel_playlist_jobs(p_playlist_id uuid) returns int
supabase/migrations/0019_share_tokens_cascade.sql:59:revoke all on function request_cancel_playlist_jobs(uuid) from public;
supabase/migrations/0019_share_tokens_cascade.sql:60:grant execute on function request_cancel_playlist_jobs(uuid) to authenticated, service_role;
lib/storage/job-queue.ts:27:   *  SECURITY DEFINER `request_cancel_playlist_jobs` RPC (0019), which self-guards on
lib/storage/job-queue.ts:29:   *  interface (not just the class) because T9's DELETE route consumes it through
lib/storage/job-queue.ts:31:  requestCancelPlaylist(playlistId: string): Promise<{ cancelled: number }>;
lib/storage/supabase/supabase-job-queue.ts:50:  async requestCancelPlaylist(playlistId: string): Promise<{ cancelled: number }> {
lib/storage/supabase/supabase-job-queue.ts:51:    const { data, error } = await this.client.rpc('request_cancel_playlist_jobs', { p_playlist_id: playlistId });
lib/storage/supabase/supabase-metadata-store.ts:268:  // RLS already scopes DELETE to owner_id = auth.uid(); the explicit .eq('owner_id')
app/api/playlists/[id]/route.ts:3:// DELETE /api/playlists/[id] — full hard-delete of a cloud playlist (Task 9). Cloud-only.
app/api/playlists/[id]/route.ts:5:// and T8 (MetadataStore.deletePlaylist + JobQueue.requestCancelPlaylist):
app/api/playlists/[id]/route.ts:33:export async function DELETE(_request: Request, { params }: Params): Promise<Response> {
app/api/playlists/[id]/route.ts:65:    // Best-effort cancel-first (all kinds, via request_cancel_playlist_jobs): a failure here
app/api/playlists/[id]/route.ts:68:      await queue.requestCancelPlaylist(id);
app/api/playlists/[id]/route.ts:70:      console.error(`DELETE /api/playlists/${id}: cancel-first failed (continuing)`, e);
app/api/playlists/[id]/route.ts:81:      console.error(`DELETE /api/playlists/${id}: blob cleanup failed (invisible orphan accepted)`, e);

exec
/bin/bash -lc "nl -ba supabase/migrations/0019_share_tokens_cascade.sql | sed -n '1,90p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	-- supabase/migrations/0019_share_tokens_cascade.sql
     2	-- Completes the delete surface (plan Task 6 / spec §B2, §B4):
     3	--   (a) share_tokens.playlist_id had NO FK (0013) — deleting a playlist orphaned its share
     4	--       tokens. Add the same composite cascade FK already used for videos/jobs (0001/0009) so
     5	--       `DELETE playlists` cascades ALL DB state atomically (one transaction, no RPC).
     6	--   (b) the playlist HARD-DELETE flow (plan Task 9 / spec §B4) needs a CANCEL-FIRST step:
     7	--       before the cascade delete removes a playlist's rows, any of its non-terminal jobs (of
     8	--       ANY kind, including `dig`) must be cancelled so an in-flight worker doesn't keep writing
     9	--       to rows that are about to disappear underneath it. Add a SECURITY DEFINER RPC that does
    10	--       this, owner-guarded via auth.uid(), mirroring the per-job request_cancel_job (0010).
    11	--       This is SEPARATE from the pre-existing, unrelated app/api/jobs/cancel ingestion-cancel
    12	--       path (SupabaseJobQueue.listByPlaylist), which filters job_kind='summary' by design for
    13	--       its own (non-delete) use case — that path is OUT OF SCOPE here and is not retrofitted
    14	--       by this migration.
    15	
    16	-- Defensive one-shot: remove any pre-existing share_tokens rows orphaned by a playlist delete
    17	-- that happened BEFORE this cascade FK existed. Once the FK below is in place this delete can
    18	-- never find a match again (RI prevents new orphans) — it exists solely so historical orphans
    19	-- don't block the ALTER ... ADD CONSTRAINT from succeeding. Untested directly (see plan Task 6
    20	-- behavior 1 / spec §B2): a clean ALTER is the only available signal that this ran without error.
    21	delete from share_tokens st
    22	  where not exists (select 1 from playlists p
    23	                    where p.id = st.playlist_id and p.owner_id = st.owner_id);
    24	
    25	-- Composite (playlist_id, owner_id) — not bare playlist_id — matches videos/jobs and keeps the
    26	-- cross-tenant guarantee (a share token's owner always equals its playlist's owner). RI actions
    27	-- bypass RLS, so this cascade fires even though share_tokens is force-RLS with no authenticated
    28	-- policy — the same mechanism already relied on for videos/jobs.
    29	alter table share_tokens
    30	  add constraint share_tokens_playlist_owner_fk
    31	  foreign key (playlist_id, owner_id) references playlists(id, owner_id) on delete cascade;
    32	
    33	-- Cascade deletes scan children by playlist_id; index it.
    34	create index if not exists share_tokens_playlist_id_idx on share_tokens (playlist_id);
    35	
    36	-- Cancel ALL non-terminal jobs (any job_kind) for a playlist. Mirrors request_cancel_job (0010)
    37	-- but scoped to a whole playlist; owner-guarded via auth.uid() (no separate ownership check
    38	-- needed — the WHERE clause itself is the guard, same pattern as 0010).
    39	-- SECURITY DEFINER hardening: schema-qualify the bare table ref (`public.jobs`) and pin
    40	-- search_path to `public, pg_temp` (pg_temp last) — this closes the classic SECURITY DEFINER
    41	-- search_path hijack where a session-local temp object shadows an unqualified name earlier in
    42	-- the path. The `service_role` grant below is inert on its own: auth.uid() is null with no
    43	-- end-user JWT, so a bare service_role caller cancels 0 rows (owner_id = auth.uid() never
    44	-- matches) — it exists only for grant-symmetry with the session client, same as 0010.
    45	create or replace function request_cancel_playlist_jobs(p_playlist_id uuid) returns int
    46	  language plpgsql security definer set search_path = public, pg_temp as $$
    47	declare n int;
    48	begin
    49	  update public.jobs
    50	     set cancel_requested = true,
    51	         status = case when status = 'queued' then 'cancelled' else status end,
    52	         updated_at = now()
    53	   where playlist_id = p_playlist_id
    54	     and owner_id = auth.uid()
    55	     and status in ('queued','active');
    56	  get diagnostics n = row_count;
    57	  return n;
    58	end $$;
    59	revoke all on function request_cancel_playlist_jobs(uuid) from public;
    60	grant execute on function request_cancel_playlist_jobs(uuid) to authenticated, service_role;

exec
/bin/bash -lc "nl -ba app/api/playlists/[id]/route.ts | sed -n '50,90p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
    50	
    51	  try {
    52	    // Pre-delete read (404 source, NOT the delete rowcount — a delete on a foreign/missing id
    53	    // is a 0-row no-op, not an error). RLS confines this to the caller's own rows. Also
    54	    // captures playlist_key BEFORE the DB delete, for the blob Principal below.
    55	    const { data: row, error: readError } = await supabase
    56	      .from('playlists').select('id, playlist_key').eq('id', id).maybeSingle();
    57	    if (readError) throw readError;
    58	    if (!row) return json({ error: 'not found' }, 404);
    59	
    60	    const principal = getPrincipalFromSession({ userId: user.id }, row.playlist_key as string);
    61	    const bundle = getStorageBundle({ supabaseClient: supabase });
    62	    const queue = bundle.jobQueue; // optional on StorageBundle; the cloud branch guarantees it
    63	    if (!queue) return json({ error: 'unsupported' }, 500);
    64	
    65	    // Best-effort cancel-first (all kinds, via request_cancel_playlist_jobs): a failure here
    66	    // must not block the delete — the cascade below removes the job rows regardless.
    67	    try {
    68	      await queue.requestCancelPlaylist(id);
    69	    } catch (e) {
    70	      console.error(`DELETE /api/playlists/${id}: cancel-first failed (continuing)`, e);
    71	    }
    72	
    73	    // Commit point: DB delete cascades videos/jobs/share_tokens (0019 FKs).
    74	    await bundle.metadataStore.deletePlaylist(principal, id);
    75	
    76	    // Best-effort blob cleanup AFTER the DB delete — a failure here still returns 200
    77	    // (invisible orphans accepted, spec §D5).
    78	    try {
    79	      await bundle.blobStore.deletePrefix(principal, '');
    80	    } catch (e) {
    81	      console.error(`DELETE /api/playlists/${id}: blob cleanup failed (invisible orphan accepted)`, e);
    82	    }
    83	
    84	    return json({ deleted: true }, 200);
    85	  } catch (err) {
    86	    logError(`playlists:delete:${id}`, err);   // never swallow the delete's real failure
    87	    return json({ error: 'internal error' }, 500);
    88	  }
    89	}

codex
**Blocking**

1. Failure does not mean “no real spend”; the spec can under-count real money.
Refs: spec §3/§5 [design.md:47](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-15-reservation-release-lifecycle-design.md:47), runner [worker-runner.ts:53](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/job-queue/worker-runner.ts:53), [worker-runner.ts:62](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/job-queue/worker-runner.ts:62).

Scenario: job reserves 150 cents. Handler successfully calls Gemini and spends real money, then `persist_summary`/blob write/DB write throws. `runOnce` catches any generic error and calls `fail_job(... retryable: true)`. With `max_attempts = 1`, `fail_job` terminalizes as `dead_letter`. Proposed release credits 150 and zeros `jobs.reserved_cents`. Ledger says 0, but real spend happened. Repeat this 100 times: the daily fuse admits far more real spend than intended.

Fix: do not infer charge disposition from `complete_job` vs `fail_job`. The handler needs an explicit accounting outcome, or at least phase-aware failure classification: release only failures that occurred before the billable provider call began, or keep failures after provider invocation unless actual-cost settlement is implemented.

2. Serve release marker is not per-attempt idempotent; double release can refund kept successes.
Refs: spec §6 [design.md:107](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-15-reservation-release-lifecycle-design.md:107), [design.md:110](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-15-reservation-release-lifecycle-design.md:110), behavior 15 [design.md:150](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-15-reservation-release-lifecycle-design.md:150).

Scenario: same doc materializes successfully once: ledger +6, `serve_model_charge.reserved_cents = 6` per proposed marker, success keeps and does not clear marker. Later a drift/version regeneration reserves again and fails: marker becomes 12, release decrements to 6 and ledger returns to +6. A duplicate release call for that same failed attempt sees marker still `>= 6`, decrements again, and ledger becomes 0 even though the first successful cached artifact was kept. That is real under-count/overspend.

Fix: marker must represent only the currently releasable reservation, not cumulative kept charges. Add a per-reservation token/day returned by reserve and required by release, or add a success-settle RPC that clears the releasable marker on success. `release_serve_model` must be idempotent for one reservation, not merely bounded by a cumulative counter.

3. Serve day handling can release the wrong day’s concurrent reservation.
Refs: spec §6 [design.md:126](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-15-reservation-release-lifecycle-design.md:126), current reserve day [0014_serve_owner_budget.sql:48](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0014_serve_owner_budget.sql:48).

Scenario: request A reserves doc at 23:59:59 UTC on day X. At 00:00:05, request B reserves the same doc on day Y. A then fails and calls proposed `release_serve_model`, which derives `v_day = now()` and targets day Y. It can decrement B’s day-Y marker/global counter while B later succeeds. Ledger day Y under-counts B’s kept artifact; day X leaks A’s failed reservation.

Fix: reserve must return, or persist, the reservation day and a reservation token. Release must target that exact reservation, not `now()`.

4. Playlist delete/cancel path is missing and can permanently leak queued/active job reservations.
Refs: unmentioned function [0019_share_tokens_cascade.sql:45](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0019_share_tokens_cascade.sql:45), delete flow [route.ts:65](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/app/api/playlists/[id]/route.ts:65), cascade delete [route.ts:73](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/app/api/playlists/[id]/route.ts:73).

Scenario: enqueue three queued jobs at 150 cents each: ledger = 450, each job has `reserved_cents = 150`. User deletes playlist. `request_cancel_playlist_jobs` sets queued jobs to `cancelled` but the spec does not add release there. Then playlist delete cascades the job rows away. The only per-job release hook is gone; ledger remains 450 until midnight. With current defaults, this self-DoSes the system for the day.

Active jobs are worse: cancel-first only sets `cancel_requested = true`; immediate cascade can delete the active rows before `fail_job` or `complete_job` runs.

Fix: include `request_cancel_playlist_jobs` and hard-delete mechanics in the money spec. The delete flow needs an atomic release of non-terminal job reservations before rows are deleted, or a DB-side delete RPC/trigger that releases reservations while the rows still exist.

**High**

5. `greatest(0, ...)` masks accounting corruption and can hide over-release.
Refs: spec §4 [design.md:66](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-15-reservation-release-lifecycle-design.md:66), §8 [design.md:158](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-15-reservation-release-lifecycle-design.md:158).

Scenario: ledger row has 100 due to a prior bug/manual repair, but a terminal job has `reserved_cents = 150`. Proposed release clamps ledger to 0 and zeros the job. The system silently loses evidence that 50 cents were mis-accounted. Same pattern can hide the serve double-release bug above.

Fix: use conditional updates like `where reserved_cents >= amount`; if not found, raise or write an audit/error row and do not zero the source marker. If availability is more important than raising, at minimum log a structured invariant violation before zeroing.

6. Reaper release is underspecified for multi-row bulk updates.
Refs: current sweep bulk update [0009_job_playlist_identity_and_worker_persistence.sql:68](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:68), spec release sketch [design.md:83](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-15-reservation-release-lifecycle-design.md:83).

Scenario: sweep expires multiple jobs from different UTC reservation days. If implementation does `update jobs set reserved_cents = 0 returning reserved_cents`, it returns new zero values and releases nothing. If it updates ledger per row after zeroing without capturing old values, same leak. If it releases before zeroing and the later job update fails, the transaction protects it, but the spec does not state the required CTE shape.

Fix: require a CTE that locks expired rows, computes terminal status, captures old `reserved_cents` and reservation day, updates jobs to zero terminal rows, then releases grouped sums by day in the same statement/transaction.

**Medium**

7. Behavior table omits real terminal/delete cases and overstates idempotency.
Refs: behaviors [design.md:134](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-15-reservation-release-lifecycle-design.md:134).

Missing rows: provider-call-succeeded but persist failed; queued/active playlist deletion; serve spanning UTC midnight; serve success followed by failed rematerialization and duplicate release; release when ledger/budget row is missing or below release amount.

Fix: add these rows as required tests. The current 17-row table would pass while still allowing both self-DoS and overspend.

**Verdict**

Not converged. Must fix Blocking items 1-4 before this is mergeable; items 2 and 3 require a different serve reservation identity model, not just more tests.
tokens used
52,996
**Blocking**

1. Failure does not mean “no real spend”; the spec can under-count real money.
Refs: spec §3/§5 [design.md:47](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-15-reservation-release-lifecycle-design.md:47), runner [worker-runner.ts:53](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/job-queue/worker-runner.ts:53), [worker-runner.ts:62](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/job-queue/worker-runner.ts:62).

Scenario: job reserves 150 cents. Handler successfully calls Gemini and spends real money, then `persist_summary`/blob write/DB write throws. `runOnce` catches any generic error and calls `fail_job(... retryable: true)`. With `max_attempts = 1`, `fail_job` terminalizes as `dead_letter`. Proposed release credits 150 and zeros `jobs.reserved_cents`. Ledger says 0, but real spend happened. Repeat this 100 times: the daily fuse admits far more real spend than intended.

Fix: do not infer charge disposition from `complete_job` vs `fail_job`. The handler needs an explicit accounting outcome, or at least phase-aware failure classification: release only failures that occurred before the billable provider call began, or keep failures after provider invocation unless actual-cost settlement is implemented.

2. Serve release marker is not per-attempt idempotent; double release can refund kept successes.
Refs: spec §6 [design.md:107](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-15-reservation-release-lifecycle-design.md:107), [design.md:110](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-15-reservation-release-lifecycle-design.md:110), behavior 15 [design.md:150](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-15-reservation-release-lifecycle-design.md:150).

Scenario: same doc materializes successfully once: ledger +6, `serve_model_charge.reserved_cents = 6` per proposed marker, success keeps and does not clear marker. Later a drift/version regeneration reserves again and fails: marker becomes 12, release decrements to 6 and ledger returns to +6. A duplicate release call for that same failed attempt sees marker still `>= 6`, decrements again, and ledger becomes 0 even though the first successful cached artifact was kept. That is real under-count/overspend.

Fix: marker must represent only the currently releasable reservation, not cumulative kept charges. Add a per-reservation token/day returned by reserve and required by release, or add a success-settle RPC that clears the releasable marker on success. `release_serve_model` must be idempotent for one reservation, not merely bounded by a cumulative counter.

3. Serve day handling can release the wrong day’s concurrent reservation.
Refs: spec §6 [design.md:126](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-15-reservation-release-lifecycle-design.md:126), current reserve day [0014_serve_owner_budget.sql:48](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0014_serve_owner_budget.sql:48).

Scenario: request A reserves doc at 23:59:59 UTC on day X. At 00:00:05, request B reserves the same doc on day Y. A then fails and calls proposed `release_serve_model`, which derives `v_day = now()` and targets day Y. It can decrement B’s day-Y marker/global counter while B later succeeds. Ledger day Y under-counts B’s kept artifact; day X leaks A’s failed reservation.

Fix: reserve must return, or persist, the reservation day and a reservation token. Release must target that exact reservation, not `now()`.

4. Playlist delete/cancel path is missing and can permanently leak queued/active job reservations.
Refs: unmentioned function [0019_share_tokens_cascade.sql:45](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0019_share_tokens_cascade.sql:45), delete flow [route.ts:65](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/app/api/playlists/[id]/route.ts:65), cascade delete [route.ts:73](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/app/api/playlists/[id]/route.ts:73).

Scenario: enqueue three queued jobs at 150 cents each: ledger = 450, each job has `reserved_cents = 150`. User deletes playlist. `request_cancel_playlist_jobs` sets queued jobs to `cancelled` but the spec does not add release there. Then playlist delete cascades the job rows away. The only per-job release hook is gone; ledger remains 450 until midnight. With current defaults, this self-DoSes the system for the day.

Active jobs are worse: cancel-first only sets `cancel_requested = true`; immediate cascade can delete the active rows before `fail_job` or `complete_job` runs.

Fix: include `request_cancel_playlist_jobs` and hard-delete mechanics in the money spec. The delete flow needs an atomic release of non-terminal job reservations before rows are deleted, or a DB-side delete RPC/trigger that releases reservations while the rows still exist.

**High**

5. `greatest(0, ...)` masks accounting corruption and can hide over-release.
Refs: spec §4 [design.md:66](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-15-reservation-release-lifecycle-design.md:66), §8 [design.md:158](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-15-reservation-release-lifecycle-design.md:158).

Scenario: ledger row has 100 due to a prior bug/manual repair, but a terminal job has `reserved_cents = 150`. Proposed release clamps ledger to 0 and zeros the job. The system silently loses evidence that 50 cents were mis-accounted. Same pattern can hide the serve double-release bug above.

Fix: use conditional updates like `where reserved_cents >= amount`; if not found, raise or write an audit/error row and do not zero the source marker. If availability is more important than raising, at minimum log a structured invariant violation before zeroing.

6. Reaper release is underspecified for multi-row bulk updates.
Refs: current sweep bulk update [0009_job_playlist_identity_and_worker_persistence.sql:68](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:68), spec release sketch [design.md:83](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-15-reservation-release-lifecycle-design.md:83).

Scenario: sweep expires multiple jobs from different UTC reservation days. If implementation does `update jobs set reserved_cents = 0 returning reserved_cents`, it returns new zero values and releases nothing. If it updates ledger per row after zeroing without capturing old values, same leak. If it releases before zeroing and the later job update fails, the transaction protects it, but the spec does not state the required CTE shape.

Fix: require a CTE that locks expired rows, computes terminal status, captures old `reserved_cents` and reservation day, updates jobs to zero terminal rows, then releases grouped sums by day in the same statement/transaction.

**Medium**

7. Behavior table omits real terminal/delete cases and overstates idempotency.
Refs: behaviors [design.md:134](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-07-15-reservation-release-lifecycle-design.md:134).

Missing rows: provider-call-succeeded but persist failed; queued/active playlist deletion; serve spanning UTC midnight; serve success followed by failed rematerialization and duplicate release; release when ledger/budget row is missing or below release amount.

Fix: add these rows as required tests. The current 17-row table would pass while still allowing both self-DoS and overspend.

**Verdict**

Not converged. Must fix Blocking items 1-4 before this is mergeable; items 2 and 3 require a different serve reservation identity model, not just more tests.
