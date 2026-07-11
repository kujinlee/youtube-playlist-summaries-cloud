# Codex Adversarial Re-Review — Stage 2b Plan v4 (Round 4, convergence check)

**Reviewer:** Codex (gpt-5.5). **Artifact:** plan v4 (`d876401`). **Date:** 2026-07-11.
**Verdict:** **1 High — NOT converged** (fixed in v5). All 7 Round-3 fixes confirmed genuine, incl. the deferred-A/B test validity.

## Finding

1. **[HIGH] Task 8 sidebar tests not fully updated.** The existing `tests/components/playlist-sidebar.test.tsx:101` and `:115` still assert `toBeDisabled()`. Task 8 adds an enabled-button test but doesn't remove the two disabled ones → after implementing Task 8, `npx jest playlist-sidebar` fails despite the plan expecting PASS. *Fix:* explicitly replace the two obsolete disabled tests with enabled-button expectations (non-empty: `onNewPlaylist` fires, no `fetch`; empty-state: button enabled). **(v5: Task 8 Step 1 now replaces both.)**

## Round-3 fixes confirmed genuine

1. Task 9 `reqSeq` guard after the await in both try + catch — stale A cannot setState.
2. Deferred-A/B test **valid** — `rerender` with `playlist=B` recomputes `cloudScope`, re-runs `[cloudScope]` effect, `fetchVideos(B)` bumps `reqSeq` to 2 (synchronously) before `resolveA`, A (seq 1) dropped. Not vacuous.
3. `jobsFrom: PlaylistJobRow[]` + `status as JobStatus`; `status(): {jobs; rollup: Rollup}` — strict-clean, typed mock accepts it.
4. `onProgressRef` assigned in render — no stale window.
5. Fake-timer leak closed (`afterEach` + unmount/clearAllTimers; idempotent double restore).
6. `status()` derives total+terminal from rows — probe/poll agree.
7. timedOut design bullet matches impl.

Cross-checks: `reqSeq` doesn't break mount/handleSort (latest-wins intended); stable ref, no deps issue; no nonexistent token/type/function in Tasks 1,2,5,6,7,9.

**NOT converged** (single narrow test-list High; fixed in v5).
