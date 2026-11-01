# Round 1 — `boundary-compaction-440` — coordinator — NOT CONVERGED (both halves); all findings FOLDED

Both halves reviewed `cfdcf659`, the head of PR #463 (backlog #440, the PreCompact boundary hook). Under the
round cap, round-1 findings are folded at every severity. Neither half named a Q4c BLOCKER by that rule's
evidence bar; Claude labelled F1 "BLOCKER" because the live sentinel refutes the deferral clause today. It is
fixed either way.

```yaml
round: 1
fixes_nontrivial: true
subject: boundary-compaction-440
halves:
  codex: ran
  claude: ran
findings:
  - {id: C1, severity: High, aim: deliverable, fix_induced: false, component: agent-signal, disposition: fixed}
  - {id: C2, severity: High, aim: deliverable, fix_induced: false, component: ceiling, disposition: fixed}
  - {id: C3, severity: Medium, aim: deliverable, fix_induced: false, component: agent-signal, disposition: fixed}
  - {id: C4, severity: High, aim: deliverable, fix_induced: false, component: idle, disposition: fixed}
  - {id: C5, severity: Medium, aim: deliverable, fix_induced: false, component: fail-open, disposition: fixed}
  - {id: C6, severity: Medium, aim: deliverable, fix_induced: false, component: fail-open, disposition: fixed}
  - {id: F1, severity: High, aim: deliverable, fix_induced: false, component: plan-signal, disposition: fixed}
  - {id: F2, severity: Medium, aim: deliverable, fix_induced: false, component: ceiling, disposition: fixed}
  - {id: F3, severity: Medium, aim: deliverable, fix_induced: false, component: agent-signal, disposition: fixed}
  - {id: F4, severity: Low, aim: deliverable, fix_induced: false, component: monitor-signal, disposition: declined}
  - {id: F5, severity: Low, aim: deliverable, fix_induced: false, component: idle, disposition: declined}
  - {id: F6, severity: Low, aim: deliverable, fix_induced: false, component: fail-open, disposition: fixed}
```

C = Codex finding N, F = Claude finding N. Every fix has a self-test case that goes red when the fix is reverted
and a mutation entry naming that case: **41/41 killed and attributed** (`--mutate . --only
scripts/check-compaction-boundary.py`, 28 s), self-test **77/77**.

## Dispositions

