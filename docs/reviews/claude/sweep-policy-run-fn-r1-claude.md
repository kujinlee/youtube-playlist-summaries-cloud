# `sweep-policy-run-fn` — round 1, Claude half (adversarial)

Backlog #140: collapse `SweepPolicy { due(); onSwept(); }` to a single `run(sweep)`.

## ⚠ The subject moved while I was reading it — this review is pinned to exact bytes

The branch is **entirely uncommitted** (`git log --oneline origin/master..HEAD` is empty; the work
lives in the working tree). The author was applying the Codex half's r1 findings *while this review
was running*: `worker-runner.ts` and `worker/main.ts` were rewritten at `12:33:22`, the test file at
`12:33:41`, and `docs/roadmap-to-launch.md` at `12:34:36` — all after I had taken my first read.

Everything below is measured against these exact files:

```
4cd46366246fe6b64c05512a5ded60c67db471ef  lib/job-queue/worker-runner.ts
11251212eef491255dd4f71850c5c0a2ede08b9c  worker/main.ts
c1e8cd987ffa901546bdd66fd8d853d952d5169f  tests/lib/lease-sweep-cadence.test.ts
```

Snapshot kept at `…/scratchpad/snap/`. If those shas no longer match, re-check my line numbers
before acting on a finding.

**Two Codex r1 findings were already fixed in the tree before I measured**, so I am not re-filing
them: the Blocking (over-strong "unwritable" claim) is now scoped at `worker-runner.ts:20-25` and
`tests/lib/lease-sweep-cadence.test.ts:122-123`; the Low (stale `onSwept()` prose) is fixed at
`worker-runner.ts:91-93` and `worker/main.ts:69-77`. My High 1 says the *scoped* version is still
wrong, for a different and measurable reason.

## What I read and ran

Read in full: `lib/job-queue/worker-runner.ts`, `worker/main.ts`,
`tests/lib/lease-sweep-cadence.test.ts`, the `origin/master` version of `worker-runner.ts`
(for the before/after), the peer half `docs/reviews/codex/sweep-policy-run-fn-r1-codex.md`, the
backlog #140 row and roadmap row diffs, `tests/integration/worker-main.test.ts:50-90`,
`tests/integration/worker-runner-runtime.test.ts`, `tests/integration/job-queue-runner.test.ts`,
`jest.config.ts`, `jest.setup.ts`, `scripts/check-test-counts.py`, `scripts/check-dashboard-entry.py`.

Ran:

| Command | Result |
|---|---|
| `npx jest tests/lib/lease-sweep-cadence.test.ts` | **25 passed / 25** (Codex saw 24 — a case was added since) |
| `npx tsc --noEmit` | **rc=0**, and `--listFiles` confirms it type-checks **80** files under `tests/integration/` |
| full suite `npx jest --ci --json` | **2844 passed / 275 suites** |
| `scripts/check-test-counts.py` | rc=0 (see Low 4 — it was *wrong* at 12:33 and corrected at 12:34:36) |
| `check-docs` / `check-review-rounds` / `check-anchors` / `check-backlog-closure` / `check-dashboard-entry` | all rc=0 (see Low 3 for why the dashboard one is a false green) |
| **12 mutations** of the shipped code, each reverted immediately | 11 killed, **1 survived** |

**Mutation-testing hygiene, as required:** every mutation was applied with `perl -0pi`, measured,
and restored from a `cp` backup in the same shell block. Final state confirmed by sha
(`4cd46366…`, `11251212…`, unchanged) and by `git status --porcelain`, whose full output is:

```
 M docs/backlog.md
 M docs/roadmap-to-launch.md
 M lib/job-queue/worker-runner.ts
 M tests/lib/lease-sweep-cadence.test.ts
 M worker/main.ts
?? docs/reviews/claude/sweep-policy-run-fn-r1-claude.md
?? docs/reviews/codex/sweep-policy-run-fn-r1-codex.md
?? docs/reviews/verdicts/sweep-policy-run-fn-r1-codex.verdict.json
```

Those five `M` entries **are the branch itself** (it is uncommitted), not mutation residue — the two
source shas above prove the sources are byte-identical to my pre-mutation snapshot. The one `??`
I added is this file.

### The mutation table (this is the evidence behind everything below)

