# Round 1 — `decision-card-soundness` — coordinator

```yaml
round: 1
fixes_nontrivial: true
subject: decision-card-soundness
halves:
  codex: ran
  claude: ran
findings:
  - {id: H1, severity: High, aim: deliverable, fix_induced: false, component: cost-evidence, disposition: fixed}
  - {id: H2, severity: Medium, aim: deliverable, fix_induced: false, component: escape-grammar, disposition: fixed}
  - {id: H3, severity: High, aim: deliverable, fix_induced: false, component: caller-and-record, disposition: filed}
  - {id: H4, severity: High, aim: deliverable, fix_induced: false, component: calibration-claims, disposition: fixed}
  - {id: H5, severity: High, aim: deliverable, fix_induced: false, component: prior-art, disposition: filed}
  - {id: H6, severity: High, aim: deliverable, fix_induced: false, component: escape-grammar, disposition: filed}
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: true, component: calibration-claims, disposition: fixed}
```

⚠ **The Claude half was dispatched LATE, after the Codex half and after the user asked why it had
not run.** It is recorded as `ran` because it did; the lateness is recorded here because the
sequencing was wrong — round 1's protocol is both halves concurrently.

⛔ **AND THE COORDINATOR'S FIRST EXPLANATION OF THAT GAP WAS FALSE.** Asked why, I produced a
documentation-conflict story — that `dev-process.md`'s Phase 1 says *"adversarial review"* which
`plugins.md` supposedly defines as the Codex half. **Refuted in two greps:** `plugins.md:143,151`
themselves say *"a Claude adversarial review"*, the cited table sits under *"Code Review (dual review
per task)"*, and **72 Claude review documents title themselves "adversarial review."** There was no
conflict. The citations were real and the inference was wrong, in the direction that excused the
omission. Caught by the user's memory — *"I don't remember this question has been raised"* — not by
any check.

## ⭐ The two halves found DISJOINT surfaces, which is the case for running both

| Half | Found |
|---|---|
| **Codex** | numeric: reproduced the defect, the calibration and the registry rejection; caught a cost range that excluded its own largest member |
| **Claude** | **design: four Highs, none numeric** — every one a thing the spec fails to specify or a prior artefact it missed |

**Zero overlap.** This repo's recorded measurement — that the halves produce no overlapping findings
— held again, and the half that was almost skipped is the one that found the structural problems.

## What survives

The **measured defect reproduces** (both halves, independently) and the mechanism's **shape** is
right. What does not survive is the **framing** and the **scope**.

## The four Highs — recorded as OPEN in the spec, not folded away

1. **No caller, and the record cannot tell *ran* from *never ran*.** `check-review-decision.py:27-31`
   declares `NO-CALLER:` and its docstring already names the remedy — *"making this a step nobody can
   skip"*. Measured: **zero** of `velocity-doc-consistency`'s four round documents mention the card,
   against 2 and 4 for the contrast subjects. The spec's own falsifier presupposes a call that does
   not exist.
2. **The calibration understated false positives.** On `peer-sites` the trigger fires at r2 and r3
   and the refusal lands at **r4, after** the #134 split; on `velocity-177` the refusal is at r2 and
   the trigger fires correctly at r3. **2 of 3 refused subjects needed no refusal.** ⭐ A one-clause
   fix — *do not refuse if the trigger fired on the previous pair* — removes one for free.
3. **Backlog #136 is the filed design task for this loop**, and says *"make the OUTPUT A ROUTE, not a
   stop/go"*, carrying the user's caution **"COST IS NOT THE OBJECTIVE"**. This spec proposes a
   stop/go. Unresolved.
4. **The escape is unreadable as specified.** Removing component names moved identification onto a
   placement rule the spec never states; the natural implementation would let **one declaration
   silence every later refusal permanently**. And the reader does not exist — `parse_header`
   discards prose, and `REVIEW GAP:`'s reader is a different script over a different file set.

## Verdict

⛔ **NOT GATE-READY.** The spec's status is changed to say so. Findings 1, 3 and 4 are **filed as
open design questions inside the spec**, because folding them would mean deciding three design
questions in a fold — which is the move this whole line of work exists to prevent.
