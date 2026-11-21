Reviewed head: 593ca25d17d67afef3408a27cd9d9cc196dd866f

# Round 3 — `usage-hook-master` (PR #610, backlog #513) — Claude half

Subject: the round-2 fold, `git diff dc858963..593ca25d`, mainly `.claude/hooks/run-hook.sh:96-150`.
Claim under attack: *every launch of a `usage-pace-*` hook runs the right copy or prints NOT RUN.*

Every world below was built in a scratch directory outside the repository (`.../scratchpad/610r3/`) with real
`git init`, `git worktree add`, `git submodule add` and `git init --separate-git-dir` (git 2.49.0). Each runs the head
launcher as `cd <dir> && env -u CLAUDE_PROJECT_DIR bash run-hook.sh usage-pace-x.sh`. Each checkout's hook prints
`RAN:<its label>`, so the output names the copy that ran.

## Self-test

`python3 scripts/check-run-hook.py --self-test` exits 0 and prints `149/149 self-test cases passed`.

## Findings

### C1 — MAJOR — a worktree whose `.git` names the main checkout's `.git` directory runs the WORKTREE's copy

- **Where:** `.claude/hooks/run-hook.sh:145-149`. In the no-`commondir` branch, a gitdir that passes `is_repo` and
  is not at a worktree's path keeps `root` unchanged, so the hook runs from the directory that holds the `.git` file.
- **Input:** a healthy `git worktree add ../wB`, then `echo "gitdir: $S/main/.git" > wB/.git`.
- **Observed:** `RAN:WT`, rc=0. In `wB`, git reports `--git-common-dir` = `$S/main/.git`, and `git worktree list`
  lists `$S/main` FIRST and `wB` second.
- **Why it refutes the claim:** the launcher states its own rule at lines 89-92 (r1 C2): main is the common dir's
  parent, the checkout `git worktree list` names first. Git says this checkout shares main's repository and that
  `main` is the main checkout, yet the copy that runs is the worktree's, which is exactly the one this guard refuses
  to trust. This is a one-line edit of an untracked file, the same class of hand-made layout as r2's X1 (rated
  Blocking). It needs no `commondir` to be removed and no `objects/` to be made.
- **Related, same branch (B2):** X1 by relocation. `mv main/.git/worktrees/wB2 main/.git/wB2moved`, remove its
  `commondir`, `mkdir objects`, and repoint `wB2/.git`. Observed `RAN:WT`. The r2 path rule decides only at
  `<x>/worktrees/<name>`, so moving the gitdir one level escapes it. To git this gitdir really is a separate
  repository, so this is within the stated spec ("a submodule / separate-git-dir keeps its own copy"). It shows that
  the path rule closes X1's exact input, not its class: anything that can rewrite `.git` chooses the repository.
- **Suggested fix (a hypothesis):** in the no-`commondir` branch, when the gitdir's basename is `.git` and its
  parent is not `$root`, the gitdir belongs to another checkout. Either set `root` to that parent, as the
  `commondir` branch does, or NOT RUN. A real submodule (`.git/modules/<name>`) and a `--separate-git-dir` under
  another name are unaffected.
- **Caused by the r2 fold:** NO. The no-`commondir` branch accepted a repository gitdir before r2; the r1 `objects/`
  test passes `main/.git` too.

### M1 — MINOR — a `--separate-git-dir` main checkout whose git dir sits under a folder named `worktrees` is NOT RUN

- **Where:** `.claude/hooks/run-hook.sh:145`, the r2 path rule.
- **Input:** `mkdir -p gitdirs/worktrees; git init --separate-git-dir=$S/gitdirs/worktrees/proj mK`.
  `git rev-parse --show-toplevel` in `mK` gives `$S/mK`, so it is a main checkout.
- **Observed:** `run-hook: NOT RUN usage-pace-x.sh — the gitdir .../gitdirs/worktrees/proj is a worktree's
  (…/worktrees/<name>) and has no commondir (backlog #513 r2)`, the JSON line, rc=0. Before r2 this ran `RAN:MK`.
