#!/usr/bin/env bash
# PreToolUse hook on Skill — stop /handoff writing to a path nothing reads.
#
# WHY THIS FILE EXISTS (measured 2026-08-27).
#   The handoff skill upstream saves to `mktemp -t handoff-XXXXXX.md`. THREE such files accumulated
#   in $TMPDIR and NOT ONE was ever read by a resuming session — random suffix, outside the repo,
#   unindexed. A produced artifact with no consumer, which is this repo's recurring "live gate with
#   NO CALLER" wearing different clothes.
#
#   The repair points the skill at .remember/remember.md, which the remember plugin's SessionStart
#   hook already injects as `=== LAST HANDOFF ===` ahead of identity and memory.
#
#   ⚠ THAT REPAIR LIVES IN A VENDORED FILE that `npx skills@latest add mattpocock/skills` overwrites.
#   The first guard written for it was a SENTENCE in docs/plugins.md — "if a resume ever finds a
#   handoff-XXXXXX.md in $TMPDIR, the skill was overwritten". That fires only AFTER a session has
#   already lost its handoff. This hook is the leading half: it fires at invocation.
#
# WHAT IT BLOCKS: invoking the handoff skill while the vendored SKILL.md no longer names
# .remember/remember.md.
#
# WHAT IT DELIBERATELY ALLOWS: every other skill, untouched (exit 0 fast). And when the skill is
# intact this is silent — a hook that talks on the happy path gets ignored on the unhappy one.
#
# ⚠ LIMIT, STATED RATHER THAN HIDDEN: this guards the INSTRUCTION, not the outcome. It cannot
# observe where the file actually lands. If the skill names the right path and the agent writes
# elsewhere anyway, only the next resume finds out — that is what the docs/plugins.md falsifier
# still covers. Two layers, different failure modes.

INPUT=$(cat)
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

IS_HANDOFF=$(echo "$INPUT" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    print("no"); sys.exit()
ti = d.get("tool_input", {}) or {}
skill = str(ti.get("skill", "")).lower()
# Plugin-qualified names arrive as "vendor:handoff"; match the bare segment.
print("yes" if d.get("tool_name") == "Skill" and skill.split(":")[-1] == "handoff" else "no")
' 2>/dev/null) || IS_HANDOFF="no"

[[ "$IS_HANDOFF" == "yes" ]] || exit 0

VERDICT_OUT=$(python3 "$REPO_ROOT/scripts/check-handoff-path.py" --quiet 2>&1)
VERDICT_RC=$?

[[ $VERDICT_RC -eq 0 ]] && exit 0

cat >&2 <<EOF

╔══════════════════════════════════════════════════════════════════════════╗
║  ⛔ BLOCKED — the handoff skill would write where nothing reads          ║
╚══════════════════════════════════════════════════════════════════════════╝

$VERDICT_OUT

MEASURED: three handoff docs were written to \$TMPDIR and none was ever read.
The documents were fine. They had no consumer.

Write the handoff to:  .remember/remember.md

That is the one path the remember plugin's SessionStart hook reads. Described
ONCE, and this refusal does not restate it -- WHY that path is the one that gets
read, and why a DIFFERENT path may have been printed at session start:
  .agents/skills/shared/handoff-path.md
  To inventory where a string appears in this repo, and why ONE command is not
  enough:  .agents/skills/shared/corpus-search.md

  Each is the ONE place that mechanism is described. This refusal used to RESTATE
  both, and drift between the copies made it print a claim and its own withdrawal
  in the same message -- which is the defect the single source removes.
  (r7 CLAUDE L1: it also named handoff-path.md TWICE, four lines apart, under a
  closing sentence saying "both"; and r7 M4: the second pointer restated the
  trigger COUNT as THREE, which that canon's own last section refutes.)

Then repair the vendored skill so this stops recurring:
  \$EDITOR .agents/skills/handoff/SKILL.md      # see docs/plugins.md -> Session Handoff
  python3 scripts/check-handoff-path.py         # must exit 0
EOF
exit 2
