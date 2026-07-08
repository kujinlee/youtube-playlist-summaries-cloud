# Stage 1E-b Whole-Branch — Codex Adversarial Review

**Reviewer:** Codex (`gpt-5.5`), read-only. Session `019f4068-430f-7fa3-b3f3-0a51ff84913c`.
**Target:** whole branch `c421391..3fb577c` (17 commits, 45 files). **Date:** 2026-07-07.
**Verdict:** revise-again — 2 Blocking, 2 High, 2 Medium.

## Blocking
1. **Stale workers can perform UNFENCED writes after lease loss** (`summary-handler.ts:86` + `worker-runner.ts:37`). Worker A finishes Gemini, loses its lease before/during `writing`; `setPhase('writing')` returns `{ok:false}` but the runner/handler discards it; the blob write + both `persistSummary` calls are NOT lease-fenced. Sweeper requeues, worker B claims and re-runs Gemini/write. A's final `complete` returns false, but A already promoted/persisted. → double Gemini charge + stale side effects from a non-owner worker. *Fix:* `setPhase` throw on `ok:false`; check `ctx.signal.aborted` before every irreversible write; lease-fence `persist_summary`.
2. **`persist_summary` clobbers unrelated top-level video state** (`0009:112`). `v.data || (p_video - 'artifacts')` overwrites current fields with STALE payload values captured at enqueue time. If, while the job runs, membership reconciliation archives the video or a sync updates metadata, completion silently reverts `archived`/operational fields. *Fix:* persist only summary-owned fields; preserve operational fields (`archived`, `removedFromPlaylist`, playlist membership/order, write-once timestamps) inside the RPC.

## High
1. **`persist_summary` can downgrade `summaryMd.status` promoted→committed** (`0009:115`). A stale worker/retry calling with `p_artifact_status='committed'` overwrites `promoted` unconditionally → the idempotency skip no longer matches → later retry re-runs Gemini against an already-promoted artifact. *Fix:* make status monotonic for the same key (reject a committed write after promotion).
2. **The long-lived worker exits on a queue RPC error before a job is claimed** (`worker/main.ts:33` + `worker-runner.ts:23`). `sweepExpired()`/`claim()` throw on a transient Supabase/network blip; those awaits are OUTSIDE `runOnce`'s try/catch, `runWorkerLoop` doesn't catch `runOnce`, `main().catch` → `process.exit(1)`. One transient error kills the worker. *Fix:* try/catch per loop iteration + backoff + continue unless shutdown.

## Medium
1. **`reserve_video_slot` returns NULL for an existing row lacking `data.serialNumber`** (`0009:86`) → `padSerial(null)` corrupts the filename. *Fix:* assign a serial to serial-less rows under the lock, or raise an explicit invariant error.
2. **Job version vs persisted doc version drift** (`summary-handler.ts:43`). Handler persists `CURRENT_DOC_VERSION` but the skip compares `existing.docVersion` to `job.version`; a job whose `version !== docVersionKey(CURRENT_DOC_VERSION)` never self-heals (always re-runs Gemini). *Fix:* reject `job.version !== docVersionKey(CURRENT_DOC_VERSION)` as NonRetryableError.

## Low
None.
