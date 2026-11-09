# Round 5 — `push-hook-quoted` (PR #542, backlog #428) — coordinator — NOT CONVERGED; the round's own BLOCKER definition was wrong, and is narrowed

REVIEW GAP: codex — alternation

```yaml
round: 5
fixes_nontrivial: true
subject: push-hook-quoted
halves:
  codex: gap
  claude: ran
findings:
  - {id: C-F1, severity: Blocking, aim: deliverable, fix_induced: true, component: detector-judge, disposition: fixed}
  - {id: C-F2, severity: Blocking, aim: deliverable, fix_induced: true, component: detector-judge, disposition: fixed}
  - {id: C-F3, severity: High, aim: adjacent, fix_induced: false, component: detector-judge, disposition: filed}
  - {id: C-F4, severity: High, aim: adjacent, fix_induced: false, component: detector-judge, disposition: filed}
  - {id: C-F5, severity: Medium, aim: deliverable, fix_induced: true, component: detector-reader, disposition: fixed}
  - {id: C-F6, severity: High, aim: adjacent, fix_induced: false, component: detector-judge, disposition: filed}
  - {id: C-F7, severity: High, aim: adjacent, fix_induced: false, component: detector-judge, disposition: filed}
  - {id: C-F8, severity: High, aim: adjacent, fix_induced: false, component: detector-judge, disposition: filed}
  - {id: C-F9, severity: Medium, aim: adjacent, fix_induced: false, component: detector-judge, disposition: filed}
```

Claude (`docs/reviews/claude/push-hook-quoted-r5-claude.md`) reviewed `822fccb8`, the round 4 fold. It reports nine
findings and calls eight of them BLOCKERs under the definition I gave rounds 4 and 5. The two self-tests pass:
325/325 and 59/59. Three of the new mutations were hand-checked and each was killed through its named case.

## The BLOCKER definition was wrong, and it is what made this loop unable to end

I defined a BLOCKER two ways:
1. the branch ALLOWS what master refuses — a loosening;
2. a command that reaches the default branch without a refusal — completeness.

**Clause 2 asks a text interceptor to prove a negative over everything bash and git can do**, and that cannot
terminate. The repo has recorded this lesson (memory: "negatives by interception cannot terminate — pre-commit the
retreat"). r5 shows it plainly. Six of its eight BLOCKERs are also allowed by MASTER:
- `xargs` and `parallel` (F3);
- branch movers behind `nice`, `env` or an alias (F4);
- the destination reconfigured with `-c remote.origin.push` or `git config` (F6);
- the matching refspec `:` and glob refspecs (F7);
- `export GIT_DIR` (F8).

None of those is a regression, and each is a member of a class with no end — any program that runs its arguments,
any config key git reads. **The structural answer is already filed: backlog #574, git's OWN pre-push hook.** It
reads the refs git is actually about to push, whatever text produced them. F3, F4, F6, F7, F8 and F9 are filed
there as its evidence, not folded.

**The retreat, committed now:** this PR's merge criterion is **"no worse than master"**:
- the branch refuses everything master refused;
- plus the bypass classes #428 set out to close: quoted and full-path pushes.

Completeness belongs to #574.

## What is folded

- **C-F1 and C-F2 are true loosenings against master**, which is clause 1. Both arise because master's crude text
  match saw words that the exact reader correctly treats as non-push text: a redirection target `> master`, and a
  `-c core.editor='git push origin master'` value. This is the THIRD member of that class, after r4's option values
  (X-F3). Rather than chase a fourth, **the fold makes "no worse than master" true by construction**: master's own
  text rules are kept as a FLOOR, and the branch refuses whenever master's rules would. The flagged loosening lines
  then hold by construction, not case by case. The cost is re-measured on the corpus. Most of master's false
  refusals return, but #428's goal was the bypasses, not those.
- **C-F5:** `A+=1` is an assignment to bash and a command word to the reader. The bash-agreement check itself
  reports it as UNSAFE. The reader is supposed to be exact over the syntax it accepts, so this is fixed (append-
  assignment parsed as an assignment).

## Filed (backlog #574's evidence)

F3, F4, F6, F7 and F8 are pre-existing completeness gaps, each confirmed in a fixture or from git's documentation.
F9: naming the branch after a `cd` does not fix the destination, because the other repository's config can
redirect it.
