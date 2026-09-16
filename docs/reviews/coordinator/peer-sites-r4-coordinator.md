# Round 4 — `peer-sites` — coordinator

```yaml
round: 4
fixes_nontrivial: false
subject: peer-sites
halves:
  claude: ran
  codex: "GAP: alternating protocol — r3 was the Codex half; r4 is Claude's by rotation"
findings:
  - {id: N1, severity: Medium, aim: deliverable, fix_induced: true, component: parse-hunks, disposition: fixed}
  - {id: N2, severity: Low, aim: instrument, fix_induced: true, component: peer-sites-suite, disposition: fixed}
  - {id: N3, severity: Low, aim: instrument, fix_induced: true, component: peer-sites-suite, disposition: fixed}
  - {id: N4, severity: Low, aim: deliverable, fix_induced: true, component: stated-bounds, disposition: fixed}
deliverable_findings: 2
stopping_rule: triggered_and_executed
```

**REVIEW GAP:** codex — not run for this round **by protocol**; r3 was the Codex half and rounds 2+
alternate. This round existed for one mechanical reason: the tree moved after r3 (its own fixes, plus
the hook removal), so `check-review-recorded.py` needed a round that had **seen the code that
merges**. It got one.

## Verdict: CONVERGED

> **"Four items to close before merge. None is Blocking, none is High, all four are one-line changes,
> and none of them is a reason to run round 5."**

**19 → 14 → 2 → 4.** The uptick to 4 is not a reversal: three of the four are in test code and prose,
and the fourth has zero reach in this repo today. All four are closed.

## N1 — the only new defect, and it is a good one

`parse_hunks`' counted walk closed r2's R5 properly (the reviewer re-verified the two-file case
returns `[5, 50]`). But `\ No newline at end of file` fell through to the **context** branch, and a
context line spends one line of *both* budgets. On real `git diff -U0` output where the old side
lacked a trailing newline:

```
@@ -3 +3 @@ b          ->  old_left=1, new_left=1, cursor=3
-c                    ->  old_left=0
\ No newline…         ->  context branch: cursor=4, old_left=-1, NEW_LEFT=0
+C                    ->  new_left > 0 is False  ->  NOT COUNTED

parse_hunks -> []     correct: [3]
```

⭐ **The docstring anticipated this line and got the failure mode exactly backwards.** It says the
marker *"can never be counted as an added line however much it looks like one"* — true, and not the
risk. It was never counted; it **spent the budget the next real `+` needed**, and that `+` vanished.
A silent false negative in the newly rewritten core, from output git produces unprompted.

