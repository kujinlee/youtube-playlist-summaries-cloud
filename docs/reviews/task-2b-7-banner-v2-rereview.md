# Task 7 Re-Review (round 2) — CONVERGED

**Artifact:** IngestProgressBanner after fix `5c60647` (full task diff `d9d814b..5c60647`). **Date:** 2026-07-11.
**Reviewers:** Codex (gpt-5.5) + Claude (independent). **Verdict: CONVERGED — no new findings.**

## Prior finding — both confirm genuinely fixed
- **[MEDIUM] fireIfAdvanced** now `d > lastFired` (strict advance). Both traced: baseline seeded `lastFired = doneCount(probe)`; poll1 1→2 fires, regression 2→1 no-fire, repeat →2 no-fire, terminal 2→3 fires via post-loop `fireIfAdvanced(r)`. Legitimate advances still fire (2×); terminal advance not suppressed. Both reverted to `!==` and confirmed the new test fails (4 calls) vs passes with `>` (2 calls) — non-vacuous.
- Comment clarified (ref holds onProgress, not "sort").
- Resolution order, cleanup, probe guards, 401 routing byte-identical to round 1 (only line 39 + comment + additive test changed).

## Deferred (both agree non-blocking)
- **abortableSleep timer-leak** (poll-client.ts, converged T1 primitive) — untouched. Both: provably inert browser no-op, fixing it reopens a converged shared primitive for no benefit. Recorded as whole-branch follow-up. Not High+.

banner 10/10, full suite 1949, tsc 0. **T7 done.**
