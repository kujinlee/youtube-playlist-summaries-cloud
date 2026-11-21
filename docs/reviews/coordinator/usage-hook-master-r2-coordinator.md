# Round 2 — `usage-hook-master` — coordinator — ⟳ NOT CONVERGED (Codex); both BLOCKERs FIXED

Codex reviewed `dc858963` (PR #610, backlog #513) in `docs/reviews/codex/usage-hook-master-r2-codex.md`: X1 and X2,
both BLOCKER, NOT CONVERGED. The Claude half is a gap by alternation.

REVIEW GAP: claude — alternation (round 2 runs ONE half; round 3 is Claude's).

```yaml
round: 2
fixes_nontrivial: true
subject: usage-hook-master
halves:
  codex: ran
  claude: gap
findings:
  - {id: X1, severity: Blocking, aim: deliverable, fix_induced: true, component: locate-main, disposition: fixed}
  - {id: X2, severity: Blocking, aim: deliverable, fix_induced: false, component: locate-main, disposition: fixed}
```

**Reproduced first.** Both inputs were rebuilt by hand over a real `git init` + `git worktree add` in the
coordinator's scratch directory, running the head launcher:

- X1: the worktree's gitdir lost its `commondir` and gained `objects/`. Output `WORKTREE`, rc 0.
- X2: the gitdir's `commondir` named an empty directory `decoy/.git` with a usage hook beside it. Output `DECOY`, rc 0.

After the fix both are NOT RUN with exit 0 and the JSON line, and a healthy worktree and the main checkout still print
`MAIN`. Inside the suite, the old launcher fails 7 of the new and changed cases; NOCDOBJ ran the worktree's copy and
DECOY ran the decoy's.

**Fix-induced?** X1 is caused by the r1 fold. It added the `objects/` test, and Codex's input satisfies exactly that
test, because a real worktree gitdir already has `HEAD` and `refs/`. X2 is not: the `.git` name test predates r1 (u4).
This is the first round with a fold-caused finding in locate-main. A fold-caused finding there in round 3 would make a
thrashing pair.

## The route — (a)+(b), and why not (c)

Both findings trusted something weaker than the structure git itself relies on. X1 decided *worktree or submodule*
from what the gitdir HOLDS. X2 decided *is this the main repository* from what the common dir is CALLED. The fold
replaces both tests with structural ones:

- **(a) The path decides.** Git always puts a worktree's private gitdir at `<common>/worktrees/<name>`. A gitdir with
  no `commondir` whose parent is named `worktrees` is therefore a broken worktree, and it is NOT RUN whatever it holds.
  Any other gitdir with no `commondir` is its own common dir, as it is for a submodule's `.git/modules/<name>` or a
  `--separate-git-dir` main checkout. That gitdir must pass `is_repo` (HEAD, objects/, refs/), and it keeps its own copy
  as before.
- **(b) The common dir must be a repository that contains the gitdir.** It must still be named `.git`. It must pass
  `is_repo`, and the gitdir's physical parent must be exactly `$common/worktrees`. This is the back-pointer read from
  the common dir's side. It is strictly stronger than reading `$common/worktrees/<name>/gitdir`: a decoy could hold that
  file without holding the gitdir, but containment requires the gitdir itself. A decoy that does contain this
  worktree's gitdir is the repository the `.git` file names, and git would call it the same thing. That is C2's
  "main is git's own answer" rule from round 1.
- **The file back-pointer (`worktrees/<name>/gitdir` → this `.git`) was not added.** Once (a) and (b) hold, the main
  checkout is proven. The file pointer only adds whether the worktree is still registered at its current path, and a
  worktree moved by hand or copied would fail it. In both cases main's own copy is the trusted one, so refusing them
  would buy no safety.
- **(c) Asking git was rejected.** It costs a git process per hook call: `git rev-parse --git-common-dir` measured
  11.8 ms mean over 50 runs, against 5.7 ms for `bash -c true`. The cost is small. The reason is the launcher's design
  record. PR #409 r2 lost because git is steered by the environment (`GIT_DIR`, `GIT_COMMON_DIR`,
  `GIT_CEILING_DIRECTORIES`), and the W7 cases exist to pin that no environment steers the launcher.

**Bound, stated in the launcher's comment:** a submodule whose NAME is `worktrees/<x>` has a gitdir at a worktree's
path, so it is NOT RUN. It fails closed and does not fall through.

## Dispositions

| Finding | Disposition | Fix and evidence |
|---|---|---|
| **X1** (BLOCKER, fix-induced). A worktree gitdir with no `commondir` and an `objects/` is read as a submodule. | FIXED | A no-`commondir` gitdir is now refused by its path: `elif [ "${gitdir%/*/*}/worktrees" = "${gitdir%/*}" ]` gives NOT RUN, and `objects/` is no longer read on its own. Case *NOCDOBJ*: Codex's input exactly, a real `git worktree add` with `commondir` unlinked and `objects/` made. A precondition row shows that gitdir has HEAD, objects/ and refs/, so only its path can refuse it. NOCD (r1 X1) now asserts the same reason. Case *JUNKGD*: a non-worktree-path gitdir that is not a repository is still NOT RUN. Mutants: **r2a** (the path test → `false`) is killed by NOCDOBJ and NOCD. **c1b** (re-anchored: `is_repo "$gitdir"` → `false`) is killed by JUNKGD. |
| **X2** (BLOCKER). A `commondir` naming an empty `decoy/.git` is accepted as main. | FIXED | The common dir must pass `is_repo` and must contain the gitdir. Case *DECOY*: Codex's input exactly, refused by `is_repo`. Case *OTHER*: the commondir names another REAL repository's `.git`. It passes `is_repo`, so only containment refuses it. Cases *fake-HEAD / fake-objects / fake-refs*: a common dir that does contain the gitdir but lacks one part, so only `is_repo` refuses it. A precondition row checks that each fake lacks exactly its named part. Mutants: **r2c** (`is_repo "$common"` → `false`) is killed by DECOY and the three fakes. **r2d** (containment → `false`) is killed by OTHER. **r2e / r2f / r2g** (drop HEAD, objects/ or refs/ from `is_repo`) are each killed by their own fake. |

**Controls, which behave as before:** U1 (a healthy worktree runs MAIN's copy, from a post-launcher, pre-launcher and
nested worktree), U2 (a relative gitdir), U3 (a real `git submodule add` runs the SUBMODULE's own copy) and C2 (the
symlinked main: the containment test holds, because both paths are resolved with `cd -P`). They are pinned against the
new checks over-refusing:

- **c1c** (`is_repo "$gitdir"` → `:`) is killed by U3.
- **r2b** (the worktree-path test → `:`) is killed by U3.
- U1's three worlds would go red under any check that refused a healthy worktree.

## Manifest

`scripts/mutations/check-run-hook.json` goes from 33 to 39 entries, and the pin in `expected_mutations.py` is 39.
Each new entry removes one piece of an r2 world:

- Codex 1's `commondir` unlink;
- Codex 1's `objects/` (killed by its precondition row);
- the decoy's commondir rewrite;
- the other repository's commondir rewrite;
- the fake common dirs' missing part (all three parts present, so the fake's copy runs);
- the junk gitdir (made a repository, so its own copy runs).

Every anchor in the file occurs exactly once, and no two entries share one. The file is written with `indent=2`,
`ensure_ascii=False` and a trailing newline. The self-test docstring says `# 149 cases`.

## Results on the fold tree

- `python3 scripts/check-run-hook.py --self-test`: `149/149 self-test cases passed`
- `python3 scripts/check-plan-code.py --mutate . --only scripts/check-run-hook.py --allow-long-local`: `OK — delivered scripts mutated: 1 file(s), 39 mutation(s), 39 killed, 39 attributed to the case each names, 0 survivor(s) — measured over ONLY scripts/check-run-hook.py — a DIAGNOSTIC slice, not the gate`
- `python3 scripts/check-fixture-variation.py scripts/check-run-hook.py`: `fixture variation OK — 32 parameter(s) examined across 1 file(s); 105 known-unvaried ratcheted, 71 exempt with a written reason`

**Thrashing watch:** this round carries one fold-caused finding (X1, locate-main). If round 3 (Claude) finds anything
caused by THIS fold in locate-main, the arming condition is met and Phase 6 convenes. The bet is recorded in
`docs/reviews/decision-scheme/decision-log.jsonl`.
