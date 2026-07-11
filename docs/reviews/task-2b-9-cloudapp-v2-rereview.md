# Task 9 Re-Review (round 2) — CONVERGED

**Artifact:** CloudApp after fix `da58db1` (full task diff `b2d35ed..da58db1`). **Date:** 2026-07-11.
**Reviewers:** Codex (gpt-5.5) + Claude (independent). **Verdict: CONVERGED — no new Blocking/High/Medium.**

## Prior High — both confirm fixed
- **[HIGH] retained playlistUrl → wrong-playlist Refresh.** `playlistUrl` now DERIVED (`urlEntry.playlistId === playlistId ? url : null`), computed in render body — no render can show the wrong playlist's URL (correct by construction, timing- and key-independent). Stale `listVideos(A)` while viewing B is double-guarded (reqSeq drops it; derivation renders it inert). Adding `playlistId` to `fetchVideos` deps causes no thrash (cloudScope memoized on playlistId → atomic change; banner holds onProgress in a ref so no effect re-fire). Removing the manual reset is safe (revisiting same playlist shows null until its fetch completes — identical UX). onRefresh/disabled/401/IngestError intact.

## Honest test note
The new discriminating test does NOT RED-vs-old in RTL — `act()` flushes the reset effect, so the original retained-state window was sub-frame (never observable/user-hittable). The fix is a correctness-by-construction improvement, not an observable-bug fix; the test is a forward regression guard. Both reviewers + the fixer independently confirmed this.

## Deferred (Low, both non-blocking)
- Codex Low: pre-effect window where a stale `listVideos(A)` could briefly set A's **video list** (display-only, explicitly "not a re-POST risk" — spend path protected by derivation). Same benign sub-frame class. Whole-branch follow-up.
- Claude Low (R1): onRefresh's createIngest result not null-checked before setSummary — fails safe (id-match gate).

cloud-app-ingest 5/5, cloud-app (2a+2b) 14/14, full suite 1954, tsc 0. **T9 done.**
