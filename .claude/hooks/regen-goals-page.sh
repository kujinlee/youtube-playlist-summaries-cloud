#!/usr/bin/env bash
# PostToolUse hook — regenerate the goals view whenever one of its SOURCES is written.
#
# WHY A HOOK AND NOT A SKILL. `/explain-diff`, `/brief` and `/explain-findings` are composers: you
# invoke them about a subject you name, and their bodies are instructions for judgement. This page
# has no subject and no judgement — every field is derived (ADR-0010). A skill here would be a
# wrapper whose entire body is "run the script", and it would have to join
# `scripts/check-explainer-delivery.py`'s PAGE_SKILLS, a check that exists to stop the delivery loop
# being described in a fourth place. `/backlog-table` set this precedent: it is a script plus a hook
# and has no skill at all.
#
# WHY IT MATTERS MORE HERE THAN FOR THE BACKLOG. The backlog page has ONE source. This page has
# five — the registry, every spec/plan header, every ADR, the milestone spines, and ROOTS/DEPENDS in
# gen-backlog-page.py — so the number of ways for it to go quietly stale is five times larger, and
# a stale page looks exactly like a current one.
#
# NEVER BLOCKS, NEVER FAILS THE TURN. Exits 0 unconditionally. The refusal cases are expected —
# an anchor claimed by no document, a ROOTS key outside the registry — and the point is to surface
# them at the moment they happen rather than the next time someone opens the page.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

FILE_PATH=$(cat | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    print(''); raise SystemExit
print(d.get('tool_input', {}).get('file_path', '') or '')
" 2>/dev/null) || exit 0

# Every input the page derives from. A source added to gen-goals-page.py and forgotten here is the
# failure mode; the docstring's derivation list is the checklist.
case "$FILE_PATH" in
  */docs/anchors.md|docs/anchors.md) ;;
  */docs/adr/*.md|docs/adr/*.md) ;;
  */docs/superpowers/specs/*.md|docs/superpowers/specs/*.md) ;;
  */docs/superpowers/plans/*.md|docs/superpowers/plans/*.md) ;;
  */scripts/gen-backlog-page.py|scripts/gen-backlog-page.py) ;;
  *) exit 0 ;;
esac

OUT=$(python3 "$REPO/scripts/gen-goals-page.py" 2>&1) || {
  echo "⚠  a goals source changed but the page was NOT regenerated:"
  echo "$OUT" | tail -4
  echo "   The page at http://127.0.0.1:7391/goals is now STALE."
  exit 0
}

echo "↻ goals view regenerated — http://127.0.0.1:7391/goals"
exit 0
