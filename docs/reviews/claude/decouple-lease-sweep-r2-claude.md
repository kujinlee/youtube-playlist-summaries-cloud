# decouple-lease-sweep — round 2 — Claude adversarial review

**Date:** 2026-09-18. **Reviewer:** Claude, adversarial mandate. **Branch:** `decouple-lease-sweep`
(HEAD `f37cbe31`, base for this round `120e5b1b`).
**Verdict: NOT CONVERGED on the tree, CONVERGED on the branch's own scope** — 0 Blocking, 1 High
(**pre-existing, explicitly NOT a fold into this branch**), 2 Medium, 4 Low.

**This is the replacement for a round-2 Claude half that died on a server error mid-review.** The
tree it left dirty is dealt with in *What I ran* — final `git status --porcelain` is **empty**.

**Lead with the conclusion on the primary deliverable:** the four-link fix chain is **real and
correctly identified, but it is not two consecutive ROUNDS of fix-induced findings** — round 1 could
not have findings induced by a previous round's fix, because there was no previous round. The
arming condition in `docs/dev-process.md` is **not met**. My recommendation is **(d) file as
follow-up, ship as-is**, with a named falsifier that fires the architecture review if round 3
produces another fix-induced finding in this sequence. The concrete redesign the brief proposed —
moving `sweepExpired()` into `runWorkerLoop` **in the same order** — **does not** make findings 2, 3
or 4 impossible by construction; it relocates them. A different pair of changes would, and I name
them. Evidence for all of this in `## THRASHING ASSESSMENT`.

---

## What I read

`lib/job-queue/worker-runner.ts` (whole file), `worker/main.ts` (whole file),
`tests/lib/lease-sweep-cadence.test.ts` (whole file), `tests/integration/worker-main.test.ts`,
`tests/integration/job-queue-runner.test.ts`, `tests/integration/worker-runner-runtime.test.ts`,
`tests/lib/blob-addressing-caller-contract.test.ts`, `lib/job-queue/dispatch.ts`,
`lib/job-queue/summary-handler.ts` + `dig-handler.ts` (abort sites only), `lib/gemini-failure.ts`,
`supabase/migrations/0008_jobs_queue.sql` (`claim_next_job`, `fail_job`, `sweep_expired_leases`),
`supabase/migrations/0009_*.sql` (`sweep_expired_leases` replacement), `fly.toml`, `jest.config.ts`,
`package.json`, `.github/workflows/ci.yml` (test step), `docs/dashboard-entries.md` (the new block),
`docs/roadmap-to-launch.md` (the changed line), `docs/dev-process.md` (Phase 6 arming condition),
`docs/review-method.md` (`:127-140` Q5, `:171-232` the stop condition, `:453-490` thrashing vs prose
floor), and all five prior review halves on this branch.

## What I ran

| Command | Result |
|---|---|
| `npx jest tests/lib/lease-sweep-cadence.test.ts` | **22 passed / 22** |
| `npx tsc --noEmit` | **rc=0** |
| 5 mutations on `lib/job-queue/worker-runner.ts` | table under *Audit of the r2 tests* |
| `git status --porcelain` (final) | **EMPTY** — stated again at the end of this file |

**On the dirty tree the previous attempt left.** I hit the same hazard and I am reporting it rather
than hiding it. My mutation battery was written as one script running five mutations back to back;
the fifth (**inverted guard**) made three tests leak a non-terminating `runWorkerLoop`, jest printed
*"Jest did not exit one second after the test run has completed"*, my 10-minute tool timeout killed
the script **before its `git checkout --` ran**, and `lib/job-queue/worker-runner.ts` was left
mutated. I found it with `git status --porcelain`, diffed it to confirm it was my own mutation and
nothing else, and reverted. **Every subsequent mutation was run one at a time with the revert in the
same invocation.** That leak is itself a finding — **L2** below.

---

## Blocking

**None.**

---

## High

### H1 — `fly.toml` states a drain contract the code does not implement, and the gap is the *same defect class the r2 fix just closed, with a window four orders of magnitude larger*

