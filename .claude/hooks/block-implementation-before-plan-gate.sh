#!/usr/bin/env bash
# PreToolUse hook on Agent / Skill — the machine-enforceable half of the Post-Plan Gate.
#
# WHY THIS FILE EXISTS (measured 2026-08-15).
#   docs/process-checklists.md:28 said: "The hook (PreToolUse on Agent) is a machine-enforceable
#   backstop — it blocks subagent dispatch while the sentinel file exists."
#   NO SUCH HOOK EXISTED. settings.json had PreToolUse matchers for Bash only, and
#   check-plan-gate.sh never wrote the sentinel it was supposed to watch for. So the documented
#   two-layer defence was ONE printed banner. A 15-task plan reached "want me to start Task 1?"
#   with zero adversarial review, and a human caught it, not the machine.
#
#   This is the shape docs/portable-practices.md keeps recording: a rule that lives as text where
#   it was supposed to live as a mechanism. A checklist line describing a hook is not a hook.
#
# WHAT IT BLOCKS: dispatching an implementation subagent, or invoking an execution skill, while
# .claude/plan-gate-pending exists.
#
# WHAT IT DELIBERATELY ALLOWS: review agents. The gate is cleared BY dispatching reviewers, so a
# blanket block would deadlock. The discriminator is the word "review" in the tool input.
#
#   ⚠ LIMIT, STATED RATHER THAN HIDDEN: that discriminator is a keyword, not a proof. An
#   implementation agent whose prompt happens to say "review" gets through. It is a backstop for
#   the honest mistake this was built for — forgetting the gate — not a defence against a
#   determined bypass. The task list (Post-Plan Gate 1/5..5/5) is the other layer.

INPUT=$(cat)
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SENTINEL="$REPO_ROOT/.claude/plan-gate-pending"

[[ -f "$SENTINEL" ]] || exit 0

VERDICT=$(echo "$INPUT" | python3 -c '
import json, sys
EXEC_SKILLS = ("subagent-driven-development", "executing-plans")
try:
    d = json.load(sys.stdin)
except Exception:
    print("ALLOW"); sys.exit()

tool = d.get("tool_name", "")
ti = d.get("tool_input", {}) or {}
blob = json.dumps(ti).lower()

# An execution skill is always an implementation dispatch, whatever its arguments say.
if tool == "Skill" and any(s in str(ti.get("skill", "")).lower() for s in EXEC_SKILLS):
    print("BLOCK:skill"); sys.exit()

if tool == "Agent":
    # Reviewers are how the gate gets cleared; let them through.
    print("ALLOW" if "review" in blob else "BLOCK:agent")
    sys.exit()

print("ALLOW")
' 2>/dev/null) || VERDICT="ALLOW"

case "$VERDICT" in
  BLOCK:*)
    cat >&2 <<EOF

╔══════════════════════════════════════════════════════════════════════════╗
║  ⛔ BLOCKED — the Post-Plan Gate has not been cleared                    ║
╚══════════════════════════════════════════════════════════════════════════╝

$(cat "$SENTINEL")

dev-process.md Phase 2: the gate is DUAL adversarial review to CONVERGENCE —
a full re-review round with no new Blocking/High. Not one reviewer, and not a
decaying severity curve from one reviewer.

Do this instead:
  1. Dispatch the plan review, Codex AND Claude, independently.
  2. Save to docs/reviews/plan-<feature>-r<N>-{codex,claude}.md
  3. Fix every Blocking/High; write a DISPOSITION for each Medium/Low.
  4. Re-review until a round adds no new Blocking/High.
  5. rm .claude/plan-gate-pending

Review agents are NOT blocked — dispatch them now.
EOF
    exit 2
    ;;
esac
exit 0
