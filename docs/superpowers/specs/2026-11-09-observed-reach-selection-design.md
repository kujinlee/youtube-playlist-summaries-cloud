# Observed-reach selection — a PR sweeps the manifests whose suites READ what it changed

> **Anchor:** `dev-speed-first` — **ADR:** none
> **Goal:** A change gets its verdict as fast as the evidence allows, with mutation coverage identical.

**Status:** ✅ APPROVED by the owner 2026-11-09 (10:33, "I agree all your recommendations"; 10:40, selection card
answer A: record under `strace -f`). Written 2026-11-09 for backlog #586, folded after review rounds 1-3 (round 3
was the cap), then folded with the owner's decisions (§7). **No review round has seen round 3's dedicated
recording job or the strace recorder**; the build plan's review closes that gap
(`docs/reviews/coordinator/observed-reach-spec-r3-coordinator.md`). Nothing here is built. Every number is marked
MEASURED (run) or INFERRED (reasoned, not run). The read sets on record were taken by an AUDIT-HOOK spike
(`docs/reviews/measurements/2026-11-09-observed-reads-spike.md`), not by strace; §5 says which figures that
affects.

## In plain words

A pull request that only edits the backlog and the dashboard still runs most of the mutation sweep. The sweep
picks a guard whenever the guard's source text NAMES a changed file, or quotes a directory above it, and dozens
of guards quote `docs` without their tests ever opening the file.

This spec picks guards by what their tests were SEEN to read instead. Master's full sweep already runs every
guard's suite; a separate job beside it runs each suite once more under `strace -f`, which logs every file the
suite and every program it starts (python, git, node, a shell) opens, lists and probes. A PR then runs a guard's
mutants only if that guard's suite touched a file the PR changed. A guard whose suite could not be traced is
picked exactly as it is today.

The owner's direction (2026-11-09 02:33): *"sweep decision should be based on actual ripple effects which can
be traced by closure"*; and 02:45: *"intention is to reduce sweep if possibility of harmful effect caused by
related file changes are low as we already [have an] occasional full sweep which will catch missed hole in
detection."* At 10:33 the owner asked whether suites that start child processes could be traced too, rather than
falling back to the widest safe pick; the strace recorder (10:40) is that answer.

## 1. The problem, measured

`select_manifests` in `scripts/check-plan-code.py` picks targets per changed path. For a path under `docs/`, the
`between` list starts AT the staged root, so every target that quotes `'docs'` is picked by every `docs/` change.

| PR | changed (added/deleted) | targets | picked today (MEASURED, current selector) |
|---|---|---|---|
| PR #545 | 2 (0) | 91 | 64 |
| PR #543 | 17 (11) | 91 | 68 |
| this spec's PR, `5ee0b6d7` | 6 (2) | 91 | 64 |
| one brand-new `docs/zzz.md` alone | 1 (1) | 91 | 51 |

- MEASURED (audit-hook spike, on `d206e066`, 90 targets, local run): 43 targets are traceable BY THE AUDIT HOOK
  (green, no child process). 47 spawn a child, one of which (`push-command`) also failed under the hook. Only 7
  targets read the two files PR #545 touches. Under strace a spawner is traced too, so **43 of 90 is a LOWER
  bound on traceability**; strace's own count is UNMEASURED.
- MEASURED: 26 of the 30 first-parent master commits ending at `4a6f1577` add or delete at least one file, so
  most PRs are not modify-only.
