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
    # ARM THE SENTINEL. Until 2026-08-15 this script printed a banner and nothing else, so
    # the PreToolUse block that process-checklists.md:28 calls "a machine-enforceable
    # backstop" could never fire — nothing created the file it watches for. The documented
    # two-layer defence was one printed reminder, and a plan reached "want me to start T1?"
    # with no review. A human caught it. Writing the file is what makes the gate physical.
    REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
    printf '%s\n' \
      "plan: $FILE_PATH" \
      "armed: $(date -u +%Y-%m-%dT%H:%M:%SZ)" \
      "clears when: the dual adversarial review of this plan converges (Post-Plan Gate 5/5)" \
      > "$REPO_ROOT/.claude/plan-gate-pending"

    cat <<'EOF'

╔══════════════════════════════════════════════════════════════════════════╗
║  ⚠️  GATE CHECK — dev-process.md Phase 2                                ║
╠══════════════════════════════════════════════════════════════════════════╣
║  An implementation plan was just written.                               ║
║  REQUIRED before offering execution options:                            ║
║                                                                          ║
║  1. DUAL adversarial review (Codex + Claude, INDEPENDENT)               ║
║  2. Save review → docs/reviews/plan-<name>-codex.md                    ║
║  3. Address all Blocking and High findings                              ║
║  4. Convergence — a full re-review round with no new Blocking/High      ║
║                                                                          ║
║  .claude/plan-gate-pending is now ARMED and BLOCKS implementation       ║
║  dispatch. Review agents are still allowed. Gate 5/5 clears it.         ║
╚══════════════════════════════════════════════════════════════════════════╝
EOF
fi

exit 0
