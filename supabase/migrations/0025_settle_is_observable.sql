-- 0025_settle_is_observable.sql
--
-- WHY THIS EXISTS: three review rounds, one High each, all on the same thing.
--
--   round 1 H3     a boolean read transport success as "the settle happened"
--   round 2 H-R2-2 the fix's `false` then meant three things, and the money alarm fired on the
--                  wrong one — loudest on refunds that HAD applied
--   round 3 H-R3-1 the fix's third value (`indeterminate`) tells the operator to reconcile against
--                  ledger_audit, which by construction contains no record of a settle
--
-- Each round refined the VOCABULARY OF THE REPORT: one bit → three values → three values plus
-- guidance. None of them added the missing thing, and the missing thing is not a vocabulary.
--
-- THERE IS NO DURABLE RECORD OF WHETHER A SETTLE APPLIED. settle_serve_model mutates two counters
-- and returns a scalar; ledger_audit records only the `release_underflow` exception; and
-- serve_model_charge.release_token — the one surviving trace — is OVERWRITTEN by the next reserve
-- (0020:251-254), so it answers only inside the ~161s lease window. The client was being asked to
-- infer a permanent money fact from a transient observation it provably cannot make, and every
-- round answered that by describing the uncertainty more precisely.
--
-- `docs/review-method.md`'s escalation rule exists to force exactly this move: stop patching the
-- next instance, and dissolve the recurrence. One INSERT does it. `indeterminate` stops being an
-- unfalsifiable log and becomes a RESOLVABLE state — one read answers "did my token settle?", and a
-- future attempt could answer it in code rather than guessing.
--
-- Note what this does NOT change: the settle's money semantics are untouched. This adds a witness,
-- not a rule.

-- The lookup this exists to serve is "did THIS token settle?", i.e. by (kind, note). Without an
-- index that read is a sequential scan over every audit row ever written, and an operator
-- instruction nobody can afford to follow is the same defect one layer out.
create index if not exists ledger_audit_kind_note_idx on ledger_audit (kind, note);

-- Body reproduced from 0020_reservation_release.sql:268-298 with ONE addition, marked below.
-- Reproduced rather than patched because Postgres has no "add a statement to a function"; the rest
-- must stay byte-identical, and the money rules in it are unchanged.
create or replace function settle_serve_model(p_token uuid, p_released boolean)
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

  -- ── THE ADDITION: a durable witness that THIS token settled. ──────────────────────────────────
  -- Written only past the `not found` gate, so the row exists if and only if this call is the one
  -- that cleared the reservation. `expected_amt` carries the refunded amount (0 on a keep) so the
  -- row is self-describing without a join.
  insert into ledger_audit(day, kind, expected_amt, note, at)
    values (v_day, 'serve_settle',
            case when p_released then v_cfg.magazine_est_cents else 0 end,
            p_token::text || ':' || p_released::text, now());

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
