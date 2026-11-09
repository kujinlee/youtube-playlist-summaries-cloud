Reviewed head: 1fc9e7bf0b61285f76c0e99dee26f1937416357f

# Adversarial review, round 1 (Claude half): SessionStart removes merged worktrees (PR #551, backlog #589)

Mandate: REFUTE "it never deletes work that exists nowhere else". Method: I built throwaway repositories (bare
origin + main clone + worktrees under `main/.claude/worktrees/`, a fake `gh` printing a constructed PR list) in
the session scratchpad. I ran the script for real against those worktrees, never against this repository
(only `--dry-run` and `--self-test` here). `--self-test`: 51/51 pass at this head.

## Findings

### F1 — HIGH — a deadline after a removal prints "NOTHING was removed"
`run()` (`scripts/prune-merged-worktrees.py`, the `except CannotRun` in `run`) catches the `CannotRun` that
`Budget.call` raises at the deadline and prints a fixed sentence: `CANNOT RUN — …; NOTHING was removed (treat as
NOT RUN)`. But `prune()` evaluates and removes worktree by worktree, so the deadline can fire after earlier
removals, or during the `git worktree remove` of the current one. Then the sentence is false and the `rows`
naming what was removed are thrown away. The docstring's "the PR list is read in full before any worktree is
touched" covers only the `gh` failure.

Reproduced: two merged, clean worktrees `aaa` and `zzz`, and a `git` wrapper first on PATH that sleeps 30 s on
`status` for `zzz`:
```
--hook --deadline 12  →  === WORKTREE PRUNE: CANNOT RUN — the check passed its 12s deadline during git status;
                          NOTHING was removed (treat as NOT RUN) ===
ls .claude/worktrees  →  zzz          (aaa is GONE)
log.tsv               →  …  aaa  aaa  cd39da5f…  removing  -
```
When the deadline instead kills the `git worktree remove` in flight (SIGKILL to its process group), the session
is also told NOTHING was removed. In fact a directory is half-deleted, and its log line says `removing` with no
outcome. This is the hook nobody watches, so it is the one place where the output has to be true.

**Fix:** catch `CannotRun` per worktree inside `prune()`. Mark the current row `FAILED` (if a removal was in
flight, log `failed: deadline`) or `DEFERRED`, stop the loop, and return the rows. Print "NOTHING was removed"
only when no removal had started. Add a case using the PATH-wrapper construction above.

### F2 — HIGH — a `skip-worktree` / `assume-unchanged` edit is deleted with no copy
Neither `git status` nor `git worktree remove` (without `--force`) reports a modified file whose index entry has
the skip-worktree or assume-unchanged bit set. Rule 2 ("no tracked changes") therefore cannot see the edit. The
index is per-worktree, so the edit exists nowhere else.

Reproduced: in merged, pushed worktree `skipwt`, `git update-index --skip-worktree a.txt; echo "LOCAL EDIT" >> a.txt`
→ `git status --porcelain` is empty → the real run prints `REMOVED skipwt`, and the edit is gone. This refutes the
guarantee directly. It is rare here: nothing in `scripts/` or the hooks sets these bits.
**Fix:** one more read in `evaluate`: `git ls-files -v -z`. Keep the worktree when any entry's tag is lowercase
(assume-unchanged) or `S` (skip-worktree), with the reason "index hides changes (skip-worktree/assume-unchanged)".
Add a case and a mutation.

### F3 — MEDIUM — commits reachable only from the worktree's own HEAD reflog become unreachable
`git worktree remove` deletes `<common>/worktrees/<name>/`, which holds this worktree's `logs/HEAD`, its
`refs/worktree/*` and `refs/bisect/*`. The branch reflog is kept, because it lives in the common dir. A commit
made on a detached HEAD and then left behind by `git checkout <branch>` survives only in that HEAD reflog.

Reproduced: worktree `reflog`: `checkout --detach; commit UNIQUE; checkout reflog` → `REMOVED reflog` → `git fsck
--unreachable --no-reflogs` lists the UNIQUE commit as `unreachable commit 3967c172…`. `gc` will collect it once
`gc.pruneExpire` passes. Mitigation: git warned "leaving 1 commit behind" at the checkout, and the object can
still be recovered until gc. That is why this is MEDIUM rather than HIGH.
**Fix:** before removal, list `git -C <wt> rev-list --walk-reflogs HEAD` (or read `logs/HEAD`) minus what is
reachable from `--branches --remotes --tags`. If that set is non-empty, keep the worktree. Alternatively, write
each such tip to `refs/pruned/<name>/<n>` and record it in the log. Apply the same rule to any
`refs/worktree/*` and `refs/bisect/*` ref.

### F4 — MEDIUM — fail-closed paths and two rules have no case, and no mutation can reach them
Every one of these is a KEEP or a bound the docstring states, and none of them is exercised by the self-test
(searched `_self_test_body` for DEFERRED, max_remove, REMOVE_MIN, copy target, could not write; none found). No
manifest entry reaches them either:
- **"a log that cannot be written keeps the worktree"**: the `return` after `could not write the log`. Delete
  it and the worktree is removed unlogged. This is a stated guarantee.
