---
name: a-filed-finding-s-proposed-fix-is-a-hypothesis
description: "FIRES-WHEN: about to implement the fix a backlog row or review finding proposes — A backlog row's proposed SHAPE is a hypothesis, not a spec — measured 2026-09-09: row #98's own rule would have false-fired on 10 of 18, the exact failure the same row warned against"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: e55c5ea7-de4d-4785-ae8f-189369f0e701
  modified: 2026-09-13T05:56:01.965Z
---

⭐ **MEASURE A FILED ROW'S PROPOSED RULE AGAINST THE REAL CORPUS BEFORE BUILDING IT.** The
diagnosis in a well-written finding is usually right; the **fix it proposes** is a guess made
before anyone looked at the data.

**Measured 2026-09-09, backlog #98.** The row proposed: *"walk merged commits, extract the item
ids their messages name, and refuse when an id's row carries no closure marker."* Over **1,497**
commits on the default branch:

| rule | ids matched | would fire on |
|---|---|---|
| **any** occurrence of `(backlog #N)` — as filed | 18 | **10** ← 56% false |
| `(backlog #N)` at the **subject TAIL** | 7 | **1** ← a true positive |

The token means *this commit TOUCHED item N*, not *closed it*: `(backlog #17)` is a large open
design item, `docs(backlog #53): …` is a FILING commit.

⚠ **The row itself warned against exactly this** — *"a false positive here is worse than the gap,
because it would train the reader to skip the gate"* — and then specified the rule that produces
it. That is the point: careful authorship does not protect the proposed mechanism, because the
author was reasoning about a corpus they had not counted.

**Why:** building the filed shape would have shipped a guard firing falsely more than half the
time, which is the documented way a gate gets ignored and then disabled — at which point it is
worse than none, because its presence implies coverage.

**How to apply:** treat the row's OBSERVATION and SEVERITY as evidence, and its SHAPE as a
hypothesis. Before writing the guard, run the proposed predicate over the actual history/corpus
and count both arms — how many it matches, and how many of those are true. If the false rate is
material, narrow it and record BOTH numbers at the code, so the next reader knows the obvious
version was tried and rejected rather than never considered.

⭐ **Second lesson from the same build: A CASE THAT DIES FROM THE DEFECT IT GUARDS IS WEAKER THAN
ONE THAT REPORTS IT.** A mutation removing a crash-preventing guard made the parser raise, which
killed the whole suite — so the harness reported *"matched 0 red cases"* and could not attribute
the death to any case. It was caught, but unattributably. The fix is not to drop the mutation:
wrap the call so the raise becomes a comparable value, and the case becomes the named observer of
its own defect instead of a casualty of it.

⟳ **IT APPLIES TO A REVIEW FINDING TOO, AND THAT COST TWO ROUNDS ON ONE BRANCH (2026-09-12, PR
#296).** Both times the finding was measured and correct, and the fix beside it was reasoned and
wrong — and in both cases the only thing that revealed it was *running the proposed fix*:

| round | proposed fix | why it fails |
|---|---|---|
| r1 LOW 1 | *"restore `drop index if exists` to the cleanup block"* | that block executes **after** the assertion it was meant to protect — re-ran the sabotage, still two reds |
| r2 LOW 1 | *"capture the best-effort undo's exit status"* | `drop … if exists <wrong-name>` **succeeds**, so the status is 0 while the object is still there |

The r2 reviewer labelled its own second bullet a partial closer, which is the honest version — and
still, the fix that actually worked was a different observation entirely (read the **gate**, not the
exit status). ⚠ A review finding arrives with more authority than a backlog row: it names file:line,
it was measured, and the reviewer just proved it. None of that transfers to the sentence after
*"Fix."* — that sentence is the one part of the review that was never executed.

**How to apply:** when implementing a reviewer's fix, run its falsifier against the fix BEFORE
believing it, exactly as you would for the finding. If the fix turns out weaker than the finding, say
so in the response with the measurement — the reviewer is usually right that something is broken and
wrong about what closes it, and only the second half needs correcting.

Related: [[check-the-assumption-not-just-the-code]] — same discipline one level earlier, on the
design's premise rather than on a filed fix. [[a-measurement-is-only-as-good-as-its-corpus]] ·
[[fixing-a-premise-is-not-covering-the-branch]] · [[a-convention-catches-what-you-read]] ·
[[a-stated-bound-outlives-its-hole]]
