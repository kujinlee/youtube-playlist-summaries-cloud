# Stage 1E-b Whole-Branch — Claude Adversarial Review (Opus)

**Reviewer:** Claude (Opus), read-only, traced all 5 integration axes against source. **Target:** whole branch `c421391..3fb577c`. **Date:** 2026-07-07.
**Verdict:** NEEDS FIXES — 2 Important cross-task defects (parity/contract drift vs already-merged local code); No Critical (owner-safety airtight end-to-end).

## Important
- **I1 — `reserveVideoSlot` has no rollback on failure → orphan bare video row.** Handler reserves the slot BEFORE `summaryCore`; on any post-reserve failure (esp. `PermanentTranscriptError`→`NonRetryableError`, or `dead_letter`) there is NO cleanup. The `{id, serialNumber}`-only row from `reserve_video_slot` is never summarized and never deleted → an invalid `Video` (missing required fields) sits in `videos`, any `VideoSchema.parse` read throws on it, and serial N + position P are permanently burned. Local rolls back (`pipeline.ts:~303` `deleteVideo`); cloud does not. *Fix:* delete the reserved row in the handler catch if nothing was promoted (mirror local), OR reserve AFTER transcript resolution.
- **I2 — `playlistIndex` contract drift.** `ingestion-payload.ts:15` is `.int().nonnegative()` ("0-indexed"), but local pipeline is 1-indexed (`pipeline.ts:219` `i+1`) and `VideoSchema.playlistIndex` is `.positive()` (≥1) — a `0` is schema-invalid and persists silently (no `.parse` on write). The not-yet-built producer would build against a wrong contract. *Fix:* lock to 1-indexed now — payload `.positive()` + fix the comment.

## Minor
- **M1 — an advisory phase write can fail the whole job.** `ctx.setPhase` rejects if `set_progress_phase` errors; the handler's `setPhase('transcribing')` is outside the try/catch. A transient DB blip on an *advisory* write fails the job (retryably). *Fix:* make phase writes best-effort (`.catch(()=>{})`).
- **M2 — idempotency skip couples to compiled `CURRENT_DOC_VERSION`, not `job.version`** — if a job's version differs from the worker's compiled version, the skip degrades to "always re-run" on retry. Benign today (aligned at 3.3); note the coupling.
- **M3 — SIGTERM burns a retry attempt** (abort → `fail(retryable:true)` while lease valid → consumes an attempt). Inherent to the cooperative model; acceptable.
- **M4 — staged-object leak on pre-promote-crash retry** (run-1's temp object orphaned). Storage garbage, not correctness; 1C/1D blob-staging concern.

## Carried-Minors triage (Opus)
- T2 status-downgrade → **DEFER** (benign: worst case one extra re-run; no corruption). [NOTE: Codex rates this High — see consolidation; fixing monotonic anyway.]
- T2 reserve-NULL → DEFER (unreachable in cloud path). [Fixing defensively anyway — cheap.]
- T3 readVideo owner filter → DEFER (airtight: playlist_id UUID transitively owner-bound).
- T4 unthreaded Gemini fns → DEFER (summary path reaches only threaded fns).
- T7 no VideoSchema.parse → DEFER, but a `.parse` would catch I2 — recommended as the I2 fix vehicle.
- T6/T8 cooperative abort / unremoved listeners → DEFER (harmless).
- T2 summaryMd denormalization → DEFER (cosmetic; key stays consistent).

## What per-task reviews missed
I1 (reserve-then-fail orphan — only visible diffing against local rollback), I2 (payload vs VideoSchema vs local 1-indexing — cross-file), M2 (docVersion coupling — a T7↔producer seam no task owned).

## Cross-reference: Codex whole-branch pass (`whole-branch-stage-1e-b-codex.md`)
Codex independently found: persist_summary operational-field clobber (Blocking — Opus missed this), status downgrade (High), worker-dies-on-queue-error (High), reserve-NULL + version-drift (Medium). Consolidated fix set spans both reviews.
