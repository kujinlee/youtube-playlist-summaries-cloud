Reviewed head: 57a1def7ded2e787602742323295a4c2c801c0e2

# Round 3 — `false-hold-judgment` (backlog #508) — Claude half

## Summary

The round-2 redesign holds up against most of what I threw at it. The section parser is now small enough to reason
about, and every forgery I tried *inside* one section fails closed. That includes a fenced or commented section, CRLF,
a trailing-space heading, a wrapped dissent, a vertical tab or U+2028 inside a line, a duplicated id, and an
empty or NBSP-only finding text. The exact-name record exemption, the same-half retirement rule and `tree_matches`
also held. Verdict names cannot be made to disagree about subject or round in a way that retires a finding. Round
numbers compare as integers. A greedy `-r<N>-` in a subject such as `foo-r2-r3-codex` parses to subject `foo-r2`,
so it cannot retire `foo`'s finding.

**One real loosening still passes, with no reviewer involved (M1).** The shared added-line budget is spent greedily,
in hunk order. Because of that, a count rise can take the added line that belonged to a MOVE. Codex r2 #1 is fixed when the moved
line comes first in the file and NOT fixed when it comes second. I reproduced a gate whose `b()` goes from 1 to 0:
`origin/master`'s detector flags that line, and the branch's flags nothing, so no answer is ever asked for. Two
smaller findings follow. A later exact heading erases an earlier section's dissent (m1). The process docs never
say that the backlog and dashboard ticks must be committed before the final round (m2). Neither of those fails open
on its own.

On the design: it is now simple enough to trust, apart from the budget's pairing order. It composes with alternation
as intended, at a cost the docs should state: a Codex finding is retired only by a later Codex round on the exact
merging tree. On this PR, Codex r2's findings on `c7f21f95034a`, `6bd002a6d73a` and `e8b3c3bfbf22` stand whatever
this Claude round answers, so the PR HOLDs and goes to the owner. That is correct here, because those lines are the owner's chosen loosening.

## Findings

### M1 (MAJOR): Codex r2 #1 survives in its mirror order. A rise takes a moved line's addition, and the real change goes unflagged

`failure_path_removals` (`scripts/check-merge-ready.py`, the loop after `added = [...]`) pairs each removed line, in
hunk order, first with an identical added line and otherwise with a rising-count added line. The pairing is
first-come. If the rising-count candidate is processed BEFORE the moved line, it takes the moved line's addition,
because the prefix and suffix match exactly. The moved line then has no partner, and it is flagged only if it sits
near a failure word.

Concrete input. This is Codex r2 #1's file with `b()` placed BEFORE `a()`, and `a()` padded so it is more than
`FAIL_WINDOW` lines from any failure word (`␠` is one space):

```
# base scripts/check-k.py                      # branch
def b():                                        def b():
    expected = """--self-test # 6 cases␠            expected = """--self-test # 9 cases
"""                                             """
    if expected.split("cases",1)[1].startswith(" "):   (same)
        return 1                                        return 1
    return 0                                        return 0
def a():                                        def a():
    v0 = 0 … v7 = 7                                 v0 = 0 … v7 = 7
    expected = """--self-test # 9 cases␠            v0 = 0 … v7 = 7
"""                                             def c():
    v0 = 0 … v7 = 7                                 expected = """--self-test # 9 cases␠
def c():                                        """
    pass                                            pass
```

Measured with a real `git diff -U5`. `b()` returns 1 on base and 0 on the branch. The branch's
`failure_path_flags(diff)` returns `[]`, while `origin/master`'s `failure_path_removals(diff)` returns
`{'scripts/check-k.py': ['expected = """--self-test # 6 cases']}`. So master HELD it, and the branch has nothing to
ask the reviewer and no HOLD. Without the padding, so that `a()` keeps its `return 1`, the branch flags exactly one line,
**`a()`'s** (`064de7bd1ce9`), with `a()`'s base line number. A reviewer who checks that line finds it moved intact
into `c()`, answers `not a loosening`, and clears the real loosening in `b()`.

