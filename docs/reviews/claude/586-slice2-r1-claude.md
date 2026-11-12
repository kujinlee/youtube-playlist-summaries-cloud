Reviewed head: b0703863d45a4379dadedce7842f7e8f95beee77

# Round 1 — 586-slice2 (PR #565) — Claude half

Subject: `scripts/strace_reads.py` at b0703863 (branch `586-slice2`), plus its wiring. Mandate: REFUTE "the parser
never fails open". Every finding below was RUN through `resolve_log` with a constructed log. The harness is
`$SCRATCH/claude586s2/adv.py` and `adv2.py`, which use the line shapes of the slice-1 fixture `samples.json`.
Common context: `Ctx(copy="/t", cwd0="/t", home="/t/.home", tmpdir="/tmp/run", workspace="/runner/work/x")`.
Thread clone used: a real-shape `clone3({flags=CLONE_VM|CLONE_FS|…|CLONE_THREAD…}) = 2`.

## Gates run

| Check | Result |
|---|---|
| `python3 scripts/strace_reads.py --self-test` | 92/92 passed |
| `check-plan-code.py --mutate . --only scripts/strace_reads.py` | 62 mutations, 62 killed and attributed, 0 survivors (a diagnostic slice) |
| Fixture provenance | the cases build lines with `L()` from `samples.json` (slice-1 run) and the two whole-log fixtures, with substitution. Not invented. |
| Wiring | check-plan-code list, `expected_mutations` (62), `check-selftest-counts` POPULATION, check-fixture-variation and the ci.yml step are all present. The sweep matches 62. `check-selftest-counts.py` gave OK (84 scripts, each count verified by running it) and `check-fixture-variation.py` gave OK |

## Findings

### F1 — Major — a chdir IN FLIGHT is applied only at its completion line, so a CLONE_FS sibling's relative path resolves against the OLD cwd
`scripts/strace_reads.py:499-505` (cwd changes on phase 1 = `c.end`) together with `:477-491` (paths resolve at phase 0
= `c.seq`). The kernel can switch the cwd at any moment between the chdir's entry and its return. A sibling's
path-only call in that window is ambiguous, but the model picks the old cwd silently. The `cwd race` rule covers only
clones (`open_copies`). The AT_FDCWD cross-check covers only `*at` calls. The old x86_64 calls the real logs contain
(`stat`, `access`, `readlink`, `mkdir`, `rmdir`, `unlink`, `rename`, `link`) carry no label. The fixture also has a
real split `chdir(... <unfinished ...>` (pid 2625).
Input:
```
1  clone3({flags=CLONE_VM|CLONE_FS|...|CLONE_THREAD...}) = 2
1  chdir("/t/sub" <unfinished ...>
2  stat("a.py", 0x7ffc351f2080) = 0
1  <... chdir resumed>)              = 0
```
Observed: `[(1,'clone3',[]), (1,'chdir',['/t/sub']), (2,'stat',['/t/a.py'])]`, with no refusal. The read may have been
`/t/sub/a.py`, which is absent from the set. The mirror case also resolves to `/t/a.py` with no refusal: `stat("a.py"
<unfinished ...>`, then a sibling's complete `chdir("/t/sub") = 0`, then the stat resumes.
Fix direction: refuse `cwd race` when a path-only, cwd-relative call in a context overlaps a chdir/fchdir in flight in
the same context. "Overlaps" means the call's [seq, end] interval intersects the chdir's [seq, end].

