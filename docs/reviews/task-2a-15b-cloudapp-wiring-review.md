# Dual Review — Stage 2a Task 15b (CloudApp wiring + VideoMenu cloud allowlist)

**Date:** 2026-07-11 · **Diff:** `24c7aee..65e8a38` (+ fix commit)

## Verified clean (both passes agree)
- **Suspense** wraps the `useSearchParams` consumer (`CloudAppBody` + `PlaylistSidebar` under one boundary) — correct Next.js App Router requirement.
- **Cloud scope memoized** on `playlistId` → stable identity → no VideoQuickView/StarRating refetch loop.
- **VideoMenu cloud allowlist** via `useScope()`: cloud = "Watch on YouTube" + Archive/Unarchive only; every other item wrapped `{!cloudMode && …}`; **local menu byte-identical** (only wrapped, conditions unchanged).
- **VideoList/VideoRow changes local-safe:** only made `outputFolder`/`baseOutputFolder` optional with `''` defaults; LocalApp still passes real values → local unaffected. Regression surface checked (VideoList mocks VideoRow; PageIntegration goes through LocalApp/provider; VideoRow/selection tests already wrap ScopeProvider).
- Callbacks: onArchive→`setArchived`(optimistic), onAnnotationChange→state-only (no money call), sort→refetch, doc callbacks→memoized noop. Empty states: pick-a-playlist; "No videos here yet" (§8.1 verbatim). tsc clean.

## Findings + adjudication
- **Codex High (real gap, controller-confirmed) → FIXED:** `PlaylistSidebar.listPlaylists()` caught ALL errors into inline text — an expired session on the sidebar (the first cloud-load fetch) showed a stuck error instead of redirecting to `/login`. CloudApp's 401→/login only covered `listVideos`/`setArchived`. Claude verified those two but did not inspect the sidebar path; Codex's broader coverage caught it. **Fixed:** PlaylistSidebar redirects on `UnauthorizedError` + RED→GREEN test (Codex Medium-2 test gap closed too).
- **Low (both) → FIXED:** sort indicator desync — playlist switch refetched default order but didn't reset `sortColumn`/`sortOrder`. Fixed (reset on playlist-change effect).
- **Medium (Codex, accepted): menu label** "Watch on YouTube" vs spec's illustrative "Open on YouTube" — kept consistent with the local menu (same component/item; the YouTube link is present). Note only.
- **Minor (Claude, accepted → whole-branch):** unspecified pick-a-playlist/error copy (only §8.1 + "no playlists yet" spec-mandated, both matched); no retry affordance on non-401 load error (2a-acceptable).

## Disposition
0 Blocking; 1 High (sidebar 401) + 1 Low (sort reset) FIXED with tests; cosmetic Medium/Minors accepted → whole-branch. Task 15b complete. **Completes plan Task 15 (T15a+T15b).** VideoMenu local-unchanged verified; local behavior preserved throughout. Review docs/reviews/task-2a-15b-cloudapp-wiring-review.md.
