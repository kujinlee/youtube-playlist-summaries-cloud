# Stage 1E-b Task 1 — Claude Adversarial Task Review (spec + quality)

**Reviewer:** Claude (Opus), read-only, adversarial mandate.
**Target:** diff `c421391..778e2ce` (migration `0009` identity re-key + queue adapter + fixtures).
**Date:** 2026-07-07.
**Verdict:** Spec ✅ / Quality **Approved** — no Critical/Important; Minor test-hygiene + deferred-coverage only.

## Spec compliance: ✅
Every Global-Constraint / brief element present and matching the brief's exact text:
- `jobs.playlist_id uuid not null` + **composite** FK `(playlist_id, owner_id) → playlists(id, owner_id) on delete cascade`; backed by `playlists.unique(id, owner_id)` (0001:18).
- `progress_phase` CHECK restricted to `transcribing|summarizing|writing`.
- `jobs_idem_active` re-keyed to include `playlist_id`; `ON CONFLICT` arbiter columns + predicate match the index.
- Old `enqueue_job(text,int,text,text,jsonb)` dropped; new `(uuid,text,int,...)` re-created with re-issued `revoke/grant`.
- `set_progress_phase` lease-fenced on `locked_by = p_worker_id AND lease_token = p_lease_token AND status='active'`; `service_role`-only grant.
- `sweep_expired_leases` backoff `10 * power(4, least(greatest(j.attempts-1,0),15))::bigint` — byte-matches `fail_job` (0008:157).
- Adapter: `playlistId` on `JobKey`/`LeasedJob`; `setProgressPhase` on interface + impl; `enqueue` sends `p_playlist_id`, `claim` maps `r.playlist_id`. `SupabaseJobQueue` is sole implementer.
- No Missing / no Extra. Scope addition (`job-queue-schema.test.ts`) necessary & correct.

## Verified sound (adversarial checks)
- **Composite FK genuinely rejects cross-tenant enqueue:** attacker `owner_id=auth.uid()` + `playlist_id=victimPl` needs `(victimPl, attacker)` in `playlists` → violation. Single-column FK would have accepted it; the cross-owner integration test proves compositeness.
- **`set_progress_phase` fence — no gap:** stale worker's `lease_token` won't match after reclaim → 0 rows → `false`.
- **Producer join tests still prove the join** under the `playlist_id`-inclusive key (one seeded playlist reused across same-key calls; `joined===true`, equal `job_id`). New identity test exercises two-playlists→two-distinct-jobs + cross-owner rejection.
- **No unmigrated callers:** grep-confirmed; `app/api/** controller.enqueue` is unrelated ReadableStream.

## Minor (test-hygiene / deferred coverage)
- **`schema.test.ts` composite-FK assertion checks only `conname`** — a single-column FK of the same name would pass. Security property is *proven* by the cross-owner integration test, so not a hole — but the guardrail file should assert the column span. **→ FIXED this task** (converges with Codex Low #1).
- **`set_progress_phase` has zero test coverage** (`0009:97` / adapter `supabase-job-queue.ts:70`). Low risk (byte-matches proven fence). **→ CARRIED FORWARD:** the first 1E-b task that consumes `set_progress_phase` must add fence-rejects-stale / phase-persists / non-service_role-rejected tests.
- **Sweep backoff interval value not asserted** — the mandatory `run_after` reset in the worker tests is evidence backoff sets a future `run_after`, but no test asserts the `10·4^n`s value. **→ CARRIED FORWARD** to the retry/backoff task.
- **Cross-owner rejection test asserts only `res.error !== null`**, not the error class. Low risk (seeding otherwise valid → deterministic rejection reason). **→ CARRIED FORWARD** (nit).

## ⚠️ Cannot verify from diff alone — RESOLVED by controller
- Green-suite (73/73, tsc 0) + `db reset` applying `0009` cleanly: **independently re-run by controller → 15 suites / 73 tests pass, tsc 0 errors.** Resolved.
- Whether a later 1E-b task exercises `set_progress_phase`: consuming task tracked as a carried-forward gate (see Minor above).
