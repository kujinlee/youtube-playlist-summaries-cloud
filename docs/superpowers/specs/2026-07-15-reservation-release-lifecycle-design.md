# Reservation Release Lifecycle — Design Spec (v6)

**Date:** 2026-07-15 (v3–v6: 2026-07-16)
**Status:** Draft v6 (revised after round-5 dual adversarial review — see §16). Pending re-review (round 6) + user approval.
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
4. **Accepted residuals = narrow KEEP cases (documented).** With the §3.1 classification, the release-only fix closes the **dominant** §1 self-DoS: an overloaded/rate-limited Gemini returns a **429/503 HTTP-status storm** → each is class A → **RELEASES** → the budget re-opens, on all three generation paths (summary/magazine/dig — §7 behaviors 2b/2c/26). What remains KEPT-until-midnight is only:
   - **(4a) Ambiguous class-B failures (150¢, global, but rare).** A genuine client-side **timeout**, an HTTP **500/502** (can follow partial generation), or a **connection-only** failure the SDK stripped of its status/code (§3.1 CL4-H2) — Google *may* have metered. KEPT for money-safety (§3.1 class B). These are far rarer than a 429/503 outage (which fails fast with a detectable status, class A) and are not a self-DoS surface in practice.
   - **(4b) Worker crash before any terminal write (150¢, global, count-unbounded).** A worker that dies mid-run **after `enqueue_job` reserved 150¢ but before completing** (SIGKILL during deploy, OOM, container recycle) leaves an `active` job; the reaper terminalizes it and — per §5 — **never releases** (a running worker *may* have billed). ~3 such crashes (e.g. a deploy crash-loop) lock the budget until midnight. **Decision (user-confirmed 2026-07-16): ACCEPT** for this slice; a crash in the narrow reserve→terminal window is rare and operationally mitigable.

   **Operational mitigation (required at deploy):** graceful worker drain before rollout (let in-flight jobs finish / stop claiming new ones before SIGTERM) so a routine deploy does not strand (4b) reservations. **The real fix** — a persisted "billable-phase-entered" marker so the reaper can release active jobs that provably never billed, and real-cost settle that measures the class-B/timeout actual — is folded into the deferred **settle** slice (below). Neither residual re-opens the §1 outage self-DoS, which §3.1 closes.

**Deferred (documented, not built here):**
- **Real-cost settle (`actual_cents` from `usageMetadata`).** *This is the transitional escape hatch:* once settle exists, the §2.1 spend-aware boolean and the §5 keep/release heuristic become redundant — you measure real spend instead of guessing. Everything tagged "transitional" below is resolved by settle. **The settle slice also closes the §2.4 generation crash residual** (a "billable-phase-entered" job marker lets the reaper release never-billed crashed jobs).
- Serve-lease-expiry sweep; generation lease-expiry settle; backfill of already-leaked reservations (fresh deploy starts clean).

---

## 3. The Money Invariant

For each UTC day `d`:

> `spend_ledger.reserved_cents[d]` = Σ estimates of reservations made on day `d` that are **still in-flight, OR converted to a kept artifact, OR terminated after a billable call may have spent money**.

A reservation is **released** (credited back) **iff** it reaches a terminal state where **(a)** no artifact was kept **AND (b)** no billable Gemini call is *positively known to have possibly metered*. Because `actual_cents` stays 0, the cap predicate `reserved_cents + actual_cents + est ≤ daily_cap_cents` keeps bounding real spend — conservatively, never below true spend.

### 3.1 Failure classification — release rejections, keep timeouts (v4 / B-2 decision)

Round-3 caught that a *blanket* "any Gemini throw ⇒ KEEP" rule (v3) is money-safe but **defeats §1's founding goal**: a Gemini outage (a storm of 503/timeout throws) would KEEP every 150¢ reservation and self-DoS all users at ~$0 real spend — the exact problem this slice exists to fix. **User decision (2026-07-16): classify.** Release only failures we can **positively identify as not-metered**; keep everything else. Three classes:

| Class | Examples | Metered? | Action |
|---|---|---|---|
| **A — Pre-send / positively-rejected** | bad input / payload validation; duration-cap; magazine caps-missing / input-cap `NonRetryableError` (`gemini.ts:60,85,505`); transcription fail-closed `NonRetryableError` (`gemini.ts:658`); **a Google API error carrying HTTP status ∈ {429, 503}** (rate-limited / overloaded → refused *before* generation → 0 tokens → $0) — **RELEASE only when the job-scoped `billing.metered` latch is `false`** (no billable Gemini call returned a body anywhere in this job — see the latch below) | **no (provable)** | **RELEASE** |
| **B — Ambiguous (may have metered)** | client-side **timeout** / `REQUEST_TIMEOUT_MS` fired / deadline-exceeded; an `AbortError` **not** from our lease-abort signal; HTTP **500 / 502 / 504** (a 500/502 can occur *after* partial generation → treat as maybe-metered); connection-refused / DNS (see H-2 below — the SDK strips the code, so these fall here, KEPT); any error we cannot positively place in A | **unknown** | **KEEP** *(transitional — settle measures real actual)* |
| **C — Post-return** | Gemini call returned, then parse / `finishReason` incomplete (`gemini.ts:236`) / section-count mismatch (`gemini.ts:547`) / persist / promote / write threw; **the billable transcription fallback (`transcribeViaGemini`) succeeded** before a later step threw | **yes** | **KEEP** |

**The safe default is KEEP** (class B/C). RELEASE (class A) fires *only* on a positive not-metered signal. This closes the **dominant** outage self-DoS — an overloaded/rate-limited Gemini returns 429/503 (an *HTTP-status storm*), all class A → RELEASE — while never under-counting. **Narrowed from v4 (round-4 CL4-M1/C4-B1):** the release set is only {429, 503}, *not* {500, 502} (a 500/502 can follow partial generation → ambiguous → KEEP). The premise "a 429/503 bills nothing" **MUST be verified once against live Gemini** before class-A RELEASE is trusted (§9, gated like `CLOUD_TRANSCRIBE_FALLBACK_VERIFIED`); until verified the flag defaults to *treat-all-Gemini-throws-as-KEEP* (v3 behavior — safe; leaves the outage residual documented in §2.4).

**The metering signal is a JOB-SCOPED POSITIVE LATCH, not an inferred-from-error flag (v6 / round-5 B5-1).** Round-5 proved the fatal weakness of inferring "did anything bill?" from the *final thrown error*: a Gemini call that **succeeds returns a value — it never throws**, so a metered-then-imperfect early attempt in `generateSummary`'s outer `MAX_SUMMARY_ATTEMPTS` quality loop (`gemini.ts:359-368`) leaves no flag on the later attempt's 503 → mis-RELEASE. The robust design tracks billing **positively**: a job-scoped `BillingLatch { metered: boolean }` that flips to `true` the **instant any billable Gemini call returns a response body**, anywhere in the job. Since *nothing larger than the job* holds a reservation, this is the terminal-correct scope.

