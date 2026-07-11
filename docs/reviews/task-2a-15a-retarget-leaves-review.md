# Dual Review — Stage 2a Task 15a (retarget shared leaves + LocalApp ScopeProvider)

**Date:** 2026-07-11 · **Diff:** `bec439f..b1285ff` · **Severity disagreement — controller adjudicated.**

## Verified clean (both passes agree)
- **LocalApp 331-line churn = pure re-indentation** (`git diff -w` → only: useMemo import, ScopeProvider import, memoized local scope, `<ScopeProvider>` wrapper; zero logic change).
- StarRating/NoteCell save requests **byte-identical** (`POST /review` body `{outputFolder, personalScore|personalNote}`).
- Leaves use `useScope()`+apiClient, no inline fetch; markup + onChange callbacks unchanged; VideoRow drops only the 3 leaf outputFolder passes (keeps it for VideoMenu/Corrections).
- Scope **memoized** (`useMemo([outputFolder, baseOutputFolder])`) → VideoQuickView effect stable.
- Test rigor **NOT weakened** — component tests now assert `apiClient` call with `LOCAL_SCOPE`+patch (LOCAL_SCOPE carries outputFolder, coverage survives); `client-api.test.tsx` still asserts exact local URL+body; VideoQuickView tests strengthened.
- CloudApp/VideoMenu untouched (T15b deferral clean); LocalApp is the ONLY mount point → no `useScope` throw.

## Findings + adjudication
- **Codex Blocking (getQuickView `+` vs `%20`):** DOWNGRADED to Minor/accepted. Controller-verified: the local quick-view route parses via `new URL().searchParams.get()` (WHATWG), which decodes `+`→space identically to `%20`, so the server receives the SAME `outputFolder`. **Route-equivalent, no functional regression**; consistent with `listVideos`'s existing `URLSearchParams` approach. (Codex itself said "route-equivalent"; the "EXACT HTTP request" bar was over-strict.)
- **Codex High / Claude Minor (NoteCell error text):** confirmed **fallback-only** — when the server returns `{error}` the text is byte-identical; only a bodyless non-2xx/network error now shows `handle()`'s `request failed with status N` instead of `'Save failed'`. Behavior (popover open, error shown, onChange not called) unchanged; arguably more specific. Minor.

## Disposition
**Accepted.** Controller adjudication: both Codex findings are functionally non-regressions (verified) — "local behavior identical" holds functionally. 0 true Blocking/High. Recorded Minors → whole-branch: (1) getQuickView local `+`/`%20` (route-equivalent); (2) NoteCell/StarRating fallback error wording. Task 15a complete. tsc 0, npm test 1862, integration 327. Review docs/reviews/task-2a-15a-retarget-leaves-review.md.
