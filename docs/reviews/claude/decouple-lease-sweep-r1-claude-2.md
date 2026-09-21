# decouple-lease-sweep — round 1 — Claude adversarial review (second Claude half)

**Date:** 2026-09-18. **Reviewer:** Claude, adversarial mandate.
**Verdict: FINDINGS** — 1 High, 1 Medium, 5 Low.

## ⚠ FILENAME COLLISION — READ THIS FIRST

I was dispatched to write `docs/reviews/claude/decouple-lease-sweep-r1-claude.md`. **A second Claude
reviewer was dispatched to the same path and wrote there while I was measuring.** I wrote mine, it
was overwritten, and I am **not** taking it back — clobbering a peer's completed review to restore
my own is the exact defect this repo has filed twice (*"a guard's evidence path is a namespace with
no allocator"*). Their file stands untouched at the original path; this is mine, at `-claude-2`.

**The two halves agree on the substance and are worth reading together.** Their M1 is my H1, their
M3 is my M1. **Their M2 — that `performance.now()`, the only clock production uses, is exercised by
zero tests — I did not find, and it is correct.** What this file adds that theirs does not:

- the **measured before/after** for H1 (`{"claims":20}` at `2a2df6d6` → `{"claims":0}` at
  `42e0722c`), which shows the fold *created* the total outage rather than inheriting it;
- their own falsifier request (their `:91-93`, *"a new case must show `claims > 0` while every sweep
  throws"*) **discharged by measurement**: I applied the fix and 13 of 15 tests pass untouched;
- the exact two assertions that must move, named;
- four Lows they did not file, including a stale symbol in the committed dashboard entry.

We disagree on one thing only: **severity of the shared top finding.** They grade it Medium on the
ground that it is not a regression from master. I grade it **High**, because the branch *had* the
graceful-degradation property at `2a2df6d6` and the fold removed it — measured below.

---

## Subject

| Commit | Subject |
|---|---|
| `18bbdfb0` | The lease sweep ran at the claim poll's rate, and bought nothing for it |
| `2a2df6d6` | Dashboard entry for the lease-sweep decoupling |
| `42e0722c` | Fold round 1: the sweep window was spent on intent, not on a sweep that landed |

Base `origin/master` = `72396668`. **The subject moved mid-review**: I started against `2a2df6d6`
and the fold landed while I was measuring. Everything below is stated against **`42e0722c`**, and
every mutation ran against a snapshot I verified byte-identical to `42e0722c` for all three sources.

Two of the three findings I had against `2a2df6d6` were already found by Codex and fixed — the
window spent on a failed attempt, and the `1.5 GB` lower bound not derivable from its own evidence.
I reached both independently before I knew; they are not re-filed, and both fixes are re-verified
under *What I checked and found clean*.

## What I read

`lib/job-queue/worker-runner.ts`, `worker/main.ts`, `tests/lib/lease-sweep-cadence.test.ts`,
`tests/integration/worker-main.test.ts`, `tests/integration/worker-runner-runtime.test.ts`,
`tests/lib/blob-addressing-caller-contract.test.ts`, `lib/storage/supabase/supabase-job-queue.ts`,
`lib/storage/job-queue.ts`, `supabase/migrations/0008_jobs_queue.sql`,
`supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql`, `fly.toml`,
`docs/dashboard-entries.md` (both 2026-09-18 blocks), `docs/roadmap-to-launch.md`.

## What I ran

- `npx jest tests/lib/lease-sweep-cadence.test.ts` — 8/8 at `2a2df6d6`, 15/15 at `42e0722c`.
- `npx tsc --noEmit` — clean.
- `check-test-counts.py` **rc=0** (`2,831 unit / 275 suites`), `check-docs.py` **rc=0**,
  `check-dashboard-entry.py` **rc=0**. *(My first pass read `$?` after a pipe into `tail` and was
  reading `tail`'s status. These are from a re-run that captured the scripts' own exit codes.)*
- `npx jest --config jest.integration.config.ts -t 'survives a throwing claim'` **against the live
  local Supabase stack** — the corrected `expect(sweepCalls).toBe(1)` passes.
- **13 mutations** on the delivered sources, plus 3 probes, all inside a detached `git worktree`
  under my scratch directory, reverted after each measurement and the worktree removed.

---

## Blocking

**None.**

---

## High

### H1 — A broken `sweep_expired_leases` stops the worker claiming *anything*, and the fold turned that from partial to total

`lib/job-queue/worker-runner.ts:49-53`

```ts
  if (opts.sweepPolicy?.due() ?? true) {
    await queue.sweepExpired();
    opts.sweepPolicy?.onSwept();
  }
  const job = await queue.claim(opts.workerId, opts.leaseSeconds ?? 120, opts.videoFilter ?? null);
```

`SupabaseJobQueue.sweepExpired` throws on any PostgREST error
(`lib/storage/supabase/supabase-job-queue.ts:104-107`: `if (error) throw error;`). The sweep sits
**outside** `runOnce`'s `try`, so a throw leaves `runOnce` and `queue.claim` is never reached.

The fold correctly stopped acknowledging a failed sweep, so the policy stays `due()` next poll. The
unstated consequence: the sweep now throws on **every** poll instead of one in thirty.

**Measured, not reasoned.** Probe: `sweepExpired` fails persistently, `claim` is perfectly healthy,
40 polls at `pollMs: 1`.

```
42e0722c (HEAD)          -> {"sweepAttempts":40,"claims":0}
2a2df6d6 (before fold)   -> {"sweepAttempts":1, "claims":20}
```

**At `2a2df6d6` the burned-window bug accidentally kept the worker claiming on 29 of every 30
polls. The fix for Codex's Medium traded a 60s recovery-bound violation for a total claim outage,
and that trade is stated nowhere.** That is why I grade this High rather than Medium: the behaviour
is not a regression from `master`, but it *is* a regression from this branch's own previous commit,
and it was introduced by a fix.

The branch asserts both sides of the contradiction:

- `tests/lib/lease-sweep-cadence.test.ts:126` — `expect(q.claim).toHaveBeenCalledTimes(1); // gating the sweep must NOT gate the poll`
- `tests/lib/lease-sweep-cadence.test.ts:221` — `expect(claims).toBe(0); // the throw precedes the claim, so no poll completed`

**Failure scenario (inputs → wrong outcome).** `sweep_expired_leases` fails while `claim_next_job`
is fine. Causes specific to that one RPC, all with precedent here: a migration `create or replace`s
it with a changed signature (`0009_job_playlist_identity_and_worker_persistence.sql:63` already does
exactly this); a stale PostgREST schema cache after deploy; a dropped or re-granted `execute`
(`0008_jobs_queue.sql:187-188`); the `auth.role() <> 'service_role'` guard at `0008:171` tripping
for that function alone. Result: **the worker claims zero jobs, indefinitely.** Every user press
queues a job nobody picks up. The only symptom is `[worker] loop iteration error (continuing):`
(`worker/main.ts:109`) every 2s — a line whose own comment says the loop is fine.

**Proposed fix.** Catch the sweep; keep the acknowledgement inside the `try` so the r1 Medium
property is preserved:

```ts
  if (opts.sweepPolicy?.due() ?? true) {
    try {
      await queue.sweepExpired();
      opts.sweepPolicy?.onSwept();   // unacknowledged on the throw path: the next poll retries
    } catch (e) {
      // A broken sweep must not gate the CLAIM. Lease reclamation degrades; work keeps flowing.
      console.error('[worker] sweepExpired failed (continuing to claim):', e);
    }
  }
```

**The peer half asks for a falsifier for this fix** (*"the existing retries-the-sweep test must still
show `sweepAttempts > 1`, and a new case must show `claims > 0` while every sweep throws"*).
**Discharged by measurement — I applied the patch and ran the suite: 13 of the 15 tests pass
untouched.** Exactly two need their assertion moved, and the property each exists for survives:

| Test | Line | Change |
|---|---|---|
| `does NOT acknowledge a sweep that threw` | `:141` | drop `rejects.toThrow`; **keep** `expect(p.onSwept).not.toHaveBeenCalled()` — that is the property |
| `retries the sweep on the next poll when it throws…` | `:202` | `expect(claims).toBe(0)` → `expect(claims).toBe(sweepAttempts)` |

The second is the regression guard this finding wants, is strictly stronger than what is there now,
and is exactly the case the peer half asked for. `sweepAttempts > 1` still holds under the patch.

⚠ **`try { … } finally { onSwept(); }` is NOT the fix** — `finally` acknowledges on the throw path
and silently undoes the r1 Medium. I saw that exact edit appear in the working tree mid-review (see
*Repo state* below). The guard holds: it is mutation `N-M13`, killed by `:141`.

---

## Medium

### M1 — `SWEEP_MS` must stay well under the lease, and nothing asserts it

*(Same finding as the peer half's M3. Filed because the evidence differs — I mutated to 30 minutes
rather than 10, and I name the third duplicated literal.)*

`worker/main.ts:35` `const SWEEP_MS = 60_000;`
`lib/job-queue/worker-runner.ts:53` `opts.leaseSeconds ?? 120`
`lib/job-queue/worker-runner.ts:56` `const leaseSeconds = opts.leaseSeconds ?? 120;`

Every safety claim rests on one relationship: the sweep interval is shorter than the lease.
`worker/main.ts:31` — *"Kept well under the 120s lease so an expiry is still reclaimed promptly"*;
`:33` — *"a 120s lease becomes up to ~180s to recovery"*. The relationship is expressed **only in
prose**. The numbers live in different modules, `120` is a bare literal duplicated at two call
sites, and `runWorkerLoop` never learns `leaseSeconds` — it could not check the invariant if it
wanted to.

**Mutation-proven:** `SWEEP_MS = 60_000` → `1_800_000` (30 minutes).

```
=== N-M10 SWEEP_MS 60s -> 30 MINUTES ===
Test Suites: 2 passed, 2 total
Tests:       15 passed, 15 total
```

`tsc --noEmit` clean too. Worst-case crash recovery becomes ~32 minutes against a documented ~180s,
and the suite plus every CI gate reports green. The suite pins *that* the cadence is gated
(`SWEEP_MS = 0` is killed by `tests/lib/lease-sweep-cadence.test.ts:194`); the direction that costs
anything — too slow — is unguarded in full.

`CLAUDE.md` names this shape directly: *"A decision becomes a gate by asserting the world still
matches it."* Right now it is a decision wearing a comment.

**Failure scenario.** Someone raises `SWEEP_MS` to shave the last of the egress — the entry's own
*"Not attempted here"* section invites exactly that reasoning — or shortens the lease to 30s to
detect heartbeat loss faster (`leaseSeconds` is already a per-call `RunnerOpts` field, so this needs
no new plumbing). Either edit silently inverts the invariant; recovery degrades by an unbounded
factor; nothing reports it; the comment still says `~180s`.

**Proposed fix.** Export the lease default from one place and assert the relationship:

```ts
// lib/job-queue/worker-runner.ts — replaces both bare `?? 120` literals
export const DEFAULT_LEASE_SECONDS = 120;
```
```ts
// tests/lib/lease-sweep-cadence.test.ts
test('the sweep interval is well inside the lease it guards — the invariant every bound here rests on', () => {
  expect(SWEEP_MS).toBeLessThanOrEqual(DEFAULT_LEASE_SECONDS * 1000 / 2); // "well under", made falsifiable
});
```

`SWEEP_MS` needs exporting. That is the whole cost, and it gives `~180s` its first falsifier.

---

## Low

### L1 — `runOnce` is documented as never rejecting and now tested as rejecting

`lib/job-queue/worker-runner.ts:108-110`:

```
      // The terminal fail RPC itself threw (e.g. transient DB error). Resolve to 'lost' rather than
      // rejecting out of runOnce — the declared outcome contract must be uniform so the long-lived
      // worker loop (Task 8) never sees an unhandled rejection from runOnce.
```

`tests/lib/lease-sweep-cadence.test.ts:148-150` asserts
`await expect(runOnce(…)).rejects.toThrow('transient PostgREST failure')`. The declared return type
is a five-member string union. The branch is the first thing in the repo to pin rejection as a
*tested* contract and does so without reconciling the comment that says the opposite. A reader who
trusts `:108-110` — it is emphatic and cites a task number — may add a bare `await runOnce(...)`
with no `try`; `tests/lib/blob-addressing-caller-contract.test.ts:150` already contains one. No live
defect today: `runWorkerLoop` is the only production caller and it catches.

**Fix:** H1's patch resolves this by construction — with the sweep caught, `runOnce` genuinely never
rejects and the comment becomes true again. If H1 is declined, amend `:108-110` to name the
exception.

### L2 — `onSwept()` re-samples the clock, so the real period is 60s **plus** the sweep's own latency

`worker/main.ts:67` `onSwept: () => { lastSweptAt = now(); },`

`due()` reads the clock (`:64`), the sweep runs, then `onSwept()` reads it **again**. The window is
measured from completion, so the effective cadence is `SWEEP_MS + latency(sweepExpired)` and the
documented `~180s` silently becomes `180s + latency`. At a healthy ~50ms that is noise; on a link
where the RPC sits near a PostgREST timeout it is not. Arguably this is the right semantics for a
rate limiter — the point is that it is unstated, while the mutation
`onSwept: lastSweptAt = now() - 30_000` **is** killed by the suite, so the tests pin a property
nobody wrote down.

**Fix:** capture the timestamp once in `due()` and pass it to `onSwept(t)`, or add one clause to the
docblock saying the period runs from completion and why.

### L3 — the sweep-retry test is bounded by wall clock where its sibling is bounded by a counter

`tests/lib/lease-sweep-cadence.test.ts:216-221`:

```ts
    const stop = setTimeout(() => ac.abort(), 50);
    …
    expect(sweepAttempts).toBeGreaterThan(1); // NOT stuck at 1 for the whole 60s window
```

Every other cadence assertion here runs on an injected clock — the stated design reason these tests
can live in `tests/lib/` at all (`:17-19`). This one asserts a count produced inside a real 50ms
window. It fails **safe** (a stalled box gives a flaky red, never a false green), so this is hygiene
rather than correctness — but the sibling 25 lines above (`:175-179`) already shows the
deterministic form: abort on a counter inside the stub.

**Fix:** `sweepExpired: async () => { sweepAttempts++; if (sweepAttempts >= 5) ac.abort(); throw … }`
and assert `toBe(5)`. Deterministic, and pins a number rather than an inequality.

### L4 — the committed entry names `RunnerOpts.shouldSweep`, which exists nowhere in the tree

`docs/dashboard-entries.md:9860` — *"Now gated by `RunnerOpts.shouldSweep`…"*
`:9872` — *"⚠ **The cursor advances only when the gate OPENS.**"*
`:9878` — *"The gate is a pure predicate over an injected clock"*

`grep -rn "shouldSweep" --include=*.ts` over the repo returns **zero** matches. The field is
`RunnerOpts.sweepPolicy: SweepPolicy` (`lib/job-queue/worker-runner.ts:33`); the cursor advances in
`onSwept()`, not when the gate opens; and the gate is a two-method object, not a predicate. The
append-only correction block fixes the *substance* (`:9925-9929`) but never retracts the dead symbol,
and it introduces a **third** set of names — `shouldSweep` / `markSweepSucceeded` at `:9927`, the
pair Codex *proposed* — while explaining why they were not used. A reader who greps any of the three
finds nothing. `scripts/check-docs.py` passes, so no gate sees this.

**Fix:** one sentence in the correction block: *"The gated field is `RunnerOpts.sweepPolicy`;
`shouldSweep` above, and `markSweepSucceeded` below, are names that never shipped."*

### L5 — `runWorkerLoop`'s `pollMs` default reaches production on tsc's word alone

`worker/main.ts:96` `const pollMs = deps.pollMs ?? POLL_MS;`

No test asserts the shipped `main()` path gets `POLL_MS`. Both cadence tests inject `pollMs: 1`; the
integration tests that exercise the default never observe it. Mutating the default away survives:

```
=== N-M7 pollMs default dropped (cast) ===  Tests: 15 passed, 15 total
```

**Stated honestly, because it changes the severity:** the *natural* form is caught by the compiler —
`const pollMs = deps.pollMs;` yields two `TS2345` errors at `worker/main.ts:105` and `:110`, since
`sleep(ms: number, …)` rejects `number | undefined`. My mutation needed an explicit `as number` to
survive. So the gap is narrow, but the failure mode if it ever opened is severe in the ironic
direction: `setTimeout(fn, undefined)` fires at ~1ms, turning the worker into a ~1000 req/s
busy-spin against the database — a 2000× increase in exactly the traffic this branch removes.

**Fix:** one assertion in the existing loop test — call `runWorkerLoop` with no `pollMs`, abort
after two claims, assert elapsed ≥ `POLL_MS`. Costs 2s of suite time, or zero with a spy on `sleep`.

---

## What I checked and found clean

**The default is genuinely preserved (brief §1).** `opts.sweepPolicy?.due() ?? true`
(`worker-runner.ts:49`). Every `runOnce` call site outside `runWorkerLoop` passes no policy and is
unchanged: `tests/integration/job-queue-runner.test.ts:32,41,61`,
`tests/integration/worker-runner-runtime.test.ts` (9 sites),
`tests/lib/blob-addressing-caller-contract.test.ts:126,150,179`. **No existing test depends on a
sweep and a claim happening inside the same `runOnce`.** `worker-runner-runtime.test.ts` uses a
fully mocked queue (`:23-34`), so its `leaseSeconds: 2` cases never touch a real sweep. `?? false`
is killed (`N-M16`); removing the gate entirely is killed (`M2`).

**Concurrency (brief §2).** Safe. Each worker holds its own gate, so N workers sweep at a union rate
of N per 60s at independent phases — strictly *more* often than one worker, never less; the worst
case is the single-worker case, bounded at 60s. `sweep_expired_leases` selects
`for update skip locked` (`0008_jobs_queue.sql:174`), so concurrent sweeps do not contend, and it is
idempotent. No window exists in which an expired lease is claimable by nobody: `claim_next_job`
reads only `status='queued'` (`0008:106`), the sweep is what moves `active`→`queued`, and the gate
delays that move without ever preventing it.

**60s against the 120s lease (brief §3).** No production path configures a lease shorter than 60s.
`leaseSeconds` appears outside tests only as the `?? 120` defaults (`worker-runner.ts:53,56`) and as
a pass-through parameter (`lib/storage/job-queue.ts:32-33`,
`lib/storage/supabase/supabase-job-queue.ts:56,67`). No env var, no `fly.toml` knob. The heartbeat
at `leaseSeconds/3` (`worker-runner.ts:80`) is per-job and irrelevant to the idle measurement. The
invariant holds today; that nothing guards it is M1.

**The `pollMs` seam (brief §4).** `main()` (`worker/main.ts:139`) passes neither `pollMs` nor
`sweepGate`, so production gets `POLL_MS = 2000` and `makeSweepGate(SWEEP_MS)`. Nothing else calls
`runWorkerLoop` outside tests. Constructing the gate inside the `while` — the mistake the docblock
at `:90-93` warns about — is killed (`N-M15`).

**The tests falsify (brief §5).** 13 mutations against the delivered sources; **11 killed, 2
survived**, both filed above (M1, L5). Killed, each via the case that names it:

| # | Mutation | Killed by |
|---|---|---|
| M1 | `?? true` → `?? false` | `sweeps by default…` `:157` |
| M2 | gate removed, unconditional sweep | `skips the sweep when not due…` `:121` |
| M4 | cursor advances on every call | `becomes due again once the interval elapses…` `:60` |
| M5 | cursor inits to `now()` not `-Infinity` | `is due on the very first call…` `:38` (+3 more) |
| M6 | `<` → `<=` | `becomes due again…` `:60` |
| M8 | `sweepGate` default dropped | `emits far fewer sweeps than claims…` `:169` |
| M11 | `SWEEP_MS` → `0` | `emits far fewer sweeps than claims…` `:194` |
| N-M13 | acknowledge **before** the await (r1 Medium reintroduced) | `does NOT acknowledge a sweep that threw` `:141` |
| N-M14 | NTP floor removed (`elapsed >= 0 &&` dropped) | `comes due immediately if the clock steps backwards` `:106` |
| N-M15 | gate built inside the `while` | `emits far fewer sweeps than claims…` `:169` |
| N-M16 | `due() ?? false` | `sweeps by default…` `:157` |

**No test here is tautological.** The three asserting only on mocks (`:121`, `:130`, `:157`) assert
the right thing at the right level — the contract *is* "`runOnce` calls `queue.sweepExpired`" — and
`:169` measures the shipped loop end to end, which is what the egress bill responds to. The `:72`
shorter-interval test adds little beyond `:60` but is not redundant (different interval, different
hand-derived count).

⚠ **The one coverage gap in this area I did *not* find, and the peer half did:** the
`performance.now()` default at `worker/main.ts:58-59` is injected away by all six `makeSweepGate`
constructions in the suite, so the only clock production uses is exercised by zero tests. Their M2
is correct and I endorse it.

**The corrected integration assertion (brief §6).** `tests/integration/worker-main.test.ts:83`
`expect(sweepCalls).toBe(1)` is exactly implied and **cannot flake green**. Derivation: iteration 1
sweeps (cursor `-Infinity`) then `claim` throws → `catch` → `sleep(2000)`; iteration 2 is 2s in, not
due, so no sweep; `claim` aborts and returns `null` → `sleep(2000, aborted)` returns at once → loop
exits. Reaching `sweepCalls === 2` needs ≥60s between iterations, and
`tests/integration/worker-main.test.ts:8` sets `jest.setTimeout(20_000)` — the test dies by timeout
at 20s long before 60s elapses, so a slow CI box gives a red, never a wrong pass. **Verified by
running it against the live local stack: 1 passed.**

**The numbers (brief §7).** All surviving arithmetic checks out.

| Claim | Check |
|---|---|
| `~79,800 req/day` | mean of 80,289 / 80,758 / 76,040 / 79,724 / 80,543 / 81,313 = **79,777.8** ✓ |
| `sixty times more often` | 120s ÷ 2s = **60** ✓ |
| `roughly 48% removed` | sweeps are 50% of requests, cut to 1/30 → 50 − 1.67 = **48.3%** ✓ |
| `2.13–2.28 GB/month` | 921 B × {76,040…81,313} × 365.25/12 = **2.13–2.28 GB** ✓ |
| `43–46% of 5 GB` | 2.13/5 = 42.6%, 2.28/5 = 45.6% ✓ |
| `~1.45–1.55 GB (29–31%)` without `__cf_bm` | (921 − 295) B × same = **1.45–1.55 GB** ✓, labelled UNMEASURED ✓ |
| Fly cost unaffected | verified in `fly.toml`: `auto_stop_machines = "suspend"` sits in `[http_service]` with `processes = ["web"]` — the worker group has no idle-stop path ✓ |

The original `1.5–2.2 GB` span I could not derive either; corrected at
`docs/dashboard-entries.md:9917-9923` and `worker/main.ts:22-28`, now with its assumption attached.
The prod-side measurements themselves (the 25/25 split, `auth`/`realtime`/`storage` at zero, the
`free` plan) I **cannot** verify — no prod access from here. Treat them as the author's, not as
confirmed by this half.

**Recovery-bound arithmetic.** `~180s` is time to **requeue** (120s lease + ≤60s window), not to
re-claim: `0009_job_playlist_identity_and_worker_persistence.sql:72-73` sets
`run_after = now() + 10s` on the first crash-reclaim, so re-claim is ~190s. The `~` carries it and
the *delta* the entry claims (≤60s) is exactly right. Not filed.

**Cancellation.** A cancel on a job whose worker crashed also waits for the sweep
(`0009:70` maps `cancel_requested` → `'cancelled'`), so it too is up to 60s slower. The ordinary
cancel path is `ctx.isCancelled()` (`worker-runner.ts:65`) and does not involve the sweep. Same 60s
bound, correctly covered by the stated trade. Not filed.

**Repo gates.** `tsc --noEmit` clean; `check-test-counts.py` rc=0 at `2,831 / 275` with the roadmap
in sync; `check-docs.py` rc=0; `check-dashboard-entry.py` rc=0.

**Anything the change should have done (brief §8).** One omission, filed as a note rather than a
finding because it is a design suggestion: the entry's *"Not attempted here, and why"* block
considers only idle backoff on `claim_next_job`. It does not consider moving the sweep **into the
database** — `pg_cron` running `select sweep_expired_leases()` every 60s costs **zero** egress, and
would remove 100% of the sweep traffic rather than 96.7% while decoupling lease reclamation from
worker liveness entirely (which dissolves H1 as a side effect). It has costs — another scheduled job
to monitor, and the `auth.role() <> 'service_role'` guard at `0008_jobs_queue.sql:171` would need
revisiting for a cron caller. Worth a line either way, since that block presents itself as an
enumeration.

**Nothing else in the repo polls a hot path.** The other intervals are client-side and already
backed off: `lib/html-doc/nav.ts:469-471` (2s → 10s ramp),
`components/cloud/IngestProgressBanner.tsx:8-9` (same shape). The rest is `EventSource`, i.e. push.

---

## Repo state at the end of this review

All mutation work ran inside a detached `git worktree` under my scratch directory, now removed
(`worktree remove --force` + `prune`); the three probe files written there are deleted. **I left the
repo unmodified.**

It was **not** clean while I finished, and the modification was **not mine**:

```diff
 M lib/job-queue/worker-runner.ts
-    await queue.sweepExpired();
-    opts.sweepPolicy?.onSwept();
+    try { await queue.sweepExpired(); } finally { opts.sweepPolicy?.onSwept(); }
```

A concurrent agent was editing the live tree. I did **not** revert it — reverting a peer's in-flight
measurement is the hazard the rule exists to prevent. Flagged because committing it would **silently
undo the r1 Medium fix**: `finally` acknowledges the sweep on the throw path. The guard holds — that
is mutation `N-M13`, killed by `tests/lib/lease-sweep-cadence.test.ts:141`. It was gone by the time
I finished writing.

---

## Verdict: **FINDINGS**

1 High, 1 Medium, 5 Low.

**H1 and M1 are the two that matter, and they share a shape worth naming:** the branch's two
headline promises — *the sweep does not gate the claim*, and *recovery is bounded at ~180s* — are
each asserted in a comment and contradicted by something the code does. H1's fix is four lines and
leaves 13 of 15 tests untouched; M1's is an export and one assertion. Taken with the peer half's M2
(the untested `performance.now()` default), all three fixes are small and belong in one pass.
