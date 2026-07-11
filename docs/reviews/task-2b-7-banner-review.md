# Claude Task Review — Stage 2b Task 7 (IngestProgressBanner, §13)

**Reviewer:** Claude (independent subagent). **Diff:** `d9d814b..79438a8`. **Date:** 2026-07-11.

## Verdict (round 1)
- **Spec compliance:** ✅ — probe (single call; 401→/login guarded by !cancelled; total 0 / terminal → hidden; no unguarded post-await setState); onProgressRef assigned in render body; resolution order exact; cleanup cancelled+abort; 401-in-poll via isFatal; effect deps `[playlistId]` no thrash; StrictMode double-invoke safe (each IIFE closes its own cancelled/controller). Read poll-client.ts directly to confirm no post-unmount setState/fetch (abort wins before onProgress).
- **Code quality:** Approved. Real tokens only. jest 9/9, tsc 0.

## Notes / Minors
- Did NOT flag the `fireIfAdvanced` regression case (focused on terminal dedup, which it verified correct). Codex caught the `!==`-vs-`>` regression bug — fixed. (Complementary dual-review coverage.)
- **Minor:** stale comment "always uses the current sort" (copy-paste leftover; holds onProgress) — clarified in fix.
- **Minor:** test 9 cleanup passes trivially under real timers (2000ms interval > 50ms window); real guarantee is poll-client abort-ordering. Tied to the deferred timer item.
- Report give-up arithmetic double-counts one sleep (24000ms actual, not 34000) — doc-only, no test impact.
- No `role=status`/`aria-live` on the outer banner (sibling IngestSummaryNotice has role=status) — out of the brief's scope; a11y-parity follow-up.

## Controller adjudication
Fix Codex Medium (fireIfAdvanced `>`) + strengthen dedup test + comment clarity. Defer the abortableSleep timer-leak Medium (converged T1 primitive, browser no-op) to whole-branch. Re-review both per §13 (fireIfAdvanced is a behavior change). See `-codex.md` + `-v2-rereview.md`.
