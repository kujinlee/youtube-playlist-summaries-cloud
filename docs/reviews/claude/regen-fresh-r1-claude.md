Reviewed head: fec9ce91663d8bea6f4898ec251c0df81dd35226

# regen-fresh (PR #536, backlog #408) — round 1, Claude half

Mandate: REFUTE. Priority 1: data loss in the owner's main checkout.

## What was run

- `python3 scripts/regen-pages.py --self-test` → **66/66**. No `.claude/regen-tree` was created in the real
  main checkout, and the `~/explainers/*.html` mtimes were unchanged before and after the run (diffed).
- Attack driver: it imports the branch's `scripts/regen-pages.py` through importlib and calls `fresh(<scratch main>)`
  against throwaway repositories under `$TMPDIR`. Each has a bare origin, and a main clone on branch `feature`
  with an unstaged edit, a staged new file and an untracked file; master then moves on. The driver runs no generator.
  It sets `GIT_CONFIG_GLOBAL=/dev/null` and `GIT_CONFIG_NOSYSTEM=1` and drops every other `GIT_*`. Scripts:
  `/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/f7c144b8-1b6c-4db3-8ef1-932d4e701b12/scratchpad/rv/attack.py`
  and `.../rv/race.py`.

How the main checkout is found: `main_of` takes `rev-parse --path-format=absolute --git-common-dir` and uses its
parent (`regen-pages.py:119`). From a linked worktree this names the main checkout. That is verified, both in the
suite and by hand.

| Attack | Result | Main checkout changed? |
|---|---|---|
| baseline | ok | no |
| tree path is a **symlink to the main checkout** | CANNOT RUN (`is_symlink`) | no |
| `GIT_DIR` + `GIT_WORK_TREE` exported to main | ok (`_env` strips both) | no |
| `GIT_CONFIG_PARAMETERS='core.worktree'='<main>'` | ok (ignored in the linked tree) | no |
| tree `.git` file → **`<main>/.git`** | **ok — proof PASSED** | **YES: HEAD detached off `feature`, index reset (staged file un-staged)** |
| tree `.git` file → **another linked worktree's admin dir** | **ok — proof PASSED** | main no; **the other worktree's branch detached and its index reset** |
| a **real worktree on a branch** at `.claude/regen-tree` with uncommitted work | **ok — proof PASSED** | main no; **that worktree's edits and new file DESTROYED** (checkout --force + clean -fd) |
| **race:** tree swapped for a symlink to main between proof and `checkout` | CANNOT RUN *after the damage* | **YES: unstaged edit reverted, staged + untracked files deleted, HEAD detached** |
| stale `index.lock` in the tree's admin dir | CANNOT RUN, on every later run | no |
| stale `refs/remotes/origin/master.lock` in main | CANNOT RUN (fetch) | no |
| stale `.claude/regen-tree.lock` file | ok (flock, not presence) | no |

Live inputs: `goal-tree.py` reads the log, the agenda, the in-flight ledger and the plans through
`_SS.main_checkout` (`goal-tree.py:954`, `:2202`). The other generators' gitignored inputs are under `~/explainers`
(the questions file). No generator reads a gitignored input relative to its own root. **Confirmed.**

---

### R1-F1 — High — "proven its OWN linked worktree" proves only "SOME worktree of this repo whose top level is that path"

**File:** `scripts/regen-pages.py:130-142` (`_own_worktree`), used before `checkout --detach --force` + `clean -fdq` at `:160`.

**Scenario.** The proof checks three things: there is a `.git` FILE, `--show-toplevel` is the tree, and
`--git-common-dir` is this repo's. Git satisfies all three in three states that are not the generator's tree:
1. `.git` contains `gitdir: <main>/.git`. Git takes the containing directory as the work tree and main's admin dir
   as the git dir. The proof passes, and `checkout --force <sha>` then **rewrites MAIN's HEAD and index**:
   measured, main went from `refs/heads/feature` to a detached `origin/master`, and the staged `staged.txt` became
   untracked. The working files survived only because the work tree is the tree.
2. `.git` contains `gitdir: <main>/.git/worktrees/<other>`. Measured: the other worktree's branch `wip` was detached
   and its staged change dropped from the index.
3. A genuine linked worktree on a branch sits at `.claude/regen-tree`, for example from a `git worktree add`, or an
   agent that picked that path. Measured: its uncommitted `page.txt` edit was reverted and its untracked `new.txt`
   was deleted. **This loss cannot be recovered.**

None of these arise on their own from this code's normal path. But the docstring at `:47` names the guard *"proven
to be its OWN linked worktree"*, and the brief asks for exactly that proof. The guard is the only thing standing
between `--force` / `clean` and someone's work.

