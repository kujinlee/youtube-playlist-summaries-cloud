# Observed-reach selection — a PR sweeps the manifests whose suites READ what it changed

> **Anchor:** `dev-speed-first` — **ADR:** none
> **Goal:** A change gets its verdict as fast as the evidence allows, with mutation coverage identical.

**Status:** ✅ APPROVED by the owner 2026-11-09 (10:33, "I agree all your recommendations"; 10:40, selection card
answer A: record under `strace -f`). Written 2026-11-09 for backlog #586, folded after review rounds 1-3 (round 3
was the cap), then folded with the owner's decisions (§7). The redesign (the dedicated recording job and the
strace recorder) is reviewed as its own stream, `spec-586-redesign`: round 1 (both halves, 20 findings) is
folded here as MECHANISM changes inside the owner's decisions
(`docs/reviews/coordinator/spec-586-redesign-r1-coordinator.md`). Nothing here is built. Every number is marked
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
`check-plan-code.py` and builds its tree as `mutate_delivered` does: `stage_tree`, the redirected `CHILD_HOME`.
**Every push and every scheduled run records under the same two FIXED, distinct `PYTHONHASHSEED`s** (constants
in the recorder; r1 Claude F6: an unseeded push is one draw of a hash-order-dependent read set, and the backlog
#506 comment above `SEED_MAX` measured hash order changing outcomes). For each manifest target, sorted, and each
of the two seeds:
1. **The TRACED run comes FIRST, cold** (r1 Codex F2, Claude F5): in a FRESH copy of the staged tree with a fresh,
   empty `CHILD_HOME`, it runs `[sys.executable, <target>, "--self-test"]` under the recorder, `cwd` that copy,
   `env=mutation_env(copy, seed)` plus the shard environment (below). No plain run of any target has touched that
   copy, so no cache it left can stand in for a read.
2. **The PLAIN control comes second**, exactly as `control_parts` runs it, in ANOTHER fresh copy, and is the count
   reference.

Nothing here feeds a sweep verdict, `control_seconds` or a mutant's timeout. A target gets a read set only when,
FOR BOTH SEEDS, both runs are green by `control_is_green`, their case counts are equal, and the trace is complete
(below). Otherwise it gets an explicit refusal and falls back (§3). The two seeds' read sets are UNITED; a target
whose two sets differ is marked `seed_dependent` in its record, so shadow mode can count them.

**Cross-run flows are refused, not bounded (r1 Claude F5).** A shard runs many suites in one tree with one
`CHILD_HOME`, so suite U can write a file (under the tree, under `.home`, or at a fixed path outside it) that a
later suite T reads; T's own trace then never shows the repo file F that U derived it from. Each run records the
paths it WROTE (below). A target whose `reads` or `probed`, over the WHOLE trace and not only the staged roots,
meet a path any OTHER target's run wrote is INCOMPLETE (`cross-run flow`). Paths under a run's copy are compared
relative to that copy; a fresh temp name never collides. The harness already sets `PYTHONDONTWRITEBYTECODE`, so
bytecode caches are not shared writes. How many targets this rule refuses is UNMEASURED; build step 1 counts it.

**The shard's environment, reproduced (r1 Claude F7).** `child_env` starts from `dict(os.environ)`, so the
recorder builds the child environment a PULL-REQUEST shard's suites see: the `mutation-sweep` step's `env`
keys, supplied to both jobs by one YAML anchor, with a PR shard's values (`EVENT=pull_request`,
`BASE_REF=master`), and the event's `GITHUB_*` values a PR run has (`GITHUB_EVENT_NAME`, `GITHUB_BASE_REF`,
`GITHUB_REF`), set in the child's env by the recorder. What cannot be reproduced (a PR's own refs, the event
payload's content) is §4.4's remaining drift. `GIT_DIR` or `GIT_WORK_TREE` set in that env refuses every target.

**The traced run's timeout (r1 Claude F10)** is `SUITE_TIMEOUT` × `TRACE_FACTOR`, where `TRACE_FACTOR` is the
largest traced/plain wall-clock ratio build step 1 MEASURES over the spawner suites, rounded up. A traced run
that times out is INCOMPLETE (`timeout`); the target takes today's rule. The job logs and stores a tally of
refusals by reason, so shadow mode reports the fallback rate by cause.

