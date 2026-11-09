# Round 1 — `prune-merged-worktrees` — coordinator

```yaml
round: 1
fixes_nontrivial: true
subject: prune-merged-worktrees
halves:
  codex: ran
  claude: ran
findings:
  - {id: R1-X-F1, severity: Blocking, aim: deliverable, fix_induced: false, component: worktree-prune, disposition: fixed}
  - {id: R1-X-F2, severity: Blocking, aim: deliverable, fix_induced: false, component: worktree-prune, disposition: fixed}
  - {id: R1-X-F3, severity: Blocking, aim: deliverable, fix_induced: false, component: worktree-prune, disposition: fixed}
  - {id: R1-X-F4, severity: Medium, aim: deliverable, fix_induced: false, component: worktree-prune, disposition: fixed}
  - {id: R1-X-F5, severity: Medium, aim: deliverable, fix_induced: false, component: worktree-prune, disposition: fixed}
  - {id: R1-C-F1, severity: High, aim: deliverable, fix_induced: false, component: worktree-prune, disposition: fixed}
  - {id: R1-C-F2, severity: High, aim: deliverable, fix_induced: false, component: worktree-prune, disposition: fixed}
  - {id: R1-C-F3, severity: Medium, aim: deliverable, fix_induced: false, component: worktree-prune, disposition: fixed}
  - {id: R1-C-F4, severity: Medium, aim: instrument, fix_induced: false, component: worktree-prune, disposition: fixed}
  - {id: R1-C-F5, severity: Low, aim: deliverable, fix_induced: false, component: worktree-prune, disposition: fixed}
  - {id: R1-C-F6, severity: Low, aim: deliverable, fix_induced: false, component: worktree-prune, disposition: fixed}
  - {id: R1-C-F7, severity: Low, aim: deliverable, fix_induced: false, component: worktree-prune, disposition: fixed}
  - {id: R1-C-F8, severity: Low, aim: deliverable, fix_induced: false, component: worktree-prune, disposition: fixed}
```

Claude half: `docs/reviews/claude/prune-merged-worktrees-r1-claude.md`, on `1fc9e7bf`, NOT CONVERGED (2 High, 2 Medium, 4 Low).
Codex half: `docs/reviews/codex/prune-merged-worktrees-r1-codex.md`, on `1fc9e7bf`, NOT CONVERGED (3 Blocking, 2 Medium).

**Fold: a REDESIGN, not a patch. ARCHIVE, NEVER DELETE.** Every data-loss finding (Codex F1, F2, F3; Claude F2, F3, F5)
has one root: `git worktree remove` is irreversible, so each rule had to be perfect, and check-then-delete always leaves
a window. Patching each (an index-flag read, a reflog walk, an exact log allowlist, a lifecycle lock) would have added
four more rules that each had to be perfect. Instead the script now runs `git worktree move <wt>
~/.worktree-archive/<repo>/<name>` (no `--force`): one `rename(2)` on the same filesystem, which carries every file,
every index flag, every late write and the worktree's own `<common>/worktrees/<name>/` (its HEAD reflog) along with it.
The script deletes NOTHING. The allowlist, the ignored-content classification and the `.remember/` copy are removed: they
no longer guard anything. The rules that stay (merged PR and the reuse rule, no open PR, no tracked change or unpushed
commit, not locked, not the cwd) now prevent DISRUPTION, not loss; two disruption guards are new (no process cwd inside,
from one `lsof -d cwd -Fn` that fails closed; no PR merged under 2 h ago). A cross-device archive is KEPT, since a move
across devices copies, and a copy is not atomic. Undo: `git worktree move <archive path> .claude/worktrees/<name>`.

| Finding | Disposition |
|---|---|
| Codex F1 (ignored files treated as disposable; a nested repo under `node_modules/`) | Fixed by the redesign: nothing is deleted, so no classification is needed and none remains. Case: `.env.local`, `research.log` and `node_modules/private/only-copy.txt` are asserted byte for byte in the archive. |
| Codex F2 / Claude F2 (`skip-worktree` / `assume-unchanged` edits hidden from `git status`) | Fixed by the redesign: the edited file moves with the directory. Case asserts both edited files' bytes in the archive. |
| Codex F3 (a concurrent writer after the checks) | Fixed by the redesign for LOSS: a write that lands before the rename moves with it; a write after it fails or lands nowhere it can destroy. For DISRUPTION, the new `lsof` cwd guard keeps a worktree any running process sits in (case `busy`; `lsof` failing archives nothing, case with a real-looking answer and rc 1), and the 2 h guard keeps freshly merged ones (case `recent`). Bound, stated in the docstring: a process holding a file open there without its cwd inside is not seen. |
| Codex F4 / Claude F1 (a deadline after a removal prints "NOTHING was removed") | Fixed. `CannotRun` is caught per worktree inside the loop; the rows already archived are kept and printed FIRST; the CANNOT RUN line comes last and says "archived N before it stopped" (it says NOTHING only when no move started). A move interrupted at the deadline is FAILED with both sides named (source exists/GONE, target exists/absent). The loop also stops, DEFERRED, when under 5 s is left. Cases: an injected deadline after the first move (rc 2, the move named, the line last and not "NOTHING"), and a near deadline deferring without touching. |
| Codex F5 / Claude F8 (the hook's deadline excludes traversal and copying; no `--repo`) | Fixed. No `os.walk` and no copy remain: the work is the `gh` call, one `lsof`, git status reads, renames and one directory listing, all subprocesses under the one `Budget`; the archive-size `du -sk` runs only with over 5 s left and is skipped otherwise. The hook now passes `--repo "$REPO_ROOT"`. |
| Claude F3 (the worktree's own HEAD reflog lost) | Fixed by the redesign: a move keeps `<common>/worktrees/<name>/` registered. Case: a detached commit left behind by a checkout is still in `git -C <archived> reflog`. |
| Claude F4 (fail-closed paths with no case or mutation) | Fixed for every path that still exists: the unwritable log (a regular file as `--log-dir`, every candidate KEPT, nothing moved), the deadline deferral, the detached HEAD, the half-moved message each have a case and a mutation. The deletion-era ones (`.remember` copy failure and collision, `HOOK_MAX_REMOVE`) are gone with the code. Remaining, stated: the `git status exited` and `git rev-list exited` branches still have no case; both are KEEPs. |
| Claude F5 (every ignored `*.log` regenerable) | Fixed by the redesign: no ignored file is classified or deleted. |
| Claude F6 (a live agent in an unlocked merged worktree loses its cwd) | Fixed: `mergedAt` is read and a PR merged under 2 h ago keeps its worktree; a merged row without `mergedAt` is CANNOT RUN. Also covered by the `lsof` guard. |
| Claude F7 (a half-deleted worktree advised to `git worktree prune`) | Fixed: a `prunable` worktree whose directory still exists now reads "its .git link is missing (a half-finished move or removal?): inspect it by hand". Case and mutation. |

**Tests.** `--self-test` 65/65; the manifest is rewritten, 27 mutations (the 18 deletion-era entries replaced, not
re-anchored), 27 killed and attributed (`check-plan-code.py --mutate . --only scripts/prune-merged-worktrees.py`). Real-repo `--dry-run`: 6 worktrees, all KEPT.

**Verdict.** Both halves NOT CONVERGED. The fold is a redesign, so round 2 runs.

**Round 2.** One half, Claude (alternation after a round 1 with both), on the redesigned script, hook and row.

REVIEW GAP: codex — alternation
