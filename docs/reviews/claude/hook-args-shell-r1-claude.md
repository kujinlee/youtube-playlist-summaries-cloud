# Round 1 — hook-args-shell — claude

Subject: PR #414, branch `hook-args-shell`, head `6120318e` (diff `origin/master...HEAD`), backlog #368.
Verified against: Claude Code **2.1.309** (`/Users/kujinlee/.local/bin/claude -> ~/.local/share/claude/versions/2.1.309`,
`claude --version` → `2.1.309 (Claude Code)`). Every experiment ran in a `cp -R` copy
(`scratchpad/r368.hzUO/wt`); the worktree was not touched.

Baseline, executed in the copy:
- `python3 scripts/check-hook-commands.py --self-test` → `33/33 self-test cases passed`
- `python3 scripts/check-hook-commands.py` → `ok — .claude/settings.json: 14 hook command(s), every one canonical and present`, rc 0
- `python3 scripts/check-plan-code.py --mutate . --only scripts/check-hook-commands.py` → `19 mutation(s), 19 killed, 19 attributed to the case each names, 0 survivor(s)`, rc 0

## The installed schema (what I could and could not verify)

Read from the 2.1.309 binary (`python3` over the raw bytes, offset 227975368, the `_s()` hook schema). The
`type: "command"` object has exactly these fields:
`type, command, args, if, shell, timeout, onFailure, statusMessage, once, async, asyncRewake, rewakeMessage, rewakeSummary, cloud`.
Their descriptions, quoted:
- `args`: "When present, `command` is resolved as an executable and spawned directly with these arguments — no shell." — **confirms** the row.
- `shell`: enum `["bash","powershell"]`; "'bash' uses your $SHELL (bash/zsh/sh) … **Defaults to bash** (powershell on Windows without Git Bash)."
- `if`: "Only runs if the tool call matches the pattern."
- `once`: "If true, hook runs once and is removed after execution"
- `async`: "If true, hook runs in background without blocking"; `asyncRewake`: "Implies async."
- `onFailure`: `continue` (default) / `block`; "Ignored for async hooks".
- `timeout`: seconds; `cloud`: `device`/`skip` (internal); `statusMessage`: spinner text.

Verified: the field list and descriptions (schema text). NOT verified: runtime behaviour of any field
end to end (no hook was launched under a mutated setting). I did not inspect group-level `matcher`.

## Medium

### M1 — `once`, `async` and `asyncRewake` silently disable a gate and the guard passes them; the docstring now claims a general rule it does not implement
`scripts/check-hook-commands.py:127-129` — the new docstring says the rule is "a command hook carrying a field
that changes HOW its command runs", and the module docstring (`:34-36`) and the dashboard entry
(`docs/dashboard-entries.md`, last entry: "refuses two settings that would make a hook run differently from how the
rest assume") read the same way. Only `args` and `shell` are covered. Probe (`scratchpad/r368.hzUO/probe.py`: set each
field on the live `block-default-branch-push.sh` hook in the copy's real `.claude/settings.json`, run the CLI):

```
if Bash(echo *)   (0, 'ok — ... 14 hook command(s), every one canonical and present')
once True         (0, 'ok — ...')
async True        (0, 'ok — ...')
asyncRewake True  (0, 'ok — ...')
timeout 0.001     (0, 'ok — ...')
onFailure continue(0, 'ok — ...')
shell bash        (1, "... carries `shell` ...")
args []           (1, "... carries `args` ...")
```

According to the schema text, `async: true` stops the push gate blocking and `once: true` removes it after its first
run. Either one stops the repo's most important hook from gating, and the guard reports "every one canonical". That
is the same class of problem as #368 (the hook is not run the way the registration shape assumes), and it is
**stronger** than `args`: `args` makes the hook fail to launch, while these make it look as though it ran.
`if` and `timeout` are the hard cases. The live settings already use `if` on 3 hooks (`.claude/settings.json:9,15,56`)
and `timeout` on the SessionStart hook, so a blanket refusal would be wrong. A pattern that cannot match the gated
command (`"if": "Bash(echo *)"` on the push gate) disables the gate just as completely.
**Route:** either refuse `once`/`async`/`asyncRewake` now, since none is used here (the same justification #368 gave
for `args`), or narrow the docstring and dashboard wording to "args and shell" and file the rest, with `if` and
`timeout`, as a backlog row with this probe as its falsifier. As shipped, the docstring states a rule the code does
not implement.

### M2 — the traversal in `execution_overrides` is a second copy of `hook_commands`' walk, and the suite tests only one event and one group
`scripts/check-hook-commands.py:131-134`. Every new case builds `{"hooks": {"Stop": [ {one group} ]}}`. I ran my own
mutations of the new function, each through `--self-test` on a mutated copy (`scratchpad/r368.hzUO/mut.py`):

```
A truthiness: key in h -> h.get(key): rc=1 KILLED
B drop args from set: rc=1 KILLED
C continue->break (stop at first non-command hook in a group): rc=0 SURVIVED
D first group only (groups[:1]): rc=0 SURVIVED
E first event only (items()[:1]): rc=0 SURVIVED
F one finding per hook (break after append): rc=0 SURVIVED
G drop the message text, keep the count: rc=1 KILLED
```

C, D and E are real regressions. Under each one, a command hook carrying `args` that sits after a prompt hook, in a
second matcher group, or under a second event is passed. The live file has 2 events and many groups. The pure case at
`:204-206` happens to put the `prompt` hook LAST, so `break` and `continue` cannot be told apart there. F is close to
equivalent: the exit code is unchanged and only one of two findings is lost on a hook carrying both keys. That is
noted, not a defect.
**Fix:** add one case with the override in a second event and a second group, placed after a non-command hook. Better,
collect overrides inside `hook_commands`' own loop so there is one walk (memory: *a second implementation of one rule
drifts*). Add the C/D/E mutations to the manifest.

