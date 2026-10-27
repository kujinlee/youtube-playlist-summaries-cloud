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
# THE RULE (round 3 — no git process). Walk up from the PHYSICAL cwd to the nearest directory that holds
# BOTH `.git` (a directory, or the file a worktree or submodule has) AND `.claude/hooks/run-hook.sh`. That
# checkout is used. With no such ancestor, use the project dir, `${CLAUDE_PROJECT_DIR:-.}`; the `:-.`
# default is the old behaviour. This is the old relative form EXTENDED TO SUBDIRECTORIES: at any checkout
# root it picks exactly the copy `bash .claude/hooks/<name>.sh` picked, a submodule with its own hooks
# keeps them, and no environment variable can steer it.
# ⟳ Round 2 refuted asking git: an inherited `GIT_CEILING_DIRECTORIES` made discovery fail, and the
# fallback ran the MAIN checkout's plan gate from a worktree (2 -> 0). And because the hook's own
# existence took part in selection, a hook missing in the worktree ran MAIN's copy. Now the marker is
# the LAUNCHER, never the hook: once a checkout is chosen, a missing hook there is NOT RUN, never
# another checkout's copy.
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
root=""
dir=$(pwd -P 2>/dev/null) || dir=""
while [ -n "$dir" ]; do
  if [ -e "$dir/.git" ] && [ -f "$dir/.claude/hooks/run-hook.sh" ]; then root="$dir"; break; fi
  [ "$dir" = "/" ] && break
  dir=$(dirname "$dir")
done
[ -n "$root" ] || root="$project"

if [ ! -f "$root/.claude/hooks/$name" ]; then
  echo "run-hook.sh: no hook '$name' under $root/.claude/hooks — NOT RUN" >&2
  exit 1
fi
exec bash "$root/.claude/hooks/$name"
