#!/usr/bin/env bash
# Enable this repo's tracked git hooks (`.githooks/`, backlog #393) for this clone and every worktree of it.
#
#     scripts/install-git-hooks.sh            # set core.hooksPath = .githooks (idempotent)
#     scripts/install-git-hooks.sh --status   # is the plan-leak pre-push hook active HERE? (exit 0 = yes)
#
# It REFUSES a different existing core.hooksPath, and live hooks in .git/hooks, because setting the path
# would silently switch those off. The logic is `scripts/check-plan-leak.py --install-hooks|--hooks-status`.
set -uo pipefail
here=$(cd "$(dirname "$0")" && pwd)
case "${1:-}" in
  --status) exec python3 "$here/check-plan-leak.py" --hooks-status;;
  '') exec python3 "$here/check-plan-leak.py" --install-hooks;;
  *) echo "usage: scripts/install-git-hooks.sh [--status]" >&2; exit 2;;
esac
