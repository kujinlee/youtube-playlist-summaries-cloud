-- supabase/migrations/0028_correction_allowance.sql
-- Backlog #62, round 1 fold. 0026's per-owner-per-day limit bounds what is WRITTEN to the ledger,
-- not what is SPENT: nothing read `correction_spend` before the paid call, so from press N+1 on
-- Gemini was billed and record_correction_spend refused the bookkeeping. This is the READ the
-- route makes before any paid call, so it can refuse the press instead.
--
-- ⚠ A CHECK, NOT A RESERVATION. Two concurrent presses at calls = N-1 both read "one left" and both
-- proceed, so the bound is N + concurrency, not N. Closing that needs reserve/settle — backlog #61.
-- Nothing is claimed here: this function writes nothing.
--
-- ⚠ DEPLOY ORDER: apply this BEFORE the code that calls it. The route fails CLOSED when this RPC
-- errors (no paid call without a readable allowance), so code-first refuses every correction.

-- correction_spend and guardrail_config are service_role-only (0026:17-19, 0011), so a session-scoped
-- `authenticated` caller can read neither. SECURITY DEFINER, owner derived INTERNALLY from
-- auth.uid() — never a parameter (0026:37) — so a caller can read only their own count.
create function correction_allowance()
  returns jsonb language plpgsql stable security definer set search_path = public as $$
declare
  v_owner uuid := auth.uid();
  v_cap int;
  v_max_calls int;
  v_calls int;
begin
  if v_owner is null then
    raise exception 'correction_allowance: authentication required';
  end if;

  select correction_max_cents, correction_max_calls_per_owner_day
    into v_cap, v_max_calls
    from guardrail_config where id = true;
  -- FAIL CLOSED on a missing config row, for the same reason as 0026:62-70: a NULL limit would
  -- otherwise read as "no limit" to the caller.
  if v_cap is null or v_max_calls is null then
    raise exception 'correction_allowance: guardrail_config missing';
  end if;

  select cs.calls into v_calls
    from correction_spend cs
   where cs.owner_id = v_owner and cs.day = (now() at time zone 'utc')::date;

  return jsonb_build_object(
    'calls', coalesce(v_calls, 0),          -- no row today means no press recorded today
    'max_calls', v_max_calls,
    'max_cents', v_cap
  );
end $$;

-- GRANTS — same three lines as 0026:107-109, for the same measured reason: `revoke ... from public`
-- does not remove the named role `anon`, which Supabase grants EXECUTE at create time.
revoke all on function correction_allowance() from public;
revoke all on function correction_allowance() from anon;
grant execute on function correction_allowance() to authenticated;
