# Reservation Release Lifecycle — Design Spec

**Date:** 2026-07-15
**Status:** Draft (Phase 1 — pending dual adversarial review + user approval)
**Scope class:** Money path (irreversible spend fuse) → requires **iterative dual adversarial review to convergence** per `docs/dev-process.md`.
**Trigger:** Must land before the Fly.io deploy / before any real traffic.

---

## 1. Problem

`spend_ledger` is a **reserve-only** daily spend fuse. Every generation and serve reserves worst-case cents against a global per-UTC-day cap, but **no code ever releases a reservation** and `actual_cents` is never written. Reservations only clear at UTC-midnight rollover (a fresh ledger row).

Consequence: a reservation for work that produced **nothing** (a failed/cancelled generation, a serve whose Gemini call threw) permanently consumes the day's budget. With shipped defaults (`daily_cap_cents=500`, `summary_est_cents=150`), ~3 failed generations exhaust the *entire system's* budget until midnight. A Gemini outage or retry burst **self-DoSes all users at ~$0 real spend**. This is the acute blocker for real traffic.

### Root cause (grounded in code)
- `spend_ledger` (`supabase/migrations/0011_cost_guardrails.sql:12-18`): `day` PK, `reserved_cents`, `actual_cents` (declared but inert — "written by the deferred reconcile"), `updated_at`.
- Reserve sites (increment-only, never released):
  - **Generation:** `enqueue_job` (latest `0018_enqueue_dig.sql:60-64`) reserves `v_est` (= `summary_est_cents`/`dig_est_cents`), then stamps `jobs.reserved_cents` (`0018:67`).
  - **Serve:** `reserve_serve_model` (latest `0014_serve_owner_budget.sql:74-85`) reserves `magazine_est_cents` in **both** `serve_owner_budget.spent_cents` (per-owner, `0014:74-78`) and `spend_ledger.reserved_cents` (global, `0014:81-85`).
- No terminal transition touches the ledger: `complete_job` (`0008_jobs_queue.sql:128-141`), `fail_job` (`0008:143-165`), `sweep_expired_leases` (`0009:63-77`), `request_cancel_job` (`0010_cancel_job_rowcount.sql:7`) — none reference `spend_ledger`.
- `jobs.reserved_cents` (added `0011:40`) is stamped at enqueue and today read only by tests — it is the ready-made hook for a release amount.
- A retry does **not** re-enter `enqueue_job`; the same job row is re-claimed (`claim_next_job`, `0008:96`, bumps `attempts`). One `enqueue_job` = one reservation, regardless of attempts.

---

## 2. Decision Summary

Three decisions taken during brainstorming (all confirmed with the user):

1. **Accounting depth = release-only.** Credit the reservation back when work terminates without a kept artifact. Do **not** write `actual_cents`; do **not** read Gemini `usageMetadata`. Successful work keeps its worst-case charge. Fail-safe: over-counts real spend, never under-counts.
2. **Scope = generation + serve.** Both reserve sites feed the same global fuse, so both get a release path.
3. **Serve crash residual = accepted.** Handle the common in-request serve failure (Gemini throws → release). A hard process crash after reserve but before the release call leaks `magazine_est_cents` (6¢) until UTC midnight — bounded (≤ `per_owner_serve_daily_cents`=60¢/owner/day), fail-safe, self-heals. No serve-lease-expiry sweep in this slice.

**Deferred (documented, not built here):** real-cost settle (`actual_cents` via `usageMetadata`); serve-lease-expiry sweep; backfill of already-leaked reservations (a fresh deploy starts clean; local dev can be reset).

---

## 3. The Money Invariant

For each UTC day `d`:

> `spend_ledger.reserved_cents[d]` = Σ estimates of all reservations made on day `d` that are **still in-flight OR converted to a kept artifact**.

A reservation is **released** (credited back) **iff** it reaches a terminal state that produced **no kept artifact**. Because `actual_cents` stays 0, the cap predicate `reserved_cents + actual_cents + est ≤ daily_cap_cents` continues to bound real spend — conservatively (each success charged at worst-case `est`), never below true spend.

