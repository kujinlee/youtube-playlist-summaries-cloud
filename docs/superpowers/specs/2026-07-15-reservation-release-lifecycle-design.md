# Reservation Release Lifecycle — Design Spec (v2)

**Date:** 2026-07-15
**Status:** Draft v2 (revised after round-1 dual adversarial review — see §12). Pending re-review + user approval.
**Scope class:** Money path (irreversible spend fuse) → **iterative dual adversarial review to convergence** per `docs/dev-process.md`.
**Trigger:** Must land before the Fly.io deploy / before any real traffic.

### Terms used in this spec (plain-language)
- **Reserve:** before doing paid work, subtract a *worst-case estimate* from the day's budget so concurrent requests can't both overspend the last of it.
- **Release:** give a reservation back when the work ended without a kept result and (per v2) without having spent money.
- **Settle:** replace the estimate with the *real* cost after the fact. **Deferred to a later slice** — not built here.
- **Estimate vs actual:** estimate = the worst-case hold (`summary_est_cents`=150¢, `magazine_est_cents`=6¢). Actual = real cents spent (not tracked in this slice).
- **RPC:** a database function callable over the API (Postgres function exposed via PostgREST).
- **Terminal state:** a job's final status — `completed`, `failed`, `dead_letter`, `cancelled`. (`queued`/`active` are non-terminal.)
- **The reaper:** `sweep_expired_leases` — the periodic sweep that reclaims jobs whose worker died mid-run (lease expired).
- **Billable call:** a Gemini API call that costs money (`generateSummary`, `generateMagazineModel`, Gemini transcription).
- **Token / nonce:** a one-time secret string the server generates and holds, used to prove a later call is the legitimate owner of a specific reservation.

---

## 1. Problem

`spend_ledger` is a **reserve-only** daily spend fuse (one row per UTC day). Every generation and serve reserves worst-case cents against a global cap, but **no code ever releases a reservation** and `actual_cents` is never written. Reservations clear only at UTC-midnight rollover.

Consequence: a reservation for work that produced **nothing** (a failed/cancelled generation, a serve whose Gemini call threw) permanently consumes the day's budget. With defaults (`daily_cap_cents=500`, `summary_est_cents=150`), ~3 failed generations exhaust the *entire system's* budget until midnight. A Gemini outage or retry burst **self-DoSes all users at ~$0 real spend**. Acute blocker for real traffic.

### Root cause (grounded in code)
- `spend_ledger` (`supabase/migrations/0011_cost_guardrails.sql:12-18`): `day` PK, `reserved_cents`, `actual_cents` (declared but inert), `updated_at`.
- Reserve sites (increment-only, never released): `enqueue_job` (latest `0018_enqueue_dig.sql:60-64`, stamps `jobs.reserved_cents` at `0018:67`); `reserve_serve_model` (latest `0014_serve_owner_budget.sql:74-85`, into **both** `serve_owner_budget.spent_cents` and `spend_ledger.reserved_cents`).
- No terminal transition touches the ledger: `complete_job` (`0008:128-141`), `fail_job` (`0008:143-165`), `sweep_expired_leases` (`0009:63-77`), `request_cancel_job` (`0010:7`), `request_cancel_playlist_jobs` (`0019_share_tokens_cascade.sql:45`).
- A retry re-claims the same row (`claim_next_job`, `0008:96`, bumps `attempts`); it never re-enters `enqueue_job`. **One `enqueue_job` = one reservation**, regardless of attempts.

---

## 2. Decisions

1. **Accounting depth = release-only, made SPEND-AWARE.** Release a reservation only when the work ended **without a successful billable call and without a kept artifact**. Do **not** write `actual_cents`; do **not** read Gemini `usageMetadata`. This is a stricter interpretation of the invariant forced by round-1 review (a bare "release on any failure" refunds real money when Gemini succeeded but the *save* step failed — see §12/F1). Fail-safe: over-counts real spend, never under-counts.
2. **Scope = generation + serve.** Both reserve sites feed the same global fuse; both get a release path.
3. **Serve crash residual = accepted.** Handle the common in-request serve failure. A hard process crash after reserve but before release leaks `magazine_est_cents` (6¢) until midnight — bounded (≤ `per_owner_serve_daily_cents`=60¢/owner/day), self-heals. No serve-lease-expiry sweep here.

