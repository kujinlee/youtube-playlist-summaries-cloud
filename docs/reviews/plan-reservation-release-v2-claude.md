# Reservation Release Plan v2 — Claude Round-2 Adversarial Re-Review (independent)

**Reviewer:** Claude, independent, full repo access.
**Artifact:** plan v2 + spec v7.
**Verdict:** **CONVERGED** (Claude's pass) — 0 new Blocking, 0 new High, 1 Medium, 3 Low. All round-1 findings genuinely fixed.

> Note: the **combined** round-2 verdict is NOT CONVERGED — the independent Codex pass (`-v2-codex.md`) found 2 new High (JobQueue-interface tsc break; PJ002 cap-headroom) that this pass missed. Both are real. Round-3 required.

## Part A — Round-1 findings: all GENUINELY fixed
- **Codex-H1** cause-walk retryability — FIXED (traced end-to-end: caption-fail + fail-closed `NonRetryableError` → `transcript-source.ts:62` wraps `{cause:geminiErr}` → `isNonRetryable` finds it → `retryable=false` → `fail_job` v_new='failed' → release fires).
- **Claude-H1** required-field — FIXED (exactly two `HandlerCtx` literals, both updated; tsc gate added).
- **Claude-H2** threading test — FIXED, guard non-vacuous (drives the real `gsOpts` branch; fails if `gsOpts.billing` dropped). One naming defect (L1).
- **Codex-M1/M2/M3, Claude-M1/M2, 5 Lows** — all verified fixed.

## Part B — New-defect hunt (clean except Medium-1)
- `isNonRetryable` governing all errors: **no regression** — `NonRetryableError` ctor takes only `message`, cannot carry a `cause`, so no retryable error is ever wrapped inside a `NonRetryableError` chain; the only nested case is the intended transcript H1 path.
- `summaryCore` driveable with the deps-double; `enqueueSummary` → queued/leasable/150¢; `billing` var in scope for the catch; serve `releaseGateOpen()` stays closed in prod; `reserve_serve_model_meta` survives DROP+recreate. ✓

### Medium-1 — Task 10 breaks 3 existing exact-match `fail()` assertions; plan wrongly claims "Expected: PASS"
`worker-runner-runtime.test.ts:84,124,169` assert `toHaveBeenCalledWith(..., { retryable: X })` (exact object). After Task 10 the runner always passes `{ retryable, billableSucceeded }`, so all three fail the deep-equality. jest surfaces it immediately (nothing ships broken), but the "no regression" claim misleads.
**Fix:** Task 10 scope must update those 3 assertions to `{ retryable: X, billableSucceeded: true }` (or `expect.objectContaining`) and correct the Step 4 "Expected: PASS" note.

## Low
- **L1** — H2 test references nonexistent `runSummaryCore`; real export is `summaryCore` (flagged placeholder, rename at impl).
- **L2** — Task 9's "update `transcript-source.test.ts:64` to assert the Gemini cause" is imprecise — that test asserts a message regex, not `.cause`, so the change doesn't break it; strengthening is optional.
- **L3** — behavior-24 serve lease-overlap relies on `settle(A)` no-op after token B overwrites `release_token`; correct via the `where release_token = p_token` guard, but assert the token-overwrite explicitly.

**VERDICT (Claude pass): CONVERGED.** Design remains money-sound. (Combined with Codex → round-3 required for the 2 new High.)
