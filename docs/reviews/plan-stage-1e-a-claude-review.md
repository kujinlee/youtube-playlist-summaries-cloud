# Stage 1E-a Plan — Claude Adversarial Review

**Reviewer:** Claude (Opus), fresh subagent, traced every claim-based test + verified SQL/roles against the migrations.
**Target:** `docs/superpowers/plans/2026-07-07-stage-1e-a-durable-job-queue.md` (v1).
**Date:** 2026-07-07.

## Blocking
1. **Global `claim_next_job` + never-reset DB breaks every claim-based test** at the Task 6 full-suite run (order-dependent; earlier suites leave `queued` rows). Traced failures in worker (stale-lease, crash-loop, fail, cancel-complete), runner (both), and store tests. **Fix:** `p_video_id` filter + run-unique video id, or assert by job id.
2. **`fail` retryable test crashes on backoff even in isolation.** After a retryable fail, `run_after = now()+10s`; the immediate re-claim filters `run_after <= now()` → returns `[]` → `c2 = undefined` → `c2.lease_token` throws. Task 3 can't go green. **Fix:** reset `run_after = now()` (via admin) before the re-claim.

## High
1. **`heartbeat_job` has zero test coverage** despite spec §7 requiring heartbeat fencing. **Fix:** add happy-path (extends lease, `ok:true`) + stale-token (`ok:false`) tests.
2. **Spec-required concurrency tests missing** (§7): concurrent enqueue of the same key (one insert, other joins) and concurrent claim (distinct jobs). These validate the two load-bearing mechanisms (`on conflict do nothing`, `SKIP LOCKED`). **Fix:** add `Promise.all` tests.

## Medium
1. **Runner cancel test block 1 is dead code** (`enq`/`requestCancel` with no assertion). **Fix:** delete or make it an asserted queued→cancelled case.
2. **Enqueue vanished-row retry loop untested** (spec §7 unit list). **Fix:** targeted test or explicit deferral note.
3. **`attempts` semantics diverge from spec** and are relabeled without reconciling consumers. **Fix:** update spec/glossary to "executions started," not just a code comment.
4. **`owner_id` FK to `profiles` silently dropped** (spec §4; anchors 1D quota FK) and not listed in Deviations. **Fix:** restore or explicitly justify. [Resolved: FK restored — anon has a profiles row.]

## Low
1. Payload-on-join behavior untested — add an assertion the join keeps the original job_id + payload.
2. Cross-user isolation untested — different owner same key → separate job; another user's `request_cancel_job` → raises (spec §7).
3. "claim returns null when empty" never asserts null.

## Non-issues (explicitly verified — no defect)
- `on conflict (cols) where … do nothing` **is** a valid partial-index arbiter; `returns setof jobs` + `return query update … returning *` is valid plpgsql; `power(…)::int` and `make_interval(secs=>…)` typecheck.
- `service_role` BYPASSRLS updates any owner's row under `force row level security` **without** a service policy (the 0007 storage policy is storage.objects-specific). One `for all using/with check (owner_id=auth.uid())` policy ≈ the spec's split policies.
- `anonSession()` → real principal, role `authenticated`, non-null `auth.uid()` → passes the enqueue guard/grant/with-check.
- Each task's `db reset` re-runs 0008 from scratch → no `create function` collision; revoke/grant signatures match.
- Crash-loop attempts math (max=2) is correct, no off-by-one (its only failure mode was the B1 isolation issue).
