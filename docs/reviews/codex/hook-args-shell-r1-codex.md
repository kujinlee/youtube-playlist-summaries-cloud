<!-- codex-review: model=gpt-6.1-sol -->

Review of `6120318e`, mandate **REFUTE**. Repository unchanged; all experiments ran in a `mktemp -d` copy.

**Medium — the override set is incomplete under its stated “HOW the command runs” contract.**  
At `scripts/check-hook-commands.py:124–139`, only `args` and `shell` are refused. Executed probes adding `timeout: 0.001`, `async: true`, `if: "false"`, or `once: true` to an otherwise canonical command each return **0**.

The installed Claude Code reports **2.1.309**, exactly the targeted version. Reading its executable establishes:

| Field | Verified installed behavior |
|---|---|
| `timeout` | Per-command timeout |
| `async` | Runs in background without blocking |
| `if` | Filters execution; runner code explicitly skips nonmatching hooks |
| `once` | Runs once, then is removed |
| `statusMessage` | Changes spinner text; no execution change established |
| `env`, `cwd` | Absent from the command-hook schema; could not verify these as supported per-hook overrides |

The schema additionally exposes `asyncRewake`, `onFailure`, and `cloud`, affecting background execution, failure handling, or execution eligibility. Probes adding each also return **0**. These are installed-code observations, not end-to-end Claude execution tests.

The narrow backlog #368 falsifier is satisfied, but the broader execution-control framing needs either enforcement or an explicit boundary identifying the accepted controls.

**Low — refusing every `shell` value overstates the documented mechanism.**  
A canonical command with `shell: "bash"` returns **1**, and the combined self-test deliberately exercises that value. The installed schema identifies `bash` as the POSIX default. Explicitly selecting that default does not establish a different execution mechanism. The docstring’s “either way it is not run the way … assumes” and PR body’s assertion that either field changes execution are therefore too strong. Blanket refusal can be a policy, but should be described as one.

The remaining requested attacks did not produce a defect:

- **No non-dict crash through `check()`.** Hook elements `null`, integer, list, boolean, and string each return **2**, naming the malformed element. None is accepted by `hook_commands`.
- **Ordering is safe.** Replacing `execution_overrides` with a throwing sentinel still gives **2** for those malformed inputs without reaching the sentinel. Validation completes before the override scan.
- **Non-command hooks remain accepted.** A prompt hook carrying both `args` and `shell`, beside a canonical command, returns **0**.
- **33/33 self-tests pass**, and the live settings check reports **14 commands**.
- The requested mutation command reports **19 killed, 19 attributed, zero survivors**, with passing control and re-control. Independently applying all 19 edits showed exactly one replacement match each, successful compilation, and the named failing case without traceback. No equivalent mutation was found.
- **Attribution caveat:** mutation 12’s “compliant world” failure depends on the ambient checkout being unsuitable for its supplied empty registry. Its separate missing-settings case also fails, so the mutation is genuinely killed; the named compliant-case attribution alone is weaker evidence.

The backlog row, dashboard entry, and live PR #414 body reproduce the falsifier, counts, and non-command behavior. Their evidence supports the narrow `args`/`shell` policy, not completeness over execution controls; the default-shell explanation also needs correction.

VERDICT: NOT CONVERGED
