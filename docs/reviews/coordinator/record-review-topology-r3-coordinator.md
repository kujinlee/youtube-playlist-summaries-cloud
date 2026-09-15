# record-review-topology — round 3, coordinator adjudication

**REVIEW GAP:** claude — not invoked; built by a worker fork that cannot spawn subagents. All three
rounds are Codex-only and **the Claude half is owed before merge**.

## Round 3 — Codex, `gpt-5.5`, against the UNCOMMITTED round-2 fixes

`docs/reviews/codex/record-review-topology-r3-codex.md` · verdict
`docs/reviews/verdicts/record-review-topology-r3-codex.verdict.json` (`gate_ran: true`).
**NOT CONVERGED**, but **no Blocking** — 1 High, 3 Medium, 1 Low.

⚠ This round was dispatched against a working tree held deliberately uncommitted, which is step 5
of the protocol being used rather than described. The reviewer was told so in its brief.

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | High | A **stacked** parent's `REVIEW GAP: codex` clears the child's missing verdict. Prose said "of this branch"; code says "added anywhere in `base..HEAD`" | **ACCEPTED, PROSE CORRECTED** — this is the same contract `verdict()` already states for the recorded-review question six lines above it. Closing it needs the true parent, which CI does not know; half a mechanism would be worse. The pass now NAMES the document, so a stacked pass is visible rather than indistinguishable |
| 2 | Medium | A reviewed **deletion** was credited to nobody: all-zero destinations were skipped, so the careful path failed for deleting code | **FIXED** — the zero entry `git diff-index` itself writes is recorded, and a path absent from HEAD compares equal to it. One spelling, and it is git's |
| 3 | Medium | `add -A` failing on one out-of-cone path under a sparse checkout discarded **every** entry already staged | **FIXED** — best effort; a partial record still fails closed, an empty one throws away evidence |
| 4 | Medium | A non-deterministic `clean` filter makes the recorded and final entries differ for the same bytes | **ACCEPTED** — such a filter breaks git itself (the file is permanently dirty to `git status`). Fails closed. Plain `autocrlf` was verified by the reviewer to match |
| 5 | Low | The dashboard entry's counts did not reconcile with the review records | **FIXED** — recounted from the rounds: sixteen findings, thirteen fixed, three accepted |

## Why this is FIX and not REDESIGN

`review-method.md`'s stop condition escalates to redesign when two consecutive rounds produce
findings caused by the previous round's fixes. r2 and r3 both did. **The test it names is not the
count — it is "can a redesign remove it?"** Applied one finding at a time:

- the stacked-parent gap survives every reshaping, because the information CI lacks is the true
  parent, not the rule's shape;
- a reviewed deletion and a sparse-checkout `add -A` failure are **branches of tree state** the rule
  governs but does not own — the same branch-coverage shape that section already documents, whose
  remedy is an exhaustiveness pass, not a new mechanism;
- the filter case is a property of git, not of this design.

The redesign that WAS owed already happened, in r2: the mechanism changed from "reconstruct what the
reviewer saw" to "ask git what it would store". r3's findings are the exhaustiveness pass over that
mechanism's branches. Recorded here per the same section's rule that an override is allowed and a
silent override is not — **this fires to REDESIGN if r4 produces a finding that a different shape
would dissolve.**

## One finding of my own, refuted by the reviewer

While r3 was in flight I noticed the `-z` raw parse walks fields two at a time and suspected a
rename or unmerged record could desynchronise it. r3 tried to construct exactly that and reported
it could not: copy records with two paths appeared only with detection options the code does not
pass. **No change made.** A premise I reasoned about lost to one somebody ran — and editing while a
round was in flight would have made that round stale, which is the rule this branch adds.
