# Claude Adversarial Review — Stage 2b Cloud Ingest Plan (Round 1)

**Reviewer:** Claude (independent subagent, full source access).
**Artifact:** `docs/superpowers/plans/2026-07-11-stage-2b-cloud-ingest.md` (commit `17f5f57`).
**Date:** 2026-07-11.
**Verdict:** NOT ready as written. 2 Blocking + confirms Codex's 3rd, 3 High, 4 Medium, 2 Low. All contract types verified correct against source (see "verified correct" list).

## Blocking

1. **Design tokens do not exist → components render unstyled.** Real `app/globals.css` tokens: `--surface-base/-raised/-overlay`, `--border/-strong`, `--text-primary/-secondary/-muted`, `--accent`, `--success`, `--warning`, `--danger`. Plan/spec §7 use `--bg`, `--text`, `--bg-elevated`, `--warn`, `--progress-track`, `--progress-fill` — all dead. Progress bar has no track/fill color = invisible. jsdom can't catch it. *Fix:* `--bg`→`--surface-base`, `--bg-elevated`→`--surface-raised`, `--text`→`--text-primary`, `--warn`→`--warning`; progress track→`--border`, fill→`--accent`. Fix spec §7 (the root).

2. **Task 7 tests are RED-forever.** Draft hardcodes `intervalMs:2000`; "progress→done"/"mixed" tests use default 1000ms `waitFor` (done appears at ~2000ms → timeout); give-up test caps at 3000ms but backoff sums ~24s. The "inject 200ms" note is self-contradictory (no seam; 200ms prod = 5 req/s for 10min = guardrail regression). *Fix:* keep prod 2000/10000, drive give-up test with fake timers.

3. **(Confirms Codex #3) Task 7 draft state machine can never resolve done/mixed** — `live` never set true, reads stale `state` in async closure. Replace with `liveRef`/probe-first.

## High

3H. **`playlistUrl` not in `PlaylistLibrary` state.** `fetchVideos` (`CloudApp.tsx:89-104`) does `setVideos(result.videos)` and discards `result.playlistUrl`. Task 9's `onRefresh` references an undefined `playlistUrl`. *Fix:* add `playlistUrl` state, set it in `fetchVideos`, guard Refresh until loaded.

4H. **`onProgress={loadVideos}` — no such fn.** Real refetch is `fetchVideos(col, order)` (required args). *Fix:* `refetchVideos = () => fetchVideos(sortColumn, sortOrder)`.

5H. **Summary-clear effect race + lint footgun.** A `useEffect([playlistId])` reading `summary?.playlistId` trips exhaustive-deps; adding `summary` to deps wipes the just-set notice on async `router.push`. *Fix:* don't use a clear-effect — render the notice iff `summary?.playlistId === playlistId`, clear only on dismiss; test cross-playlist navigation.

## Medium

6M. **Cross-nav leaks a live poll loop up to 10 min** (Codex #1) — `pollUntilTerminal` uncancellable. Add `AbortSignal` in Task 1.

7M. **Parent refetches on every poll, not on change.** Banner fires parent `onProgress` every 2-10s → dozens of redundant full-list refetches. *Fix:* dedupe via a ref on `completed+failed`.

8M. **Modal not focus-trapped** though spec §7 mandates it. *Fix:* minimal Tab/Shift-Tab trap + test.

9M. **Task 10 integration test targets the HTTP route handler**, which the Jest harness can't authenticate (`cookies()` unpopulated); `asOwner`/`markCompleted` helpers don't exist. *Fix:* mirror `jobs-producer-polling.test.ts` — seed via admin, assert `rollup(await queue.listByPlaylist(pl))` + terminal transition + owner isolation.

## Low

10L. **`✕` not disabled while submitting** (Cancel is) → close mid-submit then `onSuccess` navigates. *Fix:* guard ✕ too, and bail `onSuccess` if closed.

11L. **`ingestErrorMessage` 422 interpolates `undefined`** if body omits limit/found. *Fix:* generic fallback when either missing.

## Verified correct (no change)

Contract types (`ProducerResult`, `ProducerCounts`, `JobFanoutResult`, `playlistId: string|null`, `Rollup`, `PollOptions`, `PollResult`, `pollUntilTerminal`, `PlaylistJobRow`, `PlaylistSummary.playlistKey`, `VideoListResult.playlistUrl`, `UnauthorizedError`, `handle`, `Scope`, `useScope`); POST returns `{...ProducerResult, challengeRequired}` always-present; status codes + `Retry-After: 60` only on 429; guardrail matrix copy incl. 503 dual-cause collapse and daily-cap double-count guard; Task 1 `onProgress` placement + backward-compat (no prod callers); first-snapshot no-flash (once `liveRef` fix applied); §9 six dismissal paths; global constraints (no service-role, `merge_video_data` untouched, local path untouched, no guardrail weakened; "zero backend change" true).