| # | Mutation of shipped code | Killed by |
|---|---|---|
| M1 | `runOnce` hides the sweep's rejection: `.run(async () => { try { return await queue.sweepExpired() } catch { return 0 } })` | `does NOT acknowledge a sweep that threw`; `keeps sweeping AND keeps claiming when every sweep throws` |
| M2 | `makeSweepGate` commits in a **`finally`** | `a sweep that THROWS does not spend the window`; `keeps sweeping AND keeps claiming when every sweep throws` |
| M3 | delete `makeSweepGate`'s inner `catch` | `a sweep that THROWS does not spend the window`; `never rejects, whatever the sweep does` |
| **M4** | **delete `ALWAYS_SWEEP`'s inner `catch` (`worker-runner.ts:43-47`)** | **NOTHING — 25/25 still green. SURVIVED.** |
| M5 | default policy becomes a no-op (`?? { async run() {} }`) | `sweeps by default when no policy is supplied`; `the default policy is STATELESS` |
| M6 | remove `runOnce`'s outer `try/catch` | `still claims when the POLICY ITSELF rejects` |
| M7 | give `ALWAYS_SWEEP` a 60s cadence cursor | `the default policy is STATELESS`; `sweeps by default when no policy is supplied` |
| M8 | `makeSweepGate` commits **before** the `await` | `a sweep that THROWS does not spend the window`; `keeps sweeping AND keeps claiming…` |
| M9 | drop the `elapsed >= 0` floor | `sweeps immediately if an INJECTED clock steps backwards` |
| M10 | default clock `performance.now()` → `Date.now()` | `the DEFAULT clock is monotonic…` |
| M11 | remove the `shutdownSignal?.aborted` guard | both shutdown cases (failing sweep **and** successful sweep) |
| M12 | build the gate **inside** the `while` loop | `emits far fewer sweeps than claims over a fast idle run` |

---

## Blocking

**None.** I could not produce an input that makes the shipped wiring
(`runWorkerLoop` → `makeSweepGate` → `runOnce`) behave incorrectly. P1–P5 all hold on the shipped
path, and I killed a mutation for each (M8/M2 → P1, M6/M1 → P2, M11 → P3, M5/M7 → P4, M9/M10 → P5).
I am **extending** rather than refuting Codex's Blocking: its *scenario* is right, its *scope* is
too generous to the branch — see High 1.

## High

### High 1 — ⭐ The `finally` mistake was not eliminated. It MOVED, into shipped code, where it is still caught only by a test. Measured.

`worker/main.ts:106-111`, `lib/job-queue/worker-runner.ts:20-25`, backlog #140's FALSIFIER.

**This is the extension of Codex's Blocking, and it is a stronger claim.** Codex argued the mistake
is still writable inside a *hypothetical custom* policy, and the author's fix scoped the prose to
"unwritable **by callers of a policy**". That scoping is true and, I will argue, close to vacuous —
because the mistake is writable in **`makeSweepGate`, the only policy this repo ships**, and I wrote
it.

M2, applied to `worker/main.ts:106-111`:

```ts
      try {
        await sweep();
      } catch (e) {
        console.error('[worker] sweepExpired failed (continuing to claim):', e);
      } finally {
        lastSweptAt = now();          // ← commits the window on the throw path
      }
```

That is a three-line edit to shipped production code. It reproduces **exactly** the PR #318 r1
Medium — a sweep that threw spends the 60s cadence window — and it is caught by a test
(`a sweep that THROWS does not spend the window`), which is precisely the situation #140 was filed
to end. Before: one site holding the discipline (`runOnce`), guarded by one test. After: one site
holding the discipline (`makeSweepGate.run`), guarded by one test. **Net change to the structural
property: zero.** The refactor relocated the `finally` hazard from `worker-runner.ts` to
`worker/main.ts`; it did not remove it.

Now the part that makes this a High rather than a prose quibble — **the count moved the wrong way.**
On `origin/master`, `SweepPolicy` implementations were *dumb*: `due()` returned a boolean, `onSwept()`
recorded a timestamp, and both the commit-on-success rule *and* the never-rethrow rule lived in
`runOnce`, written once. A new policy implementation could not get either rule wrong, because it did
not hold them. On this branch, **every implementer of `SweepPolicy` must independently re-derive two
non-obvious rules** — "commit only after resolve" and "never reject". The branch already ships two
implementations of the second rule (`worker-runner.ts:43-47` and `worker/main.ts:106-111`, identical
`try/catch`, identical log string) plus a third hand-rolled copy in the test double
(`tests/lib/lease-sweep-cadence.test.ts:206-209`, `try { await sweep(); ran(); } catch {}`). Master
had one copy of each rule. This is the repo's own recorded *a second implementation of one rule
DRIFTS*, created by the change whose stated purpose is to remove a discipline.

