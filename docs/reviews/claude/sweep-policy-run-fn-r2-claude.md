# Adversarial review — `sweep-policy-run-fn` round 2 (Claude half)

**Subject:** branch `sweep-policy-run-fn` at commit `e1ea7018`, two commits on `origin/master`
(`9936ea66`, `e1ea7018`). Backlog #140 — collapse `SweepPolicy` to a single `run(fn)`.

**Tree state.** `git status --porcelain` at the start of this review was **empty**. The subject did
not move while I read it — the r1 hazard is fixed. I applied thirteen mutations to
`lib/job-queue/worker-runner.ts`, `worker/main.ts` and (once) `tests/lib/lease-sweep-cadence.test.ts`,
and created one temporary probe file `tests/lib/zz-tmp-r2-probe.test.ts` which I deleted. **At the end
of this review `git status --porcelain` outputs exactly one line:**

```
?? docs/reviews/claude/sweep-policy-run-fn-r2-claude.md
```

— this file, and nothing else. No tracked file is modified.

---

## Verdict: FINDINGS — 0 Blocking, 1 High, 2 Medium, 4 Low

**Lead with the conclusion.** The headline claim is now **true, and I could not refute it a fourth
time**: I enumerated every `SweepPolicy` construction in the repo and all three real ones are built
from `sweepPolicyFrom`. But the **fix for r2 Low 1 is guarded by nothing** — four separate mutations
that undo it, one by one, leave the suite **26/26 green**. That is r1 High 2's exact defect class
(*"a never-reject clause guarded by nothing"*, plus *"a false diagnostic"*) reproduced inside the fix
for r1 High 2, one round later. And one of the two paths that fix newly formalised — a throwing
`due()` — **fails dangerous**: measured, 100 polls produced **0 sweeps and 100 claims**, which is the
permanent-silent-death-of-lease-reclamation failure that `worker/main.ts:70-73` names as the worst
one, chosen in preference to the fail-safe direction that `worker-runner.ts:105` states as the rule.

P1–P5 all hold. I re-ran every one rather than taking Codex's word; each is killed by a named test.

---

## What I read and ran

**Read in full:** `lib/job-queue/worker-runner.ts` (247 lines), `worker/main.ts` (190),
`tests/lib/lease-sweep-cadence.test.ts` (497), `git show origin/master:worker/main.ts`,
`git show origin/master:tests/lib/lease-sweep-cadence.test.ts`, both commit messages in full, the
`docs/backlog.md` #140 row, the `docs/roadmap-to-launch.md` #140 row and test-count line, both
`docs/dashboard-entries.md` entries for this work (`:10352-10412`, `:10440-10470`),
`docs/reviews/codex/sweep-policy-run-fn-r1-codex.md`,
`docs/reviews/claude/sweep-policy-run-fn-r1-claude.md`,
`docs/reviews/codex/sweep-policy-run-fn-r2-codex.md`, and the full `git diff origin/master...HEAD`.

**Ran:**

