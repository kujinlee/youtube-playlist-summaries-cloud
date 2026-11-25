#!/usr/bin/env bash
# The ONE way every hook in .claude/settings.json is launched (backlog #364):
#
#     bash "${CLAUDE_PROJECT_DIR:-.}"/.claude/hooks/run-hook.sh <name>.sh
#
# It runs <name>.sh from THE CHECKOUT THE SESSION IS WORKING IN, which is the nearest ancestor of the
# PHYSICAL cwd that contains `.git` (a directory in a main checkout, a file in a linked worktree or a
# submodule). Only when NO ancestor has `.git` does it use $CLAUDE_PROJECT_DIR.
# ONE EXCEPTION (backlog #513): a `usage-pace-*` hook runs from the MAIN checkout of the session's repository,
# as git names it — a budget guard must not change with the branch being edited.
#
# WHY THIS SHAPE, AND NOT ONE OF THE THREE THAT LOST (PR #409 r1–r3;
# docs/reviews/architecture-review-2026-10-26-hook-launch.md). Every lost design FELL BACK to another
# checkout when the cwd's checkout "did not qualify": r1 always ran the project dir's (main's) hooks,
# so a worktree's pending plan gate went 2 -> 0; r2 asked git, which `GIT_CEILING_DIRECTORIES` steered
# back to main; r3 required a launcher marker, so every worktree made before the launcher skipped to
# main. Each qualification made a new world that fell through to main. This launcher has NO
# qualification: the filesystem alone names the checkout, nothing in the environment is consulted
# except CLAUDE_PROJECT_DIR for the no-`.git` case, and no git process runs — except for a usage-pace
# hook (below), where git names the main checkout under a GIT_*-free environment.
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
#   L5 NOT RUN exits 1: visible, not blocking. A usage-pace hook's NOT RUN exits 0 with a fixed JSON line instead
#      (backlog #513 r1 C3), as usage-pace-run.sh's own CANNOT RUN does.
#   L6 the hooks' internal `git` calls still follow the cwd and the GIT_* environment.
#   L7 Windows / PowerShell are not considered.
#   L8 the SHELL'S STARTUP ENVIRONMENT is trusted: an inherited BASH_ENV, ENV, SHELLOPTS or BASHOPTS is honoured by
#      bash before this file's first line runs (PR #419 r2: a BASH_ENV doing `cd "$CLAUDE_PROJECT_DIR"` made main's
#      hook run). The old relative form had the same exposure; hardening it for every hook is backlog #379.
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
# A usage hook's NOT RUN (backlog #513 r1 C3; why, below the walk): a fixed JSON line on stdout, exit 0. Defined
# before the walk so its two exits (an unreadable cwd; no checkout found) speak on that channel too (backlog #688 X2).
usage_not_run() {
  echo "run-hook: NOT RUN $name — $1" >&2
  if [ "$name" = usage-pace-prompt.sh ]; then
    printf '%s\n' '{"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "⚠ usage pace NOT RUN — run-hook.sh could not locate this hook in the main checkout (backlog #513: the copy in a worktree is not trusted; the reason is on stderr). Treat the usage verdict as NOT RUN; unknown is not a stop."}}'
  else
    printf '%s\n' '{"systemMessage": "⚠ usage pace NOT RUN — run-hook.sh could not locate this hook in the main checkout (backlog #513: the copy in a worktree is not trusted; the reason is on stderr). Treat the usage verdict as NOT RUN; unknown is not a stop."}'
  fi
  exit 0
}
dir=$(pwd -P && echo .) || {
  case $name in usage-pace-*) usage_not_run "cannot read the cwd (backlog #688)";; esac
  echo "run-hook: NOT RUN $name — cannot read the cwd" >&2; exit 1
}
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
  case $name in usage-pace-*) usage_not_run "no checkout contains $(pwd -P) and CLAUDE_PROJECT_DIR is unset (backlog #688)";; esac
  echo "run-hook: NOT RUN $name — no checkout contains $(pwd -P) and CLAUDE_PROJECT_DIR is unset" >&2
  exit 1