- **The latch** is a small mutable object the **runner** creates per job (`const billing = { metered: false }`) and threads through the handler → `summaryCore`/`digHandler`/`serve` → the Gemini functions (`generateSummary`, `transcribeViaGemini`, `generateDig`, `generateMagazineModel`). **Every** point that receives a Gemini response body sets `billing.metered = true` — critically **inside `generateSummary`'s outer loop, per returned `attempt()`** (`gemini.ts:363`), and after `transcribeViaGemini` returns segments, after `generateDig` returns, after `generateMagazineModel` returns. (A response body is proof-of-meter; Google bills on generated tokens.)
- **The runner's release decision:** `release = (classifyGeminiFailure(err, ourSignal) === 'release') && !billing.metered`. The latch **replaces** the per-loop `maybeMetered` flag entirely (which could only ever capture the *last* invocation's inner retries — B5-1). It subsumes: the within-inner-loop case (C4-B1), the outer-quality-loop case (B5-1), and the cross-call transcription→summary case (R5-B1/M5-1, gated-safe today but covered).

**The classifier (`classifyGeminiFailure(err, ourSignal)` → `'release' | 'keep'`)** now answers only "*is this final failure a positively-not-metered rejection?*" — the "did anything bill?" question is the latch's job. Walks the `.cause` chain `gemini.ts` populates (`:394,:441,:554`):
1. **our lease-abort? → `'keep'`.** `if (ourSignal?.aborted) return 'keep'`. Necessary, not stylistic — an SDK-internal abort surfaces as `GoogleGenerativeAIAbortError` with `.name === 'Error'` (not `'AbortError'`), so `err.name`/`instanceof` cannot distinguish our lease-abort from an SDK timeout — only our own signal can (CL4-L1).
2. **class-A pre-send / rejection → `'release'`.** `err` (or any `.cause`) `instanceof NonRetryableError` → `'release'`; a `GoogleGenerativeAIFetchError` (or our dig `GeminiHttpError`) whose `.status ∈ {429, 503}` → `'release'`.
3. **everything else → `'keep'`** (timeouts, non-lease abort, 400/500/502/504, SDK-stripped connection errors, post-return validation).

**Final rule: RELEASE iff `classify === 'release'` AND `billing.metered === false`.** The runner passes `p_billable_succeeded = !(release)`. No token counts, no cost math.

**Two more lib changes make the class-A signal reachable (round-4 — the classifier is only as good as the errors the code emits):**
- **Dig throws a typed status-bearing error (C4-H1).** `generateDig` (`lib/dig/generate.ts:268-271`) currently throws a **generic** `Error("...HTTP ${res.status}")` with no `.status` → a dig outage is invisible → dig KEEPs (§1 closure was false for dig). Fix: throw a typed `GeminiHttpError { status }` the classifier recognizes; and set `billing.metered=true` if a dig response body arrived (incl. before a mid-stream disconnect). (Dig uses a hand-rolled REST helper, not the SDK — its own typed error, distinct from `GoogleGenerativeAIFetchError`.)
- **Transcript wrapper preserves the TYPED error, not the first non-null (CL4-H1).** `resolveTranscriptSegments` (`transcript-source.ts:62`) wraps `{ cause: captionErr ?? geminiErr }`. Because `fetchTranscriptSegments` **throws** on no-captions (`youtube.ts:90`), `captionErr` is truthy for **every** caption-less cloud video, so the typed class-A `NonRetryableError` (fail-closed transcribe, `gemini.ts:658`) is discarded → classifier sees a generic error → KEEP ($0 leak). Fix: when the Gemini fallback threw a typed error, re-throw it (or set `{ cause: geminiErr }`) so `NonRetryableError` survives. (When the transcribe fallback flag flips on and it *bills*, the latch — not the error — carries that: `transcribeViaGemini` returning segments sets `billing.metered=true`, so a later summary 503 KEEPs — M5-1.)

**Situational summary (both paths):**

| Situation | Class | Action |
|---|---|---|
| Handler succeeded (`complete_job`) | — (artifact kept) | **KEEP** |
| Bad input / duration-cap / caps `NonRetryableError` (pre-send, typed), `billing.metered=false` | A | **RELEASE** |
| Gemini API status ∈ {429, 503}, `billing.metered=false` (summary/magazine SDK **or** typed dig `GeminiHttpError`) | A | **RELEASE** |
| Gemini **timeout** / non-lease `AbortError` / 500 / 502 / 504 / SDK-stripped connection error | B | **KEEP** |
| **Any billable Gemini call returned a body earlier in this job** (`billing.metered=true`), then a final 429/503 | — (latch) | **KEEP** (overrides class-A) |
| Gemini returned then parse/section-count/persist threw | C | **KEEP** |
| Transcription fallback billed, then a later step threw (`billing.metered=true`) | — (latch) | **KEEP** |
| Cancel of a `queued` job (never ran) | — | **RELEASE** |
| Cancel of an `active` job; worker crash → reaper | — | **KEEP** (may have spent — §2.4 residual) |
| Serve `generateMagazineModel`: class A throw | A | **RELEASE** |
| Serve `generateMagazineModel`: class B/C throw, or write threw | B/C | **KEEP** |
| Serve materialized successfully | — (cached) | **KEEP** |

(**At-capacity** is *not* in this table: an at-capacity `enqueue_job`/`reserve_serve_model` **rolls back its own reserve** (`0018:64`, `0014:85`) — there is no reservation to release, so it is a no-op, not a RELEASE — L-1.)

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

**Default direction:** `p_billable_succeeded` defaults to **`true` = conservative KEEP** (`false` = "releasable-unless-told-otherwise" is WRONG) so an un-updated caller — or any unclassified error (M2) — never wrongly refunds. The worker-runner passes `false` only for a §3.1 class-A (positively not-metered) failure.

