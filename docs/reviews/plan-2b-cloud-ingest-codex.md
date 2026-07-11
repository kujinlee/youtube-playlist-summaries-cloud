# Codex Adversarial Review — Stage 2b Cloud Ingest Plan (Round 1)

**Reviewer:** Codex (gpt-5.5), run from coordinator Bash.
**Artifact:** `docs/superpowers/plans/2026-07-11-stage-2b-cloud-ingest.md` (commit `17f5f57`).
**Date:** 2026-07-11.
**Verdict:** 3 Blocking, 5 High, 2 Medium, 1 Low. Contract block verified accurate (POST returns `{...ProducerResult, challengeRequired}` top-level; `playlistId: string|null`; `Retry-After` only on 429).

## Blocking

1. **Task 7 does not cancel old polls on navigation/unmount.** `active=false` in cleanup only suppresses `setState`; `pollUntilTerminal` has no cancellation contract, so it keeps sleeping+fetching until terminal/timeout — an old playlist's poll runs up to 10 min after navigating away. *Fix:* add cancellation (`AbortSignal`) to `pollUntilTerminal` (Task 1) or give the banner a cancellable loop; test asserts no `getJobStatus(old)` after `playlistId` change.

2. **Empty first snapshot polls forever.** `rollup([]).terminal === false`, and the plan's hide decision lives only in `onProgress` (not a return), so an old playlist with zero jobs polls hidden indefinitely. *Fix:* one-shot probe before the loop; return immediately for `total===0` or terminal-first.

3. **Task 7 draft state machine can never resolve done/mixed.** The draft declares `let live=false` + `wasLive()` but never sets `live=true`; `origSet` unused; `if (!wasLive()) return` therefore suppresses all terminal states. The reviewer note says "replace it" but the task still ships broken code. *Fix:* replace the draft code itself — `liveRef.current=true` set exactly when entering `{kind:'progress'}`.

## High

4. **Give-up behavior vs test contradiction.** Impl shows give-up only if `sawFirst`; note says "only if live"; the give-up test rejects from the start with no live snapshot. *Fix:* decide product behavior (chosen: **only when live**) and fix the test to yield one non-terminal snapshot first, then reject.

5. **401 during polling is swallowed.** `getJobStatus` maps 401→`UnauthorizedError`, but `pollUntilTerminal` catches all errors and retries to `{failed}` → banner shows "Lost connection" instead of `/login`. *Fix:* non-retryable (`isFatal`) support, or catch `UnauthorizedError` in the probe before entering retry polling.

6. **Task 9 assumes `PlaylistLibrary` has `playlistUrl` state — it does not.** `listVideos` returns `playlistUrl` but `CloudApp` discards it (`fetchVideos` stores only `.videos`). *Fix:* add `playlistUrl` state, set it in `fetchVideos`, guard Refresh until loaded.

7. **Task 9 passes a nonexistent refetch callback.** Real refetch is `fetchVideos(col, order)` (required args); plan references `loadVideos` and passes it as `onProgress`. *Fix:* `refetchVideos = () => fetchVideos(sortColumn, sortOrder)`; pass that.

8. **Design tokens used by Tasks 5–8 do not exist.** Plan uses `--bg`, `--bg-elevated`, `--text`, `--warn`, `--progress-track`, `--progress-fill`. Real tokens (`app/globals.css`): `--surface-base/-raised/-overlay`, `--border/-strong`, `--text-primary/-secondary/-muted`, `--accent`, `--warning`, `--danger`. *Fix:* rewrite all snippets to real tokens; `--progress-track`→`--border`, `--progress-fill`→`--accent` (no globals.css change needed).

## Medium

9. **Task 6 omits the spec-required focus trap.** Spec §7 says modal focus-trapped; Task 6 only initial-focuses + restores. *Fix:* add focus-trap behavior + Tab/Shift+Tab test.

10. **Task 7 mixed-state test mocks impossible GET.** Test returns `jobs:[]` with `rollup.total:3`; the banner recomputes rollup from rows, so that terminal rollup is ignored and the test proves nothing. *Fix:* make mocked `jobs` match the desired rollup.

## Low

11. **`onProgress` throwing pollutes retry accounting.** If `onProgress` throws inside the fetch `try`, `pollUntilTerminal` counts it as a fetch failure. *Fix:* document `onProgress` must be synchronous/non-throwing, and have the banner's `onProgress` swallow its own refetch errors.
