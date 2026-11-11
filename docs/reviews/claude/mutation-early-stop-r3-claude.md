Reviewed head: a2821eb24eb5cc14881a3e124a223944a47cae25

# Round 3 — `mutation-early-stop` (draft PR #476, backlog #405) — Claude half

Subject: `scripts/check-plan-code.py` (`early_path_allowed`, `early_must_run_full`, `early_stop_ci`,
`local_changed`), `scripts/mutations/check-plan-code.json`, the `cancel-in-progress` line in `ci.yml` and
its allowance in `check-merge-ready.py`. Read first: r1 (both halves), r2 Codex and both coordinator records.
Fixed findings (X1, C-H1, C-M1, X2-H1) are not re-reported.

Mandate: refute *"early stop skips only work whose result cannot change; any change outside the allow list, to
the target, to its manifest, or to a `.py` its source names, makes the run FULL"*.

`python3 scripts/check-plan-code.py --self-test`: **348/348 passed**, rc 0, at this head.

```yaml
round: 3
subject: mutation-early-stop
findings:
  - {id: C3-M1, severity: Medium, fix_induced: false, component: stop-rule}
  - {id: C3-L1, severity: Low, fix_induced: true, component: stop-rule}
  - {id: C3-L2, severity: Low, fix_induced: false, component: changed-list}
```

## Findings

### MEDIUM C3-M1: a module that the target reaches only through another module is not seen. Two real suites (19 entries) reach one that way today.

`early_must_run_full` forces FULL for a changed `.py` only when `cp.stem in src`, where `src` is the TARGET's own
source. The docstring states this limit ("a module reached only TRANSITIVELY ... is not seen"). r2 Codex called it
theoretical. It is not theoretical in this repo. `m4_catalog.py:92` does `from m4_base_db import CONTAINER`. Two
manifested suites import `m4_catalog` at module level and never spell `m4_base_db`:

| target | entries | `early_must_run_full(..., ["scripts/m4_base_db.py"])` | `m4_base_db` in `sys.modules` after import |
|---|---|---|---|
| `scripts/check-live-schema.py` | 12 | **False** | True |
| `scripts/check-catalog-coverage.py` | 7 | **False** | True |
| `scripts/check-anon-exposure.py` (control) | 13 | True (it spells `m4_base_db`) | n/a |

`early_stop_ci("pull_request", ["scripts/m4_base_db.py"])` is True: `scripts/m4_base_db.py` is inside the allow
list. So a PR that changes only `m4_base_db.py` early-stops all 19 entries, even though the changed module runs
in-process in both suites. That is exactly the X1 / C-H1 class, a shared module able to change what a printed red
exits with, reached one hop further.

A static walk of the sibling-import graph flags four more targets that reach a module they do not spell:
`begin-plan` and `check-diff-coverage` reach `coverage_verdict`, `regen-pages` reaches
`page_chrome`/`page_markup`, and `check-closing-table` reaches `check-plan-progress`, 167 entries in all. That
walk follows `import` statements and literal `spec_from_file_location` file names. For these four I did NOT
confirm that the module loads in-process: none of them loads at module import, so it may happen inside a case or
in a child process. Treat them as unverified.

**Reproducer (run).** The script is
`/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/f7c144b8-1b6c-4db3-8ef1-932d4e701b12/scratchpad/r3/repro_transitive.py`,
called with the worktree path. It builds `tgt.py`, which imports `mid`, which imports `deep`; `tgt` never spells
`deep`. The PR's change is `deep.py` rebinding `sys.exit` to always exit 0, the same contrived saboteur as r2's
`sitecustomize`. It runs the real `run_mutations` with the mutant `return 1 -> return 2`, which expects
`value is one`:

```
early_path_allowed(scripts/deep.py) = True
early_must_run_full(tgt) = False
early_stop_ci = (True, '... EARLY STOP ...')
FULL : ok=False caught=False survivors=['value is two']
EARLY: ok=True caught=True stop=sigint forced_full=None survivors=[]
```

**Why MEDIUM, not HIGH.** The mechanism is measured and the chain is real. But the change that alters exit
semantics is contrived, and the push-to-master FULL sweep re-asks after merge (`scripts/` is a sweep root). Even
so, the verdict on the PR is wrong.

