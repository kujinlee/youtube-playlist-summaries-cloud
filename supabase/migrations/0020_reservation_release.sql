-- 0020_reservation_release.sql
-- Reserve→release lifecycle for spend_ledger. Money path — see
-- docs/superpowers/specs/2026-07-15-reservation-release-lifecycle-design.md (v7).
-- Built up across plan Tasks 1–5. Order matters: ledger_audit (this task) must precede
-- every function that inserts into it (Tasks 2–5).

-- ── Task 1: ledger_audit ────────────────────────────────────────────────────
-- In-band invariant-violation signal for a guarded decrement that would go negative.
-- Locked down exactly like spend_ledger (0011:17-18): force RLS + NO policy blocks
-- anon/authenticated entirely; service_role has BYPASSRLS (0006_grants.sql) but that does
-- NOT bypass table GRANTs, so the explicit grant below is required, not optional.
create table ledger_audit (
  id            bigint generated always as identity primary key,
  day           date        not null,
  kind          text        not null,   -- e.g. 'release_underflow'
  expected_amt  int         not null,
  note          text,
  at            timestamptz not null default now()
);
alter table ledger_audit enable row level security;
alter table ledger_audit force  row level security;   -- no policies → no session-client access at all
grant select, insert on ledger_audit to service_role;  -- the ONLY grant; mirrors spend_ledger

-- ── Task 2: fail_job — DROP+recreate 6-arg with spend-aware release ──────────
-- Adding p_billable_succeeded changes the arg count (5→6). A bare create-or-replace would
-- leave the 5-arg overload alongside → the adapter's named-arg call resolves ambiguously
-- (the BUG-1 footgun). So DROP the 5-arg version, recreate, and re-grant the 6-arg signature.
drop function fail_job(uuid,text,uuid,text,boolean);

create function fail_job(
    p_job_id uuid, p_worker_id text, p_lease_token uuid, p_error text,
    p_retryable boolean, p_billable_succeeded boolean default true)   -- default TRUE = conservative KEEP
  returns text language plpgsql security invoker set search_path = public as $$
declare
  v_attempts int; v_max int; v_cancel boolean; v_new text; v_backoff bigint;
  v_created_at timestamptz; v_reserved int;
begin
  if auth.role() <> 'service_role' then raise exception 'workers only'; end if;
  select attempts, max_attempts, cancel_requested, created_at, reserved_cents
    into v_attempts, v_max, v_cancel, v_created_at, v_reserved
    from jobs
    where id = p_job_id and locked_by = p_worker_id and lease_token = p_lease_token and status = 'active'
    for update;
  if not found then return null; end if;            -- lost lease
  if v_cancel then v_new := 'cancelled';
  elsif not p_retryable then v_new := 'failed';
  elsif v_attempts >= v_max then v_new := 'dead_letter';
  else v_new := 'queued';
  end if;
  v_backoff := (10 * power(4, least(greatest(v_attempts - 1, 0), 15)))::bigint;
  update jobs set status = v_new, error = p_error,
       run_after = case when v_new = 'queued' then now() + make_interval(secs => v_backoff) else run_after end,
       locked_by = null, lease_token = null, lease_expires_at = null, updated_at = now()
  where id = p_job_id and locked_by = p_worker_id and lease_token = p_lease_token and status = 'active';

  -- Spend-aware release: only a genuine terminal fail that never billed. NOT 'queued' (retry
  -- reuses the reservation — behavior 6). Inside the status='active' single-writer fence → exactly-once.
  if not p_billable_succeeded
     and v_new in ('failed','dead_letter','cancelled')
     and v_reserved > 0 then
    update spend_ledger
       set reserved_cents = reserved_cents - v_reserved, updated_at = now()
     where day = (v_created_at at time zone 'utc')::date
       and reserved_cents >= v_reserved;                -- guarded decrement, never silent clamp
    if not found then
      insert into ledger_audit(day, kind, expected_amt, note, at)
        values ((v_created_at at time zone 'utc')::date, 'release_underflow', v_reserved,
                'fail_job '||p_job_id::text, now());
    end if;
    update jobs set reserved_cents = 0 where id = p_job_id;   -- belt-and-suspenders (fence is primary)
  end if;
  return v_new;
end $$;
revoke all on function fail_job(uuid,text,uuid,text,boolean,boolean) from public;
grant execute on function fail_job(uuid,text,uuid,text,boolean,boolean) to service_role;

-- ── Task 3: request_cancel_job — procedural, releases a genuine queued cancel ─
-- Same signature (uuid → int) so create-or-replace preserves grants. Procedural because we
-- must (a) pre-read OLD reserved_cents before zeroing (PG<18 RETURNING is post-update),
-- (b) audit underflow, (c) return 1 for BOTH a queued cancel and an active flag-set (H-4).
create or replace function request_cancel_job(p_job_id uuid) returns int
  language plpgsql security definer set search_path = public as $$
