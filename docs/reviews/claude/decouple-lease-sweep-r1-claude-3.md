# decouple-lease-sweep - round 1 - Claude adversarial review

**Date:** 2026-09-18. **Reviewer:** Claude, adversarial mandate (third Claude half dispatched to
round 1 — see *Process* at the end).
**Verdict: FINDINGS** — 0 Blocking, 0 High of my own, 1 Medium, 3 Low.

## ⛔ I DID NOT WRITE TO THE PATH I WAS GIVEN, AND THAT IS DELIBERATE

I was instructed to write `docs/reviews/claude/decouple-lease-sweep-r1-claude.md`. **That file
already existed when I looked (10,007 B, 07:24), and a second reviewer's file existed beside it
(`-claude-2.md`, 26,121 B, 07:26).** `-claude-2.md` opens by recording that it was itself written to
`-claude.md`, overwritten by a peer, and moved aside rather than taken back.

Writing there would have been the **third** clobber of one path in twenty minutes — the defect this
repo has filed twice as *"a guard's evidence path is a namespace with no allocator"*. I read both
files in full before deciding, and this one is filed at `-claude-3.md` instead.

⚠ **There is a cost to that and the coordinator must act on it:** `check-review-rounds.py` parses
`<subject>-r<N>-<who>.md` with `who ∈ {codex, claude}` only. Measured:

```
decouple-lease-sweep-r1-claude-2.md -> None      # unparsed, invisible to the guard
decouple-lease-sweep-r1-claude-3.md -> None      # this file: likewise
```

So **only `-claude.md` counts as the Claude half.** Keep the first reviewer's file at that name.

⚠ **And the branch as committed is CI-red on this gate right now.** All three Claude halves are
untracked (`??`); only the Codex half is committed. Simulated against a `git archive HEAD` tree,
i.e. what CI sees:

```
decouple-lease-sweep round 1: only codex — claude neither ran nor recorded a `REVIEW GAP:` line
```

Locally the check says `0 silent gaps` **only because the untracked file is sitting on disk** — the
guard reads the filesystem, not the index. One `git add` of the Claude half fixes it.

---

## What I read

`lib/job-queue/worker-runner.ts` (full), `worker/main.ts` (full),
`tests/lib/lease-sweep-cadence.test.ts` (full), the `tests/integration/worker-main.test.ts` and
`docs/roadmap-to-launch.md` diffs, the full `docs/dashboard-entries.md` diff (both 2026-09-18
entries), `supabase/migrations/0008_jobs_queue.sql:90-190`,
`supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:1-120`, `jest.config.ts`,
`scripts/build-worker.mjs`, `scripts/check-review-rounds.py:200-270`, the Codex half, and both peer
Claude halves.

## What I ran

⚠ **Not in the live repo.** The working tree was being mutated by a concurrent agent *while I was
reading it* — between two of my own tool calls the file changed underneath me:

```
call 1:  M worker/main.ts                 -  elapsed < intervalMs  ->  elapsed <= intervalMs
call 2:  M lib/job-queue/worker-runner.ts -  ?? true               ->  ?? false
```

A `Read` issued between those two calls returned `onSwept: () => { }` — an empty body that is **not**
in `HEAD` (`git show HEAD:worker/main.ts` has `onSwept: () => { lastSweptAt = now(); }`). Had I
graded from that read I would have filed a Blocking that does not exist. **I did not touch the live
tree, and I did not revert anyone's mutation.** Everything below was measured in an isolated
`git archive HEAD` snapshot under my scratch directory.

Control: `npx jest tests/lib/lease-sweep-cadence.test.ts` → **12 passed, 12 total**. Then 8
mutations, each applied to the snapshot, run, and reverted, with the control re-run green at the end:

| # | Mutation | Result |
|---|---|---|
| M1 | gate removed entirely — unconditional `await queue.sweepExpired()` | 3 failed ✅ killed |
| M2 | `?? true` → `?? false` | 1 failed ✅ killed |
| M3 | cursor advances in `due()`, `onSwept()` a no-op | 4 failed ✅ killed |
| M4 | drop the `elapsed >= 0` floor | 1 failed ✅ killed |
| M5 | `onSwept()` hoisted **before** the `await` | 2 failed ✅ killed |
| M6 | initial cursor `-Infinity` → `0` | 3 failed ✅ killed |
| M7 | `elapsed < intervalMs` → `<=` (boundary) | 2 failed ✅ killed |
| M8 | default clock `() => performance.now()` → `Date.now` | **12 passed ⛔ SURVIVED** |

M8 independently reproduces the first peer half's M2 from a different starting point. Every other
property the comments claim is genuinely pinned.

---

## Blocking

**None.**

## High

