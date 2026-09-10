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

# ⛔ THE PAYLOAD NEVER ENTERS A SHELL VARIABLE — r2 Blocking (Codex). `INPUT=$(cat)` strips NUL
# bytes, so a payload the checker correctly calls CANNOT RUN arrived here as valid JSON: measured
# `direct=2 hook=0`. Command substitution also eats trailing newlines. A temp file carries the bytes
# it was given, which is the only thing this hook is for.
TMP="$(mktemp)" || { echo "⚠ enforce-selection-card.sh: mktemp failed; card NOT CHECKED." >&2; exit 1; }
trap 'rm -f "$TMP"' EXIT
cat > "$TMP"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# ⛔ AND THE VERDICT TRAVELS BY EXIT CODE, NOT STDOUT — r2 High (Codex) / H-1 (Claude). The previous
# version compared a stdout string, so a `python3` that prints a banner (pyenv shim, conda
# activation, a chatty sitecustomize) made DETECT `"banner\nother"`: neither empty nor "other", so
# the cannot-run branch never fired, control fell through, and the hook rendered the §19 refusal
# panel over a *Bash* payload. Exit codes cannot be prefixed.
#
#   0 = an AskUserQuestion card, or an envelope with no tool_name (the checker accepts a bare tool
#       input, and ABSENCE OF A NAME IS NOT "SOME OTHER TOOL" — that was r1's Blocking)
#   3 = positively a different tool
#   4 = unreadable; fall through so the CHECKER says so in its own CANNOT-RUN grammar
#   * = the interpreter itself failed. Warn loudly and exit 1: wedging every card because python is
#       broken is a worse cure than the disease, but silence is not the alternative.
python3 - "$TMP" <<'PY' 2>/dev/null
import json, sys
try:
    with open(sys.argv[1], "rb") as fh:
        data = json.loads(fh.read().decode("utf-8", "replace"))
    name = data.get("tool_name") if isinstance(data, dict) else None
except Exception:
    sys.exit(4)
sys.exit(3 if (name is not None and name != "AskUserQuestion") else 0)
PY
DETECT_RC=$?

case $DETECT_RC in
  0|4) ;;
  3)   exit 0 ;;
  *)   echo "⚠ enforce-selection-card.sh: could not read the hook envelope (python3 rc=$DETECT_RC)." >&2
       echo "  The §19 card check DID NOT RUN. Treat this card as NOT CHECKED, never as compliant." >&2
       exit 1 ;;
esac

VERDICT_OUT=$(python3 "$REPO_ROOT/scripts/check-selection-card.py" < "$TMP" 2>&1)
VERDICT_RC=$?

[[ $VERDICT_RC -eq 0 ]] && exit 0

cat >&2 <<EOF

╔══════════════════════════════════════════════════════════════════════════╗
║  ⛔ BLOCKED — this selection card does not follow portable-practices §19  ║
╚══════════════════════════════════════════════════════════════════════════╝

$VERDICT_OUT

THE RECIPE, and it is in ONE place — docs/portable-practices.md §19:

  * every option starts with a CAPITAL letter, running A, B, C in order
  * exactly one advises — the word "recommend" in its label — and it goes FIRST
    (on a multi-select card: at least one advises, in any position)
  * the LAST option is "<letter> — I have a question about these"
  * 3 to 4 options. The tool accepts 4, and the exit spends one, so you get 3 real choices
  * every other option carries a RATIONALE and a TRADE-OFF — what it costs or gives up

⚠ The last line is the one this hook CANNOT check. It sees only that something was written.

MEASURED: three cards in one session, one compliant. The rule was not missing — it was
read from memory instead of from the file. Open §19 rather than recalling it.

⚠ PASSING THIS HOOK IS NOT SATISFYING §19. It checks shape only. It cannot see whether
two of your options are the SAME WORK in different words — which is the defect §19 was
written about — nor whether the axis is named, nor whether a rationale is true.
EOF
exit 2