**Reach: 0 of 59 `.py` files in this repo lack a trailing newline**, which is why it is Medium and
not High. Fixed with one line (`\` spends nothing), two cases, and a manifest entry.

## N2 — a case that asserted the module and measured three paths

```
"…and there are no unbounded git calls left in this module"
```

Its evidence was three kwargs lists captured from three fakes, so it could not see a call site no
case drives. The reviewer added a fourth, unbounded `subprocess.run` — **it SURVIVED 71/71.**

Fixed by making the case read the module's own source: `ast.parse` over `__file__`, find every
`subprocess.run` with no `timeout` keyword, assert the list is empty. Re-running the reviewer's exact
injection now kills it, naming the offending line:

```
72/73 passed
  [FAIL] …and NO `subprocess.run` in this module is unbounded — read from its own source: got [388] want []
```

⭐ **This is *assert the PROPERTY, not the mechanism*, and the method was already in evidence:**
reading the source with an AST is how Codex found the original unbounded call in r3, and how r4
confirmed this one. The case now uses the technique that keeps working.

## N3 — a want derived from its own subject

```python
case(…, [k.get("timeout") for k in _kws], [30] * len(_kws))
```

`[30] * len(_kws)` is computed **from the subject**, so the identical assertion over an empty capture
is `[] == []` — green on zero evidence. Nothing was wrong in the shipped tree (sibling cases require
the calls to have happened), but `check-fixture-variation.py`'s own docstring lists *"the WANT was
derived from the subject"* as a finding it made against another file. Replaced with a literal
`[30, 30, 30]`, which also asserts cardinality.

## N4 — two counts went stale, in the section whose stated point is that the claims are measured

The reviewer re-ran **every** number in the docstring against the current tree. Six were still exact.
Two had moved:

| claim | now |
|---|---|
| "**96** of 138 commits print NOTHING" | **93** |
| "`exits`, which produced **61 of the 73** containers" | **67 of 79** |

⚠ **And what moved them was the fix for the reviewer's own r1 finding.** `_span` + range intersection
recovered 6 `exits` containers (73 → 79) and made 3 more commits speak (96 → 93). **The docstring
updated the conclusion and kept the counts.** That is this project's *a measurement needs its
CONTEXT, not just its value*: the numbers were labelled *"measured over 138 python-touching commits"*
with no subject, so nothing marked them as belonging to a tree three rewrites ago.

## What the reviewer verified rather than took

- **The removal is clean.** `check-fixture-variation.py` and `check-selftest-counts.py` are
  **byte-identical** to `71378cd3` (md5 both sides). Zero `EXPECTED_MUTATIONS` keys with a missing
  file, zero manifests with no script, zero hits for `PEER_SITES_HOOK_DISABLE` / `PEER_SITES_BASE`.
  The only surviving references are the two deliberate ones — backlog #134 and the docstring that
  records why the caller was withdrawn.
- **The `else`-arm fix is shut and ratcheted in both directions.** The r2 asymmetry is gone; on B1's
  own fixture touching line 8 yields only the inner chain. Restoring `_span(cur.orelse[0])` kills two
  cases, one on behaviour and one on representation.
- **The r3 timeout work is real.** Stripping `, timeout=30` from **each** call site individually
  kills via its own named case — *"the part I most expected to be weak and it is not"*.

## The thrashing question, asked one last time and answered by the reviewer against itself

r4 raised the strongest argument for continuing, unprompted: r2's R4 was *a git call is unbounded*;
r3's S1 was *the fix for R4 was not ratcheted*; r4's N2/N3 are *the ratchet r3 added over-claims*.
Three consecutive rounds, each finding a defect in the previous round's fix, in one area.

**Its own answer, which I agree with:** thrashing is findings that come **back**. This is one
assertion being **tightened**, and each step is strictly smaller than the last — an unbounded call in
production code, then an unprotected fix, then a case name that overstates its evidence. A redesign
cannot remove N2 or N3; they are two literals. Convergent, not oscillating.

## `check-review-recorded` — diagnosed, and the obvious fix is the wrong one

The reviewer traced why it fails. `branch_verdicts()` (`:333-345`) uses `--diff-filter=A`, so it sees
only the Codex verdicts this branch **committed**. The r3 verdict records `gate_ran: true`,
`head: 71378cd3` and a `dirty` list that **does** include all six guarded files — it is invisible
solely because it is untracked.

⛔ **So the uncommitted-until-both-halves-finish discipline and this guard's ADDED rule are in direct
tension: obeying one makes the other fail.** Filed as **backlog #135**, because it is a property of
the guard rather than of this branch.

⚠ **Not assumed to clear on commit.** Committing moves `HEAD` past `71378cd3`, and neither of us
measured how the rule treats a verdict whose recorded head is now the parent. **It gets checked after
the commit, and if it still fails the PR body carries a `NO-REVIEW:` naming this exact reason** —
which is the documented escape, not a workaround.

## ⛔ THE MACHINE DISSENTS, AND THE DISSENT IS RECORDED RATHER THAN RESOLVED

```
$ python3 scripts/check-review-decision.py
ROUND_OWED — r3 produced a High
```

`converged()` (`:113-134`) requires the **last two** rounds to carry no Blocking/High **and** nothing
marked `aim: deliverable`. r3 carried a High (S1, the unratcheted timeout); r4 carried a deliverable
Medium (N1, the `\ No newline` budget bug). Because r4 stays inside the two-round window until r6,
**satisfying this rule mechanically costs two more rounds** — r5 reviewing a parser line, an AST
case, one literal and two prose numbers, and r6 reviewing whatever r5 says about those.

**The reviewer that found every serious defect on this branch wrote, unprompted: *"none of them is a
reason to run round 5."*** The human was shown both positions with the cost of each and chose to
ship on the reviewer's verdict.

⚠ **This is the second gate overridden on this branch, and the first override was WRONG** — I argued
against the thrashing verdict and the evidence went against me. That is the reason this section
exists in this shape: not to justify the decision, but to leave the machine's objection legible to
whoever next reads this branch, so the override is a recorded position rather than a silence.

**What is NOT being claimed:** that round 5 would find nothing. It might. The claim is only that
`review-method.md`'s stopping rule is **diminishing returns** — 19 → 14 → 2 → 4, with the last
round's entire output being one-line changes — and that PR #302 is this project's measured instance
of paying for the other answer.

**What makes the override defensible rather than convenient**, stated so it can be checked:

| | |
|---|---|
| every r4 item | fixed, with a falsifier, and each verified to redden under its own mutation |
| `scripts/mutations/peer-sites.json` | 25 entries, **25 RED via the case each names**, over a control proved green first |
| full sweep, final tree | **714 mutations, 714 killed, 714 attributed, 0 survivors**, 47 files |
| the component that was still moving | **removed** from the branch, not argued about |

## Final state

| | |
|---|---|
| `peer-sites.py --self-test` | **73/73** |
| `scripts/mutations/peer-sites.json` | **25 entries**, each verified RED via the case it names |
| declared total | **714** over 47 files |
| rounds | 4 — both halves twice, 19 → 14 → 2 → 4 findings |
| open, filed | #131 (arm bodies), #132 (branches noise), #133 (tree-leak rule), #134 (no caller), #135 (verdict ADDED rule) |
