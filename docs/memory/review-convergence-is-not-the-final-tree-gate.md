---
name: review-convergence-is-not-the-final-tree-gate
description: "FIRES-WHEN: deciding whether review rounds are finished — ⭐ TWO conditions, and conflating them cost 2 unnecessary review rounds (PR #302). Review CONVERGENCE is findings-based — review-method.md:302 says diminishing returns, :309 says one round is fine for a small contained change. check-review-recorded's SECOND question is about TREE IDENTITY, and has 3 answers, only one of which is another round"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 67579b5a-88c9-48c2-80a2-53aa046f97a6
  modified: 2026-09-19T04:48:12.039Z
---

**The stopping condition for review rounds is DIMINISHING RETURNS, and it is written down.**
Read `docs/review-method.md` rather than recalling it:

* `:302` — the loop runs *"until a round reaches **diminishing returns**"*.
* `:307` — re-review is required for *"any round that returned a **Blocking** finding, or
  whose fixes were **non-trivial**"*. A Medium with a one-line fix does not arm it.
* `:309` — *"For small, contained changes (single-file logic, config, thin wrappers), one
  round is fine — **do not over-apply this**."*
* `:298` — *"Address all High/P1 findings before showing the user. **Present Medium/P2 for
  a decision.**"* A Medium goes to the HUMAN; it does not automatically buy a round.

## ⭐ THE CONFLATION, measured on PR #302 (2026-09-14)

Two different conditions were merged and reported to the user as one:

| | what it asks | how it is satisfied |
|---|---|---|
| **Review convergence** | have the findings dried up? | diminishing returns (`:302`) |
| **`check-review-recorded` Q2** | did a round see the MERGING TREE? | **three** ways — one more round, **hold the fixes uncommitted** so the reviewer sees what ships, or a written `NO-REVIEW:` |

Q2 is a statement about **tree identity**, not about review quality. Rounds 3 and 4 were run
to satisfy **Q2** while being narrated as if convergence were unmet. Both returned a single
Low **in my own test code**, on a single-file change to a page generator — exactly `:309`'s
"do not over-apply" case. **The cheapest legitimate answers to Q2 were never put to the
user; the most expensive one was taken silently, twice.**

⚠ The user stopped it with one question: *"what is the stopping condition? if reviews were
converged, why continue?"* — and the answer was in a doc I had not re-read.

## ⚠ MIRROR IMAGE OF PR #299, and that is why the aim column matters

#299: every round aimed at the **deliverable** found a fail-open — stopping early would
have shipped one. #302: the deliverable produced nothing after r2's High; r3 and r4 were
aimed at my **instrument** and found instrument defects.

**Same instruction — read the AIM, not the count — opposite verdict.** #299's risk was
stopping too early; #302's cost was stopping too late. Only the aim column separates them
*in advance*. See [[gates-detect-defects-not-design]] and
[[a-framing-widened-to-fit-is-no-longer-a-claim]].

## ⟳ 2026-09-18, PR #322 — Q2 IS NON-TERMINATING BY CONSTRUCTION, so "one more round" is never the last answer

I did enumerate the three answers this time (the rule above worked) and the user chose the cheapest
real one — a single Codex half scoped to the delta. It found a genuine Low. **Then the gate fired
again, naming exactly the two files I touched while FOLDING that Low.**

⭐ **That is not bad luck, it is the gate's structure: folding round N's findings always changes code
round N never saw, so round N+1 always leaves the same residue one commit smaller.** Iterating cannot
reach zero. Four rounds ran (3 full dual + 1 single-half) and the residue never went away.

**So `NO-REVIEW:` is not the lazy answer, it is the only TERMINATING one** — and the gate says so
itself, listing it in its own failure message. Using a documented escape is not the thing
[[a-retreat-you-author-for-yourself-is-not-a-gate]] warns about; that warns against inventing a
*private* rule. Check which you are doing.

⚠ Two mechanics that cost cycles, both now written into the repo rather than only here:

1. **`gh run rerun` CANNOT see an edited PR body.** `ci.yml` reads
   `${{ github.event.pull_request.body }}`, which comes from the frozen EVENT PAYLOAD; a rerun
   replays it. Only a new `pull_request` event (a push / `synchronize`, or a reopen) picks up the
   edit. Cost two rerun cycles with byte-identical failures before I read the workflow. Documented
   beside the step in `.github/workflows/ci.yml`.
2. **Verify the declaration BEFORE pushing it:** `python3 scripts/check-review-recorded.py --base
   origin/master --pr-body-file <file>` exits 0 and echoes the reason. It also prints *"the
   final-tree question is WAIVED, not passed"* — quote that when reporting, so a waiver never reads
   as a pass.

## How to not repeat it

1. After each round ask **what was this round aimed at** — deliverable or instrument? Two
   consecutive instrument-only rounds on a contained change means STOP.
2. When a CI gate blocks, **enumerate its documented escapes and put them to the user**
   before spending 12 minutes on a round. `check-review-recorded`'s own message prints
   them.
3. Before saying "a round is owed", quote the line that owes it. If you cannot, it is not
   owed. Related: [[first-can-mean-first-before-shipping]],
   [[a-test-that-cannot-fail]].
