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
