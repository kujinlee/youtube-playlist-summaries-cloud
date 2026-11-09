# Observed-reach selection — a PR sweeps the manifests whose suites READ what it changed

> **Anchor:** `dev-speed-first` — **ADR:** none
> **Goal:** A change gets its verdict as fast as the evidence allows, with mutation coverage identical.

**Status:** 🟠 needs-you — DRAFT, written 2026-11-09 for backlog #586; waits on the owner's walkthrough (§7).
Nothing here is built. Every number is marked MEASURED (run by the spike) or INFERRED (reasoned, not run).
The measurements are on record in `docs/reviews/measurements/2026-11-09-observed-reads-spike.md`.

## In plain words

A pull request that only edits the backlog and the dashboard still runs most of the mutation sweep. The sweep
picks a guard whenever the guard's source text NAMES a changed file, and dozens of guards name
`docs/backlog.md` without ever opening it in their tests.

This spec picks guards by what their tests were SEEN to read instead. Master's full sweep already runs every
guard's test suite once, unmutated, before mutating it. Recording which files each of those runs opens costs
almost nothing. A PR then runs a guard's mutants only if that guard's suite read a file the PR changed. If the
guard cannot be traced, it is picked exactly as it is today.

The owner's direction (2026-11-09 02:33): *"sweep decision should be based on actual ripple effects which can
be traced by closure"*; and 02:45: *"intention is to reduce sweep if possibility of harmful effect caused by
related file changes are low as we already [have an] occasional full sweep which will catch missed hole in
detection."*

## 1. The problem, measured

`select_manifests` in `scripts/check-plan-code.py` picks a target for a changed path when the target's source,
or a module it imports, contains one of the path's spellings (`_names_of`). That is a NAMING test. A guard that
mentions `docs/backlog.md` in a docstring, an error message or a fixture is picked by every backlog edit.

| PR (MEASURED, spike on `d206e066`) | targets | picked by name | picked AND seen reading a changed path | picked, untraceable (spawns) | picked, traceable, read NO changed path |
|---|---|---|---|---|---|
| PR #545, docs only (2 files) | 90 | 64 | 6 (3 traceable) | 33 | **28** |
| PR #543, mixed (17 files) | 90 | 68 | 20, +1 by listing an added file (6 traceable) | 35 | **27** |

- MEASURED: only 7 targets read the two files a docs-only PR touches; the selector picks 64.
- MEASURED: 43 of 90 targets are traceable, meaning their suite spawns no child process. 46 spawn and 1 failed.
- MEASURED: none of the last 60 merged PRs changes only `scripts/`, so the docs-only shape is every PR's shape.
  Every PR records a dashboard entry.
