# Task 1 — Codex adversarial review (round 1)

**Model:** gpt-5.5 · **Date:** 2026-07-11 · **Target:** diff 629f12e..7d5db26
`tests/integration/pdf-put-atomicity.test.ts` + `docs/reviews/spec-cloud-pdf-atomicity.md`
**Counts:** Blocking 2 · High 1 · Medium 1 · Low 1. Wrong-client check: CLEAN.

## Blocking
- **B1 — torn-read-as-error absorbed as "absent" → false pass.** `test:38-40` treats `null` as
  acceptable absence, but `SupabaseBlobStore.get()` (`supabase-blob-store.ts:23-26`) returns `null`
  for **any** download error (5xx, aborted response, RLS, partial), not just 404. The object exists
  after the seed `put(A)` (`test:31`), so a `null` read is never benign here — a torn read that
  surfaces as a Storage error would be silently skipped and pass the gate.
  **Fix:** assert `buf !== null` for every read after the initial put (object always exists → null
  is a failure, not "absent").
- **B2 — no proven read/write overlap → false pass.** `test:32-38` queues 8 uploads + 8 one-shot
  downloads but never asserts any read overlapped an in-flight write, never keeps readers polling
  through the write window, and never requires observing both generations. A fast local stack where
  every read sees the initial `A` passes trivially without exercising overwrite-visibility.
  **Fix:** continuous reader polling during writes / rounds that alternate the written value, record
  observed generations, assert BOTH generations seen + every observed buffer homogeneous & in {aa,bb}.

## High
- **H1 — doc overclaims.** `spec-cloud-pdf-atomicity.md:52-67` — "zero torn reads across 8x8" and
  "bare-put is sound" are stronger than the evidence given B1/B2. "64 interleavings" is not a measured
  quantity. **Fix:** state precisely what the (strengthened) test proves; no unmeasured figures.

## Medium
- **M1 — production caveat leans on unverified S3 claim** (`:69-74`). Local Docker passing is not
  production validation. **Fix:** state explicitly this covers only the local stack; cite the vendor
  guarantee in the ADR if production semantics are load-bearing.

## Low
- **L1 — cleanup not in `finally`** (`test:37-44`): a failed assertion leaks the probe object.
  **Fix:** `try { … } finally { await blobStore.delete(...).catch(() => {}) }`.

## Controller disposition
B1, B2, H1, L1 → fix now (gate must be non-vacuous). M1 → fold into the doc rewrite. Re-review
(Codex + Claude) after the fix, per the iterative-review loop (a Blocking fix is a new design).

---

# Round 2 (re-review of fix 5b8fe64)

**Codex gpt-5.5:** B1/M1/L1 **confirmed fixed**. **B2 STILL flagged Blocking** — the
both-generations-across-alternating-rounds assertion proves both values *appear* but not that any
read overlapped an in-flight write: because each round's pre-value also alternates, both
generations appear from alternation alone. Comment@75 ("single element" claim) + doc line "reads
did overlap" are overclaims. +2 Medium (tear-detector catches only OBSERVABLE tears; SIZE
"big enough to tear" unproven). Verdict: NOT CONVERGED.

**Claude (independent re-review, sonnet):** all five round-1 findings **genuinely fixed**;
independently ran the test (green, ~2.1s, no flake) + `tsc` clean; verdict **CONVERGED**. Noted the
same B2 nuance as "worth naming" but judged the doc's own disclaimer (:119-122) honest.

**Controller adjudication:** Codex's B2 is a valid **overclaim/wording** finding, NOT a test-logic
defect — server-side visibility-window overlap is fundamentally CLIENT-UNPROVABLE; the sound parts
are (a) concurrent dispatch + (b) a per-read homogeneity/whole-length tear-detector that never
fired. The doc contradicted itself (line 96 claimed proven overlap; :101-104 honestly disclaimed
it). Remedy = precise wording, no test-logic change. Fixed in `0faa121`: comment@B2 + header note +
SIZE comment + doc line 96 + disclaimer all reworded to "generation coverage / concurrent dispatch,
NOT per-read overlap proof"; tear-detector scope (observable tears only) clarified.

# Round 3 (convergence check of 0faa121)

**Codex gpt-5.5: CONVERGED** — 0 Blocking, 0 High. Prior B2 overclaim resolved; tear-detector +
SIZE wording honest. One Medium: sanity-check bullet @doc:85 still slightly overclaimed ("visible
to a reader running in the same round" — set retains no round/timing info) → softened per Codex's
suggested wording. **Gate CONVERGED.**
