# Dual Adversarial Review — `fix/videos-list-observability`

**Branch:** `fix/videos-list-observability` · **merge-base:** master @ `592db35` · **HEAD:** `fab5e61`
**Date:** 2026-07-14
**Reviewers:** Claude (opus) + Codex (gpt-5.5), independent, two rounds to convergence.

## Scope
Two concerns surfaced by a live local run (a Korean-title video dead-lettered on BUG-4, leaving a title-less reserved-slot row `{id, serialNumber}`):
- **BUG-3 fix** — `sortVideos` (`app/api/videos/route.ts`) dereferenced `a.title`/`overallScore`/`ratings`/`durationSeconds` unguarded → one incomplete row threw an uncaught `TypeError` → `GET /api/videos` 500 → the whole playlist list failed, hiding the videos that DID complete. Fix: a missing sort key sorts LAST regardless of direction (uniform with the pre-existing `channel`/`personalScore` handling).
- **Observability** — wired the existing `lib/dev-logger` `logError` into 11 route error paths (videos, jobs poll + enqueue, jobs/cancel, pdf, html×2, playlists/[id], playlists/channel, resolve-folder, videos/[id]/review, share/revoke-all, normalize-folder) that mapped an unexpected error to a 5xx without logging it.

Commits: `6f89117` (BUG-3 + exemplar) · `aa32895` (9-route sweep) · `cc595f2` (round-1 fixes) · `fab5e61` (round-2 Lows).

## Round 1 — findings (both fixed)
- **Codex High** — `language`/`videoType`/`audience` coalesced missing values to `''`/rank-0 *before* the nulls-last guard, so an incomplete row sorted FIRST for ascending, violating the fix's own "missing sorts last regardless of direction" invariant. **Fixed** (`cc595f2`): preserve `undefined`, fall through to the shared tail. +3 tests (RED→GREEN); confirmed no existing test asserted the old coalesce behavior.
- **Claude High/Important** — `POST /api/jobs` catch-all mapped unexpected errors to 500 with zero logging — the same swallow anti-pattern fixed elsewhere, in the same file as the instrumented GET poll. **Fixed** (`cc595f2`): `logError('jobs:enqueue', e)` before the 500.
- Process note: an earlier `tsc --noEmit | tail && echo` masked tsc's exit code; a latent `TS18048` narrowing error in the nulls-last tail was hidden. **Fixed** by rewriting the tail to narrow via `== null`; tsc now verified by exit code 0.

Reviewers split on the `language`/`videoType`/`audience` case (Codex High vs. Claude non-blocking); resolved by fixing it (uniformity) rather than shipping a disputed finding.

## Round 2 — convergence (both: 0 Blocking / 0 High)
- Both verified the two round-1 fixes are **genuine** (not reworded): incomplete rows sort last for `language`/`videoType`/`audience` in **both** directions (the nulls-last branch returns before applying `order`); `jobs:enqueue` logging is correctly placed only on the unexpected-500 path.
- Both assessed the `videoType`/`audience` behavior change (complete-but-unclassified videos now sort last) as **acceptable/uniform, not a regression** — `types/index.ts` marks them `.optional()` and the Gemini schema does not require them, so sorting absent classifiers last is correct and consistent with the file's convention.
- `== null` tail confirmed correct (catches undefined+null, stable `0` for two-missing, no asc/desc asymmetry).
- Low notes closed in `fab5e61`: `language`/`videoType`/`audience` tests now assert both asc AND desc; `audience` branch uses `== null` for null/undefined consistency.

**Convergence:** a full dual re-review round with no new Blocking/High → stop condition met.

## Verdict: MERGEABLE
No unresolved Blocking/High. Full unit **2232/2232**, `tsc --noEmit` exit 0. Merge is a **human gate** (push `fix/videos-list-observability` → PR → merge, `--repo kujinlee/youtube-playlist-summaries-cloud`).

## Related / out of scope (tracked separately in docs/local-validation-findings.md)
- **BUG-4** — Korean/non-ASCII titles → "Invalid key" storage rejection (the dead-letter that *created* the orphan row); this branch fixes the crash symptom, BUG-4 is the cause.
- **Reservation-release** — deferred to the deploy trigger.
