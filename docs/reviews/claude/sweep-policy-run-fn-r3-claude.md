# Adversarial review — `sweep-policy-run-fn` round 3 (Claude half)

**Subject:** branch `sweep-policy-run-fn` at `e6a449fe`, four commits on `origin/master`
(merge-base `9e51d378`). Backlog #140. Scope as briefed: `08ea36be^..HEAD` plus current
`lib/job-queue/worker-runner.ts` and `worker/main.ts`.

**Tree state.** `git status --porcelain` was **empty** at the start of this review. I applied
**21 mutations** across `lib/job-queue/worker-runner.ts` and `worker/main.ts`, each reverted with
`git checkout --` immediately after its run, and created one temporary probe file
`tests/lib/zz-tmp-r3-probe.test.ts`, which I deleted. At the end, `git status --porcelain` outputs
exactly one line:

```
?? docs/reviews/claude/sweep-policy-run-fn-r3-claude.md
```

— this file, and nothing else. No tracked file is modified. The subject did not move while I read it.

---

## Verdict: FINDINGS — 0 Blocking, 0 High, 2 Medium, 5 Low

**Lead with the conclusion, in three parts.**

1. **The code is done.** Every mutation I could write against `sweepPolicyFrom`, `makeSweepGate`,
   `ALWAYS_SWEEP` and `runOnce`'s sweep block now dies — including all four that survived r2, and the
   one that reverts this round's behavioural change. P1–P5 re-verified by running them, not by
   reading Codex. I found **nothing wrong with the shipped behaviour**, and I agree with the direction
   of the fail-open trade.

2. **The streak does not end — but it has changed character, and that is the answer the method
   wants.** r1 was 2 High + 2 Medium, r2 was 1 High + 2 Medium, r3 is **0 High and two documentation
   Mediums**. Zero mutations survived. Every finding below is about a *sentence*, not a line of code.
   That is the **prose floor**, not thrashing — argued per-finding at the end. Do not arm Phase 6.

3. **I did refute the central claim a fourth time, and Codex verified a different proposition than
   the one the docstring states.** *"The `finally` mistake is writable in exactly ONE function"* /
   *"This is the one function where that edit is possible"* is false in the modal sense the sentence
   invites, for exactly the reason Codex's **r1 Blocking** gave and which was never applied. I
   re-ran Codex's own counterexample at HEAD: a caller-supplied `SweepPolicy` with
   `finally { commit() }`, passed through the still-exported `RunnerOpts.sweepPolicy` seam, spends
   the window on a sweep that threw — **1 sweep where P1 requires 2** — with the suite green.
   Codex r3 checked *who currently holds the rule* (grep, correct); the sentence claims *where the
   mistake can be made* (false). The other half of the claim — *"written exactly once, no
   implementation holds either"* — **holds**; I re-enumerated every construction site at HEAD, and
   it is the fifth enumeration to survive.

---

## What I read and ran

**Read in full:** `lib/job-queue/worker-runner.ts` (259), `worker/main.ts` sweep half,
`tests/lib/lease-sweep-cadence.test.ts`, `git show origin/master:lib/job-queue/worker-runner.ts`,
all four branch commit messages in full, `docs/backlog.md` row #140, `docs/roadmap-to-launch.md:505-514`,
all three `docs/dashboard-entries.md` entries for #140 (`:10353`, `:10424`, `:10478`) plus the two
#318 entries above them, `docs/reviews/codex/sweep-policy-run-fn-r{1,2,3}-codex.md`,
`docs/reviews/claude/sweep-policy-run-fn-r{1,2}-claude.md`.

**Ran:**