**`fail_job` release body (SQL — M-3).** The recreated body is the existing function verbatim, but the initial `select … into` must additionally read `created_at` and `reserved_cents` (the current `SELECT` at `0008:148` reads neither), and after `v_new` is computed the release fires **only** on a genuine terminal fail with `p_billable_succeeded=false` — a retryable requeue (`v_new='queued'`) must **not** release (behavior 6). The whole thing stays inside the existing `status='active'` single-writer fence (`0008:149-151`), so it is exactly-once:
```sql
-- after: select attempts, max_attempts, cancel_requested, created_at, reserved_cents
--        into v_attempts, v_max, v_cancel, v_created_at, v_reserved from jobs
--        where id=p_job_id and locked_by=p_worker_id and lease_token=p_lease_token and status='active' for update;
-- … (unchanged v_new computation: cancelled / failed / dead_letter / queued) …
-- … (unchanged UPDATE jobs SET status=v_new, …) …
if not p_billable_succeeded
   and v_new in ('failed','dead_letter','cancelled')   -- NOT 'queued' (retry reuses the reservation)
   and v_reserved > 0 then
  update spend_ledger
     set reserved_cents = reserved_cents - v_reserved, updated_at = now()
   where day = (v_created_at at time zone 'utc')::date
     and reserved_cents >= v_reserved;
  if not found then
    insert into ledger_audit(day, kind, expected_amt, note, at)
      values ((v_created_at at time zone 'utc')::date, 'release_underflow', v_reserved,
              'fail_job '||p_job_id::text, now());
  end if;
  update jobs set reserved_cents = 0 where id = p_job_id;   -- belt-and-suspenders (single-writer fence is primary, §4.3)
end if;
return v_new;
```
(The `v_new='queued'` exclusion is the load-bearing requeue guard; the `status='active'` fence already guarantees only one terminal writer reaches this.)

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

**Worker-runner + handler classification (fixes B1/B-2 + M2 + H-1). RELEASE only on a §3.1 class-A (positively not-metered) failure; KEEP everything else.**

The runner combines the **error classification** with the **job-scoped billing latch** (§3.1) and passes `p_billable_succeeded = !(classify === 'release' && !billing.metered)`. So `false` (RELEASE) fires only for a §3.1 class-A failure (pre-send `NonRetryableError`, or a rejection status ∈ {429, 503}) **and** `billing.metered === false`. Class B (timeouts, non-lease `AbortError`, 500/502/504, SDK-stripped connection errors), class C (post-return), and **anything with `billing.metered=true`** → `true` (KEEP).

**Implementability (§3.1) — the signal must reach the runner.** Round-3→round-5 found the class-A signal unreachable / mis-scoped on several paths. §3.1 pins the fixes; in short: (1) a **job-scoped `billing.metered` latch** (set on *any* Gemini response body — outer summary loop, transcription, dig, magazine) replaces the fragile per-loop `maybeMetered`, so a metered-then-rejected sequence at *any* granularity KEEPs (B5-1/C4-B1/R5-B1); (2) `generateDig` throws a typed `GeminiHttpError { status }` so dig outages are visible (C4-H1); (3) `resolveTranscriptSegments` preserves the **typed** Gemini error (not `captionErr ?? geminiErr` — CL4-H1). The connection-`.code` branch is **dropped** (the SDK strips `.code` — CL4-H2), so connection-only errors KEEP.

**Runner plumbing — specified end-to-end (M2 + B5-1).** Today `worker-runner.ts:53-66` catches a bare `e` and computes only `retryable`; no billable signal. The runner owns the decision, since it has the error, `ourSignal` (the lease `AbortSignal`), and the `billing` latch it created and threaded into the handler:
- Runner: `const release = classifyGeminiFailure(e, ctx.signal) === 'release' && !billing.metered;` then `failJob(..., { p_billable_succeeded: !release })`.
- **Unknown / unrecognized error ⇒ `'keep'` ⇒ KEEP.** An unclassified or new error type KEEPs — a bounded 150¢ leak in the *safe* direction, never a wrong RELEASE. SQL default (`true`) and runner default agree.
- **`billing.metered=true` ⇒ KEEP regardless of the error class** — the latch is the authoritative "real money was spent in this job" signal; it overrides a class-A final error (this is the B5-1 fix).
- Idempotency-skip is **not** a failure path — the handler `return`s → runner calls `complete` (KEEP) → never reaches this decision (M-1).

**`request_cancel_job` gating (fixes B2; H1 pre-read + H-3 audit + H-4 return — round-3).** Three constraints the single multi-CTE form couldn't satisfy together: (a) read OLD `reserved_cents` **before** zeroing (PG<18 `RETURNING` is post-update); (b) write a `ledger_audit` row on underflow (§4.2 — a plain CTE decrement just matches 0 rows, no `if not found`, so corruption is silently swallowed — H-3); (c) return **1 for both** a queued cancel *and* an active flag-set (the adapter + `cancel-job-rpc.test.ts:37` assert this — a CTE whose final statement is the ledger update would return 0 for an active cancel — H-4). Cleanest as **procedural plpgsql** (like `fail_job`), returning `int`:
```sql
declare v_old_status text; v_old_amt int; v_day date;
begin
  -- (keep the existing owner/auth guard)
  select status, reserved_cents, (created_at at time zone 'utc')::date   -- snapshot OLD under a row lock
    into v_old_status, v_old_amt, v_day
    from jobs
   where id = p_job_id and owner_id = auth.uid() and status in ('queued','active')
   for update;                                       -- serializes vs claim_next_job's `for update skip locked`
  if not found then return 0; end if;                -- nothing to cancel (terminal/foreign/missing)
  update jobs
     set cancel_requested = true,
         status         = case when v_old_status = 'queued' then 'cancelled' else status end,
         reserved_cents = case when v_old_status = 'queued' then 0 else reserved_cents end,
         updated_at     = now()
   where id = p_job_id;
  if v_old_status = 'queued' and v_old_amt > 0 then   -- RELEASE only a genuine queued→cancelled, OLD amt+day
    update spend_ledger set reserved_cents = reserved_cents - v_old_amt, updated_at = now()
     where day = v_day and reserved_cents >= v_old_amt;
    if not found then                                 -- guarded-decrement underflow → audit, never silent clamp
      insert into ledger_audit(day, kind, expected_amt, note, at)
        values (v_day, 'release_underflow', v_old_amt, 'request_cancel_job '||p_job_id::text, now());
    end if;
  end if;
  return 1;                                           -- cancellation WAS requested (queued OR active) — H-4
end;
```
An `active` flag-set sets only `cancel_requested`, never releases, and still returns 1. A repeat cancel of a terminal job → `not found` → returns 0 (idempotent). Release fires once (the `status='active'`/`queued` snapshot under lock is the single-writer guard).

