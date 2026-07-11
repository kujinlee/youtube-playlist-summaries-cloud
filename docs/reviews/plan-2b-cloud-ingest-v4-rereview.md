# Claude Adversarial Re-Review — Stage 2b Plan v4 (Round 4, convergence check)

**Reviewer:** Claude (independent subagent, full source). **Artifact:** plan v4 (`d876401`). **Date:** 2026-07-11.
**Verdict:** **CONVERGED (no new Blocking/High).** Only 2 benign Low; all 6 Round-3 fixes confirmed genuine.

## Findings (Low only)

1. **[LOW]** Deferred-A/B test may log a benign React "update not wrapped in act()" warning (B's continuation flushes outside act). `jest.setup.ts` is only `import '@testing-library/jest-dom'` — it does **not** fail tests on `console.error` — so cosmetic; assertions sound. Optional: wrap `resolveA(...)` in `await act(...)`.
2. **[LOW]** "aborts during the wait" RED parks on the controlled `sleep` until Jest's ~5s timeout (no permanent hang). Already accepted in R3.

No Blocking/High/Medium introduced by the v4 deltas.

## Deferred-A/B test — validity scrutinized (central concern)

**VALID and non-vacuous.** Traced against real `CloudApp.tsx`: first render (playlist=A) runs `fetchVideos` (`reqSeq`→1) parked on the pending A promise; `rerender` with `playlist=B` recomputes `cloudScope` (new object), re-runs `[cloudScope]` effect, calls the new `fetchVideos` (`reqSeq`→2 **synchronously**, before `resolveA`). Microtask order: B (seq 2 == reqSeq → `setPlaylistUrl(B)`), then A (seq 1 != reqSeq → dropped). Without the guard A would win last → `playlistUrl=A` → Refresh POSTs A. Test genuinely distinguishes guarded vs unguarded.

## Round-3 fixes CONFIRMED genuine
`reqSeq` guard (both try+catch, before all setState); `jobsFrom`/`status()` strict typing; `onProgressRef` assign-in-render; fake-timer `afterEach`+unmount; `status()` terminal derivation; timedOut design-bullet. Cross-checks: `reqSeq` drops only superseded calls (mount/handleSort/refetch unaffected); exhaustive-deps clean; Task 1 traced against all 9 poll-client tests; no nonexistent token/type/function.

**CONVERGED (no new Blocking/High).**

---
**Reconciliation note:** Codex R4 flagged one High (Task 8 obsolete `toBeDisabled()` tests not replaced) that this pass did not surface — a real suite-breaking gap, fixed in plan v5. Union of the two R4 passes after the v5 Task 8 fix = 0 Blocking/High/Medium → gate converged.
