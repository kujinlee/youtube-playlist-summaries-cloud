# Stage 1E-b Task 4 — Claude Task Review (abort semantics) + fix

**Reviewer:** Claude (Opus), read-only, adversarial. **Target:** diff `0085415..7dcc2c8` (signal threading through gemini/transcript). **Date:** 2026-07-07.
**Verdict:** Needs fixes → **1 Important fixed** (commit below) → Approved.

## Spec compliance: ✅
Binding properties 1–5 all hold: AbortError unwrapped in `generateSummary`'s outer catch; abort-aware `abortableSleep` with timer+listener cleanup (`{ once: true }` / `removeEventListener` — no open-handle hang); leaf `generateContent` calls forward `signal: opts?.signal`; all four signatures add OPTIONAL trailing `opts` (existing callers unchanged — 187 gemini/pipeline + 1583 unit green); `PermanentTranscriptError` thrown only on captions-empty AND Gemini-zero-segments, else retryable `Error`.

## Important (FIXED)
- **`resolveTranscriptSegments` re-wrapped AbortError unconditionally.** Its catch-all re-wrapped *every* non-`PermanentTranscriptError` — including a cleanly-unwrapped `AbortError` escaping `transcribeViaGemini` (via pre-attempt check or `abortableSleep`). Because Task 4 *added* the forwarded signal to this boundary, an abort during transcript resolution cancelled promptly but surfaced to the worker as a generic `Error` in ALL cases (not just the last-attempt edge the implementer's report described). Task 6 classifies lost-lease/SIGTERM by `AbortError` identity, so this would misclassify a deliberate shutdown as a real transcript failure → wrong retry/requeue/fail-marking.
  **Fix (`lib/transcript-source.ts`):** added `if ((geminiErr as { name?: string })?.name === 'AbortError') throw geminiErr;` at the top of the catch, mirroring `generateSummary`. New test in `transcript-source.test.ts` asserts an aborted fallback re-throws with `name === 'AbortError'` and NOT the generic "transcript unavailable…" message. Full suite 1584 green, tsc 0.

## Minor — CARRIED FORWARD
- **ACTIVE FLAG for Task 5 (summaryCore) + Task 6 (runOnce):** `extractQuickView`, the magazine `generateJson` caller, and `fixSummary` do NOT thread a signal (out of Task 4's 3-function scope). `pipeline.ts` calls `extractQuickView`, so a worker abort will NOT cancel Quick-View/magazine/fix in-flight Gemini calls. **The summary handler path (Task 5/7) must rely only on the threaded functions (`generateSummary`, `generateJson`, `transcribeViaGemini`, `resolveTranscriptSegments`), OR Task 6 must thread the rest.** Do not assume the whole pipeline is cancellable.
- `lib/dig/dig-section.ts:47` has a `signal` param it doesn't forward into `resolveTranscriptSegments` — dig deferred to 1E-b-2; add a TODO there when dig is built.
- `transcript-source.ts` throwing `PermanentTranscriptError` inside `try` to re-throw in the sibling catch is slightly convoluted (readable; non-blocking).

## ⚠️ Unverifiable from diff — RESOLVED
- Full suite 1584/1584 green + tsc 0: re-run by controller after the fix.
- Real `@google/generative-ai` honoring `requestOptions.signal`: mocked in tests; only live-API behavior confirms leaf cancellation (accepted — SDK 0.24.1 documents the field).

## Task quality verdict: Approved (post-fix).
