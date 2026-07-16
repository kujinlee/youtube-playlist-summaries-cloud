# Reservation Release Lifecycle — Design Spec (v3)

**Date:** 2026-07-15 (v3: 2026-07-16)
**Status:** Draft v3 (revised after round-2 dual adversarial review — see §13). Pending re-review (round 3) + user approval.
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
3. **Serve crash residual = accepted (bounded, 6¢, per-owner).** Handle the common in-request serve failure. A hard process crash after reserve but before release — OR a slow generation that outlives the un-heartbeated 180s serve lease and gets reclaimed (§6, H5) — leaks `magazine_est_cents` (6¢) until midnight. Bounded (≤ `per_owner_serve_daily_cents`=60¢/owner/day), self-heals. No serve-lease-expiry sweep here.
4. **Generation crash residual = accepted (documented; NOT bounded — 150¢, global).** A worker that dies mid-run **after `enqueue_job` reserved 150¢ but before any billable call** (SIGKILL during deploy, OOM during transcript fetch, container recycle) leaves an `active` job; the reaper terminalizes it and — per §5 — **never releases** (a running worker *may* have billed; releasing risks the §3 under-count). That 150¢ stays reserved on the **global** `spend_ledger` until UTC midnight. **This is the one self-DoS shape §1 does NOT fully close**: ~3 such crashes (e.g. a deploy crash-loop) lock the whole system's budget. **Decision (user-confirmed 2026-07-16): ACCEPT this residual for this slice.** Rationale: the release-only fix closes the *dominant* self-DoS surface — handler-level failures (Gemini outage, retry burst, bad input, at-capacity), which is what actually triggers the DoS at scale; a crash in the narrow reserve→first-billable window is rarer and operationally mitigable. **Operational mitigation (required at deploy):** graceful worker drain before rollout (let in-flight jobs finish / stop claiming new ones before SIGTERM) so a routine deploy does not strand reservations. The real fix — a persisted "billable-phase-entered" marker so the reaper can release active jobs that provably never billed — is folded into the deferred **settle** slice (below).

**Deferred (documented, not built here):**
- **Real-cost settle (`actual_cents` from `usageMetadata`).** *This is the transitional escape hatch:* once settle exists, the §2.1 spend-aware boolean and the §5 keep/release heuristic become redundant — you measure real spend instead of guessing. Everything tagged "transitional" below is resolved by settle. **The settle slice also closes the §2.4 generation crash residual** (a "billable-phase-entered" job marker lets the reaper release never-billed crashed jobs).
- Serve-lease-expiry sweep; generation lease-expiry settle; backfill of already-leaked reservations (fresh deploy starts clean).

---

## 3. The Money Invariant

For each UTC day `d`:

> `spend_ledger.reserved_cents[d]` = Σ estimates of reservations made on day `d` that are **still in-flight, OR converted to a kept artifact, OR terminated after a billable call may have spent money**.

A reservation is **released** (credited back) **iff** it reaches a terminal state where **(a)** no artifact was kept **AND (b)** no billable call is known to have succeeded. Because `actual_cents` stays 0, the cap predicate `reserved_cents + actual_cents + est ≤ daily_cap_cents` keeps bounding real spend — conservatively, never below true spend.

**Release / keep decision, by situation:**