And the backlog row's own justification does not survive contact with the code. `worker-runner.ts:24`
says the win is "the one place every caller touches can no longer get it wrong… ONE implementation
to audit instead of a rule at every call site." **There has only ever been one call site.** `grep`
across `lib/ worker/ tests/ app/ components/ scripts/` finds exactly one invocation of the policy —
`worker-runner.ts:103`. "A rule at every call site" describes a population of one.

**Does the backlog FALSIFIER hold?** Quoting it:

> **FALSIFIER:** with `run(fn)` in place, no mutation of the call site can commit the window on a
> throwing sweep — the `try/finally` mutation that `does NOT acknowledge a sweep that threw`
> currently kills should become UNWRITABLE rather than merely caught.

**First clause: holds, narrowly.** I could not write a call-site mutation that commits the window on
a throw — the nearest thing, M1, hides the *rejection* from the policy so the policy commits, and
that is killed by two tests.

**Second clause: FALSE as written, and it is the load-bearing one.** It says the mutation *that this
named test kills* becomes unwritable. Measured: `does NOT acknowledge a sweep that threw`
(`tests/lib/lease-sweep-cadence.test.ts:236-244`) is still alive and still killing a real mutation —
M1. So the test did not become vacuous, which means its mutation did not become unwritable; it became
a *different* mutation. Meanwhile the `try/finally` mutation the clause promises is gone is
reproducible in one shipped function, three lines, as shown above. The tick therefore rests on a
falsifier that is half satisfied by relocation and half not satisfied at all.

**Fix — pick one, they are both honest:**

(a) *Keep the code, correct the claim.* Rewrite `worker-runner.ts:20-25`, the #140 row's DONE note,
and `tests/lib/lease-sweep-cadence.test.ts:118-123` to say what is actually true: *the `finally`
mistake now lives in `makeSweepGate.run` instead of `runOnce`, guarded by
`a sweep that THROWS does not spend the window`; nothing about it became unwritable, and the
interface now obliges every future policy to re-derive both rules.* That is a legibility change with
an honest label, which this repo explicitly allows and which the #140 row itself uses to dismiss the
rejected redesign ("That is legibility, not correctness").

(b) *Make the claim true.* Move the commit-on-success rule out of the implementations and into a
single combinator, so the two rules are written once and `makeSweepGate` cannot hold them wrong:

```ts
/** Wraps a bare "is it due?" cursor into a SweepPolicy. The commit-on-resolve and never-reject
 *  rules are written HERE, once; no implementation can get them wrong because none holds them. */
export function sweepPolicyFrom(cursor: { due(): boolean; commit(): void }): SweepPolicy {
  return { async run(sweep) {
    if (!cursor.due()) return;
    try { await sweep(); cursor.commit(); }
    catch (e) { console.error('[worker] sweepExpired failed (continuing to claim):', e); }
  } };
}
```

`makeSweepGate` then supplies only the clock arithmetic, `ALWAYS_SWEEP` becomes
`sweepPolicyFrom({ due: () => true, commit: () => {} })`, the duplicated `catch` and its duplicated
log string collapse to one, and **M4 (below) stops being writable at all**. ⚠ Note this is
structurally the `due`/`onSwept` pair again — but inverted: it is now an *input* to a single correct
wrapper rather than a contract two parties must jointly honour, which is the part #318 r1 actually
objected to.

I lean (a): the code is fine, and (b) is a second refactor to justify. But (a) must actually be done
— the branch's entire reason to exist is the claim in its comment.

### High 2 — `ALWAYS_SWEEP`'s never-reject clause is guarded by nothing. M4 survived the whole suite.

`lib/job-queue/worker-runner.ts:41-49`.

Deleting the `try/catch` from the fail-safe default —

```ts
export const ALWAYS_SWEEP: SweepPolicy = {
  async run(sweep) {
    await sweep();
  },
};
```

