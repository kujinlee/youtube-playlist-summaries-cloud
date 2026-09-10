#!/usr/bin/env bash
# PreToolUse hook on AskUserQuestion — refuse a card that does not follow portable-practices §19.
#
# WHY THIS FILE EXISTS (measured 2026-09-10).
#   §19 has specified the shape of an option list since 2026-09-04 — a letter per option, exactly
#   one marked (Recommended) and placed first, a final "I have a question about these", a rationale
#   and a trade-off on each. It is restated in two memory files. On 2026-09-10 three cards were
#   presented in one session and ONE of them followed it, after two corrections from the user:
#
#       card 1   recommendation ✓   letters ✗   question-exit ✗
#       card 2   recommendation ✗   letters ✗   question-exit ✗
#       card 3   recommendation ✓   letters ✓   question-exit ✓
#
#   The user: "you seem to deviate proven style. I'd like to have this style recorded and followed."
#   It was recorded, three times over. Recording was never the gap — the rule was reconstructed from
#   recall at the moment of use instead of read. This is the leading half that fires at the point of
#   use, exactly as enforce-handoff-path.sh does for a different rule.
#
# WHAT IT BLOCKS: an AskUserQuestion payload failing any clause of §19 that is exactly decidable.
#
# WHAT IT DELIBERATELY ALLOWS: every other tool, untouched (exit 0 fast). And it is SILENT on a
# well-formed card — a hook that talks on the happy path gets ignored on the unhappy one.
#
# ⚠ LIMIT, STATED RATHER THAN HIDDEN: it reads the card's SHAPE. It cannot tell whether two options
# collapse into the same work — which is the very defect that caused §19 to be written — nor whether
# the question text names the axis, nor whether a stated rationale is true. Those stay human. The
# block message says so, so that passing this is never mistaken for satisfying §19.

INPUT=$(cat)
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

IS_CARD=$(echo "$INPUT" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    print("no"); sys.exit()
print("yes" if d.get("tool_name") == "AskUserQuestion" else "no")
' 2>/dev/null) || IS_CARD="no"

[[ "$IS_CARD" == "yes" ]] || exit 0

VERDICT_OUT=$(echo "$INPUT" | python3 "$REPO_ROOT/scripts/check-selection-card.py" 2>&1)
VERDICT_RC=$?

[[ $VERDICT_RC -eq 0 ]] && exit 0

cat >&2 <<EOF

╔══════════════════════════════════════════════════════════════════════════╗
║  ⛔ BLOCKED — this selection card does not follow portable-practices §19  ║
╚══════════════════════════════════════════════════════════════════════════╝

$VERDICT_OUT

THE RECIPE, and it is in ONE place — docs/portable-practices.md §19:

  * every option starts with a letter:  A — / B — / C —
  * EXACTLY ONE is marked (Recommended), placed FIRST, with its reason in the description
  * the LAST option is "<letter> — I have a question about these"
  * every other option carries a RATIONALE and a TRADE-OFF — what it costs or gives up
  * the question text names the AXIS: "A/B differ in whether X ships now"

MEASURED: three cards in one session, one compliant. The rule was not missing — it was
read from memory instead of from the file. Open §19 rather than recalling it.

⚠ PASSING THIS HOOK IS NOT SATISFYING §19. It checks shape only. It cannot see whether
two of your options are the SAME WORK in different words — which is the defect §19 was
written about — nor whether the axis is named, nor whether a rationale is true.
EOF
exit 2
