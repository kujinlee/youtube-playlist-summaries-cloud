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

## CM3 — the measured capture (2026-11-16 05:07-05:08 PST)

Harness 2.1.323, a throwaway `claude -p --model haiku` in a scratch directory with
`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`, and one hook saving every `Stop`, `SubagentStop` and `TeammateIdle` payload.
The session launched ONE background `Agent` named `idler` (`run_in_background: true`) that answered `ok` and went
idle; the main session then waited and stopped. Two payloads were saved, and no `TeammateIdle` event fired:

```
05:07:39  SubagentStop  agent_id a53021a581ba52350  last_assistant_message "ok"
          background_tasks: [{"id": "a53021a581ba52350", "type": "subagent", "status": "running",
                              "description": "idle probe", "agent_type": "general-purpose"}]
05:08:28  Stop          (no agent_id)  stop_hook_active false  last_assistant_message "finished"
          background_tasks: []      session_crons: []
```

**Reading:** 49 s after the named background agent finished its turn, the main session's Stop payload no longer
lists it. The idle entry does NOT persist, so signal (a) needs no change for it. **Bound, stated and not fixed:** the
agent appeared as `type: "subagent"` in this headless run; an `in_process_teammate` entry in an INTERACTIVE team
session was not captured. This is ONE capture, on one harness version.

## Fold — round 1 (fold agent, Fable 5.2)

**Method.** Every new case was written first and run against the UNFIXED `175d82c6` code: **45 of 71 passed, 26 red**
(the red count per finding is in the table). Then the fix; the suite is now **73 cases** (two `run_gh` cases were
added after the red run, with the `timeout_s` parameter they need, so they have no red-before figure). The manifest
went from 48 to **79 mutations**; seven were deleted or replaced with the code they mutated (the four prose-question mutations,
"NOT CHECKED blocks", "(a) a finished task counts as running" and "(c) EXPECTED is not pending").

