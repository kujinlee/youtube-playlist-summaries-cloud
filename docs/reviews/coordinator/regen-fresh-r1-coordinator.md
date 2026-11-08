# Round 1 — `regen-fresh` (PR #536, backlog #408) — coordinator — both halves NOT CONVERGED; all folded, the reuse design replaced

```yaml
round: 1
fixes_nontrivial: true
subject: regen-fresh
halves:
  claude: ran
  codex: ran
findings:
  - {id: X1, severity: Blocking, aim: deliverable, fix_induced: false, component: regen-runner, disposition: fixed}
  - {id: X2, severity: Blocking, aim: deliverable, fix_induced: false, component: regen-runner, disposition: fixed}
  - {id: X3, severity: High, aim: deliverable, fix_induced: false, component: regen-runner, disposition: fixed}
  - {id: X4, severity: Low, aim: deliverable, fix_induced: false, component: regen-runner, disposition: refuted}
  - {id: C1, severity: High, aim: deliverable, fix_induced: false, component: regen-runner, disposition: fixed}
  - {id: C2, severity: Medium, aim: deliverable, fix_induced: false, component: regen-runner, disposition: fixed}
  - {id: C3, severity: Low, aim: deliverable, fix_induced: false, component: regen-runner, disposition: fixed}
  - {id: C4, severity: Low, aim: deliverable, fix_induced: false, component: regen-runner, disposition: fixed}
  - {id: C5, severity: Low, aim: deliverable, fix_induced: false, component: regen-runner, disposition: fixed}
  - {id: C6, severity: Low, aim: deliverable, fix_induced: false, component: regen-runner, disposition: fixed}
  - {id: C7, severity: Low, aim: deliverable, fix_induced: false, component: regen-runner, disposition: fixed}
```

Codex (`docs/reviews/codex/regen-fresh-r1-codex.md`, its R1-F1..F3 = X1..X3, its closing note = X4) and Claude
(`docs/reviews/claude/regen-fresh-r1-claude.md`, its R1-F1..F7 = C1..C7) each reproduced DATA LOSS in scratch repos.

## The design decision

Patching the ownership proof is the wrong level. The reuse design moved ONE fixed tree, `.claude/regen-tree`, with
`checkout --detach --force` + `clean -fdq`, and both halves showed the proof in front of those commands could be passed
by something that was not the generator's tree. **Destructive reuse is removed entirely.** Each run now:

1. fetches `origin master` in the main checkout (refs and objects only, as before);
2. makes a private directory with `tempfile.mkdtemp` (mode 0700, prefix `regen-pages-`) in the temp root, and runs
   `git worktree add --quiet --detach <private>/tree <sha>` — NO `--force`, so git refuses a path that exists;
3. reads it back: its top level is itself, its `--absolute-git-dir` is an entry under `<common>/worktrees/`, HEAD is the
   sha, the status is clean;
4. runs the generators there, then REMOVES it: the admin entry whose `gitdir` file names this run's literal tree path,
   then the private directory, both with `shutil.rmtree`.

`git worktree add` and not `git archive`: the generators run git in their own root (`gen-backlog-page.py` reads the
backlog's history with `git -C REPO log`, `gen-goals-page.py` and `gen-features-page.py` run `git log` / `rev-parse HEAD`
with `cwd=ROOT`), and `goal-tree.py` finds the main checkout's live ledger and log through `--git-common-dir`.

**No `checkout`, `clean`, `reset`, `worktree prune` or `worktree remove` runs anywhere.** The brief suggested
`git worktree remove --force <path>` for the removal. It is NOT used, for a measured reason: in a scratch repo, with the
tree path swapped for a symlink to another linked worktree, `git worktree remove --force` resolved the link and DELETED
that worktree, its uncommitted edit included (rc 0). `shutil.rmtree` refuses a symlink at the top and follows none inside,
and the admin entry is matched on the literal path string, never through `realpath`, so a swap costs only the link.

A crashed run (SIGKILL) leaves its private directory and its admin entry. They are LEFT, not swept, and the docstring
says so: the entry shows as prunable in `git worktree list`, and nothing here prunes (C4).

MEASURED per-run cost, 2026-11-07, a scratch clone of this repository (4,670 files): fetch + add + read-back 2.27, 2.28,
1.60 s; removal 1.27, 0.81, 0.81 s; total **3.53, 3.09, 2.41 s** (3 runs). The reuse design was 0.65-0.83 s warm and
4.45 s cold. A full five-page run there, with a temp HOME seeded with one tray page, built 4 of 5 pages in 35.7 s, every
one naming the clone's master `8c861e2e`; goal-tree failed on `gh` auth under the temp HOME, as in the build's run.

## Per finding