**None of my own.** I reached the peer halves' claim-starvation finding independently
(`lib/job-queue/worker-runner.ts:49-53` — a throwing `sweepExpired` exits `runOnce` before
`queue.claim` is reached, and `tests/lib/lease-sweep-cadence.test.ts:222` pins `claims === 0`), so it
has now been found three times and needs no fourth write-up.

**One reviewer disagreement is worth recording rather than smoothing over.** I initially graded it
**not a finding** because I compared against `origin/master`, where the sweep is unconditional and a
throw blocks the claim on *every* poll — identical to HEAD. The second peer half graded it **High**
by comparing against the branch's own intermediate commit `2a2df6d6`, where the burned-window bug
incidentally let 29 of every 30 polls through (`{"claims":20}` → `{"claims":0}`).

Both readings are factually right; they measure different baselines. **Against the merge base this
branch changes nothing about that failure domain, so it is not a regression this PR introduces.**
Against the r1 fix it is a real behavioural loss. My own grade is **Medium-as-a-branch-finding /
High-as-a-latent-availability-bug**, and I would fix it in this PR regardless of the label, because
the peer's patch is five lines and its falsifier is already written.

## Medium

### M1 — The `~180s` bound omits the crash-reclaim backoff, and the backoff is **exponential**

`worker/main.ts:31-34`, `docs/dashboard-entries.md` (first 2026-09-18 entry), commit `42e0722c`.

The branch states its accepted cost three times, in three registers:

- `worker/main.ts:32-33` — *"a job stranded by a crashed worker is now **picked up** up to SWEEP_MS
  later than before — a 120s lease becomes up to ~180s **to recovery**"*
- dashboard, user-facing — *"that job is now **rescued** up to a minute later than before. **Recovery
  goes from about two minutes to at most three.**"*
- commit `42e0722c` — *"only crash reclaim moves, from ~122s to at most ~182s"*

`120s + 60s = 180s` is the time to **requeue**, not to run again. The live
`sweep_expired_leases` is 0009's `create or replace`, not 0008's — and 0009 added a backoff that
0008's body explicitly did not have
(`supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:70-73`):

```sql
    run_after = case when j.cancel_requested or j.attempts >= j.max_attempts then j.run_after
                     else now() + make_interval(secs => (10 * power(4, least(greatest(j.attempts - 1, 0), 15)))::bigint) end,
```

`claim_next_job` will not touch the row until `run_after <= now()`
(`supabase/migrations/0008_jobs_queue.sql:106`), and `attempts` was already incremented to ≥1 at
claim time (`0008:104`). So the exponent is **not** always 0:

| crash # | `attempts` | backoff | recovery BEFORE | recovery AFTER |
|---|---|---|---|---|
| 1st | 1 | 10s | ~134s | **~192s** |
| 2nd | 2 | 40s | ~164s | **~222s** |
| 3rd | 3 | 160s | ~284s | **~342s** |

(120s lease + sweep window + backoff + up to one 2s claim poll.)

**Where I part from the second peer half.** It found this, checked the first crash only, and declined
it: *"`run_after = now() + 10s` on the first crash-reclaim, so re-claim is ~190s. The `~` carries it.
Not filed."* At attempt 1 I agree the `~` carries 190 vs 180. **It does not carry 342 vs 180, and the
user-facing sentence is not a `~` — it says "at most three".** That is a stated maximum which the
code does not guarantee, exceeded on the very first crash (3.2 min) and exceeded by 90% on the third
(5.7 min).

This is the *same class* as the r1 Medium this branch was folded to fix — *"the bound this branch
advertised was not one the code guaranteed"* — surviving in the prose after being removed from the
code. It is also the second underivable number the user has been shown in this entry family; the
first (the egress range) was the Codex r1 Low.

**The delta the branch actually claims credit for is correct** (+≤60s in every row above), which is
why this is Medium and not High. The absolute figure is what is wrong.

*Fix:* state requeue and recovery separately, e.g. *"reclaim (requeue) moves ~122s → ~182s; the job
then waits `fail_job`-style backoff — 10s on a first crash, 40s on a second — before a claim poll
picks it up, so first-crash recovery is ~134s → ~192s."* One appended sentence in the dashboard, one
clause in `worker/main.ts:32-33`.

*Falsifier for the fix:* the corrected numbers must be reproducible from `0009:70-73` and
`0008:104-106` by a reader with no other input. The current ones are not.

---

## Low

### L1 — "Three new tests, all watched failing first" — four were added, and the fourth is the one that is not claimed

`docs/dashboard-entries.md` (second 2026-09-18 entry) and commit `42e0722c` both say *"Three new
tests, all watched failing first"*, and the dashboard then says **"Suite for this file: 8 → 12"** in
the same paragraph. 8 → 12 is four.