## Low

### L1 — `shell: "bash"` is the schema's DEFAULT, yet it is refused with "which changes how the command runs"
`scripts/check-hook-commands.py:124,137-138`, and the self-test asserts it at `:205` (`"shell": "bash"` counted as a
finding). The schema says "Defaults to bash", so on POSIX `shell: "bash"` should behave the same as no `shell` (per the
schema text; not run). The emitted message is therefore false for that input. The backlog #368 row's own **Fix**
column still reads "refuse … a `shell` other than the default". The status cell says "carrying `args` or `shell`".
The row now contradicts itself. Refusing any `shell` is the safe direction and simpler (it is one shape). The fix is
to say so: reword the Fix cell and the message, e.g. "carries `shell` — the one shape omits it".

### L2 — a comment has been separated from the code it explains
`scripts/check-hook-commands.py:261-262`: "⚠ An INDEPENDENT copy of the schema's types, not derived from
KNOWN_TYPES …" now sits directly above the new `for key, val in (("args", []), ("shell", "powershell")):` loop (`:263`),
not above `others = [...]` (`:268`), which is the code it describes. Move the new loop above the comment.

### L3 — the dashboard entry is dated 2026-10-26, but the work and the row are 2026-10-27
`docs/dashboard-entries.md:17816` `## 2026-10-26`, appended after a `## 2026-10-27` entry (`:17801`). Commit `a31b9a9c` is
dated `Tue Oct 27 01:04:35 2026`, and the backlog row says "FIXED 2026-10-27".

## Checked and not a finding

- **Robustness.** `execution_overrides` runs only after `hook_commands` accepts the structure. I built `hooks: null`,
  `hooks: [..]`, a non-dict group, `hooks` as a dict, a non-dict hook, groups as a dict, and a group missing `hooks`.
  All returned `(2, [CANNOT RUN …])` through `check()`, with no traceback. `"args": null` and `args`+`shell` on one hook
  return rc 1 with the right lines. A direct call on unvalidated input would crash, but the docstring forbids that
  and the only caller complies.
- **Ambient passes in the new cases.** The two `check()` cases assert the specific message text `carries \`{key}\``,
  not just rc 1, and mutation G confirms they need that text. The 2-finding pure case is killed when the type filter
  is dropped (manifest #19) and when `args` is dropped (my B).
- **The prose numbers are true.** 33 cases (run), 19 mutations / 3 new (manifest and harness), 14 live commands (CLI),
  and `EXPECTED_MUTATIONS` +3 → 2206. The PR body's claims are true *as far as they go*. Its "Two optional fields … would
  change how that command actually runs" is right for those two fields, but implies the list is complete; see M1.
- **The `args` claim in the row and docstring** ("spawns `command` as ONE executable with no shell") matches the
  2.1.309 schema description quoted above.

VERDICT: NOT CONVERGED