- **X1 / C1 — a forged or real `.git` at the tree path passes the proof (Blocking / High).** Fixed by the redesign:
  nothing reads, proves or moves the old path. Real-git cases: forged `gitdir:` → the main checkout's git dir; forged →
  another worktree's admin dir; a symlink there to the main checkout; a REAL worktree on a branch there with an
  uncommitted edit and an untracked file. Each run succeeds, and the main checkout's, the other worktree's (and in the
  last, that worktree's) HEAD, index, status, diffs and file bytes are byte-identical before and after.
- **X2 / C3 — the TOCTOU symlink swap (Blocking / Low).** Fixed by the redesign: no destructive verb runs after any
  check. Real-git cases swap THIS run's tree for a symlink to another worktree, and to the main checkout, inside the
  block: both checkouts are untouched, and this run's own entry and directory are still removed.
- **X3 — a Refresh timeout leaves the generator running and the lock released (High).** Fixed in both files.
  `regen-pages.py`: every generator runs with `start_new_session=True`; `launch` waits on the generator (not its pipes'
  EOF) and then `end_group` ends and reaps the whole group (SIGTERM, then SIGKILL after 5 s) before it returns, on a
  timeout and after a normal exit that left a child; a SIGTERM/SIGHUP/SIGINT to the runner kills every live generator
  group first and then unwinds (`_on_signal`); and the lock's descriptor is INHERITED by every generator (`pass_fds`),
  released by closing, never `LOCK_UN`, so a runner SIGKILLed mid-build cannot release the lock under a running
  generator. `explainer-serve.py`: the Refresh press runs the runner through `run_in_group` — its own process group,
  SIGTERM on the timeout, SIGKILL after `REGEN_GRACE` (15 s) — so the 504 can now come up to 15 s after the click's
  bound. Real-process cases: a generator timed out at 0.8 s whose child would write a marker at 1.5 s (marker never
  written); a generator that exits leaving a child (child gone on return); a driver process running `fresh` + `regen`
  sent SIGTERM mid-build (exit 143, generator dead, marker never written, tree removed, lock free); the same driver
  SIGKILLed (generator alive, lock HELD, free once it is killed); a serve "runner" that records SIGTERM.
  ⚠ Bound: a process that leaves its group (`setsid`) is not reached; it is named as having SURVIVED.
- **X4 — `check-page-links.py` calls the generators directly (Low, refuted).** It is a check, not a publisher: it builds
  every page into a temporary directory with `--out` / `--fragment-only` to validate the links of the code under test.
  Building THAT from master would check the wrong subject. It writes nothing that is served, so it is fine as it is.
- **C2 — the edit hooks say "regenerated" for a page that cannot show the edit (Medium).** Kept publishing from master.
  New `--page <key> --after-edit` prints `↻ <key>: pages show origin/master <sha>; this edit appears after it merges`, and
  all four edit hooks print that line instead of "regenerated". The backlog hook keeps its validation: it runs THIS
  checkout's `gen-backlog-page.py --out <private temp dir>` on the edited file (removed straight after; it publishes
  nothing), reports a refusal as "your edit FAILS the backlog generator", and its ⚠-line awk reads that run's output.
- **C4 — `git worktree prune` wipes other worktrees' admin data (Low).** Deleted; nothing prunes.
- **C5 — a killed git's lock file turns every later run CANNOT RUN, path truncated (Low).** `lock_hint` appends the FULL
  lock path and `rm '<path>'` to a fetch or add failure that names one; `_git` sends SIGTERM before SIGKILL on a timeout,
  so git can remove its own locks. The tree's own `index.lock` can no longer persist: every run has a new tree.
- **C6 — the suite's guard keyed on ROOT's path, not the repository (Low).** `_is_this_repository` compares common git
  dirs, so the real main checkout is refused from a linked worktree (a case, in-repository only; NOT RUN elsewhere). The
  refusal cases now hand `fresh` a decoy git that names a scratch repository, so the guard IS mutated and a guardless
  mutant reaches nothing real. The docstring names what protects it.
- **C7 — two stale instructions (Low).** `docs/memory/nothing-needs-you-must-read-the-dashboard.md` and `docs/backlog.md`
  now say `regen-pages.py --page dashboard` / `--page backlog-table`.

Claude's two notes, not findings: the permanent copy at `.claude/regen-tree` swept by `tsc`/`jest` is MOOT (the tree is
in the temp root and lives only for the run); `regenerable()` reading the caller's table stays (a rename fails loudly).

⚠ A `.claude/regen-tree` linked worktree from the reuse design EXISTS in the real main checkout (dated 21:53, before
this fold). The new code never touches that path; it is the owner's to remove (`git worktree remove .claude/regen-tree`
from the main checkout) once this merges.

`fixes_nontrivial: true`: the runner's design changed, so round 2 reviews the new code.
