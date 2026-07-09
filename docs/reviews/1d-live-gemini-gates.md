# 1D Live Gemini Verification Gates — Outcome (Task 13)

## Status: NOT EXECUTED this session

`RUN_LIVE_GEMINI` was unset for this session, so `tests/integration/gemini-live-gates.test.ts`
ran its `describe.skip` branch (both live checks skipped, zero real Gemini API calls made, zero
billing incurred). This is expected and by design — these gates are opt-in only, never part of
the normal integration/CI run.

**Decision: `CLOUD_TRANSCRIBE_FALLBACK_VERIFIED` in `lib/gemini.ts` STAYS `false`.**

The fail-closed cloud audio-fallback transcription path (`transcribeViaGemini` with `caps` set)
therefore continues to throw `NonRetryableError` before any `generateContent`/`countTokens` call,
and before any billing — exactly as it has since Task 6/12. Nothing in this task flips that flag.

## What the gates check, and why

`tests/integration/gemini-live-gates.test.ts` documents (and lets a human re-run on demand) the
two live checks that would need to both pass before a human decides to flip the flag:

1. **(a) thinkingBudget:0 → `usageMetadata.thoughtsTokenCount` present and `=== 0`.**
   `perRunWorstCents` (lib/gemini-cost.ts) prices the worst-case cost of the cloud audio-fallback
   path assuming `thinkingConfig.thinkingBudget: 0` means Gemini bills **zero** thinking tokens.
   That assumption is only tested against the mocked SDK today (`tests/lib/gemini-caps.test.ts`
   asserts the request *shape* — `thinkingConfig.thinkingBudget === 0` — is sent, not that the
   live API actually honors it with `thoughtsTokenCount === 0`). If a live run ever reported this
   field absent, or nonzero, the cost model would need to be revised before ANY unverified-cost
   money path could be enabled.

2. **(b) `countTokens` on a real YouTube `fileData` LOW-res request returns a video-scale
   `totalTokens`.** `assertTranscribeInputWithinCap` (lib/gemini.ts) is the countTokens preflight
   that would gate the cloud path once enabled — it must be counting the actual video payload,
   not silently returning near-zero for a media type it doesn't recognize. A live run confirms
   the SAME request shape `transcribeViaGemini` sends produces a plausible (hundreds-of-thousands
   scale) token count, not a stub/degenerate one.

Both are `it()`s inside a `describe.skip`-gated block, so they add zero CI cost and zero
CI flakiness risk; they exist purely as an executable, versioned procedure for the human
who eventually runs the live verification.

## Non-live fail-closed coverage (already exists, unchanged by this task)

`tests/lib/gemini-caps.test.ts:143` — *"fail-closed: with caps + `CLOUD_TRANSCRIBE_FALLBACK_VERIFIED=false`
throws `NonRetryableError` before any generateContent"* — asserts, against the mocked SDK, that:
- the guard fires before `generateContent`, and
- the guard fires before `countTokens` (i.e. before the preflight itself), so an unverified
  cloud-fallback call bills absolutely nothing, not even a countTokens call.

This test already existed prior to Task 13 (introduced alongside the fail-closed flag in the
earlier caps-threading task) and required no changes here — it continues to pass because the
flag is untouched.

## How to actually run the live gates later

```bash
RUN_LIVE_GEMINI=1 GEMINI_API_KEY=<real key> \
  npx jest tests/integration/gemini-live-gates.test.ts --runInBand
```

If both assertions pass on a real run, a human can then:
1. Flip `CLOUD_TRANSCRIBE_FALLBACK_VERIFIED` to `true` in `lib/gemini.ts`.
2. Update `tests/lib/gemini-caps.test.ts:143`'s premise comment (the guard test itself will need
   to move/adapt since the flag it asserts `=== false` will no longer hold).
3. Re-run the full unit + integration suites to confirm the (now-enabled) cloud fallback path's
   other guards (the `assertTranscribeInputWithinCap` over-cap rejection, in particular) still
   behave as designed with a live model.

Neither of those two follow-up steps was done in this session — they are gated on an actual
live run, which did not happen here.
