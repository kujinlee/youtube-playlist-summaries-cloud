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

# ⛔ ABSENCE OF A NAME IS NOT "SOME OTHER TOOL" — r1 Blocking (Codex). The first version required
# `tool_name == "AskUserQuestion"` and exited 0 otherwise, while the checker deliberately accepts a
# BARE tool input (`{"questions": […]}`) with no envelope at all. Fed that shape it exited 0 on a
# card the checker refuses with rc=2: fail-open, silently, on a payload the guard was written for.
# `.claude/settings.json` already scopes this hook to AskUserQuestion, so detection only has one job
# left — skip on a POSITIVE identification of a different tool, and check everything else.
#
# ⚠ AND A BROKEN INTERPRETER IS NOT A PASS — r1 H-3. Measured on the first version: malformed JSON,
# a JSON array, empty stdin, a pyenv shim exiting 1, and a python that prints a banner ALL produced
# `exit 0` with no message, disarming the guard for a whole session with nothing to see. The script
# obeys "cannot run is a failure" scrupulously; four lines of shell threw the verdict away.
# It warns and exits 1 rather than blocking: wedging every card because python is broken would be a
# worse cure than the disease, but silence is not the alternative.
DETECT=$(printf '%s' "$INPUT" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
    name = d.get("tool_name") if isinstance(d, dict) else None
except Exception:
    print("unreadable"); sys.exit()
print("other" if (name is not None and name != "AskUserQuestion") else "card")
' 2>/dev/null)
DETECT_RC=$?

if [[ $DETECT_RC -ne 0 || -z "$DETECT" ]]; then
  echo "⚠ enforce-selection-card.sh: could not read the hook envelope (python3 rc=$DETECT_RC)." >&2
  echo "  The §19 card check DID NOT RUN. Treat this card as NOT CHECKED, never as compliant." >&2
  exit 1
fi

# A different tool, named as such: not our business, silently.
[[ "$DETECT" == "other" ]] && exit 0

# "unreadable" falls through ON PURPOSE — python works, the payload does not parse, and the checker
# says so in its own CANNOT-RUN grammar rather than this hook guessing.
VERDICT_OUT=$(printf '%s' "$INPUT" | python3 "$REPO_ROOT/scripts/check-selection-card.py" 2>&1)
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