| Command | Result |
|---|---|
| `npx jest tests/lib/lease-sweep-cadence.test.ts` (control) | **26/26 green** |
| `npx tsc --noEmit` | **clean (rc=0)** |
| `python3 scripts/check-test-counts.py` | `roadmap test counts match the suite: 2,845 unit / 275 suites` (rc=0) |
| `python3 scripts/check-docs.py` | `Documentation integrity OK` (rc=0) |
| `python3 scripts/check-dashboard-entry.py` | `ok — an entry block was added` (rc=0) |
| `python3 scripts/check-backlog-closure.py` | rc=0 (1 pre-existing warn, #117, unrelated) |
| `python3 scripts/check-review-rounds.py` | rc=0, `0 silent gaps` |
| 13 source mutations + 1 historical-tree mutation | table below |
| 5-case temporary probe suite (deleted) | 5/5 pass — measurements quoted below |

### Mutation results (all reverted; control re-verified green after each)

| # | Mutation | Tests failed | Killed by |
|---|---|---|---|
| P1a | drop the `return` in the sweep `catch` (`worker-runner.ts:90`) | **3** | `a sweep that THROWS does not spend the window`; `does NOT acknowledge a sweep that threw`; `keeps sweeping AND keeps claiming when every sweep throws` |
| P1b | the literal `try/catch/finally { commit() }` mistake | **3** | same three |
| P2a | `sweepPolicyFrom` rethrows the sweep failure | **3** | `a sweep that THROWS…`; `never rejects, whatever the sweep does`; `the DEFAULT policy never rejects either` |
| P2b | delete `runOnce`'s defence-in-depth catch (`:166-171`) | **1** | `still claims when the POLICY ITSELF rejects, not just the sweep` |
| P3 | delete `if (opts.shutdownSignal?.aborted) return 'idle'` (`:181`) | **2** | `…shutdown arrived while the sweep was failing`; `…during a SUCCESSFUL sweep either` |
| P4 | default to a not-due policy instead of `ALWAYS_SWEEP` | **2** | `sweeps by default when no policy is supplied`; `the default policy is STATELESS` |
| P5a | `performance.now()` → `Date.now()` (`main.ts:100`) | **1** | `the DEFAULT clock is monotonic` |
| P5b | drop the `elapsed >= 0` floor (`main.ts:108`) | **1** | `sweeps immediately if an INJECTED clock steps backwards` |
| MX6 | make `makeSweepGate`'s `due()` record `lastSweptAt` | **4** | 4 cadence cases |
| **MX1** | **revert r2 Low 1: put `cursor.due()` back outside the `try`** | **0 — SURVIVES** | — |
| **MX2** | **revert r2 Low 1: unwrap `cursor.commit()`** | **0 — SURVIVES** | — |
| **MX3** | **`due()`'s diagnostic → `sweepExpired failed` (the false diagnostic)** | **0 — SURVIVES** | — |
| **MX4** | **`commit()`'s diagnostic → `sweepExpired failed`** | **0 — SURVIVES** | — |
| MX5 | flip the `due()` catch to the fail-safe direction (`due = true`) | **0 — SURVIVES** | — |
| hist | P1a applied to the r1-era test file (`git show 9936ea66:…`) | **2** | confirms the 2→3 history below |

---

## Blocking

**None.** No finding here changes what the shipped worker does today. The interpreter of every
mutation above is a test, not production: `makeSweepGate` with the default `performance.now()` clock
cannot throw from `due()` or `commit()`, so High 1 and Medium 1 are about the *guard*, the *contract*
and the *next* implementer, not about the running worker.

---

## High

### High 1 — the entire r2 Low 1 fix is guarded by nothing. Four mutations, four survivors, 26/26 green each time.

`sweepPolicyFrom` (`lib/job-queue/worker-runner.ts:68-101`) grew two new `try` blocks and two new
diagnostic strings in the r2 fold. **Nothing in the suite can tell whether any of it is there.**

Measured, one at a time, each against a control I proved green first:

| What I undid | Suite |
|---|---|
| `let due; try { due = cursor.due(); } catch { … return; }` → `if (!cursor.due()) return;` (the pre-r2 code, which *rejects* out of `run`) | **26/26 green** |
| `try { cursor.commit(); } catch { … }` → `cursor.commit();` (the pre-r2 code) | **26/26 green** |
| `'[worker] sweep cadence check failed…'` → `'[worker] sweepExpired failed…'` | **26/26 green** |
| `'[worker] sweep cadence commit failed…'` → `'[worker] sweepExpired failed…'` | **26/26 green** |

Compare what the branch says it bought. `e1ea7018`'s message: *"sweepPolicyFrom is now three stages
with three distinct diagnostics: cadence-check failure, sweep failure, commit failure."*
`docs/dashboard-entries.md:10461`: the same. `docs/backlog.md:168`: *"r2 also moved `due()` under
error handling and split the diagnostics three ways."* Every one of those three stages and all three
diagnostics can be deleted or merged back with a green suite.

**Why this is High and not Low.** This is not a generic "add a test" note. It is *the same defect,
in the same function, one round later*, and the branch's own record says so twice:

- r1 **High 2** was filed because `ALWAYS_SWEEP`'s never-reject clause "was guarded by NOTHING —
  deleting its try/catch left the suite 25/25 green" (`9936ea66`). The fix for that is celebrated in
  `docs/backlog.md:168` as *"now UNWRITABLE, because there is no second copy of the rule to delete."*
  True — and in the same round two **new** unguarded never-reject clauses were added twenty lines
  above it.
- r1 **High 2's** stated concrete cost was *a false diagnostic* — "the operator's log would flip from
  `sweepExpired failed` to `sweep policy rejected` on exactly the failure this work exists for, with
  nothing red." MX3 and MX4 are that sentence verbatim, in the opposite direction, and nothing goes
  red.

`worker-runner.ts:57-61` claims the one remaining writable mistake "fails THREE tests (measured…);
Every other route was deleted." The three-test claim is correct (I measured it). The sentence's
implication — that the function is now covered — is not: the function has five behavioural paths and
only two of them (`due` false; `sweep` throws) are observed by any test.

**Fix (small, and I have already written it).** The two probes below are the missing cases; both pass
against the delivered code and both fail against MX1/MX2 respectively. They belong in
`tests/lib/lease-sweep-cadence.test.ts` next to the existing never-reject cases:

```ts
test('run() does not reject when the CURSOR is what fails, and says so by name', async () => {
  const err = jest.spyOn(console, 'error').mockImplementation(() => {});
  const p = sweepPolicyFrom({ due: () => { throw new Error('clock'); }, commit: () => {} });
  const swept = jest.fn(async () => {});
  await expect(p.run(swept)).resolves.toBeUndefined();
  expect(swept).not.toHaveBeenCalled();
  expect(String(err.mock.calls[0][0])).toContain('sweep cadence check failed');  // kills MX1 and MX3
  err.mockRestore();
});

test('run() does not reject when COMMIT fails, and the sweep still counts as run', async () => {
  const err = jest.spyOn(console, 'error').mockImplementation(() => {});
  const p = sweepPolicyFrom({ due: () => true, commit: () => { throw new Error('bookkeeping'); } });
  const swept = jest.fn(async () => {});
  await expect(p.run(swept)).resolves.toBeUndefined();
  expect(swept).toHaveBeenCalledTimes(1);
  expect(String(err.mock.calls[0][0])).toContain('sweep cadence commit failed');  // kills MX2 and MX4
  err.mockRestore();
});
```

I ran both (plus three more) as `tests/lib/zz-tmp-r2-probe.test.ts`: **5/5 pass** against
`e1ea7018`. The file is deleted; the code is quoted here so it does not have to be re-derived.

⚠ **This finding also arms a process condition — see *Process observation* at the end.**

---

## Medium

### Medium 1 — a throwing `due()` is handled in the fail-DANGEROUS direction, against the rule stated fifteen lines below it

`lib/job-queue/worker-runner.ts:78-84`:

```ts
      try {
        due = cursor.due();
      } catch (e) {
        console.error('[worker] sweep cadence check failed (continuing to claim):', e);
        return;
      }
```

A broken cadence check is treated as **not due**. So the sweep is skipped — and if the cursor keeps
throwing, skipped forever.

**Measured**, not argued (probe 3 of 5):

```
100 × runOnce with sweepPolicyFrom({ due: () => { throw }, commit: () => {} })
  → queue.sweepExpired called  0 times
  → queue.claim         called  100 times
```

Zero sweeps for the life of the process, with a log line per poll reading *"continuing to claim"*,
which reads like reassurance. That is precisely the outcome `worker/main.ts:70-73` singles out as the
catastrophic one — *"the sweep would never run again for the life of the process — lease reclamation
silently dead, with nothing to report it"* — reached by a different route than the one that comment
guards against.

And the repository already states the correct direction, in this same file, fifteen lines below
(`worker-runner.ts:104-105`, on `ALWAYS_SWEEP`):

> *"Sweeping too often is cheap; never sweeping strands crashed jobs."*

The `commit` catch two blocks down reasons explicitly about fail-safety (`:96` — *"Failing to record
a landed sweep is fail-safe: the next poll sweeps again"*). The `due` catch does not, and picks the
other direction. Nothing in the branch record explains the asymmetry; I believe it is an accident of
writing `return` twice.

**Honest scoping, twice over.** (a) This is not *introduced* by the r2 fix. Before it, a throwing
`due()` rejected out of `run`, `runOnce`'s defence catch swallowed it, and the sweep was equally
skipped — the observable behaviour is unchanged. What r2 did was *formalise* the unsafe direction and
write a comment beside it. (b) It is unreachable in production today: `makeSweepGate`'s `due()` is
`now() - lastSweptAt` over `performance.now()`, which does not throw. It **is** reachable through the
public seam — probe 5 confirms `makeSweepGate(60_000, () => { throw … })` produces exactly the
0-sweeps/1-claim behaviour, and the `now` parameter is exported and injectable.

**Fix:** one token, `due = true` instead of `return`, so a broken cursor degrades to the documented
fail-safe default rather than to silence. ⚠ **It needs a test with it** — I measured that mutation
(MX5) as **surviving 26/26**, so flipping the direction without a case just moves an unguarded
decision.

### Medium 2 — the roadmap row was ticked with the refuted framing left intact

`docs/roadmap-to-launch.md:505`:

> `- [x]` **backlog #140 — 🟢 collapse `SweepPolicy` to a single `run(fn)`.** ✅ **DONE 2026-09-18.**
> **The only proposed change that removes a finding BY CONSTRUCTION rather than by a guard.**

That bolded sentence is the claim r1 refuted and the branch spent two rounds retreating from. The
finding is **not** removed by construction: `worker-runner.ts:22` says *"The `finally` mistake is
writable in exactly one function — the minimum, not zero"*, and `:57-60` says it is caught **by a
guard** — three tests, which I verified. `docs/backlog.md:168` carries the full correction
(*"BUT NOT FOR THE REASON FILED"*, *"THE HONEST BOUND"*). The roadmap carries none of it.

This matters beyond tidiness for one reason the repo has already paid for: the roadmap is the
compaction-proof layer (`docs/dev-process.md` → *Roadmap & Task List*). A future reader reconciling
against git reads *"removes a finding by construction"* as the settled outcome of #140, which is the
one sentence three review halves established as false.

**Fix:** one sentence in the row body, e.g. *"⚠ Shipped as `sweepPolicyFrom(cursor)`, and NOT by
construction — r1 refuted that; the mistake is writable in exactly one function and is caught by
three tests. See the backlog row."*

---

## Low

### Low 1 — the falsifier count says **2** in the one place that is live code; measured, it is **3**

`tests/lib/lease-sweep-cadence.test.ts:130-131`:

> *"`a sweep that THROWS does not spend the window` is what kills it there (measured: that mutation
> fails **2** tests)."*

`e1ea7018`'s commit message says the opposite, in capitals:

> *"⟳ THE FALSIFIER COUNT CHANGED AND IS **CORRECTED EVERYWHERE IT WAS STATED**: mutating
> sweepPolicyFrom now fails THREE tests, not two…"*

It was not corrected everywhere. `worker-runner.ts:58`, `docs/backlog.md:168` and
`docs/dashboard-entries.md:10467` all say three and are right; the test file still says two. It is the
**only live site still wrong** — the other "2"s are in `9936ea66`'s commit message and the first
dashboard entry, which are append-only history and correctly frozen.

I confirmed both numbers rather than assuming the newer one wins. Applying P1a to
`git show 9936ea66:tests/lib/lease-sweep-cadence.test.ts` kills **2**; applying it at `e1ea7018` kills
**3**. The count moved for a real reason — at `9936ea66` the `policy()` double was hand-rolled and
committed correctly on its own, so `does NOT acknowledge a sweep that threw` could not see a mutation
in production code; rebuilding the double on the combinator (r2 Low 2) is what recruited that third
test. So the correction is right, its cause is interesting, and one site missed it.

### Low 2 — the dashboard states the suite delta as `2,844 → 2,845`; against this branch's base it is `2,841 → 2,845`

`docs/dashboard-entries.md`, end of the first #140 entry: *"Suite 2,844 → 2,845."*

Measured: `origin/master`'s roadmap says **2841 unit / 275 suites** (CI-verified there by
`check-test-counts.py`); `tests/lib/lease-sweep-cadence.test.ts` holds **22** tests on master and
**26** on the branch; the only other test file touched is
`tests/integration/worker-main.test.ts`, whose diff is a one-line comment and which
`jest.config.ts`'s `testMatch` excludes anyway. `check-test-counts.py` on the branch reports **2,845**.
So the branch adds **four** tests, not one.