| Situation | Spent money? | Artifact kept? | Action |
|---|---|---|---|
| Handler succeeded (`complete_job`) | maybe | **yes** | **KEEP** |
| Failure **before any billable Gemini call was sent** (bad input, pre-call `PermanentTranscriptError` / no transcript, at-capacity, duration-cap, idempotency skip, DNS/connect failure *pre-send*) | no | no | **RELEASE** |
| Failure where **any billable Gemini call may have metered** — it returned then persist/promote threw, **OR** it threw transport/5xx/timeout (server may have metered before the client saw the error), **OR** the **transcription fallback** (`transcribeViaGemini`, itself billable) succeeded before a later step threw | **yes / unknown** | no | **KEEP** *(transitional — settle would release est and record real actual)* |
| Cancel of a `queued` job (never ran) | no | no | **RELEASE** |
| Cancel of an `active` (running) job | maybe | maybe | **KEEP** (the worker's own terminal write decides; the running job may have spent) |
| Worker crash → reaper reclaims | maybe | maybe | **KEEP** (conservative; a running worker may have spent — §2.4 residual) |
| Serve materialization threw (in-request) — `generateMagazineModel` **threw before returning** | Gemini didn't complete → no | no | **RELEASE** |
| Serve materialized successfully | yes | yes (cached) | **KEEP** |

The one signal that distinguishes rows 2 vs 3 is **"could any billable Gemini call have metered?"** — a single boolean the worker already knows. **The safe direction is KEEP:** classify RELEASE (`false`) *only* when the failure provably occurred **before any bytes were sent to any billable Gemini call** (transcription fallback included). A throw *from inside* a Gemini call is **ambiguous** — Google meters on server-side completion, so a client-side timeout/504 can fire *after* metering — and therefore KEEPs. (See §5 for the worker-runner classification and the handler→runner marker; and note the serve row's RELEASE is on a *pre-return* throw of the single serve call, whereas generation may chain transcription→summary, so generation's KEEP net is wider.) No token counts, no cost math.

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
   A new `ledger_audit` table records any release that would have driven a counter negative (previously masked by `greatest(0,…)`). The corruption is made visible, not swallowed.

   **`ledger_audit` full DDL + posture (fixes H4 — round-2).** It is a money-path table and must be locked down like `spend_ledger` (`0011:17-18`) — never PostgREST-exposed to session clients:
   ```sql
   create table ledger_audit (
     id            bigint generated always as identity primary key,
     day           date        not null,
     kind          text        not null,   -- e.g. 'release_underflow'
     expected_amt  int         not null,
     note          text,
     at            timestamptz not null default now()
   );
   alter table ledger_audit enable row level security;
   alter table ledger_audit force  row level security;   -- no policies → no anon/authenticated access at all
   grant select, insert on ledger_audit to service_role;  -- the ONLY grant; mirrors spend_ledger
   -- NO grant to anon/authenticated; NO RLS policy → /rest/v1/ledger_audit returns nothing to session clients.
   ```
   This mirrors the exact locked-down pattern of every existing money table (`spend_ledger` `0011:17-18`, `serve_model_charge` `0012:16-17`, `share_tokens` `0013:17-18`): `force row level security` with **no policy** blocks `anon`/`authenticated` entirely (they have neither `BYPASSRLS` nor a grant), while the trusted paths still write. Per `0006_grants.sql:9-10`, **`service_role` has `BYPASSRLS`** — so RLS never blocks it — *but* BYPASSRLS does **not** bypass table-level GRANTs, which is why the explicit `grant … to service_role` above is required (not optional).

   **Availability is preserved, and the "still commits" claim is now made true, not assumed (fixes H4 / L2):** the audit `insert` runs in the terminal RPC's transaction, so it must never be able to raise. It cannot: (a) the definer RPCs (`request_cancel_job`, `request_cancel_playlist_jobs`, `settle_serve_model`; owner = `postgres`, which owns `ledger_audit` → implicit full privilege, and BYPASSRLS) always insert regardless of RLS; (b) `fail_job` runs as its caller — the worker's **`service_role`**, which has BYPASSRLS *and* is granted `insert` above; (c) the table has no `NOT NULL` column the release path leaves unset (all of `day`/`kind`/`expected_amt` are provided, `note` is nullable, `id`/`at` default), no `UNIQUE`/`FK` constraint, and no `CHECK` that a release could violate. So an audit write cannot abort the terminal state flip. (The audit row *is* transaction-scoped — if the terminal transition itself later rolls back for an unrelated reason, the audit row rolls back with it. That is correct: an audit of a release that never committed would be misleading. `ledger_audit` is an in-band invariant-violation signal, not an out-of-band durable log.)
3. **Idempotent by construction.** Generation release is one-shot because it fires only under the `status='active'`→terminal single-writer guard (a second terminal write finds no `active` row and never reaches the release). Zeroing `jobs.reserved_cents` in the same statement is belt-and-suspenders, **not** the primary guard. Serve release is one-shot via a single-use **token** (§6).
4. **Day-correct.** A release always credits the ledger row for the reservation's **UTC day**, read from the row itself: generation uses `(jobs.created_at at time zone 'utc')::date` (Postgres `now()` is transaction-stable, so `created_at::date` == the reserve-day; re-queue never rewrites `created_at`); serve uses the `day` stored on the `serve_model_charge` row (§6), never `now()`.

---

## 5. Generation Path (jobs)

Fold a spend-aware release into the terminal RPCs. New migration `create or replace`s each verbatim except the added release, preserving signatures/grants/ownership — **except `fail_job`, which gains a parameter and therefore needs a DROP+recreate (see below).**

**New `fail_job` parameter — signature change, not a `create or replace` (mechanics, round-3 self-review):** the current signature is `fail_job(p_job_id uuid, p_worker_id text, p_lease_token uuid, p_error text, p_retryable boolean)` (`0008:143`) — it already has a boolean (`p_retryable`). Adding `p_billable_succeeded boolean` makes a **6-arg** function, a *different* signature. A bare `create or replace` would leave the 5-arg version in place as a second overload; with the new param defaulted, the adapter's existing 5-named-arg call (`supabase-job-queue.ts:88`) then resolves **ambiguously** between the two overloads — the exact PostgREST resolution footgun behind BUG-1. Required steps:
- `drop function fail_job(uuid,text,uuid,text,boolean);` then create `fail_job(p_job_id uuid, p_worker_id text, p_lease_token uuid, p_error text, p_retryable boolean, p_billable_succeeded boolean default true)` — body = the existing function verbatim **plus** the spend-aware release.
- Re-issue `revoke all … from public; grant execute … to service_role;` for the **new** 6-arg signature.
- Update the adapter `SupabaseJobQueue.fail` (`supabase-job-queue.ts:85-90`) to pass `p_billable_succeeded` (threaded from the worker-runner's classification, §5 below). Because only one `fail_job` overload will exist after the drop, the named-arg call is unambiguous.

**Default direction:** `p_billable_succeeded` defaults to **`true` = conservative KEEP** (`false` = "releasable-unless-told-otherwise" is WRONG) so an un-updated caller — or any unclassified error (M2) — never wrongly refunds. The worker-runner passes `false` only when it caught an error it can prove happened *before* any billable Gemini call was sent.

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

**Worker-runner + handler classification (fixes B1 + M2 — round-2). The safe default is KEEP; RELEASE only on a *proven* pre-send failure.**

Pass `p_billable_succeeded=false` (RELEASE) **only** when the failure provably occurred **before any bytes were sent to any billable Gemini call** — transcription fallback included:
- payload/validation errors, duration-cap rejection, idempotency skip, `PermanentTranscriptError` raised *before* any Gemini call, at-capacity, DNS/connection-refused *before send*.

Pass `p_billable_succeeded=true` (KEEP) for **every throw originating from a billable Gemini call itself** — `transcribeViaGemini` (`lib/gemini.ts`, the caption-less transcription fallback, **itself billable**), `generateSummary`, `generateDig`, `generateMagazineModel` — **including transport/5xx/timeout**, and for any error after such a call returned. Rationale (B1): Google meters on server-side completion, so a client-side socket timeout / SDK deadline / intermediary 504 can fire *after* the model metered a full response — billing-identical to the "Gemini returned, save failed" case, which KEEPs. The old v2 rule ("Gemini threw → no charge → RELEASE") under-counted real spend and is removed. The old rule also keyed only on `generateSummary`/`generateMagazineModel`, missing the earlier billable **transcription** step entirely.

**Marker plumbing (M2) — specified end-to-end, not assumed.** Today `worker-runner.ts:53-66` catches a bare `e` and computes only `retryable`; there is no billable signal. Add a typed marker:
- Each handler (`summary-handler.ts`, `dig-handler.ts`) attaches `billableSucceeded: false` to **every throw it raises on a proven pre-Gemini-send path** (the RELEASE list above). Any error that escapes from *inside* a billable Gemini call carries **no** `false` marker (the handler does not catch-and-reclassify Gemini throws).
- The runner reads it: `const pre = (e as { billableSucceeded?: boolean }).billableSucceeded === false;` and calls `failJob(..., { p_billable_succeeded: !pre })`.
- **Absent / unknown marker ⇒ `p_billable_succeeded=true` (KEEP).** So an unclassified or new error type KEEPs — a bounded 150¢ leak in the *safe* direction, never a wrong RELEASE. This makes the SQL default (`true`, below) and the runner default agree.

**`request_cancel_job` gating (fixes B2; SQL corrected for H1 — round-2).** The function matches `status in ('queued','active')` and returns rowcount=1 for *both* a real `queued→cancelled` flip and an `active` flag-set. Release must key on the **genuine transition**, and must read the reservation amount **before** the update zeroes it. Postgres < 18 (Supabase is PG15/17) `UPDATE … RETURNING` returns the **post-update** row, so `RETURNING reserved_cents` after `set reserved_cents = 0` yields `0` — the v2 `<OLD reserved_cents>` placeholder was non-functional and would have released `0` (leak). Use an explicit **pre-read CTE** (which also `for update`-serializes against a concurrent `claim_next_job`):
```sql
with pre as (                                  -- snapshot OLD values under a row lock
  select id,
         status         as old_status,
         reserved_cents as old_amt,
         (created_at at time zone 'utc')::date as reserve_day
    from jobs
   where id = p_job_id and owner_id = auth.uid() and status in ('queued','active')
   for update),
upd as (                                       -- flip; only a queued row becomes cancelled + zeroed
  update jobs j
     set cancel_requested = true,
         status         = case when pre.old_status = 'queued' then 'cancelled' else j.status end,
         reserved_cents = case when pre.old_status = 'queued' then 0 else j.reserved_cents end,
         updated_at     = now()
    from pre
   where j.id = pre.id
   returning pre.old_status)
update spend_ledger sl                          -- release ONLY genuine queued→cancelled rows, OLD amount, OLD day
   set reserved_cents = sl.reserved_cents - pre.old_amt, updated_at = now()
  from pre
 where pre.old_status = 'queued'
   and sl.day = pre.reserve_day
   and sl.reserved_cents >= pre.old_amt;         -- guarded decrement; underflow → ledger_audit (§4.2)
```
`did_cancel := (pre.old_status = 'queued')` drives the function's return. An `active` flag-set (`old_status='active'`) sets only `cancel_requested` and never releases. A repeat cancel of an already-`cancelled`/terminal job matches no `pre` row → no-op (idempotent). The guarded-decrement underflow branch (§4.2) writes `ledger_audit` if the ledger row is missing/below amount.

**`request_cancel_playlist_jobs` (fixes Codex-B4; SQL written for H2 — round-2).** Same defect class as H1 (post-update `RETURNING`), **plus** it is inherently multi-row and multi-day: a playlist can hold many queued jobs enqueued across a UTC-midnight boundary, each with its own `reserved_cents` and `created_at` day. A single `where day = X` decrement would leak the other day's jobs. Snapshot pre-update amounts, aggregate by reserve-day, decrement each `spend_ledger` day row by its group sum — **inside this RPC, before the route's cascade delete removes the rows**:
```sql
with pre as (                                    -- all queued jobs of the playlist, OLD amounts, under lock
  select id, reserved_cents as old_amt, (created_at at time zone 'utc')::date as reserve_day
    from jobs
   where playlist_id = p_playlist_id and owner_id = auth.uid() and status = 'queued'
   for update),
upd as (
  update jobs j
     set cancel_requested = true, status = 'cancelled', reserved_cents = 0, updated_at = now()
    from pre
   where j.id = pre.id),
per_day as (                                     -- multi-day: group OLD amounts by reserve-day
  select reserve_day, sum(old_amt) as amt from pre group by reserve_day)
update spend_ledger sl
   set reserved_cents = sl.reserved_cents - per_day.amt, updated_at = now()
  from per_day
 where sl.day = per_day.reserve_day
   and sl.reserved_cents >= per_day.amt;          -- guarded per-day decrement; underflow → ledger_audit (§4.2)
```
`active` jobs of the playlist keep their reservation (may have spent; §2.4 residual) — the existing function's active-handling is unchanged. Route order (`app/api/playlists/[id]/route.ts:65,73`) already cancels before delete — the release lives in this RPC so it runs while the rows still exist. (This is the multi-row/multi-day complexity round-1 F5 *relocated* from the reaper rather than eliminated — it is genuinely needed here and carries its own idempotency argument: a second call finds no `queued` `pre` rows → no-op.)

**Reaper (fixes round-1 H1/Codex-6 by removing the need for a multi-row release).** `sweep_expired_leases` **never releases** — a lease-expired job was `active` (running), so it may have spent. Its reservation is KEPT (over-count, safe) and self-heals at midnight. This is both correct (spend-aware) and simpler than a multi-row/multi-day release CTE. **Round-2 caveat (H3, now §2.4):** this KEEP leaves a **150¢ global, count-unbounded crash residual** for a worker that died *before* any billable call — an accepted, documented residual for this slice (see §2.4), mitigated operationally by graceful drain and closed properly by the deferred settle slice. It is *not* bounded like the 6¢ serve residual; do not conflate the two.

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
   set reserved_cents = v_cfg.magazine_est_cents,   -- SET, not +=  (single LIVE attempt)
       release_token  = v_token
 where owner_id = v_owner and doc_key = v_doc_key and day = v_day;
-- return the token to the (server-side) caller alongside status 'reserved'
```

**Single-flight scope — corrected for H5 (round-2).** Lease single-flight guarantees at most one un-settled attempt per `(owner,doc,day)` **only while the lease is live.** The serve lease TTL is `lease_ttl_seconds` (default **180s**, `0012:22`), set once at reserve and **not heartbeated** across `generateMagazineModel` (`serve-doc.ts:81-92`, unlike the worker loop). So a generation that outlives 180s can be **reclaimed** by a second view (`reserve_serve_model` on-conflict `where lease_expires_at < now() and attempt_count < K`, `0014:54-58`): the reclaim re-reserves (`serve_owner_budget += 6`, `spend_ledger += 6`) and **overwrites** `release_token` with the new attempt's token. The stranded first attempt's later `settle_serve_model(token_A,…)` then finds no match → no-op → its 6¢ is **not** released until midnight.

This residual is **bounded and safe** (folded into §2.3): releases ≤ reserves (never an under-count); each amount is the fixed 6¢; `spend_ledger` is day-global and fungible, so which attempt's 6¢ is released doesn't matter; and the per-owner burn is still capped at `per_owner_serve_daily_cents`=60¢/owner/day. `reserved_cents = SET` remains correct **for the single live attempt** — but do **not** rely on it to represent two concurrently-charged attempts; that is exactly the false invariant H5 flagged. (A future serve-lease heartbeat or the settle slice removes the overlap; out of scope here — §10.)

**New `settle_serve_model(p_token uuid, p_released boolean)`** (SECURITY DEFINER, owner from `auth.uid()`, definer/search_path restated verbatim; grants: `authenticated, anon`):
- Match the row by `owner_id = auth.uid()` **and** `release_token = p_token` **and** `reserved_cents >= magazine_est_cents`. No match → no-op (idempotent; a stale/duplicate/forged token does nothing).
- On match: clear `reserved_cents = 0, release_token = null` (one-shot). If `p_released` → also guarded-decrement `serve_owner_budget.spent_cents` (WHERE `owner_id = v_owner and day = row.day`) and `spend_ledger.reserved_cents` (WHERE `day = row.day`) by `magazine_est_cents` (§4.2). If not `p_released` (success) → just clear the marker/token (keep the charge).
- **`attempt_count` is untouched** (the K-attempt/day abuse bound survives every release; a failed serve still burns an attempt → no infinite retry).

**Why this closes all three serve findings:**
- **Un-charge-a-kept-serve (Claude-B1):** on success the server calls `settle_serve_model(token, released=false)`, which clears the marker/token. A later `settle_serve_model(token, released=true)` finds `reserved_cents=0`/token cleared → **no-op**. A direct PostgREST caller never holds the server-only token, and even with it, a settled reservation has nothing to release.
- **Double-refund (Codex-2):** marker is per-attempt (SET, cleared on settle), never cumulative; the token is single-use.
- **Wrong-day (Codex-3):** the row is keyed `(owner,doc,day)`; release targets that row's stored `day`, never `now()`.

**`reserve_serve_model` return-type change (mechanics — M1, round-2).** Returning the token changes the function's *return type*, even though its args are unchanged. Today it returns scalar `text` (`0014:22-24`), granted `authenticated, anon` (`0014:99`), destructured as a scalar in `serve-doc.ts:52-56`. Required migration steps (a return-type change cannot be done by `create or replace`):
- `drop function reserve_serve_model(<existing arg signature>);` then recreate `returns table(status text, release_token uuid)` (or a composite type), body identical except it now also returns `v_token` on the `'reserved'` branch (and `null` token on `'ok'`/`'denied'`/`'at_capacity'` paths).
- Re-issue grants `authenticated, anon` and restate `security definer` / `set search_path` verbatim.
- `reserve_serve_model_meta`'s `regprocedure` probe keys on the **argument** signature (unchanged) → still resolves; no change needed there.
- Update `serve-doc.ts:52-56` to destructure `{ status, release_token }` instead of a bare scalar.
The token is **server-held**: it is never placed in any client-visible `ResolveResult`, so a browser client cannot obtain it (this is what makes the §6 un-charge defense hold).

**Caller change (`lib/html-doc/serve-doc.ts`):** on the `'reserved'` branch, capture the returned token. `try` the materialize (`generateMagazineModel`, `serve-doc.ts:81`) + write. On success → `settle_serve_model(token, released:=false)` (keep). On throw → `settle_serve_model(token, released:=true)` (refund), then re-throw. Every WHERE keeps `owner_id = auth.uid()` (no cross-tenant release; L3).

---

## 7. Enumerated Behaviors (test contract)

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | Success keeps | handler returns; `complete_job` → `completed` | ledger + `jobs.reserved_cents` unchanged |
| 2 | Pre-send fail releases | fail **before any Gemini bytes sent** (bad payload / pre-call no-transcript / capacity / duration-cap / idempotency skip); handler marks `billableSucceeded=false`; `fail_job(billable=false)` → `failed`/`dead_letter` | ledger `-= est` on reserve-day; `jobs.reserved_cents → 0` |
| 3 | Gemini-threw KEEPS (B1) | `generateSummary`/`generateMagazineModel` throws transport/5xx/timeout (server **may have metered**); no `false` marker; `fail_job(billable=true)` | **no** release (KEEP) |
| 3b | Transcription-billable then fail KEEPS (B1) | captions absent → `transcribeViaGemini` succeeds (billable) → later step throws; no `false` marker; `fail_job(billable=true)` | **no** release (KEEP) |
| 3c | Unclassified error KEEPS (M2) | handler throws an error with **no** `billableSucceeded` marker; runner defaults `p_billable_succeeded=true` | **no** release (KEEP; bounded safe leak) |
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
| 24 | Serve lease-overlap = bounded leak, not double-refund (H5) | reserve token A; expire the 180s lease; second view reclaims (token B, `+6`); settle A | A's settle no-ops (token overwritten); B can still settle; net ≤ one release; ledger never goes negative; per-owner burn ≤ 60¢ |
| 25 | Generation crash residual KEPT + documented (H3/§2.4) | `active` job (150¢ reserved, no billable call yet); worker killed; reaper terminalizes | **no** release (KEEP); 150¢ stays reserved till midnight — asserts the accepted §2.4 residual, not a bug |

---

## 8. Edge Cases

- **Guarded decrement** (§4.2) replaces `greatest(0,…)`; a would-be-negative release writes a `ledger_audit` row instead of silently zeroing.
- **Missing ledger/budget row on release:** guarded decrement no-ops + audits; cannot happen on the normal path (reserve created the row).
- **Concurrency:** release lives inside the terminal RPC's single-writer guard; reaper never releases (so it can't race a worker's release); serve release is token-gated and single-use.
- **`p_billable_succeeded` default = `true` (KEEP):** an un-migrated / older caller — **and any unclassified error** (§5 M2) — never wrongly refunds; the unsafe direction (refund real spend) requires an explicit `false` on a proven pre-send failure.
- **Gemini-originated throw is ambiguous (B1):** a client-side timeout/504 can fire after server-side metering → treated as KEEP. Only pre-send failures RELEASE. This covers the billable **transcription fallback** too, not just `generateSummary`/`generateMagazineModel`.
- **Cancel OLD-value capture (H1/H2):** PG<18 `UPDATE … RETURNING` sees post-update values, so both cancel RPCs pre-read `reserved_cents` in a `for update` CTE *before* zeroing; playlist cancel aggregates by reserve-day for the multi-day case.
- **Serve lease overlap (H5):** a serve generation exceeding the un-heartbeated 180s lease can be reclaimed → a bounded 6¢ leak (releases ≤ reserves), folded into the §2.3 residual; never a double-refund or under-count.
- **Generation crash residual (H3/§2.4):** 150¢ global, count-unbounded, accepted for this slice; mitigated by graceful drain; closed by the deferred settle slice.

---

## 9. Testing Strategy

Against **real PostgREST + Postgres** (not mocks — the BUG-1 lesson: a mocked money test missed a real PostgREST param-drop). Integration tests assert exact ledger/budget/job-column deltas for behaviors 1–23, plus the round-2 additions: the serve lease-overlap bounded-leak (24, force lease expiry mid-generation) and the generation crash residual (25, kill an active pre-billing job → reaper KEEPs). Include: a concurrency test (two claimants race a terminal write → exactly one release); the midnight-span test (back-dated `created_at`) **for both single and playlist cancel** (H2 multi-day); the serve un-charge/double-refund/wrong-day trio (17–21); the guarded-decrement audit path (15, asserting a `ledger_audit` row *and* that the terminal transition still commits — H4). A unit-level test asserts the worker-runner's error→`p_billable_succeeded` classification for **each** error class, explicitly including: a Gemini transport/timeout throw → `true` (KEEP, B1), a transcription-fallback-succeeded-then-fail → `true` (B1), a proven pre-send error → `false`, and an unmarked/unknown error → `true` (M2 default).

---

## 10. Out of Scope / Deferred

- **Real-cost settle (`actual_cents`).** *Transitional resolver:* once built, it supersedes the §5 `p_billable_succeeded` heuristic and the §3 keep-on-post-billing-failure row — real cents replace the guess. Its own slice, when the cap constrains real traffic. **Also carries the "billable-phase-entered" job marker that lets the reaper release never-billed crashed jobs — closing the §2.4 generation crash residual.**
- **Serve-lease heartbeat / serve-lease-expiry sweep** (closes the accepted serve crash + lease-overlap residual, §2.3/H5).
- **Backfill** of already-leaked reservations (fresh deploy starts clean; local dev resets manually).
- **Operational (not code):** graceful worker drain before deploy — the required mitigation for the §2.4 residual until settle lands.

---

## 11. Review Requirements

Money path + concurrency + idempotency → **iterative dual adversarial review to convergence** (Codex + Claude, independent), re-reviewing the revised SQL each round until a round returns no new Blocking/High. Round-1 → v2, round-2 → v3 (both NOT CONVERGED; docs in `docs/reviews/reservation-release-spec-v{1,2}-*`). **Round-3 explicit targets** (verify the round-2 fixes are genuine + hunt defects they introduced): the corrected `p_billable_succeeded` taxonomy incl. transcription + timeout-after-metering (§3, §5, B1); the pre-read cancel CTEs actually reading OLD `reserved_cents` and the playlist multi-day aggregation (§5, H1/H2); `ledger_audit` RLS/grants + the "cannot abort the terminal write" claim (§4.2, H4); the serve lease-overlap residual being genuinely bounded/safe, not a double-refund (§6, H5); the `reserve_serve_model` return-type DROP+recreate not breaking the `regprocedure` probe or grants (§6, M1); the handler→runner marker plumbing defaulting to KEEP (§5, M2); and that the accepted §2.4 generation crash residual is correctly *documented*, not silently reintroduced elsewhere.

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

---

## 13. v3 Change Log (round-2 review responses)

Round-2 dual review (`docs/reviews/reservation-release-spec-v2-{codex,claude}.md`) returned **NOT CONVERGED** — both reviewers independently corroborated. The v2 fixes introduced new defects (the loop working as intended). Resolutions:

- **B1 — "Gemini threw → no charge → RELEASE" under-counts real spend (Codex C-B1 / Claude B1) [Blocking].** Two distinct holes in v2's F1: (a) it missed the billable **transcription fallback** (`transcribeViaGemini`) that runs before summary/dig; (b) it treated all Gemini transport/5xx/timeout throws as "no charge", but Google meters on server-side completion so a client-side timeout can fire *after* metering. **Fix:** RELEASE only on a **proven pre-send** failure; **every** throw from a billable Gemini call (transcription, summary, dig, magazine) — including transport/timeout — KEEPs (§3 table, §5 taxonomy). Removes the unsafe rows; the one signal becomes "could any billable Gemini call have metered?" with KEEP as the safe answer.
- **H1 — cancel CTE reads post-update `reserved_cents` → releases 0 → leak (Codex C-H2 / Claude H1) [High].** PG<18 `UPDATE … RETURNING` returns post-update rows; the v2 `<OLD reserved_cents>` placeholder was non-functional. **Fix:** explicit `for update` pre-read CTE captures OLD amount+day before zeroing; only genuine `queued→cancelled` rows release (§5).
- **H2 — playlist-cancel multi-row/multi-day release unwritten (Codex C-H2 / Claude H2) [High].** F5 *relocated* the multi-row complexity here rather than removing it. **Fix:** written set-based pre-read + `group by reserve-day` + per-day guarded decrement, inside the RPC before cascade delete (§5).
- **H3 — 150¢ global, count-unbounded reaper/crash residual = the headline self-DoS, undocumented (Codex C-H3 / Claude H3) [High, goal-affecting].** v2 documented only the 6¢ per-owner serve residual. **Decision (user, 2026-07-16): ACCEPT + document** the generation crash residual with operational mitigation (graceful drain); defer the real fix (billable-phase job marker) to the settle slice (§2.4, §5 reaper note, §10).
- **H4 — `ledger_audit` no RLS/grants → PostgREST-exposed; a missing grant would roll back the terminal write (Codex C-M1 [Med] / Claude H4 [High]) [High].** **Fix:** full DDL with `force row level security`, `grant … to service_role` only, no anon/authenticated; prove the insert cannot raise (definer BYPASSRLS + service_role grant + no violable constraint) so "still commits" is true, not assumed (§4.2). Rated High per Claude (availability regression + exposure).
- **H5 — serve "one un-settled attempt" invariant false past the un-heartbeated 180s lease (Codex C-H1 / Claude H5) [High].** A slow generation gets reclaimed → double-reserve + token overwrite → the first attempt's settle no-ops. **Fix:** correct the invariant to "while the lease is live"; document the overlap as a **bounded, safe** 6¢ residual (releases ≤ reserves) folded into §2.3; do not rely on `SET` to represent two charged attempts (§6).
- **M1 — serve token requires a return-type change, contradicting "preserving signatures" (Claude M1) [Medium].** **Fix:** specify `drop function` + recreate `returns table(status, release_token)` + re-grant + `serve-doc.ts` destructure; `regprocedure` probe unaffected (args unchanged) (§6).
- **M2 — handler→runner `billableSucceeded` marker assumed, not specified (Claude M2) [Medium].** **Fix:** specify the handler attaches `false` only on proven pre-send throws; runner reads it; **absent/unknown → KEEP** (§5). Aligns with the SQL default.
- **L1/L2** — §7 behavior 3 rewritten (Gemini-threw now KEEPS) + rows 3b/3c/24/25 added; §4.2 "still commits" now conditioned on (and guaranteed by) the audit grant.

**v3 self-review finds (grounded against the real migrations while drafting, pre-round-3):**
- **`fail_job` is a signature change, not a `create or replace`** — it already has 5 args incl. `p_retryable boolean`; adding `p_billable_succeeded` needs DROP+recreate + re-grant + adapter update, else a defaulted 6-arg overload sits alongside the 5-arg one and the adapter's named call resolves ambiguously (BUG-1 class). Specified in §5.
- **`ledger_audit` availability argument grounded in `0006_grants.sql`:** `service_role` has BYPASSRLS (so `force`-RLS-with-no-policy doesn't block it) but BYPASSRLS doesn't bypass table GRANTs (so the explicit grant is required) — §4.2 now cites this, matching the `spend_ledger`/`share_tokens` precedent.

**Verified-correct in round-2 (no new finding), carried forward:** serve un-charge / double-refund / wrong-day closure (round-1 F2 genuinely closed); generation exactly-once under concurrent claim-vs-cancel and reaper-vs-zombie; generation day-correctness; retry-never-re-reserves.

**Scope note (v3):** the round-2 growth is all *correctness of the existing surface* (real SQL for sketched CTEs, RLS on the audit table, a corrected error taxonomy, an honestly-documented residual) — no new feature. The one goal-touching item (H3) was a human decision, not a silent expansion.
