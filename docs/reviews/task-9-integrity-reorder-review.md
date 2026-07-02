# Task 9 Review — Integrity / deferrable reorder / anon isolation (0005 + integrity.test.ts)

**Reviewer:** Claude (sonnet), fresh subagent — Postgres correctness + test validity (Docker down)
**Commit:** 20e0a9a | **Verdict:** SPEC ✅ / QUALITY approved *(after controller fixes)*

## Checks — PASS
1. **reorder_videos security (Codex H7):** `security invoker` (caller RLS applies); ownership guard `if not exists (… owner_id=auth.uid() or auth.role()='service_role') then raise`; `revoke all … from public, anon`; `grant execute … to authenticated, service_role`. All four present — no SECURITY DEFINER, no security regression.
2. **Deferral exercised:** the reorder runs as one plpgsql transaction; per-row UPDATEs transiently duplicate a position; `DEFERRABLE INITIALLY DEFERRED` (0001) checks only at COMMIT → succeeds. Final `ORDER BY position` asserted [C,B,A]. On a NON-deferrable constraint the same RPC would fail on the first UPDATE.
3. **Integrity CHECK tests:** mismatched id AND missing id both inserted via owner's anon+JWT client → error asserted.
4. **Anon isolation valid:** the other user's playlist is created via a real client; anon sees only its own row, not the other's.
5. **rpc arg names** (`p_playlist_id`, `items`) + jsonb field names (`video_id`, `position`) match the function.
6. **search_path:** 0005 uses `set search_path = public` — correct for SECURITY INVOKER (unqualified `playlists`/`videos` resolve; caller RLS still applies).
7. Additive only; tsc clean; default suite 1505 green (integration excluded).

## Findings addressed (controller fixes)
- **Important I1 (FIXED):** `ownedPlaylist` now throws a clear error if the seed insert fails (was `data!.id`, which would throw an opaque TypeError and mask the real cause).
- **Important I2 (FIXED):** anon-isolation test now asserts the anon insert succeeded (`anonInsert.error` null) — closes a potential vacuous pass where both `mine` and `cross` could be empty.
- **Minor M2 (FIXED):** reorder comment corrected ("updates, not upserts") and now states the deferral-proof reasoning.
- **Minor M1 (noted):** no explicit non-deferrable negative control — documentation-level; the green already implies deferral is in effect.

No Critical. Live `test:integration` green deferred (Docker down).
