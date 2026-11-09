> **Source:** the backlog #560 / backlog #586 measurement spike's REPORT.md, run 2026-11-09 against `origin/master` d206e066 (scripts and data kept in the session scratchpad, not copied); copied unchanged below.

# Spike for backlog #560 / #586: what each mutation target's suite actually reads

Tree measured: `origin/master` at d206e066, in a detached worktree. Every suite ran unmutated, ONE at a time, in a staged
copy of `HARNESS_TREE` (the same roots `stage_tree` copies, `__pycache__` excluded; `node_modules/typescript` taken from the
main checkout), with `cwd` set to the staged tree and the env set by `cpc.mutation_env(d)` (the harness's own function: HOME is
`<d>/.home`, `PYTHONDONTWRITEBYTECODE=1`, the mutation-run marker). Each ran as `<target> --self-test` under a
`sys.addaudithook` wrapper (`runpy.run_path`, run_name `__main__`), capped at 200 s.
Scripts: `audit_wrap.py`, `driver.py`, `analyze.py`, `pick_sel.py` (selector), `compare.py`. Data: `observed.json`, `selection.json`, `compare.json`, `results/`.

## Headline (all MEASURED unless marked)

| | PR #545 (docs-only: backlog.md + dashboard-entries.md) | PR #543 (17 files: 14 docs + 3 scripts) |
|---|---|---|
| manifest targets | 90 | 90 |
| **selector-picked** (`select_manifests`, run on the master tree) | **64** | **68** |
| picked AND the hook OBSERVED reading a changed path | **6** (3 of them traceable) | **20** (+1 via a directory listing of an ADDED file; 6 traceable) |
| picked AND untraceable (it spawns child processes) | 33 | 35 |
| picked, traceable, and observed reading NO changed path (selected by NAME only) | **28** | **27** |
| NOT picked but observed reading a changed path | 1 (`check-plan-code.py`; it is in the harness set, so it is excluded from selection by design) | 1 (the same) |

⚠ There is no truly scripts-only PR: none of the last 60 merged PRs changes only `scripts/` or `.claude/hooks/` (MEASURED,
`gh pr list --state merged --limit 60`), because every PR records a dashboard entry in `docs/dashboard-entries.md`.
#543 is a mixed PR. Its scripts-only slice (3 files) was also scored: 16 observed readers over all 90 targets, 4 of them traceable.

## Cache-hit estimate for #560

Rule: a target's mutants are REUSED when the target is traceable (it spawns nothing), its suite was measured green, and no
path it was observed to open (or no directory it listed, for an added/deleted path) changed between the PR's base and head.
Anything else RE-RUNS (fail-closed).

| Scope | PR #545 rerun / reuse | PR #543 rerun / reuse |
|---|---|---|
| all 90 targets, strict (any spawn means rerun) | 50 / **40** | 53 / **37** |
| the selector's picks only, strict | 36 / **28** of 64 | 41 / **27** of 68 |
| INFERRED sensitivity: the 13 targets that spawn ONLY `git` counted as traceable | 37 / 53 (all), 25 / 39 (picked) | 44 / 46 (all), 33 / 35 (picked) |

The reuse is limited by spawning, not by reads. Only 43 of 90 targets are traceable (MEASURED), so with the strict rule 47 targets
(46 that spawn + 1 failed) always re-run, whatever the diff. For #545 only 3 traceable targets actually read a changed file
(`check-canonical-source`, `check-dashboard-entry`, `check-features`).

## Who reads `docs/backlog.md` / `docs/dashboard-entries.md` (MEASURED)

| target | backlog.md | dashboard-entries.md | traceable? | picked for #545? |
|---|---|---|---|---|
| check-canonical-source | yes | yes | yes (it opens 3,190 repo files, so it reads nearly the whole tree) | yes |
| check-dashboard-entry | – | yes | yes | yes |
| check-features | yes | – | yes | yes |
| gen-backlog-page | yes | – | NO (it spawns) | yes |
| gen-dashboard | yes | yes | NO | yes |
| gen-features-page | yes | – | NO | yes |
| check-plan-code | yes | yes | NO | no (it is the harness) |

So for #586, 7 targets observably read the two files a docs-only PR touches. The selector picks 64.