- the `.remember` copy failure (`could not copy .remember`) and the copy-target collision → KEPT;
- `HOOK_MAX_REMOVE` / `REMOVE_MIN_S` → DEFERRED. The F1 and F7 half-deletion risk rests on these two bounds;
- `git status exited` and `git rev-list exited` → KEPT. Masked, partly: the status rc path still keeps the
  worktree through `git worktree remove`'s own refusal only when the tree is dirty;
- `detached HEAD`: no mutation. It is masked by "no merged PR" (`idx.get(None)`), but the reason text changes,
  so the existing `detached` case WOULD go red. The mutation is cheap.

Each of these needs a case plus a manifest entry. For the log one, point `--log-dir` at a read-only directory
or at a regular file.

### F5 — LOW — every ignored `*.log` is classified regenerable, including user-excluded files and evidence logs
`ignored_kind` returns `"regen"` for any ignored non-directory ending in `.log`, whatever ignores it: the
repository `.gitignore`, `.git/info/exclude` or a global excludes file. Reproduced: `notes.log` added to
`info/exclude`, holding "my notes" → `REMOVED infoexc`, and the file is gone.

`.gitignore` also ignores `.claude/ci-unwatched.log`, which it describes as "the evidence base for its
false-alarm rate". A worktree's copy of that log is deleted by this rule. This is a design choice, but a broader
one than the docstring's "hook caches and logs".
**Fix:** replace the suffix rule with an explicit list of the hook log names (the same list `.gitignore`
carries), or copy ignored `*.log` files aside the way `.remember/` is copied.

### F6 — LOW — a live session or agent in an UNLOCKED merged worktree loses its cwd
This is documented in BOUNDS. But the window is exactly the coordinator's post-merge moment, when a review half
or fold agent may still sit in that worktree. This review and the concurrent Codex half are running in
`prune-wt`, which is unlocked. Nothing is lost that was written, but files the agent writes afterwards land in a
non-git directory that no later run sees.
**Fix (cheap):** add `mergedAt` to the `gh` fields, and skip any worktree whose PR merged less than N hours ago
(for example 2 h).

### F7 — LOW — a half-deleted worktree is reported as "its directory is missing" and is advised to `git worktree prune`
When a killed removal has already unlinked the worktree's `.git` file, git marks the worktree `prunable`. The
directory still exists. Reproduced: `rm .claude/worktrees/zzz/.git` → `KEPT zzz: its directory is missing (git
worktree prune clears it)` while `a.txt zzz.txt` are still there. Following that advice drops the metadata and
orphans the directory, and no later run considers it, because it is no longer a worktree. Disk leaks, which is
what this tool exists to stop. No work is lost: the files came from a tree that passed every rule.
**Fix:** for `prunable`, say "its .git link is missing (half-removed?)" when the directory exists, and name the
manual cleanup.

### F8 — LOW — the hook does not pass `--repo "$REPO_ROOT"`
`session-state.sh` computes `REPO_ROOT` but calls the script without `--repo`, so `--repo` falls back to the
hook's cwd. A cwd outside the repository gives a CANNOT RUN line at every session start. Pass
`--repo "$REPO_ROOT"`. `cwd` stays `os.getcwd()` for the cwd rule.

## Checked and NOT refuted
- **Symlinked `node_modules` pointing outside the tree:** the worktree was REMOVED and the target's
  `keep.txt` (PRECIOUS) survived. `git worktree remove` unlinks the link and does not follow it. A symlinked
  `node_modules` that does not match a `node_modules/` (slash) pattern is untracked, so the worktree is kept.
- **A rebase in progress:** porcelain reports `detached`, so the worktree is kept. Bisect also detaches HEAD.
  Stash entries live in the common dir and survive.
- **A squash merge** with HEAD equal to `headRefOid`: removal is correct, because the commits are on GitHub's
  PR ref and the local branch ref is kept.
- **A branch rebased or amended after merge:** HEAD is not an ancestor of the merged head, so it is kept.
- **A fork's merged PR with the same name:** ignored. A fork's OPEN PR keeps the worktree.
- **A `gh` rc ≠ 0, malformed JSON, or a list at the limit:** CANNOT RUN before anything is touched.
- **An untracked nested repo:** listed as `?? nested/`, so the worktree is kept.
- **Hook arithmetic:** `55 - SECONDS` leaves Budget's post-kill drain (≤ 2 s) inside the 60 s timeout. `--hook`
  always exits 0, so the `|| echo` fires only on an import-time crash. That crash prints a full traceback,
  because of `2>&1`, and is not capped at 3 lines (cosmetic).
- **Real-repo `--dry-run` (3 s):** 6 worktrees, all KEPT (3 locked agents of a live pid 69643, cwd, open PR,
  no merged PR).

## Could NOT check
- Worktrees with initialized submodules. By reading, `git worktree remove` refuses them, so they would show up
  as a FAILED line at every session start. Not built.
- Paths with spaces or newlines. By reading, the `-z` parsing is sound and `shape()` placeholders the printed
  name. Not built.
- Real `gh` behaviour for a fork-remote checkout, where `gh` may resolve the parent repository.
- A real removal timing out mid-delete under fseventsd load. F1 and F7 cover the consequences.

VERDICT: NOT CONVERGED
