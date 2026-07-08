# Stage 1E-b Task 2 — Claude Adversarial Task Review (spec + quality)

**Reviewer:** Claude (Opus), read-only, adversarial mandate.
**Target:** diff `fc47ec6..9d8d3c7` (`reserve_video_slot` + `persist_summary` appended to `0009` + `worker-persistence-rpcs.test.ts`).
**Date:** 2026-07-07.
**Verdict:** Spec ✅ / Quality **Approved** (two Important follow-ups, not gates).

## Spec compliance: ✅
- Step-3 SQL byte-matches the brief; appended at END of `0009` (44 pure insertions, Task 1 untouched); grants/`security invoker set search_path=public` consistent with sibling RPCs in `0007`.
- 6 tests present: seq + concurrent idempotency, status-only-preserves-key, 0-row raise, owner-mismatch ×2.
- **Extra (both acceptable):** sequential-idempotency reserve (dispatch-requested); `persist_summary` owner-mismatch test — **in-scope hardening** (both RPCs share the load-bearing ownership check).
- **Missing (coverage, addressed in fix):** distinct-video concurrency → distinct serials; sibling artifact-kind survival.

## Important
- **I1 (= Codex Low test:22) — concurrency test doesn't exercise the FOR UPDATE lock.** Same-video convergence holds even if the lock were deleted (unique `(playlist_id, video_id)` + reselect). The lock only matters for **different** videos: `serialNumber` lives in jsonb with **no** DB uniqueness (only `videos_playlist_position_uniq` on `position`, `0001:38`), so without the lock two reservers of distinct videos compute the same `max+1` and commit **duplicate serials**. Migration is correct (`perform 1 from playlists … for update` serializes, mirroring `claim_video_slot`), but a lock-removal regression stays green. **→ FIXED:** distinct-video concurrent-reserve test asserting distinct serial + position.
- **I2 (= Codex H1) — `persist_summary` lost-update window (no row lock on the key-preserving coalesce).** Two concurrent persists on one video can both resolve the key against the old row; the later UPDATE clobbers the other's key. **→ FIXED:** fallback key resolved from the UPDATE's own locked row (`v.data`), not a detached subquery.

## Minor
- **M1 — top-level `summaryMd` string leaks into `data`** alongside `data.artifacts.summaryMd.key` (denormalized). Verbatim from brief; not the implementer's defect. Left as-is (fixing it is a cosmetic behavior change beyond the H1/I2 fix scope); noted for a later cleanup.
- **M2 — owner-mismatch tests asserted only `error != null`.** **→ FIXED:** now also assert the victim row is unchanged.
- **M3 — RED honesty:** three tests "passed" pre-impl because a missing RPC returns non-null `PGRST202`; report discloses this and the behavior-bearing tests failed for the right reason. No action.

## ⚠️ Cannot verify from diff alone — RESOLVED
- GREEN/full-suite/tsc (6/6, 79/79, 0): verified by the implementer's `db reset` run and re-verified by the fix subagent post-fix.
- `authenticated`-role (RLS-on) path not exercised (all tests use `adminClient` service_role) — the in-function ownership check IS exercised; RLS-invoker path is covered by 1C RLS tests. Acceptable.

## Task quality verdict: Approved (post-fix: H1/I2 lost-update fixed + lock/merge test coverage added; H2 status-downgrade deferred to Task 7; Medium null-serial edge carried forward).
