# Observed-reach selection — a PR sweeps the manifests whose suites READ what it changed

> **Anchor:** `dev-speed-first` — **ADR:** none
> **Goal:** A change gets its verdict as fast as the evidence allows, with mutation coverage identical.

**Status:** ✅ APPROVED by the owner 2026-11-09 (10:33, "I agree all your recommendations"; 10:40, selection card
answer A: record under `strace -f`). Written 2026-11-09 for backlog #586, folded after review rounds 1-3 (round 3
was the cap), then folded with the owner's decisions (§7). The redesign (the dedicated recording job and the
strace recorder) is reviewed as its own stream, `spec-586-redesign`: round 1 (both halves, 20 findings) is
folded here as MECHANISM changes inside the owner's decisions
(`docs/reviews/coordinator/spec-586-redesign-r1-coordinator.md`). Round 2 (Codex, 7 findings) found every High
inside a rule round 1's fold had ADDED, so its fold SIMPLIFIES: it removes path modelling and widens the refusal
or the pick instead of adding another layer (`docs/reviews/coordinator/spec-586-redesign-r2-coordinator.md`).
Round 3 (Claude, the CAP: 10 findings and 12 places an implementer had to guess) is folded the same way: where a
rule modelled something no suite reaches today, it is REPLACED by a refusal
(`docs/reviews/coordinator/spec-586-redesign-r3-coordinator.md`). One scoped round 4 (Codex) verifies that fold
only, and its non-BLOCKER findings are FILED, not folded. Nothing here is built. Every number is marked
MEASURED (run) or INFERRED (reasoned, not run). **2026-11-09 14:55:** the owner approved design D1 for the
shadow ledger (§7, last row): §2 *The comparator* and *The ledger* carry the diff of
`docs/reviews/architecture-review-2026-11-09-plan-586-ledger-trust.md` §5. The read sets on record were taken by an AUDIT-HOOK spike
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
(below). Otherwise it gets an explicit refusal and falls back (§3). **A target whose two seeds' read sets
differ is INCOMPLETE (`seed-dependent reads`; r3 Claude F2), not unioned:** a read that follows hash order can
land on a THIRD file under a PR sweep's unseeded hash order, and neither seed's set holds it. Two seeds that
AGREE bound nothing about a third (a set iterated to its first present member, both fixed seeds landing on the
same one); that case is §4's bound 5, not a refusal.

**Cross-run flows are refused, not bounded (r1 Claude F5).** A shard runs many suites in one tree with one
`CHILD_HOME`, so suite U can write a file (under the tree, under `.home`, or at a fixed path outside it) that a
later suite T reads; T's own trace then never shows the repo file F that U derived it from. Each run records the
paths it WROTE (below). A target whose `reads` or `probed`, over the WHOLE trace and not only the staged roots,
meet a path any OTHER target's run wrote, or whose `listed` directories (over the whole trace) include an
ANCESTOR of such a path, is INCOMPLETE (`cross-run flow`; r2 Codex F5: U creates `docs/generated/flag`, T lists
`docs/generated` and branches on it, and no path of T's meets U's write). The check does not model which entry a
listing revealed: a written path below any directory T listed refuses T. Paths under a run's copy are compared
relative to that copy; a fresh temp name never collides. `wrote` is taken from each target's traced CONTROL
only; a flow through another target's MUTANT run is §4's bound 3, not this rule's (r3 Claude F3).
**Exempt from the comparison, because they carry no state between runs (r3 Claude F5):** the character devices
`/dev/null`, `/dev/zero`, `/dev/full`, `/dev/random`, `/dev/urandom`, `/dev/tty` and `/dev/pts/*`, and every
path under `/proc` or `/sys`. They are dropped from `wrote` before the comparison: `subprocess.DEVNULL` opens
`/dev/null` `O_RDWR`, and 17 `scripts/*.py` use it (MEASURED, `grep -l DEVNULL`), so without the exemption most
pairs of spawners would refuse each other. `/dev/shm` is NOT exempt (it is tmpfs and holds state), nor is any
other `/dev` path. The harness already sets `PYTHONDONTWRITEBYTECODE`, so
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

**The recorder: `strace -f` (owner, 2026-11-09 10:40).** The suite runs as `strace -f -yy -o <log> <argv>`,
so every child process is traced: python, git, node and the shell. **There is NO `-e trace=` filter (r2 Codex
F2):** round 1 chose calls by strace class, and `unshare` and `setns`, two refusal triggers, are in neither
`%file` nor `%process`, so the filter hid them. strace now logs every syscall and the PARSER classifies each by
name, so no refusal trigger can be filtered away before it is seen. The parser's table puts every syscall name
in one class, and **a name the table does not hold makes the trace INCOMPLETE** (`unclassified syscall`): a gap
in the table costs a target its read set, never a lost read. Build step 1 MEASURES which names the runner's
glibc, Python, git and Node issue, so the table is filled from the measurement, not a guess. **The strace
version is pinned (r3 Claude buildability 10):** the recorder module holds `STRACE_VERSION`, the `strace -V`
line build step 1 measured; a runner whose `strace -V` differs records every target INCOMPLETE (`strace
version`). `sweep-select` runs no strace: it compares the payload's strace version with the `STRACE_VERSION` it
imports from the module. Owner's Q1 option
B — failed opens plus stat and access probes — is implemented by strace itself, with no Python stat or access
wrapper. How each call counts:
- a SUCCESSFUL read-only open or `execve`: `reads` (an executed script is read by the kernel without a userspace
  `openat`);
- EVERY path any call names, present or not, succeeded or not: `probed` at least. This bullet IS the
  definition of `probed` (r3 Claude buildability 2): a failed open, a failed `execve` of an optional script, a
  `chdir`, a `statfs` and an `inotify_add_watch` are all probes;