declare v_old_status text; v_old_amt int; v_day date;
begin
  select status, reserved_cents, (created_at at time zone 'utc')::date
    into v_old_status, v_old_amt, v_day
    from jobs
   where id = p_job_id and owner_id = auth.uid() and status in ('queued','active')
   for update;                                       -- serialize vs claim_next_job's skip-locked claim
  if not found then return 0; end if;                -- terminal / foreign / missing
  update jobs
     set cancel_requested = true,
         status         = case when v_old_status = 'queued' then 'cancelled' else status end,
         reserved_cents = case when v_old_status = 'queued' then 0 else reserved_cents end,
         updated_at     = now()
   where id = p_job_id;
  if v_old_status = 'queued' and v_old_amt > 0 then   -- RELEASE only a genuine queued→cancelled
    update spend_ledger set reserved_cents = reserved_cents - v_old_amt, updated_at = now()
     where day = v_day and reserved_cents >= v_old_amt;
    if not found then
      insert into ledger_audit(day, kind, expected_amt, note, at)
        values (v_day, 'release_underflow', v_old_amt, 'request_cancel_job '||p_job_id::text, now());
    end if;
  end if;
  return 1;                                           -- cancellation requested (queued OR active) — H-4
end $$;

-- ── Task 4: request_cancel_playlist_jobs — set-based multi-day release ────────
-- Same signature → create-or-replace (grants + search_path=public,pg_temp preserved).
-- One data-modifying CTE: flag ALL non-terminal jobs (H-2), release only the queued subset
-- grouped per reserve-day (H-3 per-day audit), return jobs-flagged count (H-4).
create or replace function request_cancel_playlist_jobs(p_playlist_id uuid) returns int
  language plpgsql security definer set search_path = public, pg_temp as $$
declare v_n int;
begin
  -- Note: a data-modifying WITH must be the top-level statement (Postgres forbids
  -- `return (with ... )` — that nests it as a scalar subquery). `... into v_n` keeps
  -- the CTE chain top-level while still capturing the H-4 count.
  with pre as (                                  -- ALL non-terminal jobs of the playlist, under lock
    select id, status as old_status, reserved_cents as old_amt,
           (created_at at time zone 'utc')::date as reserve_day
      from public.jobs                           -- schema-qualified (0019 search_path-hijack hardening — L1)
     where playlist_id = p_playlist_id and owner_id = auth.uid() and status in ('queued','active')
     for update),
  upd as (                                       -- H-2: flag ALL; flip+zero only the queued subset
    update public.jobs j
       set cancel_requested = true,
           status         = case when pre.old_status = 'queued' then 'cancelled' else j.status end,
           reserved_cents = case when pre.old_status = 'queued' then 0 else j.reserved_cents end,
           updated_at     = now()
      from pre where j.id = pre.id
     returning j.id),
  per_day as (                                   -- queued-only OLD amounts, grouped by reserve-day
    select reserve_day, sum(old_amt) as amt
      from pre where old_status = 'queued' and old_amt > 0
     group by reserve_day),
  dec as (                                       -- guarded per-day decrement; RETURNING credited days
    update spend_ledger sl
       set reserved_cents = sl.reserved_cents - per_day.amt, updated_at = now()
      from per_day
     where sl.day = per_day.reserve_day and sl.reserved_cents >= per_day.amt
     returning sl.day),
  aud as (                                       -- H-3: audit every per_day with no successful decrement
    insert into ledger_audit(day, kind, expected_amt, note, at)
    select pd.reserve_day, 'release_underflow', pd.amt,
           'request_cancel_playlist_jobs '||p_playlist_id::text, now()
      from per_day pd
     where pd.reserve_day not in (select day from dec))
  select count(*)::int into v_n from upd;          -- H-4: jobs flagged (queued + active)
  return v_n;
end $$;

-- ── Task 5: serve token + settle ─────────────────────────────────────────────
alter table serve_model_charge add column reserved_cents int not null default 0 check (reserved_cents >= 0);
alter table serve_model_charge add column release_token uuid;   -- current in-flight reservation's one-time secret

-- reserve_serve_model: return type changes (text → table) → DROP+recreate+re-grant.
-- Body identical to 0014 except it now also mints a release_token on the 'reserved' branch.
drop function reserve_serve_model(uuid, text);

create function reserve_serve_model(p_playlist_id uuid, p_video_id text)
  returns table(status text, release_token uuid)
  language plpgsql security definer set search_path = public as $$
declare
  v_owner uuid := auth.uid();
  v_cfg guardrail_config;
  v_doc_key text;
  v_day date;
  v_promoted boolean;
  v_claimed int;
  v_existing int;
  v_lease_live boolean;
  v_result text;
  v_token uuid;                                    -- null unless we reserve
