Reviewed head: 93c31634425228ae3762ee864d2ee21184049cf9

# agent-watchdog — round 3, Claude half (PR #596, backlog #657)

Reviewed: the r2 fold `93c31634` (`git show 93c31634`) and `scripts/agent-watchdog.py` as it stands at that head,
adversarially. The brief was to refute the redesign: activity is ANY change in a fingerprint over
`(kind, name, mtime_ns, size)`; elapsed time is `time.monotonic`; `.git` is opened `O_NONBLOCK` and judged by
`fstat`; any `OSError`/`ValueError` observing one builder is CANNOT RUN for that builder only.

Self-test, run in this worktree: `73/73 self-test cases passed`.

Every mutation below was run on a COPY of `scripts/` in the session scratchpad, never in the worktree.

## Findings

### R3m1 — MINOR — the entry's NAME is in the fingerprint but no case pins it (a rename is an unchecked claim) — fix_induced: yes

`scripts/agent-watchdog.py:169-170` (`_entry`), claim at `scripts/agent-watchdog.py:22` (*"A write, a delete, a
rename, … each alter it"*).

Mutation `return (kind, name, st.st_mtime_ns, st.st_size)` → `return (kind, "", st.st_mtime_ns, st.st_size)`:
**`73/73 self-test cases passed` — survives.** The fold added sibling mutations for size and time left out of the
entry, and none for the name.

Concrete failing input, run against both the real module and the mutant on a temp worktree: rename `src/a.py` →
`src/b.py` and put `src/`'s time back (the same staging the fold's own *"a DELETION at minute 4 … even with its
directory's time put back"* case uses). Real: `rename seen: True`. Mutant: `rename seen: False` — the builder would
be woken at minute 10 instead of 14.

Real-world weight is low: an actual rename always moves the parent directory's time, which is in the fingerprint
(the *"a directory's own time counts"* case does kill the root-dropped mutation). It is a gap in the fold's own
evidence for a property its docstring names. Fix: a case *"a RENAME at minute 4 with its directory's time put back
is activity"* plus the mutation above in the manifest.

fix_induced: **yes** — the fingerprint, the rename claim and its mutation set are all introduced by the r2 fold, in
the `quiet-window` component. It is a coverage gap, not a behaviour defect; the coordinator should weigh whether a
missing mutation counts toward the thrashing condition.

### R3m2 — MINOR — `lstat` in the walk is unpinned; `stat` there turns a symlink loop into CANNOT RUN — fix_induced: no

`scripts/agent-watchdog.py:200` (`entries.append(_entry("tree", path, os.lstat(path)))`).

Mutation `os.lstat(path)` → `os.stat(path)`: **`73/73 self-test cases passed` — survives.**

Concrete failing input: a symlink loop `src/loop -> loop` in the worktree (or any dangling symlink). Real:
`symlink loop: observed`. Mutant: `CANNOT RUN cannot read …/wt/src/loop ([Errno 62] Too many levels of symbolic
links …)` — which ends the watchdog (exit 2) for a builder that is working. A dangling symlink under the mutant is
silently skipped instead (`FileNotFoundError` → `continue`), so its creation/removal is seen only through the
parent directory's time. The r1 suite has a symlink-loop case, but only for the git `index`, not for a worktree
entry. Fix: a case with a looping and a dangling symlink inside the worktree, each observed without error and each
an entry.

fix_induced: **no** — `os.lstat` in the walk predates the fold (`git show b61d0e5a:scripts/agent-watchdog.py`,
line 171).

### R3m3 — MINOR — the re-arm command is not shell-quoted — fix_induced: no

`scripts/agent-watchdog.py:230-233` (`report`, the `rest` line joins `w.spec()` with spaces).

Concrete input: `report(0, 1800, {"a": 1800}, {"b": 60}, {}, [Watch("a", "/tmp/x"), Watch("b", "/Users/me/My
Worktrees/b657", "/Users/me/t.jsonl")])` prints
`python3 scripts/agent-watchdog.py 30 b=/Users/me/My Worktrees/b657:/Users/me/t.jsonl`. Pasted, that splits into
two arguments and is refused (`'Worktrees/b657:…' is not name=worktree[:transcript]`) — loud, so not silent, but the
printed command the orchestrator is told to run does not work. Fix: `shlex.quote(w.spec())`, with a case using a
path holding a space.

fix_induced: **no** — the re-arm line predates both folds.

## Attacks that did NOT land (recorded so the next round need not repeat them)

- **Editor rename-over with the same `mtime_ns` and size.** A rename moves the parent directory's time, and every
  directory (root included) is an entry; the *directory's own time* and *root's own time* cases kill the mutation
  that drops directory entries (`71/73` under it). Not seen only if the editor also restores the directory's time —
  inside the stated BOUND.
- **git operations that touch only objects/refs.** `commit`, `reset`, `checkout`, `add`, `stash` each move `HEAD`,
  `index` or the per-worktree `logs/HEAD`. `push`/`fetch` touch only the common directory, but each is one call,
  bounded by the 270 s floor.
- **Cost / symlinks.** `os.walk` defaults to `followlinks=False`; this worktree's `node_modules` is a symlink
  (`node_modules -> ../../../node_modules`), listed in `dirs` and pruned by name in any case. Measured with the
  real `observe` + `fingerprint`: this worktree `5542 entries 0.06 s`; the main checkout (which the docstring says
  not to watch) `28032 entries 0.66 s`. Negligible against a 60 s poll.
- **False activity that keeps a dead builder active.** The per-turn hook files in this worktree's `.claude/`
  (`ci-unwatched.log`, `closing-table-warnings.log`, `banner-turn-state/`) are written relative to the hook's own
  `REPO_ROOT` (`.claude/hooks/block-idle-stop.sh:49`), i.e. by sessions whose project dir IS this worktree — the
  builder's own (or a reviewer's, which the BOUNDS already name). No writer that runs between turns was found. One
  INFO, not a finding: a `git status` the orchestrator runs in a builder's worktree can rewrite `index` (measured:
  after a `touch`, `git status` moved the index time from `1794829015` to `1794829154.58`), restarting the window
  once per peek after a change; it does not repeat on an unchanged tree. Inside "ANYTHING writing in the worktree
  counts"; worth one clause in BOUNDS.