- It fails closed, and the layout is rare. It is a sibling of the bound the r2 coordinator doc already accepted (a
  submodule at path `worktrees/x`, reproduced here too: `sup/worktrees/x` gives the same NOT RUN reason).
- **Caused by the r2 fold:** YES. The path rule is new in r2. This is the same accepted-bound class, a fail-closed
  refusal, so whether it counts toward the Phase 6 thrashing pair is the coordinator's call. It never runs a wrong
  copy.

### M2 — MINOR — the bound the r2 coordinator doc says is "stated in the launcher's comment" is not there

- **Where:** `docs/reviews/coordinator/usage-hook-master-r2-coordinator.md:61` claims: *"Bound, stated in the
  launcher's comment: a submodule whose NAME is `worktrees/<x>` … is NOT RUN."* `run-hook.sh:78-82` describes the
  path rule but never states this bound. Running `grep -n -i "submodule whose\|whose name"` over `run-hook.sh` and
  `check-run-hook.py` finds nothing. The same bound covers M1's separate-git-dir case.
- **Fix:** add one comment line under line 78–79 naming both refused layouts.
- **Caused by the r2 fold:** YES (documentation only).

### M3 — MINOR — worktrees of a bare repository and of a submodule are NOT RUN

- **Where:** `run-hook.sh:135`, the `.git` name rule.
- **Inputs and output:** `git clone --bare main bare.git; git -C bare.git worktree add ../w3d` gives NOT RUN
  ("cannot be located"). A worktree of a real submodule (common dir `sup/.git/modules/lib`) gives the same NOT RUN.
  A worktree of a `--separate-git-dir=$S/sepstore/sep.git` main gives the same NOT RUN.
- Each fails closed with the JSON line and rc=0, and none runs the worktree's copy. The bare-repo-plus-worktrees
  workflow is fairly common elsewhere, but not in this repository.
- **Caused by the r2 fold:** NO. The name rule predates r1 (u4).

## Attempts that did NOT refute (controls)

| World | Observed |
|---|---|
| healthy worktree | `RAN:MAIN` |
| `.git` names the gitdir through a symlink | `RAN:MAIN` |
| relative gitdir with a trailing `/`, commondir `../../` | `RAN:M1B` (main) |
| commondir = absolute symlink to main's `.git` | `RAN:M1C` (main) |
| `git worktree add --relative-paths` | `RAN:MAIN` |
| `.git` file path in different letter case (APFS) | `RAN:MAIN` |
| reftable main repository (`--ref-format=reftable`; `refs/` still a dir) | `RAN:MRT` (main) |
| main `.git/worktrees` replaced by a symlink elsewhere | NOT RUN, and git itself fails (`fatal: not a git repository`) |
| main `.git` a symlink to `store/m1e.git` | NOT RUN (name rule) |
| main `.git` a symlink to `store2/.git`, hook there | `RAN:STORE2`, the stated r1 C2 bound; never WT |
| `core.worktree` main (`.git` at `m3c-gd`, work tree `m3c`) | `RAN:GDPARENT`, which matches `git worktree list`'s first line; never WT |
| real submodule; nested submodule; submodule inside a worktree | own copy (`SUB`, `INNER`, `SUB`); superproject worktree `SUPWT` |
| separate-git-dir main checkout itself | `RAN:M3A` |

Containment (`${gitdir%/*} = $common/worktrees`, both `cd -P`) held under every symlink and `..` variant tried. No
decoy passed it without containing the gitdir.

## Summary

| Id | Severity | Runs a wrong copy? | Caused by r2 fold |
|---|---|---|---|
| C1 | MAJOR | YES, the worktree's own | no |
| M1 | MINOR | no (fail-closed refusal) | yes |
| M2 | MINOR | no (doc claim false) | yes |
| M3 | MINOR | no (fail-closed refusal) | no |

C1 refutes the claim. It was not introduced by the r2 fold, so it does not by itself form a thrashing pair. M1 and
M2 are fold-caused, but neither runs a wrong copy.

VERDICT: NOT CONVERGED
