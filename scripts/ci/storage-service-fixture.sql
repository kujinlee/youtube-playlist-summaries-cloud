-- The two Storage-service tables that migration 0007 needs, and NOTHING else.
--
-- ⭐ WHY THIS EXISTS. CI builds the database from `public.ecr.aws/supabase/postgres`, the same image
-- the local stack runs. That image ships the roles (`anon`, `authenticated`, `service_role`,
-- `authenticator`, `supabase_admin`), the `auth`/`extensions`/`storage` SCHEMAS, and `auth.users` —
-- all measured 2026-09-13 against a bare container. What it does NOT ship is the CONTENTS of the
-- `storage` schema: those tables are created by the storage-api service at startup, and CI does not
-- run that service. Measured: bare image has ZERO relations in `storage`; the local stack has ten.
--
-- ⛔ WHY IT MATTERS, since "a bucket insert failed" sounds ignorable. `0007_storage_and_rpcs.sql`
-- opens with `insert into storage.buckets …`, so under `ON_ERROR_STOP=1` the whole file aborts —
-- and the REST of that file creates `claim_video_slot`, `reconcile_membership`, `merge_video_data`
-- and `merge_video_data_bulk` in the **public** schema, which the manifest counts. Aborting 0007
-- leaves the gates' actual subject incomplete, so this is not about storage at all.
--
-- ⚠ WHY IT IS MINIMAL RATHER THAN DUMPED. `pg_dump -t storage.buckets -t storage.objects` was tried
-- first and does NOT apply: it references `storage.buckettype`, `storage.enforce_bucket_name_length`,
-- `storage.protect_delete` and `storage.update_updated_at_column`, none of which the `-t` form
-- carries. Chasing those dependencies means re-implementing the storage service's schema from a
-- snapshot — a second implementation of someone else's contract, which drifts silently. So this file
-- is deliberately the SMALLEST thing that lets 0007 run: the columns its three storage statements
-- name, and no more.
--
-- ⛔ THE CLAIM THAT MAKES THAT SAFE, AND IT IS CHECKED RATHER THAN ASSERTED: no schema gate reads
-- `storage.*`. `m4_catalog.CATALOG_SQL` scopes EVERY query to `nspname = 'public'`.
-- ⟳ r1 LOW 2 (claude): this used to say "at every one of its six relation queries" and the real
-- number is NINE. The count is gone rather than corrected — ALL is the claim that carries weight,
-- and a hand-counted number in a comment is a stored value with no observer, which is how it was
-- wrong in the first place.
--
-- ⛔ THE FALSIFIER IS `scripts/check-storage-independence.py`, run by the CI job, and it is a SCRIPT
-- because the first version was a grep inside the workflow that SURVIVED THREE OF FIVE MUTATIONS
-- (⟳ r1 HIGH, claude) — including the realistic one: widening `nspname = 'public'` to admit
-- `storage` contains no `storage.` at all. The replacement parses with `ast` and derives its file
-- set, so a comment cannot false-fire it and a NEW gate script is covered the day it is written.
-- If it goes red, this fixture has become load-bearing and must be REPLACED by the real service
-- schema, not extended to match.
--
-- NOT a migration, and never applied to any database that matters: `supabase migration up` does not
-- see this path, and the only caller is the CI workflow.

-- ⛔ APPLIED AS `supabase_admin`, AND THE OWNER IS THEN HANDED TO `postgres`. Both halves are
-- forced, and neither is cosmetic:
--   * `storage` is owned by `supabase_admin` (measured), and `postgres` is NOT a superuser in this
--     image OR in the local stack — both report `rolsuper=false`. So `postgres` cannot create here.
--   * 0007 runs as `postgres` and calls `create policy … on storage.objects`, which requires table
--     OWNERSHIP. Leaving these owned by `supabase_admin` moves the failure one statement later.
-- ⚠ DIVERGENCE FROM THE REAL STACK, STATED: there the two tables are owned by
-- `supabase_storage_admin`, and `postgres` is not a member of it (measured on the dev container).
-- Exactly how the storage-api service applies those policies is not something this file needs to
-- answer, because no gate reads `storage.*` — see the falsifier named above. If one ever does, this
-- divergence becomes load-bearing and the fixture must be replaced, not patched.

create table if not exists storage.buckets (
    id text primary key,
    name text not null,
    public boolean default false
);

create table if not exists storage.objects (
    id uuid primary key default gen_random_uuid(),
    bucket_id text references storage.buckets (id),
    name text,
    owner uuid
);

alter table storage.buckets owner to postgres;
alter table storage.objects owner to postgres;

-- 0007 creates policies on `storage.objects`, which requires RLS to be meaningful. The real service
-- enables it; without this the policies apply to a table that never consults them, and the CI
-- database would differ from the local one in a way no gate would report.
alter table storage.objects enable row level security;
