# Observed-reach selection — a PR sweeps the manifests whose suites READ what it changed

> **Anchor:** `dev-speed-first` — **ADR:** none
> **Goal:** A change gets its verdict as fast as the evidence allows, with mutation coverage identical.

**Status:** 🟠 needs-you — DRAFT, written 2026-11-09 for backlog #586, folded after review rounds 1 and 2
(`docs/reviews/coordinator/observed-reach-spec-r2-coordinator.md`); waits on the owner's walkthrough (§7).
Nothing here is built. Every number is marked MEASURED (run) or INFERRED (reasoned, not run). The read sets are on
record in `docs/reviews/measurements/2026-11-09-observed-reads-spike.md`; §5 scores this spec's rules on them
with a scratch scorer, once with §3's eligibility applied and once with it assumed met, and says which is which.

## In plain words

A pull request that only edits the backlog and the dashboard still runs most of the mutation sweep. The sweep
picks a guard whenever the guard's source text NAMES a changed file, or quotes a directory above it, and dozens
of guards quote `docs` without their tests ever opening the file.

This spec picks guards by what their tests were SEEN to read instead. Master's full sweep already runs every
guard's suite; a separate, extra recording run of each suite logs which files it opens, lists and probes. A PR
then runs a guard's mutants only if that guard's suite touched a file the PR changed. A guard that cannot be
traced is picked exactly as it is today.

The owner's direction (2026-11-09 02:33): *"sweep decision should be based on actual ripple effects which can
be traced by closure"*; and 02:45: *"intention is to reduce sweep if possibility of harmful effect caused by
related file changes are low as we already [have an] occasional full sweep which will catch missed hole in
detection."*

## 1. The problem, measured

`select_manifests` in `scripts/check-plan-code.py` picks targets per changed path. For a path under `docs/`, the
`between` list starts AT the staged root, so every target that quotes `'docs'` is picked by every `docs/` change.

| PR | changed (added/deleted) | targets | picked today (MEASURED, current selector) |
|---|---|---|---|
| PR #545 | 2 (0) | 91 | 64 |
| PR #543 | 17 (11) | 91 | 68 |
| this spec's PR, `5ee0b6d7` | 6 (2) | 91 | 64 |
| one brand-new `docs/zzz.md` alone | 1 (1) | 91 | 51 |

- MEASURED (spike, on `d206e066`, 90 targets, local run): 43 targets are traceable (green, no child process).
  47 spawn a child, one of which (`push-command`) also failed under the hook. Only 7 targets read the two files
  PR #545 touches.
- MEASURED: 26 of the 30 first-parent master commits ending at `4a6f1577` add or delete at least one file, so
  most PRs are not modify-only.