- **A swallowed CANNOT RUN.** `main` catches `CannotRun`, `OSError` and `ValueError` per builder; `_walk_error`
  and the walk's `lstat` skip only `FileNotFoundError`. The `os.walk` top vanishing between `isdir` and the walk
  yields an empty observation (a change), and the next poll's `isdir` reports CANNOT RUN — not silent.
- **Blocking opens.** The only `open` in the observation is the `O_NONBLOCK` one on `.git`; everything else is
  `stat`/`lstat`/`scandir`. Nothing else can block on a FIFO.
- **Ambient passes.** The wall-clock-step case drives two clocks that start 4 billion apart and steps only the wall
  one; the FIFO-after-check case substitutes the path checks, so it fails for any check-then-open implementation.
- **INFO:** `encode("utf-8", "backslashreplace")` → `encode("utf-8")` in `fingerprint` survives (`73/73`). Only
  observable with a non-UTF-8 filename (not creatable on APFS); under the mutant it raises `UnicodeEncodeError`, a
  `ValueError`, so it would surface as CANNOT RUN, not silence.

## Severity and fix-induced summary

| id | severity | fix_induced | component |
|---|---|---|---|
| R3m1 | MINOR | yes (coverage gap in the fold's own claim) | quiet-window |
| R3m2 | MINOR | no | quiet-window |
| R3m3 | MINOR | no | report |

No BLOCKER, no MAJOR. The redesign holds against every behavioural attack tried; what remains is two unpinned
properties and one unquoted command line, all fixable in one small fold or filed.

VERDICT: CONVERGED
