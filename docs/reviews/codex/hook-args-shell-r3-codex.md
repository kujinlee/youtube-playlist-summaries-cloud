<!-- codex-review: model=gpt-6.1-sol -->

Review of `6abb8ff3`, mandate **REFUTE**. Repository unchanged; experiments ran in `/tmp/hook-r3.2ThUAk`.

**Medium — one case still passes for an ambient reason, losing the recorded bet.**

At `scripts/check-hook-commands.py:262–263`, “a malformed hooks block is CANNOT RUN, not a crash” checks only exit code 2 against:

```json
{"hooks":{"Stop":{"hooks":[]}}}
```

I reran the round-2 mutation replacing the non-list-event `raise Malformed(...)` with `continue`. This case **still passes**: skipping the malformed event leaves ZERO commands, which independently returns 2.

The new companion case correctly fails, yielding **41/42** overall. The regression is caught, but the older case still does not establish its named reason. The bet explicitly excludes *any case passing for an ambient reason*. Assert the specific malformed-event diagnostic here, or replace this redundant case with the companion fixture.

The other round-2 mutations now fail appropriately:

- Rejecting every second group fails the traversal case with `RAISED` versus expected `("PreToolUse", "once")`.
- Skipping non-string commands fails the new companion case.
- Suppressing command-shape findings fails both diagnostic assertions.

**Installed Claude Code 2.1.309: schema and executed loads**

I inspected its embedded schema and executed isolated `SessionStart` registrations with scripts that write marker files.

| ACCEPTED field | Installed schema |
|---|---|
| `type` | Required literal `"command"` |
| `command` | Required string |
| `statusMessage` | Optional string; empty accepted |
| `if` | Optional string; empty accepted |
| `timeout` | Optional positive number; integer or float, boolean refused |

Executed results:

| Probe | Guard | Claude load / marker |
|---|---:|---|
| `statusMessage: {}` | 1 | Entry rejected; no marker |
| `statusMessage: ""` | 0 | Accepted; marker written |
| `if: ""` | 0 | Accepted; marker written |
| `if: 3` | 1 | Entry rejected; no marker |
| `timeout: true` | 1 | Entry rejected; no marker |
| `timeout: -1` or `0` | 0 | Entry rejected; no marker |
| `timeout: 1.5` | 0 | Accepted; marker written |
| `timeout: 1e100` | 0 | Accepted; marker written |
| Extra group keys, including execution-control names | 0 | Accepted; marker written |
| Group `matcher: {}` | 0 | Group rejected; no marker |
| Empty group `hooks: []` beside a valid group | 0 | Accepted; valid hook writes marker |

Timeout values and group matcher are declared exceptions, so those mismatches do not refute the production boundary.

These were real loads and hook executions before authentication failed. I could not complete an authenticated model turn. An interactive attempt stopped at first-run onboarding; I did not reproduce round 2’s interactive whole-file rejection. In print mode, this installation reports malformed **entries skipped**, with the rest of the file effective.

**Remaining evidence and documentation**

- Baseline: **42/42** cases; live check: **14 commands**.
- Requested mutation command: **30 killed, 30 attributed, zero survivors** after copying the required TypeScript dependency into the temporary tree.
- Independent audit: all 30 mutants had single-match anchors, compiled, failed their named cases, and produced no traceback. The kills are real.
- Repeated field probes refuse `args`, both shell values, `async`, `asyncRewake`, `once`, and the four previously UNCLASSIFIED fields. `timeout: 0.001` and restrictive `if` values still pass within the bound.
- Repeated malformed-shape probes beside a valid command return CANNOT RUN without crashing.

The docstring, backlog row, dashboard entry, and PR body accurately report counts and policy, with two qualifications: references to `FIELD_POLICY` are stale—the implementation uses `ACCEPTED`/`REFUSED`—and the PR’s “falsifier is two cases” remains imprecise: its `powershell` literal is tested using `bash`. The whole-file rejection account describes round-2 evidence; print-mode behavior observed here skips individual entries.

I found no additional production counterexample outside the declared bound. The ambient-reason case nevertheless falsifies the explicit round-3 bet.

VERDICT: NOT CONVERGED
