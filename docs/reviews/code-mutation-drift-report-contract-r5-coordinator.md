# Code review r5 — coordinator adjudication

**Subject:** commit `5fc92b73` (the round-4 fold), `scripts/check-plan-code.py` +
`scripts/mutations/check-plan-code.json`. **Date:** 2026-09-04.

**Both halves ran. Both returned NOT CONVERGED.** Neither verdict was taken on trust; every
load-bearing claim below was re-executed by the coordinator.

| half | verdict | headline |
|---|---|---|
| Codex (`gpt-5.5`) | NOT CONVERGED | High: `control_is_green` accepts `0/1 passed` |
| Claude | NOT CONVERGED | High: the new coverage defends DELETION, not WEAKENING — 4 weakenings survive at 183/183 |

## ⚠ The Codex half ran DEGRADED, and the cause was the brief, not the reviewer

Its own report says:

> NOT RUN: I did not run `--self-test` or `--mutate .` because this review's output contract said
> not to create, modify, or delete anything on disk.

My brief said *"write no file. Do not create, modify or delete anything on disk."* The second
sentence was aimed at the review artifact; Codex correctly read it as forbidding temp files, and
therefore **reviewed by reading**. That is the documented downgraded-gate failure — a reviewer that
cannot execute is a downgraded gate that still reports success — introduced, with some irony, in
the round whose purpose was fixing an output-contract defect (#222).

Treat the Codex half of r5 as a READING review. It was re-dispatched with a corrected brief
(`codex-code-r5b`) that separates the two prohibitions: no review artifact, no writes inside the
repo; temp files outside the repo expected and encouraged.

**Corrected brief-writing rule, so this does not recur:** state the prohibition as *"do not write
your review to a file, and do not modify the repository working tree"* — never as *"do not touch
disk"*, which disarms the reviewer's ability to verify anything.

## ADJUDICATION — the halves DISAGREED on `control_is_green`, and both were partly right

Codex: High. Claude: Low. Executed by the coordinator rather than deciding by reputation:

```
verdicts_are_trustworthy([], 0, True)   = True     <- Codex's route: REAL
verdicts_are_trustworthy([], 0, False)  = False
control_is_green(0, '0/0 passed')       = True     <- a suite that ran ZERO cases
control_is_green(0, '0/1 passed')       = True     <- an explicitly FAILING ratio
```

* **Codex is right** that a plan declaring **zero** mutations, with a control that merely *looks*
  green, produces `trustworthy = True` — a "measured" verdict over a run that measured nothing.
  Claude's "I found no route to a false catch" missed this path.
* **Claude is right** that when mutations **are** declared, a zero-case suite lets every mutation
  survive, so the run reports survivors and exits 1 — loud, fail-closed. Codex's High overstated
  the blast radius by not bounding it.

**Settled severity: MEDIUM.** The false-verdict route is real but needs *both* a zero-mutation plan
and a suite exiting 0 while printing a failing ratio. It is the same root as H1 — the predicate is
under-asserted — and the fix is shared: assert the property, not the mechanism.

This is the fourth recorded instance of *reviewers split → the disagreement was the finding*. The
new wrinkle: previously the finding-reviewer was right and the clean one wrong. Here **each half
was right about a different path**, so "pick the reviewer who found something" would also have
produced a wrong severity.

## The round-5 finding that matters most (Claude H1), verified

r4's own sentence was *"there are TWO printers and round 3 covered the one CI never runs."*
r5's is: **there are THREE refusal paths through the printer r4 fixed, and r4 covered one.**

`grep -n 'main(\["--mutate"' scripts/check-plan-code.py` → exactly one hit (`:2225`), driving the
after-control path. The before-control-failure path and the total-shortfall path have no case at
all. Four *weakening* mutations — as opposed to the *deleting* mutations the manifest contains —
all survive at `183/183`.

⚠ **M-A is not contrived:** it replaces `:2459`'s gate with `:2506`'s gate verbatim, i.e. it makes
the two printers share one predicate. That is exactly the de-duplication
`scripts/check-vocabulary-collisions.py` exists to encourage. **Doing the obviously-good cleanup
reintroduces r4's Blocking, and CI stays green.**

## Phase 6's prediction: CONFIRMED, and it should now be scored rather than re-argued

Phase 6 architecture review #7 predicted round 5 would find an *eighth consumer* rather than
terminate. It did — one level in rather than one out. This is the seventh consecutive round whose
defect sits inside the previous round's fix. The pattern is not converging by iteration, and
`dev-process.md`'s own rule (**four non-converging rounds fires Phase 6**) has been met twice over
on this artifact.

**Coordinator recommendation, for the human:** do NOT open round 6 on the same axis. The repeated
finding is structural — coverage is expressed as *deletion* mutations against *specific text
anchors*, which by construction cannot see a weakening. Another round finds a ninth path.

## Not folded

No fix is applied in this commit. The findings are recorded; the fold is a separate slice, and
which axis it takes is a decision for the human given the Phase 6 recommendation above.

---

# ADDENDUM — the re-dispatched Codex half (`r5b`) came back, and it changes two things

## 1. The brief correction WORKED, and it paid for itself

The reading-only run reported `NOT RUN` for both suites. The re-run, with the corrected brief,
executed:

```
--self-test                 183/183 passed
--mutate .                  7 file(s), 176 mutation(s), 0 survivor(s)
```

plus five targeted temp-copy probes, each with a real count:

```
if ev["trustworthy"]: -> if True:              red, 181/183
return rc == 0 and "passed" in out -> rc == 0  red, 179/183
NOT RUN if untrustworthy -> if False           red, 180/183
header appends ", caught {caught}"             red, 182/183
DELETE the corrected neutral header line       GREEN, 183/183   <- the new finding
```

**It found a Medium the reading run could not have found**, because finding it required deleting a
line and observing that nothing went red. That is the concrete cost of a degraded gate, measured
rather than argued: same reviewer, same model, same scope, one sentence of brief difference.

## 2. NEW — Medium: a vacuous absence-assertion (Codex r5b)

`scripts/check-plan-code.py:2305-2306`:

```python
case("...and the word `caught` appears NOWHERE under that refusal",
     "caught" in evidence(_ev_ac), False)
```

Deleting the neutral replacement line at `:1033` (`mutation entries recorded: …`) leaves the suite
at **183/183**. The case proves a forbidden word is *absent*; it does not prove the replacement line
is *present*. A refusal that printed nothing at all would satisfy it.

This is the **vacuous absence-assertion** class this project has recorded before. It is the same
root as Claude's H1 — *assert the property, not the mechanism* — and both fixes are the same shape.

**Consumer enumeration agrees between the halves:** producers at `:785`, `:985`; live consumers at
`:1030`, `:2459`, `:2506`. Neither half found a fourth. Two independent greps concurring is the
strongest evidence available here that the "eighth consumer" is *not* a fourth consumer — it is
under-asserted coverage of the three that exist.

## 3. ⚠ THE INTRUSION DETECTOR RAISED A FALSE ACCUSATION — new finding, not in either half

The wrapper reported:

```
⚠ THE AGENT WROTE BEHIND THE WRAPPER:
    docs/reviews/code-mutation-drift-report-contract-r5-claude.md — CREATED by the agent
    docs/reviews/code-mutation-drift-report-contract-r5-coordinator.md — CREATED by the agent
```

**Both claims are false.** `git status --porcelain` was clean apart from the new verdict file, and
`git log` attributes both files to commit `8c8179be`. Timestamps:

| time | event |
|---|---|
| ~08:03 | `r5b` dispatched; `dir_snapshot(docs/reviews/)` taken |
| 08:09:15 | the **Claude** reviewer writes its review there |
| 08:11:31 | the **coordinator** writes this file there |
| ~08:14 | `r5b` ends, diffs the directory, attributes both to Codex |

`dir_snapshot` compares a before/after listing of one directory. It therefore cannot distinguish
*"the agent wrote this"* from *"this directory changed during the window"* — and **dual review
guarantees a concurrent writer by construction**, since both halves are told to write into
`docs/reviews/`.

Severity: it is fail-LOUD and did not corrupt anything, and the capture was still valid. But it
writes the false accusation into `verdicts/codex-code-r5b.verdict.json`, which **CI reads**, and a
detector that cries wolf is one people learn to skip — the same "warning becomes noise" failure the
warn-only decision elsewhere is being careful about.

Same class as the recorded incident where two reviewers sharing one Postgres produced a FALSE
BLOCKING: *re-measure alone before believing a red on a shared resource.*

**Shape of a fix (not decided, not started):** attribute by writer rather than by window — e.g.
snapshot immediately before and after the `codex exec` child only, or record the wrapper's own
expected outputs and the mtimes it observed, or give each half its own output directory so the two
reviewers do not share a watched namespace. The last is probably cheapest and also removes the
stem-collision hazard that `--out` already had to work around.

## Revised recommendation to the human — unchanged in direction, firmer in evidence

Round 5 now has **three** independent findings pointing at one root: coverage asserts *mechanisms*
(this exact line, deleted) rather than *properties* (the refusal prints no tally, whatever its
wording). Claude's H1, Codex's Medium, and Codex's Low are the same defect at three sites.

**Do not open round 6 on this axis.** Fix the axis instead.
