Reviewed head: f3b3e68759d7c87f82639f91488147fc14cb3733

# Round 4 — `prune-merged-worktrees` — Claude half (scoped verification of the r3 fold, past the cap)

Scope: ONLY `git show f3b3e687`, the round-3 fold. That covers `leave_placeholder` (ARCHIVED-WITHOUT-PLACEHOLDER),
the live-HEAD check with the remote branch gone, `registered_at` for BY-PEER, `refused_now` and its 24 h TTL,
`qpath` and the quoted undo, and the new cases and mutations. Context: `docs/reviews/coordinator/prune-merged-worktrees-r3-coordinator.md`.

## The question asked: can this fold lose data, or report success for a worktree that was not archived?

**No BLOCKER found.** I traced each path the fold changes:

- **The success test drops `and not lexists(old)` (F1).** `rc == 0 and isdir(dest)` now means ARCHIVED or
  ARCHIVED-WITHOUT-PLACEHOLDER. git returns rc 0 only after its rename. `archive_target` picks a `dest` that does not
  exist yet. So a directory at the old path after rc 0 is a late recreation, not the worktree. I found no input where
  rc 0 and `isdir(dest)` hold while the worktree was not moved. (The old guard would not have caught git moving INTO a
  pre-existing `dest` either: the old path is gone in that case too. That case is pre-existing and needs a race that
  creates `dest` between `archive_target` and the move.)
- **`leave_placeholder` uses `O_EXCL`, and the fold adds a `FileExistsError` branch and a guarded write.** Nothing at
  the old path is opened for writing. A write failure is caught as `OSError`/`ValueError` (which includes
  `UnicodeEncodeError`), so the move is never hidden behind a hook CANNOT RUN.
- **The F2 live-HEAD check.** A git failure (rc != 0, or a merged oid missing locally) gives KEPT. A deadline raises
  `CannotRun` and gives DEFERRED. It fails closed, and a move loses nothing in the window that remains.
- **`registered_at`.** It can only REMOVE BY-PEER verdicts. Every failure returns False, which means FAILED. A false
  BY-PEER now needs git to register the archive path at the evaluated HEAD, and in that state the worktree really
  is archived.
- **`refused_now`.** It only changes whether a move is ATTEMPTED. A retried move loses nothing.
- **`qpath`.** It changes only the printed text. A non-printable path is still withheld.

Self-test at this head: `python3 scripts/prune-merged-worktrees.py --self-test` → `92/92 passed` (23.7 s).

## Findings

### R4-C-M1 — MEDIUM — the r3 F3 FAILED row for a half-finished peer does not say where the worktree IS, and the next run's repair hint names a path that does not exist

- **Caused by the r3 fold?** Yes. Before r3 this state was BY-PEER with `row.dest = peer`, so the output named the
  archive copy. r3 F3 correctly makes it FAILED. But the `else` branch's reason is built only from
  `both_sides(row.path, dest)`, and `peer` is already computed there and then thrown away.
- **Evidence (a command I ran):** `scratchpad/halfpeer.py` runs the module's own `_HalfPeer` fault (the directory is
  renamed into the archive, and git still registers the old path), then runs again without the fault:
  - RUN1, rc 1: `FAILED half ... source .../worktrees/half is GONE, target .../archive/half is absent`. The worktree
    is actually at `archive/half-peer`, and the row does not say so.
  - RUN2, rc 0: `KEPT half ... its directory is missing; if it was being archived, `git worktree repair
    .../archive/half` re-links it`. That path does not exist: `logged_moves` takes the LAST `archiving` line, which
    is THIS run's failed target, not the peer's. In real use the peer takes `archive/<name>` and this run takes
    `<name>-<stamp>`, so the hint again names this run's target and not the directory.
  - RUN2 `--hook`: no lines at all, so after the first session start the state is silent.
- **Not data loss.** The directory and the admin dir are intact. The message says "NEVER `git worktree prune`", and
  `git worktree repair <right path>` recovers it. The risk is a human who cannot find the directory, then reaches
  for prune.
- **Fix sketch (to file):** when `peer` was found but `registered_at` is False, add to the FAILED reason "a copy
  linked to this worktree is at <peer>: `git worktree repair <peer>`". And let `logged_moves` (or the prunable
  hint) prefer an archive entry whose `.git` links to the worktree over the last logged target.

### R4-C-L1 — LOW — the printed undo for ARCHIVED-WITHOUT-PLACEHOLDER deletes a late FILE at the old path

- **Caused by the r3 fold?** Partly. `undo_cmd` is r2. The r3 fold now prints it for exactly the state where
  something that is NOT our placeholder sits at the old path (hook line `ARCHIVED WITHOUT A PLACEHOLDER ...; undo:
  rm <old> && git worktree move ...`, `hook_lines`).
- **Evidence:** `undo_cmd` is `rm {o} && git worktree move {d} {o}`. In the F6 shape (a regular file raced into the
  old path), running the printed undo removes that file's bytes. For a late DIRECTORY, `rm` without `-r` fails and
  `&&` stops it, so that case is safe. The reason text does say "look at it before running the undo's `rm`", so a
  careful reader is warned. The undo is not automatic.
- **Fix sketch:** for NO_PLACEHOLDER rows, print `mv <old> <old>.late-<stamp> && git worktree move ...` (or omit the
  `rm`) instead of the generic undo.

### R4-C-L2 — LOW — the 24 h refusal TTL is unbounded for a future or infinite `at`

- **Caused by the r3 fold?** Yes (`refused_now`, `load_refused`).
- **Evidence (a command I ran):** `scratchpad/inf.py` gives `load_refused` → `refused_now`, at the same HEAD:
  `at = Infinity` → held (True); `at = 1e300` → held; `at = now + 10 days` → held. Python's `json` accepts
  `Infinity`, and `isinstance(x, float)` passes it. A clock stepped back, or a hand-edited file, keeps the worktree
  quietly KEPT for longer than 24 h, and possibly for ever. That is the safe direction (no move happens), so it is
  LOW. It still breaks the F5 promise "tried again a day later, not never".
- **Fix sketch:** treat `at > now` (or a non-finite `at`) as absent in `refused_now`.

### R4-C-L3 — LOW — an ARCHIVED-WITHOUT-PLACEHOLDER row is loud ONCE, then the late directory is never mentioned again

- **Caused by the r3 fold?** Yes (a new state).
- **Evidence (from reading the code):** the next run does not list the late directory at the old path (git does
  not list it as a worktree), and the archive is outside `root`. So rc 1 and the hook line happen on one session
  start only. Whatever the late writer left there, which git resolves to the MAIN checkout, is reported once.
  FAILED (rule 7) has the same once-only behaviour, so this may be intended. I am noting it, not asking for a change.

## No finding

- F7 `qpath`: `shlex.quote` only for `isprintable()`. The F7 case runs the printed undo under `sh -c` with spaces in
  the paths. The hook template `rm {rt}/<name>` keeps a placeholder token, as it did before.
- The hook cap: the ARCHIVE line, then the NO_PLACEHOLDER line, then FAILED, then stop or deferred, then the note.
  At most five lines are produced and the cap is 4, so only the size note can be cut, and the NO_PLACEHOLDER line
  always survives.
- `rc` counts NO_PLACEHOLDER as 1, and `stop_line` counts it as archived. Both are consistent.

VERDICT: NOT CONVERGED