Measured against the pre-fold commit:

```
$ git show 18bbdfb0:tests/lib/lease-sweep-cadence.test.ts | grep -c "test("   ->  8
$ npx jest tests/lib/lease-sweep-cadence.test.ts (HEAD)                      ->  12
```

The three named are `stays due until a sweep is ACKNOWLEDGED…`, `comes due immediately if the clock
steps backwards`, and `retries the sweep on the next poll when it throws…`. The fourth —
**`does NOT acknowledge a sweep that threw` (`tests/lib/lease-sweep-cadence.test.ts:142`)** — is
unnamed in both documents, so the *"watched failing first"* claim does not cover it.

That matters more than a miscount: `:142` is the `runOnce`-boundary half of the r1 Medium fix, and
it is the case that kills mutation M5 (`onSwept()` hoisted before the `await`) **and** the
`try/finally` variant a concurrent agent was experimenting with in the live tree while I reviewed. It
is arguably the single most load-bearing new test in the branch, and it is the one nobody claimed to
have watched go red.

*Fix:* say four, and name it. (The roadmap's `2827 → 2831` is correct and `check-test-counts.py`
would have caught a wrong total — it is only the narrative count that is off, which is exactly the
kind a script cannot see.)

### L2 — The r1 Low's fix has a tested half that production cannot reach and an untested half that production always uses

The monotonic-clock finding was fixed twice over — `performance.now()` as the default
(`worker/main.ts:59`) and the `elapsed >= 0` floor (`:65`). Measured, the coverage splits exactly the
wrong way:

- **the floor is tested** (`tests/lib/lease-sweep-cadence.test.ts:107`, mutation M4 killed) — but it
  can only fire under a **backwards-stepping** clock, and production's clock is monotonic, so in
  production that branch is unreachable;
- **the default clock is not tested at all** (mutation M8 survived) — and it is the only clock
  production ever constructs, via `makeSweepGate(SWEEP_MS)` at `worker/main.ts:97`.

So the suite's *"comes due immediately if the clock steps backwards"* test proves a property of a
scenario the shipped configuration cannot produce, while the change that makes that scenario
impossible is the one nothing holds in place. This sharpens rather than duplicates the first peer
half's M2 (which grades the survival) — the point here is that the green test **reads as** coverage
of the NTP fix and is not.

Both halves are worth keeping; the fix is the peer's one-line case, which I confirm would kill M8:
build `makeSweepGate(1)` with **no** injected clock and drive due → `onSwept()` → not-due → (after a
real millisecond) → due.

### L3 — `performance.now()` in the bundled worker: checked, clean, but nothing checks it

Brief §4. `scripts/build-worker.mjs` runs esbuild with `platform: 'node', target: 'node22',
format: 'cjs'`; `performance` is a Node global from 16 onward and esbuild neither polyfills nor
rewrites globals, so the bundle is fine. The arrow wrapper `() => performance.now()` rather than a
bare `performance.now` reference is also correct — it avoids any unbound-receiver hazard the previous
`Date.now` default did not have.

Filing as Low only because **no test observes it**: with M8 surviving, `dist/worker.js` could lose
the monotonic clock and both the unit suite and the build would stay green. The L2 fix closes this
too.

---

## What I checked and found clean

**The `SweepPolicy` protocol has no unintended path (brief §1).** `opts.sweepPolicy?.due() ?? true`
(`worker-runner.ts:49`): `undefined` → sweeps; `false` is not nullish so a closed gate is respected;
`onSwept()` is reachable only on the line after a resolved `await`. The only sweep-without-`onSwept`
path is the intended throw. There is no `onSwept`-without-sweep path.

**The predicate is safe at every degenerate input (brief §3).** All of these make `due()` return
**true**, i.e. fail toward sweeping rather than toward silence:

| input | `elapsed` | `!(elapsed >= 0 && elapsed < intervalMs)` |
|---|---|---|
| initial cursor `-Infinity` | `+Infinity` | `true` — due ✅ |
| `elapsed === intervalMs` exactly | `60000` | `true` — due ✅ |
| clock steps back | negative | `true` — due ✅ (floor) |
| `now()` returns `NaN` | `NaN` | `true` — due ✅ (both comparisons false) |
| `now()` returns `-Infinity` (so `-Inf − -Inf`) | `NaN` | `true` — due ✅ |
| `intervalMs <= 0` or `NaN` | any | `true` — degrades to sweep-every-poll, never to never-sweep ✅ |

The `!(a && b)` form is doing real work, not stylistic. Mutation M7 (`<` → `<=`) is killed, so the
boundary is pinned too.

