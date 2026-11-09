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

**Fold** (2026-11-08, past the round cap: the three BLOCKERs only). X-F1: `&>` never consumes the word before it, so `push 2&>/dev/null HEAD:master` reads remote `2`, refspec `HEAD:master`, and is refused on rule 1; a digit names a descriptor only when glued to `<` or `>`. The agreement inputs gained every accepted operator with an adjacent digit word, an attached digit and neither (7 inputs, 6 atoms), and a broken-lexer control that restores the X-F1 misreading reddens the check (12 unsafe of 255 accepted). X-F2: a new rule, `branch-change`, refuses a branch mover (`checkout`, `switch`, `rebase`, `reset`, `merge`, `pull`, `worktree`, `update-ref`, `symbolic-ref`, `stash branch`, `branch -m/-M/--move`, `gh … checkout`, an unreadable git option) composed with a git push in either order, and the hook names the command. A `cd`/`pushd`/`popd`, `-C`, `--git-dir`, `--work-tree` or a `GIT_DIR=` prefix is judged conservatively: the current branch becomes UNKNOWN, so `HEAD`, `@` or no refspec refuses while a named feature refspec is still allowed. Refusing every `cd` outright was measured first and rejected: +284 on the corpus, 281 of them `cd`. X-F3: a push option's value (`-o`, `--push-option`, and every `=` value) naming the default branch, beginning with `-`, or mentioning force or no-verify refuses (`option`). Every repro is a case. 265 → 325 detector cases; 79 → 99 mutations, each new one hand-checked alone in a `stage_tree` copy (rc 1, its case named once). Corpus: 1,250 → 1,266 refused (+16, all `branch-change`; the option-value rule refused none).
