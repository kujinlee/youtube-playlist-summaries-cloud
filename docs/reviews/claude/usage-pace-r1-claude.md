# Round 1 — usage-pace — claude

Branch `usage-pace` (PR #446) at `6fe44eb8`, against `origin/master`. Mandate: REFUTE. Scope, as briefed: whether
the hooks FIRE, whether the override can be reached from a worktree, and what the owner actually sees. Codex covers
the arithmetic. I edited nothing in the tree. All experiments ran in a scratch world under
`scratchpad/r399/`: a fake main checkout (`.git` directory), a fake linked worktree (`.git` file), `.remember/.git`,
and a redirected `HOME`, with the shipped `run-hook.sh` and hooks copied in.

## Gates run

| Check | Result |
|---|---|
| `python3 scripts/check-usage-pace.py --self-test` | **79/79**, 1.6 s |
| `python3 scripts/check-plan-code.py --mutate . --only scripts/check-usage-pace.py` | **27/27 killed, 27 attributed, 0 survivors**, 32 s (a scoped diagnostic, not the full gate) |
| A hand mutation outside the manifest (`localtime` → `gmtime`) | **SURVIVES**, 79/79. See m2 |
| Hook latency, 20 runs each through `run-hook.sh` | prompt median **66 ms** (max 77), spawn median **67 ms** (max 83), Python 3.14.4 |

## (1) Do the hooks fire? What I verified and what I inferred

- **VERIFIED: the tool is named `Agent`.** In this session's transcript, `tool_use` names are `Agent` 220 times
  and `Task` 0 times. A recorded hook attachment is labelled `"hookName": "PreToolUse:Agent"` (a plugin hook,
  2026-10-22), so the harness matches PreToolUse on the name `Agent`. The repo's existing plan gate already uses
  the matcher `Agent|Skill` (`.claude/settings.json:22`). Claude Code is 2.1.309.
- **VERIFIED: the hook ignores the payload.** Both hook scripts give the checker `</dev/null`, so the payload shape
  (`subagent_type: "fork"`, a missing `tool_input`, anything else) cannot change the verdict. I drove the spawn
  hook through `run-hook.sh` with a realistic PreToolUse payload (`permission_mode`, `tool_input.subagent_type:
  "fork"`): at 95% the result was a deny, rc 0. This is correct, and it means payload variation is not a risk.
- **INFERRED, NOT VERIFIED: the harness honours `permissionDecision: "deny"` in this session's permission mode.** The
  transcript records the mode as `auto`. It contains **no** recorded PreToolUse denial at all, so I have no
  observed denial of a real tool call. The docs say a deny applies in every mode; I did not see it happen.
- **INFERRED: the hook fires on an `Agent` call made by a subagent.** Not observed.
- **VERIFIED: a session whose cwd is under `.remember/` runs the spawn hook NOT RUN, so a 95% spawn is allowed**
  (`run-hook: NOT RUN usage-pace-spawn.sh …`, rc 1). This is `run-hook.sh` limit L4, which is already written down,
  so it is a bound and not a new finding.

## Findings

### M1 — Major — The gate blocks the cheap path and leaves the expensive one open, which pushes work onto the cost this PR exists to cut

`.claude/settings.json:31` (matcher `Agent` only); `scripts/check-usage-pace.py:147-149` (the REFUSE text).

`docs/process-checklists.md` → *Agent lifetime*, the measurement this PR's row cites: **69.5%** of weighted usage
came from long-lived teammates that were *woken again*, while fresh subagents were **4.3%**. Waking a finished agent
is a `SendMessage` (the transcript has 261 `SendMessage` calls against 220 `Agent` calls). No hook matches
`SendMessage` (`grep SendMessage .claude/settings.json` finds nothing).

**Concrete input:** the cache says weekly 95%. The coordinator calls `Agent` and is denied with *"NEW subagent
spawns are REFUSED … work in flight continues"*. The coordinator's obvious next move is
`SendMessage({to: "b2-implementer", …})` to a finished agent, which resumes it from its transcript. That spends a
full-context cache rewrite, the 69.5% kind, and nothing refuses it. The text even invites it, because a woken agent
feels like "work in flight". So at 90% the gate steers the coordinator **toward** the behaviour *Agent lifetime*
forbids.

This falls inside the row's literal wording ("refuses NEW subagent spawns"), so it is a spec gap. It is not an
implementation slip. It still passes the row's falsifier while missing its purpose. **Proposed fix:** at minimum,
the REFUSE text (and the WARN text) should say that waking a finished or parked agent with `SendMessage` is also off.
The owner should decide whether a `SendMessage` matcher should add the same context or deny. Waking a *running*
agent cannot be told apart from waking a finished one by the payload alone, so a deny there would need more design.

### M2 — Major — The override is handed to the agent it refuses, never expires, and is not gitignored

`scripts/check-usage-pace.py:70-71, 147-149, 169-170`.

- The deny's `permissionDecisionReason` goes to **the model**. It ends with
  `override: ALLOW_SPAWN_OVER_LIMIT=1, or touch .claude/allow-spawn-over-limit.` In `auto` mode a single Bash
  `touch` turns the gate off. The docstring calls it "the owner's override", but nothing makes it the owner's. Compare
  the repo's push escapes, where the escape is a per-command prefix that a reviewer can see in the very command it
  authorises. This one is a persistent file, made by a separate call.
- **It never expires.** The file is a bare existence test (`os.path.exists`). Once touched, it disables REFUSE for
  every later week as well. The only reminder is the "(The override is ACTIVE …)" suffix, and that appears only at
  REFUSE.
- **It is not ignored:** `git check-ignore -v .claude/allow-spawn-over-limit` exits 1. A `git add -A` (which this
  repo's memory records as a real, repeated incident) commits it, and then every clone and every new worktree is
  overridden on arrival.
- **The env half cannot be reached mid-session (inferred).** Hooks inherit Claude Code's launch environment, so an
  `export ALLOW_SPAWN_OVER_LIMIT=1` in a Bash call never reaches the hook. An agent that tries the first hint will fail
  and move on to the second one.

**Proposed fix:** gitignore the file. Have it record the `resets_at` it was granted for, and treat it as inactive once
that reset has passed (one `json.loads`, which the checker already does). Word the hint to the owner, not the agent
(e.g. "ask the owner to …").

### M3 — Major — A valid weekly ≥ 90% is let through when the display code crashes, and the prompt goes silent too

`scripts/check-usage-pace.py:79` (`local_time`), reached from `:141`, `:145`, `:148`. Nothing catches it.

These were driven through `run-hook.sh` with `HOME` redirected, and the weekly value was a valid **95** each time:

| Cache | spawn hook | prompt hook |
|---|---|---|
| `seven_day.resets_at: 1800086400000000000` (nanoseconds) | rc 1, no output: **ALLOWED** | rc 1, **no notice** (`OSError: [Errno 22]`) |
| `five_hour: {used_percentage: 95, resets_at: 1e300}` | rc 1, no output: **ALLOWED** | rc 1, **no notice** (`OverflowError`) |
| `five_hour.used_percentage: "n/a"` | rc 0, no output: **ALLOWED** (CANNOT RUN) | rc 0, CANNOT RUN notice |

The first two match the row's own FAILS IF exactly: *"with the cache at 90% or more, a new subagent spawns without
an override"*. They are also worse than CANNOT RUN. The design promises that a broken cache is LOUD. Here the checker
crashes, and the owner gets a hook-error line on stderr instead of the `⚠ CANNOT RUN … treat this as NOT RUN` line.
The third row is the designed CANNOT RUN, and it is in the brief's list. It still contradicts the docstring's *"the
five-hour window can only add a warning"* (`:14`): a corrupt five-hour window **disables** a valid weekly REFUSE.

**Proposed fix:** bound `resets_at` before formatting. A seven-day reset more than 7 days (plus slack) ahead is
CANNOT RUN, and so is a five-hour reset more than 5 hours ahead. That also catches a millisecond-unit reset, which
today reads as REFUSE "Resets Sat 06-20" and can never trip the past-reset guard. Catch `(OverflowError, OSError,
ValueError)` in `local_time` as a last resort. Consider letting a malformed five-hour window drop only its own note
rather than the weekly verdict. That is the owner's call, given the brief lists "malformed" as CANNOT RUN.

### m1 — Minor — The override from the main checkout does not apply while the session's cwd is in a worktree, and the hint does not say which checkout

`scripts/check-usage-pace.py:71, 170`; `.claude/hooks/usage-pace-spawn.sh:11`.

**VERIFIED.** With `.claude/allow-spawn-over-limit` touched in the **main** checkout and the hook launched from the
**worktree** cwd, the result was still a deny. From the main cwd it allowed. `run-hook.sh` picks the checkout from
the session's physical cwd, and the hook's `REPO_ROOT` is that checkout. The hint says `touch
.claude/allow-spawn-over-limit` as a relative path, so an owner who does what it says in their usual terminal (the
main checkout) gets no effect while a coordinator works from a worktree. The failure is closed, not open, hence
Minor. **Fix:** print the absolute path, `os.path.join(root, OVERRIDE_FILE)`.

### m2 — Minor — The "local time" cases are tautological: a UTC display survives 79/79

`scripts/check-usage-pace.py:293, 296, 338`.

The cases assert `local_time(WEEK_RESET) in message`, using the very function under test. Replacing `time.localtime`
with `time.gmtime` at `:79` (so a UTC time is labelled "local") gives **79/79 green** under
`TZ=America/Los_Angeles`. **Fix:** an independent expectation. Set `TZ` and call `time.tzset()` in the case, then
compare against a literal, for example a reset at 2026-11-02 17:00 UTC shown as `Mon 11-02 09:00 local`. I verified
that this exact pair is correct today, across the 2026-11-01 DST change, so DST handling itself is right
(`localtime` uses the reset instant's offset).

### m3 — Minor — `89.9999999` is shown as "90%" under WARN

`scripts/check-usage-pace.py:83` (`f"{p:g}"`). Input `used_percentage: 89.9999999` → `WARN: … weekly usage is 90%
(WARN at 80%; new spawns are refused at 90%)`. The message contradicts itself. `79.9999999` is OK and silent, which
is correct. **Fix:** truncate rather than round, e.g. `math.floor(p * 10) / 10`.

### m4 — Minor (inferred) — The owner may never see WARN or REFUSE: it goes into the model's context only

`scripts/check-usage-pace.py:176`. `additionalContext` is added to the model's context, and the docs describe it as
shown discreetly, not as a user-facing line. I did not observe how 2.1.309 renders it. The owner's stated problem is
being surprised by the halt, so the 80% WARN reaches the owner only if the coordinator chooses to relay it. **Fix
(owner's call):** also set the hook output's `systemMessage` (shown to the user) at WARN, REFUSE and CANNOT RUN.

## (3) The owner's experience: the exact text, and whether each is actionable

- **WARN** (85%): `⚠ usage pace: weekly usage is 85% (WARN at 80%; new spawns are refused at 90%). Resets Mon 11-02
  09:00 local.` It is clear and dated, but it has **no action**. It never says what pacing means here (finish in-flight
  work, do not wake parked agents). That ties back to M1.
- **REFUSE** (95%): `⛔ usage pace: weekly usage is 95% — NEW subagent spawns are REFUSED (at 90%); work in flight
  continues. Resets Sat 10-31 07:06 local; override: ALLOW_SPAWN_OVER_LIMIT=1, or touch
  .claude/allow-spawn-over-limit.` It is actionable, but for the wrong reader (M2), the path is ambiguous (m1), and
  it says nothing about `SendMessage` (M1).
- **CANNOT RUN**, missing: `… CANNOT RUN — no cache at <abs path> (the statusline writes it). The weekly usage is
  UNKNOWN: treat this as NOT RUN, never as fine. Spawns are not blocked.` This one is actionable.
- **CANNOT RUN**, stale: `… the cache is N min old (stale past 15 min); the statusline has not refreshed it.` It is
  half actionable, because it does not name the file to check (`~/.claude/statusline.sh`) or its path. ⚠ On a
  clone with no such statusline (this repo is public, and `docs/portable-practices.md` exports the harness), this
  line is added to **every** prompt, forever. That is a gate red from birth, which this repo's own rule (backlog #56)
  predicts will be ignored.
- **A crash** (M3) prints a Python traceback through the hook-error channel and none of the above.

## (2) Prompt latency

The prompt hook measured **66 ms median** (77 ms max) over 20 runs through `run-hook.sh`. Most of that is interpreter
start-up plus `site`/`sitecustomize` (13.4 ms of imports by `-X importtime`); the checker's own work is negligible.
I judge this **acceptable**: it is below what a person notices on submitting a prompt, and the hand parser that
replaced argparse is a sound saving. It cannot block, because every non-zero exit is mapped to 1, and that is
verified both by the self-test's `sys.exit(2)` cases and by my crash runs (rc 1).

## Verdict

**NOT CONVERGED** — 3 Major (M1 spec gap, M2 override, M3 crash lets 95% through), 4 Minor. No Blocking.
