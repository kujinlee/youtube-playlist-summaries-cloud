# Round 4 — `prune-merged-worktrees` — coordinator — STOPPED PAST THE CAP

REVIEW GAP: codex — alternation (round 4 ran the Claude half only)

```yaml
round: 4
fixes_nontrivial: false
subject: prune-merged-worktrees
halves:
  codex: gap
  claude: ran
findings:
  - {id: R4-C-M1, severity: Medium, aim: deliverable, fix_induced: true, component: worktree-prune, disposition: filed}
  - {id: R4-C-L1, severity: Low, aim: deliverable, fix_induced: true, component: worktree-prune, disposition: filed}
  - {id: R4-C-L2, severity: Low, aim: deliverable, fix_induced: true, component: worktree-prune, disposition: filed}
  - {id: R4-C-L3, severity: Low, aim: deliverable, fix_induced: true, component: worktree-prune, disposition: filed}
```

Claude half: `docs/reviews/claude/prune-merged-worktrees-r4-claude.md`, on `f3b3e687` (the r3 fold), NOT CONVERGED (1 Medium,
3 Low), scoped to that fold only. It traced every path the fold changes and found **no BLOCKER**: no input where a
worktree is reported archived without having been moved, and none where a file is lost. Self-test 92/92 at that head.

Past the cap (`docs/review-method.md` §0 Q4c) a non-BLOCKER is FILED, not folded. All four go to backlog #591 (the next
free number: #590 is on master from PR #552, and no open branch holds #591).

| Finding | Disposition |
|---|---|
| R4-C-M1 (Medium: the half-peer FAILED row, from the r3 F3 fold, does not name where the worktree is; the next run's repair hint names a path that does not exist) | FILED -> backlog #591. Not data loss: the directory and the admin dir are intact, and the message already says never `git worktree prune`. |
| R4-C-L1 (Low: the printed undo for ARCHIVED-WITHOUT-PLACEHOLDER removes a late regular FILE) | FILED -> backlog #591. The reason text warns; the undo is never run automatically. |
| R4-C-L2 (Low: the 24 h refusal TTL accepts a future or non-finite `at`) | FILED -> backlog #591. The safe direction: nothing is moved. |
| R4-C-L3 (Low: an ARCHIVED-WITHOUT-PLACEHOLDER row is loud on one session start only) | FILED -> backlog #591, noted with no change asked; FAILED has the same behaviour. |

**Thrashing or prose floor? (the arming question).** By the letter the arming condition is met: r3 (7 of 7) was caused by
the r2 fold and r4 (4 of 4) by the r3 fold, which are two consecutive fix-caused rounds in one component
(`worktree-prune`). The call, with the evidence:

- The thrashing TELL in `docs/review-method.md` is "findings are introduced by the previous round's own fix; **severity
  stays put**". Here severity did not stay put: 13 findings (r1) -> 10 -> 7 -> 4, and from MEDIUM-heavy (r3: 5 Medium) to
  one Medium and no BLOCKER.
- Where the findings sit has moved away from the design. r1's data-loss findings (5 of 13) were removed by the redesign
  (archive, never delete). No round since has found a loss path. r4's four findings are all in reporting text and state
  bookkeeping (what a FAILED row says, a printed undo, a TTL bound, how often a row is printed), not in the move or its
  guards.
- The test "can a redesign remove it?" answers no for these four: each is a sentence or a bound in a report layer. A
  redesign would remove the move itself, and the move is the part that stopped producing findings.

**Decision: an architecture review does NOT arm.** It is judged not worth convening, and the call is written here as
`review-method.md` asks. It is the coordinator's judgment against the letter, so the owner can overrule it by asking for
Phase 6. Revisit it if the follow-ups in #591 are folded and the fold itself produces a Medium or higher finding in the
move or its guards.

**Verdict.** STOPPED PAST THE CAP, no BLOCKER: no data loss and no false ARCHIVED. No further review round is run; the
four findings wait in backlog #591.