**"Kept artifact" rule, by function** (this is the crisp decision boundary):
- `complete_job` → the handler **succeeded** (the summary/dig blob was produced). **Always KEEP** — even when the final status is `cancelled` due to a `cancel_requested` race (the artifact still exists). complete_job never releases.
- `fail_job` → the handler **did not** produce an artifact. **RELEASE** when the terminal status ∈ {`failed`, `dead_letter`, `cancelled`}; **do not release** when it re-`queued`s (reservation reused by the retry).
- `sweep_expired_leases` → **RELEASE** when it gives up (→ `dead_letter`/`cancelled`); **do not release** when it re-`queued`s.
- `request_cancel_job` → a `queued` job that **never ran**; no artifact. **RELEASE**.
- Serve → **RELEASE** on materialization failure; **KEEP** on success (magazine cached).

---

## 4. Cross-Cutting Correctness Rules

These three rules apply to every release site and are the primary review targets.

1. **Atomic + exactly-once.** Each release executes **inside the same RPC** that performs the terminal state flip, within the same transaction, under the same guard predicate that already guarantees a single terminal write (`where ... and status = 'active'` for `complete_job`/`fail_job`; the `for update skip locked` expired-set for the reaper; the `status = 'queued'` guard for `request_cancel_job`). No new lock or race surface is introduced.

2. **Idempotent by zeroing the source.** The generation release reads `jobs.reserved_cents`, credits it back, and sets `jobs.reserved_cents = 0` in the **same** statement/transaction. A re-entry (double terminal write attempt) therefore credits 0. Serve release is bounded by a `serve_model_charge.reserved_cents` marker (§6) that can never go negative.

3. **Day-correct.** The release credits the ledger row for the reservation's **UTC day**, not the terminal day: `spend_ledger where day = (job.created_at at time zone 'utc')::date`. This handles a job enqueued at 23:59 UTC that fails at 00:01 the next day. If that row is absent (should not happen, but defensive), the release is a no-op.

**Underflow guard.** Every decrement uses `reserved_cents = greatest(0, reserved_cents - amount)` (and likewise for `serve_owner_budget.spent_cents`) so a data inconsistency can never violate the `>= 0` CHECK constraint. With correct idempotency, the clamp should never actually fire — it is defense-in-depth.

---

## 5. Generation Path (jobs)

Fold a release step into the existing terminal RPCs. New migration(s) `create or replace` these functions verbatim except for the added release, preserving signatures/grants/ownership.

| Terminal transition | Function (migration) | Action |
|---|---|---|
| `completed` (or `cancelled` via cancel-after-success) | `complete_job` (`0008:128-141`) | **KEEP** — no ledger change |
| `failed` / `dead_letter` / `cancelled` | `fail_job` (`0008:143-165`) | **RELEASE** |
| re-`queued` (retryable) | `fail_job` | KEEP (reservation reused) |
| `dead_letter` / `cancelled` via reaper | `sweep_expired_leases` (`0009:63-77`) | **RELEASE** |
| re-`queued` via reaper | `sweep_expired_leases` | KEEP (reservation reused) |
| `cancelled` while `queued` | `request_cancel_job` (`0010:7`) | **RELEASE** |

**Release operation (generation):** given the job row `j` transitioning to a release-terminal status, in the same transaction:
```sql
update spend_ledger
   set reserved_cents = greatest(0, reserved_cents - j.reserved_cents),
       updated_at = now()
 where day = (j.created_at at time zone 'utc')::date;
-- and, in the same RPC, zero the per-job hook so re-entry is a no-op:
--   j.reserved_cents := 0   (persisted on the jobs row update the RPC already performs)
```
`fail_job` and `sweep_expired_leases` already branch on the computed terminal status (`fail_job` `0008:152-156`); the release is gated on that same branch (only the non-`queued` terminals). `request_cancel_job` releases unconditionally on a successful `queued → cancelled` flip.

