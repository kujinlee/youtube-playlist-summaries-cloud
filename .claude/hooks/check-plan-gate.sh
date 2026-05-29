#!/usr/bin/env bash
# PostToolUse hook — fires after every Write tool call.
# If the written file is an implementation plan, injects a gate-check reminder
# so Claude cannot silently skip the Phase 2 Codex adversarial review.
#
# How it works:
#   Claude Code passes a JSON blob via stdin:
#     { "tool_name": "Write", "tool_input": { "file_path": "...", ... }, ... }
#   This script extracts file_path, checks if it's in docs/superpowers/plans/,
#   and prints a reminder block if so. The stdout is injected as a <system>
#   message into Claude's next context window.

INPUT=$(cat)

FILE_PATH=$(echo "$INPUT" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
    print(d.get('tool_input', {}).get('file_path', ''))
except Exception:
    pass
" 2>/dev/null) || FILE_PATH=""

if [[ "$FILE_PATH" == *"docs/superpowers/plans/"* ]]; then
    cat <<'EOF'

╔══════════════════════════════════════════════════════════════════════════╗
║  ⚠️  GATE CHECK — dev-process.md Phase 2                                ║
╠══════════════════════════════════════════════════════════════════════════╣
║  An implementation plan was just written.                               ║
║  REQUIRED before offering execution options:                            ║
║                                                                          ║
║  1. /codex:rescue adversarial review of this plan                       ║
║  2. Save review → docs/reviews/plan-<name>-codex.md                    ║
║  3. Address all Blocking and High findings                              ║
║  4. Explicit user approval of the plan                                  ║
║                                                                          ║
║  DO NOT invoke subagent-driven-development or executing-plans           ║
║  until all four gates are cleared.                                      ║
╚══════════════════════════════════════════════════════════════════════════╝
EOF
fi

exit 0