**Repro:** run `python3 -I attack.py gitfile_main gitfile_other_wt real_wt_at_path` in the scratch dir above.

**Fix.** Make "own" mean owned:
- (a) `rev-parse --path-format=absolute --git-dir` in the tree must be `realpath(<common>/worktrees/<name>)`, and
  must never be `common` itself;
- (b) that admin dir's `gitdir` file must resolve to `<tree>/.git`;
- (c) HEAD must be detached (`symbolic-ref -q HEAD` fails);
- (d) a marker the runner writes into the admin dir right after `worktree add` must be present. Put it in the admin
  dir, not the work tree, so `clean` cannot remove it.

Refuse with CANNOT RUN otherwise. Pass `--git-dir=<admin dir>` and `--work-tree=<tree>` explicitly to the two
mutating calls, so they cannot act on a git dir other than the one proven. Add a real-git case for each of the three
states, each asserting that nothing outside the tree changed.

### R1-F2 — Medium — the edit hooks now rebuild from master, so the edit they fire on never reaches the page, and they still say "regenerated"

**Files:** `.claude/hooks/regen-backlog-page.sh:93-104`, `.claude/hooks/regen-dashboard.sh:41-53`, and the features
and goals hooks, which have the same shape.

**Scenario.** An agent edits `docs/backlog.md` or `docs/dashboard-entries.md` in its worktree, or the owner does in
the main checkout. The hook runs `regen-pages.py --page …`, which builds from `origin/master` and cannot contain
the edit. The hook then prints `↻ backlog view regenerated` or `↻ dashboard regenerated`. It filters `$OUT` to `⚠`
lines, so the runner's `built from origin/master <sha>` line never reaches the reader.

The backlog hook's own header (`:18-22`) and its #110 M-1 note (`:105-110`) say this hook exists to surface the
generator's warnings *about the row just typed*, "the most timely channel the warning has". After this change those
warnings describe master's rows, not the edit. A new dashboard ask written on a branch is likewise invisible on
`/dashboard` until it merges. The skill text now says so, but the hook's success line does not. Each edit also now
costs a network fetch and possibly a full checkout.

**Repro:** read the two hooks. `--page` output → `awk '/^⚠/…'` (backlog) or `grep '⚠'` (dashboard). The provenance
line is dropped and the success echo is unconditional.