**`request_cancel_playlist_jobs` (fixes Codex-B4; H2 multi-day + H-2 active-flag + H-3 set-audit + H-4 return — round-3).** Inherently multi-row / multi-day (queued jobs span the UTC-midnight boundary, each with its own amount+day). Three round-3 corrections over v3: **(H-2)** the flag `cancel_requested=true` must still hit **active** jobs (the whole reason `0019` exists — an in-flight worker must stop writing to rows the cascade delete is about to remove); v3's queued-only `pre` silently dropped that → write-after-delete race. **(H-3)** the ledger underflow must audit *per day* (a single `if not found` can't fire when some days decrement and one doesn't). **(H-4)** the return must count **jobs flagged** (queued+active), not `spend_ledger` day-rows touched. One data-modifying-CTE statement satisfies all three (all `with` branches execute exactly once; `aud` reads `dec`'s RETURNING, not a table re-read):
```sql
return (
  with pre as (                                  -- ALL non-terminal jobs of the playlist, under lock
    select id, status as old_status, reserved_cents as old_amt,
           (created_at at time zone 'utc')::date as reserve_day
      from jobs
     where playlist_id = p_playlist_id and owner_id = auth.uid() and status in ('queued','active')
     for update),
  upd as (                                       -- H-2: flag ALL; flip+zero only the queued subset
    update jobs j
       set cancel_requested = true,
           status         = case when pre.old_status='queued' then 'cancelled' else j.status end,
           reserved_cents = case when pre.old_status='queued' then 0 else j.reserved_cents end,
           updated_at     = now()
      from pre where j.id = pre.id
     returning j.id),
  per_day as (                                   -- queued-only OLD amounts, grouped by reserve-day
    select reserve_day, sum(old_amt) as amt
      from pre where old_status='queued' and old_amt > 0
     group by reserve_day),
  dec as (                                       -- guarded per-day decrement; RETURNING days actually credited
    update spend_ledger sl
       set reserved_cents = sl.reserved_cents - per_day.amt, updated_at = now()
      from per_day
     where sl.day = per_day.reserve_day and sl.reserved_cents >= per_day.amt
     returning sl.day),
  aud as (                                       -- H-3 set-based audit: every per_day with no successful decrement
    insert into ledger_audit(day, kind, expected_amt, note, at)
    select pd.reserve_day, 'release_underflow', pd.amt,
           'request_cancel_playlist_jobs '||p_playlist_id::text, now()
      from per_day pd
     where pd.reserve_day not in (select day from dec))
  select count(*)::int from upd);                -- H-4: return = jobs flagged (queued + active)
```
`active` jobs keep their reservation (may have spent; §2.4) but ARE flagged. Route order (`app/api/playlists/[id]/route.ts:65,73`) cancels before delete — the release lives here so it runs while rows still exist. Idempotent: a second call finds no `queued`/`active` `pre` rows → `count=0`, no release. (This multi-row/multi-day complexity is round-1 F5 *relocated* from the reaper, not eliminated — genuinely needed here.)

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
- **Caller read (M-2):** a `returns table(...)` function comes back through supabase-js `.rpc()` as a **row set (array)** — cf. how `claim_next_job`'s table return is read as `data[0]` (`supabase-job-queue.ts:60-61`). So `serve-doc.ts:52-56` must read `const { status, release_token } = data[0]` (or the fn returns a single composite scalar consumed via `.single()`). Destructuring `{ status }` directly off `data` yields `undefined` → the `switch` hits `default: throw` on **every** serve, stranding the reservation just made. Pick the array-`data[0]` shape (matches the `claim_next_job` precedent) and pin it.

The token is **server-held**: it is never placed in any client-visible `ResolveResult`, so a browser client cannot obtain it (this is what makes the §6 un-charge defense hold).

**Caller change (`lib/html-doc/serve-doc.ts`) — classification applied to serve (B-1, round-3).** On the `'reserved'` branch, capture the token. `try` the materialize (`generateMagazineModel`, `serve-doc.ts:81`) + write. Then:
- **Success** → `settle_serve_model(token, released:=false)` (keep the charge; clear marker/token).
- **Throw** → decide with the **same** `classify(err,ourSignal)==='release' && !billing.metered` rule (§3.1). Serve has a single billable call (`generateMagazineModel`), so `billing.metered` is set only if that call returned a body before a later throw. **Release** (class A — pre-send `NonRetryableError` at `gemini.ts:505`/`:85`, or a Google rejection status ∈ {429, 503}, with `billing.metered=false`) → `settle_serve_model(token, released:=true)` (refund the 6¢). **Keep** (class B/C — timeout, non-lease `AbortError`, 500/502/504, SDK-stripped connection error, section-count/parse mismatch at `gemini.ts:547`, the write step threw, or `billing.metered=true`) → `settle_serve_model(token, released:=false)` (KEEP the charge; server may have metered) — this is the fix for the round-3 serve under-count. Then re-throw either way.

v3's blanket "`released:=true` on any throw" was the pre-B1 rule and under-counted a metered-then-timed-out magazine call (6¢). Serve now KEEPs on class B/C exactly like generation. Every WHERE keeps `owner_id = auth.uid()` (no cross-tenant release; L3). A failed serve still burns `attempt_count` (§6) whether kept or released.

---

