---
name: backlog-154-dash-scalar-ready-331
description: "FIRES-WHEN: citing backlog #154 or PR #331 — PR #331 READY (not merged) at 0791ca6f — backlog #154's false green. EIGHT rounds, each finding the next family at a NEW GRANULARITY; the fix changed KIND (refuse, don't widen). Filed #160–#163"
metadata: 
  node_type: memory
  type: project
  originSessionId: 0cfd7079-9c4f-4f89-9a59-337f426f6311
  modified: 2026-09-22T15:28:16.057Z
---

**PR #331**, branch `backlog-154-dash-block-scalar`, head `0791ca6f`, 12 commits. **READY** —
`check-merge-ready.py --pr 331` says *"READY — every gate CI will run has been run here"*, CI green.
**NOT MERGED** — human gate.

## The defect and why it took eight rounds

`scripts/check-python-pin.py` reported `rc 0 "python pin OK"` over a job with **no `setup-python`
step at all** — a shell script quoted inside a workflow read as YAML configuration.

⭐ **IT WAS NEVER ONE BUG. Each round found the next family at a granularity nobody had checked:**

| round | granularity | what was wrong |
|---|---|---|
| r1–r4 | **line** | `- run: \|` and 3 more spellings; the indent invariant had no falsifier |
| r5 | **node** | a keyless indicator (`run:` newline `\|`) — 12 more spellings, and **the refusal itself was blind to it** |
| r6 | **document** | a pin in a second YAML document credited to the first |
| r7 | **key depth** | not a YAML-shape bug at all: `uses:` matched at ANY depth |

**The rules were never wrong — a line scanner has no notion of the containers YAML has.**

## The verdict that matters for #155

r3 measured the false-green rate over one fixed 7,200-fixture space: **100% (master) → 76.7% →
36.7%**. Improving, halving, every fix correct — so **not** diminishing returns. A *wrong-instrument*
call. One shape proves the boundary: YAML's explicit key puts key and indicator on **different
lines**, unreachable by any line-local rule. So the fix changed KIND: one generic key rule **plus a
REFUSAL** (`unreadable_scalar_openers`) — which is not new, `unreadable_jobs` has done exactly this
for job keys since PR #317.

## ⛔ The lesson I paid for three times

**Three of the eight rounds found defects in MY OWN repairs**, and the sharpest:

* **my class-fix silently made SIX existing mutations unkillable.** Suite green at 111/111; only the
  mutation sweep saw it. Fixtures wrote a heredoc's sibling key at the step's key column, so the new
  depth rule filtered them *independently of masking* — the cases passed for a reason unrelated to
  what they claimed. **A fix is not done when the suite is green; it is done when the FALSIFIERS
  still fail.** See [[a-test-that-cannot-fail]], [[fixing-a-premise-is-not-covering-the-branch]].
* the inverted causal story (`Step.body` blanks the dash "before" `_structural`) was **false** and
  survived in **four copies**, each found a round apart, including `CONTEXT.md`'s glossary.
* r7 found ONE depth-blind key; sweeping the predicate found **three**. The reviewer's value was
  pointing at the right function — the class came from a six-line loop, in seconds.

## Filed, not absorbed

**#160** multi-line QUOTED scalar (measured fix deliberately NOT landed — it would be the 14th
line-local rule; #153 asked crude-vs-parse be decided ONCE) · **#161** commit the
differential-vs-libyaml harness (**12 members in one run** vs reviewers' ~1 per round) · **#162**
derive each guard's invocation from `ci.yml` · **#163** valid shapes false-RED (a DIFFERENT axis from
r7's depth sweep: colon-adjacency, not nesting).

## Process facts worth more than the code

* **CI was red on 6 pushes and nothing told me** — I stopped arming watchers on this branch. The
  *detector already existed and fired* (`check-ci-watched.py`, wired to the Stop hook); its channel
  is `exit 1` = "stderr reaches the HUMAN", who is deliberately away. **The gap was ADDRESSING, not
  detection.** A Monitor reaches me and works. See [[a-gates-channel-can-be-weaker-than-the-gate]].
* **`check-review-recorded` keys on CODEX VERDICTS and the FINAL TREE** — every round committed with
  its own fixes means no round saw the tree that merges. Exit: **commit the REVIEW ALONE**
  (`docs/reviews/` is PROSE, verified empirically), or earn a `NO-REVIEW:` waiver.
* **The waiver must be LINE-LEADING** — a `## NO-REVIEW:` heading is invisible to
  `check-dashboard-entry.exemption_reason` (the shared parser). Verify by RUNNING it.
* **Editing a PR body does not reach a run already in flight** (frozen payload). Push an empty commit.
* A comment-only change is still GUARDED. Waive it with an **AST-identity proof** (#328's precedent);
  the gate's own words are *"WAIVED, not passed"*.
* ⚠ `git stash -u` sweeps a LIVE AGENT's untracked file. I did it one sentence after saying I would not.

Related: [[an-inference-stated-as-measured]], [[arch-review-153-workflow-readers]],
[[after-fixing-search-for-the-class]], [[dual-review-what-it-catches]].