— leaves `npx jest tests/lib/lease-sweep-cadence.test.ts` at **25 passed / 25**. This is the single
surviving mutation of the twelve. The asymmetry is what makes it a finding rather than a nit:
`makeSweepGate` has a dedicated contract case (`never rejects, whatever the sweep does`,
`:124-129`, which kills the same mutation on *that* implementation — M3), and the **default**,
the one every caller that supplies no policy gets, has none.

**Concrete failure scenario.** A future edit tidies away what looks like a redundant catch (and it
*is* behaviourally redundant today — `runOnce`'s outer catch at `:104-109` absorbs the rejection
identically, which is exactly why no test notices). Suite stays green, `tsc` stays clean. Now
`sweep_expired_leases` starts failing in production — the real r1 High scenario, a stale PostgREST
schema cache or a revoked grant. The worker still claims, so intake survives; but the operator's log
line changes from

    [worker] sweepExpired failed (continuing to claim): …

to

    [worker] sweep policy rejected (continuing to claim): …

which is a **false statement**: the policy honoured its contract, the *sweep* failed. The one
diagnostic that distinguishes "the database call is broken" from "somebody shipped a bad policy" now
reports the wrong one, on the exact failure this whole branch was written for, with nothing red.

**Fix** — one case, mirroring `:124-129`:

```ts
// ALWAYS_SWEEP is the FAIL-SAFE default: every caller that supplies no policy gets it. Its
// never-rejects clause is load-bearing and, unlike makeSweepGate's, was covered by nothing —
// deleting its catch left the suite 25/25 green (r1 Claude, High 2).
test('the DEFAULT policy never rejects either, whatever the sweep does', async () => {
  await expect(
    ALWAYS_SWEEP.run(async () => { throw new Error('transient PostgREST failure'); }),
  ).resolves.toBeUndefined();
});
```

(Requires importing `ALWAYS_SWEEP`, which the test file does not yet do.) High 1's option (b) would
make this unnecessary by deleting the second copy instead.

## Medium

### Medium 1 — Two test comments name mutations that cannot be written, on tests that do kill real ones. A reader who checks will conclude the tests are dead.

`tests/lib/lease-sweep-cadence.test.ts:98-99` and `:231-235`.

`:231-235` says of `does NOT acknowledge a sweep that threw`:

> Break this catches: acknowledging the sweep before awaiting it, or a `try { … } finally {
> onSwept() }` that acknowledges anyway. […] ⚠ `finally` is the tempting wrong fix and this case is
> what kills it.

Measured, both halves are wrong for the current subject. There is no `onSwept` and no `try` around a
commit anywhere in `runOnce`, so the named mutation is unwritable *in the code this test exercises*
— and the `finally` mutation that *is* writable (M2, inside `makeSweepGate`) **does not kill this
test**; it kills the two listed against M2 in my table. What this test actually kills is M1, a
genuinely valuable and entirely unmentioned class: *`runOnce` must not neutralise the sweep's
rejection before the policy sees it*.

`:98-99` has the same shape — "advancing the cursor on `due()` instead of on `onSwept()`" — for a
test that in fact kills M2 and M8.

**Why this is Medium and not Low.** This repo's recorded failure mode is *a refactor orphans the
mutation guarding it*: comments bind by text, the next person verifies a "Break this catches" line,
finds the mutation unwritable, and deletes the case as obsolete. That would silently drop the only
coverage of M1 — and M1 is a live defect class, since it is the one way the call site can still
break P1. Same class as this repo's *assert the PROPERTY, not the mechanism*.

**Fix:** restate both in terms of the mutation each was measured to kill. For `:231-235`: *"Break
this catches: `runOnce` swallowing or neutralising `queue.sweepExpired()`'s rejection inside the
closure, so the policy sees a resolved sweep and commits a window nothing reclaimed. Measured r1:
`.run(() => queue.sweepExpired().catch(() => 0))` turns this red."*

### Medium 2 — `worker-runner.ts:177-178` claims an outcome contract `runOnce` does not keep, and the branch's new prose leans on it.

The `catch` at `:176-178` says:

> the declared outcome contract must be uniform so the long-lived worker loop (Task 8) never sees an
> unhandled rejection from `runOnce`.

