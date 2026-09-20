#!/usr/bin/env bash
# PostToolUse hook — regenerate the features view whenever one of its SOURCES is written.
#
# WHY A HOOK AND NOT A SKILL. `/explain-diff`, `/brief` and `/explain-findings` are composers: you
# invoke them about a subject you name, and their bodies are instructions for judgement. This page
# has no subject and no judgement — every field except one `for:` sentence per node is derived
# (see `scripts/gen-features-page.py`'s own docstring). A skill here would be a wrapper whose
# entire body is "run the script"; `/goals` and `/backlog-table` set this precedent already —
# script plus hook, no skill.
#
# WHY STALENESS IS INVISIBLE HERE WITHOUT THIS HOOK. `/features` derives from SEVEN path families:
# `docs/features.md` itself, `docs/anchors.md`, `docs/backlog.md`, every `docs/adr/*.md`, every
# `docs/superpowers/specs/*.md` header, every `docs/superpowers/plans/*.md` header, and every
# `docs/reviews/**` file a node's slug matches. That is wider than `/_stale`'s own idea of this
# page's sources: `PAGE_SOURCES["features"]` in `scripts/explainer-serve.py` deliberately stays
# THREE WHOLE FILES (`docs/features.md`, `docs/anchors.md`, `docs/backlog.md`), not directories —
# widening it there turns that file's own self-test 202/202 -> 201/202, because it asserts every
# declared source is a real FILE. So the two sets disagree ON PURPOSE: this hook rebuilds on the
# wide set below; `/_stale`'s banner watches only the narrow set. A spec, ADR or review edit
# therefore rebuilds the page correctly and does NOT light the staleness banner — a page that is
# silently ahead of the banner that is supposed to describe it, which is the residual this hook
# cannot close and `/_stale` does not attempt to.
#
# NEVER BLOCKS, NEVER FAILS THE TURN. Exits 0 unconditionally. The generator is cheap (~1s) because
# this case list fires on every `docs/reviews/*` and `docs/superpowers/plans/*` write, which happen
# constantly in this repo's own process — a slow or blocking hook here would tax every review round.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

# ⚠ A MALFORMED PAYLOAD MUST NOT LOOK LIKE AN UNWATCHED FILE — code review r1 (Codex), Low.
# `printf 'not json' | bash …` exited 0 and printed nothing, byte-identical to the overwhelmingly
# common case of a Write to a file this hook does not care about. Exit 0 is CORRECT on every path
# — a hook that fails the turn over a page rebuild is worse than a stale page — but silence there
# means that if the hook-input shape ever changes, this hook stops working and NOTHING says so.
# So the parser answers with a SENTINEL rather than "", and the two cases are separated below.
# ⚠ EMPTY STDIN STAYS SILENT, deliberately: invoked by hand with no payload there is nothing to
# have failed to parse, and a warning there would train the reader to ignore this line.
PAYLOAD=$(cat)
FILE_PATH=$(printf '%s' "$PAYLOAD" | python3 -c "
import json, sys
try:
    d = json.load(sys.stdin)
except Exception:
    print('<<unparseable>>'); raise SystemExit
print(d.get('tool_input', {}).get('file_path', '') or '')
" 2>/dev/null) || FILE_PATH='<<unparseable>>'

if [ "$FILE_PATH" = '<<unparseable>>' ]; then
  if [ -n "${PAYLOAD//[[:space:]]/}" ]; then
    echo "⚠  regen-features-page.sh could not read its hook payload as JSON — if the hook input" \
         "shape has changed, this hook has silently stopped rebuilding /features."
  fi
  exit 0
fi

# Every input the page derives from. A source added to gen-features-page.py and forgotten here is
# the failure mode; the page's own docstring derivation list is the checklist.
case "$FILE_PATH" in
  */docs/features.md|docs/features.md) ;;
  */docs/anchors.md|docs/anchors.md) ;;
  */docs/backlog.md|docs/backlog.md) ;;
  */docs/adr/*.md|docs/adr/*.md) ;;
  */docs/superpowers/specs/*.md|docs/superpowers/specs/*.md) ;;
  */docs/superpowers/plans/*.md|docs/superpowers/plans/*.md) ;;
  */docs/reviews/*|docs/reviews/*) ;;
  *) exit 0 ;;
esac

OUT=$(python3 "$REPO/scripts/gen-features-page.py" 2>&1) || {
  echo "⚠  a features source changed but the page was NOT regenerated:"
  echo "$OUT" | tail -4
  echo "   The page at http://127.0.0.1:7391/features is now STALE."
  exit 0
}

echo "↻ features view regenerated — http://127.0.0.1:7391/features"
exit 0
