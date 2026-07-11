# Codex Adversarial Review — Stage 2b Task 1 (pollUntilTerminal extension)

**Reviewer:** Codex (gpt-5.5, frontier). **Diff:** `eef22a7..f3663a3`. **Date:** 2026-07-11.
**Verdict:** No Blocking. 2 High + 1 Medium + 1 Low.

## Findings

1. **[HIGH] Abort can lose to terminal/failure when the signal aborts during `fetchRows()`** (poll-client.ts loop). If `fetchRows` aborts then returns a terminal row, the loop fires `onProgress` and returns `{ done: true }` before the post-fetch `signal.aborted` check → violates "when aborted → resolve `{ aborted: true }`". Same in the catch path: reaching `maxConsecutiveErrors` returns `{ failed }` before the abort check. *Fix:* check `signal.aborted` immediately after a successful `await fetchRows()` (before onProgress/terminal) and in the catch path (before isFatal/error-count).

2. **[HIGH] Abort does not interrupt the `sleep` await** (poll-client.ts). `signal.aborted` is only checked *before* `await sleep(delay)`, never during. With the default timer + long interval, cancellation is delayed up to `maxIntervalMs` (10s); with an injected never-resolving sleep the promise hangs. The "aborting during the wait" test manually calls `resolveSleep()`, so it does not prove abort itself wakes the waiter. *Fix:* race the sleep against an abort promise (abortable sleep) + post-sleep abort check; strengthen the test to NOT manually resolve.

3. **[MEDIUM] Timeout precedence changed** — new code checks `timeoutMs` at the top of the loop; the pre-diff primitive fetched first, then checked timeout. Edge case: a fetch that would return terminal exactly at the timeout boundary now returns `{ timedOut }` instead of `{ done }`. No production callers today (grep-confirmed), but a behavior change in shared code. *Fix:* keep the timeout check AFTER the fetch to preserve prior precedence.

4. **[LOW] `fatal?: boolean` is wider than described** — impl only emits `fatal: true` or omits; typing as `boolean` permits impossible `{ failed: true, fatal: false }`, weakening narrowing. *Fix:* type as `fatal?: true`.

`isFatal` retry behavior and synchronous `onProgress` isolation are implemented as requested; focused suite 19/19.
