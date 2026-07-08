# Round-2 re-review — Stage 1D spec v2 (dual, converged verdict: NOT converged)

**Date:** 2026-07-08 · Target: `docs/superpowers/specs/2026-07-08-stage-1d-cost-guardrails-design.md` (v2, commit 39f52c0)
**Reviewers:** Codex round-2 (`task-mrcme452-pkse0v`, session `019f43bd`) + Claude round-2 (fresh Opus subagent `aeaacd84bdb00d5a5`), independent.
**Scope:** verify each round-1 finding is *genuinely* fixed (not reworded) and hunt for defects the v2 fixes introduced.

## Verdict: NOT converged — another round mandatory

Both reviewers independently reached the same conclusion and the same three top findings. Per the iterate-to-convergence rule, a round that surfaces a **new Blocking + High** is proof the loop is still earning its cost → spec v3 + another full dual round.

## Blocking

- **B-A — Cap soundness still open (round-1 Claude-B1 NOT genuinely fixed).** The reservation is charged **once** at enqueue (`est`, charge-once), but a single job row can re-bill Gemini on every requeue: `jobs.max_attempts` defaults **5** (`0008:13-14`); every non-`NonRetryableError` is retryable (`worker-runner.ts:58-64`), a retryable failure requeues (`fail_job`→`queued`, `0008:152-160`), and **crash/lease-loss reclaim** requeues via `sweep_expired_leases` independent of `fail_job` classification (`0008:172-186`). The handler's idempotency skip fires only when a prior attempt already **promoted** the summary (`summary-handler.ts:47-53`), so any attempt that bills Gemini then fails pre-promotion re-bills the *entire* run next time. Worst-case actual ≈ `max_attempts` × per-run cost (~$1.5–2) against one 50¢ reservation → `reserved ≥ actual` is **false**. The v2 §3 derivation also under-counts: it omits `transcribeViaGemini` inner `retries=2` (up to 3 passes, `gemini.ts:501-550`), `generateJson`'s `retries=2` inside each of the 4 summary attempts (`gemini.ts:158-179`, `201`, `281`), and `extractQuickView`. *Fix: bound billable executions per job row and size `est` to a genuine one-run upper bound incl. inner retries — e.g. `max_attempts=1` for summary (at-most-once billing under fail AND crash-reclaim) + `est` re-derived.*

## High

- **H-B — Two-client producer wiring is an unspecified gap that violates the bundle invariant.** v2 §5 needs the **service** client for preflight + `enqueue_job` but the **session** client for auth, `resolvePlaylistId` (a per-owner `playlists` write), and GET/cancel reads. Today `getStorageBundle` builds one `jobQueue` from one client (`resolve.ts:51-64`); `enqueuePlaylist` uses that single `bundle` for both `resolvePlaylistId` and `queue.enqueue` (`producer.ts:39,63,68`); the route passes only the session client (`app/api/jobs/route.ts:29-31,51-53`). If an implementer swaps the bundle's `jobQueue` to service-role, `GET /api/jobs`→`listByPlaylist` runs service-role and leaks cross-owner rows — exactly what `supabase-job-queue.ts` warns against. *Fix: specify the split — a dedicated service `enqueuer`/`preflight` separate from the session bundle; `listByPlaylist`/status/cancel stay session-client; name `resolvePlaylistId`'s client + owner handling.*

- **H-C — The est↔max_duration coupling has no real enforcement; the proposed guard test is a static tautology.** Soundness rests on "`est` ≥ worst-case at `max_duration_seconds`," but `max_duration_seconds` is a runtime `guardrail_config` row, admin-tunable via `UPDATE`. A test comparing `est` to a hard-coded prose constant still passes after an admin raises `max_duration_seconds` in the DB — it cannot detect the unsound widening it claims to guard, and it ignores the retry multiplier (B-A). *Fix: the guard test must recompute worst-case from the **live** `guardrail_config` (`max_duration_seconds` × token-rate × attempt/retry budget), and/or move the duration bound into the atomic path (M-D).*

## Medium

- **M-D — Duration bound lives only in producer app code.** `enqueue_job` takes no duration arg and never re-validates (`payload` is opaque `jsonb`); the handler still hard-codes `MAX_DURATION_SECONDS = 4*3600` (`summary-handler.ts:17`). A 1800–14400s job that reaches the handler (direct service enqueue in tests, config drift, producer bug) bills up to 4h with no backstop. *Fix: reconcile the handler constant to the 30-min cap and re-validate duration inside `enqueue_job` (distinct SQLSTATE).* 
- **M-E — Signature-change blast radius under-enumerated (extends round-1 Claude-H3).** Beyond the two `job-queue-schema.test.ts` rewrites named in v2 §8, **ten** integration files call `enqueue_job`/`.enqueue` as an authenticated session and break on REVOKE + the new `p_owner_id`/`p_enqueue_ip` args: `cancel-by-playlist`, `job-queue-runner`, `worker-main`, `schema`, `job-queue-store`, `job-queue-producer`, `job-queue-playlist-identity`, `job-queue-worker`, `jobs-producer-polling`, `cancel-job-rpc`. Count/shape-asserting tests (`jobs-producer-polling`, `producer-roundtrip`) risk silent breakage. *Fix: enumerate the files in the test-migration note.*

## Low
- **Single user drains the global daily cap.** One registered user (20 summary/mo) at the re-derived per-job est can consume the whole `$5/day` global cap before their monthly quota bites. By-design for the demo (daily cap is global; monthly quota is per-user) — but call it out explicitly in §10.

## Round-1 findings — resolution status (both reviewers concur)
RESOLVED: Codex-B1/Claude-H2 (bypass via client enqueue → service-role-only + REVOKE + `auth.role()` guard); Codex-B2/Claude-H1/H3-sweep/Codex-H3 (release-on-failure/cancel/sweep → never-release); Codex-H4/Claude-M1 (dig enqueuable → reject `job_kind<>'summary'`); Codex-M5 (SQLSTATE collision → PT001/PT002); Codex-M6/Claude-M5 (IP through type layer → `{ownerId,enqueueIp}` context); Codex-L7/Claude-M2 (session-TZ month → UTC); Claude-M3 (velocity wording → coarse); Claude-M4 (disjoint sum → corrected `failed`); Claude-L3 (quota_allowance read grant); Claude-M6 (anon lockout → accepted/tunable).
**NOT genuinely fixed:** Claude-B1 (est upper bound) → resurfaced as **B-A** at the job-retry layer.
**PARTIAL:** Claude-H3 (schema-test shape) → two named, ten total → **M-E**.

## Next
Write spec v3 fixing B-A / H-B / H-C / M-D / M-E + the §10 Low, then re-run the full dual review on v3 (money-model change → convergence still required).