`queue.claim` at **`worker-runner.ts:121`** sits outside every `try`. A throwing `claim` rejects out
of `runOnce`, so the declared union `'idle'|'done'|'failed'|'cancelled'|'lost'` is not exhaustive and
the loop *does* see rejections — which is why `runWorkerLoop` has its own catch at
`worker/main.ts:151-156`, and why `tests/integration/worker-main.test.ts:57` exists to prove the loop
survives it.

**This is pre-existing, identically present on `origin/master`, and I am not asking this branch to
fix it.** I file it because the branch *adds new prose that rests on it*: `worker-runner.ts:29-32`
argues that `SweepPolicy.run`'s never-rejects clause is load-bearing because "the caller reaches
`queue.claim` immediately afterwards". True — but the reason given at `:177` for why that matters
("runOnce never rejects") is false in general, so a reader reconciling the two gets a wrong model of
the function. **Fix:** one clause at `:177` — *"…uniform for every path below the claim; `queue.claim`
itself can still reject, which is what `runWorkerLoop`'s own catch is for."*

## Low

1. **Duplicated log string, now in two modules.** `worker-runner.ts:46` and `worker/main.ts:110` are
   byte-identical: `'[worker] sweepExpired failed (continuing to claim):'`. Master had one. Nothing
   compares them, and High 2 already shows one of the two is untested. Resolved for free by High 1's
   option (b).
2. **`never rejects, whatever the sweep does` (`:124-129`) does not mock `console.error`.** Every
   other error-path case in the file wraps its call in
   `jest.spyOn(console, 'error').mockImplementation(() => {})`. This one does not, so the suite
   prints a full `transient PostgREST failure` stack (I saw it in the baseline run, reported against
   `worker/main.ts:55`). `jest.setup.ts` is a single `import '@testing-library/jest-dom'`, so it does
   not fail on console output — this is noise, not a failure, but noise that trains a reader to
   ignore a red stack in a green suite. **Fix:** mock it like its neighbours.
3. **`check-dashboard-entry.py` is a FALSE GREEN on this branch right now.** It passes with *"no
   tracked files changed outside the exempt paths"* only because the work is **uncommitted** — the
   script diffs `base...HEAD` (`scripts/check-dashboard-entry.py:1277`) and `HEAD` is still
   `origin/master`. The moment `lib/job-queue/worker-runner.ts`, `worker/main.ts` and
   `tests/lib/lease-sweep-cadence.test.ts` are committed, the gate will demand a
   `docs/dashboard-entries.md` entry or a `NO-ENTRY:` declaration. `grep '#140\|SweepPolicy'` on that
   file returns only the two PR #318 entries (`:9925`, `:9991`) — nothing for this work. **Not a
   defect in the change; a pre-PR obligation that today's green check does not cover.**
4. **The roadmap test count was wrong, and was corrected mid-review.** At `12:33` the diff read
   `2841 → **2843**` while the cadence file gained **three** cases (22 → 25 by `grep -c '^\s*test('`).
   The full suite measures **2844 / 275**. The author corrected the line to `2844` at `12:34:36`, and
   `scripts/check-test-counts.py` is rc=0 as I write. Recorded only because it means the branch spent
   part of its life CI-red on its own gate, and because it is the kind of thing a reviewer reading a
   stale diff would report as a finding when it is already fixed.
5. **`tests/integration/worker-main.test.ts:55`** — *"a throwing sweepExpired/claim (outside runOnce's
   try/catch)"*. `sweepExpired` has not been outside a `try/catch` since PR #318; only `claim` is.
   Harmless, one word, adjacent to code this branch touches.

## What I checked and found clean — explicitly, including where I found nothing

- **P1 (a throwing sweep must not spend the window).** Holds. `worker/main.ts:107-108` assigns
  `lastSweptAt` only after `await sweep()` resolves, inside the `try`. Killed by M8 and M2 via
  `a sweep that THROWS does not spend the window` and `keeps sweeping AND keeps claiming when every
  sweep throws`. Also holds against the new call-site attack M1.
- **P2 (a broken sweep must not block `queue.claim`).** Holds, with two independent layers. Killed by
  M6 via `still claims when the POLICY ITSELF rejects` and by M1 via `keeps sweeping AND keeps
  claiming…`. **Codex's judgement that the outer catch is not redundant is correct and I confirm it:**
  M6 goes red. The *inner* catches are the redundant ones (M3 and M4 change no behaviour, only the log
  string), which is the inverse framing Codex did not state.
