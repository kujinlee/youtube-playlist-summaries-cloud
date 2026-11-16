# Round 1 — `idle-stop-guard` — coordinator — ⟳ NOT CONVERGED (both halves)

Both halves reviewed `175d82c6` (branch `idle-stop-guard`, the owner's 11-16 02:51 request): Codex (`gpt-6.1-sol`,
`docs/reviews/codex/idle-stop-guard-r1-codex.md`, 8 MAJOR) and Claude (`docs/reviews/claude/idle-stop-guard-r1-claude.md`,
3 MAJOR, 3 MINOR). Both NOT CONVERGED.

```yaml
round: 1
fixes_nontrivial: true
subject: idle-stop-guard
halves:
  codex: ran
  claude: ran
findings:
  - {id: XM1, severity: Major, aim: deliverable, fix_induced: false, component: worktree-signal, disposition: fixed}
  - {id: XM2, severity: Major, aim: deliverable, fix_induced: false, component: question-exception, disposition: fixed}
  - {id: XM3, severity: Major, aim: deliverable, fix_induced: false, component: task-signal, disposition: fixed}
  - {id: XM4, severity: Major, aim: deliverable, fix_induced: false, component: ci-signal, disposition: fixed}
  - {id: XM5, severity: Major, aim: deliverable, fix_induced: false, component: decision, disposition: declined}
  - {id: XM6, severity: Major, aim: deliverable, fix_induced: false, component: payload-reader, disposition: fixed}
  - {id: XM7, severity: Major, aim: deliverable, fix_induced: false, component: payload-reader, disposition: fixed}
  - {id: XM8, severity: Major, aim: deliverable, fix_induced: false, component: self-test, disposition: fixed}
  - {id: CM1, severity: Major, aim: deliverable, fix_induced: false, component: question-exception, disposition: fixed}
  - {id: CM2, severity: Major, aim: deliverable, fix_induced: false, component: worktree-signal, disposition: fixed}
  - {id: CM3, severity: Major, aim: deliverable, fix_induced: false, component: task-signal, disposition: fixed}
  - {id: Cm4, severity: Minor, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
  - {id: Cm5, severity: Minor, aim: deliverable, fix_induced: false, component: self-test, disposition: fixed}
  - {id: Cm6, severity: Minor, aim: deliverable, fix_induced: false, component: ci-signal, disposition: fixed}
```

**Overlaps:** XM1 = CM2 (any file write in any worktree counts as running work). XM2 = CM1 (a `?` anywhere is a
"question to the owner").

## Dispositions — decided by the coordinator before the fold

| Finding | Disposition | Direction for the fold |
|---|---|---|
| **XM2 / CM1** — the `?` exception is a prose escape; it reopens the very hole (a closing table cell `#657 started? ✅` ALLOWS with nothing running) | FIX | Drop the punctuation test entirely. The ONLY question exception is a structured one: the last assistant turn called `AskUserQuestion`. A plain-prose question costs one block, and the `stop_hook_active` continuation then passes — one nudge, never a wedge. The block reason must stop teaching "end on a question". |
| **XM1 / CM2** — a file write is evidence work HAPPENED, not that it is HAPPENING: a fresh `git worktree add`, a merge, `__pycache__`, review files all ALLOW | FIX | A worktree counts only by a file newer than the worktree's own `.git` file's mtime AND not under `__pycache__`/`.git`; the orchestrator's own checkout never counts. ⚠ A merge of master into a builder worktree still reads as activity — state it as a BOUND in the docstring, not silently. |
| **XM3** — a task with NO `status` counts as running | FIX | Only an explicit live status (`running`, `pending`) counts; unknown or missing → not running. Add the `"failed" ∉ TERMINAL` survivor's killer. |
| **CM3** — an idle in-process teammate may keep `status: running` | FIX if measured | Capture ONE Stop payload > 30 s after a background `Agent` goes idle (throwaway `claude -p`, as the build did). If the idle entry persists, (a) must not count it (use any field that distinguishes it, else document the bound). Record the measured payload either way. |
| **XM4** — `gh` CANNOT RUN, or a missing `background_tasks`, lets the stop through | FIX | ⟳ Reversed from the build brief: because `stop_hook_active` lets the continuation pass, a block is ONE nudge, never a wedge — so fail CLOSED: an unanswered `gh` or a missing `background_tasks` is "no evidence", and the stop BLOCKS once with a reason naming what could not be read. Only a crash of the checker itself (exit ≠ 2) still allows. |
| **XM5** — "everything is finished and merged" is blocked once | DECLINED | By design. With the owner away, ending a turn with nothing running IS the failure: the next action is the next work item. The one nudge is cheap and the continuation passes. Documented in the docstring. |
| **XM6** — a FIFO transcript blocks `open()` until the hook's 10 s timeout; the walk has no deadline | FIX | Open with `O_RDONLY|O_NONBLOCK`, `fstat`, refuse a non-regular file; give the worktree walk a wall budget (≤ 1.5 s) after which that signal is "could not read". Case bounded by a thread timeout so a regression fails, never hangs. |
| **XM7** — a JSONL record `[]` raises `AttributeError` | FIX | Skip any record that is not a dict; case. |
| **XM8** — the replays run through `decide()` only; `run_gh` and the launcher are unexercised | FIX | Both replays (02:24, and the turn the owner called 02:28, timestamped 10:29:12Z = 02:29) go through `main()`; one case runs `.claude/hooks/check-idle-stop.sh` end to end with a stub `gh` on `PATH` and asserts exit 2 and the reason on stderr. |
| **Cm4** — a block by `block-idle-stop.sh` sets `stop_hook_active` and disables this guard for the continuation | FIX (prose) | State it as a bound in the docstring. |
| **Cm5** — the unreadable-worktrees-dir branch is never exercised | FIX | Case + mutation (`return None` → `return []`). |
| **Cm6** — a check stuck in `EXPECTED`/`WAITING` turns (c) on forever | FIX | Count only checks actually started (`IN_PROGRESS`/`QUEUED`/`PENDING` state); a check that never started is not running work. |
