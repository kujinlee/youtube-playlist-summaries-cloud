# Codex Adversarial Review — Stage 2b Task 7 (IngestProgressBanner, §13)

**Reviewer:** Codex (gpt-5.5). **Diff:** `d9d814b..79438a8`. **Date:** 2026-07-11.
**Verdict:** No Blocking/High. 2 Medium + 2 Low.

## Findings
1. **[MEDIUM → FIXED] `fireIfAdvanced` uses `d !== lastFired`, not `d > lastFired`** (IngestProgressBanner.tsx:39). Fires on regressions as well as advances → spurious parent refetch on a stale/eventually-consistent lower snapshot, then re-fires when it climbs back. Violates "ONLY when advances." *Fixed* → `>`, plus a strengthened advance-only test.
2. **[MEDIUM → DEFERRED] abortableSleep doesn't clearTimeout** (poll-client.ts). Parked default timer lingers ≤10s after abort/unmount. Same benign item flagged in T1 (browser no-op, settled-guarded). Deferred to whole-branch (converged T1 primitive; restructure risk > benefit).
3. **[LOW → FIXED] "done+dedup" test not a real dedup test** — only asserts onProgress called, not advance-only. Closed by the strengthened test.
4. **[LOW → DEFERRED] cleanup test doesn't assert timer cleared** — tied to finding 2, deferred.

## Confirmed correct
Probe: no unguarded post-await setState (`if (cancelled) return` after probe). onProgress ref assigned in render body (not effect). 401 in poll → isFatal → failed+fatal → /login. Resolution order exact (aborted/fatal-failed/failed/timedOut/done-or-mixed). Effect deps `[playlistId]` — no thrash, restart on change. Real tokens (track `--border`, fill `--accent`). jest 9/9.
