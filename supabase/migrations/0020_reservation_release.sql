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
