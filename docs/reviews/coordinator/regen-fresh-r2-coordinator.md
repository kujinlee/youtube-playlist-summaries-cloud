# Round 2 — `regen-fresh` (PR #536, backlog #408) — coordinator — Codex NOT CONVERGED; all folded, the worktree design replaced

```yaml
round: 2
fixes_nontrivial: true
subject: regen-fresh
halves:
  claude: gap
  codex: ran
findings:
  - {id: R2-F1, severity: Blocking, aim: deliverable, fix_induced: true, component: regen-runner, disposition: fixed}
  - {id: R2-F2, severity: High, aim: deliverable, fix_induced: true, component: regen-runner, disposition: fixed}
  - {id: R2-F3, severity: High, aim: deliverable, fix_induced: true, component: regen-runner, disposition: bounded}
  - {id: R2-F4, severity: High, aim: deliverable, fix_induced: true, component: regen-runner, disposition: fixed}
  - {id: R2-F5, severity: Medium, aim: deliverable, fix_induced: false, component: regen-runner, disposition: fixed}
  - {id: R2-F6, severity: Medium, aim: deliverable, fix_induced: true, component: regen-runner, disposition: fixed}
```

REVIEW GAP: claude — alternation

Codex (`docs/reviews/codex/regen-fresh-r2-codex.md`) reproduced R2-F1..F6 in scratch clones. `fix_induced`: F1 and F2 come
from round 1's cleanup design (admin entries made and deleted inside the main repository); F3, F4 and F6 from round 1's
process-group code (`launch`/`end_group`, `run_in_group`). F5 is the edit hook's ordering, older than round 1's change to it.

## The design decision

R2-F1 and R2-F2 exist only because the run CREATED AND DELETED admin entries inside the main repository
(`<common>/worktrees/<name>`). Patching the ownership match is the wrong level, the same reason as round 1. **The run now
registers nothing in the repository:**

1. `git fetch origin master` in the main checkout (refs and objects only, unchanged), and `config --get remote.origin.url`;
2. `Private`: `tempfile.mkdtemp` (0700, `regen-pages-*`), opened at once (`O_DIRECTORY | O_NOFOLLOW`), its
   (st_dev, st_ino) recorded;
