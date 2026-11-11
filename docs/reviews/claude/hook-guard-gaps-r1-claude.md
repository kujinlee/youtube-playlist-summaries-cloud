# hook-guard-gaps — round 1 — Claude adversarial review

Subject: PR #412, branch `hook-guard-gaps`, head `edf732e8`, `git diff origin/master...HEAD`
(5 files: `scripts/check-hook-commands.py`, `scripts/mutations/check-hook-commands.json`,
`scripts/check-plan-code.py`, `docs/backlog.md`, `docs/dashboard-entries.md`).
Mandate: refute. Every experiment below ran in a `mktemp -d` copy. Nothing in any checkout was edited.

## What I executed (all reproduced)

| Check | Result |
|---|---|
| `check-hook-commands.py --self-test` at head | 25/25, rc 0 |
| live `check-hook-commands.py` at head | rc 0, "13 hook command(s), every one canonical and present" |
| `check-plan-code.py --mutate . --only scripts/check-hook-commands.py` (full copy plus `node_modules/typescript`) | rc 0: 14 mutations, 14 killed, 14 attributed to the case each names, 0 survivors |
| `EXPECTED_MUTATIONS` sum compared with the manifests on disk | declared 2152, actual 2152 |
| `check-selftest-counts.py`, `check-ratchet-contract.py`, `check-docs.py`, `check-dashboard-entry.py` | all rc 0 |
| Known positive: r4's three probes on the real settings, master vs head | master 0/0/0; head 2/2/1, as the PR body says |
| Shape-diagnostic append removed from `problems()` at head | both re-pointed cases go red (`(1, False)`), so the "now assert the diagnostic" claim holds |

## Findings

### F1 — MEDIUM — `KNOWN_TYPES` is missing three hook types the installed Claude Code already supports
`scripts/check-hook-commands.py:52` (and the docstring at :30-33, the PR body, backlog #365's status cell
and the dashboard entry, which all repeat "a type Claude Code ADDS LATER").

**Evidence.** I ran `strings` on the installed binary, `~/.local/share/claude/versions/2.1.309`
(`claude --version` gives 2.1.309). Its hook schema factory returns
`{BashCommandHookSchema, PromptHookSchema, HttpHookSchema, AgentHookSchema, McpToolHookSchema}`, and
the entry schema is `Kr("type",[command, prompt, agent, http, mcp_tool])`, a discriminated union of
**five** types: `command`, `prompt`, `agent`, `http` and `mcp_tool`. The guard knows two.

