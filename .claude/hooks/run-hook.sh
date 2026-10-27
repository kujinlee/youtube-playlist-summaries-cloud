#!/usr/bin/env bash
# The ONE way every hook in .claude/settings.json is launched (backlog #364):
#
#     bash "${CLAUDE_PROJECT_DIR:-.}"/.claude/hooks/run-hook.sh <name>.sh
#
# It runs <name>.sh from THE CHECKOUT THE SESSION IS WORKING IN, which is the nearest ancestor of the
# PHYSICAL cwd that contains `.git` (a directory in a main checkout, a file in a linked worktree or a
# submodule). Only when NO ancestor has `.git` does it use $CLAUDE_PROJECT_DIR.
#
# WHY THIS SHAPE, AND NOT ONE OF THE THREE THAT LOST (PR #409 r1–r3;
# docs/reviews/architecture-review-2026-10-26-hook-launch.md). Every lost design FELL BACK to another
# checkout when the cwd's checkout "did not qualify": r1 always ran the project dir's (main's) hooks,
# so a worktree's pending plan gate went 2 -> 0; r2 asked git, which `GIT_CEILING_DIRECTORIES` steered
# back to main; r3 required a launcher marker, so every worktree made before the launcher skipped to
# main. Each qualification made a new world that fell through to main. This launcher has NO
# qualification: the filesystem alone names the checkout, nothing in the environment is consulted
# except CLAUDE_PROJECT_DIR for the no-`.git` case, and no git process runs.
#   - The walk is `${dir%/*}`, not `dirname`: macOS `dirname` fails above 1024 characters, and `$(…)`
#     strips a trailing newline, which picks the sibling `nl` over `nl<newline>`.
#   - `pwd -P` is read through a sentinel `.` for the same reason.
#   - A hook MISSING in the chosen checkout is NOT RUN (exit 1, non-blocking, the owner's decision
#     2026-10-27) — never another checkout's copy, which is exactly how r2 ran main's gate.
#
# LIMITS, stated (the review's L1–L7):
#   L1 a session LAUNCHED in a subdirectory loads no project hooks at all — harness behaviour, out of
#      reach of any settings.json design.
#   L2 this file always comes from the project dir, so a branch that edits it is not exercised in its
#      own worktree until merged (its HOOKS are).
#   L3 the hooks' own `$(cd "$(dirname …)/../.." && pwd)` strips a trailing newline, so in a checkout
#      whose path ends in one the hook can read a sibling's state (backlog #375; not this file).
#   L4 a stray `.git` between the cwd and the checkout root (a fixture repo, a vendored clone) is the
#      checkout — NOT RUN when it has no hooks, the same as the old relative form at that root.
#      In THIS repo: `.remember/.git` is a nested repo inside the main checkout, so a session whose cwd
#      is under `.remember/` runs every hook NOT RUN, the push gate included (the old form: 127 there).
#   L5 NOT RUN exits 1: visible, not blocking.
#   L6 the hooks' internal `git` calls still follow the cwd and the GIT_* environment.
#   L7 Windows / PowerShell are not considered.
#
# Tested over real `git worktree add` / `git submodule add` worlds, with every lost design applied as a
# mutant and killed, by `python3 scripts/check-run-hook.py --self-test`.
[ $# -eq 1 ] || { echo "run-hook: exactly one argument (the hook's file name), got $#" >&2; exit 2; }
name=$1
case $name in
  '') echo "run-hook: refused an empty hook name" >&2; exit 2;;
  */*) echo "run-hook: refused hook name '$name' — a name, not a path" >&2; exit 2;;
  .*) echo "run-hook: refused hook name '$name' — it starts with '.'" >&2; exit 2;;
esac
dir=$(pwd -P && echo .) || { echo "run-hook: NOT RUN $name — cannot read the cwd" >&2; exit 1; }
dir=${dir%.}
dir=${dir%$'\n'}
root=
while :; do
  if [ -e "$dir/.git" ]; then root=$dir; break; fi
  if [ -z "$dir" ] || [ "$dir" = / ]; then break; fi
  dir=${dir%/*}
done
if [ -z "$root" ]; then root=${CLAUDE_PROJECT_DIR:-}; fi
if [ -z "$root" ]; then
  echo "run-hook: NOT RUN $name — no checkout contains $(pwd -P) and CLAUDE_PROJECT_DIR is unset" >&2
  exit 1
fi
hook="$root/.claude/hooks/$name"
if [ ! -f "$hook" ]; then
  echo "run-hook: NOT RUN $name — $root has no .claude/hooks/$name (no other checkout's copy is used)" >&2
  exit 1
fi
exec bash "$hook"