- MEASURED (backlog #586's row): PR #539 picked 67 of 89.

## 2. The mechanism

**Record.** On a `push` to master and on the schedule (the full sweep), each shard already runs a CONTROL. The
control is every target's suite, unmutated, in the staged tree, before its mutants run. The control runs
`<target> --self-test` under a small launcher. The launcher installs `sys.addaudithook` and then runs the
target with `runpy.run_path` (the spike's `audit_wrap.py`). For each target it records:

- `reads`: the tracked paths under the staged roots that the suite opened. Imports are included, since they
  arrive as `open` events through `io.open_code`. Each path carries its git blob SHA.
- `listed`: the directories it listed.
- `spawned`: whether it started any child process, with argv kinds (`git`, `python`, `node`, shell).
- `rc` and the seconds taken.
- The tree's commit, the harness hash and the Python version.

Only the control is wrapped, never a mutant, so a verdict is never computed under the hook. INFERRED: the
hook's cost is small, because the spike ran all 90 suites under it with no timeout. It was not timed against
an unhooked run.

**Store.** Each shard uploads its part. The existing `mutation-sweep-complete` job merges the parts into one
`readsets.json` and saves it with `actions/cache/save`, keyed `readsets-<python>-<harness hash>-<sha>`. The
merge happens only when every shard's control was green: a partial set is never saved. The workflow already
uses `actions/cache` for the ffmpeg packages. A cache made on the default branch can be restored by a PR run.

**Use.** A PR run restores the newest `readsets-<python>-<harness hash>-` entry whose `<sha>` is an ancestor of
the PR's base. Then, for each target, in this order:

1. Today's whole-manifest rules come first and are unchanged: the harness, a dependency manifest, a target's
   own manifest, a shared module, an unrecognised path. Each of these runs ALL.
2. If the target has a usable read set (§3), it is picked when a path changed by the PR appears in its `reads`.
   It is also picked when a path ADDED or DELETED by the PR sits under a directory in its `listed`.
3. Otherwise it is picked by today's naming rule, exactly as now.

The log line keeps today's form and says which rule picked each target:
`  check-features <- docs/backlog.md (observed)` or `… (named: spawns)`.

## 3. Fail-closed rules: when a target falls back to today's rule

A read set is used only when every condition below holds. Otherwise the target is picked by the NAMING rule.
Nothing here can pick fewer targets than today for an untraceable one.

| Condition | Why |
|---|---|
| The suite spawned nothing | A child process's reads are not audited (the spike's caveat 2) |
| A read set exists for this target, and its control's `rc` was 0 | A new target, or a suite that failed or timed out, has no trustworthy reads |
| No path in `reads` changed between the read set's commit and the PR's BASE | Otherwise master moved under it, and the set describes a tree that no longer exists |
| The harness hash and the Python version match the cache key | A changed harness or interpreter can read differently. A changed harness already runs ALL |
| Every ADDED or DELETED path in the PR is ALSO run through the naming rule, and both results are united | `stat`, `exists`, `is_file` and `is_dir` raise no audit event (MEASURED by probe), so the existence of a file is invisible to `reads` |
| A rename counts as one deletion plus one addition | Two paths change existence |
| No cache entry restores, or it fails to parse | The run is today's selection for every target, and the log line says so; this is not an error |

## 4. Why it is sound enough, and what it can miss

**The claim.** Suppose a target's unmutated suite never opened file F. Then a change to F cannot change that
suite's control result. INFERRED: it is also unlikely to change any mutant's verdict, because a mutant runs the
same suite on the same fixtures.

**What it can miss.** This is the bound, and it is stated so it can be checked.

1. **A mutant's branch reads a file the control never opened.** If the PR changed that file, the verdict could
   differ, and it is not re-checked on the PR. The spike measured the control only. The rate at which mutants
   read outside their control's set is UNMEASURED (the spike's caveat 4).
2. **Existence checks on computed names.** §3 unites the naming rule for added and deleted paths. That covers a
   literal name, but not a name the suite builds at run time and only `stat`s.
