> **Source:** GitHub Actions run **42893595762** (workflow `strace-measure`, attempt 1, head `be0f552f`, PR #557),
> six shards, merged by `python3 scripts/strace-measure.py --merge … --jobs …` into
> [`2026-11-10-strace-on-runner.json`](2026-11-10-strace-on-runner.json). Every figure below is from that run unless it
> says otherwise; each is marked **MEASURED** (read from the JSON or the run's artifacts) or **INFERRED**.

# Backlog #586, slice 1: strace on a GitHub-hosted runner

Plan: `docs/superpowers/plans/2026-11-09-observed-reach-selection.md` → Slice 1, Task 1.2. Spec §2 ("prove the
recorder can run"). Each of the 92 manifest targets ran its `--self-test` twice per seed (plain, then under
`strace -f -yy`), seeds `PYTHONHASHSEED` = 0 and 1109, each run in a fresh `stage_tree` copy with a fresh `CHILD_HOME`.

## The decision gate: strace is USABLE — slices 2-3 stand, slice 2F is NOT taken

- **MEASURED (run 42893595762):** the ptrace probe step (`strace -f -o /tmp/p.log git --version`, then an `execve` line
  found in the log) succeeded on all 6 shards; strace was already installed on the image.
- **MEASURED (run 42893595762):** strace wrote nothing to stderr in any traced run (`strace_stderr` is empty), and the
  driver left no line unparsed (`unparsed_line_samples` is empty).

## The constants the later slices pin

| constant | value | run | |
|---|---|---|---|
| `STRACE_VERSION` (the `strace -V` first line) | `strace -- version 6.19` | 42893595762 | MEASURED |
| image | `ubuntu26` `20261101.186.1`, kernel `7.0.0-1019-azure`, node `v22.23.4`, `Python 3.12.16` | 42893595762 | MEASURED |
| `RECORD_SEEDS` | `0,1109` (slice 4 reuses them verbatim) | 42893595762 | MEASURED |
| targets | 92, shards present 6 of 6 | 42893595762 | MEASURED |
| `-yy` decorates `AT_FDCWD` | **yes** — in all 92 targets (e.g. `openat(AT_FDCWD</t>, …)`) | 42893595762 | MEASURED |
| `TRACE_FACTOR` | **20** — the largest traced/plain wall-clock ratio over spawner targets is 19.94 (`scripts/batch-ci.py`, seed 1109: 3.26 s plain, 64.99 s traced), rounded up | 42893595762 | MEASURED |
| largest ratio over ALL targets | 19.94 (the same run; the largest non-spawner ratio is 7.23) | 42893595762 | MEASURED |
| spawner targets (forked at least once) | 48 of 92 | 42893595762 | MEASURED |
| targets whose traced and plain case counts differ | **none** | 42893595762 | MEASURED |
| timeouts (limit `SUITE_TIMEOUT` × 10 = 1,200 s) | none | 42893595762 | MEASURED |

### `MEASURED_SYSCALLS` — the union, 118 names, with the number of targets (of 92) that made each (run 42893595762, MEASURED)

All 92: `access`, `arch_prctl`, `brk`, `close`, `execve`, `exit_group`, `fcntl`, `fstat`, `futex`, `getcwd`, `getdents64`, `getegid`, `geteuid`, `getgid`, `getpid`, `getrandom`, `gettid`, `getuid`, `ioctl`, `lseek`, `mkdir`, `mmap`, `mprotect`, `munmap`, `newfstatat`, `openat`, `pread64`, `prlimit64`, `read`, `readlink`, `rmdir`, `rseq`, `rt_sigaction`, `rt_sigprocmask`, `set_robust_list`, `set_tid_address`, `unlink`, `unlinkat`, `write`

Fewer than 92: `alarm` 3, `capget` 4, `chdir` 41, `chmod` 41, `clock_nanosleep` 17, `clone` 36, `clone3` 19, `close_range` 48, `connect` 17, `copy_file_range` 1, `dup` 28, `dup2` 48, `epoll_create1` 65, `epoll_ctl` 7, `epoll_pwait` 6, `epoll_pwait2` 1, `epoll_wait` 1, `eventfd2` 6, `exit` 18, `faccessat2` 1, `fadvise64` 11, `flock` 4, `fstatfs` 1, `fsync` 5, `ftruncate` 1, `getgroups` 1, `getitimer` 1, `getpeername` 2, `getpgrp` 17, `getppid` 25, `getresgid` 15, `getresuid` 15, `getsockname` 1, `io_uring_enter` 4, `io_uring_setup` 4, `kill` 11, `link` 29, `linkat` 2, `listxattr` 3, `madvise` 19, `mkdirat` 2, `mknodat` 9, `mremap` 54, `nanosleep` 2, `pidfd_open` 1, `pipe2` 48, `poll` 48, `prctl` 6, `pselect6` 7, `readlinkat` 2, `recvfrom` 1, `rename` 31, `renameat` 1, `restart_syscall` 11, `rt_sigreturn` 25, `rt_sigsuspend` 2, `sched_getaffinity` 26, `sched_yield` 2, `sendfile` 12, `sendto` 1, `setitimer` 3, `setpgid` 1, `setsid` 30, `sigaltstack` 22, `socket` 17, `socketpair` 1, `splice` 10, `stat` 4, `statfs` 22, `statx` 24, `symlink` 31, `tgkill` 2, `timerfd_create` 1, `timerfd_settime` 1, `uname` 23, `utimensat` 21, `vfork` 48, `wait4` 48, `writev` 5

### `MEASURED_IOCTLS` — the second-argument tokens (run 42893595762, MEASURED)

| ioctl token | targets |
|---|---|
| `BTRFS_IOC_CLONE or FICLONE` | 1 |
| `FIOCLEX` | 92 |
| `FIONBIO` | 5 |
| `TCGETS` | 2 |
| `TCGETS2` | 92 |
| `TIOCGPGRP` | 15 |
| `TIOCGWINSZ` | 60 |

`BTRFS_IOC_CLONE or FICLONE` is ONE token as strace prints it (two names for the same request number).

## Refusal triggers, by target (run 42893595762, MEASURED)

| trigger | targets |
|---|---|
| `io_uring_setup` | `scripts/check-page-links.py`, `scripts/check-paid-caller-arrival.py`, `scripts/explainer-serve.py`, `scripts/page_chrome.py` |
| `unshare`, `setns`, `chroot`, `pivot_root`, the mount family (`mount`, `umount2`, `open_tree`, `move_mount`, `fsopen`, `fsmount`, `fspick`, `mount_setattr`) | **none** |
| a ` (deleted)` fd label | `scripts/batch-ci.py` (12 lines), `scripts/check-stalled-work.py` (97 lines) |
| an unlink/rename/rmdir of a pre-existing path OUTSIDE the copy | **none** |

⚠ **Unresolved removals (MEASURED, run 42893595762): 28 targets** made a removal the driver could not place — e.g.
`scripts/batch-ci.py` 2,833 lines, `scripts/check-merge-ready.py` 951, `scripts/check-plan-leak.py` 702 (all 28 in
the JSON's `unresolved_removals`). The sampled lines are RELATIVE paths, e.g. `unlink(".git/objects/e3/tmp_obj_…") = 0`
(`scripts/check-doc-citations.py`): `unlink`/`rmdir` take no dirfd, so `-yy` gives no label, and the driver does not
track each pid's working directory. **INFERRED:** these are git's own temporary objects inside the suite's fixtures; the
outside-the-copy result above covers only the removals the driver could resolve, so slice 2's parser must follow each
pid's cwd (`chdir` appears in 41 targets, MEASURED) before "no external removal" is a whole claim.

## Not green (run 42893595762, MEASURED) — and why

| target | runs red | cause |
|---|---|---|
| `scripts/check-fixture-git-isolation.py` | plain and traced, both seeds (140/141) | this branch's own driver named the `--self-test` literal, so the isolation guard refused it. Fixed on this branch after the run; not a strace effect (**INFERRED** from the plain run failing the same way) |
| `scripts/check-merge-ready.py` | plain and traced, both seeds (343/400) | this branch's new workflow had an unaccounted `pull_request:` mention; every main() case became CANNOT RUN. Fixed on this branch after the run; not a strace effect (same reasoning) |
| `scripts/regen-pages.py` | **traced only**, both seeds (104/105) | the case "a git that IGNORES SIGTERM is SIGKILLed, then its pipes … are drained for a BOUNDED time" got `('re-raised', False)`. **A real strace effect (INFERRED):** the plain runs pass, and the case is a signal-timing one |

Case COUNTS are identical plain vs traced for all three, so the case-count row above holds.

## Time (run 42893595762, MEASURED)

| shard | job wall s (GitHub) | driver elapsed s |
|---|---|---|
| 1 | 656 | 628.8 |
| 2 | 577 | 551.0 |
| 3 | 540 | 511.4 |
| 4 | 213 | 182.1 |
| 5 | 365 | 337.4 |
| 6 | 445 | 415.6 |
| **sum** | **2,796** | **2,626.3** |
| max | 656 | 628.8 |

Task 4.2's unsharded `record-reads` budget comes from the SUM. ⚠ This run did each target FOUR times (plain and traced,
two seeds); a recorder that only traces does half of that. **INFERRED**, not measured: about 1,300-1,400 s traced
work per full recording.

The ten largest traced/plain ratios (run 42893595762, MEASURED):

| target | seed | spawner | plain s | traced s | ratio |
|---|---|---|---|---|---|
| `scripts/batch-ci.py` | 1109 | yes | 3.26 | 64.99 | 19.94 |
| `scripts/prune-merged-worktrees.py` | 0 | yes | 1.72 | 31.38 | 18.24 |
| `scripts/prune-merged-worktrees.py` | 1109 | yes | 1.7 | 30.64 | 18.02 |
| `scripts/regen-pages.py` | 1109 | yes | 10.13 | 145.23 | 14.34 |
| `scripts/check-doc-citations.py` | 1109 | yes | 0.54 | 7.7 | 14.26 |
| `scripts/check-review-recorded.py` | 1109 | yes | 0.99 | 13.06 | 13.19 |
| `scripts/check-review-recorded.py` | 0 | yes | 1.01 | 12.97 | 12.84 |
| `scripts/gen-work-lines.py` | 1109 | yes | 0.11 | 1.33 | 12.09 |
| `scripts/gen-work-lines.py` | 0 | yes | 0.1 | 1.2 | 12.0 |
| `scripts/check-reference-namespace.py` | 0 | yes | 0.25 | 2.67 | 10.68 |

⚠ **INFERRED:** a ratio over a sub-second plain run (`scripts/gen-work-lines.py`, 0.1 s) is mostly noise.
`scripts/regen-pages.py` traced took 145.23 s, over `SUITE_TIMEOUT` (120 s): a traced run's timeout must be
`SUITE_TIMEOUT × TRACE_FACTOR`, as the plan already says.

## Shapes slice 2's parser meets (fixtures in `scripts/fixtures/strace-lines/`, all from run 42893595762)

- `samples.json` — 400 raw lines, the first per (syscall, shape) over the six shards' `lines.json`; shapes are
  `unfinished`, `resumed`, `= -1 E`, `= N`, `-yy label`, `AT_FDCWD<`, `other`, plus signal, exit and spawn lines.
- `whole-git.log` — `scripts/peer-sites.py`, seed 0 (shard 1): a target whose suite runs `git`, 1,808 lines.
- `whole-threaded.log` — `scripts/ci-durations.py`, seed 1109 (shard 2): a target that starts a thread
  (`clone3` with `CLONE_THREAD`), 2,430 lines.
- Paths: the per-run copy directory is written `/t`, its parent `/w`; nothing else is rewritten. A returned LENGTH
  (`getcwd(...) = 41`) still counts the original path. Each file is headed with the run id.
- **MEASURED** in `whole-git.log`: strace's default `-s 32` truncates the strings inside `execve`'s argv (the raw
  log has `"/tmp/strace-measure-wo1t1cth/sm-"...`, 32 characters; the fixture shows it as `"/t"...`), while path
  arguments and `-yy` labels are printed whole.
