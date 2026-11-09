# Round 5 — `held-pins-head` (PR #541, backlog #538) — coordinator — CONVERGED

REVIEW GAP: codex — alternation

```yaml
round: 5
fixes_nontrivial: false
subject: held-pins-head
halves:
  codex: gap
  claude: ran
findings:
  - {id: C-F1, severity: Low, aim: deliverable, fix_induced: true, component: comment-prose, disposition: filed}
```

**Why there was a round 5.** Round 4 converged on `31aac2aa`. CI's mutation sweep then found survivors, and
`15178418` fixed them:
- one self-test case made stricter (the backlog #359 r3 `ls-tree` case);
- two mutations re-anchored from `_exact_pins` onto the child `_DRIVER`'s type checks.

CI's review-recorded gate correctly wanted a round that had seen that tree.

**What Claude found** (`docs/reviews/claude/held-pins-head-r5-claude.md`):
- The case is strictly stricter.
- The re-anchoring is honest: `_exact_pins`' type checks are now unreachable, because `_child_answer_ok` and the
  driver refuse first.
- All 3 entries go red through their named case.
- All 15 flagged ids are answered `not a loosening`.

**C-F1 (Low, FILED).** The `_exact_pins` docstring and the comment near the bool case still describe those checks as
load-bearing. The fix is wording only. It is filed for the next docs batch, so this branch is not re-opened past the
round cap.