## 7. Enumerated Behaviors (test contract)

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| 1 | Success keeps | handler returns; `complete_job` → `completed` | ledger + `jobs.reserved_cents` unchanged |
| 2 | Class-A pre-send fail releases | fail **before any Gemini bytes sent** (bad payload / caps `NonRetryableError` / duration-cap); `classify='release'`; `fail_job(billable=false)` → `failed`/`dead_letter` | ledger `-= est` on reserve-day; `jobs.reserved_cents → 0` |
| 2b | Class-A Gemini REJECTION {429,503} releases (B-2) | `generateSummary`/`generateMagazineModel` throws `GoogleGenerativeAIFetchError.status ∈ {429,503}`, **`billing.metered=false`**; `classify='release'`; `fail_job(billable=false)` | **released** — the §1 outage case; budget re-opens |
| 2c | Dig outage {429,503} releases (C4-H1) | `generateDig` throws typed `GeminiHttpError{status∈{429,503}}`; `classify='release'` | **released** — dig gets the same outage-closure as summary/magazine |
| 3 | Class-B Gemini TIMEOUT / 500 / 502 keeps (B1/B-2/CL4-M1) | `generateSummary` throws a client-side timeout / non-lease `AbortError` / HTTP **500/502**/504 (may have metered); `classify='keep'`; `fail_job(billable=true)` | **no** release (KEEP) |
| 3b | Class-C transcription-billed then fail KEEPS (B1) | captions absent → `transcribeViaGemini` succeeds (billable) → later step throws; `classify='keep'` | **no** release (KEEP) |
| 3c | Unclassified error KEEPS (M2) | runner can't place the error in class A → default `'keep'` | **no** release (KEEP; bounded safe leak) |
| 3d | Class-A reachable through transcript wrapper (H-1/CL4-H1) | caption-less, `CLOUD_TRANSCRIBE_FALLBACK_VERIFIED=false` → caption fetch throws **and** the typed transcription-disabled `NonRetryableError` survives `resolveTranscriptSegments` (preserved, not dropped by `captionErr ?? geminiErr`) → `classify='release'` | **released** (not a $0 KEEP-leak) |
| 3e | Inner-retry metered then 429/503 KEEPS (C4-B1) | one `generateJson` call: attempt 1 gets a body then parse-fails → retry → attempt 2 returns 503; body set `billing.metered=true`; `classify='release'` but latch → **KEEP** | **no** release (real spend not refunded) |
| 3e2 | **Outer-loop** metered then 429/503 KEEPS (B5-1 — LIVE) | `generateSummary` outer loop: attempt `i=0` **returns** a body (metered) but summary imperfect → loop continues → attempt `i=1` throws 503; `billing.metered=true` (set on the i=0 return); `classify='release'` but latch → **KEEP** | **no** release — the round-5 Blocking; the whole point of the job-scoped latch |
| 3e3 | Cross-call transcription metered then summary 429/503 KEEPS (R5-B1/M5-1) | `CLOUD_TRANSCRIBE_FALLBACK_VERIFIED=true` → `transcribeViaGemini` returns (metered, sets latch) → `generateSummary` throws 503; latch → **KEEP** | **no** release (gated-safe today; latch covers it when the flag flips) |
| 3f | SDK-stripped connection error KEEPS (CL4-H2) | DNS/ECONNREFUSED → SDK rewraps as bare `GoogleGenerativeAIError` (no `.status`/`.code`); `classify='keep'` | **no** release (KEEP; documented connection-tail residual) |
| 4 | Class-C post-return fail KEEPS | `generateSummary` returned, then parse/section-count/persist throws; `classify='keep'` → `dead_letter` | **no** release *(transitional)* |
| 5 | Cancel-mid-run keeps or releases correctly | `cancel_requested` + handler throws pre-billing | released only if `billable=false` |
| 6 | Retry reuses one reservation | retryable fail, `attempts<max`; `fail_job` → `queued` | **no** release; next attempt does not re-reserve |
| 7 | Reaper never releases | lease expires (any attempts); `sweep` → `queued`/`dead_letter`/`cancelled` | **no** release (KEEP) |
| 8 | Cancel queued releases | `request_cancel_job`, genuine `queued→cancelled` | released; `jobs.reserved_cents → 0` |
| 9 | Cancel ACTIVE keeps + returns 1 (H-4) | `request_cancel_job` on an `active` job (flag-set, status stays `active`) | **no** release; function **returns 1** (`cancel-job-rpc.test.ts:37`), `cancel_requested=true` |
| 10 | Cancel active, then success keeps | active cancel, handler already succeeded; `complete_job` → `cancelled` | **no** release (artifact exists) |
| 11 | Double-cancel no double-release | cancel an active job twice | at most one release, and only if it ever genuinely flips `queued→cancelled` |
| 12 | Playlist delete: queued released, multi-day | `request_cancel_playlist_jobs`, queued jobs on days X and Y, before cascade delete | day X and day Y ledger rows **each** `-= their group sum`; return = count of jobs flagged |
| 13 | Playlist delete: active flagged + kept (H-2) | active jobs on the deleted playlist | reservation kept (§2.4); **but `cancel_requested=true` IS set** so the worker stops writing before cascade delete |
| 13b | Playlist per-day underflow audits (H-3) | one of the multi-day `spend_ledger` rows is missing/below | that day's release no-ops **and writes a `ledger_audit` row**; other days still credit |
| 14 | Midnight-span day-correct | job `created_at` day X, terminal day Y | release credits day **X** |
| 15 | Guarded decrement audits | release when ledger row missing / below amount | no negative; `ledger_audit` row written; terminal still commits |
| 16 | Cap re-opens after release | reserve to cap, a pre-billing failure releases | subsequent `enqueue_job`/`enqueue_preflight` admits again |
| 17 | Serve class-A fail releases both | `generateMagazineModel` throws class-A (caps `NonRetryableError` **or** Google status ∈ {429,503}), no body received (`billing.metered=false`); `classify='release'` → `settle_serve_model(token, released=true)` | `spend_ledger` and `serve_owner_budget` each `-= 6`; marker/token cleared; `attempt_count` unchanged |
| 17b | Serve class-B/C fail KEEPS (B-1) | `generateMagazineModel` throws a timeout / section-count mismatch (`gemini.ts:547`), or the write step throws; `classify='keep'` → `settle_serve_model(token, released=false)` | **no** ledger change (server may have metered); marker/token cleared; `attempt_count` unchanged |
| 18 | Serve success keeps | materialize+write succeed → `settle_serve_model(token, released=false)` | no ledger change; marker/token cleared |
| 19 | Serve un-charge blocked | after a KEPT serve, call `settle_serve_model(token, released=true)` | no-op (marker/token already cleared) |
| 20 | Serve double-refund blocked | call release settle twice for one failed attempt | second is a no-op |
| 21 | Serve wrong-day blocked | reserve day X (23:59), reserve same doc day Y (00:00), release X | credits day X's row only |
| 22 | Serve K-bound survives releases | K failed serves, each released | `attempt_count` reaches `max_serve_attempts` → `'attempts_exhausted'` |
| 23 | Retry-keep path reachable | force `max_attempts > 1` in the fixture | behaviors 6/7's KEEP-on-requeue actually fire (not vacuous) |
| 24 | Serve lease-overlap = bounded leak, not double-refund (H5) | reserve token A; expire the 180s lease; second view reclaims (token B, `+6`); settle A | A's settle no-ops (token overwritten); B can still settle; net ≤ one release; ledger never goes negative; per-owner burn ≤ 60¢ |
| 25 | Generation crash residual KEPT + documented (§2.4b) | `active` job (150¢ reserved, no billable call yet); worker killed; reaper terminalizes | **no** release (KEEP); 150¢ stays reserved till midnight — asserts the accepted §2.4b crash residual, not a bug |
| 26 | Outage self-DoS is CLOSED for the HTTP-status storm (B-2) | N generations (summary/magazine/dig) all hit Google **503** (class A, `billing.metered=false`) → all release | after N releases the ledger is back to baseline; a fresh `enqueue_job` admits — the dominant §1 outage no longer self-DoSes |

---

## 8. Edge Cases

