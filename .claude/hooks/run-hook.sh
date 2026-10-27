#!/usr/bin/env bash
# Launch ONE hook from the right checkout — backlog #223.
#
#   .claude/settings.json:  bash "${CLAUDE_PROJECT_DIR:-.}"/.claude/hooks/run-hook.sh <name>.sh
#
# WHY A LAUNCHER, and not `bash "$CLAUDE_PROJECT_DIR"/.claude/hooks/<name>.sh` (PR #409 round 1).
#   The harness runs a hook command from the SESSION's cwd. The old relative form,
#   `bash .claude/hooks/<name>.sh`, therefore found nothing after any `cd` into a subdirectory:
#   every hook, the push gate included, failed to launch, and the harness called that NON-BLOCKING.
#   Anchoring at `$CLAUDE_PROJECT_DIR` alone fixed that and broke something else. The variable names
#   the checkout the SESSION STARTED IN, so a session working in a linked worktree ran the MAIN
#   checkout's hooks, and those read the main checkout's state. Codex measured it: a pending plan gate
#   in the worktree was enforced (exit 2) by the old command and IGNORED (exit 0) by the anchored one.
#
# THE RULE. Use the checkout that CONTAINS the cwd, so behaviour at any checkout root is exactly what
# the relative form gave, and a subdirectory now works too. Fall back to the project dir only when
# the cwd's checkout is not THIS repository, or is not in git at all:
#   1. top = `git rev-parse --show-toplevel` from the cwd;
#   2. it counts only if it shares the project's `--git-common-dir`, so it is a worktree of this repo
#      and not an unrelated one, AND it has the hook file;
#   3. otherwise the project dir, `${CLAUDE_PROJECT_DIR:-.}`. The `:-.` default is the old behaviour.
#
# ⛔ NO ARGUMENT IS PASSED THROUGH. `surface-recall.sh` relies on receiving none (see its comment on
# `$1`). stdin, which carries the hook payload, is inherited by `exec`.
# ⛔ The name must be a bare `<name>.sh` in `.claude/hooks/`; anything else exits 1 with a message.
#   That is non-blocking, exactly as a missing hook was before, and `check-hook-commands.py` refuses
#   such a registration in CI, so it never reaches a session.
set -u
name="${1:-}"
case "$name" in
  ""|*/*|.*|run-hook.sh) echo "run-hook.sh: refusing hook name '${name}' (want a bare <name>.sh)" >&2; exit 1 ;;
  *.sh) ;;
  *) echo "run-hook.sh: refusing hook name '${name}' (want a bare <name>.sh)" >&2; exit 1 ;;
esac

project="${CLAUDE_PROJECT_DIR:-.}"
root="$project"
top=$(env -u GIT_DIR -u GIT_WORK_TREE -u GIT_COMMON_DIR git rev-parse --show-toplevel 2>/dev/null) || top=""
if [ -n "$top" ] && [ "$top" != "$project" ] && [ -f "$top/.claude/hooks/$name" ]; then
  mine=$(env -u GIT_DIR -u GIT_WORK_TREE -u GIT_COMMON_DIR git -C "$top" rev-parse --path-format=absolute --git-common-dir 2>/dev/null) || mine=""
  theirs=$(env -u GIT_DIR -u GIT_WORK_TREE -u GIT_COMMON_DIR git -C "$project" rev-parse --path-format=absolute --git-common-dir 2>/dev/null) || theirs=""
  if [ -n "$mine" ] && [ "$mine" = "$theirs" ]; then
    root="$top"
  fi
fi

if [ ! -f "$root/.claude/hooks/$name" ]; then
  echo "run-hook.sh: no hook '$name' under $root/.claude/hooks — NOT RUN" >&2
  exit 1
fi
exec bash "$root/.claude/hooks/$name"
