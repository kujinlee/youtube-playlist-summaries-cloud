# Round 1 — `agent-long-call-guard` (PR #468, backlog #455) — coordinator — NOT CONVERGED (Codex); REDESIGN to the timeout rule alone

```yaml
round: 1
fixes_nontrivial: true
subject: agent-long-call-guard
halves:
  codex: ran
  claude: ran
findings:
  - {id: C1, severity: Medium, aim: deliverable, fix_induced: false, component: command-patterns, disposition: moot}
  - {id: C2, severity: Medium, aim: deliverable, fix_induced: false, component: command-patterns, disposition: moot}
  - {id: C3, severity: Medium, aim: deliverable, fix_induced: false, component: command-patterns, disposition: moot}
  - {id: C4, severity: Medium, aim: deliverable, fix_induced: false, component: command-patterns, disposition: moot}
  - {id: F1, severity: Low, aim: deliverable, fix_induced: false, component: docstring, disposition: fixed}
  - {id: F2, severity: Low, aim: deliverable, fix_induced: false, component: timeout-reading, disposition: fixed}
  - {id: F3, severity: Low, aim: deliverable, fix_induced: false, component: command-patterns, disposition: moot}
  - {id: F4, severity: Low, aim: deliverable, fix_induced: false, component: test-coverage, disposition: fixed}
  - {id: F5, severity: Low, aim: deliverable, fix_induced: false, component: rollout, disposition: filed}
```

Both halves reviewed head `d41eb9b9`. Codex: **NOT CONVERGED**, four Medium findings, all about the `sleep` and
`gh … --watch` patterns. Claude: **CONVERGED**, five Low findings (F1–F5).

## The design decision, and why

Claude F1 showed that in Claude Code 2.1.309 a foreground Bash call that reaches its timeout is **moved to the
background**, not left blocking, and the turn goes on. I measured it again during this fold, from inside a teammate:
`sleep 130` with no `timeout` returned at 120 s with *"Command did not complete within its 120s timeout and was moved
to the background"*, and the command went on to finish. So a call blocks the turn for at most its **effective
timeout**, whatever command it runs. The default is 120 000 ms. A call can only block past 270 s if its effective
timeout is over 270 000 ms.

Given that, the command-pattern rules did two kinds of wrong. They **refused** calls that could not block past 270 s:
a `sleep 300` under the 120 s default, and Codex C3 and C4. They also **missed** shapes that the timeout rule catches
anyway: Codex C1 and C2, and Claude F3's twelve forms. Making the parser better would only shrink a set of findings
that has no end, for a rule that adds no protection. So the **sleep and watch rules, their 19 cases (4 watch, 15 sleep) and
their 9 mutations are removed**. The effective-timeout rule is the only rule left.

**C1–C4 and F3 are resolved by removal, not fixed** (`disposition: moot`). The code that each one describes no
longer exists.

Backlog row 455's falsifier named `--watch` and `sleep`. It is **narrowed in the row**, with a ⟳ note and the
measurement. The new falsifier is: a subagent's foreground call whose effective timeout is over 270 000 ms is
allowed, OR one at or under it is refused.

## Per finding

- **C1 (quoted / prefixed `sleep` escapes)** — moot. No sleep matcher exists now. `sleep "300"` under the default
  timeout returns at 120 s.
- **C2 (inherited `gh` flags escape watch detection)** — moot, for the same reason.
- **C3 (quoted prose denied)** — moot. No command text is read now.
- **C4 (`--watch=false` denied)** — moot.
- **F1 (the docstring says "killed")** — fixed. The docstring now says the call is moved to the background, and it
  cites the measurement.
- **F2 (env parse unlike the harness's; a traceback on `inf`)** — fixed. The harness's readers come from the
  2.1.309 binary (`strings`; the names are minified):
  - Bash tool: `fn = Math.min(Rt || kQ(), OH(), maxTimeoutMs ?? Infinity)`, where `kQ() = fde()` and
    `OH() = gMe()`.
  - `fde`: `BASH_DEFAULT_TIMEOUT_MS` read by `yu()`. It is used if it is not NaN and is above 0; otherwise 120000.
  - `gMe`: `max(BASH_MAX_TIMEOUT_MS, fde())` when that value is valid and above 0; otherwise
    `max(600000, fde())`.
  - `yu`: the value is trimmed. Up to 32 characters, an exponent form gives `Number()` (NaN if it is not an
    integer) and a thousands form gives its digits. Anything else goes to `parseInt(…, 10)`.
  - The schema's `v0` turns a numeric `timeout` string into a number.

  So `timeout: 0` means the default, a negative timeout cannot block, `1e6` means 1 000 000, `300000ms` means
  300 000, and `inf` means the default. Claude F2's own reading of two cases was wrong: it said `1e6` gives 1 ms,
  but it is an integer exponent form. Its claim that `BASH_MAX_TIMEOUT_MS` false-denies an explicit 600000 is fixed:
  the cap is modelled. A `timeout` that the schema would refuse (`"5m"`, `true`, `null`) is **NOT CHECKED** on
  stderr at exit 1, and so is a `tool_input` that is not an object. Every number is a float, so a 400-digit env
  value is `inf`, not a raise. Also read: `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS` (`Qp()`/`Wye()`) makes a
  `run_in_background` call run in the foreground, so a background call is exempt only when that variable is unset.
- **F4 (clauses no case names)** — fixed. The `then`/`else`/`(` clauses went with `CMD_POS`. The `isinstance(ti,
  dict)` guard now raises NOT CHECKED, and a case names it. Each clause of the timeout reading has a case and a
  mutation. A clause that cannot change a verdict was deleted rather than tested: the `> 0` test on env values,
  and the 600000 cap without `BASH_MAX_TIMEOUT_MS`. The docstring says why.
- **F5 (old worktrees print NOT RUN on every Bash call)** — filed as **backlog #462**, as instructed. Not fixed.

## Evidence after the fold

- Self-test **37/37**.
- `check-plan-code.py --mutate . --only scripts/check-agent-long-call.py`: **29 mutations, 29 killed, 29
  attributed** to the case each one names. The pin `EXPECTED_MUTATIONS` moved from 21 to 29.
- End to end through `run-hook.sh`, as a subagent:
  - `timeout: 300000` → deny JSON at exit 0.
  - `sleep 300` with no timeout → allowed.
  - `timeout: "5m"` with `BASH_DEFAULT_TIMEOUT_MS=inf` → NOT CHECKED at exit 1, with no traceback.

## Bounds stated, not closed

- The settings flag `backgroundTasksDisabled` is not read, because a hook cannot read settings.
- The prompt-shell `shellWallCapMs` path is not modelled.
- `maxTimeoutMs` only lowers the bound.
- An in-process teammate's `agent_id` was established statically (the Claude half's chain), not captured live.