Low, not Medium: nothing depends on the number, `check-test-counts.py` gates the roadmap figure, and
the end state (2,845) is right everywhere. But a dashboard entry is read as a measurement, and this
one understates the work by three tests.

### Low 3 — `worker/main.ts:86` attributes the clock re-sample to `run`, which is the one function that no longer touches a clock

> *"The period runs from COMPLETION, not from the due check: **`run` re-samples the clock** after the
> sweep has returned…"*

`run` (`worker-runner.ts:70-99`) contains no clock arithmetic at all — that is the entire point of the
refactor. The re-sample is `cursor.commit()` at `main.ts:110`. Master's version of this sentence said
*"onSwept() re-samples the clock"*, which was precise; the rename made it wrong.

This is r2 Low 3's class exactly (*"a comment still pointed at `makeSweepGate.run` as the home of the
rule"*) — a second instance of that finding that the fix for it did not sweep up. **Fix:** *"`commit()`
re-samples the clock"*.

### Low 4 — "commit failure is fail-safe" is true for reclamation and silently false for cost

`worker-runner.ts:96`: *"Failing to record a landed sweep is fail-safe: the next poll sweeps again."*
`docs/dashboard-entries.md:10464` repeats it.

Correct as far as it goes. Measured (probe 4): with a cursor whose `commit()` always throws, 30 polls
produce **30 sweeps** — the window is never committed, so the gate degrades to sweeping on *every*
poll. That is the pre-2026-09-18 behaviour, i.e. the ~40,000 requests/day of egress this entire branch
exists to remove, restored silently with only a log line. "Fail-safe" is the right word for lease
reclamation and the wrong word for the property the branch is named for.

