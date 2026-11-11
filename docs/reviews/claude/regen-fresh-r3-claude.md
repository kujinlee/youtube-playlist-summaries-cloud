Reviewed head: 10072913c70ed96f3d453bf2cd28fceb38506611

# regen-fresh (PR #536, backlog #408) — round 3, Claude half

Mandate: REFUTE. Priority 1: data loss, or a write into the main repository. Scope: the round-2 fold `6acb6912`
(the private shared clone, `discard`, `REGEN_MAIN_CHECKOUT`, `_reap_killed`), read against
`git diff origin/master...HEAD`. Every probe ran in scratch repositories under the session scratchpad. The real
regeneration was not run. The local mutation sweep was not run.

## What was run

| Check | Result |
|---|---|
| `python3 scripts/regen-pages.py --self-test` | **101/101**, rc 0 |
| `python3 scripts/session-state.py --self-test` | **131/131**, rc 0 |
| `python3 scripts/explainer-serve.py --self-test` | **239/239**, rc 0 |
| `--shared` write-back: a scratch main (3 commits plus a dangling loose blob). Then `clone --shared --no-checkout`, a commit in the clone, `gc --aggressive --prune=now`, `repack -a -d`, `prune`, and `maintenance run --task=gc --task=loose-objects --task=incremental-repack` in the clone | SHA of every file under main's `.git`, taken before the clone and after all of that: **identical**. The main repository's dangling blob survived the clone's `prune`, and the clone's `fsck` reports it as dangling through the alternate. **Nothing in the clone writes back.** |
| Post-clone swap of `<private>/tree` for a symlink to the main checkout (R3-F1) | **reproduced**: `clone_tree` accepted it, and the main checkout's HEAD went from `refs/heads/master` to DETACHED at the sha |
| `REGEN_MAIN_CHECKOUT` set to an unrelated repository's main checkout, `main_checkout()` called from this worktree (R3-F2) | **reproduced**: returned `(<other repo>, None)` |
| Seven new mutations, each applied by hand in a scratch copy of the worktree with the suite run there | **7 of 7 go red on their named case** (table below) |

Hand-checked mutations. The scratch copy is in no repository, so the suite there reports 100 cases rather than 101,
because the real-repository refusal case is NOT RUN. Each row is one mutation applied alone. Script:
`/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/f7c144b8-1b6c-4db3-8ef1-932d4e701b12/scratchpad/mut.py`.

| Manifest index | Mutation | Suite | Named case |
|---|---|---|---|
| regen-pages 34 | identity not checked before `rmdir` | 97/100 | [FAIL] |
| regen-pages 35 | contents deleted by path, not through the fd | 97/100 | [FAIL] |
| regen-pages 45 | escalation `(SIGTERM, SIGKILL)` → `(SIGTERM, SIGTERM)` (R2-F6) | 99/100 | [FAIL] |
| regen-pages 46 | `lstat` → `stat` in discard | 93/100 | both [FAIL] |
| regen-pages 49 | a removed clone stays mapped | 99/100 | [FAIL] |
| session-state 109 | `REGEN_MAIN_CHECKOUT` ignored | red | [FAIL] |
| session-state 110 | the name trusted as text | red | [FAIL] |

## Refuted (tried, did not break)

- **Alternates writing back.** Measured above: `gc`, `repack -a -d`, `prune` and `maintenance` in the clone leave every
  byte of main's `.git` unchanged. `repack -a` copies the alternate's objects into the clone and never deletes them from
  the source. A generator's `git gc --auto` is a subset of this.
- **`discard` steered by a swap.** `shutil.rmtree.avoids_symlink_attacks` and `shutil._use_fd_functions` are both True on
  the interpreter used here (3.14.4, macOS). A symlink found inside the private dir is unlinked. A same-inode ancestor
  re-link still names the real directory, so the `rmdir` hits the right target. Hand-mutations 34, 35 and 46 show the
  cases bind.
- **Bounded drain.** `launch` joins its readers for at most `GROUP_GRACE` each, after an `end_group` bounded at
  2 × `GROUP_GRACE`. `_reap_killed` is bounded at 2 × `REGEN_DRAIN`. In `run_in_group`, a descendant that has escaped
  can still hold the pipes after a runner that SUCCEEDED, which makes the success come back as a 504 at the timeout. That
  falls inside the stated `setsid` bound, so it is not filed.

## Findings

### R3-F1 — Medium — fix_induced: yes — a swap of `<private>/tree` after the clone sends the in-clone verbs into another checkout, and the read-back accepts it

The round-2 fold introduced three path-based git verbs that run in the tree AFTER `git clone` returns:
`checkout --detach <sha>`, `update-ref refs/remotes/origin/master` and `remote set-url origin`
(`clone_tree`, `scripts/regen-pages.py`). Round 1's `git worktree add` created and checked out in one command, so the
window is new.

Reproduction (the scratchpad `sw/` dir). The scratch main is on `master` at commit 1, and `origin/master` is at
commit 2. A `git` wrapper passed to `clone_tree` runs the real clone, then renames `<private>/tree` aside and puts a
symlink to the main checkout at `<private>/tree`, which is a same-user swap. Result:

```
clone_tree ACCEPTED the swapped tree
discard notes: []
main HEAD now: 6ed39fb symbolic: DETACHED
```