⚠ **PRE-EXISTING. NOT introduced by this branch, and I am NOT asking for it to be folded in.**
Disposition: `docs/backlog.md` + roadmap in the same turn. I grade it High because of what it *is*,
not because of what this branch owes. **It is in this document because the brief scopes "current
`lib/job-queue/worker-runner.ts` + `worker/main.ts`", and because it decides whether the r2 finding
was worth three guards** — see the THRASHING section.

`fly.toml:45-46`:

```
# Graceful drain: worker traps SIGTERM (worker/main.ts) → stops claiming, finishes the in-flight
# job, exits. Give it time before SIGKILL so a deploy/rollout doesn't strand a reservation
```

It does not finish the in-flight job. `lib/job-queue/worker-runner.ts:91-93` folds the shutdown
signal into the signal the handler receives:

```ts
  const signal = AbortSignal.any(
    [wallClock.signal, leaseLost.signal, opts.shutdownSignal].filter((s): s is AbortSignal => Boolean(s)),
  );
```

So SIGTERM **aborts** the running handler. `lib/job-queue/summary-handler.ts:170` then throws
(`if (ctx.signal.aborted) throw new DOMException('worker signal aborted before write', 'AbortError')`),
`dig-handler.ts:117` likewise. That lands in `runOnce`'s catch at `:121`:

- `isNonRetryable(e)` walks the cause chain for `NonRetryableError` (`lib/gemini-failure.ts:64-67`).
  An `AbortError` is not one → `retryable: true`.
- `fail_job` (`0008:152-156`): not cancelled, `p_retryable` true, so the branch is
  `elsif v_attempts >= v_max then v_new := 'dead_letter'`.
- Measured by r1 half 3 against live prod: `summary_max_attempts = 1`, and every job ever run
  carries `max_attempts = 1` with `attempts` already incremented to 1 at claim time (`0008:104`).

**⇒ every deploy that interrupts an in-flight summary job dead-letters it.** And
`classifyGeminiFailure(e, signal)` returns `'keep'` the moment `ourSignal.aborted`
(`gemini-failure.ts:77`), so `billableSucceeded: true` — the spend is kept as well.

**Why this is High and not a footnote.** The r2 Codex Medium protects a window the width of one
`sweep_expired_leases` round trip — call it ~50 ms, and only on 1 poll in 30, since the sweep is now
gated to 60 s against a 2 s poll. The window above is **the entire handler duration**, which for a
summary job is minutes, on every deploy, with the identical consequence (`dead_letter`, spend kept).
`fly.toml:49` even buys 120 s of grace for a drain the code does not perform.

**Falsifier:** if the intended semantics really are *abort the handler on SIGTERM* — which
`docs/superpowers/plans/2026-07-07-stage-1e-b-worker-summary-handler.md:382` suggests, since it
specifies exactly this `AbortSignal.any` composition — then the defect is the `fly.toml` sentence and
the missing "a shutdown-aborted attempt must not consume the job's only attempt" rule, not the
signal wiring. Either way something is wrong; I have not decided which end should move, and that is a
design call, not a review call.

---

## Medium

### M1 — The guard narrows the window it was written for and leaves an equal-sized one immediately after it

`lib/job-queue/worker-runner.ts:83-85`:

```ts
  if (opts.shutdownSignal?.aborted) return 'idle';

  const job = await queue.claim(opts.workerId, opts.leaseSeconds ?? DEFAULT_LEASE_SECONDS, opts.videoFilter ?? null);
```

SIGTERM arriving **during `queue.claim` itself** is not covered. The claim lands, `attempts` is
incremented (`0008:104`), the handler is then invoked with an already-aborted `signal`, and the
outcome is the exact path traced in H1 — `dead_letter`, spend kept. **That is the same consequence
the guard exists to prevent.**

**The two windows are the same order of magnitude.** Both are one PostgREST round trip against the
same database. The guard removes the sweep-RPC window; the claim-RPC window remains. Measured
against the loop's own structure: `runWorkerLoop` (`worker/main.ts:138`) checks `!aborted` at the top
of every iteration, and between that check and the new guard the **only** await is the sweep — which
is due on 1 poll in 30. So the guard's entire value is concentrated in that one-in-thirty iteration,
while the unguarded claim await runs on **all thirty**.