- MEASURED (backlog #586's row): PR #539 picked 67 of 89.

## 2. The mechanism

**Record — one dedicated, unsharded job, never the control.** On a `push` to `refs/heads/master` and on the
schedule (never a `batch/**` push, never a pull request), a new job, `record-reads`, runs BESIDE `mutation-sweep`
on a GitHub-hosted Linux runner and reads nothing the sweep produces. (In-shard recording needed an owner shard
per target; round 2's rule put 68 of 91 owners and 553 of 602 s on shard 1, MEASURED, r3 F1.) It is a mode of
`check-plan-code.py` and builds its tree as `mutate_delivered` does: `stage_tree`, the redirected `CHILD_HOME`,
`seed_trees` for the run's seeds. For each manifest target, sorted, and each seed, it first runs the PLAIN control
exactly as `control_parts` does (`[sys.executable, <target>, "--self-test"]`, `cwd` the staged or seed tree,
`env=mutation_env(tree, seed)`). It then runs the same argv, `cwd` and environment under the recorder. Nothing
here feeds a sweep verdict, `control_seconds` or a mutant's timeout. A target gets a read set only when, FOR EVERY
SEED, both runs are green by `control_is_green`, their case counts are equal, and the trace is complete (below).
Otherwise it gets an explicit refusal and falls back (§3). Read sets from several seeds are united. One
difference from a shard is left: all 91 suites share one tree, so a suite's predecessors are not a shard's (§4.3).

**The recorder: `strace -f` (owner, 2026-11-09 10:40).** The suite runs as `strace -f -y -o <log> <argv>`, so
every child process is traced: python, git, node and the shell. The traced calls are `openat` (and `open`),
successful AND failed; `stat`, `lstat`, `newfstatat` and `statx`; `access`, `faccessat` and `faccessat2`; the
directory reads `getdents64` (with `-y` naming the directory); `chdir` and `fchdir`, to follow each process's
working directory; and `execve`, `clone`, `fork` and `vfork`, to know each process's parent. The exact list is
confirmed by the build's first step (below): which `stat` variant glibc and Python use on the runner is INFERRED,
not measured. Owner's Q1 option B — failed opens plus stat and access probes — is therefore implemented by strace
itself, with no Python stat or access wrapper.

**Normalising strace's paths against the staged tree.** strace logs a path as the process passed it, so the
recorder resolves each one before it counts:
- a relative path against THAT process's cwd at that moment: the cwd starts as the suite's `cwd`, a child inherits
  its parent's at `clone`/`fork`, and `chdir`/`fchdir` move it;
- an `*at` call against its directory descriptor, which `-y` prints as a path;
- a `/proc/self/...` or `/proc/<pid>/...` path (`cwd`, `fd/N`, `root`) to what it names for that process;
- `..` segments and symlinks inside the staged tree, so a path counts once under its staged-tree name.

Only paths that resolve under a staged root count. **A path with a `.git` component is never a read of a repo
file**: git's reads of its own metadata in the temp repositories that fixtures build (and of any other `.git`)
are dropped, while git's reads of working-tree files under the staged roots still count. A path that cannot be
resolved (an unknown cwd, an unknown descriptor) makes the trace INCOMPLETE, and the target is refused, never
recorded with the path dropped.

**Each record:**

- `reads`: every path under the staged roots any traced process opened, tracked or not (imports arrive as
  `openat`), each tracked one with its git blob SHA;
- `probed`: every path under the staged roots a traced process tried to open and could not, or passed to a
  `stat`- or `access`-family call, present or not;
- `listed`: the directories under the staged roots any traced process listed (`getdents64`);
- `trace`: `complete`, or the reason it is not (strace missing, ptrace denied, strace's own exit, a log that did
  not parse, an unresolved path);
- `recorder`: `strace`, or `audit-hook` under the fallback below;
- `rc`, the case count, the seed, the tree's commit, the harness hash and the Python version.

**The build plan's FIRST step: prove the recorder can run (owner, 10:40).** On a GitHub-hosted `ubuntu` runner,
in the job's own setup, install or locate `strace` and trace one suite that spawns `git`, then check that the
log names a file the child opened. If ptrace is denied or strace is unavailable there, v1 FALLS BACK to the
audit-hook recorder the spike used (`sys.addaudithook` on `open`, `os.listdir`, `os.scandir`, `glob.glob`,
`os.walk` and the process-creation events, with failed opens and wrapped `os.stat` / `os.lstat` / `os.access` as
`probed`). Under that recorder a suite that fires a process-creation event is untraceable and takes today's
naming rule (§3). The rest of this spec is unchanged by the choice of recorder.

**Cost.** UNMEASURED. strace's overhead is expected at 2-5x per traced suite (not measured here), and it lands
only on the recording job, never on a PR or the sweep. The audit-hook spike's 90 suites took 602 s serially on a
laptop (MEASURED); that is a floor for the traced pass, which now also traces every child. The job is timed on
its first CI run, gets its own `timeout-minutes` from that, and runs twice as long on the schedule's two seeds.
A master push already exceeds the account's 20-job limit, so it can queue. It is not a required check;
`mutation-sweep-complete` ignores it. The recorder is a module `check-plan-code.py` imports at top level, so
`harness_files` makes it a harness file: changing it runs ALL, and the harness hash (over the sorted
`harness_files` blobs) covers it.

**Store — the save condition (r3 F4).** The job saves `readsets.json` with `actions/cache/save` only when it
FINISHED: it was neither cancelled nor timed out, and every manifest target appears exactly once, with a read set
or an explicit refusal. A red plain control or an incomplete trace refuses that one target and does not block the
save. Nothing the sweep reports, a survivor or a red shard, can block it, because the job never reads the sweep.
The key is `readsets-<python>-<harness hash>-<sha>`. A partial set is never saved. The payload carries its own
sha, harness hash, Python and recorder, so a restore is validated by content, not by the key it was asked for.

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
   deleted path over R..HEAD (§3) lies under a directory in its `listed`, or (c) an added or deleted path over
   R..HEAD is named LITERALLY in the target's source: its path, its file name or its import spelling (Q1 B; the
   directory quotes are dropped).
4. Any other target is picked by today's naming rule, exactly as now.

**Q1's own fallback (owner, 10:33).** If the probes add more than 5 picks on PR #543's diff, measured in shadow
mode against the same read sets without `probed`'s stat and access entries, rule 3(c) reverts to option A (today's
full naming rule, directory quotes included, for added and deleted paths).

