# Round 3 — `hook-guard-gaps` — Claude half (confirmation, mandate REFUTE)

Subject: `git diff HEAD~1 HEAD` at `0af1a9f5` (parent `a87232ee`), worktree `wt-365`, branch `hook-guard-gaps`.
Nothing was edited in any checkout. The binary strings were extracted into a `mktemp -d` directory.

## Checks executed

| # | CHECK | RESULT |
|---|---|---|
| 1 | `scripts/check-hook-commands.py` diff is docstring only | ✅ The one hunk is at lines 34–36, inside the module docstring: 2 lines removed, 3 added. `git diff --quiet HEAD~1 HEAD -- scripts/mutations/check-hook-commands.json` gives rc 0, so the mutation file is unchanged. No code or cases changed. |
| 2 | Suite + live check | ✅ `--self-test` gives `29/29 self-test cases passed` with rc 0, read without a pipe. The live check reports `13 hook command(s), every one canonical and present` with rc 0. |
| 3a | `args` prose, against Claude Code 2.1.309 (`claude --version`, binary `~/.local/share/claude/versions/2.1.309`) | ✅ VERIFIED from the binary. The schema says: *"Argument list for exec form. When present, `command` is resolved as an executable and spawned directly with these arguments — no shell."* The runner does `Bn=[bs(e.command),e.args.map(bs)]` and then `Txe(Bn[0],Bn[1],{…})` with no `shell` option. So `bash .claude/hooks/x.sh` would be looked up as a single executable name. The runner code supports "would launch nothing", but nobody ran it end to end. Backlog #368 says so; the docstring does not. |
| 3b | `shell` prose | ⚠ PARTLY FALSE. See CL1. |
| 4a | Backlog #368 row | ⚠ The `args` half is accurate. The `shell` half is CL1. |
| 4b | r2 coordinator record | ⚠ It accurately restates what Codex measured. Its XL1 line repeats the claim in CL1. `check-review-rounds.py` gives rc 0. |
| 4c | Decision-log row | ✅ The last row reads `hook-guard-gaps` / `accrete` / `stopped` / `rounds_at_termination: 2`. Its prediction is unchanged and only `outcome`, `observed` and the count were filled in. `check-decision-scheme.py` gives rc 0. ℹ `check-review-decision.py` exits 1 with `ROUND_OWED — r1 left a defect open (disposition 'filed')`. That is expected: this round is the owed round. |
| 4d | Five hook types (restated in the record) | ✅ Re-verified. The hook-schema factory returns `{BashCommand, Prompt, Http, Agent, McpTool}HookSchema`, and the union is `Kr("type",[e,n,s,r,i])`. Its type literals are exactly `command, prompt, mcp_tool, http, agent`. |

## Findings

**CL1 — Low (prose, `component: prose`, fix-induced: yes, caused by the r2 fold).** The corrected `shell` prose says a
non-default `shell` gives a *different* failure from `args`. Backlog #368 says it would *"misbehave rather than not
launch"*. The coordinator's XL1 line says the earlier "launches nothing" claim *"does not"* hold. The 2.1.309 runner shows
that this depends on the machine:

- **No PowerShell on PATH.** On this machine `which pwsh powershell` finds nothing (rc 1). The runner then throws
  `Hook "…" has shell: 'powershell' but no PowerShell executable (pwsh or powershell) was found on PATH.` So the
  hook **launches nothing**. That is the claim r2's fold removed, and it is the case for this repo's dev machine.
- **PowerShell present.** The runner spawns pwsh on `<command> ; if (-not $?) { if ($LASTEXITCODE -eq 2) { exit 2 } }`.
  The canonical command `bash .claude/hooks/x.sh` has no bash-only syntax. It invokes `bash` from PATH, and exit code 2
  is passed through. So the hook would most likely **work**, not "misbehave". UNVERIFIED: no pwsh here to run it.

One more detail: the docstring says "`powershell` runs the command through `pwsh`". The runner also accepts a `powershell`
executable, which is in the error text above. That is minor.

Fix (prose only): in the docstring and #368, say that `shell: "powershell"` either fails to launch (no PowerShell on PATH,
as on this machine) or runs the canonical command through PowerShell, where it probably still works (not executed). Drop
"misbehave rather than not launch". The FALSIFIER and the proposed fix in #368 (refuse a non-default `shell`) stay
reasonable as a shape rule.

**CI1 — Info.** The decision-log row records `rounds_at_termination: 2` and `outcome: stopped`, but this confirmation
round 3 runs after it. This is consistent if a confirmation round is not counted as a round of the unit. It is noted
only so the owner can confirm that convention.

## What did not refute

- Item 1, docstring-only: held.
- Item 2, 29/29 and the live check: held.
- The `args` mechanism: held. It is now read from the runner code, not only the schema text.
- The five-type set: held.
- The verdict JSON (`gate_ran: true`, head `a87232ee`): consistent with the review it names.

VERDICT: NOT CONVERGED