begin
  if v_owner is null then raise exception 'reserve_serve_model: unauthenticated'; end if;

  select (v.data->'artifacts'->'summaryMd'->>'status') = 'promoted'
    into v_promoted
    from videos v join playlists p on p.id = v.playlist_id
    where v.playlist_id = p_playlist_id and v.video_id = p_video_id and p.owner_id = v_owner;
  if v_promoted is distinct from true then
    return query select 'denied'::text, null::uuid; return;
  end if;

  select * into v_cfg from guardrail_config where id = true;
  v_doc_key := p_playlist_id::text || '/' || p_video_id;
  v_day := (now() at time zone 'utc')::date;

  begin
    insert into serve_model_charge (owner_id, doc_key, day, lease_expires_at, attempt_count)
      values (v_owner, v_doc_key, v_day, now() + make_interval(secs => v_cfg.lease_ttl_seconds), 1)
    on conflict (owner_id, doc_key, day) do update
      set lease_expires_at = now() + make_interval(secs => v_cfg.lease_ttl_seconds),
          attempt_count = serve_model_charge.attempt_count + 1
      where serve_model_charge.lease_expires_at < now()
        and serve_model_charge.attempt_count < v_cfg.max_serve_attempts;
    get diagnostics v_claimed = row_count;

    if v_claimed = 0 then
      select attempt_count, lease_expires_at > now()
        into v_existing, v_lease_live
        from serve_model_charge
        where owner_id = v_owner and doc_key = v_doc_key and day = v_day;
      v_result := case
                    when v_lease_live then 'in_flight'
                    when v_existing >= v_cfg.max_serve_attempts then 'attempts_exhausted'
                    else 'in_flight'
                  end;
    else
      insert into serve_owner_budget (owner_id, day) values (v_owner, v_day) on conflict do nothing;
      update serve_owner_budget set spent_cents = spent_cents + v_cfg.magazine_est_cents
        where owner_id = v_owner and day = v_day
          and spent_cents + v_cfg.magazine_est_cents <= v_cfg.per_owner_serve_daily_cents;
      if not found then raise exception 'serve_owner_over_budget' using errcode = 'PJ005'; end if;

      insert into spend_ledger (day) values (v_day) on conflict do nothing;
      update spend_ledger set reserved_cents = reserved_cents + v_cfg.magazine_est_cents, updated_at = now()
        where day = v_day
          and reserved_cents + actual_cents + v_cfg.magazine_est_cents <= v_cfg.daily_cap_cents;
      if not found then raise exception 'serve_at_capacity' using errcode = 'PJ004'; end if;

      -- Mint the one-time release token for THIS live attempt (SET, not +=; single live attempt).
      v_token := gen_random_uuid();
      update serve_model_charge
         set reserved_cents = v_cfg.magazine_est_cents, release_token = v_token
       where owner_id = v_owner and doc_key = v_doc_key and day = v_day;
      v_result := 'reserved';
    end if;
  exception
    when sqlstate 'PJ005' then v_result := 'owner_over_budget'; v_token := null;
    when sqlstate 'PJ004' then v_result := 'at_capacity';       v_token := null;
  end;

  return query select v_result, v_token;
end $$;
revoke all on function reserve_serve_model(uuid, text) from public;
grant execute on function reserve_serve_model(uuid, text) to authenticated, anon;

-- settle_serve_model: match the in-flight attempt by owner+token, clear it one-shot; on
-- released=true also guarded-decrement serve_owner_budget + spend_ledger by magazine_est_cents.
create function settle_serve_model(p_token uuid, p_released boolean)
  returns boolean language plpgsql security definer set search_path = public as $$
declare
  v_owner uuid := auth.uid();
  v_cfg guardrail_config;
  v_day date;
begin
  if v_owner is null then raise exception 'settle_serve_model: unauthenticated'; end if;
  select * into v_cfg from guardrail_config where id = true;
  update serve_model_charge
     set reserved_cents = 0, release_token = null
   where owner_id = v_owner and release_token = p_token and reserved_cents >= v_cfg.magazine_est_cents
   returning day into v_day;
  if not found then return false; end if;          -- stale/duplicate/forged token → no-op (idempotent)
  if p_released then
    update serve_owner_budget set spent_cents = spent_cents - v_cfg.magazine_est_cents
     where owner_id = v_owner and day = v_day and spent_cents >= v_cfg.magazine_est_cents;
    if not found then
      insert into ledger_audit(day, kind, expected_amt, note, at)
        values (v_day, 'release_underflow', v_cfg.magazine_est_cents,
                'settle_serve_model owner_budget '||p_token::text, now());
    end if;
    update spend_ledger set reserved_cents = reserved_cents - v_cfg.magazine_est_cents, updated_at = now()
     where day = v_day and reserved_cents >= v_cfg.magazine_est_cents;
    if not found then
      insert into ledger_audit(day, kind, expected_amt, note, at)
        values (v_day, 'release_underflow', v_cfg.magazine_est_cents,
                'settle_serve_model spend_ledger '||p_token::text, now());
    end if;
  end if;
  return true;
end $$;
revoke all on function settle_serve_model(uuid, boolean) from public;
grant execute on function settle_serve_model(uuid, boolean) to authenticated, anon;