| Finding | Red before | Case(s) that pin it | Mutation(s) | Bound stated instead of fixed |
|---|---|---|---|---|
| **XM1 / CM2** worktree signal | 7 | `⭐ (b) a fresh git worktree add is not running work`; `(b) a file counts only SETTLE_S after the worktree's .git`; `(b) a fresh file under __pycache__ or inside a .git directory`; `(b) a directory with no .git is not a builder worktree`; `⭐ (b) the orchestrator's own checkout never counts`; `(b) decide passes own on`; `⭐ main: the session's OWN worktree never counts` | settle margin dropped / halved / doubled; `__pycache__` walked; `.git` walked; no-`.git` directory is a worktree; own checkout counts; `own` compared unresolved; decide / main do not pass `own` | A merge of master INTO a builder worktree still reads as activity for the window (docstring). The direction said "newer than the `.git` file"; measured over 4 real worktrees a checkout finishes within 1.56 s of `.git`, so the rule is `.git` mtime + `SETTLE_S` (60 s) — a real builder's first minute is not seen |
| **XM2 / CM1** question exception | 3 | `⭐ a closing CHECK/RESULT table whose cell reads as a question`; `a ? in prose is no exception` (five inputs); `the block does not teach ending on a question` | `?` anywhere is a question again; a closing `?` is a question again; the block teaches a question | A real plain-prose question to the owner costs one block (docstring: ONE NUDGE, NOT A LOCK) |
| **XM3** task status | 2 | `⭐ (a) a task with NO status is not running work`; `(a) only an explicit live status counts` (failed, stopped, unknown, null) | missing status defaults to running; any status but a finished one counts (the reviewers' `"failed"` survivor); `pending` is not live; case-sensitive status | — |
| **CM3** idle teammate | — | no code change (measured above) | — | `in_process_teammate` in an interactive session not captured |
| **XM4** fail closed | 8 | `⭐ gh cannot answer (rc 1) → BLOCK, naming (c), gh's own words and NOT RUN`; `gh answers with something that is not a PR list`; `⭐ a payload with no background_tasks`; `no main checkout → BLOCK, naming (b)`; `an unlistable worktrees directory → BLOCK, naming (b)`; `the block names an unread signal only when one was unread`; `⭐ main: gh cannot answer exits 2`; `⭐ END TO END: the real run_gh over a gh that exits 1` | an unread signal ALLOWS; (b) / (c) unread not named; the unread list not named; gh's cause dropped; block exits 1 | The ONE remaining NOT CHECKED (allowed, exit 1, said) is a payload that is not a JSON object: `stop_hook_active` cannot be read from it, so a block there could loop. A crash of the checker still exits 1 |
| **XM5** finished work blocked once | — | DECLINED by the coordinator; documented in the docstring | — | by design |
| **XM6** FIFO, walk deadline | 4 | `⭐ read_tail of a FIFO with no writer returns None at once`; `read_tail refuses a file that is not regular` (`/dev/zero`); `⭐ main: a FIFO transcript_path does not hang the hook`; `⭐ (b) the walk has a wall budget` — the FIFO cases run under a thread timeout, so a regression reads `HUNG` and fails | `O_NONBLOCK` removed; the regular-file test removed; the walk deadline ignored; out-of-budget read as "nothing moved"; the budget parameter ignored | The walk budget is `WALK_BUDGET_S` = 1.0 s (the direction allowed ≤ 1.5 s); the deadline is tested between directories, so ONE huge directory listing is not interrupted |
| **XM7** non-dict record | 1 | `a transcript record that is not an object` | the `isinstance` skip removed | — |
| **XM8** replays through `main()`, launcher | 0 (coverage) | `⭐ main: the replayed 02:24 …` and `… 02:29 …` exit 2; four END TO END cases run `.claude/hooks/check-idle-stop.sh` from a temp tree with a stub `gh` on `PATH` (02:29 replay → exit 2 and the reason on stderr; a running job → 0; a pending check → 0; `gh` exits 1 → exit 2 naming gh's words); two `run_gh` cases (cannot start; a `gh` that sleeps 5 s is cut at its timeout) | the real gh never called; `run_gh` drops stderr / reads a failed gh as an answer / cannot-start read as an answer / no timeout / ignores its timeout | The launcher `.sh` itself carries no mutation (no manifest in this repository targets a hook launcher); its exit mapping is exercised by the END TO END cases only |
| **Cm4** another hook's block | — | prose only | — | docstring, *ONE NUDGE, NOT A LOCK*: any Stop hook's block sets `stop_hook_active` and this guard skips the continuation |
| **Cm5** unlistable worktrees dir | 0 at function level (the decide-level case is one of XM4's 8) | `(b) a worktrees path that cannot be listed is None (unread), not 'no builders'` | `return None` → `return []` | — |
| **Cm6** never-started checks | 1 | `⭐ (c) a check that never STARTED is not running work: EXPECTED, WAITING, REQUESTED`; `(c) QUEUED and a PENDING run are pending` | EXPECTED / WAITING / REQUESTED count as started; QUEUED not pending; a PENDING run not pending; a CheckRun read by state | A `StatusContext` stuck at `PENDING` (reported once, never resolved) still holds (c) on while its PR is open |

**Gates, run on the fold's tree (2026-11-16):**

- `python3 scripts/check-idle-stop.py --self-test` → `73/73 self-test cases passed` (1.9 s)
- `python3 scripts/check-plan-code.py --mutate . --only scripts/check-idle-stop.py` → `OK — delivered scripts mutated: 1 file(s), 79 mutation(s), 79 killed, 79 attributed to the case each names, 0 survivor(s) — measured over ONLY scripts/check-idle-stop.py — a DIAGNOSTIC slice, not the gate` (189 s)
- `check-ratchet-contract.py` → `ratchet contract OK`; `check-guard-coverage.py` → every guard classified, every
  SEQUENCE guard mutation-covered; `check-fixture-variation.py` → `fixture variation OK — 2384 parameter(s) examined
  across 105 file(s)`; `check-docs.py` → `Documentation integrity OK`; `check-reference-namespace.py` → OK;
  `check-selftest-counts.py` → 89 scripts declare a count, every one verified.
- **Hook latency, measured through `.claude/hooks/check-idle-stop.sh` in this worktree**, with a `gh` on `PATH` that
  sleeps 30 s, a FIFO `transcript_path` with no writer and an empty HOME: **3.56 s, 3.27 s, 3.28 s**, exit 2 each
  time, the reason naming (c). ⚠ The worktree walk did NOT exhaust its budget in this measurement; the worst case by
  construction is `GH_TIMEOUT_S` 3.0 s + `WALK_BUDGET_S` 1.0 s + start-up (about 0.3 s here), under the 5 s asked.

**Not fixed:** nothing the Dispositions table asked for is left open. Stated as bounds, not fixed: the
`in_process_teammate` capture, the merge-into-a-builder-worktree activity, a builder's first 60 s, a `StatusContext`
stuck at `PENDING`, one huge directory listing inside the walk, and the launcher having no mutation of its own.