**This is pre-existing** (master had `await queue.sweepExpired(); const job = await queue.claim(...)`
with the same claim-time exposure), so it is not a regression and not a fold-blocker. It is filed
because the branch's own commit message presents the guard as closing the race — *"a job the user
asked for, killed by a restart, silently"* — and the sentence remains true after the fix, just less
often.

**And it is not fixable at this layer**, which is the part worth recording. A post-claim
`if (aborted)` check does not help: the damage is done by `claim_next_job` incrementing `attempts`,
and there is no un-claim. Letting the lease expire instead reaches `sweep_expired_leases`
(`0009:68-73`), whose `when j.attempts >= j.max_attempts then 'dead_letter'` branch produces the same
end state. **The complete fix is SQL** — a release path, or not charging an attempt until the handler
actually starts work. Backlog, with H1.

**Falsifier:** a test that aborts from inside `claim` (not `sweepExpired`) and asserts the handler is
never invoked would fail today.

### M2 — `RunnerOpts.sweepPolicy`'s load-bearing claim is measurably false, and it is the stated obstacle to the redesign

`lib/job-queue/worker-runner.ts:29-33`:

```ts
  /** Cadence for the pre-claim lease sweep. DEFAULTS TO ALWAYS-SWEEP, and that default is
   *  load-bearing: every other caller (both integration suites, and anything added later)
   *  depends on runOnce reclaiming expired leases for it. …
```

**No caller depends on that.** I enumerated every `runOnce` call site by grep and opened each:

| Call site | Queue | Depends on `runOnce` sweeping? |
|---|---|---|
| `worker/main.ts:140` | live `SupabaseJobQueue` | **yes** — supplies its own gate |
| `tests/integration/job-queue-runner.test.ts:32, :41, :61` | live `SupabaseJobQueue` | **no** — each enqueues a **fresh `queued` job** or asserts `'idle'` on an empty scoped queue. The file contains no reference to a sweep, a lease expiry, or `leaseSeconds` |
| `tests/integration/worker-runner-runtime.test.ts` (11 call sites, `:51`–`:254`) | **fully mocked** `makeQueue` at `:23-35` — `claim: jest.fn(async () => job)` returns the job unconditionally, `sweepExpired: jest.fn(async () => 0)` is a stub that is never asserted | **no** |
| `tests/lib/blob-addressing-caller-contract.test.ts:126, :150, :179` | mocked queue, `sweepExpired` stub at `:87`, never asserted | **no** |
| `tests/lib/lease-sweep-cadence.test.ts` (10 call sites) | mocked | **no** (it asserts the policy, not reclamation) |

The only genuine reclamation in the integration suites is `reservation-release.test.ts:515` and
`:648`, which call `adminClient().rpc('sweep_expired_leases')` **directly** — not through `runOnce`.

The `?? true` default is still worth keeping (fail toward sweeping), but the **reason** written next
to it is wrong, and it is the reason a future reader will cite when declining to move the sweep out
of `runOnce`. Correct the sentence to what is actually true: *"fail-safe default; no current caller
relies on it."*

---

## Low

### L1 — `still claims normally when no shutdown signal is supplied at all` kills nothing that was not already dead

`tests/lib/lease-sweep-cadence.test.ts:291-295`. The commit message claims *"a third case pins that
the guard does not fire when no shutdown signal is supplied."* It does pin it — and so did four
tests that already existed. Measured with the inverted-guard mutation
(`if (!opts.shutdownSignal?.aborted) return 'idle';`), scoped to the two synchronous describes:

```
● runOnce honours the sweep policy › skips the sweep when not due, but still claims          (:184, pre-existing)
● runOnce honours the sweep policy › still claims when the sweep throws …                    (:223, pre-existing)
● the sweep interval … › runOnce actually uses DEFAULT_LEASE_SECONDS …                       (:173, pre-existing)
● runOnce honours the sweep policy › still claims normally when no shutdown signal …         (:291, NEW)
● + the two new shutdown cases
```

Every mutation of the guard's *no-signal* behaviour I could construct (`!aborted`,
`shutdownSignal === undefined || …`) is killed by `:184` alone, which runs with no shutdown signal
and asserts `claim` was called. Not harmful — a cheap named case is fine documentation — but it
should not be listed as new coverage.

### L2 — The reworked test moved its stop condition *behind the guard it is testing*, and a misfiring guard now HANGS jest instead of failing it

