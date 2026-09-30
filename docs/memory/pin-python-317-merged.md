---
name: pin-python-317-merged
description: "FIRES-WHEN: citing PR #317 or the Python interpreter pin — ⭐⭐ PR #317 MERGED e7ed8c1a after TEN defects in ONE function across 7 rounds — all one root cause. ⭐ My probes missed the class twice by testing the CONTAINER's shape not its CONTENTS. ⭐ A fix can be right and land at the WRONG LAYER (twice). A pre-committed falsifier FIRED and showed I scoped the class one level too low. Architecture review = backlog #153"
metadata: 
  node_type: memory
  type: project
  originSessionId: b3d559c1-6b4c-49e1-81af-8ac588f0b7d8
  modified: 2026-09-21T20:14:16.777Z
---

**MERGED 2026-09-21 as `e7ed8c1a`.** `scripts/check-python-pin.py` — every CI job pins the Python
interpreter, the pins agree, and the pin took effect. Born because CI and a dev machine disagreed
about the SAME COMMIT (`723` vs `722` attributed mutations, PR #315).

The handoff said it "owes a review round". It owed **ten defect fixes** and was 11 commits behind.

## ⭐⭐ TEN DEFECTS, ONE ROOT CAUSE — the guard reads YAML by SCANNING LINES

So anything *shaped* like a step is a step. Each round taught it one more legal construct:

| round | defect | direction |
|---|---|---|
| r1 | any pin-shaped line in the file counted | false green |
| r2 codex | narrowed to "inside the step" | false green |
| r2 claude | narrowed to the step's `with:` — **a `- name:` step hid its pin** (62 of 70 steps here are written that way) | MISS |
| r3 coord+codex | a `uses:` inside a heredoc declared a step | false green |
| r3 codex | a **DASH** inside a block scalar manufactured a phantom step | false green |
| r3 claude | `_steps` **silently DROPPED LINES** after a nested list — a real pin vanished | MISS |
| r3 coord | a **COMMENT** at the dash indent ended the step | MISS |
| r4 codex | `strategy.matrix.include` read as a step | false green |
| r5 BOTH halves independently | a matrix **dimension named `steps`** | false green |
| r5 codex | `steps: &anchor` / `!!tag` read as UNPINNED | MISS (regression I caused) |
| r6 codex | ⭐ **`steps` is a legal JOB ID** — the job key at indent 2 beat the real list at 4, inverting the shallowest-`steps:` invariant | false green |

## ⭐⭐ THE THREE LESSONS THAT TRANSFER

**1. I TESTED THE SHAPE OF THE CONTAINER, NEVER ITS CONTENTS — twice.** I probed
`strategy.matrix` in r4-prep AND r5-prep and passed both; my fixtures used a dimension holding a
list of **SCALARS**. Every real defect used a list of **MAPPINGS**, which is what a step looks
like. Two rounds of my own probing could not have found the class.
⭐ **When probing a container, vary what is INSIDE it, not just the container's name/nesting.**

**2. A FIX CAN BE RIGHT AND LAND AT THE WRONG LAYER. Twice, same session:**
  * the block-scalar mask applied to each step's body **after** `_steps()` split — a dash inside a
    heredoc is consumed BY the split, so the mask never ran. Moved INTO the splitter.
  * the job-key exclusion applied to whole FILES and not to job BLOCKS — and `unpinned_jobs` calls
    `declared_pins` on **blocks**. Fixed by making `job_blocks` return the job's BODY.
⭐ **"Which lines are structure" is prior to "which step owns a line."** Ask which question your
fix answers and whether something earlier already answered it wrongly.
⭐ And: **write the case for the CONSEQUENCE beside the case for the cause.** The cause-only case
passed while the guard was still broken where it counted.

**3. ⭐ A PRE-COMMITTED FALSIFIER FIRED, AND IT WAS RIGHT.** At the 4th defect I read
`dev-process.md`'s THRASHING condition as met, answered `review-method.md`'s *can a redesign remove
it?* with YES, redesigned instead of convening the architecture review, and pre-committed: *a
fourth finding in r3 means the redesign failed*. r3 produced a fourth AND a fifth. The reviewer's
diagnosis is the keeper:

> *"You scoped the class as STEP IDENTIFICATION, and a redesign does remove that. The class is one
> level up, and your own docstring states it exactly: this guard reads YAML by scanning lines."*

⭐ **Answer "can a redesign remove it?" against the WIDEST class the evidence supports, not the one
your current fix addresses.** See [[a-retreat-you-author-for-yourself-is-not-a-gate]].

## Process facts worth keeping

* ⭐ **Both halves found the r5 matrix-dimension defect INDEPENDENTLY, with the same fixture.**
  Strongest signal of the whole sequence. [[dual-review-what-it-catches]].
* ⭐ **I REFUTED a Codex finding with evidence and it agreed on re-derivation** (r5 "attribution"):
  `check-plan-code.py:1479` — an `expect` must IDENTIFY one red case, not be the only case that
  reddens. Proof was a full `--mutate .` reporting `861 killed, 860 attributed`.
* **A mutation must reproduce the OLD BEHAVIOUR, not destroy the function.** `opens_steps = None`
  made every case return `[]`, so the case asserting `[]` still passed.
* ⛔ **ONE RULE, TWO GUARDS = a mutation that removes one is masked by the other.** Coverage
  theatre. The entry must remove both.
* **Exit the fix-then-new-round loop by committing the REVIEW ALONE** after the last guarded
  change — `check-review-recorded` keys on CODEX verdicts, see [[closing-table-r7-r8-merged-327]].

Final: 84 cases, 39 mutations, CI `868/868 killed, 868 attributed, 0 survivors`, merge gate READY
with **no waiver**. Architecture review = **backlog #153** (parse, or refuse), user-sequenced after
this PR. Still open: #148 · #149 Tier 2 · #151 · #152 · #153.
