# Codex Adversarial Re-Review — Stage 2b Plan v3 (Round 3)

**Reviewer:** Codex (gpt-5.5). **Artifact:** plan v3 (`2d9e316`). **Date:** 2026-07-11.
**Verdict:** 0 Blocking, **2 High + 2 Medium + 2 Low — NOT converged.** All 5 Codex-R2 fixes confirmed genuine.

## New findings

1. **[HIGH] Task 9 stale `listVideos(A)` can still set B's `playlistUrl` to A.** The reset closes the click window, not the in-flight-response window: if A's `fetchVideos` resolves after navigating to B, it runs `setPlaylistUrl(A.url)` on the B component → Refresh re-POSTs A (money path). *Fix:* request-sequence/scope guard in `fetchVideos` before `setState`. **(v4: `reqSeq` guard + deferred-A/B test)**

2. **[HIGH] Task 7 `jobsFrom` strict-TS failure.** Rows infer `status: string`, not `JobStatus`; the typed `getJobStatusMock` won't accept them under strict tsconfig. *Fix:* type as `JobStatus[]`/`PlaylistJobRow[]` or cast. **(v4: typed + `status as JobStatus`)**

3. **[MEDIUM] `onProgressRef` passive-effect stale window.** A poll callback firing after commit but before the ref-update effect calls the previous `onProgress` once. *Fix:* assign in render or `useLayoutEffect`. **(v4: assign in render)**

4. **[MEDIUM] Fake-timer progress test leaves the loop parked, no cleanup guard.** No `try/finally` around `useRealTimers()`; a throw leaks fake timers into later tests. *Fix:* `afterEach` restore + unmount/clear timers. **(v4: file `afterEach` + unmount/clearAllTimers)**

5. **[LOW] `status()` `.rollup.terminal` not derived from buckets** (harmless — poll ignores `.rollup` — but the comment promises agreement). *Fix:* derive terminal from rows. **(v4: derived)**

6. **[LOW] Task 7 design bullet contradicts fixed impl** (`{done|timedOut}→mixed/done`). *Fix:* update bullet. **(v4: fixed)**

## Round-2 fixes confirmed
timedOut→gaveup (impl); jobsFrom real rows (bucket sums correct; caveats = typing + terminal above); split progress test avoids batching; Task 9 reset contract + Refresh-disabled; CloudAppBody useRouter; probe-401 cancelled-guard; Task 1 abort tests (incrementing now, finite timeout, callable pre-aborted fetchRows, abort-during-sleep choreography adequate).