**Deferred (documented, not built here):**
- **Real-cost settle (`actual_cents` from `usageMetadata`).** *This is the transitional escape hatch:* once settle exists, the §2.1 spend-aware boolean and the §5 keep/release heuristic become redundant — you measure real spend instead of guessing. Everything tagged "transitional" below is resolved by settle.
- Serve-lease-expiry sweep; backfill of already-leaked reservations (fresh deploy starts clean).

---

## 3. The Money Invariant

For each UTC day `d`:

> `spend_ledger.reserved_cents[d]` = Σ estimates of reservations made on day `d` that are **still in-flight, OR converted to a kept artifact, OR terminated after a billable call may have spent money**.

A reservation is **released** (credited back) **iff** it reaches a terminal state where **(a)** no artifact was kept **AND (b)** no billable call is known to have succeeded. Because `actual_cents` stays 0, the cap predicate `reserved_cents + actual_cents + est ≤ daily_cap_cents` keeps bounding real spend — conservatively, never below true spend.

**Release / keep decision, by situation:**

| Situation | Spent money? | Artifact kept? | Action |
|---|---|---|---|
| Handler succeeded (`complete_job`) | maybe | **yes** | **KEEP** |
| Failure **before** a billable call succeeded (bad input, no transcript, at-capacity, Gemini transport error/timeout) | no | no | **RELEASE** |
| Failure **after** a billable call returned (persist/promote threw) | **yes** | no | **KEEP** *(transitional — settle would release est and record real actual)* |
| Cancel of a `queued` job (never ran) | no | no | **RELEASE** |
| Cancel of an `active` (running) job | maybe | maybe | **KEEP** (the worker's own terminal write decides; the running job may have spent) |
| Worker crash → reaper reclaims | maybe | maybe | **KEEP** (conservative; a running worker may have spent) |
| Serve materialization threw (in-request) | Gemini failed → no | no | **RELEASE** |
| Serve materialized successfully | yes | yes (cached) | **KEEP** |

The one signal that distinguishes rows 2 vs 3 is **"did a billable call succeed?"** — a single boolean the worker already knows (it caught the error and knows whether it was past `generateSummary`). No token counts, no cost math.

---

## 4. Cross-Cutting Correctness Rules

1. **Atomic + exactly-once.** Each release executes **inside the same RPC** that performs the terminal state flip, in one transaction, under the guard that already guarantees a single terminal write (`where … and status='active'` for `complete_job`/`fail_job`; the genuine-transition guard for cancels; the token match for serve). No new lock/race surface.
2. **Guarded decrement, never silent clamp.** Every credit-back is a **conditional** decrement:
   ```sql
   update spend_ledger set reserved_cents = reserved_cents - :amt, updated_at = now()
    where day = :reserve_day and reserved_cents >= :amt;
   if not found then
     -- invariant violation: the reservation we expected to release isn't there.
     insert into ledger_audit(day, kind, expected_amt, note, at)
       values (:reserve_day, 'release_underflow', :amt, :context, now());
     -- do NOT silently zero; the audit row surfaces the mis-accounting.
   end if;
   ```
   A new `ledger_audit` table records any release that would have driven a counter negative (previously masked by `greatest(0,…)`). Availability is preserved (the terminal transition still commits); the corruption is made visible, not swallowed.
3. **Idempotent by construction.** Generation release is one-shot because it fires only under the `status='active'`→terminal single-writer guard (a second terminal write finds no `active` row and never reaches the release). Zeroing `jobs.reserved_cents` in the same statement is belt-and-suspenders, **not** the primary guard. Serve release is one-shot via a single-use **token** (§6).
4. **Day-correct.** A release always credits the ledger row for the reservation's **UTC day**, read from the row itself: generation uses `(jobs.created_at at time zone 'utc')::date` (Postgres `now()` is transaction-stable, so `created_at::date` == the reserve-day; re-queue never rewrites `created_at`); serve uses the `day` stored on the `serve_model_charge` row (§6), never `now()`.

---

## 5. Generation Path (jobs)

Fold a spend-aware release into the terminal RPCs. New migration `create or replace`s each verbatim except the added release, preserving signatures/grants/ownership.

**New `fail_job` parameter:** `p_billable_succeeded boolean` (default `false` = safe/releasable-unless-told-otherwise is WRONG; default must be **`true` = conservative KEEP** so an un-updated caller never wrongly refunds). The worker-runner passes `false` only when it caught an error it can prove happened *before* a billable call succeeded.

| Transition | Function | Action |
|---|---|---|
| `completed` (or `cancelled` via cancel-after-success) | `complete_job` (`0008:128-141`) | **KEEP** — never releases |
| `failed`/`dead_letter`/`cancelled` **and** `p_billable_succeeded=false` | `fail_job` | **RELEASE** |
| `failed`/`dead_letter`/`cancelled` **and** `p_billable_succeeded=true` | `fail_job` | **KEEP** *(transitional)* |
| re-`queued` (retryable) | `fail_job` | KEEP (reservation reused) |
| any terminal via reaper | `sweep_expired_leases` (`0009:63-77`) | **KEEP** — reaper never releases (running worker may have spent) |
| `queued → cancelled` | `request_cancel_job` (`0010:7`) | **RELEASE** (never ran) |
| `active` cancel (sets `cancel_requested`, status unchanged) | `request_cancel_job` | **KEEP** (worker's terminal write decides) |
| playlist delete: `queued → cancelled` jobs | `request_cancel_playlist_jobs` (`0019:45`) | **RELEASE** before rows are deleted |
| playlist delete: `active` jobs | `request_cancel_playlist_jobs` | **KEEP** (may have spent; reservation self-heals at midnight) |

**Worker-runner change (`lib/job-queue/worker-runner.ts:53-66`):** classify the caught error. Pass `p_billable_succeeded=false` when the failure is provably pre-billing:
- payload/validation errors, duration-cap rejection, idempotency skip, `PermanentTranscriptError` raised *before* any Gemini call, at-capacity, and a Gemini call that threw (transport/5xx/timeout → no successful response → no charge).
Pass `p_billable_succeeded=true` (KEEP) for any error after `generateSummary`/`generateMagazineModel` returned. The handler surfaces this via a typed marker on the error (e.g. an `billableSucceeded` flag) so the runner doesn't guess.

**`request_cancel_job` gating (fixes B2).** The function matches `status in ('queued','active')` and returns rowcount=1 for *both* a real `queued→cancelled` flip and an `active` flag-set. Release must key on the **genuine transition**, not rowcount:
```sql
with flipped as (
  update jobs
     set cancel_requested = true,
         status = case when status='queued' then 'cancelled' else status end,
         reserved_cents = case when status='queued' then 0 else reserved_cents end,
         updated_at = now()
   where id = p_job_id and owner_id = auth.uid() and status in ('queued','active')
  returning (status = 'cancelled') as did_cancel,
            (created_at at time zone 'utc')::date as reserve_day,
            (case when status='queued' then <OLD reserved_cents> else 0 end) as amt)
release from spend_ledger for rows where did_cancel …   -- guarded decrement (§4.2)
```
(Capture the OLD `reserved_cents` before zeroing — via a `for update` read or an OLD-value CTE.) Only `did_cancel` rows release.

**`request_cancel_playlist_jobs` (fixes Codex-B4).** Same pattern, set-based: flip `queued→cancelled` for the playlist's jobs, release each cancelled job's reservation (guarded decrement, grouped by reserve-day) **inside this RPC, before the route's cascade delete removes the rows**. `active` jobs keep (may have spent). Route order (`app/api/playlists/[id]/route.ts:65,73`) already cancels before delete — the release must live in the cancel RPC so it runs while the rows still exist.

**Reaper (fixes H1/Codex-6 by removing the need for a multi-row release).** `sweep_expired_leases` **never releases** — a lease-expired job was `active` (running), so it may have spent. Its reservation is KEPT (over-count, safe) and self-heals at midnight. This is both correct (spend-aware) and simpler than a multi-row/multi-day release CTE.

---

## 6. Serve Path (magazine materialization)

Round-1 review found the naive serve release (a) client-callable to un-charge a *kept* serve, (b) cumulative-marker double-refundable, (c) `now()`-day wrong under a midnight straddle. Fix with a **per-attempt token + stored day + clear-on-settle** model.

**Schema changes on `serve_model_charge` (`0012:7-15`):**
```sql
alter table serve_model_charge add column reserved_cents int not null default 0 check (reserved_cents >= 0);
alter table serve_model_charge add column release_token uuid;  -- the current in-flight reservation's one-time secret
```
`reserved_cents` here means **only the current in-flight attempt's releasable amount** (0 or `magazine_est_cents`), never a cumulative sum.

**`reserve_serve_model` (the `'reserved'` branch, after 5b succeeds, before `return`, inside the same `begin…exception` block):**
```sql
v_token := gen_random_uuid();
update serve_model_charge
   set reserved_cents = v_cfg.magazine_est_cents,   -- SET, not +=  (single in-flight attempt)
       release_token  = v_token
 where owner_id = v_owner and doc_key = v_doc_key and day = v_day;
-- return the token to the (server-side) caller alongside status 'reserved'
```
Lease single-flight already guarantees at most one un-settled attempt per `(owner,doc,day)` at a time, so `reserved_cents` as "current attempt" is correct.

**New `settle_serve_model(p_token uuid, p_released boolean)`** (SECURITY DEFINER, owner from `auth.uid()`, definer/search_path restated verbatim; grants: `authenticated, anon`):
- Match the row by `owner_id = auth.uid()` **and** `release_token = p_token` **and** `reserved_cents >= magazine_est_cents`. No match → no-op (idempotent; a stale/duplicate/forged token does nothing).
- On match: clear `reserved_cents = 0, release_token = null` (one-shot). If `p_released` → also guarded-decrement `serve_owner_budget.spent_cents` (WHERE `owner_id = v_owner and day = row.day`) and `spend_ledger.reserved_cents` (WHERE `day = row.day`) by `magazine_est_cents` (§4.2). If not `p_released` (success) → just clear the marker/token (keep the charge).
- **`attempt_count` is untouched** (the K-attempt/day abuse bound survives every release; a failed serve still burns an attempt → no infinite retry).

**Why this closes all three serve findings:**
- **Un-charge-a-kept-serve (Claude-B1):** on success the server calls `settle_serve_model(token, released=false)`, which clears the marker/token. A later `settle_serve_model(token, released=true)` finds `reserved_cents=0`/token cleared → **no-op**. A direct PostgREST caller never holds the server-only token, and even with it, a settled reservation has nothing to release.
- **Double-refund (Codex-2):** marker is per-attempt (SET, cleared on settle), never cumulative; the token is single-use.
- **Wrong-day (Codex-3):** the row is keyed `(owner,doc,day)`; release targets that row's stored `day`, never `now()`.

**Caller change (`lib/html-doc/serve-doc.ts`):** on the `'reserved'` branch, capture the returned token. `try` the materialize (`generateMagazineModel`, `serve-doc.ts:81`) + write. On success → `settle_serve_model(token, released:=false)` (keep). On throw → `settle_serve_model(token, released:=true)` (refund), then re-throw. Every WHERE keeps `owner_id = auth.uid()` (no cross-tenant release; L3).

---

## 7. Enumerated Behaviors (test contract)

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | Success keeps | handler returns; `complete_job` → `completed` | ledger + `jobs.reserved_cents` unchanged |
| 2 | Pre-billing fail releases | fail before Gemini (bad payload / no transcript / capacity); `fail_job(billable=false)` → `failed`/`dead_letter` | ledger `-= est` on reserve-day; `jobs.reserved_cents → 0` |
| 3 | Gemini-threw releases | `generateSummary` throws (transport/timeout); `fail_job(billable=false)` | released |
| 4 | Post-billing fail KEEPS | `generateSummary` returned, then persist/promote throws; `fail_job(billable=true)` → `dead_letter` | **no** release *(transitional)* |
| 5 | Cancel-mid-run keeps or releases correctly | `cancel_requested` + handler throws pre-billing | released only if `billable=false` |
| 6 | Retry reuses one reservation | retryable fail, `attempts<max`; `fail_job` → `queued` | **no** release; next attempt does not re-reserve |
| 7 | Reaper never releases | lease expires (any attempts); `sweep` → `queued`/`dead_letter`/`cancelled` | **no** release (KEEP) |
| 8 | Cancel queued releases | `request_cancel_job`, genuine `queued→cancelled` | released; `jobs.reserved_cents → 0` |
| 9 | Cancel ACTIVE keeps | `request_cancel_job` on an `active` job (flag-set, status stays `active`) | **no** release |
| 10 | Cancel active, then success keeps | active cancel, handler already succeeded; `complete_job` → `cancelled` | **no** release (artifact exists) |
| 11 | Double-cancel no double-release | cancel an active job twice | at most one release, and only if it ever genuinely flips `queued→cancelled` |
| 12 | Playlist delete: queued released | `request_cancel_playlist_jobs` flips queued→cancelled before cascade delete | each cancelled job released; then rows deleted |
| 13 | Playlist delete: active kept | active jobs on the deleted playlist | reservation kept (self-heals midnight); documented |
| 14 | Midnight-span day-correct | job `created_at` day X, terminal day Y | release credits day **X** |
| 15 | Guarded decrement audits | release when ledger row missing / below amount | no negative; `ledger_audit` row written; terminal still commits |
| 16 | Cap re-opens after release | reserve to cap, a pre-billing failure releases | subsequent `enqueue_job`/`enqueue_preflight` admits again |
| 17 | Serve fail releases both | `generateMagazineModel` throws → `settle_serve_model(token, released=true)` | `spend_ledger` and `serve_owner_budget` each `-= 6`; marker/token cleared; `attempt_count` unchanged |
| 18 | Serve success keeps | materialize+write succeed → `settle_serve_model(token, released=false)` | no ledger change; marker/token cleared |
| 19 | Serve un-charge blocked | after a KEPT serve, call `settle_serve_model(token, released=true)` | no-op (marker/token already cleared) |
| 20 | Serve double-refund blocked | call release settle twice for one failed attempt | second is a no-op |
| 21 | Serve wrong-day blocked | reserve day X (23:59), reserve same doc day Y (00:00), release X | credits day X's row only |
| 22 | Serve K-bound survives releases | K failed serves, each released | `attempt_count` reaches `max_serve_attempts` → `'attempts_exhausted'` |
| 23 | Retry-keep path reachable | force `max_attempts > 1` in the fixture | behaviors 6/7's KEEP-on-requeue actually fire (not vacuous) |

---

## 8. Edge Cases

- **Guarded decrement** (§4.2) replaces `greatest(0,…)`; a would-be-negative release writes a `ledger_audit` row instead of silently zeroing.
- **Missing ledger/budget row on release:** guarded decrement no-ops + audits; cannot happen on the normal path (reserve created the row).
- **Concurrency:** release lives inside the terminal RPC's single-writer guard; reaper never releases (so it can't race a worker's release); serve release is token-gated and single-use.
- **`p_billable_succeeded` default = `true` (KEEP):** an un-migrated / older caller never wrongly refunds — the unsafe direction (refund real spend) requires an explicit `false`.

---

## 9. Testing Strategy

Against **real PostgREST + Postgres** (not mocks — the BUG-1 lesson: a mocked money test missed a real PostgREST param-drop). Integration tests assert exact ledger/budget/job-column deltas for behaviors 1–22, plus behavior 23 (force `max_attempts > 1`). Include: a concurrency test (two claimants race a terminal write → exactly one release); the midnight-span test (back-dated `created_at`); the serve un-charge/double-refund/wrong-day trio (17–21); the guarded-decrement audit path (15). A unit-level test asserts the worker-runner's error→`p_billable_succeeded` classification for each error class.

---

## 10. Out of Scope / Deferred

- **Real-cost settle (`actual_cents`).** *Transitional resolver:* once built, it supersedes the §5 `p_billable_succeeded` heuristic and the §3 keep-on-post-billing-failure row — real cents replace the guess. Its own slice, when the cap constrains real traffic.
- **Serve-lease-expiry sweep** (closes the accepted serve crash residual).
- **Backfill** of already-leaked reservations (fresh deploy starts clean; local dev resets manually).

---

## 11. Review Requirements

Money path + concurrency + idempotency → **iterative dual adversarial review to convergence** (Codex + Claude, independent), re-reviewing the revised SQL each round until a round returns no new Blocking/High. Explicit targets: the `p_billable_succeeded` default/direction (§5, §8); exactly-once under concurrent workers vs the (now non-releasing) reaper (§4.1); cancel transition-gating for single and playlist cancel (§5); serve token one-shot + clear-on-success + stored-day (§6); the guarded-decrement audit path never masking a real logic bug (§4.2).

---

## 12. v2 Change Log (round-1 review responses)

Round-1 dual review (`docs/reviews/reservation-release-spec-v1-{claude,codex}.md`) returned NOT CONVERGED. Resolutions:

- **F1 — release refunds real spend (Codex B1 / Claude H2) [Blocking].** A generation can spend money (Gemini succeeded) then fail at persist → old spec released it → under-count. **Fix:** spend-aware release (§2.1, §3, §5 `p_billable_succeeded`). *Transitional — settle removes the heuristic.*
- **F2 — serve release exploitable / double-refundable / wrong-day (Claude B1, Codex 2 & 3) [Blocking].** **Fix:** per-attempt token + stored day + clear-on-settle (§6).
- **F3 — cancel-active mis/double-release (Claude B2) [Blocking].** **Fix:** release only on genuine `queued→cancelled` (§5).
- **F4 — playlist-delete leaks reservations (Codex B4) [Blocking].** **Fix:** release queued reservations inside `request_cancel_playlist_jobs` before cascade delete (§5).
- **F5 — reaper multi-row release underspecified (Claude H1 / Codex 6) [High].** **Fix:** reaper never releases (§5) — spend-aware makes this both correct and simpler; the multi-row CTE is no longer needed.
- **F6 — `greatest(0,…)` masks corruption (Codex 5 / Claude M1) [High].** **Fix:** guarded decrement + `ledger_audit` (§4.2).
- **F7 — behavior-table gaps, marker atomicity, `max_attempts>1` (Codex 7, Claude M2/L2) [Medium/Low].** **Fix:** §7 expanded to 23 rows; §6 pins marker placement; behavior 23 forces `max_attempts>1`.
- **L1/L3** — §4.3 names the status/transition guard as primary (zeroing is secondary); §6 keeps `owner_id` on every serve decrement.

**Scope note:** v2 is larger than the initial "minimal release-only" sketch — the review showed the minimal version was unsafe. The growth (spend signal, serve token model, playlist-delete path, audit table) is correctness required by the money-path class, not gold-plating.
