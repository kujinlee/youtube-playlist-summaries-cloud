# Round 2 — `prune-merged-worktrees` — coordinator

REVIEW GAP: codex — alternation (round 2 ran the Claude half only)

```yaml
round: 2
fixes_nontrivial: true
subject: prune-merged-worktrees
halves:
  codex: gap
  claude: ran
findings:
  - {id: R2-C-F1, severity: Medium, aim: deliverable, fix_induced: false, component: worktree-prune, disposition: fixed}
  - {id: R2-C-F2, severity: Medium, aim: deliverable, fix_induced: false, component: worktree-prune, disposition: fixed}
  - {id: R2-C-F3, severity: Low, aim: deliverable, fix_induced: false, component: worktree-prune, disposition: fixed}
  - {id: R2-C-F4, severity: Low, aim: deliverable, fix_induced: false, component: worktree-prune, disposition: fixed}
  - {id: R2-C-F5, severity: Low, aim: test, fix_induced: false, component: worktree-prune, disposition: fixed}
  - {id: R2-C-F6, severity: Low, aim: deliverable, fix_induced: false, component: worktree-prune, disposition: fixed}
  - {id: R2-C-F7, severity: Low, aim: deliverable, fix_induced: false, component: worktree-prune, disposition: fixed}
  - {id: R2-C-F8, severity: Low, aim: deliverable, fix_induced: false, component: worktree-prune, disposition: fixed}
  - {id: R2-C-F9, severity: Low, aim: deliverable, fix_induced: false, component: worktree-prune, disposition: fixed}
  - {id: R2-C-F10, severity: Low, aim: deliverable, fix_induced: false, component: worktree-prune, disposition: fixed}
```

Claude half: `docs/reviews/claude/prune-merged-worktrees-r2-claude.md`, on `e2a10f59`, NOT CONVERGED (2 Medium, 8 Low).
No loss path was found: the r1 redesign holds. The findings are disruption, efficacy, wording and test gaps.

| Finding | Disposition |
|---|---|
| F1 (Medium: `lsof` is blind to agents using absolute paths; a late write after the move recreates the directory, which git resolves to the MAIN checkout) | Fixed. After a verified move, `leave_placeholder` creates a regular FILE at the old path (`O_EXCL`, so anything already there is left alone), named as the old directory, holding one line: the archive path and the undo command. A late `<old>/x` write now fails with ENOTDIR. A placeholder is not a registered worktree, so the next run never lists it. The limit is stated in the docstring (rule 5) and the backlog row: `lsof` sees only a cwd, and agents using absolute paths are protected only by the 2 h rule and the placeholder. Cases: a placeholder at each archived path naming the archive and the undo; a late write raises ENOTDIR; a following run does not count the placeholders. Mutation: no placeholder. |
| F2 (Medium: a squash-merged branch whose remote is gone is KEPT forever as if unpushed) | Fixed. The `origin/master` fallback is removed: rule 2 already puts HEAD at or under a merged PR's `headRefOid`, so every commit of it is on GitHub. The check against an EXISTING `origin/<branch>` stays. The self-test's `gone` case now expects ARCHIVED (the dry-run set goes from six to seven). Its mutation is dropped with the rule. A HEAD that GitHub lacks is still kept by rule 2 (the `reuse` case). |
| F3 (Low: the cross-device reason says a move copies) | Fixed. git refuses with "Cross-device link" (rc 128) and moves nothing; the KEPT reason, rule 6 and the mutation's description now say so. The guard stays as the clear early refusal. |
| F4 (Low: a missing worktree directory is advised `git worktree prune`) | Fixed. The reason now names `git worktree repair <archive path>`, with the path taken from the last `archiving` log line for that source, and says NEVER `git worktree prune`. Case and mutation. |
| F5 (Low: 8 mutations survive) | Fixed: 7 cases added, each turning its survivor red: post-move check (`_FakeMove`: rc 0 and nothing moved is FAILED), the prunable `return` (a detached prunable row has ONE reason), the zone-less `mergedAt`, the warn boundary (silent at 10, printed at 11), the `GIT_ENV_DROP` loop (a dry run with `GIT_DIR` set to a bogus path still sees the same seven), `stopped or` (`_OneShot`: the FIRST `git status` raises and later calls succeed, so a loop that went on would move the next worktree), and the hook cap (`HOOK_MAX_LINES` set to 2 over 4 lines). The existing persistent `_StopAfterMove` is kept: it pins the report after a deadline. The 8th survivor, `main`'s second cut to `HOOK_MAX_LINES`, cannot be killed on its own: `hook_lines` already caps, and the except path prints one line. That duplicate was REMOVED, and `hook_lines` is the one cap. |
| F6 (Low: a worktree git refuses to move is FAILED at every session start) | Fixed. A failed move whose source is still in place and whose target is absent records `path -> HEAD` in `.claude/pruned-worktrees/refused.json`, beside the log. It is reported FAILED that once, with "remembered" in the reason. After that it is KEPT quietly ("git refused to move it before, at this HEAD") until its HEAD changes. Entries for worktrees that no longer exist are dropped on save; `--dry-run` never writes it. Cases: a real refusal (a `modules` admin dir; a bare gitlink is NOT refused by git 2.49, measured), FAILED once; the next run KEPT, hook silent; a changed HEAD tried again. Mutations: the check, and the recording. |
| F7 (Low: two concurrent runs report FAILED for each other's moves) | Fixed. A failed move whose source is gone or a placeholder, while an archive entry (`<name>` or `<name>-*`) has a `.git` naming the same admin dir, is BY-PEER, "archived by a concurrent run", and does not fail the run. The hook prints nothing for it, since the run that moved it reports it. Case (`_PeerFirst`: a peer moves to `<dest>-peer` and leaves its placeholder first) and mutation. |
| F8 (Low/Info: the registered set only grows, and every walker pays) | Fixed as documentation, per the brief. No code: the docstring BOUNDS and the backlog row state it. Archived worktrees stay registered and in `git worktree list`, and `git worktree remove <archive path>` is the owner's cleanup, prompted by the over-10 line. |
| F9 (Low: `lsof -Fn` escapes a newline, so such a path never matches) | Fixed as documentation: a bound in the docstring and the backlog row (names here are generated ASCII). |
| F10 (Low: the undo is relative to the main checkout) | Fixed with F1. `undo_cmd(dest, old)` prints `rm <old> && git worktree move <archive> <old>`, ABSOLUTE both ways, in the log, the CLI line and the placeholder. The hook line prints `<main>/.claude/worktrees/<name>` absolute too. The logged-undo case asserts the absolute form; the undo case runs it (`rm`, then the move). Mutation: a relative undo. |

**Tests.** `--self-test` 79/79. Mutations 39 (27, minus the dropped gone-remote entry, plus 13 new; the half-moved entry
is re-anchored, since its code was restructured for F4), all killed and attributed
(`check-plan-code.py --mutate . --only scripts/prune-merged-worktrees.py`).

**Verdict.** NOT CONVERGED (Medium): F1 and F2 changed behaviour, and the fold adds new code (placeholder, refused
state, peer classification) that no review has seen.

**Round 3.** One half, Codex (alternation), on the folded script. Round 3 is the cap: from round 4, findings are FILED
unless one is a BLOCKER (`docs/review-method.md` §0 Q4c).

REVIEW GAP: claude — alternation