fi
# Backlog #513: a USAGE-PACE hook governs what the session spends, so it never follows the branch being edited.
# It runs from the MAIN checkout of the repository the session is in, and GIT names that checkout (r3 Phase 6,
# docs/reviews/architecture-review-2026-11-20-usage-hook-launcher.md: three rounds of hand-parsing `.git`/`commondir`
# each made a new layout disagree with git). The guard it calls is origin/master's (usage-pace-run.sh, backlog #522).
#   1. `git rev-parse --path-format=absolute --git-dir --git-common-dir --show-toplevel`, run with `-C $root`, under
#      an environment with EVERY exported GIT_* name unset (PR #409 r2 lost to GIT_DIR / GIT_CEILING_DIRECTORIES
#      steering git; here nothing but the directory steers it), under a 5 s alarm.
#   2. NOT RUN when the common dir is a bare repository (`core.bare`): it has no main checkout.
#   3. The main checkout is the one that OWNS the common dir: its parent when the common dir is named `.git` (git's own
#      main-worktree rule, the first entry `git worktree list` prints); else the work tree git reports from inside the
#      common dir (a submodule's `.git/modules/<name>`, whose core.worktree names it); else, when the session is NOT in
#      a linked worktree (git-dir == common-dir, a `--separate-git-dir` checkout), the session's own toplevel.
#      A linked worktree whose main checkout git cannot name (its main uses a separate git dir) is NOT RUN.
# ⛔ FAIL CLOSED: a git failure, a timeout, or output that is not exactly three lines is NOT RUN, and so is a main
# checkout with no .claude/hooks/<name> (below) — never the session's own copy. A usage hook's NOT RUN is said where the session sees it
# (r1 C3): exactly as usage-pace-run.sh's `cannot` does, a FIXED JSON line on stdout (additionalContext for the prompt
# hook, a systemMessage otherwise) and exit 0 (unknown is not a stop); the detail goes to stderr.
# ⚠ BOUNDS, stated (r3 M2): a layout git reads as a STANDALONE repository (a worktree's gitdir hand-given its own
# objects/, r3 B2) runs that checkout's own copy, because that is git's answer; a symlinked or misnamed `.git` makes
# its parent "main" exactly as git does (r1 C2); git's per-user config (~/.gitconfig) is still read.
# git, with no GIT_* variable from the session and a 5 s alarm (macOS has no `timeout`; SIGALRM survives the exec).
git_clean() (
  for v in $(compgen -e); do case $v in GIT_*) unset "$v";; esac; done
  exec perl -e 'alarm shift; exec @ARGV or exit 127' 5 git "$@"
)
case $name in
  usage-pace-*)
    out=$(git_clean -C "$root" rev-parse --path-format=absolute --git-dir --git-common-dir --show-toplevel 2>/dev/null) \
      || usage_not_run "git cannot read the repository at $root (backlog #513)"
    gd=${out%%$'\n'*}; rest=${out#*$'\n'}; common=${rest%%$'\n'*}; top=${rest#*$'\n'}
    case $top in *$'\n'*) usage_not_run "git's answer for $root is not three lines (a path holds a newline; backlog #513)";; esac
    if [ "$gd" = "$out" ] || [ "$common" = "$rest" ] || [ -z "$top" ]; then
      usage_not_run "git's answer for $root is not three lines (backlog #513)"
    fi
    bare=$(git_clean -C "$root" config --bool core.bare 2>/dev/null)
    if [ "$bare" = true ]; then
      usage_not_run "the repository of $root is bare ($common), so it has no main checkout (backlog #513)"
    fi
    if [ "${common##*/}" = .git ]; then
      main=${common%/*}
    elif owner=$(git_clean -C "$common" rev-parse --show-toplevel 2>/dev/null) && [ -n "$owner" ]; then
      main=$owner
    elif [ "$gd" = "$common" ]; then
      main=$top
    else
      usage_not_run "git names no main checkout for the worktree $top (its common dir $common; backlog #513)"
    fi
    root=$main;;
esac
hook="$root/.claude/hooks/$name"
if [ ! -f "$hook" ]; then
  case $name in usage-pace-*) usage_not_run "$root has no .claude/hooks/$name (backlog #513)";; esac
  echo "run-hook: NOT RUN $name — $root has no .claude/hooks/$name (no other checkout's copy is used)" >&2
  exit 1
fi
exec bash "$hook"