**Fix (cheap, keeps the text-match philosophy).** Before the per-file loop, close the changed set over the
sibling text relation until nothing new is added. Repeat until stable: any `scripts/**/*.py` whose source names
the stem of a changed `.py` counts as changed too. Then apply the existing `cp.stem in src` test to the closed
set. It stays coarse and needs no call graph. The FAILS-IF case is the reproducer above: a 3-file chain where
the deepest file changed, and early mode must record SURVIVED with `forced_full: "diff"`.

### LOW C3-L1: local `--early-stop` takes `origin/master...HEAD` only, so uncommitted and untracked changes are invisible to it

`local_changed` (r1 fold) runs `git diff --name-only -z origin/master...HEAD`. `mutate_delivered` stages the
WORKING TREE. A developer who edits a trailer, or adds `scripts/startup/sitecustomize.py`, and runs
`--mutate . --early-stop` before committing gets `[]`. `early_must_run_full` then trusts master for a file that
differs on disk. Note that `early_stop_ci` reads `[]` as "lost"; the local path does not.

**Reproducer (run).** In a temp repo with `origin/master` = HEAD, the trailer of `scripts/zero.py` was edited
in the working tree and `scripts/startup/sitecustomize.py` was added untracked:

```
 M scripts/zero.py
?? scripts/startup/
local_changed: []
early_must_run_full(scripts/zero.py): False
```

From there the run is the existing self-test CONTROL ("a trailer exiting 0 in a file the PR left alone IS
stopped"), so the local tally reads KILLED where FULL reads SURVIVED.

**Why LOW.** CI re-decides from the committed diff, which forces this file to FULL. So the false kill is local and
advisory. Still, it is the opposite of what `local_changed`'s docstring promises.

**Fix:** use `git diff --name-only -z origin/master` (no `...HEAD`, so the working tree is included) plus
`git ls-files --others --exclude-standard -z`. Alternatively, return None when `git status --porcelain` is
non-empty.

### LOW C3-L2: rename detection hides the SOURCE path of a rename, so the allow list never sees it (CI and local)

Both `ci.yml` (`git diff --name-only -z "$BASE"...HEAD`) and `local_changed` keep git's default rename detection.
In that mode a rename is listed by its DESTINATION only. The allow list assumes it sees every changed path.

**Reproducer (run).** In a temp repo, `git mv .github/workflows/ci.yml docs/ci.yml`:

```
--- default:        docs/ci.yml
--- --no-renames:   .github/workflows/ci.yml
                    docs/ci.yml
early_stop_ci(["docs/ci.yml"])                            -> True
early_stop_ci([".github/workflows/ci.yml","docs/ci.yml"]) -> False
```

**Impact.** I found no refused file whose REMOVAL turns a printed red into exit 0. A removal mostly produces a
crash or a red control. So this is a hole in the input to the gate, with no demonstrated false kill; hence LOW.
**Adjacent, outside this PR's subject but the same input:** `sweep_needed(["docs/0007.sql"])` is False, while
the `--no-renames` list gives True. A PR that renames a staged file such as
`supabase/migrations/0007_storage_and_rpcs.sql` into `docs/` therefore skips the WHOLE sweep, although
`check-storage-grant-pin` reads that file. That one may deserve its own backlog row.

**Fix:** add `--no-renames` to both diff invocations. One flag; deletions are already listed.

## Checked and clean

- **Path normalisation.** `git diff --name-only -z` never emits `..` or absolute paths. A trailing space is
  stripped only from a name that is not importable. A `docs/x.py` or `docs/x.pth` is refused, because the
  `.pth`/`.py` arms run before the `docs/` arm. `scripts/fixtures/*.json` is refused, since only
  `scripts/mutations/*.json` is allowed.
- **Shadowing.** No `scripts/**/*.py` today has a stdlib stem. No suite imports a third-party top-level module
  (`yaml`, `requests`, ... : 0 hits), so a third-party-named file cannot shadow one. The only extra `sys.path`
  insertions are a script's own directory or a child-process target directory.
- **Manifest retargeting.** `load_manifests` makes the FILENAME the authority, so an entry for B placed in A's
  manifest is refused. The `cp.parent.name == "mutations"` arm cannot be reached through another manifest.
- **Stacked PRs.** `ci.yml` runs `pull_request` only for `branches: [master]`, so a PR based on another branch
  never takes the early path. The "master's full sweep measured it" premise is not violated through a non-master
  base.
- **`cancel-in-progress` / `check-merge-ready` allowance.** It is unchanged since r2 Codex checked it (one exact
  stripped line, count one). Not re-derived.

VERDICT: NOT CONVERGED
