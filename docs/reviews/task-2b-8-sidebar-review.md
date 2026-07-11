# Task 8 Dual Review — PlaylistSidebar un-disable (single-pass)

**Diff:** `5c60647..b2d35ed`. **Date:** 2026-07-11. **Reviewers:** Codex (gpt-5.5) + Claude (independent). **Verdict: CLEAN.**

## Claude — Spec ✅ / Approved (0 findings)
Both obsolete `toBeDisabled()` tests genuinely replaced (grep: zero `toBeDisabled` remain); `onNewPlaylist?: () => void` typed + threaded to onClick; no listPlaylists/fetch on click; disabled/title/cursor-not-allowed removed; existing behavior (list, null-title→"Untitled playlist", aria-current, empty, loading/error) untouched; real tokens; replacement tests non-vacuous (toBeEnabled + onNewPlaylist once + fetch-not-called). Optional prop preserves existing no-prop call sites (incl. CloudApp before T9).

## Codex — No Blocking/High. 1 Low (DEFERRED — redundant)
- **[LOW]** click test could add `expect(mockListPlaylists).toHaveBeenCalledTimes(1)` to directly lock "does NOT trigger listPlaylists." **Deferred as redundant:** the existing `global.fetch`-not-called assertion already proves this (`listPlaylists` → `handle` → `fetch`). Not a coverage gap. Whole-branch may add for explicitness.
Confirmed: optional prop valid at all call sites incl. CloudApp; button enabled + calls callback; tokens real.

playlist-sidebar 8/8, full suite 1949, tsc 0. **T8 done.**