| # | Finding | Disposition |
|---|---|---|
| F1 | A `paused:` sentinel, or one from another session, counts as mid-work; the project dir's sentinel reaches a worktree session | **FIXED** `scripts/check-compaction-boundary.py:280-283` (`sentinel_armed`: `paused:` → not armed; a `session:` that differs from `CLAUDE_CODE_BRIDGE_SESSION_ID` → not armed; either id unknown → armed, because the ceiling bounds that guess) and `:399` (the session's own checkout only; the project dir only when no checkout holds the cwd). The grammar and the session id come from `check-plan-progress.py` (`parse_sentinel`, `current_session`) and are not copied. Re-run against the live coordinator state: `signals` went from `plan+agent` to `agent`. ⚠ **Residual, stated in the docstring and the backlog row:** the bridge session id is SHARED by a coordinator and its in-process teammates (measured: this fold agent's env carries `session_01Fq…`, the coordinator's id), so a teammate whose cwd is the same checkout still reads the coordinator's LIVE plan as its own. Closing that would need the sentinel to record `CLAUDE_CODE_SESSION_ID`, which is `begin-plan.py`'s change, not this PR's. |
| C2 / F2 | The ceiling can exceed the model's hard limit (1.5 × 1M = 1.5M; 1.5 × 180k on a 200k model) | **FIXED** `:286-289`: ceiling = min(1.5 × W, 90% × L), where L is the smallest documented window (200k, 1M) that holds W. Claude Code caps W at the model's window, so this choice of L is conservative: a 180k W on a 1M model gets 180k, which is early but never late. The log records `limit` and `ceiling_by` (`1.5W` or `limit`). The 10% margin also covers the tool results after the last usage, which `ctx` does not see (F2's second point). ⚠ The table lists the documented windows and was NOT MEASURED per model; it is stated as such. |
| C1 | A completed foreground Agent stays open: its result carries an `agentId:` footer | **FIXED** `:202`: `agentId` marks a background launch only when the result says `agent launched`. Measured on the coordinator transcript: all 65 background launch results begin `Async agent launched successfully.` and all 189 teammate spawns begin `Spawned successfully.`. The new case uses Codex's real completed-result shape. |
| C3 / F3 | A lost notification holds `agent` for the whole tail | **FIXED** `:240`: an open Agent stops counting 3 h (`AGENT_LEASE_S`) after its call. Codex proposed 30 min and Claude proposed 3 h. Claude's measurement decides it: the longest live agent was about 1.2 h, so 30 min would drop live work. |
| C4 | Fresh tool activity is read as idle, because only assistant records set `last_at` | **FIXED** `:167`: any `assistant`, `user` (tool results, prompts) or `attachment` (queued notifications) record with a timestamp is activity. The old case "last_at is the last ASSISTANT record" pinned the defect and has been replaced. |
| F5 | The 5-min idle threshold may be longer than the harness's idle compaction | **BOUND STATED** `:24-28` and the backlog row. The PreCompact payload carries `trigger` and nothing else that separates idle from threshold compaction (the study's own measurement), so there is nothing better to read. Codex cites about an hour of documented inactivity, and the transcript's idle rewrites point to a 1 h TTL here. A 5-min TTL is NOT MEASURED. 300 s is kept because a lower value would allow compaction during silent long tool runs. |
| C5 | Malformed transcript records are skipped, so an obsolete signal survives | **FIXED** `:162` and `:389`: any record that is not a JSON object is counted, and any count fails OPEN (`allow-cannot-run`, with the count logged). The cut first line of a tail is dropped in `read_tail`, so it is never counted. Measured cost: **0 malformed lines in the coordinator's 74,195**. |
| C6 | A FIFO at the transcript or the log hangs `open()` past the hook's bounds | **FIXED** `:328-331`: every file the hook reads or writes (transcript, settings, sentinel, `.git`, `commondir`, log) goes through `open_regular`, which opens `O_NONBLOCK` and refuses anything that is not a regular file. Both FIFO cases run in a thread and release their peer after 2 s, so the reverted mutant reports `hung` and does not hang the suite. Also from C6's validation notes: undecodable snapshot output raised `UnicodeDecodeError` and the wrapper then took a SECOND snapshot. **FIXED** `:460` (`errors="replace"`). |
| F6 | `"cwd": 5` crashes `log_path` (`TypeError`) | **FIXED** `:412` `_cwd`: a missing or non-string cwd becomes `.`, and both `evaluate` and `log_path` use it. A non-string `transcript_path` is now a CANNOT RUN reason, not a crash. |
| F4 | Monitors that end with no `<status>` count until their 30-min expiry | **NO CHANGE**. Bounded at 30 min. Claude rates it as noise in the log, and I agree. |

## The halves DISAGREED on whether the ceiling is the usual path, and both views are recorded

- **Codex (C3):** with p = 11/243 = 4.53% of agents never notified and 20 agents a day, it estimates **0.91 stale
  opens a day** and **about 60% odds of at least one a day**. On that basis "ceiling is the usual path" is credible
  during sustained work. Codex labels these estimates, not a measured ceiling rate.
- **Claude (F3):** it **measured** 370 busy stretches (split at gaps of 5 min or more): median growth 8.4k, p90 44.6k,
  and only **14 of 370 (3.8%)** grow by 150k or more, which is the W→1.5W headroom. A stale signal therefore usually
  clears at the next idle gap, before the ceiling. Claude adds that this is per stretch, not per compaction, so the
  ceiling's share of compactions will be higher than 3.8%.
- **Resolution:** neither figure is the quantity the backlog row's drop rule names (the share of ALLOWED auto
  compactions that the ceiling forced). `--summary` measures that quantity. This fold makes the log trustworthy by
  removing the two causes of false `block-*` rows: a paused or foreign plan (F1) and an agent past its lease (C3).
  The disagreement is settled by the log, not by either estimate.

## Gates run (foreground, on the fold)

| Check | Result |
|---|---|
| `check-compaction-boundary.py --self-test` | 77/77 |
| `check-plan-code.py --mutate . --only scripts/check-compaction-boundary.py` | 41 killed, 41 attributed, 0 survivors |
| `check-fixture-variation.py` (pin re-derived with `analyse()`, +7 keys) | OK |
| `check-selftest-counts.py`, `check-ratchet-contract.py` | OK |
| `check-docs.py`, `check-review-rounds.py`, both plan-leak scans | see the commit's report |

## Next

Round 2 has ONE half, Claude (Opus), over the fold commit. `REVIEW GAP: codex — alternation` (round cap: both
halves in r1, then alternate in r2 and r3).
