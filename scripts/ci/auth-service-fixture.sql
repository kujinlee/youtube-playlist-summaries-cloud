-- The `auth.users` columns our own code reads, which the database image does not ship.
--
-- ⭐ WHY. `public.ecr.aws/supabase/postgres` ships the `auth` schema AND `auth.users` — but the
-- table it ships is the base shape. GoTrue's own migrations, run by the auth SERVICE, add columns
-- over time, and CI does not run that service. MEASURED 2026-09-13, column counts:
--
--     local stack (GoTrue has run)   35 columns
--     bare image                     21 columns
--     missing in CI                  14
--     ...of which OUR code reads      1   -> `is_anonymous`
--
-- ⛔ IT IS LOAD-BEARING, UNLIKE THE STORAGE FIXTURE. `public.handle_new_user()` is a trigger on
-- `auth.users` and reads `coalesce(new.is_anonymous, false)`; without the column, gate 8
-- (`run-schema-assertions.sh`) dies with `record "new" has no field "is_anonymous"` while seeding
-- its corpus. So this file is not a convenience — the behavioural half of the suite cannot run
-- without it.
--
-- ⚠ WHICH MEANS THE "ONLY ONE COLUMN" CLAIM NEEDS A FALSIFIER, AND IT ALREADY HAS ONE: gate 8
-- INSERTS into `auth.users` and asserts the resulting `profiles` row. If a future migration reads
-- another GoTrue column, that gate fails in CI with the field named in the error — exactly as it
-- did here. So the check is the suite, not a new guard, and the correct response to that failure is
-- to add the column here after confirming the local stack has it.
--
-- ⚠ The other 13 are deliberately NOT added. Adding columns nothing reads would make this file a
-- second, drifting copy of GoTrue's schema — the failure mode the storage fixture's header
-- describes. One column, one reason, one falsifier.
--
-- NOT a migration: `supabase migration up` never sees this path, and the only caller is
-- `scripts/ci/start-schema-db.sh`.

-- PART 1 — the missing COLUMN.
alter table auth.users add column if not exists is_anonymous boolean not null default false;

-- ══════════════════════════════════════════════════════════════════════════════════════════════
-- PART 2 — the `auth` HELPER FUNCTIONS, which the image ships in an OLDER FORM than the platform.
--
-- ⛔ THIS IS THE ONE THAT SILENTLY WEAKENS RLS, so read the mechanism before touching it. MEASURED
-- 2026-09-13: the bare image defines
--
--     auth.uid() := select nullif(current_setting('request.jwt.claim.sub', true), '')::uuid
--
-- which reads ONLY the legacy singular GUC. The platform (and the local stack) define it as a
-- COALESCE that also reads the `request.jwt.claims` JSON. PostgREST sets the JSON form, and so do
-- this repo's own assertions:
--
--     perform set_config('request.jwt.claims', json_build_object('sub', me::text)::text, true);
--     set local role authenticated;                          -- 05_assert.sql:784-785
--
-- So on the bare image `auth.uid()` returns NULL for a caller who IS authenticated, every
-- owner-scoped policy evaluates false, and the suite fails with
-- `ASSERTION FAILED — the OWNER cannot read their own manifest`. Three gates (1, 2 and 8) die on
-- that single line.
--
-- ⚠ FIXED FOR ALL FOUR HELPERS, NOT JUST THE ONE THAT FAILED. `auth.role()`, `auth.jwt()` and
-- `auth.email()` differ between image and stack in the same way; fixing only `uid` would have
-- meant meeting the next one as a fresh failure two gates later.
-- ⟳ r1 LOW 1 (claude): this said THREE and left `auth.email()` in its legacy form — an
-- instance-shaped fix inside a paragraph claiming to have closed the class, which is this
-- session's most repeated defect. Nothing in the repo calls `auth.email()` TODAY (grepped:
-- zero hits in migrations and in the M4 spec), so it was latent rather than live: the first
-- policy to use it would have failed in CI only, and read as a CI problem rather than a
-- fixture gap. Included now because the class is 'every auth helper the image ships legacy',
-- not 'the ones something happens to call'.
--
-- ⛔ THE RISK, STATED PLAINLY BECAUSE IT RUNS THE WRONG WAY. A fixture that made `auth.uid()` MORE
-- permissive than production would turn CI green while prod stays broken — the worst direction for
-- a test double. Two things bound it: (a) these bodies are COPIED VERBATIM from the running stack
-- via `pg_get_functiondef`, never retyped or reasoned out; (b) they are strictly a SUPERSET-READER
-- of the image's version — the legacy GUC is still the first branch of the coalesce, so nothing
-- that resolved before stops resolving.
--
-- ⚠ ITS FALSIFIER IS THE SUITE ITSELF, and it already fired once: gate 8's owner-read assertion is
-- precisely the thing that detects a broken `auth.uid()`. If the platform changes these helpers,
-- re-derive them with:
--
--     docker exec -i <stack> psql -U postgres -tAc "select pg_get_functiondef('auth.uid'::regproc);"
--
-- ⚠ `create or replace` — deliberately NOT `create if not exists`. The image HAS these functions;
-- the point is to replace an older body, so a form that skipped existing ones would be a silent
-- no-op and this whole file would do nothing while appearing to work.

CREATE OR REPLACE FUNCTION auth.uid()
 RETURNS uuid
 LANGUAGE sql
 STABLE
AS $function$
  select 
  coalesce(
    nullif(current_setting('request.jwt.claim.sub', true), ''),
    (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'sub')
  )::uuid
$function$;

CREATE OR REPLACE FUNCTION auth.role()
 RETURNS text
 LANGUAGE sql
 STABLE
AS $function$
  select 
  coalesce(
    nullif(current_setting('request.jwt.claim.role', true), ''),
    (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'role')
  )::text
$function$;

CREATE OR REPLACE FUNCTION auth.jwt()
 RETURNS jsonb
 LANGUAGE sql
 STABLE
AS $function$
  select 
    coalesce(
        nullif(current_setting('request.jwt.claim', true), ''),
        nullif(current_setting('request.jwt.claims', true), '')
    )::jsonb
$function$;

CREATE OR REPLACE FUNCTION auth.email()
 RETURNS text
 LANGUAGE sql
 STABLE
AS $function$
  select 
  coalesce(
    nullif(current_setting('request.jwt.claim.email', true), ''),
    (nullif(current_setting('request.jwt.claims', true), '')::jsonb ->> 'email')
  )::text
$function$;