**The recorder: `strace -f` (owner, 2026-11-09 10:40).** The suite runs as
`strace -f -yy -o <log> -e trace=%file,%process,getdents64,fchdir,io_uring_setup <argv>`, so every child process
is traced: python, git, node and the shell. **The calls are chosen by strace CLASS, never by a hand-written list
(r1 Codex F3, Claude F4):** `%file` is every syscall that takes a file name (`open`, `openat`, `openat2`, the
`stat` and `access` families, `statx`, `readlink`/`readlinkat`, `execve`/`execveat`, `chdir`, `unlink*`,
`rename*`, `mkdir*`, `symlink*`, `link*`, …) and `%process` every process-lifecycle call (`clone`, `clone3`,
`fork`, `vfork`, `execve`, `exit*`, `unshare`, `setns`). Build step 1 MEASURES what the runner's glibc, Python,
git and Node actually call under it, instead of confirming a guessed list. Owner's Q1 option B — failed opens
plus stat and access probes — is implemented by strace itself, with no Python stat or access wrapper. How each
call counts:
- a SUCCESSFUL open or `execve`: `reads` (an executed script is read by the kernel without a userspace `openat`);
- a FAILED one, and EVERY path any other `%file` call names, present or not, succeeded or not (`readlink`,
  `unlink`, `rename`, `mkdir`, `link` failing with `ENOENT` or `EEXIST` are existence probes): `probed` at least;
