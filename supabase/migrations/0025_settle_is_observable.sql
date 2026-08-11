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
-- not a rule. The body below is byte-identical to 0020_reservation_release.sql:268-298 apart from
-- the marked insert — verified by diffing the two, not by intending it.
--
-- LIMIT OF THE DURABILITY CLAIM, stated because an overclaimed guarantee is worse than a known gap
-- (round-4 review). 0020:21 says ledger_audit has "no policies → no session-client access at all".
-- That is true for SELECT/INSERT/UPDATE/DELETE and FALSE for TRUNCATE: RLS does not cover TRUNCATE,
-- and MEASURED on the live stack, `authenticated` and `anon` both hold the TRUNCATE privilege — on
-- this table AND on spend_ledger, serve_owner_budget, serve_model_charge and guardrail_config. It
-- is a Supabase platform default for `public`, not something this migration introduces, and it is
-- not reachable through PostgREST (which exposes no TRUNCATE verb). Recorded as backlog #30 as a
-- money-table-wide revoke, because hardening only the table this migration happens to touch would
-- be the instance-not-class error three rounds of this review were spent correcting.
-- So: the witness is durable against every access path the application actually exposes, and not
-- against a direct-SQL session holding one of those roles.

-- The lookup this exists to serve is "did THIS token settle?" — `kind = 'serve_settle' and note
-- like '<token>:%'`. Without an index that is a sequential scan over every audit row ever written,
-- and an operator instruction nobody can afford to follow is the same defect one layer out.
--
-- `text_pattern_ops` IS LOAD-BEARING, not a flourish. MEASURED on the live stack: with the default
-- `text_ops` opclass the planner uses the index for `kind` only and applies the prefix as a FILTER,
-- so the read still scans every serve_settle row — and there is one per paid serve, forever. With
-- `text_pattern_ops` the prefix becomes an Index Cond:
--
--   Index Cond: ((kind = 'serve_settle') AND (note ~>=~ '<token>:') AND (note ~<~ '<token>;'))
--
-- The default opclass cannot do that under a non-C collation. Caught by checking the plan rather
-- than by assuming the index would be used, which is the same "verify, don't characterise" rule
-- this review has applied to everything else.
-- LOCK NOTE (round-6 review): a plain `create index` takes a write lock for the build, and
-- `create index concurrently` cannot run inside a migration's transaction. Measured on the live
-- stack: ledger_audit is 60 rows / 48 kB, and it grows by one row per PAID serve — so the build is
-- milliseconds and the lock is not worth splitting this into a non-transactional migration. Revisit
-- if that table ever reaches a size where an exclusive build is felt.
--
-- DROP-THEN-CREATE, not `if not exists` (round-5 review M-R5-1). MEASURED: `create index if not
-- exists` on an existing name SKIPS — it never changes the opclass — so any database that applied
-- an earlier revision of this migration with the default `text_ops` would keep the unusable index
-- forever, and the fix would reach only fresh databases. The one place that needs repairing is
-- precisely the one `if not exists` cannot touch.
drop index if exists ledger_audit_kind_note_idx;
create index ledger_audit_kind_note_idx
  on ledger_audit (kind, note text_pattern_ops);

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
  -- that cleared the reservation.
  --
  -- `expected_amt` MEANS ONE THING across every kind: THE CENTS THIS ROW IS ABOUT — and note that
  -- the column is called EXPECTED, which is exactly right here. For `release_underflow` it is the
  -- amount whose guarded decrement failed. For `serve_settle` it is the amount this settle
  -- UNDERTAKES to return, 0 on a keep — written here, BEFORE the two ledger decrements below, so it
  -- is a statement of intent and not a receipt (round-5 review L-R5-1 caught an earlier draft of
  -- this comment claiming "actually returned", which the statement order makes impossible). If a
  -- decrement then fails, its own `release_underflow` row records that, and the pair reads
  -- correctly: intended here, failed there. Spelled
  -- out because this repo's own `check-sentinel-meanings` rule is that a column meaning a
  -- CONJUNCTION of things is a defect, and a reviewer reasonably read the two writers as carrying
  -- two meanings (round-4 review L-R4-3).
  --
  -- ⚠ CONSEQUENCE FOR ANY FUTURE ALARM: `sum(expected_amt) where day = …` is no longer a sum of
  -- anomalies. Routine settles are in this table now, so such an alarm MUST filter on
  -- `kind = 'release_underflow'`. That is the one thing this change makes easy to get wrong.
  --
  -- RETENTION, decided knowingly (round-4 review L-R4-2): this turns ledger_audit from an
  -- exception-only log into one row per settled serve, forever, and `service_role` holds no DELETE
  -- (`roadmap-to-launch.md`: "ledger_audit: cannot be wiped, and must not be"). At this project's
  -- scale the append-only property is worth more than the bytes — but it IS a policy change, so it
  -- is written down here rather than discovered later.
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