### F2 — Major — a chdir that STARTS before a copy-clone's entry and ends after its return escapes `cwd race`
`scripts/strace_reads.py:492-505`. `open_copies` is only consulted when the chdir COMPLETES. A chdir whose entry precedes
the clone's entry and whose return follows the clone's return is never inside the counted window. The child's
snapshot, taken at the clone's entry, then holds the old cwd. This is the spec's §2 race ("a chdir/fchdir in the
parent's shared context between that entry and the clone's return"), reached from a chdir in flight across the window.
Input:
```
1  clone3({...CLONE_FS...CLONE_THREAD...}) = 2
1  chdir("/t/sub" <unfinished ...>
2  clone(child_stack=NULL, flags=CLONE_CHILD_CLEARTID|CLONE_CHILD_SETTID|SIGCHLD, child_tidptr=0x79c7f31b6e50) = 3
1  <... chdir resumed>)              = 0
3  stat("a.py", 0x7ffc351f2080) = 0
```
Observed: `(3,'stat',['/t/a.py'])`, with no refusal. The child could have inherited `/t/sub`.
Fix direction: as in F1, test interval overlap, not completion inside the window.

### F3 — Major — `PROC` misses `/proc/<pid>/task/<tid>/{cwd,root,fd/N}`, so such a path resolves LITERALLY
`scripts/strace_reads.py:331`: `^/proc/[^/]+/(?:fd/[^/]+|cwd|root)`. Spec §2 says "`/proc/*/cwd` or `/proc/*/root` …
a failed or path-only call through one is INCOMPLETE".
Inputs and observed results:
- `1  stat("/proc/self/task/1/cwd/a.py", 0x7ffc351f2080) = 0` gives `['/proc/self/task/1/cwd/a.py']` with no refusal.
- `1  stat("/proc/1/task/1/fd/3/a.py", 0x7ffc351f2080) = 0` gives `['/proc/1/task/1/fd/3/a.py']` with no refusal.
- Control: `/proc/self/cwd/a.py` gives `unresolved /proc path`.

The true read is `/t/a.py`, a copy file, and it is missing. The parse-time `realpath` cannot rescue this: it resolves
against the PARSER's process.
Fix direction: allow `(?:task/[^/]+/)?` after the pid segment. A broader option is any `/proc/` path-only call that is
not a known non-link entry.

### F4 — Major — `renameat2(..., RENAME_EXCHANGE)` moves a runtime link to the SOURCE side, and `_runtime_links` tracks only src→dst
`scripts/strace_reads.py:514-518`. An exchange swaps both names, so the link now lives at the old `src`.
Input (all under `tmpdir`, so the #602 rule allows the rename):
```
1  symlink("/t", "/tmp/run/A") = 0
1  mkdir("/tmp/run/B", 0777) = 0
1  renameat2(AT_FDCWD</t>, "/tmp/run/B", AT_FDCWD</t>, "/tmp/run/A", RENAME_EXCHANGE) = 0
1  stat("/tmp/run/B/a.py", 0x7ffc351f2080) = 0
```
Observed: `(1,'stat',['/tmp/run/B/a.py'])`, with no refusal. The control `stat("/tmp/run/A/a.py")` gives `through a
runtime link`. The true read is `/t/a.py`.
Fix direction: for an exchange, add the dst→src move too, or refuse `RENAME_EXCHANGE` outright.

### F5 — Major — a runtime link created by `link`/`linkat` is not a runtime link
`scripts/strace_reads.py:327` (`LINKS = ("symlink", "symlinkat")`) and `:512-513`.
- (a) A hard link OF a symlink is itself a symlink: `link()` and `linkat` without `AT_SYMLINK_FOLLOW` do not follow.
  Input: `symlink("/t", "/tmp/run/A") = 0`, then `link("/tmp/run/A", "/tmp/run/A2") = 0`, then
  `stat("/tmp/run/A2/a.py", …) = 0`. Observed: `['/tmp/run/A2/a.py']`, with no refusal.
- (b) `linkat(..., AT_SYMLINK_FOLLOW)` through a runtime link makes a hard link to the COPY FILE. A later open's label
  names only the alias. Input: `symlink("/t/a.py", "/tmp/run/L") = 0`, then
  `linkat(AT_FDCWD</t>, "/tmp/run/L", AT_FDCWD</t>, "/tmp/run/H", AT_SYMLINK_FOLLOW) = 0`, then
  `openat(AT_FDCWD</t>, "/tmp/run/H", O_RDONLY|O_CLOEXEC) = 3</tmp/run/H>`, then `read(3</tmp/run/H>, …)`. Observed:
  every path is `/tmp/run/L` or `/tmp/run/H`, with no refusal. `/t/a.py`, the bytes actually read, never appears.

The linkat source is final-component NOFOLLOW (`NOFOLLOW_FINAL` contains `linkat`), so the `AT_SYMLINK_FOLLOW` case is
not refused either.
Fix direction: treat a successful link/linkat whose source is a runtime link (or any link with `AT_SYMLINK_FOLLOW`)
as `through a runtime link`. A simpler option is to add the link's new path to `links` whenever its source is one.

### F6 — Major — a call that did not complete (`= ? ERESTARTSYS …`, `= ? <unavailable>`) counts as SUCCESS, so the model applies a chdir the kernel never performed
`scripts/strace_reads.py:499`. Success is tested as `not c.ret.startswith("-1 ")`, and the same test appears at `:289`,
`:379`, `:513`, `:515` and `:560`.
Input:
```
1  chdir("/t/sub") = ? ERESTARTSYS (To be restarted if SA_RESTART is set)
1  stat("a.py", 0x7ffc351f2080) = -1 ENOENT (No such file or directory)
```
Observed: `(1,'stat',['/t/sub/a.py'])`. The cwd is still `/t`, so the true path is `/t/a.py`, which is missing.
`<... chdir resumed>) = ? <unavailable>` behaves the same. For the reads this direction only over-includes. For the
cwd model it misplaces every later relative path.
Fix direction: treat a return that is not a plain integer (or `-1 E…`) as unknown, and refuse when it is a chdir or
fchdir. Simpler: refuse any `= ?` on a cwd-changing call.

### F7 — Minor — a trailing slash makes the kernel FOLLOW a final symlink, but `components()` drops it before `_follows_final`
`scripts/strace_reads.py:336-338` and `:548`. Input: `symlink("/t/sub", "/tmp/run/L") = 0`, then
`lstat("/tmp/run/L/", 0x1) = 0`. Observed: `['/tmp/run/L']`, with no refusal. The lstat stats `/t/sub`, a copy
directory. This is Minor because the target is a directory's metadata and the shape is rare. The fix is cheap: a
path text ending in `/` follows the final component.

### Not findings (checked, refused correctly)
- `[pid N]` prefixes and truncated `"…"...` paths are refused: `log did not parse` and `undecodable path`.
- A relative symlinkat under a dirfd is refused, and so is a rename of a directory holding a link (`through a runtime
  link`).
- `fchdir(3</t/sub>)` moves the cwd correctly.
- A non-canonical `ctx.copy` is refused through the AT_FDCWD cross-check (`cwd model disagrees`).
- `unshare(CLONE_FS)` is not refused here. It is slice 3's `DENIED_SYSCALLS` (plan line 435), so it is out of scope.
  Slice 3 must not drop it.

VERDICT: NOT CONVERGED
