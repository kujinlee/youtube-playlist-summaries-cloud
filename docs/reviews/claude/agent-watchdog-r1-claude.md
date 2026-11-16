Reviewed head: fdf36367b9cc77cbd9b54056cb2d4d09adc0ee4d

# agent-watchdog — round 1, Claude half (PR #596, backlog #657)

Reviewed: `git diff origin/master...HEAD` at `fdf36367` (branch `agent-watchdog`), adversarially — the brief was to
refute that the watchdog reports every genuinely quiet builder and never swallows a CANNOT RUN.

Self-test, run in this worktree: `51/51 self-test cases passed` (rc 0).

Every mutation below was run on a COPY of `scripts/` in the session scratchpad, never in the worktree.

## Findings

### F1 — MAJOR — a file with a FUTURE mtime makes a builder permanently "active": the row's own falsifier

`scripts/agent-watchdog.py:205` — `idle = now - max(last, armed)`. `last` is an absolute mtime, so any file in the
worktree whose mtime is later than the wall clock gives a negative `idle` at every poll, and the builder is never
reported however long it writes nothing.

Concrete failing input (run): a linked worktree `w2` whose only source file was stamped `touch -t 203001010000
w2/src/fixture.json`, watched with `main(['10', 'a=w2'])` on a fake clock that advances 60 s per sleep. Result: still
watching after 240 simulated minutes of a builder that wrote nothing. Ways a future stamp arrives: an archive or
fixture extracted with its stored times, a `touch -t`/`os.utime` in a test that targets the worktree, or a clock
step backwards (NTP correction) after a write.

This is exactly the backlog row's **Fails if** ("a builder worktree is quiet for N minutes and the orchestrator is
not woken"), and nothing reports it — the report only prints when someone is quiet or broken.

Fix direction: judge CHANGE, not recency. Keep the previous poll's `newest()` value per builder and restart that
builder's window only when the value differs (the window is then counted from the poll where it last changed, on
the watchdog's own clock). That makes the absolute mtime irrelevant, so a future stamp, clock skew or a
network-filesystem clock cannot freeze it. A case: stamp one file in 2030 before arming, expect exit 1 at minute 10.

### F2 — MAJOR — the walk's `onerror` call site is unguarded: dropping it silently skips an unreadable directory, 51/51 green

`scripts/agent-watchdog.py:151` — `os.walk(w.worktree, onerror=_walk_error)`. The self-test only calls
`_walk_error` directly (case "CANNOT RUN: a directory the walk cannot list…", lines 414-416); no case drives `newest`
or `main` over a directory that cannot be listed, and the manifest mutates `_walk_error`'s body, not the call.

Constructed mutation (survives): `os.walk(w.worktree, onerror=_walk_error)` → `os.walk(w.worktree)`. Self-test on
the mutant: `51/51 self-test cases passed`. Behaviour difference, measured on a worktree with `chmod 000
w/locked`: the original raises `CANNOT RUN: cannot list w/locked: Permission denied`; the mutant returns a normal
timestamp — the very "skip in silence" the `_walk_error` docstring exists to prevent. Unit coverage of the handler
does not compose to the call site.

Fix: one case that builds a worktree with an unlistable subdirectory and asserts `newest` refuses (skip the case
with a CANNOT RUN line when running as root, where `chmod 000` does not deny), and a manifest entry for the call.

### F3 — MINOR — an OSError other than the ones caught escapes as a traceback with exit 1, which the contract says means QUIET

`scripts/agent-watchdog.py:146-157` catch only `FileNotFoundError`; `main` (lines 199-204) catches only
`CannotRun`. Anything else propagates, and an uncaught Python exception exits **1** — the code the docstring
(lines 37-41) reserves for "at least one builder is quiet". Stdout is empty, no builder is named, and the exit
code tells the orchestrator the wrong thing.

Concrete failing inputs (both run):
- the git directory's `logs` is a FILE, not a directory → `os.stat(gd/'logs/HEAD')` raises `NotADirectoryError`;
  `python3 agent-watchdog.py 5 a=w` exits **1** with a traceback.
