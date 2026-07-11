# Task 10 Dual Review — jobs-poll-banner integration test (single-pass)

**Diff:** `da58db1..2082609`. **Date:** 2026-07-11. **Reviewers:** Codex (gpt-5.5) + Claude (independent).

## Owner isolation (security property) — BOTH confirm genuine & non-vacuous
Two real users; B reads via B's session client (anon key + user JWT, NOT service_role) through `SupabaseJobQueue.listByPlaylist` → real Postgres RLS path. Positive control (`ca` sees total≥1) guards against a false-negative from a broken seed. If RLS were dropped, B's query returns A's row (total=1≠0) → test fails. Service_role only seeds. Same mechanism as the accepted sibling `jobs-producer-polling` RLS test.

## Codex findings (test-strength)
- **[MEDIUM → FIXED] Rollup coverage partial** — only asserted `{total, terminal, completed}`, not the full 8-bucket shape → a zero-bucket/queued miscount would pass. *Fixed:* assert full bucket shape at `before` (all queued) AND a mixed terminal (1 completed + 1 failed → exercises the `failed` bucket through the store).
- **[MEDIUM → ACCEPTED] pollUntilTerminal is effectively a single terminal read** (both jobs terminal before the poll). *Accepted:* pollUntilTerminal's loop (queued→sleep→re-read→transition, backoff, onProgress, abort, isFatal) is exhaustively unit-tested in T1 `poll-client.test.ts`; the integration test's role is proving the store→poll wiring at real terminal state + RLS isolation, which it does. Forcing a live-DB mid-poll transition duplicates unit coverage for low marginal value.
- **[LOW → FIXED] Admin update error unasserted** — a silent update error would leave jobs non-terminal and (with `now:()=>0`) spin to a Jest timeout. *Fixed:* `expect(error).toBeNull()` on the terminal-drive updates.

## Claude — Spec ✅ / Approved
Independently confirmed session-client (not service_role) isolation path, positive control, no cross-test pollution (randomUUID keys), 7-arg enqueue_job. Judged the rollup granularity + poll short-circuit acceptable (granular behavior unit-covered elsewhere). No changes required.

## Outcome
Strengthened per Codex's cheap high-value Mediums/Low; single-read poll accepted (unit-covered). **T10 done** after fix + integration-green re-run.
