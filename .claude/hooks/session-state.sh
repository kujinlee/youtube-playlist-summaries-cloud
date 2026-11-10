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
# backlog #589: ARCHIVE the worktrees under .claude/worktrees/ whose PR merged (67 of them, 11 GB, froze the Mac on
# 2026-11-09). It never deletes: `git worktree move` to ~/.worktree-archive/<repo>/ keeps every file and the reflog;
# a placeholder FILE is left at the old path (a late write fails, ENOTDIR); undo, absolute paths as printed:
# `rm <old> && git worktree move <archive>/<name> <old>`. Its work is one `gh` call, one `lsof`, git
# status reads and renames, all under one deadline. It runs AFTER the in-flight block, on what is LEFT of
# settings.json's 60 s bound for this hook: `--deadline` is 55 s minus the seconds already used ($SECONDS). With under
# 10 s left it is NOT RUN, and says so. `--repo` is passed: the hook's cwd may be outside the repository (PR #551 r1
# Claude F8). It prints nothing unless it archived, deferred or failed, could not run, or the archive holds over 10.
PRUNE_LEFT=$((55 - SECONDS))
if [ "$PRUNE_LEFT" -ge 10 ]; then
  python3 "$REPO_ROOT/scripts/prune-merged-worktrees.py" --hook --repo "$REPO_ROOT" --deadline "$PRUNE_LEFT" </dev/null 2>&1 \
    || echo "=== WORKTREE PRUNE: CANNOT RUN — prune-merged-worktrees.py exited $? (treat as NOT RUN) ==="
else
  echo "=== WORKTREE PRUNE: NOT RUN — only ${PRUNE_LEFT}s of the hook's 60 s were left ==="
fi
exit 0