**Fix.** Choose one:
- Keep the edit hooks on the fresh tree, but print the runner's `built from origin/master <sha>` line together with
  "your edit appears after merge". Also run a write-nothing validation of the EDITED file (for example the
  generator's `--fragment-only --out <tmp>` against the working tree), so the at-edit warnings survive.
- Retire the edit hooks for the fresh-tree pages and rely on the merge hook.

Either way, the success line must not claim the edit was rendered.

### R1-F3 — Low — a race between the proof and `checkout --force` lands on the main checkout (measured)

**File:** `scripts/regen-pages.py:156-166`. The proof and the mutating calls are separate subprocesses with
`cwd=tree` given as a PATH.

**Scenario.** If the tree path is replaced by a symlink to the main checkout after `_own_worktree` returns, the
mutating calls follow it. `tree_lock` excludes only other runs of this runner, so any other actor can do this.
Measured with a git wrapper that swaps the directory just before `checkout`: main's unstaged edit was reverted, its
staged and untracked files were deleted by `clean -fd`, and HEAD was detached. The post-check then said CANNOT RUN,
after the damage was done.

Nothing in the repository does such a swap today, so the likelihood is low. The consequence is the worst outcome
this PR guards against.

**Repro:** `python3 -I race.py`.

**Fix.** Pin the identity for the mutating calls. Use `--git-dir=<proven admin dir> --work-tree=<realpath(tree)
taken at proof time>`. Run them with `cwd` set to a directory fd opened `O_NOFOLLOW` at proof time
(`preexec_fn=lambda: os.fchdir(fd)`), and re-check `os.lstat(tree)` against that fd's `st_ino`/`st_dev`
immediately before each call.

### R1-F4 — Low — `git worktree prune` in the main checkout is redundant, and it deletes the admin data of ANY worktree that is temporarily missing

**File:** `scripts/regen-pages.py:162`.

**Scenario.** `prune` is repository-wide. Any linked worktree whose directory is absent at that moment loses
`.git/worktrees/<name>`: its index, which holds staged work, and its HEAD/branch link. Such a directory can be
mid-`mv`, on an unmounted volume, or renamed by a test. Measured in a scratch repo: after
`mv ../t2 ../t2-aside; git worktree prune; mv back`, `git -C ../t2 status` gave `fatal: not a git repository`.

The prune is also unnecessary. `worktree add --force`, which the code already passes, accepts a path that is
registered but missing. Measured: `rm -rf ../t1; git worktree add --detach --force ../t1 HEAD` succeeds with no
prune.

**Fix.** Delete the `prune` call. If a registered-but-missing tree must be cleared, use
`git worktree remove --force <tree>` for THAT path only.

### R1-F5 — Low — a timeout-killed git call leaves a lock that turns every later rebuild into CANNOT RUN, and the remedy is truncated out of the message

**File:** `scripts/regen-pages.py:101-110` (`_git` uses `subprocess.run(timeout=)`, which sends SIGKILL); `_brief`
at `:113` truncates to 160 characters.

**Scenario.** A `checkout` or `worktree add` that is SIGKILLed cannot remove `.git/worktrees/regen-tree/index.lock`.
That happens at `GIT_TIMEOUT`, or when Claude Code kills a hook's process tree, and the edit hooks carry no
`timeout` in `settings.json`. Measured: with a planted `index.lock`, every later run says
`CANNOT RUN … fatal: Unable to create '/private/var/…` and the path is cut off. The "remove it by hand" hint exists
only in the not-own branch. The failure is loud, so this is not data loss, but every page stays frozen until a human
reads the full path. The same applies, more narrowly, to ref locks in the MAIN checkout's `.git` from a killed fetch.

**Fix.** When the failure text matches `index.lock': File exists`, print the full lock path and the exact `rm`
command. Optionally, auto-remove an `index.lock` in the generator-owned admin dir, never in main's, that is older
than `GIT_TIMEOUT` while this runner holds `tree_lock`. Send SIGTERM before SIGKILL on timeout.

### R1-F6 — Low — the self-test guard refuses ROOT, not THIS REPOSITORY; its mutation exclusion is sound but the stated reason is not what protects it

**File:** `scripts/regen-pages.py:203-210`.

**Scenario.** The guard compares `realpath(repo)` with `realpath(ROOT)`. Run from a linked worktree (this branch's
`rgf`), ROOT is that worktree. A case calling `fresh(<the real main checkout>)`, or `fresh(<any other worktree of
this repo>)`, would not be refused, and `main_of` would then materialise in the REAL main checkout. No current case
does this: every real-git case uses `tmp`. But the case named *"…whatever a case passes for tree_for"* (`:688`)
asserts more than the guard enforces.

On the exclusion from mutation: `check-plan-code.py:stage_tree` copies into a non-repository temp dir (verified:
`$TMPDIR` is in no repo). There, a guard-removal mutant would hit `main_of`, which says not-a-repo, so CANNOT RUN,
and the case would stay green. In the harness the mutant is therefore both harmless and invisible. The protection
that actually exists is the in-repo run (CI / local `--self-test`): there, removal goes `ok` and the case turns red.
So the exclusion is sound. The docstring's reason ("a mutant … would do exactly that to the real checkout") is true
only of an in-place run.

**Fix.** Key the guard on the repository's common dir (`main_of(repo)[1] == main_of(ROOT)[1]`, computed with
`_git`), not on ROOT's path. Reword the exclusion note to name what protects the guard: the in-repo self-test run.

### R1-F7 — Low — two callers still regenerate from the caller's checkout

**Files:**
- `docs/memory/nothing-needs-you-must-read-the-dashboard.md:15` ("regenerate `/dashboard` (`python3
  scripts/gen-dashboard.py`)"). This is a standing instruction that is executed every time "nothing needs you" is
  written.
- `docs/backlog.md:6` (`python3 scripts/gen-backlog-page.py` renders…).

Both write the served `~/explainers` page from whatever tree the session is in, which is exactly the #408 defect.
The hooks, the Refresh route, `regen-pages.sh`, `/goal-tree` and the dashboard skill are routed correctly. A grep of
`scripts/`, `.claude/` and `.agents/` found no other live caller. `check-anchors.py` and `check-group-claims.py` only
read or import `gen-backlog-page.py`; `brief-compose.py` and `compaction-state.py` import `gen-dashboard.py` and
write no page.

**Fix.** Point both at `python3 scripts/regen-pages.py --page dashboard` and `--page backlog-table`.

### Noted, not filed as findings

- A permanent full copy of the repo now lives at `<main>/.claude/regen-tree`. `tsconfig.json` includes `**/*.ts`
  excluding only `node_modules`, and `jest.config.ts` has no `testPathIgnorePatterns`, so `tsc` and `jest` run in
  the MAIN checkout would sweep it. `.claude/worktrees/*` already has the same exposure, so this class predates the
  PR. The PR makes it permanent rather than transient.
- `regenerable()` reads the page table from the CALLER's `explainer-serve.py`, not master's. A generator renamed on
  master fails loudly by name, so no fix is needed.

VERDICT: NOT CONVERGED
