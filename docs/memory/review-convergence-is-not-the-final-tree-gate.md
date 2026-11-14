---
name: review-convergence-is-not-the-final-tree-gate
description: "FIRES-WHEN: deciding whether review rounds are finished, or check-review-recorded blocks on the final tree — TWO conditions: CONVERGENCE (findings dried up, bounded by the r3 round cap) vs the gate's TREE-IDENTITY question, which has 3 answers and iterating rounds never terminates it"
metadata:
  node_type: memory
  type: feedback
  originSessionId: 67579b5a-88c9-48c2-80a2-53aa046f97a6
  modified: 2026-09-19T04:48:12.039Z
---

**Two different stopping conditions — never report one as the other.**

| | what it asks | how it is satisfied |
|---|---|---|
| **Review convergence** | have the findings dried up? | a round with no new Blocking/High (diminishing returns), **bounded by the round cap**: from r4 findings are FILED unless a BLOCKER — [[review-rounds-capped-at-r3]], `docs/review-method.md` §0 Q4c |
| **`check-review-recorded` final-tree question** | did a round see the MERGING TREE? | **three** ways: one more round scoped to the delta, hold fixes uncommitted so the reviewer sees what ships, or a written `NO-REVIEW:` |

The final-tree question is about **tree identity**, not review quality, and it is **non-terminating by construction**:
folding round N's findings always changes code round N never saw. So `NO-REVIEW:` is the only TERMINATING answer once
the findings have converged — a documented escape, not a private retreat ([[a-retreat-you-author-for-yourself-is-not-a-gate]]).

**Why:** on PR #302 two extra rounds were run to satisfy the tree question while narrated as unmet convergence; on
PR #322 four rounds never cleared the residue.

**How to apply:**
1. After each round ask **what was it aimed at** — the deliverable or my instrument? Two consecutive instrument-only
   rounds on a contained change = STOP. (`review-method.md`: for small contained changes one round is fine — *"do
   not over-apply this"*; a Medium goes to a decision, it does not automatically buy a round.)
2. When the gate blocks, **enumerate its three answers** (its own failure message prints them) and pick the cheapest
   real one.
3. Before saying "a round is owed", quote the line in `review-method.md` that owes it — read it, do not cite line
   numbers from memory (the `:302/:307/:309` cites this file once carried had moved by 2026-11-14).
4. Verify a `NO-REVIEW:` declaration before pushing: `python3 scripts/check-review-recorded.py --base origin/master
   --pr-body-file <file>` exits 0 and prints *"the final-tree question is WAIVED, not passed"* — quote that, so a
   waiver never reads as a pass.
5. `gh run rerun` cannot see an edited PR body (`ci.yml` reads the frozen event payload); only a new `pull_request`
   event (push/synchronize or reopen) picks it up.

## History

- **PR #302 (2026-09-14):** rounds 3 and 4 each returned a single Low in my own test code, on a single-file page
  generator. The user stopped it: *"what is the stopping condition? if reviews were converged, why continue?"*
- **Mirror image, PR #299:** every round aimed at the deliverable found a fail-open — stopping early would have shipped
  one. Same instruction (read the AIM, not the count), opposite verdict. See [[gates-detect-defects-not-design]],
  [[a-framing-widened-to-fit-is-no-longer-a-claim]].
- **PR #322 (2026-09-18):** enumerated the answers; user chose a single Codex half on the delta; it found a Low; folding
  it re-armed the gate on exactly the two files touched. 3 full dual + 1 single-half rounds; residue never reached zero.
  Two `gh run rerun` cycles failed byte-identically before I read the workflow.
- Related: [[first-can-mean-first-before-shipping]], [[a-test-that-cannot-fail]].
