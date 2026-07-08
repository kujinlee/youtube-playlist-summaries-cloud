# Codex adversarial review — Stage 1D spec (round 1)

**Date:** 2026-07-08 · task `task-mrclxoks` · Target: `docs/superpowers/specs/2026-07-08-stage-1d-cost-guardrails-design.md`

## Blocking
- **B1 — Preflight gates bypassable by direct `enqueue_job`.** `enqueue_job` is granted to `anon`/`authenticated`, so a caller invokes it directly (or churns anon accounts), skipping `enqueue_preflight` → no hard per-IP velocity / `max_free_users` / queue-depth / CAPTCHA signal; only quota + daily-cap (which are in `enqueue_job`) apply. Per-IP velocity can't work in a client-callable RPC (client controls `p_enqueue_ip`). *Fix: move hard gates into `enqueue_job`, or revoke client execute and enqueue only via a trusted server path.* (Money is still bounded by the daily cap in `enqueue_job`; this is a fairness/availability + defense-in-depth hole.)
- **B2 — Release-on-terminal-failure breaks the cap after billed work.** A job reserves 30¢, reaches Gemini (billed), then fails/dead-letters; releasing the reservation frees ledger capacity while real spend remains → repeated billed-then-terminal jobs exceed `$DAILY_CAP`. *Fix: never release after any billable phase (reserve-and-hold), or release only definitely-pre-Gemini failures via a billable marker.*

## High
- **H3 — Queued cancellation leaks reservations.** `request_cancel_job` flips `queued→cancelled` directly; spec only added release to `fail_job`/`sweep`. A cancelled-while-queued job never releases → daily capacity falsely exhausted. *Fix: release in `request_cancel_job` too (or never-release, per B2).*
- **H4 — `dig` publicly enqueuable though unhandled.** `jobs` check allows `dig`; a caller enqueues `p_job_kind='dig'` → reserved, quota-debited, unhandled queue row. *Fix: reject `job_kind <> 'summary'` in `enqueue_job` until the dig worker ships.*

## Medium
- **M5 — SQLSTATE contract inconsistent:** both quota and cap errors use `P0001` → wrapper can't distinguish without string-matching. *Fix: distinct SQLSTATEs.*
- **M6 — No IP channel in the queue interface:** `JobQueue.enqueue(key, payload)` has no IP arg; impl will ship null IP. *Fix: carry enqueue IP through the signature.*

## Low
- **L7 — Month period uses session TZ** while daily spend uses UTC. *Fix: `date_trunc('month', now() at time zone 'utc')::date`.*
