# Stage 1E-a Spec — Claude Adversarial Review

**Reviewer:** Claude (Opus), fresh-subagent adversarial pass with full file access.
**Target:** `docs/superpowers/specs/2026-07-06-stage-1e-a-durable-job-queue-design.md` (v1).
**Date:** 2026-07-07.
**Note:** run as the fallback while the Codex CLI was broken (missing npm platform binary). Codex was
subsequently reinstalled (v0.142.5) and ran its own pass — see `...-spec-codex.md`. Both are retained.

## Blocking

- **B1. `complete()`/`fail()` cannot fence on lease ownership.** Stalled `w1` → sweep reclaims → `w2` claims → `w1` `complete()`s over `w2`. `complete`/`fail` take no `workerId`. **Fix:** all worker mutations carry `workerId`(+lease token) and fence `WHERE id=$ AND locked_by=$w AND status='active'`; 0 rows → discard.
- **B2. Crash-only jobs never reach `dead_letter` — infinite re-lease.** Sweep unconditionally returns `active`+expired to `queued` regardless of `attempts`; a job that always SIGKILLs its worker re-leases forever (contradicts Decision #1). **Fix:** sweep routes to `dead_letter` when `attempts+1 >= max_attempts`.
- **B3. Enqueue conflict-handling unspecified + TOCTOU.** "Return existing job on join" has no atomic statement; concurrent enqueues can both insert → `23505`, or the follow-up SELECT finds nothing if the live job terminated in the gap. **Fix:** `INSERT ... ON CONFLICT (...) WHERE status IN (...) DO NOTHING`, then SELECT, in one txn, with a vanished-row retry.

## High

- **H1. RLS `SELECT`-only + `SECURITY INVOKER` → INSERT denied.** Mirror 0002 (`for all ... with check owner_id=auth.uid()`) or make enqueue `SECURITY DEFINER` with an owner guard.
- **H2. Freeing the key on `completed` re-charges quota + regenerates source-of-truth.** Only `failed`/`cancelled`/`dead_letter` should free the key; `completed` must join/return or require a version bump.
- **H3. No indexes for the claim/sweep hot paths** — both seq-scan as terminal rows accumulate. Add partial indexes.
- **H4. `attempts` double-count** when unfenced `fail()` races the reclaim sweep → premature dead-letter. Fixed by B1's fence.

## Medium

- **M1. Double-execution window inherent + untestable with the stub.** Even fenced, a window exists between reclaim and `w1`'s next heartbeat. Worse: the identity/echo stub has no interior await, so the abort-on-lost-lease path can never fire in 1E-a tests despite §7's "whole lifecycle" claim. **Fix:** injectable checkpoint/await in the test handler; bound the heartbeat window.
- **M2. Cancellation lost when a cancelled-but-active job throws.** `fail()` routes to queued/dead_letter/failed, never `cancelled`. **Fix:** `fail()` and sweep check `cancel_requested` and short-circuit to `cancelled`.
- **M3. No queue-depth / concurrency cap** (§8 requires) and the self-sweep needs `SKIP LOCKED`/row-lock safety with multiple workers.
- **M4. `join` silently discards a divergent payload** (key excludes `payload`). **Fix:** define — reject on mismatch, or document that key fully determines payload.
- **M5. Worker `service_role` confinement incomplete for a new long-lived entrypoint.** State the worker is a separate process; extend the import-graph confinement scan to cover it.

## Low

- **L1.** `queued → cancelled` "immediate" needs one atomic statement (`cancel_requested=true` always; flip to `cancelled` only `WHERE status='queued'`).
- **L2.** No retention/archival of terminal rows — make it an explicit deferred item, not silent.
- **L3.** `updated_at` relies on manual `now()` — consider a `BEFORE UPDATE` trigger.
- **L4.** `ORDER BY created_at` has no tie-breaker — add `, id` for stable FIFO.

**Open-questions check:** Q1 (dead-letter visibility) genuinely deferrable. Q2 (enqueue returns status on join) is load-bearing — decide yes now; it hides M4 (join + divergent payload), the actually-unresolved question.