- **P3 (a shutting-down worker must not claim).** Holds at `worker-runner.ts:119`. Killed by M11 via
  **both** shutdown cases — the failing-sweep one and the successful-sweep one. The refactor did not
  disturb the guard's position relative to the sweep.
- **P4 (the default must sweep).** Holds. Killed by M5 and M7 via `sweeps by default when no policy is
  supplied` and `the default policy is STATELESS`.
- **P5 (monotonic clock, fail safe backwards).** Holds. Killed by M9 (`sweeps immediately if an
  INJECTED clock steps backwards`) and M10 (`the DEFAULT clock is monotonic…`). I also checked the
  degenerate inputs by reading `worker/main.ts:104-105`: `lastSweptAt = -Infinity` gives
  `elapsed = Infinity` → sweeps; a `NaN` clock makes both comparisons false → sweeps. Both fail safe.
- **⭐ REFUTING Codex.** Its *Other Attacks* section asks for *"a dedicated 'default sweeps on two
  consecutive calls' test"* to pin `ALWAYS_SWEEP`'s statelessness. **That test already exists** —
  `the default policy is STATELESS — two consecutive no-policy calls both sweep`,
  `tests/lib/lease-sweep-cadence.test.ts:351-358` — and I killed M7 (a 60s cursor added to
  `ALWAYS_SWEEP`) with it. Codex reviewed a tree with 24 cases and this is the 25th; either it was
  added after Codex read, or Codex missed it. Nothing to do.
- **`this`-binding and stale capture in `() => queue.sweepExpired()` (`worker-runner.ts:103`).**
  Clean, and I agree with Codex. The closure calls the method *on* `queue`, so the receiver is
  preserved; it is constructed per `runOnce` invocation from that call's own `queue` parameter, so
  there is nothing to go stale. A `.bind`-free extraction (`const s = queue.sweepExpired`) would break
  it, but nothing does that.
- **Other implementers or consumers of `SweepPolicy`.** I grepped `lib/ worker/ tests/ app/
  components/ scripts/` for `SweepPolicy|sweepPolicy|sweepGate|makeSweepGate|onSwept|ALWAYS_SWEEP`.
  Production: `makeSweepGate`, `ALWAYS_SWEEP`, `runOnce` (`:103`, the sole invocation),
  `runWorkerLoop` (`worker/main.ts:142`). Tests: only `lease-sweep-cadence.test.ts`. **No stale
  `due()`/`onSwept()` implementation survives anywhere.** Confirms Codex.
- **`tests/integration/` (NOT in CI — `jest.config.ts` `testMatch` covers `tests/lib`, `tests/api`,
  `tests/scripts`, `tests/smoke.test.ts`, `tests/components` only).** ✅ **They still compile**, and
  this is measured, not assumed: `npx tsc --noEmit --listFiles` type-checks **80** files under
  `tests/integration/` (`tsconfig.json` `include` is `**/*.ts`, `exclude` is `node_modules` only) and
  exits 0. **By inspection they still pass**, and the reason is structural: not one of them passes
  `sweepPolicy` or `sweepGate`, so every one takes the `?? ALWAYS_SWEEP` default, whose behaviour —
  sweep unconditionally, swallow the failure, proceed to claim — is *identical* to master's
  `if (opts.sweepPolicy?.due() ?? true) { try { … } catch { … } }`. The three suites that touch
  `runOnce` (`worker-runner-runtime`, `job-queue-runner`, `worker-main`) stub or really implement
  `sweepExpired` and none asserts on it, except `worker-main.test.ts:83`'s `expect(sweepCalls).toBe(1)`
  — which is about `runWorkerLoop`'s gate, untouched by this branch, and was already retargeted in
  PR #318. ⚠ I could not execute them (no live Supabase); this is inspection plus a real `tsc`.
- **The `cycle()` helper — the brief's premise is wrong, and that is worth recording.** The brief says
  *"the `cycle()` helper now swallows errors — does that weaken any assertion?"*. It does **not**
  swallow: `:40-47` awaits `policy.run(...)` bare, with no `try`. If a policy rejected, `cycle` would
  reject and its test would fail — which is precisely how M3 killed `a sweep that THROWS does not
  spend the window`. No assertion is weakened. Its real limitation is narrower and benign: `ran`
  records that the sweep was *invoked*, not that the window was *committed*, so it cannot by itself
  distinguish "swept and committed" from "swept and did not commit" — which is why the P1 test at
  `:103-116` has to probe the *following* call to observe the commit, and it does.
