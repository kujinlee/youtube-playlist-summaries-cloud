<!-- codex-review: model=gpt-6.1-sol -->

Review of `a87232ee`, mandate **REFUTE**. Repository unchanged; experiments ran in a `mktemp -d` copy.

**Low — the documented `shell` failure mechanism is inaccurate.**  
`scripts/check-hook-commands.py:34` says a canonical command with `args` **or a non-default `shell`** runs “as an executable with no shell.” The installed Claude Code 2.1.309 schema distinguishes them: `args` selects direct execution; absent `args`, the command runs through a shell, and `shell: "powershell"` selects `pwsh`. Backlog #368’s title likewise asserts both launch nothing, although its evidence establishes only the `args` mechanism.

Executed probes confirm the guard accepts both `args: []` and `shell: "powershell"` with exit **0**. They do not establish that both fail identically. Correct the docstring and qualify #368’s shell claim. PowerShell execution was not tested; `pwsh` is unavailable here.

The ACCRETE implementation otherwise survived the requested checks:

- **Five-type set verified locally:** `claude --version` reports **2.1.309**. Its installed executable’s hook-schema factory defines `command`, `prompt`, `agent`, `http`, and `mcp_tool`, then combines exactly those five in the discriminated union.
- Appending `agent`, `http`, or `mcp_tool` separately: **0** each. List, object, number, and null `type`: **2**, with the type-specific CANNOT RUN diagnostic and no crash. Missing and unknown types also return **2**.
- Reasons `None`, `0`, `False`, `[]`, `{}`, empty string, and whitespace: **1**, specifically for the empty/invalid reason. A written string passes.
- **29/29 cases pass.** Captured findings match their named conditions. Suppressing the shape diagnostic makes both strengthened divergence cases fail despite their remaining registry violation.
- **16/16 mutations are real:** each replacement matched once, compiled, and produced its named failing case without a traceback. The repository mutation runner independently reported **16 killed, 16 attributed, zero survivors**, with green control and re-control.
- Baseline probes reproduce **0/0/0 → 2/2/1**. The current check accepts all **13 commands**.

The live PR #412 body, backlog #365, and dashboard counts and probe claims reproduce. Backlog #368 correctly records the accepted `args` gap and labels its end-to-end behavior unverified; its shell assertion and the guard’s corresponding explanation need correction.

VERDICT: NOT CONVERGED