The log line keeps today's form and names the rule: `  check-features <- docs/backlog.md (observed)` or
`… (named: untraced)`, and a parseable `WOULD-SKIP:` / `SKIPPED:` line lists the targets dropped.

## 3. Fail-closed rules: when a target falls back to today's rule

A read set is used only when every condition holds; otherwise rule 4 (naming) applies to that target (owner, Q3,
2026-11-09: today's rule, never always-pick). Under strace this applies only where tracing FAILED for a suite.

| Condition | Why |
|---|---|
| The trace is `complete`: strace ran, ptrace was allowed, the log parsed, and every path resolved (§2). Under the audit-hook fallback recorder only: no process-creation event fired | An incomplete trace, or a child the audit hook cannot see (spike caveat 2), has no trustworthy reads |
| A read set exists, its recording green with the plain control's case count | A new, failed or recorder-disturbed suite has no trustworthy reads |
| No path in `reads` or `probed` was MODIFIED between the set's sha R and BASE | Master moved under it |
| Added and deleted paths are taken over R..HEAD, not only BASE..HEAD | A master addition after R can switch on a dependency the set never saw (r1 Codex F1, reproduced). With Use 3(b) this also covers a file added after R under a walked directory (r1 Claude F4): it is an `A` over R..HEAD, so 3(b) PICKS the target. The round-1 row that sent such a target to the fallback is removed (r3 F2): it was redundant, and the fallback can pick fewer |
| The payload's harness hash, Python and recorder match the run's | A changed harness, interpreter or recorder can read differently |
| The restore validated (§2 Resolve) | Otherwise every target uses today's rule |

## 4. Why it is sound enough, and what it can miss

**The claim.** If a target's unmutated suite, and every process it started, never opened, probed or listed above
file F, then a change to F cannot change that suite's control result. INFERRED: it is also unlikely to change a
mutant's verdict, because a mutant runs the same suite on the same fixtures.

**What it can miss.** The bound, stated so it can be checked:

1. **A mutant's branch reads a file the control never opened.** UNMEASURED (spike caveat 4).
2. **A dependency with no syscall on the path.** strace sees a probe made in C code or in a child, which the
   audit hook did not. It cannot see a process OUTSIDE the traced tree: a daemon the suite talks to that it did
   not start (a running git `fsmonitor`, a database, Docker), nor an open submitted through `io_uring`, which is
   not an `openat` call. INFERRED rare here; not measured.
3. **Reads the recorder mis-attributes or misses:** a path the normaliser resolves wrongly (§2), a read the `.git`
   rule drops that a suite depended on, and a suite that writes into the shared staged tree and changes a later
   suite's reads (spike caveat 8). The recording job runs every suite in one tree, so its predecessors differ
   from those in any shard. Under the audit-hook fallback, spike caveats 5 and 7 also apply (a mis-resolved
   `dir_fd` open, a C extension's own `fopen`).
4. **Drift between trees and events.** Reads recorded on master can differ from the PR head's. The suites see
   `GITHUB_*` from `os.environ` (`child_env`), so a suite that branches on the event reads differently on a
   `push` than on a `pull_request`. Every figure here is from a local run; CI's reads are not yet measured.

**Why that is acceptable (owner, Q5, 2026-11-09: accepted; revisit on the first §8.1 event).** Every miss is a
mutant left unchecked on the PR. No mutant, case or pin is removed, so master's coverage is IDENTICAL, and
master's full sweep (every merge, and daily) catches a miss. That is the backstop the owner named at 02:45. The
cost of a miss is NOT one red sweep: backlog #560's row records "10 survivors = 3 distinct defects, each red 1-3
days", and while one is unfixed every later full sweep is red and comments on the single open `sweep-red` issue,
so a second miss can hide behind the first. §8.1 is the detector that separates them.

## 5. Expected saving

**Every figure in this section came from the AUDIT-HOOK spike** (`d206e066`, local), whose recorder could not
trace a suite that started a child. Under strace:
- the traceability figures (43 of 90 traceable, 47 spawners falling back) are a LOWER bound;
- the pick figures are NOT a bound in either direction, and no new figure replaces them. A spawner that is now
  traced drops out where its children read no changed path (fewer picks). strace also sees probes, C-level reads
  and child reads the hook missed, and a child such as `git status` that stats every working-tree file makes its
  target pick on any change (more picks). INFERRED both ways; only shadow mode (Q4) measures it.

The scorer applies §3 to the spike's read sets three ways (r2 Codex F3):

- **Strict** (R = `d206e066`, every §3 row): **0 usable read sets on every scored commit, so the saving is 0**
  (MEASURED): 14 of the 15 commits below, PR #545 and PR #543 have bases older than R; this spec's PR and
  `4a6f1577` fail the harness hash. The spike cannot measure an eligible saving; only shadow mode can (Q4).
- **Footprint** (R = BASE: a recording at the PR's own base that read what the spike read; every check passes
  by construction). The table; INFERRED, since the reads at each historical base were not recorded.
- **Lag 1** (R = BASE's parent, every §3 row applied, the harness hash included: r3 F2): INFERRED, in the last
  column. 7 of 15 commits get 0 usable sets: six have a harness change over R..BASE, and `311d3631` modifies
  `scripts/fixture_git.py`, which all 43 traceable sets read. Additions under `scripts/` are not the cause (round
  2 said so with the hash off): 5 of the last 45 master commits add or delete there, three of them harness
  changes (MEASURED). Removing §3's listed-directory row changes no figure (MEASURED, re-scored).

| Q1 option (§7; audit-hook read sets) | PR #545 | PR #543 | this spec's PR | 15 non-FULL of the last 30: median (total) | same, lag 1, hash on |
|---|---|---|---|---|---|
| today's selector (MEASURED) | 64 | 68 | 64 | 67 (1,014) | 67 (1,014) |
| A — the full naming rule for added/deleted paths | 36 | 65 | 61 | 65 (879) | 65 (996) |
| D — naming with sub-root directory quotes only | 36 | 46 | 50 | 45 (676) | 53 (841) |
| B — literal namers + probes + listings (CHOSEN) | 36 | 41 | 36 | 40 (637) | 48 (807) |

- The other 15 of those 30 commits run ALL under every option and gain nothing (MEASURED): 13 change the harness
  or the workflow, and 2 change a module more than half the targets name (`codex-review`, `fixture_git`).
- Adding any file under `scripts/` picks all 43 traceable targets, because the import system lists `scripts`
  for each (MEASURED); correct, since a new module can shadow an import. So one such commit picks 76, against 67.
- Under the audit hook the saving was capped by spawning: 33 of PR #545's 36 picks are spawners (MEASURED reads,
  INFERRED pick). strace lifts that cap by however many spawners read no changed path; UNMEASURED.
- Wall-clock seconds are NOT estimated: the slowest control took 55 s and is a spawner.
- Option B assumed its `stat` probes add no picks (UNMEASURED, and strace sees more probes than the hook); its
  own fallback (§2) measures that. A MODIFIED probed path (Use 3a) adds 0 picks here: the spike's probes are
  failed opens of absent paths (MEASURED).
- Not applied, because the spike did not record them: the Python-version check and the case-count check.

**The cadence the saving depends on (r3 F3).** The saving exists only while every master push records. A
harness change resets it until the next recording lands.
- MEASURED (CI history, r3): all 45 of the last 45 master commits got a `push` run (never cancelled). A PR
  run's BASE is the master tip when it starts; a master run takes 40-60 min.
- MEASURED over 113 PR runs since `c85a10ba`, IF each GREEN master run saved at its end: the newest recording
  was at lag 0 for 37%, lag 1 for 48%, lag 2+ for 15%. With the harness hash (two of its three files), 73%
  have a usable set at lag 0-1, 78% at lag 0-2, and 22% miss because a harness change is in flight.
- INFERRED, the dedicated job, which saves without waiting for the sweep and after a red one: with the save at
  the master run's start + 25 min (assumed; 20 or 30 min give 90% and 89%), lag 0 rises from 42 to 82 of 113
  and usable sets from 88 to 101 (89%) (round-3 coordinator, `r3f_lag_dedicated.py`). **These save times assumed
  the audit-hook job's duration.** strace's overhead (UNMEASURED) lengthens the job, so the save lands later and
  these shares are an upper bound until the first CI run times it.
- INFERRED saving by lag, option B, 15 non-FULL commits, from today's 1,014 picks: 377 at lag 0, 207 at lag 1,
  123 at lag 2 (the spike's reads stand in for each R).
- **Narrowing the validity hash is DEFERRED.** Every `ci.yml` edit resets every recording, but hashing only
  `check-plan-code.py` lifts usable sets just from 101 to 103 of 113 (INFERRED, same script), and it needs a
  proof of which workflow edits cannot change a suite's reads, which only the built job can give.

**Git-only spawners are no longer a later step.** 13 targets spawn only `git`; 1,681 of `batch-ci`'s git calls
ran in tmp fixtures (MEASURED). strace traces those children, and §2's `.git` rule drops git's reads of its own
metadata, so such a target is traceable in v1. The separate proof per spawn that the old Q2 asked about is not
needed (Q2 superseded, §7).

## 6. How backlog #560 reuses the recording

Backlog #560 caches each MUTANT's verdict across runs. It can reuse this spec's INFRASTRUCTURE: the strace
recorder and its path normaliser, the blob-hashed record format, the recording job, the cache key and the resolve
job. It cannot reuse the read sets themselves: its row requires everything THAT MUTANT RUN read, and a mutant can
open, spawn or probe what its control did not. So backlog #560 must record per mutant execution, with the
mutation's identity and the environment in its key. This spec does not claim more. INFERRED (the spike's own
audit-hook scorer, so a LOWER bound under strace): 40 of 90 targets would be reusable at the strict rule for
PR #545, before any per-mutant recording narrows it. The owner agreed (2026-11-09) that backlog #560 is the speed
lane's next big item and that backlog #534 retires when it lands.

## 7. The owner's decisions (2026-11-09)

All six questions were answered at 10:33 ("I agree all your recommendations", recorded in
`docs/explainers/questions.md`), and the recorder at 10:40 (selection card, answer A). The goal name
`dev-speed-first` was accepted at 10:33. **No question is open for the owner.**

| # | Question | Decision (owner, 2026-11-09) |
|---|---|---|
| Q1 | Which rule picks a traceable target for an added or deleted path, given that an existence check may be its only dependency? | **B** (10:33): record failed opens and stat/access probes, and keep a literal-name test (path, file name, import spelling); directory quotes dropped. Falls back to **A** if the probes add more than 5 picks on PR #543's diff (§2). Since 10:40 strace records the probes natively; no Python stat/access wrapper |
| Q2 | Should git-only spawns in tmp fixtures count as traceable? | 10:33: not in v1. **SUPERSEDED at 10:40**: strace traces every child, so they are traced in v1 (§5) |
| Q3 | When a target cannot be traced, today's naming rule or always pick it? | **Today's rule** (10:33). Since 10:40 it applies only where tracing FAILS for a suite (strace unavailable, ptrace denied, an incomplete trace), or to spawners under the audit-hook fallback (§2, §3) |
| Q4 | Shadow mode first? | **Yes, for 20 COMPLETE PRs** (10:33; §8.6: an incomplete comparison is inconclusive and does not count). Switch only if no would-skip target's verdicts differ between the PR's own sweep and its base's full sweep (§8.1). 0 in 20 bounds the per-PR miss rate below 14% (95%), ASSUMING the 20 are consecutive (not chosen), independent, and each has at least one would-skip target. Shadow mode also MEASURES the real saving, the fallback rate and Q1's probe count, which §5 cannot. Reaching 20 was INFERRED at about 48 merged PRs, roughly 6 days, from audit-hook-era figures (half of commits run ALL, about 89% of the rest get a usable set, §5); a slower strace job lowers that share, so it may take longer |
| Q5 | Accept §4's bound, with master's full sweep as the catch and §8.1 as the detector, and that a harness change resets the saving until the next recording lands? | **Accepted** (10:33). Revisit on the first §8.1 event |
| Q6 | Ship before backlog #560, as its first slice, or inside it? | **Before** (10:33). It builds the infrastructure backlog #560 extends with per-mutant recording (§6) |
| — | The recorder | **`strace -f`** in the `record-reads` job, on each master push, on Linux (10:40, card answer A). Build step 1 proves it on a GitHub-hosted runner, else the audit-hook recorder (§2) |

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
2. **The selection is not the exact one.** A committed read-set fixture built from the spike's sets (spawners
   marked untraced) plus PR #545's diff selects EXACTLY the 33 spawners named by today's rule plus
   `check-canonical-source`, `check-dashboard-entry` and `check-features`, each with its reason. Also cased: a
   traced spawner whose child read a changed path is picked, and one whose children read none is not; a traceable
   non-reader with no mandatory reason is not picked; an own-source and an own-manifest change pick their target
   with no read set; a FULL rule still runs ALL.
3. **A fail-closed rule does not fire.** Each §3 condition is a self-test case with an ADJACENT negative: an
   incomplete trace for each reason (strace missing, ptrace denied, an unparseable log, an unresolved relative
   path); under the audit-hook recorder, a `Popen`, an `os.fork` and an `os.system` spawner; a missing, red,
   short-count, stale (read or probed path modified), wrong-key, wrong-recorder and unvalidated set; a path added
   over R..BASE under a listed directory PICKS by 3(b), with an addition under an unlisted one as the negative;
   an addition over R..BASE that switches on a dependency (Codex's r1 reproduction); an unparseable cache or diff;
   a MODIFIED path in `probed` only, by size and by executable bit (r2 Codex F1), with an unprobed modification as
   the negative. Each one's mutation (dropping it) must go red.
4. **A path is normalised wrongly.** Cased against a recorded strace log: a relative open after a `chdir`, a
   relative open in a child that inherited its parent's cwd, an `openat` through a directory descriptor, a
   `/proc/self/cwd` path, and a `..` path each resolve to their staged-tree name; a read inside a temp
   repository's `.git` does not count, while the same git process's read of a working-tree file under a staged
   root does.
5. **A partial or wrong read set is saved or used.** `readsets.json` is saved by a recording job that was
   cancelled or timed out, with a target missing or doubled, or from a `batch/**` push or a PR. Or a read set is
   kept whose recording count differs from its plain control's under any seed. Or a shard runs a selection other
   than `sweep-select`'s output. Cased: a recording job beside a sweep that is red by a survivor SAVES; a
   cancelled recording job does not; a red plain control refuses only its own target.
6. **A missing comparison counts as a clean one.** A shadow PR counts toward Q4's 20 only when, for EVERY
   would-skip target, the PR's sweep at its final push and the base's full sweep each gave a verdict per mutant.
   A cancelled run, a missing artifact or a CANNOT RUN control on either side makes it INCONCLUSIVE, logged,
   never a pass; a control failed on one side only is a differing verdict. **Evaluated (r3 F5)** only after BOTH
   sweeps finished, by the next scheduled run, over PRs merged since the last one; until then PENDING, counted
   neither way. A base with a cancelled or timed-out shard is INCONCLUSIVE; a red base with per-mutant verdicts
   is comparable. A PR with no usable read set has no would-skip target and is not a sample. Cased: a cancelled
   PR run, a missing base artifact and a red control give INCONCLUSIVE; a pending PR is not counted.