- MEASURED (backlog #586's row): PR #539 picked 67 of 89.

## 2. The mechanism

**Record — a separate run, never the control.** On a `push` to `refs/heads/master` and on the schedule (never a
`batch/**` push, never a pull request), after a shard's verdicts are final, the shard runs ONE extra pass: each
target it OWNS runs `<target> --self-test` under the recording launcher. A target's owner is the LOWEST-index
shard whose `shard_slice` holds one of its entries, so the owner always ran that target's real control in the
same job (a fixed `index mod N` partition does not: MEASURED, 27 of 91 such owners at N=24 run no control for
their target, r2 Codex F2). That pass feeds neither `control_is_green` nor `control_seconds`, so a recorder fault
cannot red a target or move a mutant's timeout. The launcher reproduces the real control's argv, `sys.path[0]`,
`cwd` and environment (`mutation_env(d, seed)`), once per seed the run uses; read sets from several seeds are
united. A target gets a read set only when, FOR EVERY SEED, its recording run is green by `control_is_green` AND
its case count equals that seed's real control count in the owner shard; and the merge refuses it when two shards
that ran its control report different counts. Otherwise it has none and falls back (§3). Each target's record:

- `reads`: every path under the staged roots the suite opened, tracked or not (imports arrive as `open` events
  through `io.open_code`), each tracked one with its git blob SHA;
- `probed`: every path under the staged roots it tried to open and could not, plus — under option B of Q1 —
  every path it passed to `os.stat`, `os.lstat` or `os.access`, present or not;
- `listed`: the directories it listed (`os.listdir`, `os.scandir`, `glob.glob`, `os.walk`);
- `spawned`: whether any process-creation event fired: `subprocess.Popen`, `os.system`, `os.exec`,
  `os.posix_spawn`, `os.spawn`, `os.fork`, `os.forkpty`, `pty.spawn`;
- `rc`, the case count, the seed, the tree's commit, the harness hash and the Python version.

The launcher is a module `check-plan-code.py` imports at top level, so `harness_files` makes it a harness file:
changing it runs ALL, and the harness hash (over the sorted `harness_files` blobs) covers it. INFERRED cost: the
spike's 90 hooked suites took 602 s serially on a laptop, so about 602/N s per shard; it is timed on one real
full sweep before the build plan fixes N's budget.

**Store.** Each shard uploads its part as an artifact. `mutation-sweep-complete` merges them only when every
expected shard contributed, every manifest target appears exactly once (with a read set or an explicit refusal),
and every shard's sweep finished. It then saves `readsets.json` with `actions/cache/save`, keyed
`readsets-<python>-<harness hash>-<sha>`. A partial set is never saved. The payload carries its own sha, harness
hash and Python, so a restore is validated by content, not by the key it was asked for.

**Resolve once, before the matrix.** A new job, `sweep-select`, runs before `mutation-sweep`. It lists the cache
entries with the `readsets-<python>-<harness hash>-` prefix through the Actions API, keeps those whose sha is an
ancestor of BASE, takes the nearest, restores it by exact key and validates the payload. It computes the
selection ONCE and passes the target list (or `full: <why>`) to every shard as a job output. Shards no longer
select, so two shards cannot slice two different lists with one stride. A miss, an API failure or a payload that
does not validate is today's selection for every target, logged; never an error. BASE is the commit the diff
starts from: `git merge-base origin/$BASE_REF HEAD`.

**The diff.** `git diff --name-status -z --no-renames origin/$BASE_REF...HEAD`, so each path carries `A`, `M`
or `D`, and a rename arrives as a `D` plus an `A`. An unparseable list is today's `changed is None`: FULL.

**Use.** Today's rules come first and are unchanged, as the code has them:

1. FULL: a harness file, a dependency manifest, a manifest whose target this tree does not load, a staged path
   no target names or quotes, a path named by more than `SHARED_FULL_FRACTION` of targets.
2. Mandatory: a target's own source or own manifest changed picks that target, read set or not.
3. A target with a usable read set (§3) is picked when (a) a changed path, `A`, `M` or `D`, is in its `reads` or
   its `probed` (a size or mode change seen only through `stat`/`access` is an `M`: r2 Codex F1), (b) an added or
   deleted path lies under a directory in its `listed`, or (c) an added or deleted path is matched by the
   existence rule the owner chooses in Q1.
4. Any other target is picked by today's naming rule, exactly as now.

The log line keeps today's form and names the rule: `  check-features <- docs/backlog.md (observed)` or
`… (named: spawns)`, and a parseable `WOULD-SKIP:` / `SKIPPED:` line lists the targets dropped.

## 3. Fail-closed rules: when a target falls back to today's rule

A read set is used only when every condition holds; otherwise rule 4 (naming) applies to that target.

| Condition | Why |
|---|---|
| No process-creation event fired | A child's reads, and a forked child's, are not audited (spike caveat 2) |
| A read set exists, recorded green with the real control's case count | A new, failed or hook-disturbed suite has no trustworthy reads |
| No path in `reads` or `probed` was MODIFIED between the set's sha R and BASE | Master moved under it |
| Added and deleted paths are taken over R..HEAD, not only BASE..HEAD | A master addition after R can switch on a dependency the set never saw (r1 Codex F1, reproduced) |
| No path added or deleted over R..BASE lies under a directory in its `listed` | A file added after R under a walked directory is read on the PR's tree but is in no `reads` (r1 Claude F4) |
| The payload's harness hash and Python match the run's | A changed harness or interpreter can read differently |
| The restore validated (§2 Resolve) | Otherwise every target uses today's rule |

## 4. Why it is sound enough, and what it can miss

**The claim.** If a target's unmutated suite never opened, probed or listed above file F, then a change to F
cannot change that suite's control result. INFERRED: it is also unlikely to change a mutant's verdict, because a
mutant runs the same suite on the same fixtures.

**What it can miss.** The bound, stated so it can be checked:

1. **A mutant's branch reads a file the control never opened.** UNMEASURED (spike caveat 4).
2. **Existence checks the chosen Q1 option does not see** (§7 Q1 states each option's gap).
3. **Reads the hook cannot see:** a C extension's own `fopen`, a mis-resolved `dir_fd` open, and a suite that
   writes into the shared staged tree and changes a later suite's reads (spike caveats 5, 7, 8).
4. **Drift between trees and events.** Reads recorded on master can differ from the PR head's. The suites see
   `GITHUB_*` from `os.environ` (`child_env`), so a suite that branches on the event reads differently on a
   `push` than on a `pull_request`. Every figure here is from a local run; CI's reads are not yet measured.

**Why that is acceptable.** Every miss is a mutant left unchecked on the PR. No mutant, case or pin is removed,
so master's coverage is IDENTICAL, and master's full sweep (every merge, and daily) catches a miss. That is the
backstop the owner named at 02:45. The cost of a miss is NOT one red sweep: backlog #560's row records "10
survivors = 3 distinct defects, each red 1-3 days", and while one is unfixed every later full sweep is red and
comments on the single open `sweep-red` issue, so a second miss can hide behind the first. §8.1 is the detector
that separates them.

## 5. Expected saving

Read sets MEASURED (spike, `d206e066`, local). The scorer applies §3 to them three ways (r2 Codex F3):

- **Strict** (R = `d206e066`, every §3 row): **0 usable read sets on every scored commit, so the saving is 0**
  (MEASURED). 14 of the 15 commits below, PR #545 and PR #543 among them, have bases older than R (ancestry
  fails); this spec's PR and `4a6f1577` have `check-plan-code.py` changed over R..BASE (the harness hash fails). The spike
  cannot measure an eligible saving; only shadow mode can (Q4).
- **Footprint** (R = BASE: a recording at the PR's own base that read what the spike read; every check passes
  by construction). The table; INFERRED, since the reads at each historical base were not recorded.
- **Lag 1** (R = BASE's parent; staleness, listing and R..HEAD rules applied, harness hash assumed equal):
  INFERRED, in the last column. 4 of the 15 commits get 0 usable sets, because an addition under `scripts/`
  over R..BASE makes every traceable set stale (all of them list `scripts`). So the saving needs a recording at,
  or very near, nearly every master commit.

| Q1 option (§7) | PR #545 | PR #543 | this spec's PR | 15 non-FULL of the last 30: median (total) | same, lag 1 |
|---|---|---|---|---|---|
| today's selector (MEASURED) | 64 | 68 | 64 | 67 (1,014) | 67 (1,014) |
| A — the full naming rule for added/deleted paths | 36 | 65 | 61 | 65 (879) | 65 (988) |
| D — naming with sub-root directory quotes only | 36 | 46 | 50 | 45 (676) | 46 (774) |
| B — literal namers + probes + listings | 36 | 41 | 36 | 40 (637) | 41 (726) |

- The other 15 of those 30 commits run ALL under every option and gain nothing (MEASURED): 13 change the harness
  or the workflow, and 2 change a module more than half the targets name (`codex-review`, `fixture_git`).
- Observed reach can pick MORE than today: one commit that adds a module under `scripts/` picks 76 under every
  option (footprint), against today's 67.
- The saving is capped by spawning: 33 of PR #545's 36 picks are spawners (MEASURED reads, INFERRED pick).
- Adding any file under `scripts/` picks all 43 traceable targets, because the import system lists `scripts`
  for each of them (MEASURED). That is correct: a new module can shadow an import.
- Wall-clock seconds are NOT estimated: the slowest control took 55 s and is a spawner that stays picked.
- Option B's figures assume the `stat` probes add no picks; that is UNMEASURED until the launcher records them.
  The r2 rule that a MODIFIED probed path picks (§2 Use 3a) adds 0 picks here, since the spike's probes are
  failed opens of absent paths (MEASURED).
- Not applied, because the spike did not record them: the Python-version check and the case-count check.

**A later step: git-only spawners.** 13 targets spawn only `git`; 1,681 of `batch-ci`'s git calls ran in tmp
fixtures (MEASURED). Counting such a spawn as traceable needs a recorded proof that it reads no repo file (`cwd`
outside the staged tree, no argv path inside it). Not in v1; see Q2.

## 6. How backlog #560 reuses the recording

Backlog #560 caches each MUTANT's verdict across runs. It can reuse this spec's INFRASTRUCTURE: the launcher,
the blob-hashed record format, the artifact merge, the cache key and the resolve job. It cannot reuse the read
sets themselves: its row requires everything THAT MUTANT RUN read, and a mutant can open, spawn or probe what
its control did not. So backlog #560 must record per mutant execution, with the mutation's identity and the
environment in its key. This spec does not claim more. INFERRED (the spike's own scorer): 40 of 90 targets would be
reusable at the strict rule for PR #545, before any per-mutant recording narrows it. The owner agreed
(2026-11-09) that backlog #560 is the speed lane's next big item and that backlog #534 retires when it lands.

## 7. Questions only the owner can answer

| # | Question | Recommended answer |
|---|---|---|
| Q1 | An added or deleted path can matter to a suite that only checked whether it EXISTS, and `stat` raises no audit event (MEASURED by probe). Which rule picks a traceable target for such a path? **A:** today's full naming rule, directory quotes included (safest; saves only on modify-only PRs). **B:** record failed opens and wrapped `os.stat` / `os.lstat` / `os.access` calls, keep the literal namers (path, file name, import spelling), drop the directory quotes. **C:** literal namers only, no probe recording. **D:** naming with directory quotes below the staged root only | **B.** It sees an existence check on a computed name, which A sees only by over-picking and C not at all. Gap: a probe made in C code or in a child (spawners already fall back). Its footprint is the lowest under every scoring in §5 (40 median against today's 67; 41 at lag 1), but those are INFERRED: applied strictly to the spike, every option saves 0, so the real saving is measured in shadow mode (Q4). Unchanged by r2's re-scoring: the ORDER B < D < A < today holds in both. Its `stat` probes are measured in shadow mode before the switch, and B falls back to A if they add more than 5 picks on PR #543's diff |
| Q2 | Should git-only spawns in tmp fixtures count as traceable, for 13 more targets? | **Not in v1.** A second step, after a recorded proof per spawn (§5) |
| Q3 | When a target cannot be traced, fall back to TODAY's naming rule, or always pick it? | **Today's rule.** Never fewer than now. Always picking raises PR #545 from 36 to 50 (47 untraceable + 3 readers; INFERRED) |
| Q4 | Run in SHADOW mode first, logging both selections while still running today's? | **Yes, for 20 COMPLETE PRs** (§8.5: an incomplete comparison is inconclusive and does not count). Switch only if no would-skip target's verdicts differ between the PR's own sweep and its base's full sweep (§8.1). 0 in 20 bounds the per-PR miss rate below 14% (95%), ASSUMING the 20 are consecutive (not chosen), independent, and each has at least one would-skip target; 5 PRs would bound it only below 45%. Shadow mode also MEASURES the real saving and the fallback rate, which §5 cannot |
| Q5 | Do you accept §4's bound, with master's full sweep as the catch and §8.1 as the detector? | **Yes.** It is your 02:45 direction. Revisit on the first §8.1 event |
| Q6 | Ship before backlog #560, as its first slice, or inside it? | **Before.** It is target-level and smaller, and it builds the infrastructure backlog #560 extends with per-mutant recording (§6) |

Recording on master only (never on a PR) is not a question: a PR's unmerged code must not decide another PR's
sweep, by the same argument §2 gives.

## 8. FAILS IF

The built feature FAILS IF any of these is observed.

1. **A would-skip or skipped target's verdict was wrong.** In shadow mode: a target in a PR's `WOULD-SKIP:` line
   whose per-mutant verdicts (survivors, CANNOT RUN) on the PR's own sweep, at any push, differ from its base's
   full sweep. After the switch: a red master full sweep whose red targets (read from each shard's structured
   results artifact) intersect the `SKIPPED:` set of a PR merged since the last green full sweep (the PR found
   from the squash subject's `(#N)`, its selection from that run's artifact). One case stops the switch, or
   reverts it, until §4 is re-examined.
2. **The selection is not the exact one.** A committed read-set fixture plus PR #545's diff selects EXACTLY the
   33 spawners named by today's rule plus `check-canonical-source`, `check-dashboard-entry` and
   `check-features`, each with its reason. Also cased: a traceable reader of a changed path is picked; a
   traceable non-reader with no mandatory reason is not; an own-source and an own-manifest change pick their
   target with no read set; a FULL rule still runs ALL.
3. **A fail-closed rule does not fire.** Each §3 condition is a self-test case with an ADJACENT negative: a
   `Popen`, an `os.fork` and an `os.system` spawner; a missing, red, short-count, stale (read or probed path
   modified), wrong-key and unvalidated set; a path added after R under a listed directory, with an addition
   under an unlisted one as the negative; an addition over R..BASE that switches on a dependency (Codex's r1
   reproduction); an unparseable cache or diff; a MODIFIED path in `probed` only, by size and by executable bit
   (r2 Codex F1), with an unprobed modification as the negative. Each one's mutation (dropping it) must go red.
4. **A partial or wrong read set is saved or used.** `readsets.json` is saved with a shard missing, a target
   missing or doubled, a green-sweep condition unmet, or from a `batch/**` push or a PR; or a read set kept for a
   target its owner shard ran no control for, or whose per-seed or cross-shard counts disagree; or a shard runs
   a selection other than `sweep-select`'s output.
5. **A missing comparison counts as a clean one.** A shadow PR counts toward Q4's 20 only when, for EVERY
   would-skip target, both the PR's sweep at its final push and the base's full sweep produced a verdict per
   mutant; a cancelled run, a missing artifact or a CANNOT RUN control on either side makes that PR
   INCONCLUSIVE, logged, never a pass. A control that failed on one side and not the other is a differing
   verdict. Cased: a cancelled PR run, a missing base artifact and a red control each yield INCONCLUSIVE.