`tests/lib/lease-sweep-cadence.test.ts:355-374`. The r2 rework moved the abort from `sweepExpired` to
`claim`:

```ts
      sweepExpired: async () => { sweepAttempts++; throw new Error('transient PostgREST failure'); },
      claim: async () => { claims++; if (claims >= 5) ac.abort(); return null; },
```

The stated reason is sound (aborting mid-sweep trips the new guard and skews the counters). The cost
is not stated: **`claim` is now downstream of the guard, so a guard that wrongly fires means `claim`
is never reached, `ac` never aborts, and `runWorkerLoop` spins forever.** Before the rework this test
aborted from `sweepExpired`, which runs *before* the guard unconditionally — it was the file's only
loop test with a guard-independent stop condition, and that property is now gone. `:312` and `:384`
already aborted from `claim`, so **all three loop tests now share the same failure mode.**

**Measured.** With the inverted guard and no `--forceExit`:

```
    thrown: "Exceeded timeout of 15000 ms for a test.
    thrown: "Exceeded timeout of 5000 ms for a test.
Jest did not exit one second after the test run has completed.
Tests:       9 failed, 13 passed, 22 total
```

…and the process was still alive when I killed it at **150 s**. CI runs `npm test` → `"test": "jest"`
(`package.json:9`, `.github/workflows/ci.yml:91`) with **no `--forceExit`**, so this does not fail the
job, it **stalls** it until the workflow timeout. With `--forceExit` the same mutation resolves in
10 s as a clean timeout failure.

**Cheap fix:** give the loop tests a belt-and-braces bound that does not depend on the code under
test — e.g. a counter in `sweepExpired` that aborts at 50 as a backstop, or `pollMs` plus an
`AbortSignal.timeout`. Not a fold-blocker; it costs a CI stall the day someone breaks the guard.

### L3 — Two throwing-sweep tests still spray a stack trace through the suite output

The r2 diff added `jest.spyOn(console, 'error')` to `:236` and to the new `:253`, but `:206`
(`does NOT acknowledge a sweep that threw`) and `:223` (`still claims when the sweep throws`) still
do not mock it. Confirmed in my green run: the 22-pass output carries a full
`at runOnce (lib/job-queue/worker-runner.ts:49:21)` trace from `:229`. Cosmetic, but it makes a real
failure harder to spot in CI output, and the fix is now inconsistent across four sibling tests.

### L4 — "FOURTH consecutive round whose finding was introduced by the PREVIOUS round's fix" is overstated in the commit message and the dashboard entry

`f37cbe31` subject line and body; `docs/dashboard-entries.md` *"Four rounds, four times."*

There have been **two review rounds**, not four, and **finding 2 was not induced by a previous
round's fix** — it was induced by the branch's own original commit, which is not a round. The chain
that is real is *four fixes, two of which induced the next finding*. Full derivation in the next
section. This matters beyond pedantry: the arming condition in `docs/dev-process.md` is written in
**rounds**, and the commit message states the branch has satisfied it when it has not.

Suggested wording: *"a four-link fix chain across two rounds; two of the four links were fix-induced."*

---

## THRASHING ASSESSMENT

### The chain, with the cause of each link established rather than asserted

| # | Finding | Round | Caused by | Evidence |
|---|---|---|---|---|
| 1 | *(the change itself)* gate the sweep to a 60 s cadence | — | — | `18bbdfb0` |
| 2 | r1 Medium (Codex): a failed sweep must not spend the window | **r1** | **the original change** — before it there was no window to spend | `docs/reviews/codex/decouple-lease-sweep-r1-codex.md` Medium 1 |
| 3 | r1 High (Claude half 2): a failed sweep must not block the claim | **r1** | **the fix for #2**, in severity | measured by half 2: `{"claims":20}` at `2a2df6d6` → `{"claims":0}` at `42e0722c`. Mechanism: once `onSwept()` only fires on success, a permanently-throwing sweep is permanently `due()`, so an *intermittent* claim outage became a *total* one |
| 4 | r2 Medium (Codex): must not claim while shutting down | **r2** | **the fix for #3**, unambiguously | `docs/reviews/codex/decouple-lease-sweep-r2-codex.md`: *"before this fix, the sweep rejection escaped to `runWorkerLoop`'s catch, then `sleep(..., abortedSignal)` resolved immediately and the loop exited without claiming"* — verified by reading `worker/main.ts:145-151` and `sleep`'s `if (signal.aborted) return resolve()` at `:117` |