- `readlink*` of a path: `reads` of the link itself (its content is the link's target);
- **a call is a WRITE unless the table names it READ-ONLY (r2 Codex F6), and the table classifies by syscall
  NAME, never by whether the line carries a path (r3 Claude F4).** Under `-yy` every descriptor argument is
  printed with its path (`close(3</t/scripts/fixture_git.py>)`), so "a descriptor call that names no path"
  named nothing, and read literally every `close` was a write. The READ-ONLY class, closed:
  - path calls: `open`, `openat` and `openat2` without `O_CREAT`, `O_WRONLY`, `O_RDWR`, `O_TRUNC` or
    `O_TMPFILE`; `stat`, `lstat`, `newfstatat`, `statx`, `statfs`; `access`, `faccessat`, `faccessat2`;
    `readlink`, `readlinkat`; `execve`, `execveat`; `chdir`; `getxattr`, `lgetxattr`, `listxattr`, `llistxattr`;
    `inotify_add_watch`;
  - (Round 4: the allowlist is default-deny; see backlog #590.)
  - descriptor calls, whose `-yy` label supplies a path that is NOT written: `read`, `readv`, `pread64`,
    `preadv`, `preadv2`, `lseek`, `close`, `close_range`, `dup`, `dup2`, `dup3`, `fcntl` (every command,
    locks included: a lock is not content), `flock`, `ioctl`, `mmap` (except a `MAP_SHARED` mapping with
    `PROT_WRITE`, which is a write), `munmap`, `fstat`, `fstatfs`, `fgetxattr`, `flistxattr`, `fchdir`,
    `getdents64` (also `listed`), `poll`, `ppoll`, `select`, `pselect6`, the `epoll_*` calls, `fsync`,
    `fdatasync`, `fadvise64`, and the IN side of `sendfile` and `copy_file_range`;
  - process, memory and signal calls that take no file (`clone`, `clone3`, `fork`, `vfork`, `wait4`,
    `exit_group`, `brk`, `futex`, `rt_sig*`, `getpid` and the like), completed from build step 1's measurement.

  Every other call, succeeded or not, is `wrote` for every path it names or its descriptor's label names: a
  writing open, `write`, `writev`, `pwrite64`, `pwritev*`, `ftruncate`, `truncate`, `fallocate`, `chmod`,
  `fchmod*`, `chown`, `fchown*`, `lchown`, `utime*`, `utimensat`, `futimesat`, the `*xattr` setters and
  removers, `mknod*`, `mkdir*`, `rmdir`, `unlink*`, `link*`, `symlink*`, the OUT side of `sendfile`,
  `copy_file_range` and `splice`, and BOTH sides of `rename*`. A metadata change is a write because a suite can
  branch on what `stat` returns;
- `getdents64` on a descriptor `-yy` names: `listed`.

**What makes a trace INCOMPLETE on sight** (the target takes today's rule, §3): a syscall name the parser's
table does not hold; `io_uring_setup` anywhere (an open submitted through `io_uring` is not a syscall strace
sees; §4.2's "rare" becomes a detected refusal); `unshare`, `setns`, `chroot` or `pivot_root`; the mount family, `mount`, `umount2`, `open_tree`, `move_mount`,
`fsopen`, `fsmount`, `fspick` and `mount_setattr`, each of which changes path resolution (r3 Claude
buildability 7); a `clone`/`clone3` whose flags the parser cannot read; a line from a pid no parsed clone
created, or a cwd race (both below); a strace
`unfinished`/`resumed` pair that does not match; strace's own nonzero exit; the timeout above.

**Normalising strace's paths against the staged tree.** strace logs a path as the process passed it, so the
recorder resolves each one before it counts:
- **a SUCCESSFUL open takes its path from the kernel, not from reconstruction (r1 Claude F2):** `-yy` decorates
  the returned descriptor with the path the kernel resolved at that moment (`= 3</tmp/x/scripts/a.py>`), symlinks
  included, so a read through a link that has since been deleted still resolves to its staged-tree name.
  Reconstruction (the next items) is needed only for failed opens and path-only calls. **The label is printed
  after the call returns, so it names the path at THAT moment** (r3 Claude buildability 8). Its two hazards are
  refused, not modelled: a label ending ` (deleted)` at or under the copy is INCOMPLETE (`deleted label`), and
  outside the copy the suffix is stripped and the path kept for the cross-run check; a `rename*` with either side
  at or under the copy is INCOMPLETE (`rename in the copy`), since a label printed concurrently can name either
  side. The parser decodes strace's C escapes (`\"`, `\\`, `\n`, octal `\ooo`, `\xHH`); a path it cannot
  decode is INCOMPLETE (`undecodable path`);
- **the working directory, per the `clone` flags (r1 Codex F6, Claude F4):** the cwd starts as the suite's `cwd`.
  A `clone`/`clone3` WITH `CLONE_FS` (every thread glibc creates) SHARES its parent's filesystem context: the
  recorder keeps one cwd per shared context, and a `chdir`/`fchdir` in any member moves it for all. Without
  `CLONE_FS` (`fork`, `vfork`, `posix_spawn`) the child gets a COPY. `unshare(CLONE_FS)` is INCOMPLETE above, not
  modelled. Where `-yy` decorates `AT_FDCWD` with the cwd (INFERRED; build step 1 checks the runner's strace), that
  is the authority and the model is a cross-check whose disagreement is INCOMPLETE. **Log order (r3 Claude
  buildability 9):** `strace -f -o` interleaves processes, so a child's first lines can precede its parent's
  `clone(...) = PID`. The parser reads the log twice: pass one builds the process tree from every `clone`,
  `clone3`, `fork` and `vfork` return value, resumed lines included; pass two applies the cwd model. A child
  starts with its parent's cwd at the clone's ENTRY line. A `chdir`/`fchdir` in the parent's shared context
  between that entry and the clone's return is INCOMPLETE (`cwd race`), and a pid that no parsed clone created,
  other than the root, is INCOMPLETE (`unknown pid`);
- an `*at` call against its directory descriptor, which `-yy` prints as a path;
- **`/proc` (r1 Claude F11):** a `/proc/<pid>/fd/N`, `/proc/self/fd/N`, `/proc/*/cwd` or `/proc/*/root` path is
  resolved ONLY through the kernel's decoration of the returned descriptor on the same line; a failed or
  path-only call through one is INCOMPLETE (resolving `fd/N` otherwise needs a descriptor table across `dup`,
  `fcntl` and `O_CLOEXEC`, which the recorder does not keep);
- **`..` is NEVER folded (r2 Codex F3).** Folding it lexically drops a link component before the link can be
  followed (`outside/link/../flag` with `link -> staged/docs/nested` is `staged/docs/flag` to the kernel). A
  successful open needs no folding: its `-yy` label is the kernel's own resolution. A FAILED or path-only call
  whose path, after joining with its cwd or directory label, has a `..` component is INCOMPLETE (`unresolved ..`);
- **symlinks on a failed or path-only call: REFUSED, not resolved (r3 Claude F9, replacing round 1's link
  table).** (i) A path any component of which is a link created during the trace (a logged `symlink*`, or a
  `rename*` whose source was one) is INCOMPLETE (`through a runtime link`). (ii) A path lexically OUTSIDE the
  copy is resolved at parse time, before the copy is removed: the parser takes `os.path.realpath` of its longest
  existing prefix and appends the rest; if the result lies at or under the copy's real path, the call went
  through a pre-existing link into the staged tree and is INCOMPLETE (`through a pre-existing link`). Round 1's
  claim that a pre-existing link "cannot point into" the copy was false for a link to an ANCESTOR of the copy
  (`L -> /tmp`, then `L/<copy>/docs/x`). A link changed during the trace is a logged write, so it falls under (i).
  Cost: targets whose FAILED probes pass through a runtime link (`check-review-recorded`'s `_cli` fixture is the
  named one) lose their read set; a SUCCESSFUL open keeps its `-yy` label and needs neither rule;
- **a repo symlink: REFUSED, not mapped (r3 Claude F7, replacing round 1's staging provenance and round 2's
  listing refusal).** `stage_tree` copies with `shutil.copytree`'s default, which DEREFERENCES symlinks, so a
  staged regular file or directory can stand for a repo symlink. A read, probe or listing AT OR UNDER a staged
  path that is a symlink in R's tree is INCOMPLETE (`through a repo link`). The test is by PREFIX, so a path a
  directory link would cover (`docs/alias/new`, absent at staging) is refused too. Cost today: 0 targets. All 21
  tracked symlinks (`git ls-files -s`, mode `120000`) are under `.claude/skills`, which `HARNESS_TREE` does not
  stage (MEASURED). A directory that merely HOLDS a link needs nothing: the link is itself a tracked path, so
  adding or deleting it is an `A` or `D` under that directory.

Only paths that resolve AT OR UNDER a staged root count as `reads`, `probed` or `listed` for rule 3: a root
itself counts (r3 Claude buildability 3: `check-docs.py` lists `.agents/skills`, and 3(b) needs that listing).
`wrote`, and the cross-run check's reads, probes and listings, keep every path.

**`.git` reads, exactly (r1 Codex F4, Claude F9).** The staged tree has NO `.git`: `stage_tree` copies
`HARNESS_TREE` only, into a temp directory outside the checkout. Three cases, decided by the path's COMPONENTS,
never by a prefix, so `.github/workflows/ci.yml` and `.githooks/pre-push` are ordinary staged reads that count:
- a path with a `.git` component that is NOT under the real checkout (a fixture's temp repository): dropped;
  git's reads of working-tree files under the staged roots still count;
- ANY path at or under the real checkout, `$GITHUB_WORKSPACE`, its `.git` included: INCOMPLETE (`real
  checkout`; r3 Claude F8). That is today's rule, the fallback owner Q3 already accepts. No suite reaches it
  today: `grep -l GITHUB_WORKSPACE scripts/*.py` gives 0 hits (MEASURED), and the staged copy lives in a temp
  directory outside the workspace, so git's discovery from the copy cannot reach the checkout. Round 1's mapping
  of the working tree and its `git_membership` flag (old rule 3(d)) are REMOVED: they served no suite.

**Each record:**

- `reads`: every path at or under the staged roots any traced process opened, tracked or not (imports arrive as
  `openat`), each tracked one with its git blob SHA;
- `probed`: every path at or under the staged roots that any traced call NAMED, present or not, succeeded or
  not (the recorder's bullet above is the definition);
- `listed`: the directories at or under the staged roots any traced process listed (`getdents64`);
- `wrote`: every path any traced process named in a call the parser does not class READ-ONLY, anywhere (for the
  cross-run rule; never a dependency of its own);
- `trace`: `complete`, or the reason it is not (strace missing, ptrace denied, strace's own exit or version, a
  log that did not parse, an unclassified syscall, an unresolved path or `..`, `io_uring`, an unmodelled
  `clone`/`unshare`, the mount family, an unknown pid or a cwd race, a `/proc` path, a deleted label, a rename in
  the copy, an undecodable path, a runtime or pre-existing link, a repo link, the real checkout, seed-dependent
  reads, a cross-run flow, the timeout);
- `recorder`: `strace`, or `audit-hook` under the fallback below;
- `rc`, the case count, both seeds, the tree's commit, and the VALIDITY KEY (§2 Store).

The repo-link refusal is decided by the recorder from R's tree at staging; nothing for it is stored per target.

**The build plan's FIRST step: prove the recorder can run (owner, 10:40).** On a GitHub-hosted `ubuntu` runner,
in the job's own setup, install or locate `strace` and trace one suite that spawns `git`, then check that the
log names a file the child opened. The same step MEASURES what the rest of this section left INFERRED: the
syscall names the runner's glibc, Python, git and Node issue (the parser's table), whether `-yy` decorates
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
recorder, the strace version (`STRACE_VERSION`, above), the Node MINOR version (`node -v`; the workflow pins
only `'22'`), the runner image (`ImageOS`, `ImageVersion`), and the git blob ids at R of the dependency manifests
(`DEPENDENCY_MANIFESTS`: `package.json`, `package-lock.json`; r3 Claude F10). A lockfile bump over R..BASE
changes the staged, UNTRACKED `node_modules/typescript`, whose reads are never in `Δ`; `sweep-select` compares
these blob ids with BASE's (`git rev-parse BASE:<path>`), so such a bump sends every target to today's rule. The cache key is `readsets-<python>-<harness hash>-<sha>`; the
payload carries its sha and the whole validity key, so a restore is validated by content, not by the key it was
asked for.

**Resolve once, before the matrix.** A new job, `sweep-select`, runs before `mutation-sweep`. It lists the cache
entries with the `readsets-<python>-<harness hash>-` prefix through the Actions API, keeps those whose sha is an
ancestor of BASE, takes the nearest, restores it by exact key and validates the payload: every element of the
validity key must equal `sweep-select`'s own: its runner's Python, image and `node -v` (it runs the shards'
`setup-node` step), the harness hash, the `STRACE_VERSION` it imports, and BASE's dependency-manifest blob ids.
Otherwise every target takes today's rule, logged. A shard on a different image than `sweep-select` cannot re-select
without breaking the one-list stride, so each shard LOGS its own `ImageVersion` beside `sweep-select`'s, and
shadow mode counts a mismatch as a drift event (§4.4). It computes the
selection ONCE and passes the target list (or `full: <why>`) to every shard as a job output. Shards no longer
select, so two shards cannot slice two different lists with one stride. A miss, an API failure or a payload that
does not validate is today's selection for every target, logged; never an error. BASE is the commit the diff
starts from: `git merge-base origin/$BASE_REF HEAD`.

**The diff.** `git diff --name-status -z --no-renames origin/$BASE_REF...HEAD`, so each path carries `A`, `M`
or `D`, and a rename arrives as a `D` plus an `A`. An unparseable list is today's `changed is None`: FULL. Any
status other than `A`, `M` or `D` (`T` typechange, `U`, `X`, or anything else) makes the list unparseable,
so FULL (r3 Claude buildability 6); that holds for both of `Δ`'s lists below. Rules
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
   `reads` or its `probed` (a size or mode change seen only through `stat`/`access` is an `M`: r2 Codex F1), or
   an `A` or `D` path P has ANY ancestor directory, at any depth, in its `reads` or `probed` (r3 Claude F1: a
   suite that stat-probes `docs/superpowers/archive`, absent at R, sees it appear when a PR adds
   `archive/x.md`, and git reports only the file's `A`; deleting a directory's last file is the mirror case.
   This is 3(b)'s any-ancestor reading applied to probes; its cost is about nil, since the import system
   already lists `scripts` and 3(b) picks those targets); (b) an `A` or `D` path P, or ANY of its ancestor
   directories at any depth, is in its `listed` (r2 Codex F1: deleting a directory's last file removes the
   directory from its PARENT's listing, which git reports only as the file's `D`; the any-ancestor reading needs
   no model of which directories appear or vanish, and is the reading §5 scored); (c) an `A` or `D` path is named
   LITERALLY by the target's source OR by a module it imports, through today's import closure (`_importers`):
   its path, its file name or its import spelling (Q1 B; the directory quotes are dropped; r1 Claude F13).
   Round 1's rule 3(d), `git_membership`, is removed: a read of the real checkout is now INCOMPLETE (§2).
4. Any other target is picked by today's naming rule, exactly as now.

**Q1's own fallback (owner, 10:33).** If the probes add more than 5 picks on PR #543's diff, measured in shadow
mode against the same read sets without `probed`'s stat and access entries, rule 3(c) reverts to option A (today's
full naming rule, directory quotes included, for added and deleted paths).

The log line keeps today's form and names the rule: `  check-features <- docs/backlog.md (observed)` or
`… (named: untraced)`, and a parseable `WOULD-SKIP:` / `SKIPPED:` line lists the targets dropped.

**Shadow mode's data and its comparator (r1 Codex F7, Claude F3, F12).** The repository uploads no artifact
today (`grep upload-artifact .github/workflows/*.yml`: no hits, MEASURED) and `--evidence` is retired, so the
build ADDS four things (the fourth, the committed ledger, since the owner's 14:55 decision, §7):
- **Per-mutant verdicts.** Every `mutation-sweep` shard, on a PR, a master push and the schedule, writes
  `verdicts.jsonl` (a new `check-plan-code.py` option): one line per mutant run, `{target, mutant, seed,
  verdict}` with the verdict `killed`, `survived`, `cannot-run` or `timeout`, one line per target control
  (`green`/`red`), and a final line `{complete: true|false}` (false when the shard was budget-stopped or its
  controls did not all run). It is uploaded with `actions/upload-artifact` as
  `verdicts-<run_id>-<run_attempt>-<shard index>`, `retention-days: 90`, `if: always()`.
- **The selection.** `sweep-select` uploads `selection-<run_id>-<run_attempt>`, same retention: the PR, HEAD,
  BASE, R, the validity-key check, the picks with their rules, and `WOULD-SKIP` with each target's reason.
- **The comparator.** A new script, `scripts/shadow-compare.py`, run by a new scheduled job, `shadow-compare`
  (daily, on the default branch only, read-only token). It is STATELESS over its inputs: each run re-scans every
  PR merged since the ledger's FIRST epoch's start, so a comparison PENDING at one run is retried at the next and
  cannot fall out of a time window, nor out of an epoch a reset closed while it was pending (r4 redesign class
  search). It omits only a PR the ledger holds decided by the identity of what was compared (each push's run and
  its attempt count), never by the PR number alone: a later attempt of a decided push is compared again and can
  only latch (r4 redesign class search). A run's attempt count is FINAL only when a report OBSERVED the run
  completed after GitHub's 30-day re-run limit plus a one-day margin, and the ledger recorded that observation; a
  run's age alone never freezes it (r5 redesign F1, r6 redesign B1). The observation's time is GITHUB's clock, the
  `Date` header of the report's own repository call, so it and the run's creation time come from one clock; the
  report fails, writing nothing, when its runner's clock differs from that header by more than an hour, an alarm and
  not the defence (r7 redesign F1). A recorded run is past the runs listing's reach (about 10 days, backlog #595),
  so its safety is that server-clock comparison against GitHub's documented re-run limit, not a later listing
  (r7 redesign F1). It uploads its result as a REPORT, `shadow-report-<run_id>-<run_attempt>` (90 days),
  and reads no earlier report. Every ATTEMPT of a run is its own report, read whatever the run's current status, so
  re-running a run cannot hide an earlier attempt's miss (r2 redesign Codex C2).
- **The ledger.** A committed file, `docs/shadow-ledger.json`, changed only by a pull request that absorbs
  reports. It records WHICH reports it absorbed, by identity (the run id and attempt), never by a timestamp: one
  report can be published after a later one was absorbed (r1 redesign Codex X1, X2). An absorb takes EVERY trusted
  report the ledger has not absorbed, never a subset (r2 redesign Codex C1: a subset let unrelated absorbs keep the
  ledger fresh while a report contradicting an existing row aged out unread). A miss or a post-switch event only
  tightens, so it is absorbed from any trusted report, except one the ARCHIVED epochs already hold EXACTLY, every
  item of it (for a miss: the PR, each missing push's HEAD and BASE, and each differing target with its mutant
  and seed, or control; for an event: the PR and each target), empty evidence never counting as held (r4 redesign
  B1: matching a miss by the PR alone dropped a new miss on another target): the owner's reset cleared it, and a report written before the
  reset, or a red master that stays red after it, must not re-latch it (r3 redesign F1). Evidence no archived epoch
  holds latches, whenever it was generated, because the owner has not seen it; a clean row and Q1's probe delta only loosen, so they are
  absorbed only from a report written by BASE's code for the current epoch. A decided row is never replaced,
  except by a miss. A guard on every pull request REBUILDS the absorb from the ledger at BASE and EVERY trusted
  report the ledger at BASE has not absorbed, and refuses any other result, so a change that removes or alters a
  decided row, leaves a listed report out, keeps a row a listed miss contradicts, drops a miss or an event, adds
  a row no trusted report holds, or advances the ledger past a report it did not absorb cannot pass. Everything the switch counts lives inside the current EPOCH; moving the epoch requires the owner's
  recorded decision and archives the old epoch, its misses included, verbatim (r1 redesign Codex X3), and the new
  epoch's start is no earlier than the newest report the ledger absorbed and no later than the day of the change
  (r3 redesign F2: a backdated start re-decided what the archive holds). A report attempt that completed without a
  report is absorbed as a no-report entry, so it is listed once, not on every absorb (r3 redesign F4). A row
  counts only under the selector that decided it (r1 redesign Claude F5), and only when its PR merged at or after
  the current epoch's start: a PR merged before a reset can latch the new epoch but never open it (r4 redesign
  class search). A PR decided in the ledger keeps that
  decision, so neither an input's nor a report's expiry can undo it. An expired input with no decided row is
  INCONCLUSIVE, never clean. The switch reads the ledger's current epoch at BASE, as it reads `docs/backlog.md`;
  a report can only CLOSE the switch, never open it, and a trusted report the ledger has not absorbed that holds
  a miss closes it.

**A MISS, precisely.** For each push of a PR, the comparator pairs that push's PR sweep with the full sweep of
THAT push's own BASE (each push has its own BASE). A miss is a target in that push's `WOULD-SKIP` set for which,
for some mutant and seed both sweeps ran, the verdicts differ, or whose control is green on one side and red on
the other. Misses are taken over EVERY push, not the final one, and LATCH: a miss at any push stops the switch,
even if a later push compares clean. **A differing verdict is re-run before it counts** (backlog #506's
class). A PR or master-push sweep is UNSEEDED (`ci.yml` passes `--seeds` only on the schedule), so its original
hash order cannot be replayed (r2 Codex F7). **Where the re-run runs (r3 Claude buildability 12):** in the
`shadow-compare` job itself. For each side it checks out that commit (the repository is public, so the
read-only token suffices), stages a FRESH tree with `stage_tree`, and runs that ONE mutant through a new
`check-plan-code.py` option (`--only <target> --mutant <id> --seeds <s>`) 3 times under EACH of the recorder's
two fixed seeds. It runs in isolation, with none of a shard's earlier leftovers in the tree. **What latches
(r3 Claude F6):** if under ANY replay seed both trees give one stable verdict and those verdicts differ, it is
a MISS and latches. Anything else (a tree whose verdict varies, or trees that agree under both replay seeds) is
an `unreproduced difference`: INCONCLUSIVE, the PR is not counted toward Q4's 20, and the ledger lists every
one with its mutant, so the switch decision sees how many there were. **The remaining bound:** a real miss
that shows only under a hash order neither replay seed produces, or only after another mutant's leftovers in a
shard's shared tree, never latches. It is kept out of the 20 but cannot stop the switch (§4, bounds 3 and 5). **A PR counts toward Q4's 20** only when every push
with a would-skip target compared COMPLETE (both verdict files present, both `complete: true`, a verdict for every
would-skip target's mutants on each side) and clean.

## 3. Fail-closed rules: when a target falls back to today's rule

A read set is used only when every condition holds; otherwise rule 4 (naming) applies to that target (owner, Q3,
2026-11-09: today's rule, never always-pick). Under strace this applies only where tracing FAILED for a suite.

| Condition | Why |
|---|---|
| The trace is `complete` (§2): strace ran at the pinned version, ptrace was allowed, the log parsed, every syscall name classified, every pid's creation parsed, every path decoded and resolved (kernel-labelled or through the cwd model, never by folding `..`, never through a runtime link or a pre-existing link into the copy), no `io_uring_setup`, no unmodelled `clone`/`unshare`, no mount-family call, no unresolved `/proc` path, no deleted label or rename in the copy, nothing at or under a repo symlink or the real checkout, the two seeds' sets equal, no cross-run flow (by path or by a listed ancestor), no timeout. Under the audit-hook fallback recorder only: no process-creation event fired | An incomplete trace, or a child the audit hook cannot see (spike caveat 2), has no trustworthy reads |
| A read set exists, its recording green with the plain control's case count under BOTH seeds | A new, failed or recorder-disturbed suite has no trustworthy reads |
| Rule 3 reads `Δ = (R..BASE) ∪ (BASE..HEAD)`, unioned and never netted (§2) | Master can change, add or delete a path in `reads`, `probed` or under `listed` after R, and a PR can undo it; the net `R..HEAD` diff hides both (r1 redesign Codex F1 and Claude F1, each reproduced or constructed). The old row "no path in `reads` or `probed` MODIFIED over R..BASE, else today's rule" is REPLACED: such a path is in `Δ`, so rule 3(a) PICKS the target, which is today's selection or more, where today's rule could pick fewer |
| The payload's validity key (Python, harness hash, recorder, strace version, Node minor, runner image, the dependency manifests' blob ids) matches `sweep-select`'s | A changed harness, interpreter, recorder, tool, image or `node_modules` can read differently |
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
   depended on. A cross-run flow from another target's CONTROL (spike caveat 8) is not in this bound: each traced
   run starts in a fresh copy, and a read of another control's write, or a listing of a directory above it, is
   INCOMPLETE (§2). **A flow from another target's MUTANT run IS in this bound (r3 Claude F3):** `wrote` is
   recorded from controls only, and within one seed's tree a later run sees what an earlier mutant left there
   (`seed_trees`' docstring in `scripts/check-plan-code.py`: "the unseeded harness's own, pre-existing,
   exposure"). It is the same family as bound 1, and no mechanism is added for it. Under the audit-hook fallback, spike caveats 5 and 7 also apply (a mis-resolved
   `dir_fd` open, a C extension's own `fopen`), and cross-run flows remain bounded, since the hook records no writes by children.
4. **Drift between trees and events.** Reads recorded on master can differ from the PR head's. The recorder
   reproduces a PR shard's environment (§2), but not a PR's own refs or event payload, so a suite that reads
   those can read differently. A shard whose runner image differs from `sweep-select`'s is logged, not re-selected
   (§2 Resolve). Every figure here is from a local run; CI's reads are not yet measured.
5. **A hash order neither fixed seed produces (r3 Claude F2, F6).** A target whose two seeds' sets differ is
   refused (§2), but two seeds that AGREE bound nothing about a third: a suite that iterates a set until its
   first present member can read a different file under a PR sweep's unseeded hash order. The harness's own
   comment above `SEED_MAX` measured a seed-dependent outcome at about 1 in 120 seeds. The comparator replays
   under the same two seeds, so such a miss shows as an `unreproduced difference` (§2): INCONCLUSIVE and listed,
   never a latched miss. UNMEASURED how many targets read this way.

6. **Two open holes from round 4, filed as backlog #590 (r4 Codex F1, F2).** (a) A pre-existing external symlink
   unlinked during the trace hides a probe made through it, because the parse-time link test cannot resolve it
   afterwards. (b) `ioctl` is classed read-only, but `FS_IOC_SETFLAGS` and kin modify an inode, so a cross-run
   write goes unseen. Round 4 is past the cap, so they are FILED, not folded. The fix is a change to how events are
   classified (a default-deny allowlist measured from our own suites), not to the approach, and **backlog #590 must
   close before any skip takes effect; shadow mode alone is not enough.**

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
ancestors), which is rule 3(b) since the r2 fold, so 3(b)'s share is scored as the rule now reads. It nets
`R..HEAD` and sends a set stale over R..BASE to today's rule, where `Δ` now picks; that raises picks in the lag
columns only (R = BASE has an empty R..BASE). It does not apply the r2 fold's refusals, and every one of them
can only LOWER the saving: an unclassified syscall, an unlabelled path with `..`, a listing through a repo
directory link, and a cross-run flow now judged by listed ancestors and by every non-read-only call each send a
target to today's rule; so do the r3 fold's refusals (seed-dependent reads, a runtime or pre-existing link, a
deleted label, a rename in the copy, an unknown pid or cwd race, the mount family, a dependency-manifest change
over R..BASE). The r3 fold's one widening of a pick, 3(a)'s any-ancestor reading, is not scored either; it is
INFERRED to add about nil, since a probed ancestor under `scripts` is already a listed one. How many targets they refuse is UNMEASURED; build step 1 counts them by reason. Not
re-scored; shadow mode measures the net.

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
  against 67. The same holds one level down: since the r2 fold, 3(b) picks on ANY listed ancestor, so a file
  added inside `scripts/mutations/` also picks every target that listed `scripts`. Round 1's narrower
  deepest-existing-ancestor rule would have spared those; the r2 fold gives that saving up, because the rule
  needed a model of which directories appear and vanish, and that model was wrong (r2 Codex F1). The size of the
  loss is UNMEASURED; it is already inside the figures below, which were scored with the wider reading.
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
fixture's own metadata, so such a target is traceable in v1; one that reads anything under the REAL checkout is
INCOMPLETE and takes today's rule (§2; 0 such suites today, MEASURED). The separate proof per spawn that the old Q2 asked about is not
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
`dev-speed-first` was accepted at 10:33. The shadow ledger's design (D1) was decided at 14:55 (selection card,
answer A), after the build plan's review armed Phase 6. **No question is open for the owner.**

| # | Question | Decision (owner, 2026-11-09) |
|---|---|---|
| Q1 | Which rule picks a traceable target for an added or deleted path, given that an existence check may be its only dependency? | **B** (10:33): record failed opens and stat/access probes, and keep a literal-name test (path, file name, import spelling); directory quotes dropped. Falls back to **A** if the probes add more than 5 picks on PR #543's diff (§2). Since 10:40 strace records the probes natively; no Python stat/access wrapper |
| Q2 | Should git-only spawns in tmp fixtures count as traceable? | 10:33: not in v1. **SUPERSEDED at 10:40**: strace traces every child, so they are traced in v1 (§5) |
| Q3 | When a target cannot be traced, today's naming rule or always pick it? | **Today's rule** (10:33). Since 10:40 it applies only where tracing FAILS for a suite (strace unavailable, ptrace denied, an incomplete trace), or to spawners under the audit-hook fallback (§2, §3) |
| Q4 | Shadow mode first? | **Yes, for 20 COMPLETE PRs** (10:33; §8.6: an incomplete comparison is inconclusive and does not count). Switch only if no would-skip target's verdicts differ between the PR's own sweep and its base's full sweep (§8.1). 0 in 20 bounds the per-PR miss rate below 14% (95%), ASSUMING the 20 are consecutive (not chosen), independent, and each has at least one would-skip target. Shadow mode also MEASURES the real saving, the fallback rate and Q1's probe count, which §5 cannot. **Reaching 20 is a PREDICTION, not a measurement** (r1 redesign Claude F12): about 48 merged PRs, roughly 6 days, from audit-hook-era figures (half of commits run ALL, about 89% of the rest get a usable set, §5). It is likely OPTIMISTIC: a slower strace job lowers the usable share; 2 of the last 3 master `push` runs of `ci.yml` concluded `failure` (MEASURED: `42662571317` on `c3ef94d7`, `42634452353` on `4a6f1577`), and a base whose shard was budget-stopped has no complete verdicts, so its PRs are INCONCLUSIVE; and a PR now counts only when EVERY push compared complete (§2, shadow mode). The comparator's ledger reports the count, so the prediction is checked, not assumed. The decision (20 complete PRs) is unchanged |
| Q5 | Accept §4's bound, with master's full sweep as the catch and §8.1 as the detector, and that a harness change resets the saving until the next recording lands? | **Accepted** (10:33). Revisit on the first §8.1 event |
| Q6 | Ship before backlog #560, as its first slice, or inside it? | **Before** (10:33). It builds the infrastructure backlog #560 extends with per-mutant recording (§6) |
| — | The recorder | **`strace -f`** in the `record-reads` job, on each master push, on Linux (10:40, card answer A). Build step 1 proves it on a GitHub-hosted runner, else the audit-hook recorder (§2) |
| — | Where the shadow ledger lives: a committed file read at BASE, or a chain of Actions artifacts? | **A committed ledger** (owner, selection card, 2026-11-09 14:55, answer A "Committed ledger (recommend)"; design D1 of `docs/reviews/architecture-review-2026-11-09-plan-586-ledger-trust.md`, whose §5 diff is applied in §2 *The comparator* and *The ledger*). The comparator writes stateless `shadow-report-<run_id>-<run_attempt>` reports (r3 redesign F7); `docs/shadow-ledger.json` changes only through a guarded absorb PR; an input that can OPEN the switch is read at BASE, and a report can only CLOSE it. Declined: D0, seven more fixes to the artifact chain |
| Q7 | Is the saving WORTH the machinery? (the shadow phase proves the selector misses nothing, never that it saves enough) | **A stop gate** (owner 2026-11-11 15:58, signature line ✍ DECISION 1 of 1, "yes add the gate"). At the end of shadow mode (Q4), over the same 20 complete PRs, the comparator reports the median share of today's selected mutation targets that observed reach would skip. **Under 25%, the feature STOPS:** slices 1-5 stay as built, `record-reads` is switched off, today's selector stays, and slices 6-8 are not built. At 25% or more, Q4's switch rule decides as before. **FAILS IF** the switch happens with no reported median, or with one under 25% |

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
   short-count, wrong-key, wrong-recorder and unvalidated set; a read or probed path MODIFIED over R..BASE that
PICKS by 3(a) rather than falling back (§3 replaced the old stale-set fallback; r3 Claude buildability 11); a path added
   over R..BASE under a listed directory PICKS by 3(b), with an addition under an unlisted one as the negative;
   an addition over R..BASE that switches on a dependency (Codex's r1 reproduction); an unparseable cache or diff;
   a MODIFIED path in `probed` only, by size and by executable bit (r2 Codex F1), with an unprobed modification as
   the negative. **From the redesign's round 1:** a path master ADDS over R..BASE that is in `probed` under a
   computed, non-literal name, outside any listed directory, PICKS (Claude F1), with an unprobed addition in the
   same directory as the negative; a path master deletes over R..BASE that is in `reads` PICKS; a PR that deletes
   a file master added over R..BASE under a listed directory PICKS (Codex F1's `docs/activated`), where the net
   `R..HEAD` diff is empty; an `A` or `D` at any depth below a listed directory picks (Claude F8, any-ancestor since
   the r2 fold), and a `D` of a directory's LAST file picks a target that listed only that directory's
   GRANDPARENT (r2 Codex F1's `docs/sub/only`), with a `D` outside every listed directory as the negative; an added path named only by a module the target imports PICKS through the import closure (Claude
   F13). **From the redesign's round 3:** an `A` of `docs/superpowers/archive/x.md` picks a target that only
   stat-probed the absent `docs/superpowers/archive`, and a `D` of that directory's last file picks a target that
   only probed it (Claude F1), with an `A` under an unprobed sibling directory as the negative; a `T` status in
   either list of `Δ` is FULL. A validity-key mismatch for each element (strace version, Node minor, runner
   image, a `package-lock.json` blob changed over R..BASE) and a set `GIT_DIR` each give today's rule. Each one's
   mutation (dropping it) must go red.
4. **A path is normalised wrongly, or a lost read reads `complete`.** Cased against recorded strace logs: a
   relative open after a `chdir`; a relative open in a `fork` child that copied its parent's cwd; a thread
   (`CLONE_FS`) that `chdir`s followed by ANOTHER thread's relative open and failed probe, which resolve against
   the moved cwd (Codex F6); an `openat` through a directory descriptor; a SUCCESSFUL open of a `..` path resolved by its `-yy`
   label, and a FAILED probe of `outside/link/../flag` with `link -> staged/docs/nested` made INCOMPLETE, never
   folded to `outside/flag` (r2 Codex F3); a successful open through a
   temp-dir symlink into the staged tree, logged after the link was deleted, resolving by its `-yy` label to its
   staged-tree name (Claude F2, after `check-review-recorded`'s `_cli` fixture); a failed probe through a link
   created during the trace, which is INCOMPLETE (r3 Claude F9); a failed probe of `L/<copy>/docs/x` with a
   pre-existing `L -> /tmp`, INCOMPLETE, and a failed probe of an absent `/tmp/other/x` with no link, NOT refused;
   a read under a staged path that was a repo symlink, INCOMPLETE (r3 Claude F7: `docs/alias -> value`); a
   `readlink`, an `execve` of a staged script, an `openat2` and a failed `unlink` each recorded (Codex F3). Each
   of these makes the trace INCOMPLETE: `io_uring_setup`; `unshare(CLONE_FS)`; a failed open through
   `/proc/self/fd/N`; a `mount` or `move_mount`; a line from an unknown pid, and a `chdir` between a clone's entry
   and return; a label ending ` (deleted)` under the copy; a `rename` inside the copy; an undecodable path; two
   seeds whose read sets differ (r3 Claude F2); a strace whose `-V` differs from `STRACE_VERSION`; a read of a
   path another target's run wrote (Claude F5's laundered dependency); a LISTING of a directory
   that is an ancestor of a path another target's run wrote (r2 Codex F5: U creates `docs/generated/flag`, T lists
   `docs/generated`); a listing of a staged directory under a repo directory link (r2 Codex F4: `docs/alias ->
   real/`, a PR adding `docs/real/new`); a syscall name the parser's table does not hold; `unshare` and `setns`
   EXECUTED by a real child under the runner's strace, not a synthetic log line (r2 Codex F2); the traced
   timeout. A `truncate`, a `chmod`, a `utimensat` and BOTH sides of a `rename` each land in `wrote`, so a later
   target that stats the file is refused (r2 Codex F6). A `read`, `close`, `lseek`, `fcntl` and `PROT_READ`
   `mmap` of a staged file are NOT writes, with an `ftruncate` of it as the adjacent positive (r3 Claude F4). Two
   targets that each open `/dev/null` `O_RDWR` do not refuse each other, while a write under `/dev/shm` read by
   a later target does refuse it (r3 Claude F5). A
   read inside a temp repository's `.git` does not count, while the same git process's read of a working-tree
   file under a staged root does; reads of `.github/workflows/ci.yml` and `.githooks/pre-push` DO count (Claude
   F9); a read of the real checkout's `.git/index` (Codex F4's `git -C "$GITHUB_WORKSPACE" ls-files docs`), or of
   any path under `$GITHUB_WORKSPACE`, is INCOMPLETE (r3 Claude F8). A suite that caches a repo file under `.home` is traced cold: its read set names the repo file
   (Codex F2).
5. **A partial or wrong read set is saved or used.** `readsets.json` is saved by a recording job that was
   cancelled or timed out, with a target missing or doubled, or from a `batch/**` push or a PR. Or a read set is
   kept whose recording count differs from its plain control's under any seed. Or a shard runs a selection other
   than `sweep-select`'s output. Or a target is recorded under only one seed, or from a traced run that was not
   the first run in a fresh copy. Cased: a recording job beside a sweep that is red by a survivor SAVES; a
   cancelled recording job does not; a red plain control refuses only its own target; two seeds whose read sets
   differ refuse the target (`seed-dependent reads`; r3 Claude F2, replacing round 1's union); the child env carries the shard step's keys and
   `EVENT=pull_request` (Claude F7).
6. **A missing comparison counts as a clean one.** A shadow PR counts toward Q4's 20 only when, for EVERY push
   with a would-skip target, the PR's sweep at that push and that push's base's full sweep each gave a verdict per
   mutant (§2, shadow mode). A cancelled run, a missing or expired artifact, a `complete: false` verdict file, a
   flaky re-run or a CANNOT RUN control on either side makes it INCONCLUSIVE, logged, never a pass; a control
   failed on one side only is a differing verdict. **Evaluated** by `shadow-compare` only after BOTH sweeps
   finished; until then PENDING, counted neither way, and re-scanned on every run from the ledger's epoch start,
   so a pending PR is never dropped (Codex F7). A base with a cancelled or timed-out shard is INCONCLUSIVE; a red base with per-mutant verdicts
   is comparable. A PR with no usable read set has no would-skip target and is not a sample. Cased: a cancelled
   PR run, a missing base artifact and a red control give INCONCLUSIVE; a pending PR is not counted, and is
   decided by a LATER run; a miss at a non-final push followed by a clean final push is a MISS (Codex F7); a
   difference that flips on re-run is INCONCLUSIVE, one stable on both trees under the same replay seed is a
   miss (Claude F12), and an unseeded difference that does not reproduce under either replay seed is an
   `unreproduced difference`: INCONCLUSIVE, listed in the ledger, never a miss and never clean (r2 Codex F7,
   r3 Claude F6). A difference that reproduces under only ONE of the two replay seeds LATCHES as a miss (r3
   Claude F6), and the re-run happens inside `shadow-compare` on fresh staged trees. **The ledger (§2, owner
   2026-11-09 14:55):** a committed change to `docs/shadow-ledger.json` that removes or alters a decided row,
   lowers a miss count, adds a row no trusted report holds, records a report as absorbed without absorbing its
   misses, absorbs some listed trusted reports while leaving another out, or moves the epoch without the owner's
   recorded decision or without archiving the old epoch verbatim, or to a start before the newest absorbed report,
   or re-latches in the new epoch evidence an archived epoch holds, or holds back evidence the archived epochs do
   not hold exactly (another target, mutant, seed or push of an archived PR, or empty evidence), passes the guard;
   or a report omits a PR whose decided row does not cover a later attempt of its run (a run frozen by its age, with
   no recorded observation of its final attempt count, among them, or one frozen by an observation timed by the
   report runner's clock rather than GitHub's), or a PR pending at a reset;
   or a row whose PR merged before the current epoch's start counts toward opening it; or the switch opens on anything but the ledger's current epoch at BASE (a report, an
   artifact, the PR's own ledger, an archived epoch's rows, a row decided under another selector); or a trusted
   report holding a miss the ledger has not absorbed leaves the switch open, whenever it was published and
   whatever the current status of its run (a rerun in progress included).
