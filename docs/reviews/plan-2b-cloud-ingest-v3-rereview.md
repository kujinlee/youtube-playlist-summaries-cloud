# Claude Adversarial Re-Review — Stage 2b Plan v3 (Round 3)

**Reviewer:** Claude (independent subagent, full source). **Artifact:** plan v3 (`2d9e316`). **Date:** 2026-07-11.
**Verdict:** **1 HIGH + 1 MEDIUM + 2 LOW — NOT converged.** All 5 Codex-R2 and 5 Claude-R2 findings verified genuinely fixed. The one High is a residual of the R2-H3 fix (same defect class, in-flight trigger), one-line-fixable.

## New findings

1. **[HIGH] Task 9 stale in-flight `listVideos` re-poisons `playlistUrl` → Refresh re-POSTs wrong playlist (residual of R2-H3).** `PlaylistLibrary` is unkeyed, so A→B *updates* the instance; A's late response runs `setPlaylistUrl(A.url)` on the B component. If A resolves after B, `playlistUrl` is stuck at A while viewing B; Refresh (enqueues jobs — money/irreversible) posts A. `disabled={playlistUrl===null}` doesn't help (it's non-null during the poison window). Blast radius partly contained (summary notice is id-gated). *Fix (one line):* scope/cancelled guard in `fetchVideos` before `setState`, or `key={playlistId}` on `PlaylistLibrary`. **(v4: `reqSeq` sequence guard — chosen over `key` to preserve filter/sort persistence across playlist switches)**

2. **[MEDIUM] Fake-timer tests lack `try/finally` around `useRealTimers()`** → a throw leaks frozen time into later real-timer tests, turning one real failure into a cascade of timeouts. *Fix:* file-scope `afterEach(() => jest.useRealTimers())`. **(v4: added)**

3. **[LOW] "renders N of M" parks the poll loop across the timer switch** — benign (no wakeup), but cleaner to `unmount()` + `clearAllTimers()` first. **(v4: added)**

4. **[LOW] "aborts during the wait" RED fails via ~5s Jest timeout, not the `now` backstop** — the controlled sleep never re-resolves, so RED parks (no permanent hang, just slow). Acceptable. **(v4: left as-is; noted)**

## New-defect hunt — cleared
`cancelled ∈ TERMINAL_STATUSES` (poll-client:3), no fixture sets it; no token/type/self-contradiction in v3 edits (`BannerState` + `PollResult` narrowing sound; `refetchVideos: () => Promise<void>` assignable to `onProgress?: () => void`; all tokens exist); Task 10 harness verified (`SupabaseJobQueue.listByPlaylist`, `adminClient/newUser/signInAs/ensureGuardrailHeadroom`, 8-arg `enqueue_job`).

## Round-2 findings CONFIRMED fixed
All 5 Codex-R2 (timedOut→gaveup, jobsFrom rows, Refresh reset mechanism, onProgressRef, abort-during-wait test) and all 5 Claude-R2 (impossible mock, split tests, abort RED backstop, CloudAppBody useRouter, probe-401 guard) genuinely fixed — traced against source, incl. the `await act` progress commit (not flaky) and the abort-during-sleep microtask choreography (reliable).
