Reviewed head: 70e9188fa423ecc68eb2a53d8ad6f01962991ad0

# idle-stop-guard — round 5, Claude half (adversarial)

Subject: `scripts/check-idle-stop.py` and its launcher `.claude/hooks/check-idle-stop.sh` at `70e9188f`.
Round 5 is past the round cap: every non-BLOCKER below is to be FILED, not fixed.

## What was run

- `python3 scripts/check-idle-stop.py --self-test`. Last line: `61/61 self-test cases passed` (rc 0).
- Probes went through the real launcher (`bash .claude/hooks/check-idle-stop.sh`), using a copy of the three
  scripts in `…/scratchpad/r5-isg/w`, a stub `gh` on PATH and a throwaway `HOME`. The probe driver is
  `…/scratchpad/r5-isg/probe.py`. Observed results (exit code, wall seconds):

| # | Input | Exit | Time |
|---|---|---|---|
| P0 | "Now starting backlog #657.", `background_tasks: []`, gh `[]` | 2 | 0.52 s |
| P1 | same + `[{"type":"in_process_teammate","status":"running"}]` (an idle teammate, see F1) | 0 | 0.09 s |
| P2 | same + `[{"type":"shell","status":"running","command":"python3 -m http.server 7391"}]` | 0 | 0.09 s |
| P3 | gh is a `sh` script that forks `sleep 20` (the grandchild holds stdout) | 2 | 3.09 s |
| P3b | P3 + `stop_hook_active: true` | 0 | 0.09 s |
| P4 | `~/.claude/.rate-limits.json` is a FIFO | 2 | 0.12 s |
| P5 | FIFO cache + P3's slow gh | 2 | 3.10 s |
| P6 | payload over 1 MiB (`MAX_STDIN`) | 1 (NOT CHECKED, allowed) | 0.10 s |
| P7 | `stop_hook_active: "true"` (a string) | 2 | 0.12 s |
| P8 | `stop_hook_active: true` | 0 | 0.09 s |
| P9 | another PR's `StatusContext` stuck at `PENDING` | 0 | 0.14 s (a stated bound, docstring lines 77-78) |
| P10 | CheckRun `IN_PROGRESS` | 0 | 0.09 s |

- **Wedge (2):** I found none. `decide` returns ALLOW on `stop_hook_active is True` before any signal is read
  (`check-idle-stop.py:194`). `main` returns 2 only on BLOCK, and a crash becomes 1 in the launcher. The slowest
  path I could build was 3.10 s (P5): `run_gh` is bounded at 3 s, and `subprocess.run` kills `gh` and only
  `wait()`s on POSIX, so a grandchild that holds the pipe does not extend the bound (P3). The stdin bound (2 s)
  and the cache-read deadline add at most about 3 s more, which stays under the 10 s timeout in
  `.claude/settings.json:202`.
- **Refusing a genuinely running task (3):** I found none. I read the Stop payload builder in the Claude Code
  2.1.323 binary. The payload's `background_tasks` is built by `e9n(taskRegistry.all())`, which keeps only tasks
  where `nS(r)` holds. `nS` is `status === "running" || status === "pending"`, and it drops a task whose
  `isBackgrounded === false`. So the harness already emits only live statuses, and `LIVE` at
  `check-idle-stop.py:108` agrees with it. A live background task always yields exit 0 (P1, P2, P10).
- **Dead paths from (b):** nothing in the code is dead. Every one of `moved_worktrees`, `_recent`,
  `window_text`, `IDLE_WINDOW_S`, `SETTLE_S`, `WALK_BUDGET_S`, `SKIP_DIRS` and `main_checkout` is gone from
  `scripts/check-idle-stop.py`, its launcher and its manifest. The only remaining mentions are history comments
  in `scripts/check-fixture-variation.py:435-438`. `WORKTREES` (`check-idle-stop.py:107`) is still used by the
  self-test (line 609) and by the re-add mutation (`scripts/mutations/check-idle-stop.json`, the last entry), so
  it is not dead. Its comment says so. Every top-level import is used. The docstring no longer claims (b).
  The `main.root` exemption (`check-fixture-variation.py:1475`) now correctly says `root` only reaches `run_gh`.

## Findings

### F1 — MAJOR (filed; a BLOCKER-class lead, not reproduced end to end) — an IDLE in-process teammate is emitted as `status: "running"`, which brings back the XB1 shape through (a)

