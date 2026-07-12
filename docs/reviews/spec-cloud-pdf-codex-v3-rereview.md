# Codex adversarial RE-REVIEW — Cloud Summary PDF spec v3 (round 3)

**Model:** gpt-5.5 · **Date:** 2026-07-11 · **Verdict: CONVERGED.**
**Counts:** (A) genuine 3/3 groups. (B) new Blocking 0, new High 0 — **CLEAN**.

*(Round-3 note: the first Codex invocation hung reading stdin and was killed; a clean
stdin-fed retry produced this result. Both round-3 passes — Codex + Claude — converged.)*

## (A) Round-2 fixes — verification

1. **Single-flight/semaphore failure cleanup — GENUINE.** §3 step 6 mandates `finally` cleanup
   for both semaphore release and `inFlight.delete(cacheKey)` on success/error/timeout;
   failed-leader waiters get 503 with the entry removed so the next request retries; §11 has the
   poison-prevention test.
2. **`mdKey` validation ordering — GENUINE.** §3 step 2 runs `assertCloudSummaryMdKey(mdKey)`
   immediately after selecting `mdKey`, before blob read / base derivation / any storage op; §4
   names `lib/html-doc/assert-cloud-summary-md-key.ts`; §11 tests rejection before any storage.
3. **Round-2 Lows — GENUINE.** 503-after-charge = not double charge; stray `format`/`download`
   ignored; "never stale" → collision-negligible; ADR key updated to
   `pdfs/{base}.r{PDF_RENDER_VERSION}.{sha256(htmlNonceFree).slice(0,16)}.pdf`.

## (B) Final sweep — CLEAN, CONVERGED

No new Blocking or High. The single-flight/semaphore acquisition-order concern is covered at the
invariant + test level (map entry deleted on any settle; waiters get 503, not a poisoned promise).
The round-3 Claude Low (release the slot only if acquired) was folded into §3 step 6.

**Verdict: CONVERGED — this round is the diminishing-returns gate.**
