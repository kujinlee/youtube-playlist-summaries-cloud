Reviewed head: ca56bebe4c0bc525e1bdaa5a826ef9f49ea4c859

# PR #610 (backlog #513), round 1, Claude half: adversarial review

Subject: `git diff origin/master...HEAD`. The change makes `.claude/hooks/run-hook.sh` run the MAIN checkout's copy of
a `usage-pace-*` hook when launched from a linked worktree. The claim under test is that the worktree's own copy is
never run, and that an unlocatable main checkout is NOT RUN.

Method: I built real layouts with `git init` / `git worktree add` (git 2.49.0, `GIT_CONFIG_GLOBAL=/dev/null`) under the
session scratchpad (`.../scratchpad/610r1-claude/w/`). I ran this head's launcher and origin/master's launcher
(`git show origin/master:.claude/hooks/run-hook.sh`) from each one, with `CLAUDE_PROJECT_DIR` unset. Each checkout got
a `usage-pace-probe.sh` and a `probe.sh` that print which checkout they came from. I did NOT run the mutation sweep. I
applied u4 and u5 by hand to scratch copies of the launcher, outside the worktree.

`python3 scripts/check-run-hook.py --self-test`, which took 15.6 s, printed: **`99/99 self-test cases passed`** (exit 0).

## Layouts run