- `checkout --detach` ran IN THE MAIN CHECKOUT, detaching its HEAD from `master` and moving its working tree. The other
  two verbs also ran there; they rewrote the same values in this scratch setup.
- `read_back` did not catch it. It compares `os.path.realpath(top)` with `os.path.realpath(tree)`, and the same for the
  git dir. `realpath` FOLLOWS the swapped symlink, so the main checkout's top level and `.git` match their own realpaths.
  With a clean main, HEAD equals the sha and the status is clean, so every check passes, and the generators would then
  run in the main checkout.
- With uncommitted edits in main, a non-forced `checkout` either carries them or refuses, and the status check then
  refuses the tree. So there is no data loss, but HEAD has still been moved.
- This falsifies the docstring's claim "NOTHING RUNS IN THE MAIN REPOSITORY BUT `fetch`, `rev-parse` and `config --get`".
  It also falsifies `read_back`'s "never a checkout git reached by walking up".
- Severity is Medium, not Blocking. The private path is random and 0700, so only a same-user process that is watching
  the temp root can make the swap, and no file content is lost. It is the same threat class as R2-F1, which this branch
  chose to defend.

Fix direction:
- Compare without `realpath`: `priv.path` is already resolved, so `top` and `gd` must equal `str(tree)` and
  `str(tree / ".git")` exactly.
- Before each in-clone step, require that `os.lstat(tree)` is a real directory.
- Better still, run the in-clone steps with their cwd anchored to a descriptor opened `O_NOFOLLOW` on the tree right
  after the clone (`preexec_fn=lambda: os.fchdir(fd)`), so no path lookup can be redirected.

A case should do exactly the reproduction above and assert that main's HEAD is still symbolic. It should be backed by a
mutation that restores `realpath`.

### R3-F2 — Low — fix_induced: yes — `REGEN_MAIN_CHECKOUT` honours ANY repository's main checkout, and overrides even a real checkout

`session-state.main_checkout` (new in `6acb6912`) validates the env name only as "git, asked from it, names it as its
own main checkout". It never checks that the name is the main checkout of the repository `root` belongs to.

Reproduced. With `REGEN_MAIN_CHECKOUT=<scratch>/other`, which is an unrelated `git init`, `main_checkout(<this worktree>)`
returned `(<scratch>/other, None)`. It is honoured even when `root` is a genuine checkout of this repository whose own
common dir gives the right answer.

Everything that writes through `main_checkout` would then write into the other repository:
- the ledger writes in `session-state --add/--done`;
- `goal-tree.py`'s `.claude/goal-tree-log.jsonl` and agenda log appends;
- `compaction-state.py`.

`regen-pages._env()` strips only `REPO_VARS`, so an inherited value also passes through `launch` whenever the tree is
not in `_TREE_MAIN`.

Low, because the runner is today the only setter and it sets the right path. But the review asked exactly this question
("can it be pointed at a wrong path that a generator then writes to"), and the answer is yes, with no case asserting
otherwise.

Fix direction:
- Honour the name only when `root` is NOT itself a checkout with a usable common dir, which is the clone case.
- Also require that the clone's `.git/objects/info/alternates` names `<named>/.git/objects` (or an equivalent
  same-repository proof).
- Add `MAIN_CHECKOUT_ENV` to what `_env()` drops before `launch` sets it.

### R3-F3 — Low — fix_induced: no — `_git`'s stop-signal path SIGKILLs git without the lock-cleanup grace, and its drain is unbounded (R2-F4's class, unfixed sibling)

`_git`'s `except BaseException:` arm runs `p.kill(); p.communicate()`. This arm predates round 2: it is present at
`1a7206cf`, line 150. A stop signal during the main checkout's `git fetch` raises `SystemExit` there through `_on_signal`.
Two consequences:

1. The fetch is SIGKILLed with no grace, the shape review r1 C5 fixed on the timeout path, so `*.lock` files can be left
   in the MAIN repository's `.git`. That blocks the owner's own `git fetch`/`pull` until they are removed. Under
   `run_in_group` the group's SIGTERM usually reaches git first, but the handler's SIGKILL races git's own cleanup.
2. The `communicate()` after the kill is unbounded, which is the R2-F4 shape that was fixed only in `explainer-serve.py`.
   The timeout arm has the same unbounded `p.communicate()` after `p.kill()`.

Not reproduced; this is from reading the code. Low.

Fix direction: give the BaseException arm the timeout arm's terminate → `GIT_GRACE` → kill sequence, and bound both
post-kill drains as `_reap_killed` does.

## Thrashing check (Phase 6 arming)

Round 2's findings in component `regen-runner` were fix-induced by round 1's fold: R2-F1, F2, F3, F4 and F6, per the r2
coordinator doc. This round's R3-F1 and R3-F2 are fix-induced by round 2's fold, in the same component. **That is two
consecutive rounds whose findings came from the previous round's own fix, in one component, so the architecture-review
arming condition in `docs/dev-process.md` is MET.**

The pattern is that each redesign of the tree's lifecycle (reuse → linked worktree → shared clone) moves the trust
boundary to a new path, and a new path-based check lands on it. R3-F1 is the same "a path that names something else
after a check" defect that R1 X2 and R2-F1 were, now on the creation side.

## Verdict

R3-F1 (Medium, fix-induced) is a reproduced write into the main checkout, against the branch's own stated invariant.
Round 3 is the last round in which findings are fixed.

VERDICT: NOT CONVERGED