- **`ALWAYS_SWEEP` as a shared module-level singleton.** Genuinely stateless today
  (`worker-runner.ts:41-49` closes over nothing), pinned by the M7-killing test. Safe. The residual
  risk Codex names — someone adding state later — is the one that test exists for.
- **Every remaining test in the file.** All 25 accounted for. I found **no tautology**, and **no case
  that would pass with the refactor reverted** — reverting to `due()`/`onSwept()` would not compile
  against this file, since `cycle` and the `policy()` double both call `run`. The two cases I flagged
  in Medium 1 have accurate *assertions* and inaccurate *comments*; they kill real mutations.
- **A caller committing the window on a throwing sweep (the brief's attack 2).** At the call site:
  **no**, I could not write it — the nearest attempt (M1) is caught by two tests. Inside a policy
  implementation: **yes**, trivially, and that is High 1.
- **The outer catch swallowing a programmer error (the brief's attack 3).** Real but minor, and I
  agree with Codex's disposition of *not blocking*. A malformed policy (`{}` from JSON or a
  non-TypeScript caller) makes `.run` a `TypeError` at `:103`, caught at `:104`, logged, and intake
  continues. Losing intake to a config typo is strictly worse than logging it, and the log line names
  the policy. I would not change it.
- **Reentrancy.** `run` is async and `lastSweptAt` is written after the `await`, so two overlapping
  `run` calls on one gate would both sweep. Unreachable today: `runWorkerLoop` awaits each `runOnce`
  and builds one gate outside the loop (`worker/main.ts:142`, pinned by M12). Identical on master —
  **not a regression, and I am not filing it.**
- **Backlog #140 and roadmap ticks.** The ✅ on `docs/backlog.md:140` and the `[x]` on
  `docs/roadmap-to-launch.md:502` are **honest about what shipped** — the DONE note volunteers the
  Codex refutation and says "unwritable **at the call site**" rather than the stronger claim. My
  quarrel is with the FALSIFIER they were ticked against, dissected in High 1: its first clause holds,
  its second is false. `check-backlog-closure.py` is rc=0 (its one warning, `#117`, is pre-existing and
  unrelated). `check-review-rounds.py`, `check-docs.py` and `check-anchors.py` are rc=0.

---

## Verdict: **FINDINGS**

2 High, 2 Medium, 5 Low. **Nothing blocking, and the shipped behaviour is correct** — P1 through P5
all hold, I killed 11 of 12 mutations, and I could not construct an input that makes
`runWorkerLoop → makeSweepGate → runOnce` do the wrong thing.

The findings are about **what the branch claims** and **what is left unguarded**, which for a change
whose entire justification is a structural-safety claim is the part that matters:

- **High 1** — the `finally` hazard moved from `runOnce` to `makeSweepGate` rather than disappearing,
  and the interface now obliges *every* future policy to re-derive two rules that master wrote once.
  The branch ships the second copy in the same commit. The prose must be corrected (option a) or the
  claim made true (option b).
- **High 2** — M4 is the one surviving mutation: the fail-safe default's never-reject clause has no
  test, while the non-default's does.

Both are cheap. High 2 is one test case; High 1(a) is three comment blocks and a backlog clause.
I would not merge on the prose as it stands, because the #140 row's DONE note and
`worker-runner.ts:20-25` are what the next reader will cite.

**`git status --porcelain` at the end of this review** — the five `M` entries are the uncommitted
branch itself, the three `??` are review artefacts; **no mutation residue, source shas unchanged**:

```
 M docs/backlog.md
 M docs/roadmap-to-launch.md
 M lib/job-queue/worker-runner.ts
 M tests/lib/lease-sweep-cadence.test.ts
 M worker/main.ts
?? docs/reviews/claude/sweep-policy-run-fn-r1-claude.md
?? docs/reviews/codex/sweep-policy-run-fn-r1-codex.md
?? docs/reviews/verdicts/sweep-policy-run-fn-r1-codex.verdict.json
```
