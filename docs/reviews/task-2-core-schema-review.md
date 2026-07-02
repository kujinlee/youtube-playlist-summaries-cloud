# Task 2 Review — Core schema migration (0001_core_schema.sql)

**Reviewer:** Claude (sonnet), fresh subagent (task reviewer, SDD) — by-eye Postgres correctness (Docker down)
**Commit:** de90f1e | **Verdict:** SPEC ✅ / QUALITY approved

## Postgres correctness — all 7 checks PASS (verified by reading, migration not run)
1. **Composite FK target valid:** `playlists` has `unique (id, owner_id)` (not just PK on id) → the `videos (playlist_id, owner_id) → playlists(id, owner_id)` FK will apply cleanly (would ERROR without the explicit unique).
2. **NULL-safe CHECK:** `data->>'id' is not null and data->>'id' = video_id` rejects mismatched AND missing id (missing → `is not null` false → fails). Correct.
3. **Deferrable position:** named `constraint … unique (…) deferrable initially deferred` (constraint form, not a bare index which can't be deferrable). Reorder-within-txn works.
4. **Forced RLS:** `enable` + `force` on all three tables.
5. **PK/types/FKs:** no type mismatches (uuid/uuid, text/text), every FK targets a unique/PK column, cascades correct.
6. **Ordering:** profiles → playlists → videos, no forward refs; `gen_random_uuid()` native on Supabase PG15.
7. **Test:** `relrowsecurity`/`relforcerowsecurity` column names match the assertion; alphabetical order matches.

Additive only (0001 migration + schema.test.ts). tsc clean; default suite 1505 green (integration excluded).

## Finding (Minor — FIXED by controller)
- **`pg_class` query lacked a schema/relkind filter** on a security-relevant assertion (forced-RLS regression). → **FIXED**: added `and relnamespace = 'public'::regnamespace and relkind = 'r'` so a same-named relation in another schema can't skew the result.

No Critical/Important findings. Live `db reset` green deferred to the user's Docker.