**The `pollMs` seam does not reach production (brief §5).** `main()` calls
`runWorkerLoop({ queue, handler, shutdownSignal, workerId })` (`worker/main.ts:139`) with no
`pollMs`, so `POLL_MS = 2000` stands. The `pollMs: 1` in tests does not mask anything I could find:
25 polls complete in single-digit milliseconds, far inside one 60s window, so `expect(sweeps).toBe(1)`
is structural rather than timing-dependent — and if a box were ever slow enough to elapse 60s, jest's
5s default timeout fires first, giving a red rather than a false green.

**The retry test is not meaningfully flaky (brief §6).** `tests/lib/lease-sweep-cadence.test.ts:216`
allows 50ms for `sweepAttempts > 1`; one iteration is a mock throw plus a 1ms timer, so it needs
roughly 2–3ms. It fails **safe** in any case — a starved event loop gives a flaky red, never a green
over a broken gate. (The second peer half's L3 asks for the deterministic counter form; I agree it is
better hygiene, and I disagree that it is urgent.)

**Which tests survive removing the gate (brief §6, asked explicitly).** Mutation M1 leaves **9 of 12
green**. The three that kill it are `skips the sweep when not due, but still claims` (`:122`),
`performs the sweep when due, and acknowledges it` (`:131`) and `emits far fewer sweeps than claims…`
(`:170`). The six `makeSweepGate` cases all pass — correctly, they test a pure function in isolation
— but it is worth knowing that half the suite says nothing about whether the gate is wired in. The
one test that carries the wiring, and therefore the egress claim, is `:170`.

**No test here is tautological or mock-only in a way that matters.** `sweeps by default when no
policy is supplied` (`:158`) does survive M1, but it is asserting the default contract, not the gate,
so that is the correct outcome rather than a hole.

**The corrected egress arithmetic is right.** I recomputed independently of both peers:
921 B × 76,040/day × 30.44 = 2.13 GB; × 81,313 = 2.28 GB; 42.6–45.6% of 5 GB → *"43–46%"*; the
keep-alive variant at 626 B gives 1.45–1.55 GB and 29–31%. All match. The **48%** removal figure also
checks out: sweeps fall from ~39,900/day to 1,440/day against a measured ~79,800 total, i.e. 48.2%,
and since both RPCs return a 2 B body behind identical headers, request share equals egress share.
⚠ The month length is the 30.44-day mean; a reader recomputing with 30 gets 2.10–2.25 and will think
they have found a discrepancy — one word would fix that (the first peer half raises the same point).

**The test-location claim is accurate.** `jest.config.ts` `testMatch` lists `tests/lib/**`,
`tests/api/**`, `tests/scripts/**`, `tests/smoke.test.ts`, `tests/components/**` — and **not**
`tests/integration/**`. So *"only this location is guarded by the `verify` check in CI"*
(`tests/lib/lease-sweep-cadence.test.ts:18-20`) is true.

**The integration assertion change is sound (original brief §6).** `sweepCalls` `>= 2` → `toBe(1)` is
implied, not brittle: both loop iterations land inside one 60s window, and `jest.setTimeout(20_000)`
makes a legitimate two-window elapse impossible.

**Nothing else in the repo polls a hot path server-side.** The only `setInterval` outside tests in
`lib/`, `app/` and `worker/` is the lease heartbeat at `lib/job-queue/worker-runner.ts:76`, which runs
only while a job is in flight.

---

## Process

**Three Claude halves were dispatched for round 1 of one branch**, at least two of them to the same
filename; the first `-claude.md` was overwritten once before I arrived. Two of the three sit at names
`check-review-rounds.py` cannot parse. Whatever the dispatch bug is, the observable cost here is that
**the guard for "both halves ran" is satisfied by exactly one of three files**, and the repo would be
none the wiser if the wrong one were the one committed.

Separately, a concurrent agent was editing `worker/main.ts` and `lib/job-queue/worker-runner.ts` in
the live tree throughout this review, including a `try { … } finally { onSwept(); }` variant that
would silently undo the r1 Medium fix if committed. **I left every one of those edits alone** and
worked from an isolated snapshot. I made no modification to the repository other than writing this
file.

---

## Verdict: FINDINGS

0 Blocking, 0 High of my own, 1 Medium, 3 Low — plus agreement with the peer halves' claim-starvation
finding and their `SWEEP_MS`-vs-lease finding, and a recorded disagreement on the former's severity
baseline.

**Most important thing here that is not already in the other two halves: M1.** The branch's headline
cost — *"at most three minutes"* — is not a bound the schema supports, because 0009's crash-reclaim
carries the same exponential backoff `fail_job` does. The fix is one sentence, and the reason to
spend it is that this is the third number in this entry family to be published without being
derivable, and the second to be found by a reviewer rather than by the author.
