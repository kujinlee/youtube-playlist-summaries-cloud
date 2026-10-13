# Round 11 — THRASHING OR PROSE FLOOR? The arming question, answered with per-finding evidence

`docs/dev-process.md` requires this question to be answered in the round document once the
condition is in sight, and **not** answered by a round count: *"It fires when two consecutive
rounds carry findings caused by the previous round's own fix, in one component."*

## Verdict: THRASHING, in one component, and the redesign that removes the class has been taken

**Component:** `scripts/check-plan-code.py`'s unattributable-kill branch — the `if not fails` arm
of `run_mutations`, plus the helper it calls.

## Per-finding evidence — every finding names the fix that caused it

| round / half | finding | caused by |
|---|---|---|
| r11 Codex | **H1** — a multi-line exception message pushes the heading out of `diagnostic_tail`'s 400 chars even with an EMPTY stdout, so *"the next occurrence will name it"* was false as shipped | `6b217be9`, this session's fix for the original defect |
| r11 Codex | L2 — "18 `[FAIL]` lines" asserted in two comments | `6b217be9`, which withdrew that figure elsewhere in the same commit |
| CI shard 5 | **a SURVIVOR** — printing the child's traceback made a PRE-EXISTING case unfalsifiable, because a traceback quotes the source line the case asserted | `6b217be9` |
| r11 Claude | **H1** — naming ONE heading as the killer is false at interpreter shutdown; four real children displaced the fatal exception, and the flooding composite left the real killer nowhere | `c7bf43df`, the fold of Codex H1 |
| r11 Claude | **H2** — two of the three worlds the fold introduced have no falsifier | `c7bf43df` |
| r11 Claude | M1 — "two entries" | `c7bf43df`, which was itself correcting the previous figure on that subject |

That is **two consecutive folds, each producing Highs about the previous fold, in one component.**
The condition is met on its own terms, and it is not a count: the handoff records the same shape
across rounds 1–10 (*"each fix CREATED the next instance"*).

## It is not a prose floor

A prose floor looks like findings whose character stays constant while severity drifts — the
2026-08-28 measurement where Blocking totals ran 4→5→4 over improving prose. These findings are
not prose. Each is a MEASURED behaviour of delivered code, each came with a reproduction, and each
changed the shipped artifact: a false attribution over real children, an unfalsifiable arm proved
by mutating a 260-case mirror, a survivor found by CI.

## The test dev-process names: *can a redesign remove it?* — YES, and here it is

Every finding in this lineage is the same defect wearing a different coat: **the harness made a
causal claim about text it cannot interpret.**

* `caught = rc == 1` claimed "the suite failed a case" where a traceback also exits 1.
* The message claimed *"a report-format defect in `<file>`"*.
* The fold claimed *"the child DIED with `<heading>`"*.

Each fix moved the claim rather than removing it, which is why each fix produced the next finding.
The redesign is to **stop claiming**: `exception_headings` names every heading in order, flags the
ones CPython itself ignored, and the message states that it does NOT know which killed the child.
That is taken, in this round.

⚠ **AND THE HALF OF THE REDESIGN THAT IS NOT MINE TO TAKE.** The same principle applied one layer
out is backlog **#270's option ②**: a suite that produced no tally line and no `[FAIL]` never
reported, which is a CANNOT RUN like `rc == 2` and not a kill. That removes the remaining causal
claim — `caught` — at its source. It changes what the sweep LABELS a kill (not the pass/fail: such
an entry already carries `attributed: false`), so it is a decision about the instrument's contract
and it is filed, not taken.

## Consequence for Phase 6

Thrashing is the arming condition for the architecture review (`dev-process.md` Phase 6), so it is
**armed and owed** — as the round-10 handoff already recorded. Sequencing it is the owner's
decision, and it is one of the two they have reserved alongside the merge. This document is the
record that the condition fired and was answered rather than passed over.

⛔ **NOT CONVERGED.** Round 11: Codex 1 High + 2 Medium + 2 Low; Claude 2 High + 1 Medium + 3 Low.
Zero of two consecutive clean rounds; there have been zero in eleven.
