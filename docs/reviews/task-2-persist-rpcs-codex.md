# Stage 1E-b Task 2 — Codex Adversarial Review

**Reviewer:** Codex (`gpt-5.5`), read-only. Session `019f3ff8-6c63-7533-9a44-996808e262c7`.
**Target:** diff `fc47ec6..9d8d3c7` (`reserve_video_slot` + `persist_summary` appended to `0009` + `worker-persistence-rpcs.test.ts`).
**Date:** 2026-07-07.
**Verdict:** revise — 0 Blocking, 2 High, 1 Medium, 4 Low.

## High
- **H1 — `persist_summary` lost-update on the key-preserving coalesce (`0009:108-110`).** The preserved `summaryMd.key` is read by a subquery from a **pre-UPDATE snapshot** with no row lock. Tx A (status-only) reads `old.md`; Tx B persists `new.md`; Tx A's UPDATE lands second and writes `old.md` back → B's key lost. `persist_summary` is **not** lease-fenced, so a lease-reclaimer + slow original are a real concurrent-writer path. **→ FIXED** (see below): resolve the fallback key from the UPDATE's own locked row (`v.data`), eliminating the detached snapshot. Converges with Claude reviewer I2.
- **H2 — `persist_summary` can downgrade artifact status (`0009:111`).** Row already `artifacts.summaryMd.status='promoted'`; a stale/retried `p_artifact_status='committed'` call overwrites it back to `committed`. **→ DEFERRED to Task 7 (handler), owner-flagged.** This is a genuine *design decision*, not a mechanical fix: the summaryMd key is stable per video (serial-based filename), so a legitimate re-summarize (job_version bump) re-writes the same key `committed`→`promoted`; a blanket anti-downgrade guard would mask that in-progress re-write and lie about artifact state. The status-write *sequence and caller discipline* live in the not-yet-built worker handler (Task 7), which owns the decision: enforce monotonicity in the caller, or add a guarded transition in the RPC. Recorded for the user's decision.

## Medium — CARRIED FORWARD
- **`reserve_video_slot` can return NULL for an existing video row lacking `data.serialNumber` (`0009:86`).** `0001` requires only `data.id`; test seeds create `{id}`-only rows. An existing `(playlist,video)` row with no serial → line 86 null → insert conflicts do-nothing → line 94 re-reads null → returns null. **Assessment:** does not occur in the cloud write path (rows are created by `reserve_video_slot` itself, which always sets `serialNumber`, or by full-`Video` upsert). Carry forward: a later hardening should, under the playlist lock, either assign a serial to a serial-less existing row or raise an explicit invariant error rather than return NULL.

## Low — test hygiene (3 of 4 FIXED, converge with Claude I1)
- **`test:22` same-video concurrency does not prove the playlist row lock.** Without `FOR UPDATE`, same-video calls still converge via the `(playlist_id, video_id)` conflict + reselect. **→ FIXED:** added a distinct-`video_id` concurrent-reserve test asserting distinct `serialNumber` AND distinct `position` — this catches a removed lock.
- **`test:14` reserve tests only compare `a.data === b.data`; no non-null / row-count / target-serial assertion.** **→ FIXED:** assert `data` is a positive integer and equals the persisted row's `serialNumber`.
- **`test:32` artifact-preservation covers only `summaryMd`; sibling kinds unproven.** **→ FIXED:** seed `artifacts.deepDiveMd`, run a `summaryMd` status-only persist, assert the sibling survives unchanged.
- **`test:44` error-path tests assert only `error !== null`.** **→ PARTIALLY FIXED:** owner-mismatch tests now also assert the victim row is unchanged. (Message/code-branch assertion left as a nit — supabase-js surfaces plpgsql raises generically.)