- **Guarded decrement** (§4.2) replaces `greatest(0,…)`; a would-be-negative release writes a `ledger_audit` row instead of silently zeroing.
- **Missing ledger/budget row on release:** guarded decrement no-ops + audits; cannot happen on the normal path (reserve created the row).
- **Concurrency:** release lives inside the terminal RPC's single-writer guard; reaper never releases (so it can't race a worker's release); serve release is token-gated and single-use.
- **`p_billable_succeeded` default = `true` (KEEP):** an un-migrated / older caller — **and any unclassified error** (§5 M2) — never wrongly refunds; the unsafe direction (refund real spend) requires an explicit `false` on a proven pre-send failure.
- **Gemini failure classification + billing latch (§3.1, B-2 / round-4 / round-5):** RELEASE only when `classify(err) === 'release'` (pre-send `NonRetryableError`, or Google status ∈ **{429, 503}**) **AND** the **job-scoped `billing.metered` latch is `false`**. The latch (set on *any* Gemini response body anywhere in the job — the outer summary loop, transcription, dig, magazine) is the authoritative "real money spent" signal and overrides a class-A final error (B5-1). KEEP class B (timeout/non-lease-abort/500/502/504/SDK-stripped-connection), class C (post-return), and anything with `billing.metered=true`. Applies to generation, serve, and the typed-dig path. Unrecognized → KEEP. Requires the job-scoped latch, the typed dig `GeminiHttpError`, and the transcript wrapper preserving the typed cause; plus one-time live verification (§9).
- **Cancel OLD-value capture + audit + return (H1/H-3/H-4):** both cancel RPCs are procedural/`for update` pre-read of OLD `reserved_cents` *before* zeroing (PG<18 `RETURNING` is post-update); release gated on genuine `queued→cancelled`; underflow writes `ledger_audit` (per-day for playlist); the function return counts **jobs flagged** (queued+active), not ledger rows. Playlist still flags `cancel_requested` on active jobs (H-2).
- **Serve lease overlap (H5):** a serve generation exceeding the un-heartbeated 180s lease can be reclaimed → a bounded 6¢ leak (releases ≤ reserves), folded into the §2.3 residual; never a double-refund or under-count.
- **Accepted residuals (§2.4):** (4a) a rare class-B timeout-after-metering (150¢, KEEP for money-safety) and (4b) a worker crash before any terminal write (150¢ global, count-unbounded); both mitigated by graceful drain / closed by settle. Neither re-opens the §1 outage self-DoS (§3.1 closes it).
- **At-capacity is a no-op, not a RELEASE (L-1):** `enqueue_job`/`reserve_serve_model` roll back their own reserve at capacity → nothing to credit back.

---

## 9. Testing Strategy

Against **real PostgREST + Postgres** (not mocks — the BUG-1 lesson: a mocked money test missed a real PostgREST param-drop). Integration tests assert exact ledger/budget/job-column deltas for behaviors 1–26. Include: a concurrency test (two claimants race a terminal write → exactly one release); the midnight-span test (back-dated `created_at`) **for both single and playlist cancel** (multi-day, behavior 12); the cancel-return-contract assertions (behavior 9 active-cancel returns 1; playlist returns jobs-flagged count — H-4); the playlist active-flag test (behavior 13 — `cancel_requested=true` on the active job — H-2); the per-day audit path (behavior 13b — H-3); the serve un-charge/double-refund/wrong-day trio (19–21); the guarded-decrement audit path (15, asserting a `ledger_audit` row *and* that the terminal transition still commits — H4).

**Classification unit tests (`classifyGeminiFailure`, §3.1 — B-2/H-1/round-4).** A unit suite asserts `'release'` vs `'keep'` against **realistic, code-accurate** error shapes (round-4 CL4-H2: do NOT assert on synthetic shapes the code never emits):
- `GoogleGenerativeAIFetchError` with `.status ∈ {429,503}` and `billing.metered=false` → `release`; with `.status ∈ {500,502,504}` → `keep` (CL4-M1).
- a typed dig `GeminiHttpError{status:503}` → `release` (C4-H1); `{status:500}` → `keep`.
- a pre-send `NonRetryableError` surfaced *through* `resolveTranscriptSegments` (with the caption fetch also throwing, the real path) → `release` — proves the typed error is preserved, not dropped by `captionErr ?? geminiErr` (CL4-H1).
- **billing-latch tests (B5-1/C4-B1/R5-B1) — the critical under-count guards.** With `billing.metered=true`, a final `.status=503` → the runner decision is **KEEP** even though `classify` alone says `'release'`. Cover all three granularities: (i) inner-retry body-then-503 in one `generateJson`; (ii) **outer-loop** — `generateSummary` attempt `i=0` returns a body then attempt `i=1` throws 503 (B5-1, the live Blocking); (iii) **cross-call** — `transcribeViaGemini` returns (latch set) then `generateSummary` throws 503. All → KEEP. And the converse: a first-and-only-attempt clean 503 with `billing.metered=false` → RELEASE (behavior 2b).
- a bare `GoogleGenerativeAIError` from an SDK-rewrapped connection failure (no `.status`/`.code`) → `keep` (CL4-H2 — the connection tail genuinely KEEPs; do not test a fake `{code:'ECONNREFUSED'}`).
- a client-side timeout / SDK-abort `GoogleGenerativeAIAbortError` (`.name==='Error'`) with `ourSignal.aborted===false` → `keep`; with `ourSignal.aborted===true` (our lease abort) → `keep` (requeue, not a verdict) — and assert the classifier distinguishes them **via `ourSignal`, not `err.name`** (CL4-L1).
- a section-count/parse post-return error → `keep`; an unrecognized error → `keep`.

**Live verification gate (§3.1).** Before trusting class-A RELEASE in production, verify against **live Gemini** that (a) an overloaded/rate-limited call surfaces as `GoogleGenerativeAIFetchError` with `.status ∈ {429,503}`, and (b) those statuses genuinely carry no token billing. Gate behind a flag (mirror `CLOUD_TRANSCRIBE_FALLBACK_VERIFIED`): until set, fall back to treat-all-Gemini-throws-as-KEEP (v3 behavior — safe; leaves only the §2.4-documented outage residual). The behavior-2b/2c/3d RELEASE tests run against mocked errors; the live check is a separate manual gate recorded in `docs/local-validation-findings.md`.

---

## 10. Out of Scope / Deferred

- **Real-cost settle (`actual_cents`).** *Transitional resolver:* once built, it supersedes the §3.1 keep/release classification and the §3 keep-on-class-B/C rows — real cents replace the guess, so even the ambiguous class-B timeout resolves to its true cost. Its own slice, when the cap constrains real traffic. **Also carries the "billable-phase-entered" job marker that lets the reaper release never-billed crashed jobs — closing the §2.4b crash residual.**
- **Serve-lease heartbeat / serve-lease-expiry sweep** (closes the accepted serve crash + lease-overlap residual, §2.3/H5).
- **Backfill** of already-leaked reservations (fresh deploy starts clean; local dev resets manually).
- **Operational (not code):** graceful worker drain before deploy — the required mitigation for the §2.4b crash residual until settle lands.