3. **Reads the hook cannot see.** These are a C extension calling `fopen`, an `open` relative to a `dir_fd`
   that resolves to the wrong file, and a suite that writes into the shared staged tree and changes what a
   later suite reads (the spike's caveats 5, 7 and 8). Node and shell users are spawners, so they fall back.
4. **Drift between trees.** Reads recorded on master can differ from the PR head's reads. §3's staleness rule
   covers files changed on master. A change made by the PR itself to the target's own code is not a gap: the
   target's own source is in its `reads`, so it is picked.

**Why that is acceptable.** Every miss is a mutant whose verdict is left unchecked on the PR. No mutant, case
or pin is removed, so coverage of master is IDENTICAL. The master full sweep runs on every merge, and the
schedule runs it daily. That sweep is what catches a miss, and a red sweep opens a `sweep-red` issue. This is
the backstop the owner named at 02:45 (quoted above). INFERRED cost of a miss: one red master sweep and one fix
PR, the same failure shape backlog #560 records (12 red post-merge sweeps since 11-01, as recorded in that row).

## 5. Expected saving

| | PR #545 | PR #543 |
|---|---|---|
| Picked today (MEASURED) | 64 | 68 |
| Picked with observed reach, strict: a spawner falls back (MEASURED reads, INFERRED selection) | **36** (−28, −44%) | **41** (−27, −40%) |
| Counting the 13 git-only spawners as traceable (INFERRED, a later step) | 25 (−39) | 33 (−35) |

- The selection rows apply §2 and §3 to the spike's measured reads and its measured spawn list. The rule was
  not run end to end in CI: INFERRED.
- Wall-clock seconds are NOT estimated. Targets differ widely in cost (MEASURED: the slowest control took 55 s,
  and it is a spawner that stays picked), so 28 fewer targets does not mean 44% less time.
- The saving is capped by spawning, not by reads. 33 of PR #545's 36 remaining picks are spawners (MEASURED).
- **The later step: git-only spawners.** 13 targets spawn only `git`, and 1,681 of batch-ci's git calls ran in
  tmp fixtures (MEASURED). Counting such a spawn as traceable needs proof that it reads no file in the repo. The
  proof would be: `cwd` outside the staged tree, and no argv path inside it. That proof is not in v1; see Q2.

## 6. How backlog #560 reuses the recording

Backlog #560 caches each MUTANT's verdict across runs. A mutant is skipped when nothing it read changed since
its last green run. It needs the same thing this spec builds: per-target observed reads with content hashes,
recorded on a trusted tree, stored in `actions/cache` and failing closed on spawns.

- §2 records blob SHAs, not only paths, so backlog #560 needs no second recorder. That is why the hashes are
  included.
- What backlog #560 adds: a verdict per mutant keyed on (target hash, mutation id, read-set hashes), and
  reuse across ALL targets, not only the picked ones. MEASURED estimate for PR #545 at the strict rule: 40 of 90
  reused.
- The owner agreed (2026-11-09) that backlog #560 is the speed lane's next big item, and that backlog #534 (batch
  CI) retires when it lands. This spec is the first slice of that recorder.

## 7. Questions only the owner can answer

| # | Question | Recommended answer |
|---|---|---|
| Q1 | When a target cannot be traced, should it fall back to TODAY's naming rule, or always be picked? | **Today's rule.** That is never fewer than now. Always picking would raise PR #545 from 36 to 49 picks (INFERRED: 46 spawners + 3 traceable readers) |
| Q2 | Should git-only spawns in tmp fixtures count as traceable, for 13 more targets? | **Not in v1.** Do it as a second step, after a recorded proof per spawn (§5) |
| Q3 | Should read sets be recorded on master's full sweep only, or on PR runs too? | **Master only.** It is the trusted tree, and a PR's unmerged code must not decide another PR's sweep |
| Q4 | Should it run in SHADOW mode first, logging both selections while still running today's? | **Yes, for 5 PRs.** Then switch, if no shadow-skipped target was red on that PR's merge sweep |
| Q5 | Do you accept §4's bound (unmeasured mutant-branch reads), with the full sweep on master as the catch? | **Yes.** This is your 02:45 direction. Revisit if a master sweep goes red on a target that observed reach skipped on its PR |
| Q6 | Should this ship before backlog #560, as its first slice, or be folded into it? | **Before.** It is smaller, it is target-level, and it is the recorder backlog #560 needs |

## 8. FAILS IF

The built feature FAILS IF any of these is observed.

1. **A skipped target reds.** A target that observed reach skipped on a PR is red on that PR's merge-commit
   full sweep, and the cause is the PR's change. Detected by comparing the PR's logged selection with the
   `sweep-red` issue's targets. One case means re-examining §4 before continuing.
2. **No saving.** Replaying PR #545's diff against a read set from its base picks 64 targets, meaning none
   dropped, or picks a traceable target that read no changed path.
3. **A fail-closed rule does not fire.** Each of these must reach today's rule, each as a self-test case with
   an ADJACENT negative: a spawner; a missing, stale, failed or wrong-key read set; an added or deleted path seen
   only by `exists`; an unparseable cache. Each one's mutation (dropping the condition) must go red.
4. **A partial read set is saved.** `readsets.json` is saved when any shard's control was not green, or a PR run
   restores a set whose commit is not an ancestor of its base.
