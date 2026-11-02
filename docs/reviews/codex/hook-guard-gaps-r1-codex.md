<!-- codex-review: model=gpt-6.1-sol -->

Review of `edf732e8`, mandate **REFUTE**. Repository unchanged; experiments ran in `/tmp/hook-review-365.mTaOgb/repo`, with copied `node_modules`.

1. **Medium — `KNOWN_TYPES` rejects hook types already supported today.**  
   `scripts/check-hook-commands.py:52,83` recognizes only `command` and `prompt`. The [official hook schema](https://code.claude.com/docs/en/hooks#common-fields) also recognizes `http`, `mcp_tool`, and `agent`. All five support `Stop`. Installed Claude Code **2.1.309** also contains agent-hook processing and MCP-hook availability diagnostics.

   Appending each supported type to today’s settings makes this guard return **2, CANNOT RUN**. A legitimate registration would therefore fail CI. Today’s tracked settings remain green; no existing non-command registration was found in the searched repository/plugin JSON files. Expand the known set to the supported schema. The prose describing additional types as something Claude Code might add *later* is already inaccurate.

2. **Medium — list/object `type` crashes instead of reporting CANNOT RUN.**  
   At `scripts/check-hook-commands.py:83`, set membership assumes a hashable value. Appending `{"type":[]}` or `{"type":{}}` raises an uncaught **TypeError**. The CLI exits **1 with a traceback**, violating the promised malformed-input contract of exit 2 with a CANNOT RUN diagnostic.

   Number `42` and `null` correctly return 2. Check that `type` is a string before testing membership; add list/object regression cases.

3. **Low — non-string exemption reasons still provide unexplained exemptions.**  
   `scripts/check-hook-commands.py:110` coerces values with `str(...)`. Against today’s settings, reasons `None`, `0`, `False`, `[]`, and `{}` each return **0**, accepting all 13 commands. These values contain no written explanation. Require a nonempty string rather than accepting its string representation. Empty and whitespace strings correctly return 1.

Executed verification:

- **25/25 self-tests passed.** The pure cases produced their named findings; no remaining wrong-reason failure was found in the delivered fixtures.
- Suppressing the shape diagnostic turns **both strengthened divergence cases red**, as required.
- The requested mutation command completed: **14 killed, 14 attributed to their named cases, zero survivors**.
- Live check: **exit 0**, all **13 commands** canonical and present.
- Replayed round-4 probes against baseline and HEAD: `{}` **0→2**, `"commmand"` **0→2**, empty reason **0→1**.
- Inspected live **PR #412**, backlog row **#365**, and the dashboard entry. Their counts and three concrete probe results reproduce. Their claim that every out-of-set type becomes Malformed is false for unhashable values; their future-type explanation overlooks already-supported types. Marking the gap fully fixed is therefore premature.

VERDICT: NOT CONVERGED
