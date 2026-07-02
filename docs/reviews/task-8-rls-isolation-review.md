# Task 8 Review — RLS isolation / mutation / cross-owner FK attack

**Reviewer:** Claude (sonnet), fresh subagent — test-validity focus (Docker down)
**Commit:** 90c8f78 | **Verdict:** SPEC ✅ / QUALITY approved

## Test validity — all PASS (would fail if RLS were broken; not vacuous)
1. **Seed proves real rows exist:** `seedPlaylistWithVideos` inserts via A's anon+JWT client and asserts `e1`/`e2` null → B's empty result is proof RLS hid real rows, not that seeding failed.
2. **Real RLS path:** all seeding + assertions use `signInAs` (anon key + user JWT); `adminClient` used only in `newUser` (createUser) — the permitted scope. No assertion uses BYPASSRLS.
3. **Mutation semantics:** B update AND delete on invisible rows → `data: []` (0 affected, no error), then A's rows confirmed still present via A's client.
4. **with-check:** A reassigning `owner_id` on its own visible row → error (not a 0-row no-op) — the distinguishing assertion is present.
5. **FK attack, both cases:** (a) owner_id=B/playlist=A → composite FK reject; (b) owner_id=A spoof → with_check reject. Both assert error; mechanisms correctly attributed.
6. Additive only; tsc clean; default suite 1505 green (integration excluded).

## Findings addressed (controller fixes)
- **Important I-1 (FIXED):** videos isolation check now asserts `expect(vids.error).toBeNull()` — matches spec §7 "0 rows, not error" for all three tables (profiles/playlists already did).
- **Minor M-1 (FIXED):** with-check test now confirms A's row still has the original `owner_id` after the rejection (no partial write).
- **Minor M-2 (FIXED):** FK-attack `asA` comment clarified — the FK passes (valid `(A.playlistId, A.userId)` row), so only `with_check` rejects the spoof.
- **Minor M-3 (noted):** fixed `playlist_key` strings are collision-safe because each test creates fresh users; only a concern without `db reset` — documented run procedure covers it.

No Critical. Live `test:integration` green deferred (Docker down).
