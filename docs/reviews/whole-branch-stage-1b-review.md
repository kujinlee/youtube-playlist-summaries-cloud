# Whole-Branch Final Review — Stage 1B (Auth + RLS Schema)

**Reviewer:** Claude (Opus), cross-cutting whole-branch pass (SDD final review)
**Range:** 5d5383d..f9f8d40 (22 commits) | **Method:** by-eye; Docker down → integration suite authored + tsc-clean, live green deferred; `npm test` 1505 green, `tsc` clean.
**Verdict:** CHANGES NEEDED → resolved (see Resolutions).

## Blocking
- **B1 — missing table GRANTs (the central cross-file gap).** Migrations create `profiles`/`playlists`/`videos` with forced RLS + owner policies but issue **zero** table-level GRANTs. The pinned CLI (2.109.0) default `auto_expose_new_tables` is unset → new `public` tables are NOT exposed to the Data API roles without explicit grants. RLS only *filters* rows a role already has base access to; without the GRANT, a user-JWT request returns `42501 permission denied`, not `data: []`. **The entire user-JWT integration suite would be red on first run** — the deferral was masking a real failure. (Ironically `exec-sql-guard.test.ts` correctly expects permission-denied; the core-table tests assume success — same mechanism, opposite expected outcomes.) → **RESOLVED**: `0006_grants.sql` grants CRUD to `anon, authenticated` (RLS still confines to `owner_id = auth.uid()`); GRANT is idempotent so it's safe even if a local image ships the legacy auto-grant seed.

## High (resolve with B1's grant migration)
- **H1** — `reorder_videos` (SECURITY INVOKER) UPDATEs fail for the authenticated caller without the grant. Fixed by 0006.
- **H2** — the anon guest `/try` write path (1C) needs the grant too; 0006 grants `anon` so 1C doesn't reopen the convention. Spec §5.4 updated to make the grant part of the reusable convention.

## Medium
- **M1 — `/auth/auth-error` page didn't exist** → callback redirect 404s at runtime (unit test only checks the header). → **RESOLVED**: added `app/auth/auth-error/page.tsx`.
- **M2 — `exec_sql` is a live `security definer … execute(arbitrary sql)` object** shipped in a numbered migration that applies to the hosted DB. Contained in 1B (service_role-only, guard-tested) but a leaked service key = full-DB RW. → **Tracked as a pre-public gate** (spec §10): drop it or replace with typed views before public launch.
- **M3** — `[db.seed] enabled=true` points at an absent `./seed.sql`; benign (`db reset` tolerates it). Noted.

## Low
- L1 policy-presence hard-codes 3 rows (fine for 1B); L2 middleware anon-provision returns before re-reading user (behaviorally fine); L3 empty-read parity constrains 1C `readIndex` (correctly deferred, target shape verified in `lib/index-store.ts`).

## Cross-cutting checks that PASSED
- **RLS attacker trace:** with grants in place, no B→A path. Forced RLS + 3 owner policies + composite FK genuinely close cross-owner injection; the `videos` policy checking only `owner_id` is as strong as a playlist-ownership join because of the composite FK. SECURITY DEFINER trigger confined to insert; SECURITY INVOKER reorder keeps caller RLS + owner guard.
- **Migration apply-order:** 0001→0006 clean, no forward references; the only reachability defect was B1 (a privilege gap, not an ordering bug — `db reset` applies all without SQL error; failure surfaces at query time).
- **service_role confinement end-to-end:** `server-only` + runtime guard + exhaustive-entrypoint import-graph scan (app/** + pages/** + middleware.ts), side-effect/re-export/dynamic aware, realistic `@/` planted-violation test. Nothing imports service.ts in 1B.
- **Spec §8:** met or explicitly+correctly deferred (Google live redirect; async MetadataStore 1C prereq; anon-TTL + exec_sql pre-public gates). Only silently-unmet item was M1 (now fixed).
- **Consistency:** naming, Principal↔playlist_key mapping, empty-read parity target all consistent. Accumulated per-task Minors were all addressed in-branch.

## Resolutions applied
1. `0006_grants.sql` (B1/H1/H2) + spec §5.4 convention update.
2. `app/auth/auth-error/page.tsx` (M1).
3. Spec §10 pre-public gates: anon-TTL + `exec_sql` removal + Google live redirect (M2).

**After resolutions: READY TO MERGE**, conditioned on the user's Docker `test:integration` run going green (the grant migration is the load-bearing fix that makes it pass).