**Fix:** half a sentence — *"…fail-safe for reclamation: the next poll sweeps again. Note the cost
side — a persistently failing commit reverts the gate to per-poll sweeping, i.e. the egress
regression."*

---

## ⭐ The claim, enumerated: I could not refute it a fourth time

> *"Both rules are written exactly once, in `sweepPolicyFrom`; no implementation holds either."*

**Method.** `grep -rn` over the whole repo (excluding `node_modules` and `docs/reviews/`) for
`SweepPolicy`, `SweepCursor`, `sweepPolicyFrom`, `sweepPolicy`, `sweepGate`, `ALWAYS_SWEEP`,
`makeSweepGate`, `sweepExpired`, then opened every hit in `lib/`, `worker/`, `tests/`, `app/`,
`components/`, `scripts/`. **Every construction of a `SweepPolicy` value in the repository, all five:**

| # | Site | Built from `sweepPolicyFrom`? | Holds a rule? |
|---|---|---|---|
| 1 | `lib/job-queue/worker-runner.ts:68` — `sweepPolicyFrom` itself | n/a — it **is** the one copy | both, once |
| 2 | `lib/job-queue/worker-runner.ts:110` — `ALWAYS_SWEEP` | ✅ `{ due: () => true, commit: () => {} }` | neither |
| 3 | `worker/main.ts:105` — `makeSweepGate` | ✅ clock arithmetic only | neither |
| 4 | `tests/lib/lease-sweep-cadence.test.ts:230` — the `policy()` double | ✅ `{ ran, ...sweepPolicyFrom({ due: () => due, commit: ran }) }` | neither |
| 5 | `tests/lib/lease-sweep-cadence.test.ts:357` — `rejecting` | ❌ hand-rolled | **breaks** never-reject, deliberately |