**Note (cancel-after-success):** `complete_job` sets `cancelled` when `cancel_requested` is true (`0008:134`) but the handler had already succeeded — the artifact exists, so complete_job **keeps**. Only `fail_job`'s `cancelled` (handler did not succeed) releases. This asymmetry is intentional and is a required review checkpoint.

---

## 6. Serve Path (magazine materialization)

The serve reserve is a **lease-per-attempt** model (`reserve_serve_model`, `0014:22-95`) deliberately built with "no release RPC" (charge-per-attempt is the abuse bound). We add a scoped release for the common in-request failure.

**Schema change:** add an unsettled-reservation marker to `serve_model_charge` (`0012:7-15`):
```sql
alter table serve_model_charge
  add column reserved_cents int not null default 0 check (reserved_cents >= 0);
```
- `reserve_serve_model` (the `'reserved'` branch, `0014:87`) additionally does `reserved_cents = reserved_cents + magazine_est_cents` on the `serve_model_charge` row.
- New RPC **`release_serve_model(p_playlist_id uuid, p_video_id text)`** (SECURITY DEFINER, `auth.uid()`-derived owner, mirroring `reserve_serve_model`'s definer/search_path attributes verbatim; grants: `authenticated, anon`). It credits back **one** `magazine_est_cents` bounded by the marker:
```sql
-- only if there is an unsettled reservation to release (idempotent, can't over-release)
update serve_model_charge
   set reserved_cents = reserved_cents - v_cfg.magazine_est_cents
 where owner_id = v_owner and doc_key = v_doc_key and day = v_day
   and reserved_cents >= v_cfg.magazine_est_cents;
if found then
  update serve_owner_budget
     set spent_cents = greatest(0, spent_cents - v_cfg.magazine_est_cents)
   where owner_id = v_owner and day = v_day;
  update spend_ledger
     set reserved_cents = greatest(0, reserved_cents - v_cfg.magazine_est_cents),
         updated_at = now()
   where day = v_day;
end if;
```
- `attempt_count` (the K-day bound) is **NOT** credited back — a failed materialization still burns an attempt, so release can never become an infinite retry loop.
- **Reservation day for serve:** the serve reserve and release both happen in the same request within seconds, so `v_day = (now() at utc)::date` is correct for both. (A serve that spans midnight is out of scope; the marker simply won't match on the next day and release becomes a no-op — safe.)

**Caller change (`lib/html-doc/serve-doc.ts`):** wrap the post-reserve materialization (`generateMagazineModel` at `serve-doc.ts:81` + the model write) in `try/catch`. On the `'reserved'` branch, if materialization or the write throws → call `release_serve_model(...)` then re-throw. On success → no release (keep). The `'in_flight'`/`'at_capacity'`/`'denied'` branches never reserved, so they never release.

---

## 7. Enumerated Behaviors (test contract)

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | Success keeps charge | Job handler returns; `complete_job` → `completed` | `spend_ledger.reserved_cents` unchanged; `jobs.reserved_cents` unchanged |
| 2 | Non-retryable fail releases | Handler throws `NonRetryableError`; `fail_job` → `failed` | ledger `reserved_cents -= est` on reserve-day row; `jobs.reserved_cents → 0` |
| 3 | Dead-letter releases | Retryable fail, `attempts ≥ max`; `fail_job` → `dead_letter` | ledger released; `jobs.reserved_cents → 0` |
| 4 | Cancel-mid-run releases | `cancel_requested` + handler throws; `fail_job` → `cancelled` | ledger released |
| 5 | Retry reuses one reservation | Retryable fail, `attempts < max`; `fail_job` → `queued` | **no** release; `jobs.reserved_cents` unchanged; next attempt does not re-reserve |
| 6 | Reaper re-queue keeps | Lease expires, `attempts < max`; `sweep` → `queued` | **no** release |
| 7 | Reaper give-up releases | Lease expires, `attempts ≥ max`; `sweep` → `dead_letter`/`cancelled` | ledger released |
| 8 | Cancel queued releases | `request_cancel_job` on a `queued` job | ledger released; `jobs.reserved_cents → 0` |
| 9 | Cancel-after-success keeps | `cancel_requested` but handler already succeeded; `complete_job` → `cancelled` | **no** release (artifact exists) |
| 10 | Midnight-span day-correct | Job `created_at` day X, fails day Y | release credits day **X** ledger row, not day Y |
| 11 | Double-terminal idempotent | Two terminal-write attempts for one job | second credits 0 (`jobs.reserved_cents` already 0) |
| 12 | Cap re-opens after release | Reserve to cap, then a failure releases | subsequent `enqueue_job`/`enqueue_preflight` admits again |
| 13 | Serve fail releases both | `generateMagazineModel` throws; catch → `release_serve_model` | `spend_ledger.reserved_cents` and `serve_owner_budget.spent_cents` each `-= 6`; `serve_model_charge.reserved_cents -= 6`; `attempt_count` unchanged |
| 14 | Serve success keeps | Materialization + write succeed | no release |
| 15 | Serve release idempotent | `release_serve_model` called twice for one reservation | second is a no-op (marker `< magazine_est_cents`) |
| 16 | K-bound survives releases | K failed serves, each released | `attempt_count` reaches `max_serve_attempts` → `'attempts_exhausted'`; no infinite retry |
| 17 | Serve crash residual (accepted) | Process dies after reserve, before catch | 6¢ remains reserved until midnight; documented, not a test failure |

---

## 8. Edge Cases

- **Underflow:** all decrements clamped `greatest(0, …)`; correct idempotency means the clamp is never load-bearing.
- **Missing ledger/budget row on release:** defensive no-op (the `where day = …` matches nothing). Cannot happen on the normal path (reserve created the row).
- **Concurrency:** release lives inside the terminal RPC's existing single-writer guard; two workers cannot both terminal-write the same job (`where status='active'` + lease token). The reaper and a live worker cannot both release (the reaper only touches `status='active' and lease_expires_at < now()`, and flips status atomically).
- **Serve double-fire:** the marker column makes `release_serve_model` self-bounding; a retry within the same day that reserved again would set the marker back up, and each release consumes exactly one `magazine_est_cents`.

---

## 9. Testing Strategy

**Against real PostgREST + Postgres** — not mocks. (BUG-1 lesson: a mocked money test missed a real PostgREST param-drop that dead-lettered every job.) Integration tests exercise the real RPCs and assert exact ledger/budget/job-column deltas for behaviors 1–16; behavior 17 is asserted as documented-residual (reserve without release leaves the marker set). Include a concurrency test: two claimants race a terminal write → exactly one release. Include the midnight-span test (behavior 10) by inserting a job with a back-dated `created_at`.

---

## 10. Out of Scope / Deferred

- **Real-cost settle (`actual_cents`).** Read `usageMetadata` at each `lib/gemini.ts` `generateContent` site, accumulate across a job's passes, price with the existing `lib/gemini-cost.ts` constants, and write `actual_cents` in an atomic settle. Efficiency win (~3–5× throughput per cap); safe-on-crash (falls back to the kept reservation). Its own slice, when the cap constrains real traffic.
- **Serve-lease-expiry sweep.** Would close the accepted serve crash residual. Deferred (bounded, self-healing).
- **Backfill.** Existing leaked reservations are not reconciled by this slice. A fresh deploy starts with an empty ledger; local dev resets today's row manually (already done this session).

---

## 11. Review Requirements

Money path + concurrency + idempotency → **iterative dual adversarial review to convergence** (Codex + Claude, independent), re-reviewing the *revised* SQL each round until a round returns no new Blocking/High. Explicit review targets: the cancel-after-success asymmetry (§5 note), day-correctness (§4.3), exactly-once under concurrent workers/reaper (§4.1), serve marker idempotency (§6), and the underflow clamp never masking a real logic error.