| Command | Result |
|---|---|
| `npx jest tests/lib/lease-sweep-cadence.test.ts` (control) | **30/30 green** |
| `npm test -- --ci` (full unit suite) | **2849 passed / 275 suites, 0 failures** |
| `npx tsc --noEmit` | **clean (rc=0)** |
| `python3 scripts/check-test-counts.py` | `2,849 unit / 275 suites` (rc=0) |
| `check-docs` / `check-dashboard-entry` / `check-review-rounds` / `check-anchors` / `check-backlog-closure` | all rc=0 (one pre-existing warn, #117, unrelated) |
| 21 mutations, each reverted, control re-proved | tables below |
| 6-case probe suite (`zz-tmp-r3-probe.test.ts`, deleted) | measurements below |

⚠ **One incidental positive worth recording:** while the probe file existed,
`check-test-counts.py` refused with *"the jest results are STALE … Treat this check as NOT RUN"*
(rc=1). The guard correctly reported CANNOT RUN rather than a stale green.

### Mutations — the four that survived r2 are dead, and the new fix is guarded

| # | Mutation | Failed | Killed by |
|---|---|---|---|
| **MA** | **revert this round's change: `let due = true` → `let due: boolean` + `return`** | **2** | `a throwing due() SWEEPS ANYWAY`; `a gate whose CLOCK throws keeps sweeping` |
| MB | `let due = true` → `let due = false` | 2 | same two |
| MC | delete `if (!due) return;` | 9 | every cadence case + `skips the sweep when not due` |
| **MX1** | r2's survivor: `due()` back outside the `try` | **2** | same two — *was 0 at r2* |
| **MX2** | r2's survivor: unwrap `cursor.commit()` | **2** | `…CLOCK throws…`; `a throwing commit() … leaves the window UNCOMMITTED` — *was 0* |
| **MX3** | r2's survivor: `due()` diagnostic → `sweepExpired failed` | **1** | `a throwing due() SWEEPS ANYWAY` — *was 0* |
| **MX4** | r2's survivor: `commit()` diagnostic → `sweepExpired failed` | **1** | `a throwing commit() …` — *was 0* |
| N5 | delete the `due`-catch diagnostic entirely (silent fail-open) | 1 | `a throwing due() SWEEPS ANYWAY` |
| N9 | rebuild `ALWAYS_SWEEP` hand-rolled *without* a never-reject catch | 1 | `the DEFAULT policy never rejects either` |
| N10 | `SWEEP_MS` 60s → 30 min | 1 | `SWEEP_MS is at most half the default lease` |
| MX6 | make `makeSweepGate`'s `due()` record the attempt | 4 | 4 cadence cases |

**P1–P5, re-run rather than taken from Codex. All hold.**

| P | Mutation | Failed | Killed by |
|---|---|---|---|
| P1a | drop the `return` in the sweep `catch` | **3** | `a sweep that THROWS does not spend the window`; `does NOT acknowledge a sweep that threw`; `keeps sweeping AND keeps claiming when every sweep throws` |
| P2a | `sweepPolicyFrom` rethrows the sweep failure | 4 | the two above + both never-reject cases + `a failing SWEEP is reported as a sweep failure` |
| P2b | `runOnce`'s defence-in-depth catch rethrows | 1 | `still claims when the POLICY ITSELF rejects` |
| P3 | delete the post-sweep shutdown guard | 2 | both shutdown-during-sweep cases |
| P4 | `ALWAYS_SWEEP` defaults to never-due | 2 | `sweeps by default…`; `the default policy is STATELESS` |
| P5a | `performance.now()` → `Date.now()` | 1 | `the DEFAULT clock is monotonic` |
| P5b | drop the `elapsed >= 0` floor | 1 | `sweeps immediately if an INJECTED clock steps backwards` |

### Probes (measured, then deleted)

| Probe | Measured |
|---|---|
| 1 — throwing `due()`, 100 polls through `runOnce`, at HEAD | **100 sweeps / 100 claims** |
| 2 — same through the shipped `makeSweepGate(60_000, throwingClock)` | **100 sweeps / 100 claims** |
| 1/2 re-run with MA applied (the pre-fix code) | **0 sweeps / 100 claims** ← the `0 sweeps across 100 polls` claim, reproduced |
| 3 — throwing `commit()`, 30 polls | **30 sweeps / 30 claims** ← the `30 sweeps in 30 polls` claim, reproduced |
| 4 — caller-supplied policy with `finally { commit() }` | **1 sweep** where P1 requires 2 — see Medium 1 |
| 5 — `due()` returns `undefined` / `'yes'` | **0/3** sweeps and **3/3** sweeps — see Low 5 |
| 6 — malformed (`undefined`) cursor | **3/3** sweeps, **3/3** claims, 0 rejections — fail-open works |

---

## Blocking

**None.** Nothing here changes what the shipped worker does, and I could not construct a production
input that reaches a wrong outcome.

## High

**None, and I want to be explicit that I looked.** r1 and r2 each found a High in the previous
round's fix; I attacked this round's fix the same way — MA, MB, MX1–MX4, N5 — and every one dies.
The behavioural change is guarded, the diagnostics are guarded, the direction is guarded, and both
guards run through the shipped seam. **The High-severity streak ends here.**

---

## Medium

### Medium 1 — ⭐ the fourth refutation. *"Writable in exactly ONE function"* is false in the sense the sentence invites, and it is Codex's r1 Blocking, unwithdrawn

Five live sites say a version of this:

| Site | Text |
|---|---|
| `lib/job-queue/worker-runner.ts:22` | *"The `finally` mistake is **writable in exactly one function** — the minimum, not zero."* |
| `lib/job-queue/worker-runner.ts:57` | *"**This is the one function where that edit is possible**"* … *":60 Every other route was deleted."* |
| `tests/lib/lease-sweep-cadence.test.ts:129` | *"the mistake is writable in exactly ONE function — the minimum, not zero"* |
| `docs/backlog.md:168` | *"The honest bound: the mistake is writable in exactly ONE function"* |
| `docs/roadmap-to-launch.md:509` | *"the mistake is writable in **exactly one function — the minimum, not zero**"* |
| `docs/dashboard-entries.md:10372` | *"the mistake is now **possible in exactly one place** … and a test fails if anyone makes it there"* |

`SweepPolicy` is still exported, and `RunnerOpts.sweepPolicy` (`:142`) and `runWorkerLoop`'s
`sweepGate` (`main.ts:139`) still accept an arbitrary one. So a second function where the edit is
possible is one `const bad: SweepPolicy = { async run(sweep) { … } }` away. **Measured, not argued**
— Codex r1's counterexample, re-run verbatim at HEAD (probe 4):

```
poll 1: sweep throws  -> the caller's `finally` commits the window
poll 2: window spent  -> sweep SKIPPED
PROBE4 sweeps = 1   (P1 holds only if 2)
```

Suite green throughout. The dashboard's promise — *"a test fails if anyone makes it there"* — is
false for that route: the three tests that kill the mistake all mutate `sweepPolicyFrom`, and nothing
observes a caller-supplied policy's commit discipline.

**Why this is a finding and not pedantry.** Codex r1 asked for one of two fixes: *"narrow the
docs/backlog/comments to 'unwritable at the call site; **policy implementations still own the
contract**'"*, **or** *"remove/privatize the arbitrary `SweepPolicy` injection seam"*. **Neither was
applied.** A third thing was done instead — `sweepPolicyFrom`, which is a genuine improvement and
makes the *corpus* claim true — and the modal claim then quietly reappeared in new words. The retreat
sequence is now: `unwritable` → `unwritable by callers` → `written exactly once` → **`writable in
exactly one function`**, and the fourth is the first one refuted by the *first* round's evidence.

**What Codex r3 actually checked, which is a different proposition.** Its note reads:
*"`writable in exactly ONE function`: grep confirms `sweepPolicyFrom` is the single real rule holder;
the rejecting test double is a deliberate contract violator."* That verifies *who holds the rule
today*. The sentence asserts *where the mistake can be made*. Both readings are available in the
prose, which is the defect.

**Fix — one clause, no code change.** At `:22` and `:57`: *"…writable in exactly one function **in
this repository** — the minimum, not zero. ⚠ `SweepPolicy` is exported and `RunnerOpts.sweepPolicy`
accepts an arbitrary one, so a caller who implements `run` themselves still owns both rules and no
test observes them; implement `SweepCursor` and use `sweepPolicyFrom` instead."* The dashboard
sentence needs *"anyone making it **there**"* → *"anyone making it in `sweepPolicyFrom`"*.

⚠ I am **not** recommending privatizing the seam on this branch. `tests/…:423`'s `rejecting` double
needs it, and closing it is a design change at round 3.

### Medium 2 — the durable record stops one round short, and the roadmap points at it as *"the full account"*

`docs/roadmap-to-launch.md:511` says: *"Full account in `docs/backlog.md` #140."*
`08ea36be` — the commit that made the **only behavioural change on this branch** — did not touch
`docs/backlog.md`. Verified: `git show --stat 08ea36be` lists `dashboard-entries`, `roadmap`, the
review doc, `worker-runner.ts`, the test file, and `worker/main.ts`. **No backlog.**

So row #140's status column ends at r2-Codex. It contains **no trace** of:

- **r2-Claude High 1** — the three-stage error handling was guarded by nothing; four mutations, four
  survivors; four cases added.
- **r2-Claude Medium 1** — the `due()` catch fail-dangerous → fail-open flip. That is the single
  operationally consequential fact about this branch: *a broken cadence check now sweeps on every
  poll instead of never sweeping again.* A reader reconciling #140 from the backlog would not learn
  it exists.

`grep` on the row for `sweeping anyway`, `fail-open`, `due = true`, `never ran again`, `0 sweeps`
returns nothing.

**This is r2 Medium 2's class, one round later, caused by the fold that fixed it.** r2 Medium 2 was
*"the roadmap was ticked with the refuted framing left intact"*; the fold corrected the roadmap and
left the document the roadmap delegates to behind.

**Fix:** two sentences appended to row #140 — the High 1 gap and its four cases, and the direction
flip with its measured numbers (0/100 before, 100/100 after, and that no shipped cursor can throw
today). ~5 minutes; it is the compaction-proof layer, per `docs/dev-process.md`.

---

## Low

### Low 1 — the same degradation, ten lines apart, gets opposite verdicts and only one of them is quantified

`worker-runner.ts:105-108`, the **commit** catch:

> *"…a persistently throwing commit never advances the window, so the gate degrades to per-poll
> sweeping: **the ~40,000 requests/day of egress this whole branch exists to remove, restored
> silently behind a log line.**"*

`worker-runner.ts:85-86`, the **due** catch, eighteen lines above:

> *"a broken cursor degrades to sweeping on EVERY poll — **costly, loud in the logs, and correct**."*

Measured, the two are the same event: probe 3 gives **30 sweeps / 30 polls**, probes 1–2 give
**100 sweeps / 100 polls**. Both are per-poll sweeping; at `POLL_MS = 2000` both are ~43,200
attempts/day. One is written up as the regression the branch exists to remove; the other as correct.
Both framings are defensible in isolation — the *direction* really is right and the cost really is
the branch's whole subject — but a reader comparing the two adjacent catches gets no signal that
they describe identical behaviour.

Also: `e6a449fe`'s message says **~43,200/day** (theoretical, `86400/2`) while the code says
**~40,000/day** (measured prod traffic, `79,800/2`). Both correct; neither says which kind of number
it is.

**Fix:** one clause at `:86` — *"…on EVERY poll: the same ~40,000 requests/day named in the commit
catch below. Loud and costly beats silent and broken, which is why this is the right direction and
not a cost-free one."*

### Low 2 — the honest scoping that made it into the commit message is half of the honest scoping the review gave

r2-Claude's Medium 1 scoped itself twice: **(a)** *"not introduced by the r2 fix"* and **(b)**
*"unreachable in production today: `makeSweepGate`'s `due()` is `now() - lastSweptAt` over
`performance.now()`, which does not throw."*

`08ea36be` carries **(a)** verbatim (*"⚠ Honest scoping, from the reviewer: this was NOT introduced
by r2"*). **(b) appears in no delivered document.** I grepped `worker-runner.ts`, `worker/main.ts`,
the test file, the backlog and the roadmap for `unreachable` / `cannot throw`: nothing.

It matters because the dashboard's plain-English half reads as a near-miss outage — *"would keep
treating it that way forever. Measured: a hundred checks in a row, zero cleanups, each one logging a
line that reads like everything is fine."* True of the seam; **no cursor this repo ships can throw**
(`() => true`, and monotonic-clock subtraction). The fix is prophylactic, which is fine, but a reader
should not have to derive that.

**Fix:** one clause — *"Unreachable with either shipped cursor (`performance.now()` arithmetic and
`() => true`); reachable through the exported `now` and `SweepPolicy` seams, which is why it is
guarded rather than left."*

### Low 3 — the round number disagrees with itself inside one dashboard entry

`docs/dashboard-entries.md:10478`'s human half opens *"**Third round** on the same small cleanup"*;
its own `<!--tech-->` half opens *"**r2 Claude:** 0 Blocking, 1 High, 2 Medium, 4 Low."* The review
file is `sweep-policy-run-fn-**r2**-claude.md`, and `check-review-rounds.py` pairs halves by that
`r<N>`. Two of three say r2.

Same drift upstream: the committed `docs/reviews/claude/sweep-policy-run-fn-r2-claude.md` process
table labels the previous round's findings `r2` and **its own** findings `r3`, so that table's round
column does not match its own filename. Harmless today; it will mislead whoever reconciles this
branch's rounds against the review-round gate.

### Low 4 — the `2,844 → 2,845` correction misattributes which entry carried the error

`:10515`: *"the suite delta for **the previous round** was 2,841 → 2,845…"*. That figure sits at
`:10422`, the end of the **first** #140 entry (the r1 fold) — two entries back. r2-Claude's Low 2
identified it correctly as *"end of the first #140 entry"*; the fold generalised it to "the previous
round".

**The numbers themselves are all correct** — I verified them independently:

| Claim | Verified |
|---|---|
| base `9e51d378` roadmap | **2841 unit / 275 suites** ✅ |
| `9936ea66` cadence file | 26 tests (master: 22) ⇒ **2845** ✅ |
| `e1ea7018` cadence file | 26 tests, no net change ⇒ **2845** ✅ |
| HEAD cadence file | 30 tests ⇒ **2849**, and `check-test-counts.py` agrees ✅ |
| `2,841 → 2,845`, `2,845 → 2,849` | both correct ✅ |
| entry 1's *"control restored → 26/26 green"* | correct for `9936ea66` — the file already held 26 there ✅ |

### Low 5 — the fix covers a cursor that **throws**, not a cursor that **misbehaves**; the comment does not say which

`:85` says, without qualification: *"a broken cursor degrades to sweeping on EVERY poll."*
Measured (probe 5): a cursor whose `due()` returns `undefined` produces **0 sweeps in 3 polls** —
it fails **closed**, i.e. straight back into the silent-death mode this round exists to remove. A
cursor returning `'yes'` sweeps every poll.

Honestly scoped: **`tsc` closes this for any TypeScript implementer** — `due(): boolean` rejects a
void or string return, and `tsc --noEmit` is in CI. The reachable population is a JS caller or an
`as unknown as` cast. So this is a **residual, not a defect** — but the comment's unqualified
"broken cursor" is wider than what the code does, and the instance/class distinction is one this
repo pays for repeatedly. **Fix:** *"a cursor that **throws**"*, three words.

---

## Answers to the five attack questions, explicitly

**1. Is the fail-open trade correct, stated honestly everywhere, and is there a third option?**

**Correct — and I'd pick it again.** The repo's own stated rule (`:117`, on `ALWAYS_SWEEP`) is
*"sweeping too often is cheap; never sweeping strands crashed jobs"*, and the failure it replaces is
the one `main.ts:70-73` singles out as catastrophic. Worth recording: **against `master` this is a
strict improvement in both directions.** `master`'s `runOnce` calls `opts.sweepPolicy?.due()`
**outside** its `try` (`git show origin/master:lib/job-queue/worker-runner.ts:73`), so a throwing
`due()` escaped `runOnce` entirely — 0 sweeps **and** 0 claims that poll. The three states are
`master` 0/0 → pre-fix 0 sweeps/100 claims → HEAD 100/100. Nothing states this and it is the
strongest single argument for the change.

**Honesty: Low 1 and Low 2.** Direction stated honestly; cost quantified in one of the two places it
applies and nowhere flagged as unreachable today.

**A third option exists and neither round considered it — a *bounded* fail-open.** Keep the
combinator's own backstop counter, e.g. `if (++consecutiveCursorFailures % 30 !== 1) { due = false }`,
so a broken cursor sweeps once every ~60s instead of every 2s: reclamation keeps working, cost stays
inside the branch's own budget, and the log stays loud. **I am not recommending it.** It adds state
to the one function the branch spent three rounds emptying of state, to defend a path no shipped
cursor can reach (Low 2). Recording it because the question deserves an answer, not because it
should be built.

**2. Any path where `let due = true` stays true when it should not?**

**No in-contract path.** Five exits enumerated and each checked: `due` is assigned unconditionally as
the *first* statement of the `try`, so it survives as `true` only when `cursor.due()` throws — which
is the intent — or when the cursor is malformed enough to `TypeError` (probe 6: 3/3 sweeps, 3/3
claims, 0 rejections — fail-open, as designed). Out of contract, JS truthiness applies in **both**
directions, and the interesting one is the *false* direction, not the true one — Low 5. There is no
re-entrancy hazard: `runWorkerLoop` awaits each `runOnce` and `due` is function-local.

**3. Are the four log-string assertions change detectors?**

**They are legitimate, and I measured the boundary Codex did not.** Three rewordings:

| Reword | Fires? |
|---|---|
| `'sweep cadence check failed'` → `'sweep cadence probe threw'` | **yes** (1 test) |
| `'sweepExpired failed'` → `'sweep_expired_leases call failed'` | **yes** (1 test) |
| `'(sweeping anyway)'` → `'(will sweep)'` — the parenthetical | **no — survives** |

That is the right shape. The assertions are anchored on the **subsystem name**, which is the thing
under test (r1 High 2's concrete cost was a diagnostic naming the wrong subsystem) and are blind to
the surrounding prose. They will fire on a rename of the subsystem — including the arguably *better*
`sweepExpired` → `sweep_expired_leases` — but that is a one-line test edit and the alternative is no
guard at all. **I agree with Codex.**

**4. Does `a gate whose CLOCK throws keeps sweeping rather than going quiet` exercise production code?**

**Yes — production code, non-production input, and that is the only reachable framing.** It calls the
shipped `makeSweepGate` and therefore the shipped `sweepPolicyFrom`; the sole substitution is the
`now` parameter, which is exported precisely so the cadence is testable. Both of the cursor's methods
route through it, so the case covers the `due()` throw *and* the subsequent `commit()` throw in one
run — which is why MX2 also dies on it.

**Is it enough? Yes, with the caveat in Low 2.** No production cursor can throw, so there is no
"more real" path to reach for; a case that waited for `performance.now()` to fail would never run.
The companion case at `:174` covers the same property directly on the combinator, so the property is
pinned at both the unit and the seam.

**5. P1–P5.** Re-run, all hold, table above. I did not take Codex's word on any of them; my P2a
count is **4**, not the 2 Codex reported, because it also kills
`a failing SWEEP is reported as a sweep failure` — a case that did not exist when Codex measured.

---

## What I checked and found clean — stating explicitly where I found nothing

- **The claim `"written exactly once, no implementation holds either"` HOLDS at HEAD** — fifth
  enumeration, and the first to include the four new tests. Every `SweepPolicy` value in the repo:
  `sweepPolicyFrom` itself; `ALWAYS_SWEEP` (`:122`); `makeSweepGate` (`main.ts:107`); the `policy()`
  double (`tests:298`); the `rejecting` double (`tests:425`, hand-rolled, holds neither rule, exists
  to break the contract). The four cases added this round all construct **cursors**, not policies, so
  they add no copy. No `app/`, `components/` or `scripts/` file mentions any of these symbols.
  **I could not refute this half.**
- **`"restores master's single-copy property"` is accurate.** I read `master`'s `worker-runner.ts`:
  both rules written once in `runOnce`, `due`/`onSwept` dumb. HEAD: both written once in
  `sweepPolicyFrom`, every implementation dumb. True.
- **`"fails 3 tests"` is exact** — P1a, the three named at `:58-60`, verbatim and in that set.
  Verified at HEAD; the count moved from 2 for the reason r2 Low 1 gave.
- **`"0 sweeps across 100 polls"`** — reproduced by mutating HEAD back to the pre-fix direction and
  re-running probe 1: **0 sweeps, 100 claims**.
- **`"30 sweeps in 30 polls"`** — reproduced exactly (probe 3).
- **`"Two tests, one of them through the shipped `makeSweepGate(..., now)` seam"`** — MA kills exactly
  two, and one of them is the seam case. Exact.
- **`"Four cases added; all four mutations now die, control green"`** — MX1/MX2/MX3/MX4 all die;
  control 30/30 re-proved after each.
- **`"26/26 green each time"` in `08ea36be`** — correct for the tree r2 measured (`e1ea7018`, 26
  tests). Not stale: the file is 30 now because those four cases were added by that same commit.
- **All four commit messages are accurate for the trees they describe.** `9936ea66`: 2845 ✅,
  "fails 2 tests" ✅ (26 tests at that tree). `e1ea7018`: 2845 ✅; its *"CORRECTED EVERYWHERE IT WAS
  STATED"* was false and `08ea36be` says so in as many words — correctly handled as append-only
  history. `08ea36be`: every number checked above; `"tsc clean; 2849 unit / 275 suites; all gates
  green"` ✅ independently re-run. `e6a449fe`: an accurate report of what Codex r3 said; its
  ~43,200/day arithmetic is right (`86400 / POLL_MS=2000`).
- **`e6a449fe`'s framing "It verified rather than accepted every number"** is true of the numbers.
  It lists `'writable in exactly ONE function'` among them, which is not a number and was verified
  under a different reading — Medium 1.
- **The roadmap row** now carries the honest bound and the *"NOT 'removes a finding by construction'"*
  retraction. r2 Medium 2 folded correctly.
- **`worker/main.ts:85-88`** now credits `commit()` rather than `run` for the clock re-sample. r2
  Low 3 folded correctly, and the re-sample really is at `main.ts:112`.
- **`tests/…:131`** now says the mutation fails **3** tests. r2 Low 1 folded correctly, and it is the
  measured number.
- **`worker-runner.ts:105-108`** now distinguishes fail-safe-for-reclamation from not-fail-safe-for-cost.
  r2 Low 4 folded correctly.
- **The suite is green in full** — 2849/2849, 275 suites, `tsc` clean, and every doc gate rc=0. The
  only `check-backlog-closure` warn is #117, pre-existing and unrelated.
- **The diff touches nothing outside the worker.** 8 files: two source, one test, five docs/review
  artefacts. No schema, migration, API route or client code.
- **`ALWAYS_SWEEP` is still stateless and still hoisting-safe**, and N9 shows the property survives
  even if someone rebuilds it by hand.
- **Backlog #139** (the SIGTERM/attempt-accounting 🔴) is correctly **not** folded here; it is
  pre-existing on master and explicitly out of scope by the reviewer's own disposition.

---

## Process: thrashing or prose floor? — **PROSE FLOOR.** Do not arm Phase 6

r2's process note argued the thrashing condition was armed on its letter. Round 3 is the evidence
that settles it, and it settles it the other way.

| Round | Blocking | High | Medium | Low | Findings against **code** |
|---|---|---|---|---|---|
| r1 | 1 (Codex) | 2 | 2 | 5 | yes — the design, and an unguarded clause |
| r2 | 0 | 1 | 2 | 4 | yes — 4 surviving mutations + a fail-dangerous direction |
| **r3** | **0** | **0** | **2** | **5** | **none — 21 mutations, 0 survivors** |

Per-finding, this round:

| Finding | From the previous round's fix? | Subject |
|---|---|---|
| Medium 1 | No — **carried from r1**, never applied | a sentence |
| Medium 2 | Yes — the fold omitted one document | a document |
| Low 1 | Yes — r2 Low 4's fix quantified one catch, not its neighbour | a sentence |
| Low 2 | Yes — the fold dropped half the review's scoping | a sentence |
| Low 3, 4 | Yes — fold artefacts | round labels, an attribution |
| Low 5 | No — carried, and closed by `tsc` | a sentence |

`docs/review-method.md`'s test is *can a redesign remove it?* For r2's High 1 and Medium 1 the answer
was **yes** (give the combinator the state instead of a cursor). **For every finding here the answer
is no** — a redesign does not fix a missing clause in a docstring or a backlog row that is one round
stale. The code stopped moving; only the prose is still being corrected, and the corrections are
getting smaller. That is the documented signal to **go build**, not to convene an architecture review.

⚠ For the record against my own conclusion: the streak of *"every round finds a defect in the
previous round's fix"* technically continues — four of my seven findings are fold artefacts. What
ends is the part that matters: **no round-3 finding is reachable by a mutation, and none changes what
the worker does.**

---

## Recommendation and merge readiness

**READY: the CODE is ready. The RECORD is not — two edits, both documentation, neither touching a
line of TypeScript.** So my answer to *"is this branch ready to merge?"* is **no, not as-is; yes
after two paragraphs.**

1. **Medium 1** — add the scoping clause at `worker-runner.ts:22` and `:57` (and the same at
   `tests:129`, `backlog.md:168`, `roadmap:509`, `dashboard:10372`). This is Codex's r1 fix (a),
   fifteen words, outstanding since round 1.
2. **Medium 2** — bring `docs/backlog.md` row #140 up to `08ea36be`. The roadmap calls it the full
   account; today it omits the branch's only behavioural change.
3. **Lows 1–5** are worth taking in the same pass — all are one clause each — but none of them would
   stop me merging.

⛔ **Do not open round 4 for these.** Both Mediums are prose, both fixes are quoted verbatim above,
and a fourth round would be measuring the same 34 lines for the fourth time against a suite that
just killed 21 of 21 mutations. Fold, re-run the gates, merge.

**What would change my mind to "not ready" on the code:** a production path by which `cursor.due()`
or `cursor.commit()` can throw (I found none — both shipped cursors are total), or a caller in this
repo supplying its own `SweepPolicy` (there is none — `runWorkerLoop` is the only non-test caller and
it uses `makeSweepGate`). If either appeared, Medium 1 would become a High and the bounded fail-open
of question 1 would stop being hypothetical.

**Next action:** hand Medium 1 and Medium 2 to the author as a fold-and-merge, not a review round.

---

*Reviewer: Claude (adversarial half, round 3). Subject frozen at `e6a449fe`; it did not move.
`git status --porcelain` at completion: `?? docs/reviews/claude/sweep-policy-run-fn-r3-claude.md` —
this file only. All 21 mutations reverted with `git checkout --`; the probe file deleted; control
re-verified 30/30 green and the full suite 2849/2849 after cleanup.*