⚠ **#3's underlying bug was PRE-EXISTING**, and both of the other r1 Claude halves said so:
`decouple-lease-sweep-r1-claude.md:70` — *"This is not a regression — the unconditional
`await queue.sweepExpired()` on master did exactly [this]"*; half 3 at `:98` initially graded it *not
a finding* for the same reason. Only its **totality** was fix-induced. So even link 3 is a half-link.

### (a) Genuine thrashing, or a small function with many real edge cases?

**The case FOR thrashing.** Every one of findings 2, 3 and 4 is a *sequencing* defect between two
operations — a sweep and a claim — that have **no** data dependency, no shared failure mode, and no
reason to be ordered. All three live inside the same ~18 lines. Each was fixed by adding a *guard*
rather than by changing the arrangement, and the file now carries three of them
(`onSwept` inside the `try` and after the `await`; a non-rethrowing `catch`; a shutdown re-check) plus
34 lines of comment explaining why each is where it is. `review-method.md:172-176` describes exactly
this: *"a local question can always be answered yes by patching … a wrong shape never fails a round;
it emits a stream of defects that get fixed, and each fix makes the gates greener."* The comment
block at `worker-runner.ts:50-82` is, read coldly, a description of a shape that needs three
load-bearing warnings to stay correct.

**The case AGAINST.** Three things count against, and I find them heavier.

1. **The arming condition is written in ROUNDS and is not met.** `docs/dev-process.md`: *"two
   consecutive rounds whose findings came from the previous round's fix, in one component."*
   `review-method.md:463` says the same. Round 1 **cannot** qualify: there is no previous round.
   Only round 2 qualifies. Count of qualifying rounds: **one, not two.** And CLAUDE.md's *"reaching
   four rounds OBLIGES ASKING, and does not fire"* — we are at round **two**.
2. **Each finding was real, each fix was correct, and the severity DROPPED.** `review-method.md:463`
   makes *"severity stays put"* part of the thrashing tell. It did not: High (total claim outage,
   measured 40 sweeps / 0 claims) → Medium (a ~50 ms race on a job in a shutdown window). That is the
   profile of a sequence being driven to correctness, not of a design fighting itself.
3. **The single test — *can a redesign remove it?* (`review-method.md:200`) — answers NO for the
   redesign that was proposed, and only partly YES for better ones.** Worked below. That test, not
   the symptom list, is what `review-method.md:196` says decides it, on the evidence of a measured
   false escalation on 2026-08-14.

**Does "each fix was individually correct and each finding real" support or undermine the thrashing
reading?** It is **neutral on its own and slightly undermining here**, and the distinction is the one
`review-method.md:191-194` draws. *Mechanism* defects are also individually real and individually
fixable — that is precisely why the heuristic exists. What separates them is whether the fixes are
answering *"the rule cannot be satisfied"* or *"the rule doesn't say what happens in case X."* All
three of findings 2–4 are the second shape: **"what happens when the sweep throws?", "what happens
when the sweep blocks?", "what happens when SIGTERM lands mid-sweep?"** Those are branches of a
concurrent protocol that the design *governs* but does not *own* — abort timing and RPC failure are
properties of the runtime, not of the arrangement. `review-method.md:219-226`: *"If the branches live
in code the design merely governs … then no redesign can delete them. It can only fail to mention
them, which is the defect you already have."*

**Conclusion (a): a small function with real edge cases, converging — with one honest caveat.** The
caveat is that the *reason* the edge cases exist is that two unrelated operations were put in
sequence, and a shape that did not sequence them would have had fewer branches to enumerate. That is
a real cost; it is not a mechanism defect.

### (b) Evaluating the proposed redesign concretely: move `sweepExpired()` into `runWorkerLoop`

The shape as briefed — same order, sweep first, claim second, just hoisted one level:

```ts
  while (!deps.shutdownSignal.aborted) {
    if (sweepPolicy.due()) {
      try { await deps.queue.sweepExpired(); sweepPolicy.onSwept(); }
      catch (e) { console.error(…); }
    }
    const r = await runOnce(deps.queue, deps.handler, { … });   // claim + handle
  }
```

**Finding 2 (a failed sweep must not spend the window): NOT dissolved.** `onSwept()` after the
`await` inside the `try` is a *discipline*, not a structure, and relocating the three lines preserves
it verbatim. The tempting `finally` is exactly as available in `runWorkerLoop` as it is in `runOnce`.
The test at `:206` would still be the only thing standing between the code and the regression.

**Finding 3 (a failed sweep must not block the claim): NOT dissolved — it depends entirely on the
`catch` surviving the move.** With the inner `catch` above, yes, the claim is reached. Drop it and
`runWorkerLoop`'s outer `catch` (`worker/main.ts:146-151`) swallows the rejection, `continue`s the
loop, and skips that iteration's claim. And because a permanently-throwing sweep is permanently
`due()` — the mechanism that made #3 *total* — every iteration would throw and the claim would again
be reached **never**. **The identical outage, at the new location.** So the guard is still
load-bearing after the move; only its address changed.

**Finding 4 (must not claim while shutting down): NOT dissolved.** A shutdown arriving during
`await deps.queue.sweepExpired()` sits between the `while (!aborted)` check and `runOnce`, exactly as
before. You still need `if (deps.shutdownSignal.aborted) break;` between the sweep and the claim.

**⇒ The briefed redesign converts three guards in one function into three guards in another. Its
answer to "can a redesign remove it?" is NO for all three.** It does buy one real thing: `runOnce`
becomes a pure claim-and-run with no sweep concern at all, and the `SweepPolicy` field leaves
`RunnerOpts`. That is a legibility win, not a correctness one, and **it is not what the brief asked
me to establish.**

**Every `runOnce` caller, by grep, and what each would need.** Enumerated by
`grep -rn "runOnce" --include=*.ts . | grep -v node_modules`:

| Caller | Call sites | What the move costs it |
|---|---|---|
| `worker/main.ts:140` | 1 | gains the sweep block; `sweepGate` dep stays |
| `tests/integration/job-queue-runner.test.ts` | `:32 :41 :61` | **nothing** — fresh `queued` jobs, no sweep reference anywhere in the file |
| `tests/integration/worker-runner-runtime.test.ts` | `:51 :68 :81 :97 :119 :145 :164 :184 :192 :211 :254` | **nothing** — fully mocked `makeQueue` (`:23-35`); its `sweepExpired` stub becomes dead and can be deleted or left |
| `tests/lib/blob-addressing-caller-contract.test.ts` | `:126 :150 :179` | **nothing** — mocked queue, `sweepExpired` stub at `:87` never asserted |
| `tests/lib/lease-sweep-cadence.test.ts` | `:175 :186 :196 :210 :226 :239 :261 :281 :293 :302` | **the real cost.** The whole `runOnce honours the sweep policy` describe (**9 tests**) must move to the loop boundary. 6 of them are currently 5-line mock assertions; at the loop boundary each needs an `AbortController` stop condition — which is the shape that produced **L2** |

**What breaks: nothing in production, and nothing in any integration suite.** That is the finding
worth carrying out of this section, and it directly refutes the code comment at
`worker-runner.ts:29-33` (**M2**) which asserts the opposite and is the sentence a future reader
would cite to decline the move.

### (c) Is there a better redesign?

Two, and they are orthogonal to each other and to (b):

**C1 — encapsulate the protocol: `SweepPolicy.run(fn)` instead of `due()` + `onSwept()`.**

```ts
  /** Runs `sweep` if due, commits the window only if it RESOLVES, and never rejects. */
  run(sweep: () => Promise<unknown>): Promise<void>;
```

This **does** dissolve finding 2 by construction: commit-on-success is inside the policy, there is no
`onSwept` for a caller to hoist, and `finally` is not reachable from the call site. It also dissolves
the *"a caller who supplied only the first would have a cursor that never advances"* hazard the
existing doc comment at `:10-13` identifies and then solves by convention. Codex's own r1 Medium said
this: *"The current `() => boolean` seam cannot express 'commit after success' cleanly."* **Cost:
small.** ~15 lines moved; `makeSweepGate`'s tests change shape but not count.

