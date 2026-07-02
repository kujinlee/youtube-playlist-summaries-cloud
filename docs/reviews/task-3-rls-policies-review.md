# Task 3 Review — RLS owner policies (0002_rls_policies.sql)

**Reviewer:** Claude (sonnet), fresh subagent — by-eye Postgres correctness (Docker down)
**Commit:** 07fe81d | **Verdict:** SPEC ✅ / QUALITY approved

## Checks — all PASS
1. Three `for all` policies; correct owner columns: `profiles_self` on `id = auth.uid()` (profiles keys on id, has no owner_id), `playlists_owner`/`videos_owner` on `owner_id = auth.uid()`. Each has both `using` + `with check` with identical predicates.
2. Policy names match the test verbatim.
3. `pg_policies` semantics correct: `FOR ALL` → `cmd = 'ALL'`; explicit `WITH CHECK` → `with_check is not null` true.
4. 0002 applies after 0001 (filename order); no dependency inversion.
5. **videos-policy gap analysis holds:** the 0001 composite FK forces `videos.owner_id` = its playlist's `owner_id`, so `owner_id = auth.uid()` is exactly as strong as "the video's playlist is owned by the caller" — no join to `playlists` needed (spec §5.2 B1 reasoning).
6. Additive only; existing forced-RLS test untouched.

Matches spec §5.2 byte-for-byte. tsc clean; default suite 1505 green (integration excluded).

## Findings (Minor — recorded for final review, no action now)
1. The policy-presence `toEqual([3 rows])` isn't self-defending if a *future* migration adds a second policy on these tables (would fail cryptically). Not an issue in 1B (no later stage adds policies to these three). Consider a `policyname IN (...)` filter if that changes.
2. Policies are default `AS PERMISSIVE` — correct for a single policy per table; noted only for future multi-policy scenarios.

No Critical/Important. Live `db reset` green deferred.
