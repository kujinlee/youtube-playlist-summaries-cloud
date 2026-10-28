#!/usr/bin/env bash
# PostToolUse hook — rebuild EVERY generated page after a Bash command whose TEXT contains `gh pr merge`
# (owner decision D3, 2026-10-28). A plain substring, deliberately over-eager: a false fire costs one rebuild
# (~18 s); a miss needs `eval`, an alias, or a merge spelled without that text. No shell is parsed.
# and the goal tree alone after an edit of docs/goal-threads.md (backlog #363). The decisions and the
# runner live in scripts/regen-pages.py, which has the cases; this file only hands it the payload.
#
#     bash .claude/hooks/regen-pages.sh --self-test     # runs scripts/regen-pages.py --self-test
#
# NEVER BLOCKS, NEVER FAILS THE TOOL CALL: exit 0 unconditionally, like regen-dashboard.sh. Each
# generator has its own timeout and one failing never stops the others; every page NOT rebuilt is
# named in the output. ⚠ So this hook's exit code carries NO information.
set -uo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

if [ "${1:-}" = "--self-test" ]; then
  exec python3 "$REPO/scripts/regen-pages.py" --self-test
fi

python3 "$REPO/scripts/regen-pages.py" --hook || echo "⚠  regen-pages.py exited $? — generated pages may be STALE"
exit 0