**C2 — order the loop claim-first, sweep-after.** A throwing sweep cannot block a claim that already
happened, and a shutdown during the sweep is caught by the next `while (!aborted)` — so findings 3
and 4 are dissolved **by construction**, not by guards. **But it has a real regression I could not
argue away:** a busy worker that always gets a job would only sweep *between* jobs, so reclamation
latency goes from ≤60 s to ≤(60 s + one job duration), which for a summary job is minutes. The
fire-and-forget variant (`void sweeper.run()` before the claim, never awaited) fixes that and is the
truest "structurally independent" shape — but it needs in-flight suppression to avoid overlapping
sweeps, and an in-flight flag re-opens finding 2's question in a new form. **I do not recommend C2.**

**And the shape that is actually right is neither.** The largest exposure in this file is H1/M1 — an
aborted attempt consuming a job's only `attempts` — and **no arrangement of sweep and claim touches
it.** It is decided by `claim_next_job`'s `attempts = attempts + 1` (`0008:104`) and `fail_job`'s
`elsif v_attempts >= v_max` (`0008:154`). Redesigning `runOnce` to prevent a 50 ms window while a
multi-minute window with the same consequence stays open is the shape of the mistake, not a fix for
it.

### (d) Recommendation — **FILE AS FOLLOW-UP, SHIP AS-IS**

Committing to one, as asked.

1. **Do not convene the architecture review.** The arming condition is not met (one qualifying round,
   not two; round two, not four). The decisive test — *can a redesign remove it?* — is **NO** for the
   briefed redesign and **partial** for the better ones.
2. **Ship this branch.** It is correct as far as I can measure: 22/22 green, `tsc` clean, four
   mutations on the new guard all killed by named cases, no caller regression.
3. **File three follow-ups, in `docs/backlog.md` and the roadmap in the same turn:**
   - **(i)** H1 + M1 — *an aborted attempt must not consume a job's only attempt*; decide whether
     SIGTERM aborts or drains, and fix `fly.toml:45-46` either way. **This is the big one and it is
     bigger than anything found in two rounds of reviewing this function.**
   - **(ii)** C1 — collapse `SweepPolicy` to a single `run(fn)`. Small, and it is the only change of
     the three that removes a finding *by construction*.
   - **(iii)** M2 + L2 — correct the false caller claim; give the loop tests a guard-independent
     stop condition.

**⚠ THE OVERRIDE AND ITS FALSIFIER** (`review-method.md:233-236` requires this, and warns that an
override without one *"is the round-8 failure wearing a better argument"*):

> This assessment declines the architecture review on the ground that findings 2–4 are
> **branch-coverage** defects in a concurrent protocol, not **mechanism** defects.
> **It FIRES to REDESIGN if round 3 produces any finding in `runOnce`'s sweep/claim sequence that was
> introduced by the r2 shutdown-guard fix.** That would be three fix-induced links in a row, in one
> ~18-line component, and at that point the shape is the defect regardless of what the round counter
> says.

---

## What I checked and found clean

**Stated explicitly, per the brief: I found nothing wrong in any of the following.**

**The guard is in the right place, and I tried to move it.** Four mutations, each run and reverted
individually:

| # | Mutation | Killed by | Verdict |
|---|---|---|---|
| M1 | delete `if (opts.shutdownSignal?.aborted) return 'idle';` | 2 tests (`:253`, `:274`) | **killed** |
| M2 | guard moved **inside the `catch`** (throw path only) | 1 test — `does not claim … during a SUCCESSFUL sweep either` (`:274`) | **killed, and by exactly the class test.** The commit message's claim that the second case earns its keep is **verified, not taken** |
| M3 | guard moved **above** the sweep block | 2 tests (`:253`, `:274`) | **killed** |
| M4 | `return 'lost'` instead of `'idle'` | 2 tests (`:253`, `:274`) | **killed** |

**Should the sweep also be skipped when already aborted?** No, and the current choice is right.
`:285` asserts `sweepExpired` was still called, with the comment *"the sweep itself is still worth
doing"*. Reclaiming another machine's stranded leases on the way out is useful work, it is one RPC,
and it cannot harm a job this worker owns (`sweep_expired_leases` only touches rows whose
`lease_expires_at < now()`). M3 above confirms moving the guard earlier is caught.