- `readlink*` of a path: `reads` of the link itself (its content is the link's target);
- an open with `O_CREAT`, `O_WRONLY`, `O_RDWR` or `O_TRUNC`, and the destination of `rename*`, `link*`,
  `symlink*`, `mkdir*`, and the path of `unlink*`: `wrote`;
- `getdents64` on a descriptor `-yy` names: `listed`.

**What makes a trace INCOMPLETE on sight** (the target takes today's rule, §3): `io_uring_setup` anywhere (an
open submitted through `io_uring` is not a syscall strace sees; §4.2's "rare" becomes a detected refusal);
`unshare`, `setns`, `chroot` or `pivot_root`; a `clone`/`clone3` whose flags the parser cannot read; a strace
`unfinished`/`resumed` pair that does not match; strace's own nonzero exit; the timeout above.

**Normalising strace's paths against the staged tree.** strace logs a path as the process passed it, so the
recorder resolves each one before it counts:
- **a SUCCESSFUL open takes its path from the kernel, not from reconstruction (r1 Claude F2):** `-yy` decorates
  the returned descriptor with the path the kernel resolved at that moment (`= 3</tmp/x/scripts/a.py>`), symlinks
  included, so a read through a link that has since been deleted still resolves to its staged-tree name.
  Reconstruction (the next items) is needed only for failed opens and path-only calls;
- **the working directory, per the `clone` flags (r1 Codex F6, Claude F4):** the cwd starts as the suite's `cwd`.
  A `clone`/`clone3` WITH `CLONE_FS` (every thread glibc creates) SHARES its parent's filesystem context: the
  recorder keeps one cwd per shared context, and a `chdir`/`fchdir` in any member moves it for all. Without
  `CLONE_FS` (`fork`, `vfork`, `posix_spawn`) the child gets a COPY. `unshare(CLONE_FS)` is INCOMPLETE above, not
  modelled. Where `-yy` decorates `AT_FDCWD` with the cwd (INFERRED; build step 1 checks the runner's strace), that
  is the authority and the model is a cross-check whose disagreement is INCOMPLETE;
- an `*at` call against its directory descriptor, which `-yy` prints as a path;
- **`/proc` (r1 Claude F11):** a `/proc/<pid>/fd/N`, `/proc/self/fd/N`, `/proc/*/cwd` or `/proc/*/root` path is
  resolved ONLY through the kernel's decoration of the returned descriptor on the same line; a failed or
  path-only call through one is INCOMPLETE (resolving `fd/N` otherwise needs a descriptor table across `dup`,
  `fcntl` and `O_CLOEXEC`, which the recorder does not keep);
- **symlinks on a failed or path-only call (r1 Claude F2):** `..` is folded lexically, then every component is
  resolved through a LINK TABLE: the links created during the trace (`symlink*`, `link*`, `rename*` are traced),
  and none from staging (below). A link that already existed when the staged copy was made cannot point into
  it, since the copy's temp path did not exist yet; so a path that traverses a link the table cannot resolve, and
  that could name a staged path, is INCOMPLETE;
- **staging provenance (r1 Codex F5):** `stage_tree` copies with `shutil.copytree`'s default, which DEREFERENCES
  symlinks, so a staged regular file can stand for a repo symlink (21 tracked symlinks, MEASURED,
  `git ls-files -s`, mode `120000`). At staging the recorder builds a map from each staged path under a repo
  symlink (a file link, or any path under a directory link) to its repo link path and the repo path it resolves
  to, through every link in the chain. A read or probe of a mapped staged path records ALL of them, so a PR that
  changes only the target, or only the link, picks. A link whose target leaves the staged roots or does not exist
  makes any read through it INCOMPLETE (`unmapped staged path`).

Only paths that resolve under a staged root count as `reads`, `probed` or `listed`; `wrote` keeps every path.

**`.git` reads, exactly (r1 Codex F4, Claude F9).** The staged tree has NO `.git`: `stage_tree` copies
`HARNESS_TREE` only, into a temp directory outside the checkout. Three cases, decided by the path's COMPONENTS,
never by a prefix, so `.github/workflows/ci.yml` and `.githooks/pre-push` are ordinary staged reads that count:
- a path with a `.git` component that is NOT under the real checkout (a fixture's temp repository): dropped;
  git's reads of working-tree files under the staged roots still count;
- a path under the REAL checkout's working tree (`$GITHUB_WORKSPACE`, reached by an absolute path or by
  `git -C "$GITHUB_WORKSPACE"`): mapped to its repo path and counted exactly like a staged path;
- a path under the REAL checkout's `.git`: a MEMBERSHIP dependency, recorded as `git_membership: true` rather
  than as paths. The index alone lists every tracked path WITH its blob id and stat data (`git ls-files -s`), and
  `objects/` holds every tracked file's content, so the dependency is on the whole tracked set: ANY `A`, `M` or
  `D` anywhere (§2 Use, rule 3(d)) picks the target. A target that consults the real repository's metadata
  therefore runs whenever its answer could have changed, which is today's selection or more.

**Each record:**

- `reads`: every path under the staged roots any traced process opened, tracked or not (imports arrive as
  `openat`), each tracked one with its git blob SHA;
- `probed`: every path under the staged roots a traced process tried to open and could not, or passed to a
  `stat`- or `access`-family call, present or not;
- `listed`: the directories under the staged roots any traced process listed (`getdents64`);
- `wrote`: every path any traced process created, wrote, renamed, linked or unlinked, anywhere (for the
  cross-run rule; never a dependency of its own);
- `git_membership`: `true` when a traced process read the real checkout's `.git` (above);
- `trace`: `complete`, or the reason it is not (strace missing, ptrace denied, strace's own exit, a log that did
  not parse, an unresolved path, `io_uring`, an unmodelled `clone`/`unshare`, a `/proc` path, an unmapped staged
  path, a cross-run flow, the timeout);
- `seed_dependent`: whether the two seeds' sets differed;
- `recorder`: `strace`, or `audit-hook` under the fallback below;
- `rc`, the case count, both seeds, the tree's commit, and the VALIDITY KEY (§2 Store).

The staged-path provenance map is not stored per target: it is a function of R's tree, rebuilt by the resolver.

**The build plan's FIRST step: prove the recorder can run (owner, 10:40).** On a GitHub-hosted `ubuntu` runner,
in the job's own setup, install or locate `strace` and trace one suite that spawns `git`, then check that the
log names a file the child opened. The same step MEASURES what the rest of this section left INFERRED: the
syscalls the runner's glibc, Python, git and Node issue under `%file`/`%process`, whether `-yy` decorates
`AT_FDCWD`, whether any suite trips `io_uring_setup` (Node 22's libuv), and `TRACE_FACTOR`. If ptrace is denied or strace is unavailable there, v1 FALLS BACK to the
audit-hook recorder the spike used (`sys.addaudithook` on `open`, `os.listdir`, `os.scandir`, `glob.glob`,
`os.walk` and the process-creation events, with failed opens and wrapped `os.stat` / `os.lstat` / `os.access` as
`probed`). Under that recorder a suite that fires a process-creation event is untraceable and takes today's
naming rule (§3). The rest of this spec is unchanged by the choice of recorder.

**Cost.** UNMEASURED. strace's overhead is expected at 2-5x per traced suite (not measured here), and it lands
only on the recording job, never on a PR or the sweep. The audit-hook spike's 90 suites took 602 s serially on a
laptop (MEASURED); that is a floor for the traced pass, which now also traces every child. The job is timed on
its first CI run, gets its own `timeout-minutes` from that; every recording runs two seeds and two runs per
seed, each in a fresh copy of the staged tree (the copy's cost is UNMEASURED).
A master push already exceeds the account's 20-job limit, so it can queue. It is not a required check;
`mutation-sweep-complete` ignores it. The recorder is a module `check-plan-code.py` imports at top level, so
`harness_files` makes it a harness file: changing it runs ALL, and the harness hash (over the sorted
`harness_files` blobs) covers it.

**Store — the save condition (r3 F4).** The job saves `readsets.json` with `actions/cache/save` only when it
FINISHED: it was neither cancelled nor timed out, and every manifest target appears exactly once, with a read set
or an explicit refusal. A red plain control or an incomplete trace refuses that one target and does not block the
save. Nothing the sweep reports, a survivor or a red shard, can block it, because the job never reads the sweep.
A partial set is never saved. **The VALIDITY KEY (r1 Claude F7)** is the Python version, the harness hash, the
recorder, the strace version (`strace -V`), the Node MINOR version (`node -v`; the workflow pins only `'22'`),
and the runner image (`ImageOS`, `ImageVersion`). The cache key is `readsets-<python>-<harness hash>-<sha>`; the
payload carries its sha and the whole validity key, so a restore is validated by content, not by the key it was
asked for.

**Resolve once, before the matrix.** A new job, `sweep-select`, runs before `mutation-sweep`. It lists the cache
entries with the `readsets-<python>-<harness hash>-` prefix through the Actions API, keeps those whose sha is an
ancestor of BASE, takes the nearest, restores it by exact key and validates the payload: every element of the
validity key must equal `sweep-select`'s own runner's (and the strace version the one the recorder pins), or
every target takes today's rule, logged. A shard on a different image than `sweep-select` cannot re-select
without breaking the one-list stride, so each shard LOGS its own `ImageVersion` beside `sweep-select`'s, and
shadow mode counts a mismatch as a drift event (§4.4). It computes the
selection ONCE and passes the target list (or `full: <why>`) to every shard as a job output. Shards no longer
select, so two shards cannot slice two different lists with one stride. A miss, an API failure or a payload that
does not validate is today's selection for every target, logged; never an error. BASE is the commit the diff
starts from: `git merge-base origin/$BASE_REF HEAD`.

**The diff.** `git diff --name-status -z --no-renames origin/$BASE_REF...HEAD`, so each path carries `A`, `M`
or `D`, and a rename arrives as a `D` plus an `A`. An unparseable list is today's `changed is None`: FULL. Rules
1, 2 and 4 read this list, the PR's own change, as today.

**The comparison set (r1 Codex F1, Claude F1).** Rule 3 reads instead `Δ = (R..BASE) ∪ (BASE..HEAD)`: both
`git diff --name-status -z --no-renames` lists, UNIONED as (path, status) pairs and never netted. A net `R..HEAD`
diff loses two things the union keeps: a path master changed over R..BASE that the PR changes back (net empty,
but BASE's verdict and HEAD's can differ: Codex's `docs/activated` reproduction), and a master add or delete of
a path in `reads` or `probed` (Claude's `docs/flags/strict.on` probe, whose status flip switches on a read the
recording never saw). Either list unparseable is FULL.

**Use.** Today's rules come first and are unchanged, as the code has them:

1. FULL: a harness file, a dependency manifest, a manifest whose target this tree does not load, a staged path
   no target names or quotes, a path named by more than `SHARED_FULL_FRACTION` of targets.
2. Mandatory: a target's own source or own manifest changed picks that target, read set or not.
3. A target with a usable read set (§3) is picked when, over `Δ`: (a) a path, `A`, `M` or `D`, is in its
   `reads` or its `probed`, including a staged path's provenance (a size or mode change seen only through
   `stat`/`access` is an `M`: r2 Codex F1); (b) an `A` or `D` path P lies under a directory in its `listed`,
   meaning: the DEEPEST ancestor of P that existed at R is in `listed` (r1 Claude F8; listing a directory reveals
   exactly its own entries, so a new file inside an existing subdirectory picks only the targets that listed that
   subdirectory, and a new subdirectory picks those that listed its parent); (c) an `A` or `D` path is named
   LITERALLY by the target's source OR by a module it imports, through today's import closure (`_importers`):
   its path, its file name or its import spelling (Q1 B; the directory quotes are dropped; r1 Claude F13); or
   (d) `git_membership` is true and `Δ` is not empty.
4. Any other target is picked by today's naming rule, exactly as now.

**Q1's own fallback (owner, 10:33).** If the probes add more than 5 picks on PR #543's diff, measured in shadow
mode against the same read sets without `probed`'s stat and access entries, rule 3(c) reverts to option A (today's
full naming rule, directory quotes included, for added and deleted paths).

The log line keeps today's form and names the rule: `  check-features <- docs/backlog.md (observed)` or
`… (named: untraced)`, and a parseable `WOULD-SKIP:` / `SKIPPED:` line lists the targets dropped.

**Shadow mode's data and its comparator (r1 Codex F7, Claude F3, F12).** The repository uploads no artifact
today (`grep upload-artifact .github/workflows/*.yml`: no hits, MEASURED) and `--evidence` is retired, so the
build ADDS three things:
- **Per-mutant verdicts.** Every `mutation-sweep` shard, on a PR, a master push and the schedule, writes
  `verdicts.jsonl` (a new `check-plan-code.py` option): one line per mutant run, `{target, mutant, seed,
  verdict}` with the verdict `killed`, `survived`, `cannot-run` or `timeout`, one line per target control
  (`green`/`red`), and a final line `{complete: true|false}` (false when the shard was budget-stopped or its
  controls did not all run). It is uploaded with `actions/upload-artifact` as
  `verdicts-<run_id>-<run_attempt>-<shard index>`, `retention-days: 90`, `if: always()`.
- **The selection.** `sweep-select` uploads `selection-<run_id>-<run_attempt>`, same retention: the PR, HEAD,
  BASE, R, the validity-key check, the picks with their rules, and `WOULD-SKIP` with each target's reason.
- **The comparator.** A new script, `scripts/shadow-compare.py`, run by a new scheduled job, `shadow-compare`
  (daily, read-only token). It is STATELESS over its inputs: each run re-scans every PR merged since the shadow
  start date (a constant in the script), so a comparison PENDING at one run is retried at the next and cannot
  fall out of a time window. It uploads its result as `shadow-ledger-<run_id>` (90 days); a PR already decided in
  the newest ledger keeps that decision, so an input artifact's expiry cannot undo it. An expired input with no
  decided row is INCONCLUSIVE, never clean.

**A MISS, precisely.** For each push of a PR, the comparator pairs that push's PR sweep with the full sweep of
THAT push's own BASE (each push has its own BASE). A miss is a target in that push's `WOULD-SKIP` set for which,
for some mutant and seed both sweeps ran, the verdicts differ, or whose control is green on one side and red on
the other. Misses are taken over EVERY push, not the final one, and LATCH: a miss at any push stops the switch,
even if a later push compares clean. **A seed-flaky difference** (backlog #506's class) is re-run before it
counts: the comparator runs that one mutant 3 times on each tree under the seed each side used; if either tree
gives two different verdicts across its runs, the pair is INCONCLUSIVE (logged as a flake, the PR not counted);
if each tree is stable and they still differ, it is a miss. **A PR counts toward Q4's 20** only when every push
with a would-skip target compared COMPLETE (both verdict files present, both `complete: true`, a verdict for every
would-skip target's mutants on each side) and clean.

## 3. Fail-closed rules: when a target falls back to today's rule

A read set is used only when every condition holds; otherwise rule 4 (naming) applies to that target (owner, Q3,
2026-11-09: today's rule, never always-pick). Under strace this applies only where tracing FAILED for a suite.

| Condition | Why |
|---|---|
| The trace is `complete` (§2): strace ran, ptrace was allowed, the log parsed, every path resolved (kernel-labelled, through the cwd model, the link table or staging provenance), no `io_uring_setup`, no unmodelled `clone`/`unshare`, no unresolved `/proc` path, no cross-run flow, no timeout. Under the audit-hook fallback recorder only: no process-creation event fired | An incomplete trace, or a child the audit hook cannot see (spike caveat 2), has no trustworthy reads |
| A read set exists, its recording green with the plain control's case count under BOTH seeds | A new, failed or recorder-disturbed suite has no trustworthy reads |
| Rule 3 reads `Δ = (R..BASE) ∪ (BASE..HEAD)`, unioned and never netted (§2) | Master can change, add or delete a path in `reads`, `probed` or under `listed` after R, and a PR can undo it; the net `R..HEAD` diff hides both (r1 redesign Codex F1 and Claude F1, each reproduced or constructed). The old row "no path in `reads` or `probed` MODIFIED over R..BASE, else today's rule" is REPLACED: such a path is in `Δ`, so rule 3(a) PICKS the target, which is today's selection or more, where today's rule could pick fewer |
| The payload's validity key (Python, harness hash, recorder, strace version, Node minor, runner image) matches `sweep-select`'s runner | A changed harness, interpreter, recorder, tool or image can read differently |
| `GIT_DIR` and `GIT_WORK_TREE` are unset in the recording's child env | Either one points git at a repository the `.git` rule cannot classify |
| The restore validated (§2 Resolve) | Otherwise every target uses today's rule |

## 4. Why it is sound enough, and what it can miss

**The claim.** If a target's unmutated suite, and every process it started, never opened, probed or listed above
file F, then a change to F cannot change that suite's control result. INFERRED: it is also unlikely to change a
mutant's verdict, because a mutant runs the same suite on the same fixtures.

**What it can miss.** The bound, stated so it can be checked:

1. **A mutant's branch reads a file the control never opened.** UNMEASURED (spike caveat 4).
2. **A dependency with no syscall on the path.** strace sees a probe made in C code or in a child, which the
   audit hook did not. It cannot see a process OUTSIDE the traced tree: a daemon the suite talks to that it did
   not start (a running git `fsmonitor`, a database, Docker). An open submitted through `io_uring` is no longer in
   this bound: `io_uring_setup` makes the trace INCOMPLETE (§2). INFERRED rare here; not measured.
3. **Reads the recorder mis-attributes or misses:** a path the normaliser resolves wrongly despite §2's rules (a
   defect, cased in §8.4), and a read the `.git` rule drops from a fixture's temp repository that a suite
   depended on. A cross-run flow (a suite reading what another suite wrote, spike caveat 8) is no longer in this
   bound: each traced run starts in a fresh copy, and a read of another run's write is INCOMPLETE (§2). Under the
   audit-hook fallback, spike caveats 5 and 7 also apply (a mis-resolved `dir_fd` open, a C extension's own
   `fopen`), and cross-run flows remain bounded, since the hook records no writes by children.
4. **Drift between trees and events.** Reads recorded on master can differ from the PR head's. The recorder
   reproduces a PR shard's environment (§2), but not a PR's own refs or event payload, so a suite that reads
   those can read differently. A shard whose runner image differs from `sweep-select`'s is logged, not re-selected
   (§2 Resolve). Every figure here is from a local run; CI's reads are not yet measured.

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

**How the figures below were scored, against this fold's rules (r1 redesign Claude F8, F13).** The scorer
(`r3f_opts.py`, round-3 coordinator) applies rule 3(c) WITH today's import closure (`_importers`), as the rule now
says. It applies 3(b) with the ANY-ancestor reading (an `A`/`D` path picks a target that listed any of its
ancestors), which picks a superset of the deepest-existing-ancestor rule, so 3(b)'s share of every pick figure is
an UPPER bound. It nets `R..HEAD` and sends a set stale over R..BASE to today's rule, where `Δ` now picks; that
raises picks in the lag columns only (R = BASE has an empty R..BASE). The two changes move the figures in
opposite directions and were NOT re-scored; the net is UNMEASURED, and shadow mode measures it.

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
- Adding a file directly under `scripts/` picks all 43 traceable targets, because the import system lists
  `scripts` for each (MEASURED); correct, since a new module can shadow an import. So one such commit picks 76,
  against 67. Under the deepest-existing-ancestor rule (§2 Use 3(b)) a file added inside an EXISTING subdirectory
  such as `scripts/mutations/` picks only the targets that listed that subdirectory.
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
ran in tmp fixtures (MEASURED). strace traces those children, and §2's `.git` rule drops git's reads of a
fixture's own metadata, so such a target is traceable in v1; one that reads the REAL checkout's `.git` is picked
on any change (§2, rule 3(d)). The separate proof per spawn that the old Q2 asked about is not
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
| Q4 | Shadow mode first? | **Yes, for 20 COMPLETE PRs** (10:33; §8.6: an incomplete comparison is inconclusive and does not count). Switch only if no would-skip target's verdicts differ between the PR's own sweep and its base's full sweep (§8.1). 0 in 20 bounds the per-PR miss rate below 14% (95%), ASSUMING the 20 are consecutive (not chosen), independent, and each has at least one would-skip target. Shadow mode also MEASURES the real saving, the fallback rate and Q1's probe count, which §5 cannot. **Reaching 20 is a PREDICTION, not a measurement** (r1 redesign Claude F12): about 48 merged PRs, roughly 6 days, from audit-hook-era figures (half of commits run ALL, about 89% of the rest get a usable set, §5). It is likely OPTIMISTIC: a slower strace job lowers the usable share; 2 of the last 3 master `push` runs of `ci.yml` concluded `failure` (MEASURED: `42662571317` on `c3ef94d7`, `42634452353` on `4a6f1577`), and a base whose shard was budget-stopped has no complete verdicts, so its PRs are INCONCLUSIVE; and a PR now counts only when EVERY push compared complete (§2, shadow mode). The comparator's ledger reports the count, so the prediction is checked, not assumed. The decision (20 complete PRs) is unchanged |
| Q5 | Accept §4's bound, with master's full sweep as the catch and §8.1 as the detector, and that a harness change resets the saving until the next recording lands? | **Accepted** (10:33). Revisit on the first §8.1 event |
| Q6 | Ship before backlog #560, as its first slice, or inside it? | **Before** (10:33). It builds the infrastructure backlog #560 extends with per-mutant recording (§6) |
| — | The recorder | **`strace -f`** in the `record-reads` job, on each master push, on Linux (10:40, card answer A). Build step 1 proves it on a GitHub-hosted runner, else the audit-hook recorder (§2) |

Recording on master only (never on a PR) is not a question: a PR's unmerged code must not decide another PR's
sweep, by the same argument §2 gives.

## 8. FAILS IF

The built feature FAILS IF any of these is observed.

1. **A would-skip or skipped target's verdict was wrong.** In shadow mode: a target in a PR's `WOULD-SKIP:` line
   for which a MISS (§2, shadow mode: per push, against that push's own base, over every push, after the flake
   re-run) is observed. After the switch: a red master full sweep whose red targets (read from each shard's
   `verdicts-*` artifact, §2) intersect the `SKIPPED:` set of a PR merged since the last green full sweep (the PR
   found from the squash subject's `(#N)`, its selection from that run's `selection-*` artifact). One case stops
   the switch, or reverts it, until §4 is re-examined.
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
   the negative. **From the redesign's round 1:** a path master ADDS over R..BASE that is in `probed` under a
   computed, non-literal name, outside any listed directory, PICKS (Claude F1), with an unprobed addition in the
   same directory as the negative; a path master deletes over R..BASE that is in `reads` PICKS; a PR that deletes
   a file master added over R..BASE under a listed directory PICKS (Codex F1's `docs/activated`), where the net
   `R..HEAD` diff is empty; an `A` inside an existing subdirectory picks a target that listed that subdirectory and
   not one that listed only its parent, and an `A` in a NEW subdirectory picks a target that listed the parent
   (Claude F8); an added path named only by a module the target imports PICKS through the import closure (Claude
   F13); `git_membership` picks on any change, with an empty `Δ` as the negative; a validity-key mismatch for each
   element (strace version, Node minor, runner image) and a set `GIT_DIR` each give today's rule. Each one's
   mutation (dropping it) must go red.
4. **A path is normalised wrongly, or a lost read reads `complete`.** Cased against recorded strace logs: a
   relative open after a `chdir`; a relative open in a `fork` child that copied its parent's cwd; a thread
   (`CLONE_FS`) that `chdir`s followed by ANOTHER thread's relative open and failed probe, which resolve against
   the moved cwd (Codex F6); an `openat` through a directory descriptor; a `..` path; a successful open through a
   temp-dir symlink into the staged tree, logged after the link was deleted, resolving by its `-yy` label to its
   staged-tree name (Claude F2, after `check-review-recorded`'s `_cli` fixture); a failed probe through a link
   created during the trace, resolved through the link table; a staged file that was a repo symlink, recorded as
   the link AND its target (Codex F5: `docs/alias -> value`, a PR modifying only `docs/value` picks); a
   `readlink`, an `execve` of a staged script, an `openat2` and a failed `unlink` each recorded (Codex F3). Each
   of these makes the trace INCOMPLETE: `io_uring_setup`; `unshare(CLONE_FS)`; a failed open through
   `/proc/self/fd/N`; a path through a link the table cannot resolve; a staged link whose target leaves the
   roots; a read of a path another target's run wrote (Claude F5's laundered dependency); the traced timeout. A
   read inside a temp repository's `.git` does not count, while the same git process's read of a working-tree
   file under a staged root does; reads of `.github/workflows/ci.yml` and `.githooks/pre-push` DO count (Claude
   F9); a read of the real checkout's `.git/index` sets `git_membership` (Codex F4's `git -C "$GITHUB_WORKSPACE"
   ls-files docs`). A suite that caches a repo file under `.home` is traced cold: its read set names the repo file
   (Codex F2).
5. **A partial or wrong read set is saved or used.** `readsets.json` is saved by a recording job that was
   cancelled or timed out, with a target missing or doubled, or from a `batch/**` push or a PR. Or a read set is
   kept whose recording count differs from its plain control's under any seed. Or a shard runs a selection other
   than `sweep-select`'s output. Or a target is recorded under only one seed, or from a traced run that was not
   the first run in a fresh copy. Cased: a recording job beside a sweep that is red by a survivor SAVES; a
   cancelled recording job does not; a red plain control refuses only its own target; two seeds whose read sets
   differ give their UNION and `seed_dependent: true` (Claude F6); the child env carries the shard step's keys and
   `EVENT=pull_request` (Claude F7).
6. **A missing comparison counts as a clean one.** A shadow PR counts toward Q4's 20 only when, for EVERY push
   with a would-skip target, the PR's sweep at that push and that push's base's full sweep each gave a verdict per
   mutant (§2, shadow mode). A cancelled run, a missing or expired artifact, a `complete: false` verdict file, a
   flaky re-run or a CANNOT RUN control on either side makes it INCONCLUSIVE, logged, never a pass; a control
   failed on one side only is a differing verdict. **Evaluated** by `shadow-compare` only after BOTH sweeps
   finished; until then PENDING, counted neither way, and re-scanned on every run from the shadow start date, so
   a pending PR is never dropped (Codex F7). A base with a cancelled or timed-out shard is INCONCLUSIVE; a red base with per-mutant verdicts
   is comparable. A PR with no usable read set has no would-skip target and is not a sample. Cased: a cancelled
   PR run, a missing base artifact and a red control give INCONCLUSIVE; a pending PR is not counted, and is
   decided by a LATER run; a miss at a non-final push followed by a clean final push is a MISS (Codex F7); a
   difference that flips on re-run is INCONCLUSIVE, one stable on both trees is a miss (Claude F12).
