#!/usr/bin/env bash
# The LEADING half of the memory-index budget gate — see the lagging half in
# `.github/workflows/ci.yml` ("Memory index injection budget").
#
# ⛔ WHY A HOOK EXISTS AT ALL, and it is not belt-and-braces. Measured 2026-10-19 (r1 CLAUDE N2)
# over two worktrees at the same HEAD: a working tree grown past the limit with NOTHING COMMITTED
# gives rc=1 OVER BUDGET, while a fresh checkout of that same HEAD — what CI sees — gives rc=0 ok.
# A session loads the WORKING TREE (the harness path is a directory symlink into `docs/memory/`,
# same inode), so the overflow that actually degrades a session is invisible to CI by construction.
# That is backlog #309's class: the matcher reads the working file, so no git-shaped guard can see it.
# The guard itself was never blind — it reads the right path. It simply had no caller here.
#
# ⚠ ADVISORY, DELIBERATELY. It warns and always exits 0. A blocking hook on a docs-only threshold is
# what backlog #56 measured getting switched off, and the remedy (move history rows to the triggered
# `slice-history.md` entry) is a judgement about which rows are history — not something to force
# mid-edit. The CI step stays the one that fails.
#
# ⚠ WHAT IT CANNOT DO: it fires on writes THROUGH THE TOOL. An edit by any other route — another
# agent, an editor, a script — is unobserved, which is exactly how the backlog #309 instance arrived.
set -uo pipefail

payload=$(cat)
path=$(printf '%s' "$payload" | python3 -c 'import json,sys
try: print(json.load(sys.stdin).get("tool_input",{}).get("file_path",""))
except Exception: print("")' 2>/dev/null || echo "")

case "$path" in
  */docs/memory/MEMORY.md) ;;
  *) exit 0 ;;
esac

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
out=$(cd "$root" && python3 scripts/check-memory-index-budget.py 2>&1)
rc=$?

# rc 1 = over budget, rc 2 = CANNOT RUN. Both are worth saying; neither blocks.
if [ "$rc" -ne 0 ] || printf '%s' "$out" | grep -q '^WARNING'; then
  printf '⚠ memory index budget (advisory, rc=%s):\n%s\n' "$rc" "$out" >&2
fi
exit 0
