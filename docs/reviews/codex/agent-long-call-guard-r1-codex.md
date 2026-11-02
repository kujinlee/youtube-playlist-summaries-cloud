<!-- codex-review: model=gpt-6.1-sol -->

Reviewed head: d41eb9b9e42189cc30dca1d3adda3c9e8dcc6e38

Four findings. All are **Medium, FILE under Q4c; FIX under round-1 Q3** because fixes can stay within changed files. None is fix-induced. None establishes a Q4c BLOCKER: missed command patterns still encounter the independent timeout guard; false denials do not demonstrate data loss, a security hole, or false green.

Reproductions ran through `bash .claude/hooks/run-hook.sh agent-long-call.sh`, using this payload with each command substituted:

```json
{"agent_id":"a1","tool_name":"Bash","tool_input":{"command":"COMMAND"}}
```

Both timeout environment variables were unset unless stated otherwise.

1. **Direct quoted sleep escapes the guard — `scripts/check-agent-long-call.py:75`.**

   Input RUN: `sleep "300"`. Result: **exit 0, stdout `''`, stderr `''`**. Shell quoting preserves the numeric argument; this is a direct sleep, not the documented `bash -c`/script exclusion. It violates backlog #455’s explicit sleep falsifier.

   Siblings searched by running `/bin/sleep 300`, `command sleep 300`, `X=1 sleep 300`, and `timeout 300 sleep 301`; all also silently allowed. `timeout 200 sleep 301` allowed, appropriately bounded. Local fix: tokenize direct shell words and recognize quoted operands and supported prefixes; add these regression cases.

2. **Inherited flags bypass watch detection — `scripts/check-agent-long-call.py:74`.**

   Inputs RUN:
   - `gh --repo a/b pr checks --watch`
   - `gh pr --repo a/b checks --watch`
   - `gh run --repo a/b watch 1`

   Each produced **exit 0, stdout `''`, stderr `''`**. I also ran their `--help` forms: all exited 0 and recognized the intended subcommand, confirming valid flag placement.

   Siblings searched across both watch families and flag positions. Flags following `checks` were detected correctly. Local fix: recognize inherited flags between command words and add cases for both families.

3. **Quoted prose can be denied as executable code — `scripts/check-agent-long-call.py:73`.**

   Input RUN: `echo "then sleep 300 "`. Result: **`"permissionDecision": "deny"`**, with reason **“it sleeps 300 (300 s), over 270 s.”** This echo returns immediately.

   Siblings searched: `echo "a; sleep 300 "` and `echo "then gh run watch 1"` also denied. Plain `echo "sleep 300"` allowed. Both regexes search inside quoted strings; the existing quoted-echo fixture at lines 215–216 does not exercise this shape.

   Local fix: distinguish quoted text from shell command positions before applying both rules, and strengthen the fixture.

4. **Explicitly disabled watch is denied — `scripts/check-agent-long-call.py:74`.**

   Input RUN: `gh pr checks --watch=false`. Result: **`"permissionDecision": "deny"`**, with reason **“it watches … which blocks until CI finishes.”** The pattern accepts the boundary before `=false` without interpreting the Boolean value.

   Siblings searched: both watch families and alternate flag positions above; this Boolean-value defect applies to `checks --watch`. Local fix: parse the flag value and test true/false forms.

Additional verification:

- Every command probe remained allowed with absent, empty, or whitespace-only `agent_id`. Background probes, including `timeout: 600000`, allowed.
- `sleep 271`, `5m`, `1h`, and chained `a && sleep 300` denied; `sleep 270` allowed. Timeout boundaries behaved as specified.
- Malformed JSON and non-object payloads exited 1 with **NOT CHECKED**. Invalid default `Infinity` caused a visible traceback and launcher exit 1; it neither wedged nor silently allowed. `NaN` and garbage defaults silently allowed; invalid `BASH_MAX_TIMEOUT_MS` did likewise.
- Registration correctly uses matcher `Bash`, the shared launcher, and a matching internal Bash guard.
- Self-tests passed **37/37**. All **21 manifest mutations** triggered their named failures; additional hour-unit, `&&`, and newline mutations also failed the corresponding cases.
- The PR body and docstring explicitly disclose the `bash -c` and script-file exclusions.
- No files were written; `.claude/plans/` was not accessed.

VERDICT: NOT CONVERGED