**Is `'idle'` the right union member?** Yes. `runWorkerLoop:145` does `if (r === 'idle') await
sleep(pollMs, deps.shutdownSignal)`, and `sleep:117` returns immediately on an already-aborted
signal, so the loop re-tests `!aborted` and exits with no added latency. The alternatives are worse:
`'lost'` and `'failed'` both assert something about a job that was never claimed. No caller
distinguishes `'idle'` from anything else except that one line.

**Does any caller depend on `runOnce` claiming under an aborted signal?** **No.** `runWorkerLoop` is
the only caller that passes `shutdownSignal` at all (grep over the repo returns
`worker/main.ts:142`, and test call sites in `lease-sweep-cadence.test.ts` only). Both
`tests/integration/worker-main.test.ts` tests abort from a point *after* the claim — the handler
(`:39`) and `claim` itself (`:65`) — so neither reaches the new guard's branch.

**The reworked test's counters are deterministic.** `:355-374`: the sweep throws every time, so
`onSwept` never fires, `lastSweptAt` stays `-Infinity`, `due()` is true forever — 5 iterations,
`sweepAttempts` incremented before `claims` in each, abort on claim #5, loop exits. `5 === 5`. The
pair of assertions still does what its comment says: `sweepAttempts` climbing proves the window was
not spent (r1 Medium), `claims === sweepAttempts` proves intake was not blocked (r1 High). My only
objection to it is L2, which is about how it fails, not whether it passes.

**No tautology among the three new tests.** Each asserts `claim` **not** called against a mock that
would have recorded the call; M1 turns two of them red. `:291` is redundant (L1) but not tautological
— it does assert a real thing.

**Dashboard block and commit message, line by line.** *"Suite: 2,838 → 2,841"* — 3 new tests, matches
the `roadmap-to-launch.md` edit `2838 → 2841` and the file's own 22 passing. *"`claim_next_job`
increments `attempts` at claim time (`0008:104`)"` — **verified in the migration**, the line reads
`attempts = attempts + 1, updated_at = now()`. *"with `summary_max_attempts = 1` that consumes the
job's only attempt"* — consistent with r1 half 3's live measurement; I did not re-query prod. *"Codex
… named the killed mutation for each of the 7 tests added in that fold"* — **true**, its r2 doc lists
exactly 7 bullets. *"The new guard turned an existing test red, and the test was right … the counters
read 5/4"* — mechanism confirmed by reading the pre-rework stub in the diff (`if (sweepAttempts >= 5)
ac.abort();` *before* `throw`): the 5th sweep aborted, the guard then correctly skipped that
iteration's claim, leaving 4. **The only overstatement I found is L4** (the "four rounds" framing).

**The dashboard entry's plain-language half is accurate and does not overclaim.** *"The worker now
checks whether it is shutting down immediately before picking up work"* is literally what the code
does; it does not claim the race is closed, which matters given M1.

**The gates.** `npx tsc --noEmit` rc=0. The new `docs/reviews/codex/…verdict.json` is present so
`check-review-rounds.py` can see the Codex half. I did **not** run `check-docs.py`,
`check-dashboard-entry.py` or the full 2,841-test suite — CI runs all three, and r1 half 2 already
recorded them green on the preceding commit.

---

## Verdict

**NOT CONVERGED on the tree — CONVERGED on this branch's scope.** The distinction is deliberate and
is the one `review-convergence-is-not-the-final-tree-gate` exists for.

- **Nothing here blocks the merge.** H1 and M1 are pre-existing, larger than the branch, and belong
  in the backlog; M2, L1–L4 are a comment correction, a redundant test, a CI-stall hazard, log noise
  and a wording fix.
- **The r2 fix is correct, correctly placed, and correctly tested.** Four mutations killed, the
  class-vs-instance test earns its keep by measurement.
- **Primary deliverable:** **do not convene the architecture review**; ship as-is; file (i), (ii) and
  (iii); record the override with the falsifier quoted above.

**Working tree at the end of this review:** `git status --porcelain` → **empty** (stated per the
brief; the one stranded mutation is described in *What I ran* and was reverted).
