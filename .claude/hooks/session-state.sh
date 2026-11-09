#!/usr/bin/env bash
# SessionStart (startup, resume, and after every compaction): print what is IN FLIGHT, derived from git and
# `gh` at that moment — backlog #362. Compaction keeps what is on disk and loses what is in flight; a
# hand-written handoff went stale within minutes (it said "watch PR #407's CI" while PR #407 had a merge
# conflict and no CI at all). This block is computed when it is read, so it cannot be stale.
#
# ⛔ ALWAYS EXIT 0. A SessionStart failure must never stop a session; `session-state.py` writes CANNOT RUN
# INTO the block instead, so a failure is visible where the state would have been.
# ⚠ Registered by the repo's one relative shape (`check-hook-commands.py`), so it shares backlog #364's
# limit: after a compaction in a session whose cwd is a subdirectory, it does not launch.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# ⛔ stdin is NOT read: the payload is not needed, and draining it blocked the hook when the pipe was held
# open (PR #410 r2: 60 s, empty output). The python child gets /dev/null for every subprocess it starts.
python3 "$REPO_ROOT/scripts/session-state.py" </dev/null 2>&1 || echo "=== IN FLIGHT: CANNOT RUN — session-state.py exited $? ==="
# backlog #589: remove the worktrees under .claude/worktrees/ whose PR merged (67 of them, 11 GB, froze the Mac on
# 2026-11-09). It runs AFTER the in-flight block, on what is LEFT of settings.json's 60 s bound for this hook: its
# `--deadline` is 55 s minus the seconds already used ($SECONDS), so the two together stay under 60. With under 10 s
# left it is NOT RUN, and says so. It prints nothing unless it removed, deferred or failed, or could not run.
PRUNE_LEFT=$((55 - SECONDS))
if [ "$PRUNE_LEFT" -ge 10 ]; then
  python3 "$REPO_ROOT/scripts/prune-merged-worktrees.py" --hook --deadline "$PRUNE_LEFT" </dev/null 2>&1 \
    || echo "=== WORKTREE PRUNE: CANNOT RUN — prune-merged-worktrees.py exited $? (treat as NOT RUN) ==="
else
  echo "=== WORKTREE PRUNE: NOT RUN — only ${PRUNE_LEFT}s of the hook's 60 s were left ==="
fi
exit 0
