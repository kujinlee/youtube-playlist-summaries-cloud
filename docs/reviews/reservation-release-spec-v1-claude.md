# Adversarial Review — Reservation Release Lifecycle spec (money path)

**Reviewer:** Claude (independent adversarial pass)
**Spec:** `docs/superpowers/specs/2026-07-15-reservation-release-lifecycle-design.md`
**Verdict:** **NOT CONVERGED** — 2 Blocking, 2 High. Must-fix list at the end.

Method: every spec claim cross-checked against the actual SQL in migrations
0008/0009/0010/0011/0012/0014/0018 and the callers `lib/html-doc/serve-doc.ts`,
`lib/html-doc/serve-summary-core.ts`, `app/api/html/[id]/route.ts`,
`lib/job-queue/worker-runner.ts`. Line refs verified against current code (the
spec's own line cites are accurate; deviations noted).

---

## BLOCKING

### B1 — Client-callable `release_serve_model` lets a client un-charge KEPT serves → defeats the per-owner cap AND the global daily fuse (real overspend)

**Where:** spec §6, lines 108 (`grants: authenticated, anon`) and 128 (caller calls
release on the `'reserved'` branch). Verified caller/role:
`app/api/html/[id]/route.ts:42` (`createServerSupabase(cookieStore)` = the user's
**session** client, RLS/`auth.uid()`=user) → `serve-summary-core.ts:42,105` →
`serve-doc.ts:52`. So `reserve_serve_model` / `release_serve_model` are invoked with
session credentials and MUST be granted `authenticated/anon` — which means PostgREST
exposes `/rest/v1/rpc/release_serve_model` to any logged-in user.

**Why it breaks:** The original serve design (`0012` header comment: *"charge-per-attempt
+ K-attempt bound + **no release RPC**"*) made "no release" the deliberate abuse bound.
`release_serve_model` credits back **all three** counters (`serve_model_charge.reserved_cents`,
`serve_owner_budget.spent_cents`, `spend_ledger.reserved_cents`) whenever the marker
`>= magazine_est_cents`. It has **no way to verify the materialization actually failed** —
the trusted caller only calls it on `catch`, but a malicious client can call the RPC
directly at will.

**Failure scenario (inputs → wrong ledger state):**
1. Attacker (authenticated) legitimately views one of their promoted docs. serve-doc
   reserves (owner_budget +6, spend_ledger +6, marker +6), `generateMagazineModel`
   **succeeds**, artifact written, KEEP. Real ~6¢ spent; fuse correctly at +6.
2. Attacker POSTs directly to `rpc/release_serve_model` with the same
   `p_playlist_id/p_video_id`. Marker 6→0, `serve_owner_budget` 6→0, `spend_ledger` 6→0.
   Real 6¢ was spent; **fuse now shows 0**.
3. Repeat across every promoted doc the attacker owns (and across sybil owners). Each doc
   = one real generation (~6¢) whose charge is erased. `per_owner_serve_daily_cents`
   (60¢ = 10 serves/day) and the global `daily_cap_cents` ($5) are both bypassed —
   real serve spend is unbounded by either cap.

This directly violates the spec's own central invariant (§3): *"Fail-safe: over-counts
real spend, **never under-counts**."* The release, as specified, under-counts on demand.
It is strictly worse than the status quo (no release RPC = caps hold).

**Suggested fix (pick one, spec must address):**
- Make serve materialization server-mediated: have the Next handler perform the
  reserve→generate→release sequence via a **`service_role`** client and grant
  `reserve_serve_model`/`release_serve_model` to `service_role` **only** (not
  anon/authenticated). This closes the hole with a one-line grant change but requires
  serve-doc to use a service client for these two RPCs. OR
- Bind release to unforgeable proof-of-in-flight: `release_serve_model` credits only when
  the caller's lease is still live AND is the current lease holder (return a lease token
  from `reserve_serve_model`, require it on release, and expire the lease on release so a
  reserve→release loop can't churn). A bare `(playlist,video)` release is insufficient.
- At minimum: the spec must explicitly analyze and rule out the "un-charge a kept serve"
  vector before this is mergeable. Currently §6 grants anon/authenticated with no
  discussion of it.

---

### B2 — `request_cancel_job` release on an ACTIVE job → mis-release / double-release

**Where:** spec §5 table row "`cancelled` while `queued`" + prose: *"`request_cancel_job`
releases **unconditionally** on a successful `queued → cancelled` flip"* (lines 81, 92).
Actual function `0010_cancel_job_rowcount.sql:7-20`:
```sql
update jobs
   set cancel_requested = true,
       status = case when status = 'queued' then 'cancelled' else status end, ...
 where id = p_job_id and owner_id = auth.uid()
   and status in ('queued','active');
get diagnostics n = row_count;   -- returns 1 for BOTH queued→cancelled AND active(flag-set, status unchanged)
```

**The bug:** the function matches **active** jobs too (`status in ('queued','active')`) and
for an active job sets `cancel_requested=true` **without changing status**. It returns
`n=1` in that case. The spec's "unconditional on a … flip" is contradictory: the referenced
function's rowcount does **not** distinguish "flipped queued→cancelled" from "flagged an
active job." An implementation that gates the release on `n>0` (or "unconditionally on
match") releases in the wrong cases.

**Failure scenario A (under-count → overspend):** Job is `active`, running, reservation
150¢ held. Owner calls `request_cancel_job`. Row matches (active), `cancel_requested=true`,
status stays `active`, `n=1`. If release fires on `n=1` → `spend_ledger −=150`, `jobs.reserved_cents→0`.
The handler then **succeeds** → `complete_job` sets `cancelled` (cancel-after-success) →
**KEEP** (no release). Net: artifact kept, reservation already released → 150¢ under-count.

**Failure scenario B (double-release):** Same active job, owner clicks cancel twice.
Each call matches (status still `active`), `n=1` each. Two releases of 150¢ → ledger
double-credited. If the day row also holds other jobs' reservations, `greatest(0,…)` does
**not** save you (it stays positive) → 150¢ overspend admitted.

**Correct behavior** (spec even states it in §3/§5): release only on the genuine
`queued → cancelled` transition; an active cancel must NOT release (the running job will
terminate via `complete_job` KEEP or `fail_job` RELEASE, which handle the reservation).

**Suggested fix:** Gate the release on the actual transition, not the rowcount, and make it
one-shot:
```sql
with flipped as (
  update jobs
     set cancel_requested = true,
         status = case when status = 'queued' then 'cancelled' else status end,
         reserved_cents = case when status = 'queued' then 0 else reserved_cents end,
         updated_at = now()
   where id = p_job_id and owner_id = auth.uid() and status in ('queued','active')
  returning (status = 'cancelled') as did_cancel,
            (created_at at time zone 'utc')::date as d,
            <pre-update reserved_cents>          -- capture OLD value, see B3 note
)
update spend_ledger sl set reserved_cents = greatest(0, sl.reserved_cents - f.amt), updated_at = now()
from flipped f where f.did_cancel and sl.day = f.d;
```
(Note: `RETURNING status` reflects the NEW status = `'cancelled'` for a real flip, but for
an active row the new status is still `'active'`, so `did_cancel` is false — correct. You
still need the OLD `reserved_cents`; see B3.) The behaviors table (§7) also has **no row**
for "cancel an ACTIVE job → NO release" — add it (this is the exact case that breaks).

---

## HIGH

### H1 — Reaper release is a multi-row / multi-day set operation the §5 single-row template does not express

**Where:** spec §5 table rows for `sweep_expired_leases` + the §5 release template
(single scalar `j.reserved_cents`, single `where day = (j.created_at …)`). Actual reaper
`0009:63-77` is a **set-based** `update jobs j … from expired e` that terminalizes an
arbitrary set of expired rows in one statement, each row independently going to `queued`
(KEEP), `dead_letter` or `cancelled` (RELEASE), with **different `created_at` days and
different `reserved_cents`**.

**Why it breaks:** You cannot fold the single-row template into a set UPDATE. Two concrete
traps:
1. A single `update spend_ledger where day = X` cannot credit N released rows spanning
   multiple days/amounts.
2. If you try `update jobs … returning j.reserved_cents` to compute the credit, the
   `RETURNING` sees the **post-update** row — if you also set `reserved_cents = 0` in the
   same UPDATE, every returned amount is 0 → **nothing gets released** (silent leak, the
   self-DoS direction). If you *don't* zero, you lose idempotency.

**Failure scenario:** 5 summary jobs (`max_attempts=1`) all lease-expire; reaper dead-letters
all 5. A naïve single-row-template port credits 0 (or only one day's row) → 5×150¢ = 750¢
stays reserved forever until midnight → the exact self-DoS the spec exists to prevent.

**Suggested fix:** Specify the reaper release as an explicit CTE that snapshots the
**pre-update** `reserved_cents` for release-terminal rows, aggregates by
`(created_at at utc)::date`, then decrements each ledger day-row and zeroes the job rows —
e.g. join `expired` back to `jobs` to read old `reserved_cents`, compute per-row
`released_amt = case when new_status in ('dead_letter','cancelled') then old_reserved else 0 end`,
`group by day`, one `update spend_ledger … from agg`. This is materially more complex than
`fail_job`'s single-row path (which can stash the amount in a scalar via the `FOR UPDATE`
select) and must be written out in the spec, with its own concurrency/idempotency argument.

### H2 — Reaper/`fail_job` release of a job that DID persist an artifact (lease-loss race) → under-count

**Where:** spec §3 "kept-artifact rule" keys KEEP/RELEASE on **which function** terminalizes,
asserting `sweep_expired_leases`/`fail_job` ⇒ "handler did not produce an artifact." §8
concurrency only argues "reaper and live worker cannot both release" — it does **not**
address a reaper releasing a job whose artifact already landed.

**Why it breaks:** `persist_summary` (`0009:104`) is a **separate** committed write from
`complete_job`. A handler can commit its artifact, then lose the completion race:
1. Handler writes artifact (`persist_summary` commits, `artifacts.summaryMd.status` set).
2. Lease expires (slow/paused worker); reaper reclaims first (`0009:68` `for update skip
   locked`) → `attempts(1) >= max(1)` → `dead_letter` → **RELEASE** 150¢, zero `reserved_cents`.
3. Worker's `complete_job` runs: `where status='active'` now false → 0 rows → `ok=false` →
   worker-runner returns `'lost'` (`worker-runner.ts:56`). No KEEP.

Net: **artifact kept, reservation released** → violates "released iff no kept artifact" →
150¢ under-count = overspend direction. The heartbeat/abort (`worker-runner.ts:45-49`) shrinks
but does not eliminate the window (the artifact write can commit before the abort propagates).

**Why it's newly introduced:** with today's no-release ledger this race costs nothing (the
reservation just lingers). Adding release **monetizes** it as an under-count. Bounded to
`summary_est_cents` (150¢) per occurrence.

**Suggested fix:** Acknowledge explicitly (like the serve crash residual in §2.3) as a
bounded, rare over-credit; OR gate the reaper/`fail_job` release on the absence of a
persisted artifact (harder — requires the RPC to consult `videos.artifacts`); OR note it
is subsumed by the deferred `actual_cents` settle. It must not be silently assumed away by
"reaper ⇒ no artifact."

---

## MEDIUM

### M1 — The `greatest(0, …)` clamp gives false comfort; it does not protect against B2/H1 under-counts

**Where:** spec §4 "Underflow guard" + §8 "Underflow." The clamp only prevents dropping
below **0**; it does **not** prevent dropping below the *true* value when the day row holds
other jobs' reservations. A double-release (B2-B) or a mis-aggregated reaper release (H1)
on a busy day row lands at a still-positive but too-low number, admitting real overspend,
and the clamp never fires. The spec's "correct idempotency means the clamp never fires" is
true but circular — for the reaper (H1) and cancel (B2) paths, exactly-once is not yet
established, so the clamp is not the safety net the text implies. Fix: rest the safety
argument on the status/transition guards (B2/H1 fixes), and downgrade the clamp's stated
role to pure defense.

### M2 — Serve marker increment must be pinned atomic with the 5a/5b increments

**Where:** spec §6: *"`reserve_serve_model` (the `'reserved'` branch, `0014:87`) additionally
does `reserved_cents = reserved_cents + magazine_est_cents`."* This is one sentence; the
placement is load-bearing. It must execute **after** 5b succeeds and **before** `return`,
inside the same `begin … exception` block, so that a PJ004/PJ005 rollback also unwinds the
marker (else marker desyncs: marker>owner/ledger → later release under-credits owner/ledger;
or marker<owner/ledger → release can't reclaim a real leak). Spec should state: marker `+=`
sits immediately after the 5b `spend_ledger` update, and the release's three-way decrement
mirrors it exactly (all gated by the marker `if found`). Verified the release template
(§6 lines 111-123) already does the three-way `if found` correctly — only the reserve-side
placement is underspecified.

---

## LOW

### L1 — §4.2 overstates the `jobs.reserved_cents = 0` zeroing as the idempotency mechanism
The real single-writer guard for `complete_job`/`fail_job` is `where … status='active'`
(a second terminal write finds no row and never reaches the release). The zeroing is
belt-and-suspenders. Behavior #11's framing ("second credits 0 because `reserved_cents`
already 0") could mislead an implementer into relying on the zero instead of the status
guard — which matters because the reaper path (H1) needs the zeroing done *correctly* in a
set context and the cancel path (B2) needs the transition guard, not the zero. Reword to
name the status/transition guard as primary.

### L2 — With default config, the requeue-KEEP behaviors (5, 6) are unreachable → vacuous tests
`summary_max_attempts` and `dig_max_attempts` default to **1** (`0011:31-32`), stamped onto
`jobs.max_attempts` at enqueue (`0011:84`). So `fail_job` always hits
`v_attempts(1) >= v_max(1)` → `dead_letter` (never `queued`), and the reaper always
dead-letters. Behaviors 5 ("retry reuses one reservation") and 6 ("reaper re-queue keeps")
never fire under shipped config. Not a defect, but the §9 test contract must **force
`max_attempts > 1`** for those cases or they pass vacuously and the KEEP-on-requeue path
ships untested.

### L3 — Serve release must retain `owner_id = v_owner` on every decrement (no ownership oracle needed, but the predicate is load-bearing)
`release_serve_model` is safe from cross-tenant release *only* because every WHERE includes
`owner_id = v_owner` (marker + `serve_owner_budget`) so a caller can only touch their own
rows; `spend_ledger` is global (day-only) which is correct. The spec should state this
invariant explicitly so an implementer neither (a) adds a spurious ownership SELECT nor
(b) drops the `owner_id` predicate from `serve_owner_budget` (which would let one owner
decrement another's budget). Low because the §6 template already includes `owner_id`.

---

## Verified-correct (no finding) — for the convergence trail
- **Day-correctness of the generation reserve/release** (§4.3): `enqueue_job` sets
  `created_at = now()` at INSERT and reserves against `v_day = (now() at utc)::date`; Postgres
  `now()` is transaction-start-stable, so `created_at::date at utc == v_day` always — no
  midnight straddle between reserve site and stamp. Re-queue never rewrites `created_at`, so
  release always credits the reservation's original day. Behavior 10 is sound.
- **Retry never re-reserves** (§1, behavior 5): a retry re-claims the same row via
  `claim_next_job` (`0008:96`, bumps `attempts`); it never re-enters `enqueue_job`. The
  `jobs_idem_active` partial index covers only `queued/active/completed`, so a released
  `failed/dead_letter/cancelled` row is out of the index and a *fresh* enqueue correctly
  makes a new reservation. One `enqueue_job` = one reservation. Confirmed.
- **Cancel-after-success asymmetry is detectable** (§5 note): handler success →
  `queue.complete` → `complete_job` (KEEP); handler throw → `queue.fail` → `fail_job`
  (RELEASE) — routed by outcome in `worker-runner.ts:53-66`. `complete_job` never releases;
  only `fail_job`'s `cancelled` releases. The routing is real. (The residual risk is B2/H2,
  not this note.)
- **Serve try/catch scope**: only the `'reserved'` branch falls through the switch
  (`serve-doc.ts:56-74` returns for every other status), and the materialization to wrap
  is `generateMagazineModel` (81-85) **and** `writeModelEnvelope` (86-92) — both must be
  inside the try, as §6 states. Release is therefore reachable only when this request
  reserved. Correct (the problem is B1's *direct* RPC reachability, not the caller).
- **Worker double-terminal**: `worker-runner.ts` `settled` flag + the DB `status='active'`
  guard make complete/fail mutually exclusive and single-shot per job. `fail_job` returns
  `null` on lost lease (`0008:151`) *before* any release, so a lease-loser never releases.

---

## VERDICT

**NOT CONVERGED.** Must-fix before merge:

1. **B1** — `release_serve_model` granted to anon/authenticated is a client-callable
   un-charge that defeats the per-owner and global caps (real overspend, violates §3's
   "never under-counts"). Make it server-mediated/`service_role`-only, or bind it to an
   unforgeable in-flight lease token.
2. **B2** — `request_cancel_job` release must be gated on the genuine `queued→cancelled`
   transition, not the function's rowcount (which also counts active-job flag-sets) →
   otherwise mis-release (kept-after-success) or double-release on repeated cancel. Add the
   missing "cancel active job → NO release" behavior row.
3. **H1** — Specify the reaper release as a multi-row, multi-day CTE (snapshot pre-update
   `reserved_cents`, aggregate by `created_at` day); the §5 single-row template silently
   leaks in the set context.
4. **H2** — Acknowledge/mitigate the reaper-releases-a-persisted-artifact lease race
   (under-count), currently assumed away by "reaper ⇒ no artifact."

Medium/Low (M1, M2, L1–L3) are dispositions to record, not merge blockers.
