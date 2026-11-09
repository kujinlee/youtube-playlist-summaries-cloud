# Round 3 — `prune-merged-worktrees` — coordinator — STOPPED AT THE CAP

REVIEW GAP: claude — alternation (round 3 ran the Codex half only)

```yaml
round: 3
fixes_nontrivial: true
subject: prune-merged-worktrees
halves:
  codex: ran
  claude: gap
findings:
  - {id: R3-X-F1, severity: Medium, aim: deliverable, fix_induced: true, component: worktree-prune, disposition: fixed}
  - {id: R3-X-F2, severity: Medium, aim: deliverable, fix_induced: true, component: worktree-prune, disposition: fixed}
  - {id: R3-X-F3, severity: Medium, aim: deliverable, fix_induced: true, component: worktree-prune, disposition: fixed}
  - {id: R3-X-F4, severity: Medium, aim: deliverable, fix_induced: true, component: worktree-prune, disposition: fixed}
  - {id: R3-X-F5, severity: Medium, aim: deliverable, fix_induced: true, component: worktree-prune, disposition: fixed}
  - {id: R3-X-F6, severity: Low, aim: test, fix_induced: true, component: worktree-prune, disposition: fixed}
  - {id: R3-X-F7, severity: Low, aim: deliverable, fix_induced: true, component: worktree-prune, disposition: fixed}
```

Codex half: `docs/reviews/codex/prune-merged-worktrees-r3-codex.md`, on `83168172`, NOT CONVERGED (5 Medium, 2 Low).
None is a loss path: Codex found "no loss of existing worktree contents in the unmodified move sequence". Every finding is
about code the r2 fold added (the placeholder, the gone-remote rule, BY-PEER, `refused.json`, the absolute undo), so all
seven are `fix_induced: true`. Round 2's were all `false`, so this is ONE fix-induced round, not two in a row: THRASHING
(`docs/dev-process.md` Phase 6) is not armed.

Each fix is the simplest one that fails safe: it KEEPS the worktree, or it reports the row loudly with rc 1. It adds
no lock and no lifecycle coordination.

| Finding | Disposition |
|---|---|
| F1 (Medium: a late write between git's rename and the placeholder recreates the directory; rc 0, ARCHIVED, the hook silent) | Fixed. The post-move check is now `rc == 0 and the target is a directory`: the move has happened even if the old path was recreated since. If `leave_placeholder` cannot create its file (`O_EXCL` meets something already there), the row is the new verdict **ARCHIVED-WITHOUT-PLACEHOLDER**. The run exits rc 1, and the hook prints a line with the reason ("git there resolves to the MAIN checkout, move what it holds into the archive by hand") and that row's undo. What is at the old path is never touched. The shared-lock suggestion is not taken: it would be a new state, and the loud report fails safe. Cases (`_AfterMove`: a directory with `late.txt` appears right after the move): rc 1, the verdict, `late.txt` intact, the archive in place; the hook prints it with its undo. Mutations: the old-path condition restored, the verdict dropped, the rc dropped, the hook line dropped. |
| F2 (Medium: with the remote branch deleted, a commit made after the listing is archived) | Fixed. With `origin/<branch>` absent, rule 2 is asked again of the LIVE `HEAD`, after `git status`: `git merge-base --is-ancestor HEAD <oid>` for each merged head. If none answers 0, the worktree is KEPT: "its remote branch is gone and HEAD is not at or under a merged PR's head". The window between this check and the move remains; a move loses nothing, and the placeholder stands. Case (`_CommitBeforeStatus`: a new commit on top of the merged head, made just before `git status`): KEPT, rc 0, in place. Mutations: the listed head asked instead of `HEAD`; the check dropped. |
| F3 (Medium: BY-PEER for a peer interrupted between its rename and git's admin update) | Fixed. BY-PEER now also needs `registered_at`: `git worktree list` names the archive path, at the HEAD this run evaluated. Anything else (a half-finished peer, a peer's archive at another HEAD, or a git call that fails) is FAILED, rc 1. Cases: `_HalfPeer` (a bare `os.rename` into the archive) gives FAILED, and `_PeerMovedOn` (a peer move followed by a commit there) gives FAILED. The r2 `_PeerFirst` case is still BY-PEER. Mutations: the registration check dropped; the HEAD match dropped. |
| F4 (Medium: a placeholder WRITE failure escapes as an exception; the hook prints CANNOT RUN and omits the move) | Fixed. The write and the close are inside `try` (`OSError`, `ValueError`). A failure gives ARCHIVED-WITHOUT-PLACEHOLDER, rc 1, "could not be written (...): it may be empty", with the undo. Cases: the module's `_fdopen` swapped for a function that raises `OSError(28)`. The CLI gives rc 1, the verdict and the undo. The hook names the move in its WORKTREE ARCHIVE line and in the WITHOUT A PLACEHOLDER line, and prints no CANNOT RUN. Mutation: the catch narrowed to an exception that never happens. |
| F5 (Medium: one transient move failure disables archival for ever at that HEAD) | Fixed, the 24 h form. `refused.json` entries are `{head, at}`, and `refused_now` holds one only at the same HEAD and for under `REFUSED_TTL_S` (24 h); after that the worktree is tried and reported again. An r2-format entry (a bare HEAD) reads as absent: one more FAILED, never a move. Matching git's message was rejected because git localises its messages. Cases: remembered 23 h ago gives KEPT, rc 0; 25 h ago gives FAILED, rc 1; an r2-format entry gives FAILED. Mutation: the entry never expires. The two r2 refusal mutations are re-anchored. |
| F6 (Low: removing `O_EXCL` survives the suite) | Fixed. Case (`_AfterMove` with a sentinel FILE at the old path): its bytes are unchanged and the collision is reported, rc 1. Mutation: `O_EXCL` dropped (the file is then opened without truncation and overwritten from byte 0). |
| F7 (Low: the undo is not runnable when a path has a space) | Fixed. `qpath` gives each path `shlex.quote` when it is printable, and `shape`'s withheld form otherwise, so no newline or tab reaches a terminal or the tab-separated log. `undo_cmd`, the CLI's archive path and the hook's template use it. Cases: a repository under `f7 sp/` with the archive `arch ive/` is archived, and the printed undo, run by `sh -c` in the main checkout, restores the worktree, which git lists again. A pure case checks that `shlex.split` round-trips each path and that a newline is withheld. Mutations: no quoting; quoting a non-printable path raw. |

**Tests.** `--self-test` 92/92 (79, plus 13). Mutations 52 (39, plus 13 new; 4 re-anchored: the post-move check, the
refusal kept, the refusal recorded and BY-PEER, whose code changed). All are killed and attributed
(`check-plan-code.py --mutate . --only scripts/prune-merged-worktrees.py --allow-long-local`). Pin 39 -> 52 in
`scripts/mutations/expected_mutations.py`.

**Verdict.** STOPPED AT THE CAP. Round 3 is the cap (`docs/review-method.md` §0 Q4c). Findings went from 13 (r1) to 10
(r2) to 7 (r3). Since the r1 redesign none has been a loss path, and none of r3's is a BLOCKER, so r3 is folded and the
review loop stops here.

**Round 4.** ONE scoped verification round, the Claude half, over THIS fold only (the r3 diff:
`leave_placeholder`, `registered_at`, `refused_now`, `qpath`, the live-HEAD check, the new verdict through the CLI, hook
and rc, and the new cases and mutations). Its non-BLOCKER findings are FILED, not folded. A BLOCKER is folded.