- a worktree subdirectory with mode `r--` (listable, not searchable) → `os.walk` lists it, `os.lstat` of its
  child raises `PermissionError: [Errno 13] … 'w/locked/f'`, uncaught.

Fix: in `newest`, convert any `OSError` other than `FileNotFoundError` on the optional git files and on the
per-entry `lstat` into `CannotRun` naming the path; one case per path.

### F4 — MINOR — a stageable `continue` is not mutated, and the manifest comment says it cannot be staged

`scripts/agent-watchdog.py:149-150` (`except FileNotFoundError: continue` in the `GIT_OPTIONAL` loop). Constructed
mutation `continue` → `break` survives (`51/51`). It changes behaviour when `index` is absent and `logs/HEAD` is
fresh: `logs/HEAD` is then never read. That is stageable with the existing `World` (remove `index`, stamp
`logs/HEAD` at `t0+8`, expect 8.0). `scripts/mutations/expected_mutations.py`'s new comment says the two
`except FileNotFoundError: continue` lines are "races … which no case can stage" — true of the walk's one
(line 156-157), false of this one. Add the case and the mutation, or correct the comment.

### F5 — MINOR — the 270 s floor is presented as sufficient; it bounds one TOOL CALL, not the time between activity

`scripts/agent-watchdog.py:24-27` and the backlog row's DONE text ("a silent foreground call is bounded at 270 s …
so a window of 270 s or less is refused") answer open question (a) as if any window over 270 s cannot report a
working builder. But silence also includes the model's own generation between calls (a long extended-thinking turn
or a single large `Write`), and waits not routed through foreground Bash (a `Monitor` wait, a background job the
builder then waits on). `4.6` is accepted (case at line 330) and would report such a builder. The floor is
necessary, not sufficient; the docstring and row should say so (the checklist's recommended `30` is fine in
practice). No code change required.

### F6 — MINOR — two activity claims in the docs are not what happens in this repo

1. `scripts/agent-watchdog.py:28` — "A builder that READS for a long stretch … changes nothing in its worktree."
   Observed in this worktree during this review: `.claude/banner-turn-state/<session>.json`,
   `.claude/recall-cache/.last-said`, `.claude/ci-unwatched.log` and `scripts/__pycache__/` were all modified in
   the last 20 minutes, by hooks and by running a self-test, not by edits to tracked files. So reading CAN register
   as activity, and — the converse — a FINISHED builder whose worktree then hosts review rounds (this one does: the
   Codex and Claude halves run here) is not reported as quiet, contrary to the bound at lines 47-48 ("a finished
   builder goes quiet and is reported"). Worth one sentence in BOUNDS: anything working in the worktree counts,
   reviewers and hooks included.
2. `docs/process-checklists.md:178` offers `[:<transcript>]` but nothing says where a builder's transcript is. It
   lives at `~/.claude/projects/<slug>/<session>/subagents/agent-<name>-<hash>.jsonl`, whose hash is not known
   before the spawn result. Without that, the transcript answer to open question (a) is not actionable from the
   checklist. Name the path pattern (or say how to find it) in the checklist line or the docstring.

## What I tried that held

- Exit code on a quiet builder, CANNOT RUN at arming and mid-watch, both reported in one poll: each pinned by a
  case and a mutation in the manifest.
- `.git` exclusion vs a linked worktree's `.git` FILE: the file is counted (it is in `files`, not `dirs`), the main
  checkout's `objects/` are not; correct.
- `node_modules` is a symlink in real worktrees (`node_modules -> ../../../node_modules`); `os.walk` does not
  follow it and it is excluded by name anyway. A full walk of this worktree (5,353 files) took 0.05 s, so the 60 s
  poll costs nothing.
- Argument edge cases (`nan`, `inf`, negative, `=` in a path, duplicate names) are refused or harmless.
- The `LONGEST_SILENT_CALL_S` identity case reads `check-agent-long-call.py`'s `LIMIT_S = 270` (line 87) and its
  drift mutation is in the manifest.

VERDICT: NOT CONVERGED
