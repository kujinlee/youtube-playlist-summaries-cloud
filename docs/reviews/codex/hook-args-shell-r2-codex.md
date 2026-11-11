<!-- codex-review: model=gpt-6.1-sol -->

Review of `396a7578`, mandate **REFUTE**. Repository unchanged; experiments ran under `/tmp/hook-r2.cwmgwW`.

**Medium — an accepted `statusMessage` value disables the settings file, outside the declared bound.**  
`scripts/check-hook-commands.py:136,154–157` accepts this canonical hook:

```json
{
  "type": "command",
  "command": "bash .claude/hooks/x.sh",
  "statusMessage": {}
}
```

With `x.sh` present and an empty exemption registry, `check()` returns **0**, “every one canonical and present.”

I then invoked installed Claude Code **2.1.309** against that temporary settings file. Before the invocation timed out, Claude emitted:

> These settings files did not load, so nothing in them is in effect, including hooks and permission rules.

It specifically identified `statusMessage` as expecting a string and receiving an object. This is an executed loader rejection, not an inference from the schema. The command never becomes an effective registration.

The declared exceptions cover `timeout`/`if` values and group `matcher`; they do not cover `statusMessage`. Validate this accepted field’s type and add a regression case.

**Medium — the new wrapper lets the traversal case pass for an exception instead of its named finding.**  
`scripts/check-hook-commands.py:201–207` converts `Malformed` into a one-element findings list. The second-event/second-group case asserts only that the list has length one.

I applied this mutation in the temporary copy:

```python
for index, g in enumerate(groups):
    if index:
        raise Malformed("second group incorrectly rejected")
```

**All 38 cases still passed.** The traversal case receives `["RAISED …"]`, counts one, and reports success without finding the refused field. Actual multi-group settings become CANNOT RUN.

Two additional regressions also survived all 38 cases: skipping non-list event groups and skipping non-string commands. Those weaken the old validation contract. Assert the expected finding text and explicitly test malformed entries beside a valid command, so ZERO commands cannot supply the rejection.

The `field_problems.settings` EXEMPT explanation is mechanically honest: there are four distinct `fp()` call sites, plus variation through `check()`, and the variation checker passes. Its rationale does not make the exception-to-finding conversion sound.

Other executed results:

- **38/38 baseline cases pass**; the live check passes over **14 commands**.
- The requested mutation command reports **25 killed, 25 attributed, zero survivors**. Independently applying each mutation confirmed one replacement match, successful compilation, its named failing case, and no traceback. These are real kills; they do not establish that every case fails for its named reason.
- I read all **14 command-hook schema fields** from the installed 2.1.309 executable: `type`, `command`, `args`, `if`, `shell`, `timeout`, `onFailure`, `statusMessage`, `once`, `async`, `asyncRewake`, `rewakeMessage`, `rewakeSummary`, `cloud`.
- Repeated probes refuse `args`, `shell`, `async`, `asyncRewake`, and `once`; `onFailure`, `rewakeMessage`, `rewakeSummary`, and `cloud` are refused as UNCLASSIFIED. `timeout: 0.001` and restrictive `if` values pass within the declared bound.
- The installed group schema exposes only `matcher` and `hooks`. Group-level probes with execution-control names pass the guard, but I found no supported execution control there beyond the declared `matcher` exception.
- Comparing old and new `hook_commands` across **52 shapes** produced identical results. Current validation still refuses the requested malformed groups, entries, missing `hooks`, non-string commands, and unknown types. No tested structure crashed `check()`.
- The docstring, backlog row, dashboard entry, and live PR body accurately report the counts and blanket-shell policy. Their stated boundary is incomplete because of the `statusMessage` counterexample. The “row’s falsifier is two cases” claim is also imprecise: its shell literal is `powershell`, while the suite uses `bash`.

VERDICT: NOT CONVERGED
