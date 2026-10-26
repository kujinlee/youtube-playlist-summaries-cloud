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

# ⛔ backlog #111: the payload goes through a FILE and the verdict comes back by EXIT CODE — the fix
# enforce-selection-card.sh shipped first. The detector used to print "yes"/"no" and compare STDOUT, so a
# `python3` that prints a banner (pyenv shim, conda activation, a chatty sitecustomize) or exits non-zero
# produced neither, and this hook exited 0 in silence: disarmed for the session, indistinguishable from a
# compliant run. Exit codes cannot be prefixed by a banner.
TMP="$(mktemp)" || { echo "⚠ enforce-handoff-path.sh: mktemp failed; the handoff path is NOT CHECKED." >&2; exit 1; }
trap 'rm -f "$TMP"' EXIT
cat > "$TMP" || { echo "⚠ enforce-handoff-path.sh: could not read the hook payload; the handoff path is NOT CHECKED." >&2; exit 1; }
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

#   0 = the handoff skill   3 = a readable envelope for anything else (not mine)
#   4 = an envelope that is not JSON (r1: truncated or empty) — CANNOT TELL whether it is /handoff
#   * = the interpreter itself failed: warn and exit 1 (non-blocking), never a silent 0
python3 - "$TMP" <<'PY' 2>/dev/null
import json, sys
try:
    with open(sys.argv[1], "rb") as fh:
        d = json.loads(fh.read().decode("utf-8", "replace"))
except Exception:
    sys.exit(4)
if not isinstance(d, dict):
    sys.exit(4)
ti = d.get("tool_input", {}) or {}
skill = str(ti.get("skill", "")).lower() if isinstance(ti, dict) else ""
# Plugin-qualified names arrive as "vendor:handoff"; match the bare segment.
sys.exit(0 if d.get("tool_name") == "Skill" and skill.split(":")[-1] == "handoff" else 3)
PY
DETECT_RC=$?

case $DETECT_RC in
  0) ;;
  3) exit 0 ;;
  4) echo "⚠ enforce-handoff-path.sh: the hook envelope is not readable JSON, so this could not tell whether" >&2
     echo "  this is /handoff. The handoff-path check DID NOT RUN — treat it as NOT CHECKED." >&2
     exit 1 ;;
  *) echo "⚠ enforce-handoff-path.sh: could not read the hook envelope (python3 rc=$DETECT_RC)." >&2
     echo "  The handoff-path check DID NOT RUN. Treat this /handoff as NOT CHECKED, never as compliant." >&2
     exit 1 ;;
esac

# ⛔ THE VERDICT TRAVELS BY RECEIPT (backlog #111 r2). The checker writes 0/1/2 to a file once it has
# reached a verdict; the hook acts on that alone. No exit-code guessing (an interpreter failure is also 1),
# and no matching of the checker's prose (a rewording silently downgraded a block to a warning). A checker
# that never ran — broken, killed, or a wrapper that exits 0 — leaves no receipt.
RECEIPT="$(mktemp)" || { echo "⚠ enforce-handoff-path.sh: mktemp failed; the handoff path is NOT CHECKED." >&2; exit 1; }
trap 'rm -f "$TMP" "$RECEIPT"' EXIT
VERDICT_OUT=$(python3 "$REPO_ROOT/scripts/check-handoff-path.py" --quiet --receipt "$RECEIPT" 2>&1)
VERDICT="$(tr -d '[:space:]' < "$RECEIPT" 2>/dev/null)"

case "$VERDICT" in
  0)   exit 0 ;;
  1|2) ;;
  *)   echo "⚠ enforce-handoff-path.sh: check-handoff-path.py reached no verdict (no receipt). The handoff path" >&2
       echo "  is NOT CHECKED — treat this /handoff as unverified, never as compliant." >&2
       [[ -n "$VERDICT_OUT" ]] && printf '%s\n' "$VERDICT_OUT" >&2
       exit 1 ;;
esac

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
