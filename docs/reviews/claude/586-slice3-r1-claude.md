Reviewed head: 42ba603d198def868421a0fdf64b139c7e1db896

# 586-slice3 r1 — Claude half (adversarial)

Scope: `git diff d990caa9..42ba603d`, mainly `scripts/strace_reads.py` (`classify`, `measurement_disagrees`,
`record_from_log`, `merge_seeds`, `cross_run`). Contract: plan Slice 3, spec §2 (cross-run flows, normalisation,
`.git` reads, Record) and §3/Use rule 3. Probes live outside the repository in
`/Users/kujinlee/.claude-tmp/claude-501/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/b387c8e6-9003-42f5-a944-1d4eb1de0c9b/scratchpad/claude586s3/probe{1,2,3,4}.py`,
and each was run with `python3 -I`.

## Findings

### F1 — Major (fail-open): `wrote`/`all_named`/`all_listed` leave out paths the trace NAMED, so `cross_run` misses flows

`scripts/strace_reads.py:record_from_log` (around L955-990) builds every whole-trace set from slice 2's `kept`
list. `kept` is the READ-selection view, and it removes two kinds of path the cross-run rule needs:

1. **Any path with a `.git` component** (`resolve_calls`, `if ".git" not in components(p): kept.append(p)`).
   The spec drops these from *reads* (§2 "`.git` reads, exactly"). For the cross-run check it says
   "`wrote`, and the cross-run check's reads, probes and listings, keep every path" (spec §2, just before the `.git`
   section), and "a written path below any directory T listed refuses T" (spec §2, cross-run paragraph).
2. **The argument path of a successful labelled open** (`_named`: `if opened and call.label ...: continue`). This
   is right for reads, because the kernel's label stands. For cross-run, though, the argument is the path T *named*,
   and it can be a link another target created.

Inputs I ran (probe2.py, probe4.py), in Ctx copy `/t`, or `/tmp/cU` vs `/tmp/cT`:

| # | U's trace | T's trace | `cross_run` got | should be |
|---|---|---|---|---|
| J | `mkdir("/t/docs/sub/.git", 0777) = 0` | `getdents64(3</t/docs/sub>, ...) = 80` | U `complete`, **T `complete`** (U.wrote = `[]`) | T `cross-run flow`: U's write is below a directory T listed |
| I | `mkdir("/t/.git")`, then `openat(..."/t/.git/HEAD", O_WRONLY\|O_CREAT\|O_TRUNC, 0666) = 3</t/.git/HEAD>` | `newfstatat(..."/t/.git"...) = 0`, then `openat(..."/t/.git/HEAD", O_RDONLY) = 3</t/.git/HEAD>` | both `complete`, both sets empty | T refused (it read a path U wrote) |
| B | writes `/dev/shm/r/.git/hooks/pre-commit` | reads the same path | both `complete` | T refused |
| S | `symlink("/tmp/cU/docs/b.md", "/tmp/cU/.home/cur") = 0` (U.wrote = `copy:.home/cur`) | `openat(..."/tmp/cT/.home/cur", O_RDONLY) = 3</tmp/cT/docs/b.md>` (T.all_named = `copy:docs/b.md` only) | **T `complete`** | T refused: it named `copy:.home/cur`, which U wrote. Control: the same pair with U writing a regular file there IS refused (`cross-run flow`) |

Why this matters for selection: in J, T's branch on `docs/sub` now holding `.git` comes from U, and nothing in T's
record names the file U derived it from. In S, which file U links to can depend on a repo file F that T never
names. T is still marked usable, so a change to F skips T.

Exposure today is probably low, since fixtures mostly use per-run temp dirs. But it is the dangerous direction,
it goes against the spec's explicit "keep every path", and it is a CLASS. The Record's whole-trace sets are fed
from a filter built for the staged read sets.

Suggested fix: `resolve_calls` returns the unfiltered named paths too, or `record_from_log` keeps them some other
way. `wrote`/`all_named`/`all_listed` are built from those, `.git` paths and the labelled open's argument
included. Add a case for J, which is the spec's own example shape, plus the S pair with its regular-file control.

### F2 — Minor (fail-open, unwitnessed): a write-class call on an UNDECORATED descriptor records no path

`record_from_log` with `write(5, "x", 1) = 1` → `complete`, `wrote=[]`. `sendfile(5, 3</t/docs/a>, NULL, 10) = 10`
→ `complete`, `wrote=[]` (`_out_side`: `_desc_path("5")` returns `(None, True)`, so `[]`). The module's own rule is
"an operand this function cannot read makes the call a write", and here the path it would write is unknown.
Under that rule this should refuse, not record nothing. `strace -yy` decorates every valid descriptor, and I found
no successful undecorated write-class call in `scripts/fixtures/strace-lines/` (grep over `whole-*.log` and
`samples.json`: only `close_range` / EBADF lines). So this is Minor. A cheap fix: a successful WRITES-class call
whose descriptor operand is a bare number refuses (`unresolved path`).

### Checked and NOT a finding

- **Hardlink of a staged file out of the copy, then a read of the new name** (probe1 C): `docs/a.md` lands in
  `probed`, and rule 3(a) picks on an `M` in `probed`, so the change is selected.
- **Rename of a directory outside the copy into place, with a peer reading below it** (probe1 A): slice 2
  already refuses it (`external path removed` → the peer gets `peer trace incomplete`).
- `/dev/null` with its `<char 1:3>` label: written as `/dev/null` and exempt, so two `O_RDWR` openers stay
  complete (probe2 H).
- `/proc/../dev/shm/d` cannot use the `/proc` exemption: `unresolved ..` (probe2 K).
- Split `<unfinished ...>`/`resumed` calls: openat `O_RDWR`, flags in the resumed half, `mmap` `PROT_WRITE` +
  `MAP_SHARED` and `ioctl FS_IOC_SETFLAGS` are each a write or refused correctly (probe3 N-Q).
- `mmap` with `PROT_READ|PROT_WRITE|PROT_EXEC` + `MAP_SHARED` is a write. `O_ACCMODE` and `O_RDONLY|O_APPEND` are
  reads, which is correct because neither can write data. `utimensat(fd, NULL)` writes the fd's label.
  `copy_file_range` writes operand 2 only. `sendfile` writes operand 0 only.
- `measurement_disagrees` reads the committed JSON (118 syscalls, 7 ioctls, header `strace -- version 6.19`, run
  42893595762). A missing key disagrees.
- `merge_seeds` / `cross_run`: a refusal wins, `seed-dependent reads` keeps its writes known, and the result is
  order-free.

## CHECK / RESULT

| CHECK | RESULT |
|---|---|
| `python3 scripts/strace_reads.py --self-test` | 250/250 passed |
| `python3 scripts/check-plan-code.py --mutate . --only scripts/strace_reads.py` | 184 mutations, 184 killed, 0 survivors, rc=0 (diagnostic slice) |
| Cross-run flow via a `.git`-component write (J, I, B) | **FAIL-OPEN**: T `complete` (F1) |
| Cross-run flow via a peer-created symlink opened by a label (S) | **FAIL-OPEN**: T `complete`; regular-file control refused (F1) |
| Write on an undecorated fd (`write(5,…)`, `sendfile(5,…)`) | records nothing, `complete` (F2, Minor; 0 in the corpus) |
| Hardlink out of the copy, then a read | safe: picked through `probed` |
| openat / mmap / ioctl operands, split calls included | correct |
| Exemptions (`/dev/null` label, `/proc/..`) | correct |
| Measurement pin over the committed JSON | correct |

Findings: 1 Major (F1), 1 Minor (F2).

VERDICT: NOT CONVERGED