## The spawners: 46 targets, not the 10 the brief expected (MEASURED)

Popen counts, by kind of argv. The `cwd` counts how many spawns started inside the staged tree. Strictly, every one of them is untraceable.

- **git only (13):** batch-ci (1681, all in tmp fixtures), begin-plan 105, brief-compose 6, check-decision-scheme 32, check-diff-coverage 103,
  check-doc-citations 264, check-plan-progress 11, check-reference-namespace 77, check-review-recorded 475, gen-work-lines 25,
  goal-tree 29, peer-sites 1, record-review-verdict 179.
- **python children** (these can run a repo script and read the repo themselves, so they are genuinely untraceable): bounded_read, check-banner-armed (19),
  check-ci-watched, check-closing-table (18), check-fixture-git-isolation (209), check-handoff-path, check-merge-ready (110),
  check-plan-code (162), check-selection-card, check-selftest-counts, check-stalled-work, check-surface-recall (198),
  check-transcript-references (18), check-usage-pace, codex-review (18), compaction-state (20), explainer-serve, fixture_git
  (it also calls `os.system` once), gates-for-pr (28), gen-backlog-page, observer_log, push-command, regen-pages (12), session-state, sweep-red-alert.
- **node:** check-page-links (82), check-paid-caller-arrival (20), page_chrome, explainer-serve, check-stalled-work.
- **shell only:** check-compaction-boundary (16), check-rc-contract (1598). Shell mixed with others: check-run-hook (202), push-command (99), check-plan-leak.
- other (unclassified argv): gen-dashboard, gen-backlog-page, session-state, check-stalled-work.

The full per-target argv samples are in `observed.json` → `spawn_samples`. This list is the fail-closed cost: these targets can
never be reused by a read-set cache unless the children are traced too, e.g. by putting the wrapper on the children's path.

## NOT MEASURED

- `scripts/push-command.py`: rc 1, 349/352 cases passed, 54 s. Its suite FAILED under the hook, so its data is NOT MEASURED.
  Unknown whether the hook or this local environment caused it, since it was not re-run without the hook. It spawns anyway, so it re-runs in every estimate.
- No timeouts (MEASURED: all 90 finished under 200 s; the longest was check-merge-ready at 55 s).

## What would make these numbers wrong

1. **Existence checks are invisible.** `os.stat`, `Path.exists`, `is_file` and `is_dir` raise NO audit event (MEASURED by probe). A suite
   whose behaviour depends on a file being present is under-counted. For an ADDED or DELETED path this can turn a "reuse" into a stale verdict.
2. **Child processes are not audited.** 46 of 90 targets spawn children, as listed above. A git child in a tmp fixture is probably harmless
   (INFERRED, not verified); a python child running a repo script is not.
3. **The selector ran on the master tree (d206e066), not on each PR's head.** The reads were measured on that same tree, which is 1 commit after
   #545's merge and 4 after #543's, not on each PR's base or head. A target's read set can differ between trees: INFERRED to be small.
4. **The read sets are from ONE unmutated run.** A mutant can take a different branch and open files the control never opened. A cache
   keyed on the control's reads assumes they are the same, and that assumption is UNMEASURED.
5. **`dir_fd`-relative opens are mis-resolved.** `shutil.rmtree` opens directories relative to a dir fd; the hook sees a bare name.
   These were filtered out by keeping only paths tracked under the staged roots (up to 240 such opens per target were dropped). A real
   read of a relative name that also exists at the tree root would be mis-attributed.
6. **The import system's directory listings** (`os.listdir('scripts')` on every import) count as a listing dependency. Only ADDED or DELETED
   paths are matched against listings, and no added path in either PR is under `scripts/`.
7. **What the hook does see:** imports DO appear as `open` events (through `io.open_code`), and no `.pyc` is involved, because no
   `__pycache__` is staged and bytecode writes are off. `sqlite3.connect` and `mmap` events were captured; there were zero of either. A C extension
   reading through its own `fopen`, or a tool such as `tsc` reading via node, is missed. The only node users are already counted as spawners.
8. Each suite ran in a SHARED staged tree, in sequence, as the harness's controls do. A suite that wrote into the tree could change what a later one read.
   Writes into the tree are recorded per target (`observed.json` → `writes`); they were not cross-checked against later reads.
