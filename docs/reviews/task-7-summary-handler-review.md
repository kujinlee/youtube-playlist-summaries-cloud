# Stage 1E-b Task 7 — Claude Task Review (summary handler, keystone) + fix

**Reviewer:** Claude (Opus), read-only, adversarial. **Target:** diff `1c3f808..02b07a0` (idempotent, self-healing `summaryHandler`). **Date:** 2026-07-07.
**Verdict:** Approved → **1 Important + 1 Minor fixed** → clean.

## Spec compliance: ✅ (7 binding properties)
1. Payload validation → `NonRetryableError`; over-long rejected pre-flight (before bundle/reserve/Gemini). ✅
2. Idempotency skip correct + safe: skips (no Gemini) ONLY on `artifacts.summaryMd.status==='promoted'` AND `docVersionKey(existing.docVersion)===job.version`; reads `artifacts` off the DB jsonb; `existing` via owner-safe `readVideo`; does NOT skip on `committed`. ✅
3. Owner-safe: uses `bundle.blobStore.putStaged/exists/promote` + owner-scoped `persistSummary(job.ownerId,…)`; does NOT use `writeArtifact` (the `playlist_key`-keyed `meta.updateVideoFields` path). ✅
4. Ordered write / self-heal: putStaged→verify tempKey→persistSummary(committed)→promote→persistSummary(promoted). Re-run re-reserves the SAME serial (idempotent `reserve_video_slot`), re-stages the same deterministic key, `promote` idempotent on `finalExists`. No drift, no orphan. ✅ (test e genuine)
5. Retryability: `NonRetryableError` for malformed + over-long; transient transcript error propagates unwrapped. ✅ (completed by the fix below)
6. Video build + fields correct (`summaryMd`=key, serial, playlistIndex, sort-key timestamps, docVersion, archived, processedAt). ✅
7. `ctx.signal` passed into `summaryCore` → threaded to Gemini/transcript. ✅

**setPhase-wrapper concern — clean, no bug:** phases land correctly (transcribing before core → wrapper fires summarizing immediately before the single `generateSummary` call → writing after core). `summaryCore` calls `generateSummary` exactly once. Only residue is a `as typeof generateSummary` type-smell; runtime spread is overload-safe. Keep as-is.

## Important (FIXED)
- **`PermanentTranscriptError` was not mapped to `NonRetryableError`.** `resolveTranscriptSegments` throws `PermanentTranscriptError` when a transcript is *provably* unavailable (captions AND Gemini both zero segments). The handler had no catch around `summaryCore`, so it propagated unwrapped → the runner marks it **retryable** → the job burns `max_attempts` (each cycle holding a worker slot) to `dead_letter`. That defeats the purpose of the permanent-error class and the "don't pay max_attempts on a provably-permanent failure" design (same philosophy as the over-long pre-flight reject).
  **Fix (`summary-handler.ts`):** wrapped `summaryCore` in try/catch — `PermanentTranscriptError` → `NonRetryableError` (fails immediately); every other error (transient transcript, Gemini blip, AbortError from wall-clock/lease) propagates unwrapped so the runner classifies it retryable / 'lost'. New test `(g)`.

## Minor (FIXED)
- **`IngestionPayloadSchema` was structural-only** — `durationSeconds: z.number()` let `NaN`/`Infinity`/≤0 through, and `NaN > MAX_DURATION_SECONDS` is `false` → a `NaN` duration bypassed the over-long guard and reached `transcribeViaGemini`. **Fix:** `durationSeconds: z.number().finite().positive()`, `playlistIndex: z.number().int().nonnegative()`. New test `(h)` (NaN → `NonRetryableError` pre-flight).

## Minor — CARRIED FORWARD
- **No runtime `VideoSchema.parse` before persist** — the built `Video` is compile-time typed only; out-of-range live-Gemini values would persist unvalidated. **Parity-preserving** (the local pipeline also never `.parse`s), so not a regression — noted for a possible future defense-in-depth pass (would apply to both local + cloud).

## ⚠️ Unverifiable-from-diff
- Task 6 runner marking a propagated non-`NonRetryableError` as retryable (assumed, correctly out of this task's scope — covered by the runtime suite).
- Live-Gemini `Video` validity (mocked in all tests).

## Task quality verdict: Approved (post-fix). Integration 103, unit 1588, tsc 0.
