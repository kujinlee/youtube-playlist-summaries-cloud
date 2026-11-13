Reviewed head: 36bb765ee44cae84a6833767f52c742c5f146411

# 586-slice2 — round 3, the Claude half (adversarial)

Subject: `scripts/strace_reads.py` (`git diff origin/master...HEAD`). Mandate: REFUTE convergence, meaning find a log the
parser gets wrong. Every input below was RUN through `resolve_log` with
`Ctx(copy="/t", workspace="/runner/work/x", staged_roots=("scripts",), cwd0="/t", home="/t/.home", tmpdir="/tmp/run")`
(`("app","scripts")` for the `[id]` probes). The probe scripts are outside the repository, in the session scratchpad
`claude586s2/adv3.py`, `adv4.py`, `adv5.py` and `adv6.py`. The round-1 `adv.py` and `adv2.py` were re-run at this head,
and every refusal they produced is unchanged.

Gates at this head: `--self-test` 135/135, rc 0. `check-plan-code.py --mutate . --only scripts/strace_reads.py` rc 0:
83 mutations, 83 killed, 0 survivors.

## Findings

### F1 — Major (FAIL-OPEN) — a rename that moves a cwd's directory leaves the cwd model on the old TEXT

`scripts/strace_reads.py:593-603` (the cwd model in `_named_all`'s event loop). A context's `cwd[k]` changes only on
`CWD_CHANGES` (`chdir`, `fchdir`). In the kernel, a cwd is an inode reference. When `rename` moves that directory (or any
ancestor of it), the process's cwd moves with it. The model keeps the old path text and resolves every later relative
name against a directory that no longer exists at that path.

Input (`adv6.py` CWDMV-A, run):

```
1  mkdir("/tmp/run/w", 0777) = 0
1  chdir("/tmp/run/w") = 0
1  rename("/tmp/run/w", "/tmp/run/v") = 0          # the kernel cwd is now /tmp/run/v
1  getcwd("/tmp/run/v", 4096) = 11
1  symlink("/t/scripts", "/tmp/run/v/L") = 0
1  access("L/new.py", F_OK) = -1 ENOENT (No such file or directory)
```

- **Output:** no refusal. `access` is recorded as `['/tmp/run/w/L/new.py']`.
- **The truth:** the kernel resolved `/tmp/run/v/L/new.py`, followed the runtime link `L`, and probed
  `/t/scripts/new.py`, a path under a staged root.
- **Why nothing catches it:** the recorded path is outside the copy. It is not under the known link `/tmp/run/v/L`. The
  rename closure maps only links that existed under the rename's source, and `L` was created after the rename. So
  `through a runtime link` does not fire, and the probe of `scripts/new.py` is lost.
- **Consequence:** a PR that adds `scripts/new.py` would change this suite's behaviour, yet the suite would be skipped.

The same input with each of these probe calls also passes unrefused, each with a stale `/tmp/run/w/L/...` path:

| Probe | Probe name |
|---|---|
| `stat("L/x.py")` | CWDMV-C |
| `execve("L/tool", ...)` | CWDMV-B |
| `readlink("L/link")` | CWDMV-D |
| an ancestor rename `a → b` with cwd `a/w` | CWDMV-E |
| a forked child inheriting the stale cwd | CWDMV-F |

- **The bound that limits it (also run):** a later call in the same context that carries an `AT_FDCWD</tmp/run/v>` label
  refuses with `cwd model disagrees` (CWDMV-CONTROL). So the hole is open only while that context makes no dirfd-taking
  call. It needs the dirfd-less syscalls (`access`, `stat`, `lstat`, `readlink`, `execve`, `chdir`), which x86_64 strace
  still prints by those names.
- **Why it is still Major:** the detector is a lagging consistency check, not part of the model. A log with no such
  later call fails open.
- **Fix, by class:** a successful rename whose source is at or above any context's current cwd must either rewrite that
  cwd (`dst + cwd[len(src):]`) or refuse with a named reason (for example `cwd moved`). This matches round 1's rule:
  refuse where the model falls short of the kernel. It also applies to a cwd snapshot taken for a pending copying child.

### F2 — Minor (false refusal) — the order-insensitive closure refuses a log the kernel finishes

`scripts/strace_reads.py:634-646`, `_runtime_links`. Input (`adv3.py` R1b, run):

```
symlink("/t", "/tmp/run/x/z/L") = 0
rename("/tmp/run/x", "/tmp/run/y") = 0
rename("/tmp/run/y/z", "/tmp/run/x") = 0
stat("/tmp/run/x/L/a.py", ...) = -1 ENOENT
```

- **Output:** `rename cycle`.
- **The kernel's result:** acyclic, two moves. The link ends at `x/L`.
- **Why it refuses:** the closure ignores order and re-applies `x → y` to `x/L`. That gives `y/L` at pass 3, which is
  more than `len(moves)+1` = 3 passes. R1 (link at `x/z/z/L`) is refused the same way.
- **Safe direction:** the closure over-reports and then refuses. It never under-reports, so the pass bound cannot return
  early with an undersized set.

### F3 — Minor (stall) — the pass bound limits PASSES, not work, and it counts every rename

`scripts/strace_reads.py:640`. The bound is `len(moves) + 1`, and `moves` includes renames that touch no link, such as git's
`index.lock → index`.

Codex's r2 linear cycle plus N unrelated renames (`adv3.py --slow`, run; every run ends `rename cycle`):

| N | time |
|---|---|
| 50 | 0.07 s |
| 100 | 0.53 s |
| 200 | 3.40 s |
| 400 | 27.05 s |

That is roughly cubic. A branching cycle in which every rename succeeds in the kernel:

```
symlink A/L; A → B/1; symlink A/L; A → B/2; B → A
```

plus N unrelated renames (`adv4.py`, run):

| N | time |
|---|---|
| 10 | 0.02 s |
| 16 | 0.17 s |
| 20 | 0.76 s |
| 22 | 1.7 s |
| 24 | 3.7 s |
| 26 | 8.1 s, maxrss 51 MB |

That is exponential, about 2.1× per two renames. The r2 non-termination is therefore bounded but can still stall CI.
It never fails open, because the end state is always a refusal.

- **Possible fix:** bound by the number of moves that ever touch a link, or cap `len(links)`.
- **Not measured:** how many renames a real suite makes (the `whole-git.log` fixture has 0).

### F4 — Minor (false refusal) — an unbalanced `(`, `[` or `{` inside a `-yy` label breaks the scan

`scripts/strace_reads.py:152` (`scan_args`). The scanner pushes on brackets even inside a `<...>` label. Input (`adv3.py`
PAREN, run):

```
openat(AT_FDCWD</t>, "a(b", O_RDONLY) = 3</t/a(b>
read(3</t/a(b>, "x", 1) = 1
```

- **Output:** `log did not parse`. `a[b` and `a{b` give the same result.
- **What still works (run):** balanced names are correct, including Next.js `app/api/html/[id]/route.ts` and
  `app/s/[token]`.
- **Why it is Minor:** `git ls-files` has no path with an unbalanced bracket, and the direction is a refusal.

### Note (no instance) — an interpreter the kernel reads without a syscall

`execve` of a `#!` script, or of an ELF with `PT_INTERP`, makes the kernel open the interpreter internally, with no syscall
for it in the log. If an interpreter lived inside the copy, that read would be invisible. A scan of `git ls-files`
shebangs found only `/usr/bin/env` and `/bin/...`, so there is no instance. The spec does not state this bound, and one
sentence in it would.

## Not findings (probed at this head, held)

- **openat2:**
  - Admitted: `RESOLVE_BENEATH`, `NO_SYMLINKS|NO_MAGICLINKS` and `CACHED`. These only restrict resolution.
  - Refused: `RESOLVE_IN_ROOT`, the numeric `0x10`, and `resolve=` spelled after `mode=`.
  - A mode-only struct through a runtime link is refused.
- **vfork, clone3 and clone:**
  - `vfork` and `clone3{CLONE_VM|CLONE_VFORK}` children get a cwd copy, so a child's chdir does not move the parent.
  - An unreadable clone3 struct gives `unmodelled clone`.
  - `clone(CLONE_VM|CLONE_FS)` without `CLONE_THREAD` shares the cwd.
  - A thread's chdir in flight across a parent's clone3 VFORK gives `cwd race`.
- **Threads and execve:**
  - A thread chdir resumed `= ?` at exit_group gives `unknown return`.
  - A completed thread chdir followed by the thread's exit moves the sibling's cwd correctly.
  - A non-leader `execve` (the `superseded` line) gives `log did not parse`.
  - A relative execve during a thread chdir race gives `cwd race`.
  - A signal line between two halves is fine.
- **/proc non-following calls are admitted correctly:**
  - Calls: `lstat`, `newfstatat NOFOLLOW`, `readlinkat`, `lgetxattr`, `unlinkat`, `utimensat NOFOLLOW`,
    `fchownat NOFOLLOW`, `execveat NOFOLLOW` (ELOOP), a failed `rename`, and `symlink` with a magic target.
  - Following versions and `newfstatat` without the flag are refused.
  - A trailing `/`, `/.` or `//` on `/proc/self/cwd` is refused for both `lstat` and `newfstatat NOFOLLOW`.
  - A symlink to `/proc/self/cwd` that is then followed is refused.
  - `inotify_add_watch ... IN_DONT_FOLLOW` is refused, which is a safe over-refusal.
- **Descriptors and empty paths:**
  - `O_PATH|O_NOFOLLOW` on a runtime link, then `linkat AT_EMPTY_PATH` gives `through a runtime link`.
  - `statx AT_EMPTY_PATH` resolves to the dirfd's label. With an undecorated fd it gives `unresolved path`. With
    `AT_FDCWD` it resolves to the cwd.
  - `fchmodat2 NOFOLLOW` on a runtime link is admitted correctly.
  - `mmap` is covered by the descriptor label.
- **Flags and labels:**
  - A flag name spelled inside path text is not read as a flag.
  - `renameat2` with numeric flags gives `unmodelled flags`.
  - A label containing `>` parses correctly.
  - A string truncated with `"..."...` is handled.
- **Deleted directories:**
  - A deleted dirfd label used in a failed probe records `.../gone (deleted)/a.py`. That is harmless: a lookup in a dead
    directory returns ENOENT whatever the PR tree holds.
  - `fchdir` to a deleted directory gives `deleted label`.
- **Other probes:**
  - A hard link of a copy file read through /tmp: the source is named by `link`, so it lands in `probed` as the spec says.
  - A chdir through a runtime link created later is refused.
- **Left to slice 3:** `chroot`, `pivot_root`, `mount`, `unshare`, `setns`, `name_to_handle_at`/`open_by_handle_at` and
  `io_uring` are slice-3 refusals by spec line 166 and plan lines 435 and 464.
- **Round-1 inputs:** `adv.py` and `adv2.py` were re-run, and all 22 refusals or correct sets are unchanged. One of them,
  G (`unshare(CLONE_FS)`), is still admitted, and that remains slice 3's to refuse.

VERDICT: NOT CONVERGED
