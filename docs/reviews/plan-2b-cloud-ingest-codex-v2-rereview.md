# Codex Adversarial Re-Review — Stage 2b Plan v2 (Round 2)

**Reviewer:** Codex (gpt-5.5). **Artifact:** plan v2 (`7040d8d`). **Date:** 2026-07-11.
**Verdict:** No new Blocking; **3 new High + 1 Medium + 1 Low — not converged.** All 12 Round-1 fixes confirmed genuine.

## New findings

1. **[HIGH] Task 7 treats `timedOut` as done/mixed instead of give-up.** The `{ done | timedOut }` branch falls through to `done` when no failures — but the 10-min cap is a give-up path ("Lost connection…", spec §6). *Fix:* handle `'timedOut' in result` → `{ kind: 'gaveup' }` before terminal resolution. **(v3: fixed)**

2. **[HIGH] Task 7 tests use impossible job snapshots (Round-1 impossible-mock reintroduced).** `status()` returns `jobs:[]` for every status, but the banner polls `…then(r => r.jobs)` and `pollUntilTerminal` recomputes `rollup(rows)` — so terminal is never reached; progress→done and mixed tests can't go green. *Fix:* build `jobs` from bucket counts. **(v3: fixed via `jobsFrom`)**

3. **[HIGH] Task 9 Refresh can re-POST the wrong playlist after A→B nav.** `playlistUrl` set only after `listVideos` resolves; the playlist-change effect clears videos/sort but not `playlistUrl`, so A's URL stays live until B loads. *Fix:* reset `playlistUrl`/`refreshError` on playlist change. **(v3: fixed)**

4. **[MEDIUM] Task 7 freezes the first `onProgress`.** Effect deps = `[playlistId]`, but `refetchVideos` changes with sort; a mid-ingest refetch can overwrite the user's current sort. *Fix:* hold `onProgress` in a ref. **(v3: fixed via `onProgressRef`)**

5. **[LOW] Task 1 abort test doesn't prove abort-during-wait.** Add a controlled `sleep`, abort before resolving, assert `{aborted}` with no extra fetch. **(v3: added)**

## Round-1 fixes confirmed genuine

Task 1 defaults/pre-abort/isFatal-before-counter/onProgress-isolation/backoff; no production callers; token rewrite genuine; Task 7 no stale `state` read + probe-first; empty/terminal probe no longer polls; 401 probe+poll → `/login`; give-up only-when-live; onProgress skips terminal; `fireIfAdvanced` keyed on completed+failed+dead_letter; Task 6 focus trap + submit guards; Task 9 real `fetchVideos`/`playlistUrl` + id-gated summary; Task 10 real harness + 8-arg `enqueue_job` + `status='completed'` → terminal.
