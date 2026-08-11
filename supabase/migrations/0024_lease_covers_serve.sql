-- 0024_lease_covers_serve.sql
--
-- The serve path's bounded work is a static sum (lib/serve-budget.ts). This constraint makes
-- "the work fits the lease" true at CONFIGURATION time, once, for every request forever —
-- rather than negotiated per request. See the spec §3.3.
--
-- 161 = SERVE_FLOOR_SECONDS = ceil((140_400 enforced + 20_000 margin) / 1000).
-- Pinned by tests/integration/serve-config-invariant.test.ts, which asserts EVERY floor literal in
-- this file — a literal here cannot import the constant, and pinning only the CHECK would let a
-- retune edit one line and leave the fix-up below stranded at the old value (round-1 review M2).
--
-- The floor 0012 shipped was one second: a lease that short was legal, which is why the app could
-- never assume the lease covered its work. If it did not, the reclaim clause in
-- reserve_serve_model admits a SECOND PAID PRODUCER — two charges, one document.

do $$
declare
  v_name text;
  v_count int;
begin
  -- Drop every pre-existing LOWER-BOUND check on lease_ttl_seconds, not just the first: `select
  -- conname into v_name` would silently take one row and raise TOO_MANY_ROWS on a partially-applied
  -- schema.
  --
  -- Matched on `>=` rather than on the column name alone (round-1 review, both reviewers). A
  -- substring match on '%lease_ttl_seconds%' also drops constraints this migration has no business
  -- touching — an operator's upper bound (`lease_ttl_seconds <= 3600`), or a multi-column CHECK
  -- whose other half is unrelated — and nothing recreates them. Dropping a guard you did not author
  -- is the one thing a migration must never do silently.
  select count(*) into v_count from pg_constraint
   where conrelid = 'guardrail_config'::regclass and contype = 'c'
     and pg_get_constraintdef(oid) ~* 'lease_ttl_seconds[[:space:]]*>=';
  if v_count > 1 then
    raise warning 'dropping % pre-existing lease_ttl_seconds lower-bound checks', v_count;
  end if;
  for v_name in
    select conname from pg_constraint
     where conrelid = 'guardrail_config'::regclass and contype = 'c'
       and pg_get_constraintdef(oid) ~* 'lease_ttl_seconds[[:space:]]*>='
  loop
    execute format('alter table guardrail_config drop constraint %I', v_name);
  end loop;
end $$;

-- FIX UP EXISTING ROWS BEFORE CONSTRAINING THEM. `add constraint` VALIDATES what is already in the
-- table, so on any database whose lease was ever tuned below the new floor this migration would be
-- unrunnable — a deploy-blocker, not a local annoyance. Measured: the local stack sat at 30 and
-- refused the migration outright.
--
-- Raising to the floor is the correct repair, not a workaround. A lease shorter than the work was
-- never safe: it is precisely the configuration that lets the reclaim clause admit a second paid
-- producer. There is no value below the floor worth preserving.
update guardrail_config
   set lease_ttl_seconds = 161
 where lease_ttl_seconds < 161;

-- Idempotent: the loop above removes our own constraint if the migration is re-applied.
alter table guardrail_config
  add constraint guardrail_config_lease_ttl_covers_serve check (lease_ttl_seconds >= 161);
