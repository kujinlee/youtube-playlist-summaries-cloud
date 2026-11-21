# Phase 6 architecture review — `locate-main` in `.claude/hooks/run-hook.sh` (PR #610, backlog #513)

- Subject: the block that finds the main checkout for a `usage-pace-*` hook, branch `usage-hook-master`, read at head
  `593ca25d`.
- Armed by THRASHING in one component, `locate-main`. Round 2's X1 was caused by the r1 fold (its `objects/` test). Round 3's
  M1 was caused by the r2 fold (its `…/worktrees/<name>` path rule). See `docs/reviews/coordinator/usage-hook-master-r{2,3}-coordinator.md`
  and `docs/reviews/claude/usage-hook-master-r3-claude.md`.
- Every claim is tagged **[M]** (measured here: built over real `git init` / `worktree add` / `submodule add` /
  `--separate-git-dir` / `clone --bare`, git 2.49.0) or **[I]** (inferred).

## The evidence: every fold re-derived git, and each re-derivation disagreed with git somewhere new

| Round | Launcher's own test | Layout where it disagreed with git |
|---|---|---|
| r1 | "a gitdir with `objects/` is a submodule" | X1 (r2): a worktree gitdir with `objects/` added |
| r2 | "a no-`commondir` gitdir at `…/worktrees/<n>` is a broken worktree" | M1 (r3): a `--separate-git-dir` main or a submodule under a folder named `worktrees` |
| r2 | "the common dir must be `.git`, a repository, and contain the gitdir" | C1 (r3): a `.git` file naming main's `.git` ran its own copy |

Each fold closed the exact input and opened a neighbour. The questions the launcher was answering are *is this a
repository*, *which repository owns this gitdir* and *which checkout owns that repository*. These are git's own
discovery rules. Copying them in 60 lines of shell means re-implementing `setup_git_directory()`, one layout at a time.
**[M]** for the three rows. **[I]** that the next layout would also have been found.

## Can a redesign remove it? Yes: ask git and stop parsing

The decision is to make git the authority and delete the hand-parsing (`is_repo`, the `.git`-file reader, the
`commondir` reader, containment and the path rule, about 55 lines).

1. One `git -C "$root" rev-parse --path-format=absolute --git-dir --git-common-dir --show-toplevel`, where `$root` is
   the launcher's own walk result. It runs in a subshell that unsets **every exported `GIT_*` name**
   (`compgen -e`, not a hand-kept list), under a 5 s `perl` alarm, because macOS has no `timeout`.
2. `git config --bool core.bare` gives `true`, which means NOT RUN: a bare repository has no main checkout.
3. **How the main checkout is chosen, and why.** It is the checkout that owns the common dir:
   - (a) the common dir is named `.git` → its parent. This is exactly how git names the first entry of `git worktree list`.
   - (b) otherwise, the work tree git reports from inside the common dir. This covers a submodule's
     `.git/modules/<n>`, whose `core.worktree` names it.
   - (c) otherwise, if git-dir == common-dir (a `--separate-git-dir` checkout) → the session's own toplevel.
   - (d) otherwise NOT RUN: a linked worktree whose main git cannot name.

   **Why not the coordinator's literal "git-dir == common-dir → own copy":** r3's C1 input (`wB/.git` = `gitdir:
   main/.git`) has git-dir == common-dir == `main/.git`, yet `git worktree list` names `main` first. The literal rule would
   keep C1 broken; mutant g10 is exactly that rule and is killed by the C1 case. **Why not "the first line of `git
   worktree list`":** for a `--separate-git-dir` checkout it prints the git dir, which is not a checkout. **[M]**
4. Any git failure, timeout, answer that is not three lines, or main with no `.claude/hooks/<name>` is NOT RUN, with the
   same fixed JSON line and exit 0 as before.

**Re-checking r2's rejection of option (c), asking git.** The rejection had two grounds.

- **Cost.** r2 measured 11.8 ms for one `git rev-parse`. That cost is real and quoted below.
- **Environment steering.** PR #409 r2 lost to `GIT_DIR`, `GIT_COMMON_DIR` and `GIT_CEILING_DIRECTORIES`. Steering is
  answered by construction: git sees no `GIT_*` at all. Four cases (GIT_DIR+GIT_WORK_TREE, GIT_COMMON_DIR,
  GIT_CONFIG_COUNT setting core.bare, GIT_CEILING_DIRECTORIES) each run main's copy, and the mutant that deletes the
  sanitization (g0) is killed by all four. **[M]**
- **The W7 cases still pass unchanged.** They pin that no environment steers the launcher for ordinary hooks, and
  ordinary hooks still run no git process. **[M]**

The ground was right for #409's design, which asked git with the session's environment. It does not apply to a
sanitised call.

## Latency, measured (100 launches each, twice, from a linked worktree, macOS)

| Launch | Old launcher (`593ca25d`) | New launcher |
|---|---|---|
| ordinary hook (`probe.sh`) | 10.8 / 11.3 ms | 10.4 / 10.1 ms |
| usage-pace hook | 13.2 / 13.8 ms | 48.9 / 52.1 ms |

The cost is **about +37 ms per usage-pace launch, and nothing for any other hook.** It comes from two
`perl`-alarmed git calls (git ~10.0 ms, perl ~6.6 ms, bash `-c true` 4.6 ms); a submodule worktree pays a third call.
The fast path (common dir named `.git`) is the common case. **[M]**

## What is deliberately NOT handled (stated bounds)

- **A layout git reads as a standalone repository runs its own copy.** This covers r3 B2 and r2's NOCDOBJ, where a
  worktree gitdir was given its own `objects/`. It also covers a hand-edited `commondir` naming another real repository
  (r2's OTHER), or naming a directory with `objects/` and `refs/` but no HEAD (r2's fake-HEAD), which runs that directory's copy. That is git's answer: anyone who can rewrite `.git` or `commondir`
  already chooses the repository git uses for every command.
- **Worktrees of a bare repository, and of a `--separate-git-dir` main checkout, are NOT RUN** (r3 M3). Git names no
  checkout to trust, and failing closed is the rule. A submodule's worktree now runs the submodule's copy.
- **`~/.gitconfig` is still read**, because unsetting `GIT_CONFIG_GLOBAL` restores the default.
- **The 5 s alarm is a ceiling on a hung git**, not a budget. A slow repository makes a hook launch that much slower
  before it fails closed.
- **A symlinked or misnamed `.git` makes its parent "main"**, exactly as git does (r1 C2, unchanged).