| Layout | This head | origin/master | Verdict |
|---|---|---|---|
| Worktree, absolute gitdir, path with spaces (`main repo`, `wt a`) | RAN MAIN, rc 0 | RAN WT | correct |
| Relative gitdir (`-c worktree.useRelativePaths=true`, `.git` = `gitdir: ../main repo/.git/worktrees/wt-rel`) | RAN MAIN | RAN WT | correct |
| Worktree of a worktree (`git -C "wt a" worktree add wt2`) | RAN MAIN | RAN WT2 | correct |
| **Stale gitdir: `.git/worktrees/wtstale` moved away** | **RAN STALE (the worktree's copy), rc 0** | RAN STALE | **C1** |
| **Main checkout renamed (`mv mv1 mv1-renamed`): the worktree's absolute gitdir is now dangling** | **RAN MV1WT (the worktree's copy), rc 0** | RAN MV1WT | **C1** |
| gitdir present, `commondir` removed | RAN STALE (the worktree's copy), rc 0 | same | C1 |
| commondir names the main `.git` through a symlinked alias (`alias-main -> main repo`) | RAN MAIN | RAN WTALIAS | correct |
| Main `.git` is a symlink to a dir NOT named `.git` | NOT RUN, rc 1, stderr only | RAN WT | refuses (C3) |
| **Main `.git` is a symlink to `store/proj/.git`** | **RAN STOREMAIN (a third checkout)** | RAN SYMWT | **C2** |
| Main checkout's `.git` is a FILE (`--separate-git-dir=sep/repo.git`), launched in main | RAN SEPMAIN | RAN SEPMAIN | correct (no commondir, so unchanged) |
| Worktree of that separate-git-dir main | NOT RUN, rc 1, stderr only | RAN SEPWT | refuses (C3) |
| **Separate git dir that happens to be named `.git` (`elsewhere/x/.git`), worktree of it** | **RAN DECOY (`elsewhere/x`, not a checkout)** | RAN SEP2WT | **C2** |
| Bare clone + `git worktree add` | NOT RUN, rc 1, stderr only | RAN BAREWT | refuses (C3) |

**Non-usage hooks:** `probe.sh` and a missing `missing.sh` gave byte-identical output and exit codes under both
launchers in all 13 directories, plus one outside every checkout. Only `usage-pace-probe.sh` differs. The new block is
gated on `case $name in usage-pace-*)`, and nothing outside it changed. So "every other hook is unchanged" holds.

## Findings

### C1 — BLOCKER — `.claude/hooks/run-hook.sh:83`: a stale or broken gitdir runs the WORKTREE's own copy

The `.git` file's existence is the only signal of a linked worktree. If `$gitdir/commondir` is not a file, the
`if [ -f "$gitdir/commondir" ]` block is skipped without a word and `root` stays at the worktree. That is the
submodule path, which U3 relies on. The same branch is also taken when the gitdir **does not exist at all**. So in that
case the launcher runs the branch's copy, which is exactly what the PR says it never does.

- **Failing input 1:** `git -C mv1 worktree add mv1-wt; mv mv1 mv1-renamed; cd mv1-wt; bash run-hook.sh usage-pace-probe.sh`.
  **Observed: `RAN MV1WT`, rc 0.** The worktree's copy ran, and there was no NOT RUN line. Renaming or moving the main
  checkout is an ordinary accident and fits the threat model the PR states ("ACCIDENT, NOT A HOSTILE BRANCH").
- **Failing input 2:** move `main/.git/worktrees/wtstale` away, for example with `git worktree prune` after a move.
  **Observed: `RAN STALE`, rc 0.**
- **Failing input 3:** the gitdir exists but has no `commondir`. **Observed: `RAN STALE`, rc 0.** This case is harder
  to tell apart from a submodule, but a missing gitdir is not.
- **Fix direction:** when `$gitdir` is not a directory, return NOT RUN. Only a gitdir that exists, has no `commondir`
  and looks like a submodule should keep the root. A world needs adding for the dangling gitdir: U4 covers a
  *commondir* that names a missing dir, but no world covers a *gitdir* that is missing.

### C2 — MINOR — `.claude/hooks/run-hook.sh:91,96`: "the common dir is named `.git`" does not prove its parent is the main checkout

After `cd -P`, the launcher takes the PHYSICAL common dir's parent as the main checkout. When the main checkout's
`.git` is a symlink, or a `--separate-git-dir` that happens to be named `.git`, that parent is a different directory.
The launcher then runs *its* `usage-pace-*` copy.

- **Failing input:** main `symmain/.git -> store/proj/.git`, worktree `symwt`. **Observed: `RAN STOREMAIN`**, the hook of
  `store/proj` and not of `symmain`.
- **Failing input:** `git init --separate-git-dir=elsewhere/x/.git sep2`, then a worktree `sep2wt`, with hooks placed
  in `elsewhere/x`. **Observed: `RAN DECOY`.** `elsewhere/x` is not a checkout of anything.
- Neither case runs the worktree's copy. Both run a copy the PR's claim does not name. The layouts are unusual, so this
  is MINOR. The honest bound should be stated in the header comment, or the launcher should check `core.worktree` /
  `core.bare`. That check would mean reading the config, which the "no git process" design avoids.

### C3 — MINOR — `.claude/hooks/run-hook.sh:79,92-94`: a usage-pace NOT RUN signals on stderr only, against usage-pace-run.sh's own contract

Every new NOT RUN path exits 1 with stderr only. The general launcher's L5 permits this ("visible, not blocking").
But `usage-pace-run.sh:32` records a security review finding that *"stderr alone is not seen"*, and so it always emits
a `systemMessage` / `additionalContext` at exit 0 when it cannot run. This PR adds a new way for the pace guard to
vanish, and it skips that contract.

- **Failing input:** a bare clone plus `git worktree add barewt`, or a worktree of a `--separate-git-dir` main.
  **Observed:** `NOT RUN usage-pace-probe.sh — the main checkout of the worktree … cannot be located`, rc 1, nothing on
  stdout.
- In such a layout the weekly-limit guard is now **permanently off** for every prompt, spawn and wake. On origin/master
  it ran (from the worktree's copy). The only signal is the harness's non-blocking-error stderr. It does not exit 0
  silently, but by the repo's own measured standard it is not seen. The bare-repo layout is common in general, but it
  is not this repo's layout, hence MINOR. The fix could emit the same fixed JSON line that `cannot()` uses, or record
  this as a stated limit.

### C4 — MINOR — `scripts/check-run-hook.py:423-424`: the "U4 commondir names a missing directory" case cannot go red under its fix's removal

`wtgone` has `commondir` pointing at a dir that does not exist. Two things protect it in the code: the `|| common=`
plus the name check, and the `exit 1` after the refusal. I applied each mutant by hand to a scratch copy of the
launcher and ran it in an equivalent layout:

- **u4** (`[ "${common##*/}" != .git ]` → `false`): `common` is empty, so `root=""` and `hook=/.claude/hooks/usage-pace-probe.sh`.
  **Observed:** `NOT RUN usage-pace-probe.sh —  has no .claude/hooks/usage-pace-probe.sh`, rc 1. The case's `(1, NOT_RAN)`
  stays **green**.
- **u5** (`exit 1` → `:`): **Observed:** both NOT RUN lines print and the result is rc 1. The case is still **green**.

So this case passes for an ambient reason: an empty root reaches a nonexistent `/.claude/hooks`. Only `wtbare` (U4
proper) kills u4 and u5, and the mutants name only that case, so nothing marks this case as unprotected. The fix
would assert the U4 message (`backlog #513` in stderr) for `wtgone` as well, or add `wtgone` to the `USAGE_MSG_CASE`
check.

The other cases go red when their fix is removed:

- U1 and U2 die under u1.
- U2 dies under u2, but only through the C1 fall-through, which runs the worktree's copy.
- U1 dies under u3.
- U5 dies under u6.
- U3 dies under u7.
- U6 dies under u8.
- "U1 … in the main checkout" has no fix to remove. It is a regression pin and cannot go red under any u-mutant.

### C5 — MINOR — `scripts/check-run-hook.py:54`: the stated case count is stale

The docstring says `--self-test  # 98 cases`, but the run printed `99/99 self-test cases passed`. The docstring
contradicts the suite's own output.

## Summary

The core redirect works for absolute, relative, spaced, nested and worktree-of-worktree layouts. Non-usage hooks are
byte-identical to origin/master. C1 refutes the PR's central invariant: a dangling gitdir, for example after the main
checkout is renamed, runs the worktree's own copy with rc 0 and no NOT RUN line. No world tests that input.

VERDICT: NOT CONVERGED