- **Where:** `scripts/check-idle-stop.py:133-140` (`running_tasks`), `:202-204`. The docstring bound is at
  `:49-53` and `:82-83`.
- **Evidence:** I read the code statically from the 2.1.323 binary. I did NOT capture a payload.
  - When an in-process teammate's turn ends, the runner updates the task to
    `{...o, isIdle: !0, evictAfter: … Date.now()+X0, …}` and leaves `status` at `"running"`.
  - The harness's own "is it working" predicates test `status==="running" && !isIdle`.
  - The Stop payload builder `e9n` copies `status` and never `isIdle`. `nS` filters only on status and
    `isBackgrounded`. A teammate task literal has no `isBackgrounded` field, so it passes the filter.
- **Consequence:** in an interactive session with `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`, which this user
  has set in `~/.claude/settings.json`, a teammate that FINISHED and went idle stays in `background_tasks` as
  running until it is evicted. Eviction is `evictAfter`. Its constant `X0` is unresolved, eviction can be
  postponed (viewing, sibling hold), and a resumable teammate may never be evicted.
  - The orchestrator usually stops right after a teammate's idle notification. During that window,
    "Now starting backlog #657." with nothing running exits 0 (P1).
  - That is Codex's XB1 world (a builder that finished, then the announcement) reached through (a) instead
    of (b).
- **Why not BLOCKER:** the r1 CM3 headless capture showed a named Agent as `type: subagent`, and it left the
  list. Whether this user's interactive named Agents are `in_process_teammate` tasks, and how long the window
  lasts, is not measured.
- **What would settle it:** one interactive capture of the Stop payload more than 30 s after a named
  teammate goes idle. If it shows `status: "running"`, this is a BLOCKER under rule (1).

### F2 — MAJOR (filed) — a long-lived background server disables the guard for the whole session, and the docstring's justification is false for it

- **Where:** `scripts/check-idle-stop.py:79` ("A background job that only WAITS … counts as running: it will
  wake the session"), `:139-140`.
- **Input:** P2. `background_tasks: [{"type":"shell","status":"running","command":"python3 -m http.server 7391"}]`
  with "Now starting backlog #657." gives exit 0.
- **Why the justification fails:** a server, an explainer page server or a `tail -f` never exits and never
  wakes the session. Once one is started with `run_in_background`, every idle stop for the rest of the session
  is allowed on its first attempt.
- **Why it is realistic:** the agent did not forge anything. The project memory tells the orchestrator to
  restart the owner's explainer server on port 7391 after using it.
- **Fix direction (for the filed row):** do not count a `shell` or `monitor` entry whose command is a known
  server shape, or one older than N hours. Alternatively, state the bound honestly.

### F3 — MINOR (filed) — a payload over 1 MiB allows the stop as NOT CHECKED

- **Where:** `scripts/check-idle-stop.py:231-232, 241-244`, and `bounded_read.MAX_STDIN`.
- **Input:** P6. `last_assistant_message` of 1 MiB + 27 bytes gives exit 1 ("NOT CHECKED … ALLOWED").
- **Note:** the schema caps `description`/`command` at 1000 characters but does not cap
  `last_assistant_message`. One assistant message over 1 MiB is far beyond realistic output, so I record this
  as a bound, not a hole. The docstring's "the ONLY way an unread input allows" (line 12) should name the byte
  bound as well as a non-object.

### F4 — MINOR (filed) — the docstring calls `in_process_teammate` "not captured"; the binary now answers half the question

- **Where:** `scripts/check-idle-stop.py:51-53, 82-83`.
- **Problem:** the bound reads as hypothetical ("one that stayed `running` while idle would over-ALLOW"). The
  status transition in F1 shows that an idle teammate does stay `running` until it is evicted. The bound should
  say so and cite the `isIdle` field the payload omits, so a later reader does not treat it as unlikely.

## Refutation attempts that did not find a BLOCKER

- A string `stop_hook_active` (P7) is judged rather than passed. The schema types the field as a boolean
  (`stop_hook_active:I()`), so this cannot happen from the harness.
- A non-empty `agent_id` on the main session's Stop: the base hook input sets `agent_id: s?.agentId`, which is
  undefined for the main loop, so there is no bypass.
- A malformed `gh` answer, a nested JSON bomb and a FIFO usage cache all BLOCK once or are bounded (P4,
  self-test).

VERDICT: CONVERGED