**Consequence.** This repo's tracked settings use only `command` today, and so do all 229 hook entries
in every `settings*.json` and `hooks.json` under `~/.claude` and `~/code`, so nothing is red now. But
`ci.yml:402` runs the live check. If anyone adds a valid `agent`, `http` or `mcp_tool` hook to
`.claude/settings.json`, CI reports CANNOT RUN. The message reads as if the config is wrong ("a type
this guard does not know"), and the docstring tells the reader such a type is new to Claude Code,
which is false. Failing loudly is the right *direction*. What is wrong is the claim that the set
reflects Claude Code's current surface. Plugin `hooks.json` files are out of scope, because the guard
reads only the tracked settings file.

**Fix.** Set `KNOWN_TYPES = {"command", "prompt", "agent", "http", "mcp_tool"}`. Only `command` is
inspected; the others are skipped as `prompt` is today. Cite the version where the set was read:
"read from Claude Code 2.1.309's hook schema". Change "a type Claude Code adds later" to "a type
Claude Code adds after 2.1.309" in the docstring, the PR body, the backlog row and the dashboard entry.

### F2 — MEDIUM — a non-hashable `type` crashes the guard with exit 1, which means "a violation", not CANNOT RUN. This change introduced it.
`scripts/check-hook-commands.py:83`. The line is `if h.get("type") not in KNOWN_TYPES:`, and a
membership test against a `frozenset` hashes its operand.

**Evidence.** In a temp world with one good command plus a second entry:

| `type` value | head rc | output |
|---|---|---|
| `["command"]` | **1** | `TypeError: cannot use 'list' as a set element (unhashable type: 'list')` |
| `{"a":1}` | **1** | `TypeError: … unhashable type: 'dict'` |
| `null`, `1`, `true`, `"Command"`, `" command"` | 2 | CANNOT RUN with the type named, which is correct |

On `origin/master` the same `["command"]` input does not crash, because `== "command"` is just False
and the entry is skipped. So the crash is new. An uncaught traceback exits 1, the repo's code for
"a violation", rather than 2, CANNOT RUN. That breaks the guard's own contract that anything stopping
the rule from being applied is CANNOT RUN (`check()` docstring, :120). Claude Code's own schema would
reject such a file, so it is unlikely in practice. But this branch exists to close exactly this class:
an unexpected `type` must be Malformed.

**Fix.** Use `t = h.get("type"); if not isinstance(t, str) or t not in KNOWN_TYPES: raise Malformed(...)`.
Add a case with `type: ["command"]` that expects rc 2.

### F3 — LOW — the `prompt` membership has no falsifier: removing it from `KNOWN_TYPES` survives the whole suite
`scripts/check-hook-commands.py:52`, and the case at :199-200.

**Evidence.** A hand mutation, `KNOWN_TYPES = frozenset({"command"})`, gives **25/25 passed**. The
only case containing a `prompt` hook, "ZERO command hooks is CANNOT RUN", expects 2. With `prompt`
unknown it still gets 2, now via Malformed rather than via zero commands. That is passing for an
ambient reason: the expected value does not tell the two causes apart. The 14-mutation manifest has
no entry for this, so `--mutate` cannot see it. Consequence: a future edit could drop `prompt`, and
under F1's fix also `agent`, `http` or `mcp_tool`, and a settings file carrying such a hook would go
CANNOT RUN in CI, with no case going red first.

**Fix.** Add a case with one good `command` plus one hook of each known non-command type, expecting
rc **0**. Re-point the ZERO case to assert its message ("registers ZERO hook commands"). Add a
manifest mutation that drops `"prompt"` from `KNOWN_TYPES`, expecting the new case, and bump
`EXPECTED_MUTATIONS` (15) and the declared sum (2153).

### F4 — LOW — a non-string `UNREGISTERED` reason passes the emptiness check
`scripts/check-hook-commands.py:110`, `if not str(unregistered[f]).strip():`.

**Evidence.** Calling `problems()` directly with reason `None` gives `[]` (accepted, because
`str(None)` is `"None"`), and reasons `0` and `[]` also give `[]`. `""`, `" "` and `"\t\n"` are
refused correctly. The registry is a Python literal in this file, so a non-string reason only
arrives through a code edit. That is why this is LOW. But `str()` turns "no reason" into a
four-letter reason.

**Fix.** Use `r = unregistered[f]; if not isinstance(r, str) or not r.strip():`. Optionally add a
`None` case.

### F5 — LOW, pre-existing and OUT OF SCOPE (file it, do not fold it) — the exec form (`args`) is invisible to the guard
`scripts/check-hook-commands.py:86-90`, which reads only `command`.

**Evidence.** The 2.1.309 schema says that when `args` is present, "`command` is resolved as an
executable and spawned directly with these arguments — no shell". I added `"args": ["--x"]` to the
live `block-idle-stop.sh` entry in a copy, and the guard printed rc **0**, "every one canonical and
present". Claude Code would then try to exec a binary literally named `bash .claude/hooks/block-idle-stop.sh`,
which launches nothing. That is the defect class this guard exists for. `shell: "powershell"` is a
second unread key that changes how the command runs (UNVERIFIED end to end: I did not launch a
session with either). This did not change in this diff.

**Fix.** File a backlog row: refuse a `command` hook that carries `args` or a non-default `shell`, or
treat them as a second shape.

## Attack points with nothing found

- **Case 3 (does each case fail for its named reason):** both new `type` cases go red when the check
  is removed or narrowed (`is None` → the `commmand` case reddens). The empty-reason case goes red
  when the check is removed. Both shape-diagnostic cases go red when the diagnostic is suppressed.
  The one gap is F3.
- **Case 4 (mutations):** 14/14 killed and attributed to the case each names. The total of 2152 is
  real.
- **Case 5 (live):** rc 0 over 13 commands.
- **Case 6 (docs):** the PR body's known-positive figures (0/0/0 → 2/2/1), "25 cases", "14 mutations",
  "13 commands" and the backlog row's ✅ all match what I executed. The one false sentence, repeated
  in all three documents, is F1's "a type Claude Code adds later".

VERDICT: NOT CONVERGED