There are no others. No `app/`, `components/` or `scripts/` file mentions any of these symbols.
`tests/integration/worker-runner-runtime.test.ts:32` and
`tests/lib/blob-addressing-caller-contract.test.ts:87` stub `sweepExpired` on a queue and construct no
policy at all.

**Is #5 a loophole? No — I tried to make it one and it does not work.** Three tests:

1. *Does it hold a rule?* It holds **neither**. It has no cursor, no commit, and no catch; its body is
   `throw`. A copy of a rule is something that can drift out of agreement with the original. This
   cannot drift, because it asserts nothing.
2. *Does it carry its exemption honestly, where a reader will hit it?* Yes, in two places — the
   interface's own docstring at `worker-runner.ts:64-67` (*"⚠ ONE hand-rolled `run` remains, at
   … the `rejecting` double — it exists precisely TO break the never-rejects contract"*) and at the
   test itself (`:351-354`). The exemption is stated at the definition site, not only in a commit
   message.
3. *Is it load-bearing, or is the exemption doing work the code should do?* Load-bearing: mutation P2b
   (delete `runOnce`'s defence-in-depth catch) fails **exactly** this test and no other. Remove the
   `rejecting` double and `runOnce:166-171` becomes unguarded. It cannot be built from the combinator,
   because the combinator's whole purpose is to make the thing it tests impossible.

So the deliberate violator is honest, minimal, and the only one. **The claim survives.** For the
record, the three earlier refutations were: (1) *"unwritable"* — false, the seam is exported; (2)
*"unwritable by callers"* — true and near-vacuous; (3) *"written exactly once"* — false with the test
double counted. I attacked the same sentence from a fourth angle — the **population**, by enumeration
rather than reasoning — and it holds at `e1ea7018`.

**One residual worth naming, which the claim does not cover and does not misstate.** `SweepCursor.due()`
carries a rule of its own, written in its docstring as a prohibition (`worker-runner.ts:43-44`):
*"Must not record anything — the window is spent by a sweep that LANDED, not by one that was
contemplated."* That is a non-obvious discipline the type cannot express, held by every cursor
implementation rather than by the combinator, and its failure mode is the worst one in the file
(`main.ts:70-73`: the sweep never runs again). I checked whether the branch introduced it: **it did
not** — `git show origin/master:worker/main.ts:68-72` carries the identical warning about `due()` vs
`onSwept()`, so parity with master is preserved and r1 High 1's counting argument is satisfied. I also
checked whether it is guarded for the shipped cursor: mutation MX6 (make `due()` record) fails **4**
tests. So: real residual, pre-existing, guarded for the one cursor that exists. Not a finding against
this branch — but it is the piece a redesign could still dissolve (below).

---

## Question 2, answered path by path: what the r2 Low 1 fix did and did not introduce

**Can `run` still reject?** No — verified by exhaustive path walk *and* by running it.
`sweepPolicyFrom` has exactly five exits: the `due`-threw `return`; the `!due` `return`; the
`sweep`-threw `return`; the commit-threw fallthrough; the clean fallthrough. Everything that can throw
is inside a `try`: `cursor.due()` (:79), `await sweep()` (:87) — which also catches a *synchronously*
throwing `sweep`, a non-function `sweep`, and a rejecting thenable — and `cursor.commit()` (:94). A
null or undefined `cursor` throws a `TypeError` inside the first `try`. The only uncaught statements
are the three `console.error` calls themselves. Probes 1 and 2 confirm `resolves.toBeUndefined()` for
both new paths.

**Is a commit failure really fail-safe?** For reclamation yes, for cost no — Low 4, measured at 30
sweeps in 30 polls.

**Does the `return` in the sweep catch change anything beyond skipping commit?** No. It is the last
statement before the commit block and the commit block is the last thing in `run`; there is no
`finally`, no shared teardown, no value to return. Mutation P1a (delete it) and P1b (express the same
thing as `finally { commit() }`) produce **identical** results — 3 failures, the same three tests —
which is the behavioural proof that skipping commit is its only effect.

**Is three stages over-engineering that obscures the rule?** No. Each stage answers a different
operator question and the failures are genuinely distinguishable at the source (*the database call is
broken* / *the clock is broken* / *the bookkeeping is broken*), which is exactly what r1 High 2 was
filed about. Twenty-eight lines for a function with five paths is not bloated, and collapsing them
would rebuild the false diagnostic. The problem is not that there are three stages — it is that
**nothing can tell whether there are three stages** (High 1), and that one of the three chose the
wrong direction (Medium 1).

---

## What I checked and found clean

State explicitly where I found nothing — the following were examined and are correct.

- **P1–P5 all hold.** Re-run rather than taken from Codex; every one is killed by a named test, table
  above. Codex's r2 report was accurate on all five, and its P1 count of "2 tests" was correct against
  the tree it read and is now 3 for the reason in Low 1.
- **`ALWAYS_SWEEP` statelessness and initialization order.** `sweepPolicyFrom` is a function
  *declaration*, hoisted, so it is initialized before `ALWAYS_SWEEP`'s initializer runs at `:110` — no
  TDZ hazard. The cursor literal captures no mutable state, so the module-level singleton is safe to
  share across callers; `the default policy is STATELESS — two consecutive no-policy calls both sweep`
  (`:371`) pins it and P4 kills the plausible regression.
- **Re-entrancy.** `run` checks `due`, awaits, then commits, so two overlapping calls on one
  `makeSweepGate` would both sweep. Not reachable: `runWorkerLoop` (`main.ts:140-148`) builds one
  policy and awaits each `runOnce` sequentially, and `ALWAYS_SWEEP` holds no window to race on. Noted,
  not filed.
- **The gate is built once, not per iteration** (`main.ts:140`, outside the `while`). A gate
  constructed inside the loop would reset its cursor every poll and be due every time — the comment at
  `:134-136` says so and the placement matches.
- **The shutdown guard covers both the throw path and the success path** (`worker-runner.ts:181`), and
  P3 kills it via two tests, one per path. This was r2 Codex's Medium generalised to its class by the
  author rather than patched at the instance — correctly done.
- **`runOnce`'s defence-in-depth catch is not a fourth copy of the rule.** It guards a different
  subject (an arbitrary injected policy, at the call boundary) and, unlike the `ALWAYS_SWEEP` catch
  that r1 High 2 deleted, it is guarded — P2b kills it. Keeping this one and deleting that one is
  consistent, and the distinguishing criterion (does a test observe it?) is the right one.
- **The `SweepPolicy.run` docstring's warning not to lean on `runOnce`'s "never sees an unhandled
  rejection" comment** (`:31-34`) is accurate: `queue.claim` at `:183` does sit outside every `try` in
  `runOnce`, which is why `runWorkerLoop` needs its own catch at `main.ts:149`. r1 Medium 2 folded
  correctly.
- **The monotonic-clock case is not vacuous.** P5a (`performance.now()` → `Date.now()`) is killed, and
  only by the one case written for it — the fail-safe floor is precisely why nothing else can tell the
  two clocks apart, as `:173-175` says.
- **`tests/integration/worker-main.test.ts`'s comment fix** (r1 Low 5) is right: after the fix, a
  throwing `sweepExpired` no longer escapes `runOnce`, so `claim` really is "the one call outside
  `runOnce`'s try/catch".
- **All doc gates are green**, listed in the table at the top; `check-review-rounds.py` reports
  `0 silent gaps` and will be satisfied by this file. `tsc --noEmit` clean. `check-test-counts.py`
  agrees with the roadmap at 2,845 / 275.
- **`docs/backlog.md:168` — I read the whole row and found no overstatement.** It carries the
  three-test count (correct), the "writable in exactly ONE function — the minimum, not zero" bound
  (correct), the "NOT FOR THE REASON FILED" retraction, and all three refutations of the central claim
  in order. It is the most accurate document on this branch. The `✅ (was 🟢)` marker and the roadmap
  `[x]` agree.
- **Both commit messages are accurate for the trees they describe.** `9936ea66`'s "fails 2 tests" is
  correct against `9936ea66` — I verified it by checking that tree's test file out and running the
  mutation. `e1ea7018`'s only inaccuracy is the word "EVERYWHERE" in the correction notice (Low 1).
- **Nothing outside the worker is touched.** The diff is 12 files: two source, two test, and eight
  docs/review artefacts. No schema, no migration, no API route, no client.

---

## Process observation — the thrashing condition is armed on its letter

Filed here rather than as a finding, because it is the coordinator's call and not a defect.

`docs/dev-process.md` Phase 6 arms an architecture review on **two consecutive rounds whose findings
came from the previous round's own fix, in one component** — and instructs that reaching it *obliges
asking*, with per-finding evidence, *thrashing or prose floor?*

Per-finding, in one component (`sweepPolicyFrom`, 34 lines):

| Round | Finding | Caused by the previous round's fix? |
|---|---|---|
| r2 | Low 1 — `due()` outside the `try` | **Yes** — the path was created by r1's move into `sweepPolicyFrom` |
| r2 | Low 2 — the test double re-derived both rules | **Yes** — the *claim* it falsifies was made by r1's fix |
| r2 | Low 3 — comment names `makeSweepGate.run` | **Yes** — the rule moved in r1's fix |
| r3 | High 1 — the three new stages are unguarded | **Yes** — they are r2 Low 1's fix |
| r3 | Medium 1 — the `due()` catch fails dangerous | **Yes** — that `return` is r2 Low 1's fix |
| r3 | Low 1 — the stale "2 tests" | **Yes** — the count moved because of r2 Low 2's fix |
| r3 | Low 3 — "`run` re-samples the clock" | Carried from r1's fix, missed by r2 Low 3's |
| r3 | Medium 2, Low 2, Low 4 | No — documentation, independent |

Two consecutive rounds, most findings traceable to the prior fix. **It is not a prose floor** — High 1
is four executed mutations against shipped code, not a wording dispute.

**The test the method asks — *can a redesign remove it?* — has a concrete yes.** All three of High 1,
Medium 1 and the `due()`-must-not-record residual exist only because `SweepCursor` is a
caller-supplied object that can throw and can misbehave. Give the combinator the *state* instead of a
cursor:

```ts
export function sweepPolicyFrom(intervalMs: number, now: () => number = () => performance.now()): SweepPolicy
// makeSweepGate(ms, now) === sweepPolicyFrom(ms, now);  ALWAYS_SWEEP === sweepPolicyFrom(0)
```

`lastSweptAt` becomes private to the combinator. There is then **no cursor to throw** (so High 1's two
paths and Medium 1's direction question both cease to exist rather than being tested), and **no `due()`
for anyone to write a side effect into** (so the residual is dissolved rather than relied on). The
injectable seam that Codex r1 objected to shrinks from "any object implementing two methods" to "a
number and a clock". `makeSweepGate` becomes a one-line alias or disappears.

⚠ **I am not recommending it for this branch.** It would be the *fourth* redesign of a 34-line
function inside one review cycle, and this repo's own memory says the failure mode is "individually
thoughtful, fail as a set". My recommendation is: **land High 1's two tests and Medium 1's one-token
direction flip, fix the four Lows, merge** — then decide about the redesign with a clear head, or file
it. I record the redesign here only because the method requires the question to be *answered*, and the
answer is yes.

---

## Recommendation

**NOT READY to merge as-is** — High 1 means a delivered, twice-advertised behaviour has no falsifier,
and this repo's standing rule is that such a claim is not a claim.

**Ready after four small edits, none of which touches the design:**

1. **High 1** — add the two tests quoted above (written and run; they pass at `e1ea7018` and kill
   MX1–MX4).
2. **Medium 1** — `due = true` instead of `return` in the `due` catch, plus a case that observes it
   (MX5 survives today, so the flip needs its own falsifier).
3. **Medium 2** — one corrective sentence in the roadmap row.
4. **Lows 1–4** — the `2` → `3` in `tests/lib/lease-sweep-cadence.test.ts:131`; the `2,844` → `2,841`
   in the dashboard; `run` → `commit()` at `main.ts:86`; half a sentence on the cost side of
   "fail-safe" at `worker-runner.ts:96`.

**Next action:** hand these to the author; Medium 1 is the only one that changes runtime behaviour and
is the only one worth a second opinion before folding.

---

*Reviewer: Claude (adversarial half, round 2). Subject frozen at `e1ea7018`; it did not move.
`git status --porcelain` at completion: `?? docs/reviews/claude/sweep-policy-run-fn-r2-claude.md` —
this file only. Every mutation reverted with `git checkout --`; control re-verified 26/26 green.*
