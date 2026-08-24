-- supabase/migrations/0026_record_correction_spend.sql
-- Slice A (spec §5.2, decided 2026-08-24, amended same day to (b′)). ONE narrow RPC so an attended
-- correction's ACTUAL spend reaches the global ledger, bounded PER OWNER PER DAY so one account can
-- only degrade its own budget. NOT the reservation protocol — no lease, no token, no
-- pre-authorisation. Reserve/settle remains slice C (backlog #61).

-- (0) Per-owner-per-day counter. Mirrors serve_model_charge (0012:7-18): force-RLS, service_role
--     grants only, no anon/authenticated policy — writable ONLY inside the definer RPC below.
--     FK targets profiles(id), as every owner_id in this schema does.
create table correction_spend (
  owner_id uuid not null references profiles(id) on delete cascade,
  day date not null,                                        -- (now() at time zone 'utc')::date
  calls int not null default 0 check (calls >= 0),
  cents int not null default 0 check (cents >= 0),
  unique (owner_id, day)
);
alter table correction_spend enable row level security;
alter table correction_spend force row level security;
grant select, insert, update, delete on correction_spend to service_role;

-- (1) The two bounds, and they are chosen TOGETHER. What reaches the global ledger from one owner
--     is ceiling × N, so tuning either alone re-opens the hole:
--       25 × 20 = 500¢ = 100% of daily_cap_cents (0011:28) -- the original defect
--       12 ×  8 =  96¢ =  19%                              -- shipped
--     The ceiling is DERIVED: a capped correction pass costs 3¢
--     (correctionActualCents({8192+4000, 8192})), fixSummary retries twice, so the worst case is 9¢.
--     12 covers it with headroom and nothing more; the cap-soundness test asserts that cover so the
--     two cannot drift apart silently.
alter table guardrail_config
  add column correction_max_cents int not null default 12 check (correction_max_cents >= 1);
alter table guardrail_config
  add column correction_max_calls_per_owner_day int not null default 8
    check (correction_max_calls_per_owner_day >= 1);

-- (2) record_correction_spend. SECURITY DEFINER because spend_ledger and correction_spend are both
--     service_role-only and the caller is a session-scoped `authenticated` user.
--     ⚠ auth.uid() is derived INTERNALLY — owner is NEVER a parameter (0012:26-28).
create or replace function record_correction_spend(p_cents int)
  returns void language plpgsql security definer set search_path = public as $$
declare
  v_owner uuid := auth.uid();
  v_day date := (now() at time zone 'utc')::date;
  v_cap int;
  v_max_calls int;
  v_claimed int;
begin
  if v_owner is null then
    raise exception 'record_correction_spend: authentication required';
  end if;

  -- NULL IS NOT A SMALL NUMBER. Without this, `p_cents > v_cap` yields NULL, `if NULL then` is
  -- FALSE, and the row falls through to an `actual_cents int not null` violation (0011:15) the
  -- operator then has to decode. Fail with the reason, not the symptom.
  if p_cents is null then
    raise exception 'record_correction_spend: p_cents is required';
  end if;

  select correction_max_cents, correction_max_calls_per_owner_day
    into v_cap, v_max_calls
    from guardrail_config where id = true;

  -- ⚠ FAIL CLOSED ON A MISSING CONFIG ROW. This is the guard's own "what would I see if it were
  -- silently doing nothing?" case, and without this the answer is "nothing at all": no row means
  -- v_cap is NULL, every comparison below is NULL, each `if` is FALSE, and ANY amount is accepted.
  -- The guard does not fail — it evaporates. guardrail_config is a singleton seeded by 0011:36, but
  -- service_role holds DELETE on it (0011:35), and "unlikely" is not the standard for the only
  -- bound on a global money resource.
  if v_cap is null or v_max_calls is null then
    raise exception 'record_correction_spend: guardrail_config missing — refusing to record unbounded spend';
  end if;

  -- PER-CALL CEILING. Still correct, still necessary, and NOT sufficient on its own — see the
  -- header. REJECT, never clamp: a silent truncation turns an accounting bug into invisible
  -- under-reporting, and this is the only place an inflated report can be caught.
  if p_cents < 0 or p_cents > v_cap then
    raise exception 'record_correction_spend: correction spend % exceeds ceiling %', p_cents, v_cap;
  end if;

  -- PER-OWNER-PER-DAY BOUND, CHECKED BEFORE THE GLOBAL LEDGER IS TOUCHED.
  -- Conditional-UPDATE arbiter, exactly as reserve_serve_model claims its lease (0012:59-66): the
  -- predicate lives in the `where` of the DO UPDATE and the verdict is row_count. A `select` then
  -- an `if` would let two concurrent presses both read calls = N-1 and both proceed.
  -- The INSERT path is unconditional, so call 1 always lands; the UPDATE fires while calls < N.
  -- Exactly N succeed and the (N+1)th claims nothing.
  insert into correction_spend (owner_id, day, calls, cents)
    values (v_owner, v_day, 1, p_cents)
  on conflict (owner_id, day) do update
    set calls = correction_spend.calls + 1,
        cents = correction_spend.cents + excluded.cents
    where correction_spend.calls < v_max_calls;
  get diagnostics v_claimed = row_count;

  if v_claimed = 0 then
    raise exception 'record_correction_spend: owner daily correction limit % reached', v_max_calls;
  end if;

  -- Only now the GLOBAL ledger. NO IDEMPOTENCY TOKEN, deliberately: this records spend that ALREADY
  -- happened, so a duplicate over-reports rather than double-charging, and over-count is the safe
  -- direction. (insert-then-conditional-update mirrors 0012:85-88.)
  insert into spend_ledger (day) values (v_day) on conflict do nothing;
  update spend_ledger
     set actual_cents = actual_cents + p_cents, updated_at = now()
   where day = v_day;
end $$;

-- (3) GRANTS. `revoke ... from public` removes the PUBLIC pseudo-role and NOT the named role `anon`
--     — Supabase grants anon EXECUTE at CREATE FUNCTION time via pg_default_acl, so the explicit
--     anon revoke is load-bearing, not decoration. Measured on prod 2026-08-11 (backlog #33):
--     26 of 30 public functions were anon-executable exactly because that line was omitted.
--     (reserve_serve_model deliberately DOES grant anon — the share path needs it. This one does
--     not: only a signed-in owner corrects a document.)
revoke all on function record_correction_spend(int) from public;
revoke all on function record_correction_spend(int) from anon;
grant execute on function record_correction_spend(int) to authenticated;
