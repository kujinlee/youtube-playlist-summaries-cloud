-- 0018_enqueue_dig.sql
-- Admit job_kind='dig' in enqueue_job. The dig quota (quota_allowance dig rows),
-- dig_est_cents, and dig_max_attempts config, plus the section_id/job_kind/job_version
-- idempotency index (jobs_idem_active), already exist (0008 + 0011). This migration only
-- relaxes the one-line kind guard; the est/attempts dispatch (case p_job_kind ... 'dig' ...)
-- is already present in the 0011 body and is preserved verbatim.
create or replace function enqueue_job(
  p_owner_id uuid, p_playlist_id uuid, p_video_id text, p_section_id int,
  p_job_kind text, p_job_version text, p_payload jsonb, p_enqueue_ip inet
) returns table(job_id uuid, status text, joined boolean)
  language plpgsql security invoker set search_path = public as $$
declare
  v_id uuid; v_status text; v_payload jsonb; v_cfg guardrail_config;
  v_est int; v_maxatt int; v_dur text; v_anon boolean; v_allow int;
  v_period date; v_day date; v_tries int := 0;
begin
  -- 0. Auth + kind gate. Primary defense is the grant (service_role only); this is belt-and-suspenders.
  if auth.role() <> 'service_role' then raise exception 'enqueue_job: server only'; end if;
  if p_owner_id is null then raise exception 'owner required'; end if;
  if p_job_kind not in ('summary','dig') then raise exception 'unsupported_job_kind'; end if;

  select * into v_cfg from guardrail_config where id = true;                          -- singleton, once
  v_est    := case p_job_kind when 'summary' then v_cfg.summary_est_cents    else v_cfg.dig_est_cents    end;
  v_maxatt := case p_job_kind when 'summary' then v_cfg.summary_max_attempts else v_cfg.dig_max_attempts end;

  loop
    v_tries := v_tries + 1;
    if v_tries > 8 then raise exception 'enqueue_job: retry limit exceeded'; end if;

    -- 1. INSERT-or-JOIN. Aliased ON CONFLICT predicate MUST textually match jobs_idem_active
    --    (0008/0009) so Postgres binds the partial unique index as the arbiter.
    insert into jobs as j (owner_id, playlist_id, video_id, section_id, job_kind, job_version, payload, enqueue_ip, max_attempts)
    values (p_owner_id, p_playlist_id, p_video_id, p_section_id, p_job_kind, p_job_version, p_payload, p_enqueue_ip, v_maxatt)
    on conflict (owner_id, playlist_id, video_id, section_id, job_kind, job_version)
      where j.status in ('queued','active','completed')
      do nothing
    returning id into v_id;

    if v_id is not null then
      -- NEW ROW → run the guardrails; any raise below rolls back this INSERT.
      -- 2. Duration backstop (robust cast; reject-not-admit for missing/malformed/over-cap).
      v_dur := (p_payload->>'durationSeconds');
      if v_dur is null or v_dur !~ '^[0-9]{1,7}(\.[0-9]{1,6})?$'   -- missing/non-numeric/over-long ⇒ reject (length-bounded so ::numeric can't blow up)
         or v_dur::numeric > v_cfg.max_duration_seconds            -- NUMERIC compare, no ::int / no floor: 1800.999999 > 1800 ⇒ PJ003
      then
        raise exception 'too_long' using errcode = 'PJ003';
      end if;

      -- 3. Atomic quota debit (per-owner, per-kind, per-UTC-month).
      select p.is_anonymous into v_anon from profiles p where p.id = p_owner_id;
      select qa.monthly into v_allow from quota_allowance qa where qa.is_anonymous = v_anon and qa.kind = p_job_kind;
      v_period := date_trunc('month', now() at time zone 'utc')::date;
      v_day    := (now() at time zone 'utc')::date;
      insert into usage_counters (owner_id, kind, period_start, used)
        values (p_owner_id, p_job_kind, v_period, 0) on conflict do nothing;
      update usage_counters set used = used + 1
        where owner_id = p_owner_id and kind = p_job_kind and period_start = v_period and used < v_allow;
      if not found then raise exception 'quota_exceeded' using errcode = 'PJ001'; end if;

      -- 4. Atomic daily reserve against the global cap (never released in 1D).
      insert into spend_ledger (day) values (v_day) on conflict do nothing;
      update spend_ledger set reserved_cents = reserved_cents + v_est, updated_at = now()
        where day = v_day and reserved_cents + actual_cents + v_est <= v_cfg.daily_cap_cents;
      if not found then raise exception 'daily_cap_exceeded' using errcode = 'PJ002'; end if;

      -- 5. Stamp the reservation on the row and return.
      update jobs set reserved_cents = v_est where id = v_id;
      return query select v_id, 'queued'::text, false; return;
    end if;

    -- CONFLICT → JOIN the existing live/completed row: NO debit, NO reserve, NO duration check.
    select j.id, j.status, j.payload into v_id, v_status, v_payload from jobs j
      where j.owner_id = p_owner_id and j.playlist_id = p_playlist_id and j.video_id = p_video_id
        and j.section_id = p_section_id and j.job_kind = p_job_kind and j.job_version = p_job_version
        and j.status in ('queued','active','completed')
      limit 1;
    if v_id is not null then
      if v_payload is distinct from p_payload then
        raise log 'enqueue_job: joined % with a divergent payload (kept existing)', v_id;
      end if;
      return query select v_id, v_status, true; return;
    end if;
    -- conflicting row went terminal (failed/cancelled) in the gap: retry the insert
  end loop;
end $$;
revoke all on function enqueue_job(uuid,uuid,text,int,text,text,jsonb,inet) from public, anon, authenticated;
grant execute on function enqueue_job(uuid,uuid,text,int,text,text,jsonb,inet) to service_role;
