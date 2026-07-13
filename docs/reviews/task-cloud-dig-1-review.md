# Task 1 Review — 0018 enqueue_dig migration (CLEAN, converged)

Dual review of commit `1891398` (base `e09e1ed`). Diff: `enqueue_job` create-or-replace admitting `dig`, `tests/integration/enqueue-dig.test.ts`, one-line `cost-guardrails.test.ts` probe fix.

## Claude task-reviewer — ✅ Approved
- **Named-risk check (0011 vs 0018 body diff):** exactly two line differences — `create`→`create or replace` and the guard (`<> 'summary'` → `not in ('summary','dig')` + stale-comment removal). Every other line (declare, auth/owner checks, est/attempts `case` dispatch, retry loop, INSERT-or-JOIN, ON CONFLICT target/predicate, duration backstop, quota debit, spend_ledger reserve, revoke/grant) byte-identical. No drift.
- ON CONFLICT `(owner_id, playlist_id, video_id, section_id, job_kind, job_version) where status in (...)` matches live `jobs_idem_active` (0009:11-13, supersedes 0008).
- Anon test genuine: `anonSession()` (real `signInAnonymously()`) + asserts `is_anonymous===true` before PJ001. Idempotent-join asserts `usage_counters.used` stays 1 (real no-double-charge).
- `cost-guardrails.test.ts` `'dig'`→`'bogus'` correct: RPC kind guard fires before INSERT, so 'bogus' exercises the same `unsupported_job_kind` path.
- **Minor (non-blocking, rolled up):** enqueue-dig.test.ts doesn't pin `dig_est_cents`/`dig_max_attempts` before use — implicit dependence on no other file mutating them (grep confirms none today). Worth a comment if a future test tunes dig config.

## Codex adversarial — 0 Blocking / High / Medium / Low
No reproduction drift beyond the guard; ON CONFLICT matches index; signature/grants intact; tests assert quota debit / no-double-charge / genuine anon; `cost-guardrails` edit preserves unsupported-kind coverage.

## Disposition
Converged, no fixes required. Tests: enqueue-dig 3/3, full unit 192/192, integration 344/346 (2 pre-existing skips), tsc clean.