Fix: two passes per file. First consume every EXACT re-add (moves) across all hunks, then pair rising counts among
the additions that are left. A rise pairs only lines that are identical apart from a raised count, so a pairing among
rises cannot carry a semantic change. Pin it with this file in both orders: `b()` after `a()` (Codex's) and before.
Not BLOCKER: the trigger needs a count-shaped string whose trailing whitespace is code, plus an identical sibling
that moves. The m7 bound already concedes the count-as-code regime. But the r2 coordinator doc records this class as
**fixed**, and it is not.

### m1 (MINOR): a later exact `## Loosening answers` heading silently erases an earlier, well-formed section's findings

`loosening_answers` reads only after the LAST exact heading. A malformed section names only its own ids, so a
dissent in an earlier section becomes *no answer*, not a finding. Measured with `codex-review.loosening_answers`
(X, Y are 12-hex ids):

- `## Loosening answers / X: finding: exit 1 now 0 / Y: not a loosening / VERDICT: NOT CONVERGED / (blank) / ## Loosening answers` → `{}`
- the same section followed by a fenced quote ```` ``` / ## Loosening answers / Y: not a loosening / ``` ```` before `VERDICT:` → `{Y: finding}`, so **X's finding is lost**
- a Codex body (Codex has no "last line is VERDICT" rule; the Claude recorder has one) `## … / X: finding: x / VERDICT: NOT CONVERGED / ## … / X: not a loosening` → `{X: not a loosening}`

X then has no answer from that half, so it clears on the other half's exact assent. That case is the other
half's assent overriding a dissent, which r1 m3 and r2 Codex 5 were written to refuse. It needs two exact headings
in one review, so it is unlikely, but it costs one clause to close. Treat MORE THAN ONE exact heading as malformed,
so every id named after the first heading is a finding. A line starting `VERDICT:` inside the section, such as
`VERDICT:CONVERGED`, similarly truncates it and drops the findings after it. Both are covered by the same rule if
"malformed" also covers any id named after the section ends.

### m2 (MINOR, process composition): "commit the backlog and dashboard ticks BEFORE the final round" is not written where a coordinator reads it

The r1 coordinator doc decided not to exempt `docs/backlog.md`, `docs/dashboard-entries.md` or
`docs/goal-threads.md`, and to require that they are committed before the final round. `docs/review-method.md`'s new
paragraph says only "on the exact tree". `grep -n 'before the final round' docs/review-method.md
docs/process-checklists.md docs/dev-process.md` finds nothing. Today the dashboard entry is usually written last. A
coordinator who follows the docs gets a HOLD with `reviewed a different tree`. That fails closed and costs a
false HOLD, which is exactly what #508 set out to cut. Fix: one sentence in the review-method paragraph.

### Checked and NOT findings (bounds, already stated or harmless)

- A hand-written verdict JSON, a verdict deleted on the branch, or a verdict whose file name disagrees with its
  recorded `review` field is the trust bound the gate already states ("the answer is the reviewer's text, copied,
  not proof"). Re-running the same id with `--allow-overwrite` replaces a dissent. That is equivalent to a later
  round of the same half on the merging tree, which the retirement rule already accepts.
- `REVIEW_RECORD` lets a coordinator doc or the decision log change after the round. Gates READ those files
  (`check-decision-scheme.py`, `check-review-rounds.py`), but they are judged by their own gates at merge, and the
  answers concern code lines. Nothing in `scripts/` `runpy`s or imports a `docs/reviews/` path.
- `record-review-verdict.py` refuses with TREE MOVED unless the half's head is checked out, so the "record before any fold
  edit" warning is enforced, not just advised (r1 m6 / backlog #526 covers only the overlay timing).

## Self-tests (run at 57a1def7, this worktree)

- `python3 scripts/check-merge-ready.py --self-test` → `324/324 self-test cases passed` (rc 0)
- `python3 scripts/codex-review.py --self-test` → `228/228 passed` (rc 0)
- `python3 scripts/record-review-verdict.py --self-test` → `100/100 passed` (rc 0)

## Mutations

I selected every entry in `scripts/mutations/check-merge-ready.json` and `codex-review.json` that is new or changed
against `origin/master`: **63 entries**, covering both rounds, a superset of r2's 39. I staged them into a temporary
copy with `check-plan-code.stage_tree` and ran them through `check-plan-code.run_mutations` (the harness's own rule:
an anchor that matches 0 or more than 1 times fails the run). Result: `OK=True`, **0 survivors**, 0 anchor problems. Every
entry anchors exactly once and goes red through its named case. Nothing was mutated in place. No mutation covers
M1's order, because no case covers it.

## Flagged lines (my reading of each)

- `26a23836138b` `def failure_path_removals(...)`: the signature gains `at`. The body behind it now drops a removed
  line whose only change is a raised `--self-test  # N cases` (owner's card A), and master flagged that line. It is
  also where M1 lives.
- `795043e96b8f` `def gather(read, base)`: gains `head="HEAD"`, so the default behaviour is identical.
- `c7f21f95034a`, `6bd002a6d73a`, `e8b3c3bfbf22`: the "loosens a gate" HOLD loop now skips flagged lines answered
  `not a loosening` on the exact tree. Master held every such line.
- `f13e64d753fa` `codex-review.py` `verdict_record(..., tree=None)`: gains `loosening_answers=None`. The record is
  unchanged when it is not given, and no refusal path is touched.

## Loosening answers
LOOSENING-CHECK 26a23836138b: finding: a removed failure-path line whose only change is a raised --self-test count is no longer returned, so master's HOLD on it is gone (and see M1)
LOOSENING-CHECK 795043e96b8f: not a loosening
LOOSENING-CHECK c7f21f95034a: finding: a flagged failure-path line answered not a loosening by a verdict on the exact tree is no longer HELD; master held every flagged line
LOOSENING-CHECK 6bd002a6d73a: finding: the loosens-a-gate HOLD is emitted only for flagged lines left unanswered, so reviewer-cleared lines merge where master held
LOOSENING-CHECK e8b3c3bfbf22: finding: part of the same HOLD message, now reached only for unanswered flagged lines, so reviewer-cleared lines are no longer held
LOOSENING-CHECK f13e64d753fa: not a loosening

VERDICT: CONVERGED