---

## 11. Review Requirements

Money path + concurrency + idempotency → **iterative dual adversarial review to convergence** (Codex + Claude, independent), re-reviewing each round until a round returns no new Blocking/High. Round-1→v2, 2→v3, 3→v4, 4→v5, 5→v6 (all NOT CONVERGED; docs `docs/reviews/reservation-release-spec-v{1,2,3,4,5}-*`). **Round-6 explicit targets** (verify the round-5 fix is genuine + hunt any surviving under-count): the **job-scoped `billing.metered` latch** genuinely covers *every* point a billable Gemini body can be received before a later class-A throw — the `generateSummary` outer `MAX_SUMMARY_ATTEMPTS` loop (B5-1), the three inner retry loops (C4-B1), and the transcribe→summary→(swallowed)quickview sequence (R5-B1/M5-1) — with **no** metered-then-released path surviving at any granularity; the latch is threaded correctly runner→handler→core→gemini and read in the runner's final decision; behavior 17 no longer lists `connection`; and the whole live spec agrees on the latch (no stale `maybeMetered`/`no prior metered attempt`/`connection→release`). The SQL bodies were verified closed in round-4/round-5 and are unchanged in v6.

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

---

## 14. v4 Change Log (round-3 review responses)

Round-3 dual review (`docs/reviews/reservation-release-spec-v3-{codex,claude}.md`) returned **NOT CONVERGED** — narrowing (findings were follow-ons of v3's own fixes). Both reviewers corroborated the serve-taxonomy Blocking; Claude additionally surfaced a **goal-affecting** contradiction. Resolutions:

- **B-2 — v3's blanket "KEEP all Gemini throws" defeats §1's goal (Claude B-2) [Blocking, goal-affecting].** Conservative-KEEP means a Gemini outage still self-DoSes at ~$0 spend — the exact §1 problem — while §2.4 claimed it "closed". **User decision (2026-07-16): classify.** New **§3.1**: RELEASE only positively-not-metered class-A failures (pre-send `NonRetryableError`, Google API {429,500,502,503}, connection/DNS); KEEP class B (timeout/504/non-lease-abort) and class C (post-return). Single helper `classifyGeminiFailure(err, ourSignal)`. Closes the outage self-DoS; keeps the one ambiguous timeout money-safe. §1/§2.4/§5/§10 rewritten to one consistent story; §2.4 residual shrunk to (4a) rare class-B timeout + (4b) crash-window.
- **B-1 / C3-B1 — serve leg still refunded on any throw (Codex C3-B1 / Claude B-1) [Blocking].** The B1 fix was generation-only. **Fix:** serve caller applies the same `classifyGeminiFailure` — `settle_serve_model(released=true)` only on class A, `released=false` (KEEP) on class B/C (§6).
- **H-1 — the taxonomy was unreachable through the real error flow (Claude H-1) [High].** `resolveTranscriptSegments` flattened typed pre-send errors into a generic `Error`, so no class-A signal reached the runner → every caption-less failure KEPT at $0. **Fix:** the transcript wrapper must preserve `{ cause }`; `classifyGeminiFailure` walks the `.cause` chain `gemini.ts` already populates (§3.1, §5).
- **H-2 — playlist CTE stopped flagging `cancel_requested` on active jobs (Claude H-2) [High].** v3's queued-only `pre` dropped the write-after-delete guard that is `0019`'s entire purpose. **Fix:** the data-modifying-CTE flags ALL non-terminal jobs, flips/zeroes only the queued subset (§5).
- **H-3 — guarded-decrement audit not expressible in the single multi-CTE cancel form (Claude H-3) [High].** A CTE decrement just matches 0 rows on underflow — no audit. **Fix:** `request_cancel_job` → procedural plpgsql with `if not found then insert ledger_audit`; playlist → a set-based `aud` CTE auditing every `per_day` with no successful decrement (§5).
- **H-4 — cancel `returns int` row_count read the ledger update, not the jobs mutation (Codex C3-M2 / Claude H-4) [High].** An active-cancel would return 0 (breaks `cancel-job-rpc.test.ts:37`); a 5-queued-1-day playlist would return 1 not 5. **Fix:** `request_cancel_job` returns 1 on any matched cancel; playlist returns `count(*) from upd` (jobs flagged) (§5).
- **M-1 — idempotency-skip classified RELEASE but actually completes (Claude M-1) [Medium].** The handler `return`s → `complete_job` → KEEP. **Fix:** removed from the RELEASE set; §3/§5/§7 aligned.
- **M-2 — `returns table` → `.rpc()` array, but §6 destructured an object (Codex C3-H1 / Claude M-2) [Medium/High].** **Fix:** read `data[0]` (matches the `claim_next_job` precedent) (§6).
- **M-3 — `fail_job` release body was prose-only (Claude M-3) [Medium].** **Fix:** SQL given — reads `created_at`/`reserved_cents`, gates on `v_new in ('failed','dead_letter','cancelled')` (excludes the `queued` requeue — behavior 6) + `not p_billable_succeeded`, audits underflow (§5).
- **L-1 — at-capacity listed as RELEASE but nothing is reserved (Claude L-1).** Clarified as a no-op (§3.1, §8).
- **L-2 — `PermanentTranscriptError` path description inaccurate (Claude L-2).** Behavior 3b uses the realistic "transcription billed then threw" shape; the pre-call description is dropped.

**Round-3 verified-closed (carried forward, no v4 change):** H4 (`ledger_audit` RLS/grants + "insert cannot raise") — genuinely airtight for the paths that insert; H5 (serve lease-overlap bounded residual) — no double-refund; M1 `regprocedure` probe survives the return-type change; the `fail_job` DROP+recreate analysis.

**Scope note (v4):** the round-3 growth is the §3.1 classifier (a lib-layer helper + a transcript-wrapper fix) and correct SQL for the cancel/`fail_job` bodies. The one goal-touching item (B-2) was a human decision that *restored* the slice's original goal (release outages) with a money-safe carve-out (keep ambiguous timeouts) — a re-alignment, not an expansion.

---

## 15. v5 Change Log (round-4 review responses)

Round-4 dual review (`docs/reviews/reservation-release-spec-v4-{codex,claude}.md`) returned **NOT CONVERGED** — 1 Blocking + 3 High, all on one topic: the §3.1 classifier's *implementability* against the codebase's heterogeneous error production (SDK summary/magazine, hand-rolled REST dig, wrapped transcript, retry loops). The SQL bodies were verified closed. Resolutions — all tighten the classifier to be robustly-detectable, positively-pre-generation, and retry-aware:

- **C4-B1 — classifier could RELEASE after an earlier metered retry (Codex) [Blocking, under-count].** `generateJson` attempt 1 gets a billable response then fails on local parse; retry; attempt 2 returns 503 → classifier saw only the final 503 → RELEASE → refunds a metered generation. **Fix:** the retry loops (`generateJson`, `transcribeViaGemini`, dig's retry) set an aggregate **`maybeMetered=true`** if any attempt received a response body or was ambiguous; the classifier KEEPs whenever `maybeMetered` (§3.1 step 2). Only the *sole under-count vector* found in round-4 — closed.
- **C4-H1 — dig outage RELEASE not implementable (Codex) [High].** `generateDig` (`lib/dig/generate.ts:268`) throws a generic `Error("...HTTP 503")` with no `.status` → invisible to the classifier → dig KEEPs its 150¢ (the §1 closure was false for dig, which uses a REST helper, not the SDK). **Fix:** `generateDig` throws a typed `GeminiHttpError { status }` the classifier recognizes; dig's retry participates in `maybeMetered` (§3.1, behavior 2c).
- **CL4-H1 — the H-1 transcript fix picked the wrong `.cause` (Claude) [High].** `transcript-source.ts:62` wraps `{ cause: captionErr ?? geminiErr }`; the caption fetch **always throws** (`youtube.ts:90`), so `captionErr` is truthy and the typed class-A `NonRetryableError` is discarded → caption-less cloud videos KEEP at $0 (behavior 3d was false). **Fix:** preserve the **typed** Gemini error (re-throw it, or `{ cause: geminiErr }`) so it survives to the classifier (§3.1, §5).
- **CL4-H2 — connection/DNS marker unreachable (Claude) [High].** The SDK's `handleResponseError` rewraps undici `fetch failed` as a bare `GoogleGenerativeAIError`, stripping `.code` → the classifier's connection-code branch is dead in production, and the §9 test asserted a synthetic shape. **Fix:** **drop** the connection-code branch; connection-only errors KEEP (a small documented §2.4 residual — the dominant outage returns a detectable 429/503 status); §9 tests only code-real shapes.
- **CL4-M1 — release set too wide (Claude) [Medium].** {500, 502} can occur *after* partial generation → maybe-metered. **Fix:** narrow the class-A release set to **{429, 503}** (rate-limited/overloaded, pre-generation); 500/502/504 → class B KEEP; §9 gate aligned.
- **CL4-L1/L2 — `ourSignal.aborted` is necessary (SDK aborts have `.name==='Error'`), and "connection storm" → "HTTP-status storm."** Both folded into §3.1.

**Round-4 verified-closed (carried forward, no v5 change):** B-1 (serve leg), H-2/H-3/H-4 (cancel RPCs — valid Postgres, correct returns/audit), M-1/M-2/M-3 (idempotency-skip, `data[0]`, `fail_job` release SQL). Both reviewers independently confirmed these; Claude found **no class-B/C mis-RELEASE** in the SQL, and the one under-count vector (C4-B1) is in the classifier, now closed.

**Scope note (v5):** no SQL changed. The growth is entirely in making the §3.1 classifier honest about the *three* ways this codebase emits Gemini errors — retry-aggregate, typed dig error, typed transcript error — and narrowing the release set to the two statuses that are provably pre-generation. This is the intrinsic cost of the B-2 "classify" decision: a classifier is only as correct as the signals the code actually produces.

---

## 16. v6 Change Log (round-5 review responses)

Round-5 dual review (`docs/reviews/reservation-release-spec-v5-{codex,claude}.md`) returned **NOT CONVERGED** — but both reviewers converged on **one root cause** with **one fix**, and Claude's review verified *every other* round-4 fix and all SQL as genuinely closed. The narrowing reached a single point:

- **B5-1 / R5-B1 — the `maybeMetered` flag was scoped per-inner-retry-loop and missed metering that happened in an *earlier successful call/attempt* (Claude B5-1 [Blocking, LIVE] + Codex R5-B1 [Blocking, gated-safe]).** A successful Gemini call **returns — it never throws**, so no error-carried flag can capture it. Concretely: `generateSummary`'s outer `MAX_SUMMARY_ATTEMPTS=4` quality loop can meter on attempt `i=0` (returns an imperfect summary) then throw a 503 on `i=1` → the 503 carried `maybeMetered=false` → mis-RELEASE of a metered generation (B5-1, live). The cross-call transcribe→summary sibling (R5-B1) is the same shape, gated-safe today by the fail-closed transcribe flag (M5-1). **Fix:** replace the per-loop `maybeMetered` with a **job-scoped positive `billing.metered` latch** — a mutable flag the runner creates and threads through the handler/core/gemini functions, set `true` the instant *any* billable Gemini call returns a response body. The release decision becomes `classify(err)==='release' && !billing.metered`. Job is the maximal scope for a reservation, so this is terminal-correct: it subsumes the inner-loop, outer-loop, and cross-call cases in one signal (§3.1, §5, behaviors 3e/3e2/3e3, §9).
- **L5-1 / R5-H1 — behavior 17 still listed `connection` as a serve class-A RELEASE trigger (Claude L5-1 [Low] / Codex R5-H1 [High]).** Stale contradiction with §3.1's dropped connection branch (CL4-H2) → a possible serve under-count if implemented literally. **Fix:** removed `connection` from behavior 17; serve release is caps-`NonRetryableError`/`{429,503}`-only with `billing.metered=false`.
- **L5-2 — "no prior metered attempt" wording read as retry-scoped.** Restated as the job-scoped latch everywhere (§3.1 table, behaviors 2b/2c, §5).

**Round-5 verified-closed (carried forward, no v6 change) — Claude's independent grounding against the vendored SDK:** CL4-H1 (transcript typed-cause — the fix is adequate; `geminiErr` is the pre-send `NonRetryableError` with the flag off), CL4-L1 (`ourSignal.aborted` is the *only* discriminator — SDK aborts have `.name==='Error'`), CL4-H2 (connection errors surface as bare `GoogleGenerativeAIError`, no `.status`/`.code` → KEEP), CL4-M1 ({429,503} excludes 500/502/504 everywhere), C4-H1 (typed dig error shape correct; dig has no outer loop). **All SQL bodies** (`fail_job`, cancel RPCs, `settle_serve_model`, `ledger_audit`) re-confirmed unchanged and closed.

**Scope note (v6):** no SQL changed; the situational classifier logic didn't grow — it *shrank*. The fragile per-loop `maybeMetered` (which had to enumerate every retry loop and still missed the outer loop) is replaced by one job-scoped positive latch. Tracking billing *positively as it happens* is simpler and strictly more correct than inferring it from the terminal error — the round-5 lesson.
