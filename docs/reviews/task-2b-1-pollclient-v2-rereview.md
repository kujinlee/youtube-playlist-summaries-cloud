# Task 1 Re-Review (round 2) — CONVERGED

**Artifact:** `pollUntilTerminal` after fix commit `5136d31` (full task diff `eef22a7..5136d31`). **Date:** 2026-07-11.
**Reviewers:** Codex (gpt-5.5) + Claude (independent subagent). **Verdict: CONVERGED — no new Blocking/High/Critical/Important.**

## Prior findings — both reviewers confirm genuinely fixed (not reworded)
1. **[HIGH] abort vs. successful fetch** — fixed: `signal.aborted` checked right after `await fetchRows()` (before onProgress/terminal) and in the catch path (before isFatal/error-count).
2. **[HIGH] abort vs. sleep** — fixed: new `abortableSleep` races the injected/default sleep against a one-shot `abort` listener; pre-aborted → immediate resolve, no listener leak, `settled` guard against double-finish; never-resolving injected sleep now wakes on abort (strengthened test).
3. **[MEDIUM] timeout precedence** — fixed: timeout checked after the fetch in both success and catch paths, not at loop-top (matches pre-diff semantics).
4. **[LOW] `fatal?: boolean`** — fixed: narrowed to `fatal?: true`; no other repo code consumes `PollResult` yet.

Verification (both, independent): `npx jest poll-client` 21/21; `npx tsc --noEmit` 0 errors; grep confirms zero production callers.

## Residuals — DEFERRED (both reviewers classified non-blocking)
- **[MEDIUM] onProgress-aborts-signal still returns `{done}`** (Codex) / (Claude note #2). Both: deliberate per the approved fix brief; arguably correct since the terminal state was genuinely reached; the real `IngestProgressBanner` `onProgress` (fireIfAdvanced → parent refetch) never aborts the signal. Owner: whole-branch review may reconsider. Not a production path.
- **[LOW] abortableSleep: stray default `setTimeout` not cleared / injected-sleep rejection swallowed** (Claude note #1 / Codex Low). Runs in the browser client — no long-lived Node event loop to keep alive; the default `setTimeout` never rejects; the ≤10s stray timer fires as an inert no-op (settled guard). Injected rejecting sleeps are test-only. Owner: whole-branch review.

## Decision
Convergence gate met (re-review round returned no new Blocking/High). Residuals deferred with rationale rather than spinning another fix+re-review round on accepted Medium/Low (avoids over-applying the iterative-review loop on a small contained change). **T1 done.**
