# Round 4 — `push-hook-quoted` (PR #542, backlog #428) — coordinator — NOT CONVERGED; three BLOCKERs folded

REVIEW GAP: claude — alternation

```yaml
round: 4
fixes_nontrivial: true
subject: push-hook-quoted
halves:
  codex: ran
  claude: gap
findings:
  - {id: X-F1, severity: Blocking, aim: deliverable, fix_induced: true, component: detector-reader, disposition: fixed}
  - {id: X-F2, severity: Blocking, aim: adjacent, fix_induced: false, component: detector-judge, disposition: fixed}
  - {id: X-F3, severity: Blocking, aim: deliverable, fix_induced: true, component: detector-judge, disposition: fixed}
```

Codex (`docs/reviews/codex/push-hook-quoted-r4-codex.md`) reviewed `66a2d8a0`, the Phase 6 fold, against this
round's BLOCKER definition: a command the branch ALLOWS that master refuses, or one that reaches the default
branch, `--force`, `--no-verify`, core.hooksPath or ALLOW_PLAN_LEAK without a refusal. It ran 265/265 and 59/59,
and three hand-checked mutations went red through their named cases.

- **X-F1 (fold-induced).** `push 2&>/dev/null HEAD:master` is read wrongly. The reader drops the `2` as a
  descriptor, but bash passes `2` as an argument and then applies the `&>` redirection. So `HEAD:master` is taken as
  the remote, and no refspec is seen. Master allows this command too. It still disproves the claim that the reader is
  exact. The bash-agreement inputs never put a digit before `&>`, so the agreement check is only as good as its inputs,
  as the Phase 6 review warned.
- **X-F2 (pre-existing).** `git checkout master && git push origin HEAD`, and `git switch master && git push`, are
  judged against the branch that was current BEFORE the command ran. Master allows these too.
- **X-F3 (a literal loosening).** `--push-option master`, `--push-option --force` and `--push-option --no-verify`
  are allowed. Master refuses them, through its crude text match. A push-option value is not a destination or a
  flag, so this costs no safety. But the loosening answers bind it (7 ids answered `finding`), and the cheapest
  sound exit is to refuse them conservatively, as master did.

The fold for all three is specified in the fold brief. X-F1 extends the agreement inputs as well as fixing the
reader. X-F2 refuses any branch-changing command (`checkout`, `switch`, `rebase`, `reset`, `worktree`, `-C`
changes) composed with a push. X-F3 refuses any push whose option value is the default branch name or begins
with `-`.
