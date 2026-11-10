<!-- codex-review: model=gpt-6.1-sol -->

**F1 — BLOCKER — Ignored filenames are treated as proof that content is disposable.**  
`scripts/prune-merged-worktrees.py:168–178`

Reproduced in disposable repositories: both worktrees returned `REMOVED`, destroying unique content:

- `research.log`, ignored through `.git/info/exclude`, containing unique research.
- An independent Git repository under ignored `node_modules/private/`, containing its only commit.

Neither content is backed up. Any ignored `*.log` qualifies, and any path containing `node_modules` or `__pycache__` qualifies regardless of its contents.

**Fix:** Preserve ignored content before deletion, or require explicit ownership metadata for disposable directories and reject nested repositories. Restrict log exemptions to exact, documented hook paths. Add destructive regression cases for both reproductions.

**F2 — BLOCKER — Index flags hide unique tracked edits from both safety checks.**  
`scripts/prune-merged-worktrees.py:273`, `:328`

Reproduced separately with `git update-index --assume-unchanged f` and `git update-index --skip-worktree f`, followed by an uncommitted edit to `f`. Both worktrees returned `REMOVED`; their unique edits disappeared. Ordinary `git status` and unforced `git worktree remove` both trusted those flags.

**Fix:** Reject worktrees with either flag, or verify tracked contents using an independent index without those flags. Add cases for both; the existing tracked-change mutation does not exercise this path.

**F3 — BLOCKER — A concurrent writer can add unique ignored work after inspection.**  
`scripts/prune-merged-worktrees.py:273–290`, `:303–328`

Reproduced by inserting a write of ignored `.env.local` immediately before the actual removal command, after evaluation completed. Git removed the worktree and the unique file. The same interval allows `.remember/` changes after its backup.

The cwd check protects only this process. Another live session can occupy the candidate worktree without leaving a detectable change or lock.

**Fix:** Require an exclusive lifecycle lock honored by every session and writer, and refuse automatic deletion without it. Rechecking status narrows the race but cannot close it. Backups must occur while exclusive ownership is held.

**F4 — MEDIUM — A deadline after deletion falsely reports that nothing was removed.**  
`scripts/prune-merged-worktrees.py:350–360`, `:414–416`

Fault injection reproduced this output after the first worktree had actually been removed:

```text
rc: 2
=== WORKTREE PRUNE: CANNOT RUN — injected deadline on next git call; NOTHING was removed (treat as NOT RUN) ===
actually removed: ['a']
```

A timeout during `git worktree remove` can likewise leave partial deletion while producing that assurance.

**Fix:** Retain completed results across failures. Distinguish preflight failure from interruption after mutation began; report completed removals and any partially removed candidate explicitly.

**F5 — MEDIUM — The hook’s deadline excludes filesystem traversal and copying.**  
`.claude/hooks/session-state.sh:19–21`; `scripts/prune-merged-worktrees.py:204–211`, `:303–319`

The shell subtraction accounts for elapsed whole seconds, but the resulting budget bounds subprocess calls only. `os.walk`, `shutil.copytree`, and log filesystem operations can exceed it. A large `.remember/` or slow filesystem can consume the remaining hook timeout before Python prints its result. The six-second removal threshold does not bound these operations.

**Fix:** Bound backup and traversal work under the shared deadline, and defer deletion when backup cannot finish safely. Test the combined hook with slow backup I/O and interrupted removal.

Validation: **51/51 self-tests passed despite these counterexamples.** The 18 mutations omit index flags, concurrent writes, nested repository preservation, post-removal timeout reporting, and bounded backup operations. The shell deadline arithmetic is unreachable by the current Python-only mutation manifest and self-test.

Could not check: the mutation sweep was not rerun; actual macOS timeout/partial-deletion behavior and live-session coordination were not exercised. Tested ordinary symlinked `node_modules`: its external target survived. Paths containing spaces worked. No repository files were changed, no GitHub actions were taken, and nothing under `.claude/plans/` was read.

NOT CONVERGED