3. `git clone --shared --no-checkout --quiet <main checkout> <private>/tree`. The objects are read through alternates. Then,
   INSIDE the clone and only there: `checkout --detach <sha>`, `update-ref refs/remotes/origin/master <sha>` (a clone copies
   the main checkout's LOCAL branches, which can be far behind), and `remote set-url origin <main's URL>` (so a generator's
   `git fetch origin master` and `gh` reach GitHub, never the main checkout's local `master`);
4. read back: the top level is the clone, `--absolute-git-dir` is `<tree>/.git` (its own repository, no linked worktree),
   HEAD is the sha, the status is clean;
5. each generator gets `REGEN_MAIN_CHECKOUT=<main checkout>`;
6. `discard`: the contents go through the held descriptor (`shutil.rmtree(name, dir_fd=)`, symlinks unlinked), then the
   directory is `rmdir`ed only while `os.lstat` of its path still gives the recorded identity. A swap is REFUSED and named.

In the main repository only `fetch`, `rev-parse` and `config --get` run. Nothing under its `.git` is created, edited or
deleted apart from what the fetch writes.

**VERIFIED before choosing: what each generator reads through git**, by grep of the five generators and by running their
calls in a real clone of this repository (2026-11-07):

| Generator | Reads | In the clone |
|---|---|---|
| `gen-dashboard.py` | `git log HEAD --first-parent`, `gh` (cwd=ROOT) | works; `gh repo view` resolved `kujinlee/youtube-playlist-summaries-cloud` once `origin` was the GitHub URL |
| `gen-backlog-page.py` | `git -C REPO log -- docs/backlog.md`, `git show <sha>:docs/backlog.md`, `rev-parse --short HEAD` | works (history through alternates) |
| `gen-goals-page.py` | `git log --follow`, `git show`, `rev-parse HEAD` | works |
| `gen-features-page.py` | `git log --format=%s -n` | works |
| `goal-tree.py` | `git fetch origin master` + `git log origin/master` in its root; `gh pr list`, `gh repo view`; `session-state.main_checkout` for the ledger and its log | fetch 0.46 s from GitHub into the clone; `gh pr list` returned PR #537 and PR #536. ⛔ `--git-common-dir` names the CLONE, so `main_checkout` would have read the clone's empty `.claude/` |

That last row is why `session-state.main_checkout` changed. It now honours `REGEN_MAIN_CHECKOUT`, but never as text: git
is asked from that path and must name it as its own main checkout. A linked worktree or a relative path is refused. This
is two cases and two mutations in `session-state.py`, plus a composition case in `regen-pages.py` that runs the REAL
`main_checkout` in a REAL clone with what `launch` hands a generator.

MEASURED per-run cost, 2026-11-07, a scratch clone of this repository (4,417 tracked files), the same five git steps the
runner makes (fetch, clone, checkout, update-ref, set-url, read-back, removal), 3 runs: **4.02, 4.14, 3.71 s** (fetch
0.40-0.51 s, clone + checkout + read-back 2.45-2.75 s, removal 0.75-1.03 s). Round 1's worktree design was 2.41-3.53 s.
About 0.6-1.1 s more per run buys a cleanup that cannot reach the repository.

**R2-F1's residual is BOUNDED.** The private directory's own ancestors are the temp root, which is no repository. The
identity check bounds a swap there to "deletes only a directory with the identity this run created". Between the last
`lstat` and the `rmdir` a swap can still remove an EMPTY directory, because `rmdir` refuses one with contents. This is
stated in the module docstring.

## Per finding

- **R2-F1 — a swapped `<common>/worktrees` symlink sends `rmtree` elsewhere (Blocking).** Fixed by the redesign: nothing
  under `<common>` is read or deleted. Cases (real git, as reproduced): `<common>/worktrees` renamed aside and replaced
  MID-RUN by a symlink to unrelated data holding a same-named `tree/UNCOMMITTED` survives byte for byte, and this run's
  directory is still removed. A run with master unchanged leaves EVERY file in the main repository's git dir
  byte-identical (FETCH_HEAD aside). The residual is covered by identity cases: an EMPTY directory swapped in at the
  private path survives (refused); the private dir's ANCESTOR swapped for a symlink to a same-named tree elsewhere
  survives, file included, while the run's own tree is still deleted through its descriptor; a symlink swapped in at the
  private path is refused and its target survives.
- **R2-F2 — editable `gitdir` text deletes another worktree's admin entry (High).** Fixed by the redesign: ownership is
  never inferred, because there is no entry to own. Case (real git, as reproduced): a LIVE worktree's admin `gitdir`
  rewritten mid-run to name this run's tree keeps its admin entry, and `git status` there still works.
- **R2-F3 — a descendant that `setsid`s and closes the lock fd outlives cleanup (High). BOUNDED, not fixed.** Portable
  containment (descendant tracking across sessions) is not available on macOS: no cgroups, no subreaper. The generators
  are this repository's own scripts, none leaves its group, and the repository states the same bound for its hooks
  (CLAUDE.md: "a process that leaves its group (`setsid` or `setpgid`) is not killed"). The bound is now written in the
  module docstring (`⚠ BOUND, stated (review r2 F3) — THIS IS NOT CONTAINMENT`), in `end_group`, at `_HELD_FDS`, in
  `run_in_group` and in backlog row 408. The overclaim is removed: `end_group`'s docstring no longer says an escaped
  process "is named in the result's text as having SURVIVED". It is not detected, as Codex measured. The warning text now
  says "a process still in its group SURVIVED SIGKILL", which is the only thing `gone` measures.
- **R2-F4 — the post-SIGKILL `communicate()` is unbounded (High).** Fixed in `explainer-serve.py`: `_reap_killed` drains
  for at most `REGEN_DRAIN` (2 s), then CLOSES both pipes and reaps the direct child with a bounded wait. It is used on
  the timeout path and the `BaseException` path. Case: a real runner whose descendant `setsid`s and holds the pipes,
  sleeping 20 s; the timeout (0.8 s, grace and drain 0.3 s) still raises in under 5 s. Mutation: the drain made unbounded
  again.
- **R2-F5 — a publishing failure suppresses the edited file's validation warnings (Medium).** Fixed in
  `.claude/hooks/regen-backlog-page.sh`: the validation verdict and its ⚠ lines (the awk relay that gen-backlog-page's
  suite reads and runs) are printed straight after validation, BEFORE publishing. MEASURED in a scratch copy, as reproduced
  (a validator printing `⚠ … UNREAD` and exiting 0, a publisher exiting 2 `CANNOT RUN offline`): the new hook prints the
  ⚠ line and its detail, then the publishing failure; HEAD's hook printed only the failure. No sibling hook has the shape:
  `regen-dashboard.sh`, `regen-features-page.sh` and `regen-goals-page.sh` run no separate validation, so they have no
  `$VAL` to lose.
- **R2-F6 — the SIGKILL escalation has a surviving mutation (Medium).** Fixed: a REAL generator that ignores SIGTERM,
  timed out at 1 s with `GROUP_GRACE` 0.5 s, is gone before `launch` returns and is reported as a timeout. The mutation
  `(SIGTERM, SIGKILL)` → `(SIGTERM, SIGTERM)` is registered against that case.

## Cases and mutations

`regen-pages.py`: 85 → **101** cases. Round 1's worktree cases are retargeted onto the clone: the add-args case becomes
the clone-args case plus the in-clone steps; the admin-entry match cases are removed with `own_entries`; the
read-back's git-dir cases now require `<tree>/.git`. New: no origin URL, a failed clone, a failed in-clone step, the
clone → main-checkout map and its hand-off, origin/master and origin's URL in a real clone, the real `main_checkout`
composition, the git dir byte-identical, R2-F1 (as reproduced plus three identity swaps), R2-F2, R2-F6, and `discard`
over directories, files and symlinks, and over an empty private dir. Every real-git data-loss case is kept (main and the other worktree byte-unchanged).

Mutations 45 → **53**. The nine entries whose anchors were in removed code are retargeted one for one (no origin URL,
`--shared`, origin/master in the clone, the git-dir read-back, the descriptor deletion, the private dir's `rmdir`, its
identity, deletion by path, the discard call). Eight are new: the SIGKILL escalation (F6), `lstat` not `stat`, the
clone → main-checkout map, its hand-off to `launch`, its removal, a failed in-clone step, a failed clone, and origin's
URL. `explainer-serve.py` 238 → 239 cases, 72 → 73 mutations (F4). `session-state.py` 129 → 131 cases, 109 → 111
mutations (`REGEN_MAIN_CHECKOUT` ignored; trusted as text).

`fixes_nontrivial: true`: the runner's design changed again, so round 3 reviews the new code.
