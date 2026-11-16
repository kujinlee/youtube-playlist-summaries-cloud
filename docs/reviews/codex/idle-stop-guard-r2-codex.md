<!-- codex-review: model=gpt-6.1-sol -->

- **MAJOR — scripts/check-idle-stop.py:128–135:** An answered question remains an exception indefinitely until another tool call or text-form user prompt. Concrete transcript: assistant `AskUserQuestion(id="q")`; user `tool_result(tool_use_id="q", content="Yes")`; assistant text `"Starting now."`. With `background_tasks: []`, no worktrees and CI `[]`, `decide()` returns `('allow', '')`. The last assistant turn asks nothing.

- **MAJOR — scripts/check-idle-stop.py:119:** `splitlines()` splits valid JSON strings containing literal U+2028. Concrete JSONL: an assistant AskUserQuestion record, then `{"type":"user","message":{"content":"Continue\u2028now"}}` serialized with `ensure_ascii=False`, then an assistant closing reply. The human record becomes two invalid fragments and is skipped, preserving the old question exception. Observed result: `('allow', '')` with nothing running.

- **MAJOR — scripts/check-idle-stop.py:121–123:** Deeply nested transcript JSON escapes the narrow exception handler. Concrete transcript file: `'{"x":' + '['*200000 + '0' + ']'*200000 + '}\n'`; Stop payload names that file and supplies `background_tasks: []`. A child process calling `main()` exited **1** with `RecursionError`. The launcher therefore permits an idle stop instead of blocking unreadable evidence.

- **MAJOR — scripts/check-idle-stop.py:265–269:** Malformed CI fields crash rather than fail closed. Concrete `gh` response, exit 0: `[{"number":1,"statusCheckRollup":42}]`. With all other signals idle, `decide()` raises `TypeError`; the launcher maps the crash to exit 1 and allows the stop. A check with `"status":[]` similarly raises during set membership.

- **MAJOR — scripts/check-idle-stop.py:225–235:** The walk deadline never runs inside the file loop. Concrete controlled filesystem input: one directory containing 1,100 old files, with `lstat` latency injected at 10 ms per file. `_recent(..., deadline=start+1)` returned **False after 13.03 seconds**, rather than reporting an unread signal. This exceeds the entire 10-second hook timeout even after directory enumeration has finished.

- **MINOR — scripts/check-idle-stop.py:128 and self-tests at :592:** Human-prompt representation lacks mutation coverage. My in-memory mutation changed `isinstance(content, list) and any(...)` to `False and any(...)`; **all 73 cases still passed**. It lets AskUserQuestion survive a subsequent human prompt represented as `[{"type":"text","text":"Continue"}]`.

  Required check result lines:

  > 73/73 self-test cases passed

  > OK — delivered scripts mutated: 1 file(s), 79 mutation(s), 79 killed, 79 attributed to the case each names, 0 survivor(s) — measured over ONLY scripts/check-idle-stop.py — a DIAGNOSTIC slice, not the gate

VERDICT: NOT CONVERGED
