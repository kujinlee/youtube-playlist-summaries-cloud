---
description: Show readable skill and slash-command usage for the current Claude Code session
disable-model-invocation: true
allowed-tools: Bash(python3 *)
---

# Session skill report

Produce a readable timeline of skill usage for the current session by parsing the Claude Code transcript.

Run:

```bash
python3 scripts/session-skill-report.py \
  --session-id "${CLAUDE_SESSION_ID}" \
  --cwd "${CLAUDE_PROJECT_DIR:-$PWD}" \
  --format text
```

If the user passed a transcript path in `$ARGUMENTS`, use that instead:

```bash
python3 scripts/session-skill-report.py --transcript "$ARGUMENTS" --format text
```

Then show the command output directly. Do not summarize away the timeline table.

What the report includes:

- hook-injected skills at SessionStart (for example `superpowers:using-superpowers`)
- explicit user slash commands such as `/feature-dev` or `/commit-commands:commit`
- Claude `Skill` tool invocations such as `superpowers:test-driven-development`
- subagent spawns via `Task` tool

If the report is empty, tell the user the transcript may not have recorded skill activity yet, or they can rerun with an explicit `--transcript` path.
