<!-- codex-review: model=gpt-6.1-sol -->

Reviewed head: 53e087cf4337233830ec12be5a37d3a35bfd7ed6

REVIEW GAP: Claude — alternation.

All reproductions below ran through `bash .claude/hooks/run-hook.sh agent-long-call.sh`. Unless stated otherwise, timeout-related environment variables were unset.

1. **Medium · BLOCKER (Q4c) · fix-induced — `scripts/check-agent-long-call.py:142`: nonpositive maximums silently bypass the guard.**

   Ran with `BASH_MAX_TIMEOUT_MS=0`:
   ```json
   {"tool_name":"Bash","agent_id":"a1","tool_input":{"command":"sleep 900","timeout":300000}}
   ```
   Produced **exit 0, empty stdout and stderr**: allowed. Repeated with `BASH_MAX_TIMEOUT_MS=-1`, same result.

   The installed 2.1.309 binary’s `gMe()` accepts an environment maximum only when `!isNaN(t)&&t>0`; otherwise it returns `Math.max(600000,fde(n))`. Executing its extracted functions confirmed an effective timeout of **300000**, which requires denial. The hook instead caps this call at 120000.

   Restore the positive-value validation before applying the cap. This is a reproduced false green with a local fix in an existing changed file, satisfying Q4c. Sibling search covered both environment readers: default validation also omits positivity; standalone nonpositive defaults preserve the verdict, but maximums do not.

2. **Low · BLOCKER (Q4c) · fix-induced — `scripts/check-agent-long-call.py:116`: Python trimming changes the harness’s timeout interpretation.**

   Ran with `BASH_DEFAULT_TIMEOUT_MS="\uFEFF300000"`—a literal leading BOM:
   ```json
   {"tool_name":"Bash","agent_id":"a1","tool_input":{"command":"sleep 900"}}
   ```
   Produced **exit 0, empty stdout and stderr**. JavaScript `String.trim()` removes the BOM; Python `str.strip()` does not. Executing the binary’s extracted reader returned default **300000**, so the hook falsely allows a long foreground call.

   The reverse also reproduces: a leading U+0085 yields **deny JSON**, while the harness reads NaN and uses 120000. Use JavaScript-compatible whitespace trimming locally. Sibling search found the same Python trimming in numeric timeout strings at lines 136–137; both readers need consistent treatment.

3. **Medium · FILE · fix-induced — `scripts/check-agent-long-call.py:152`: false-valued disable flags wrongly deny background calls.**

   Ran with `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=false`:
   ```json
   {"tool_name":"Bash","agent_id":"a1","tool_input":{"command":"sleep 900","timeout":600000,"run_in_background":true}}
   ```
   Produced **exit 0 with `permissionDecision: "deny"`**. Values `"0"` and `"banana"` also denied.

   In the installed binary, this variable uses `M.bool()`, whose reader recognizes only trimmed, case-insensitive `1`, `true`, `yes`, and `on` as true. Thus `"false"` permits backgrounding. Python’s nonempty-string check differs. Mirror the boolean reader and add false-valued cases. This is a false refusal, not a Q4c BLOCKER. Sibling search covered the background exemption, its documentation, and its test: all encode the same nonempty-string assumption.

Validation: **37/37 self-tests; 29/29 mutations killed and attributed**. Boundary, exponent, thousands, negative, numeric-string, main-session, malformed-input, and background-flag probes otherwise behaved as described. Tested malformed inputs printed NOT CHECKED at exit 1 without tracebacks. No additional required case was found lost through removal of the command-pattern rules.

VERDICT: NOT CONVERGED
