# Round 1 — `agent-watchdog` — coordinator — ⟳ NOT CONVERGED (both halves); every finding FIXED

Both halves reviewed `fdf36367` (PR #596, backlog #657): Codex (`gpt-6.1-sol`, `docs/reviews/codex/agent-watchdog-r1-codex.md`)
and Claude (`docs/reviews/claude/agent-watchdog-r1-claude.md`). Both NOT CONVERGED.

```yaml
round: 1
fixes_nontrivial: true
subject: agent-watchdog
halves:
  codex: ran
  claude: ran
findings:
  - {id: XM1, severity: Major, aim: deliverable, fix_induced: false, component: quiet-window, disposition: fixed}
  - {id: XM2, severity: Major, aim: deliverable, fix_induced: false, component: newest, disposition: fixed}
  - {id: XM3, severity: Major, aim: deliverable, fix_induced: false, component: gitdir, disposition: fixed}
  - {id: Xm4, severity: Minor, aim: deliverable, fix_induced: false, component: newest, disposition: fixed}
  - {id: Xm5, severity: Minor, aim: deliverable, fix_induced: false, component: gitdir, disposition: fixed}
  - {id: CF1, severity: Major, aim: deliverable, fix_induced: false, component: quiet-window, disposition: fixed}
  - {id: CF2, severity: Major, aim: deliverable, fix_induced: false, component: newest, disposition: fixed}
  - {id: CF3, severity: Minor, aim: deliverable, fix_induced: false, component: newest, disposition: fixed}
  - {id: CF4, severity: Minor, aim: deliverable, fix_induced: false, component: newest, disposition: fixed}
  - {id: CF5, severity: Minor, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
  - {id: CF6, severity: Minor, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
```

**Overlaps:** XM1 = CF1 (a future mtime). XM2 = CF3 (an OSError other than a missing file escapes).

Every fix was test-first: the new cases were added to the suite and run against the unfixed code (`54/60`, six red:
the symlink-loop/`logs`-file pair, the `r--` directory, the directory transcript, the FIFO `.git` — reported as
`BLOCKED`, not hung — the future-stamped file, and the two-builder poll with a looping `index`), then the code was
fixed (`60/60`). Three new cases were green from the start because the code was right and only a MUTATION survived
(CF2's mode-000 walk, Xm5's non-UTF-8 `.git`, CF4's fresh `logs/HEAD`); each is now the named killer of that mutation.

| Finding | Disposition | Fix and evidence |
|---|---|---|
| **XM1 / CF1** — a file stamped in the future holds a builder "active" forever | FIXED | `main` keeps, per builder, `(newest value, the watchdog's clock when it last changed)`; the window restarts only when the value CHANGES, and an mtime is never compared with now. Case *a file stamped a YEAR in the future does not keep a builder active: woken at minute 10* (red before: `slept 200 times and never exited`). Mutations: the absolute comparison restored, a change not restarting the window, every poll a change. |
| **XM2 / CF3** — any OSError but `FileNotFoundError` escapes as a traceback (exit 1 = "quiet"), and hides the other builders | FIXED | `newest` turns any other `OSError` on an optional git file and on a worktree entry's `lstat` into `CannotRun` naming the path, so `main` reports THAT builder CANNOT RUN and still judges the rest. Cases: a symlink-loop `index` and a `logs` FILE; an `r--` directory; and in `main`, a looping `index` on builder b beside builder a → exit 2, `CANNOT RUN b:` and `active a:` in one report. Two mutations (each `raise` → `continue`). |
| **XM3** — a FIFO `.git` blocks the open forever | FIXED | `gitdir_of` refuses a `.git` that is neither a directory nor a regular file BEFORE opening it. The case runs the call in a thread bounded at 5 s and unblocks the reader itself on a timeout, so a regression fails the case and never hangs the suite (a hung suite would be a CANNOT RUN of the mutation sweep). Mutations: the check dropped; its `raise` → `return worktree`. |
| **Xm4** — a directory is accepted as a transcript | FIXED | `newest` stats the transcript once and refuses a non-regular file. Case + mutation (`S_ISREG` → `False`). |
| **Xm5** — narrowing `except (OSError, UnicodeDecodeError)` survives | FIXED | Case *a .git file that is not UTF-8*; mutation added. The old mutation on that `raise` (formerly attributed to the no-`.git` case, now answered first by the regular-file check) is re-attributed to this case. |
| **CF2** — dropping `onerror=_walk_error` at the call site survives | FIXED | Case *a directory the walk cannot LIST (mode 000), through newest() and the real walk*; mutation on the call site. As root, where `chmod` does not deny, the case FAILS with a CANNOT RUN message rather than passing. |
| **CF4** — `continue` → `break` in the `GIT_OPTIONAL` loop survives; the pin comment called it unstageable | FIXED | Case *a missing index does not hide a fresh logs/HEAD*; mutation added; the comment in `scripts/mutations/expected_mutations.py` now says only the WALK's `continue` is unstageable. |
| **CF5** — the 270 s floor read as sufficient | FIXED (docs) | Docstring: the floor is necessary, not sufficient (model generation between calls, Monitor and background waits), and a window just over it can report a working builder; use 30. |
| **CF6.1** — hooks, `__pycache__` and review rounds count as activity | FIXED (docs) — stated, not excluded | BOUNDS now says anything writing in the worktree counts, and why `.claude/` is not excluded: a hook firing on the builder's own turns IS its activity. A finished builder whose worktree then hosts a review is not reported quiet. |
| **CF6.2** — nowhere says where a builder's transcript lives | FIXED (docs) | The path pattern `~/.claude/projects/<slug>/<session>/subagents/agent-<name>-<hash>.jsonl` is in the docstring and the `docs/process-checklists.md` line, with "known after the spawn". |

**Manifest:** 43 → 53 mutations. Retired with the code they mutated: *the window is no longer counted from arming*,
*an active builder's age is counted from arming*. Twelve added (above). Pin and its comment updated.

## Gates, on the fold commit

- `python3 scripts/agent-watchdog.py --self-test` → `60/60 self-test cases passed`
- `python3 scripts/check-plan-code.py --mutate . --only scripts/agent-watchdog.py` → `OK — delivered scripts mutated: 1 file(s), 53 mutation(s), 53 killed, 53 attributed to the case each names, 0 survivor(s)`
- `check-ratchet-contract.py` → `ratchet contract OK`; `check-selftest-counts.py --only agent-watchdog.py` → verified;
  `check-docs.py` → `Documentation integrity OK`; `check-reference-namespace.py` → OK; `check-fixture-variation.py` → OK.

Round 2 owes ONE half (alternation).
