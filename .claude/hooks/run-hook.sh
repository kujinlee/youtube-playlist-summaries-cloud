#!/usr/bin/env bash
# The ONE way every hook in .claude/settings.json is launched (backlog #364):
#
#     bash "${CLAUDE_PROJECT_DIR:-.}"/.claude/hooks/run-hook.sh <name>.sh
#
# It runs <name>.sh from THE CHECKOUT THE SESSION IS WORKING IN, which is the nearest ancestor of the
# PHYSICAL cwd that contains `.git` (a directory in a main checkout, a file in a linked worktree or a
# submodule). Only when NO ancestor has `.git` does it use $CLAUDE_PROJECT_DIR.
# ONE EXCEPTION (backlog #513): a `usage-pace-*` hook found in a LINKED WORKTREE runs from that worktree's
# MAIN checkout instead — a budget guard must not change with the branch being edited.
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
# Backlog #513: a USAGE-PACE hook governs what the session spends, so it never follows the branch being edited.
# From a linked worktree it runs from the MAIN checkout, found on the filesystem alone (the worktree's `.git` file
# names its git dir, whose `commondir` names the main checkout's `.git`); no git process runs. The guard it calls
# is origin/master's (usage-pace-run.sh, backlog #522).
# ⛔ FAIL CLOSED (r1 C1, X1, X2): once `.git` is a FILE, every step of locating the main checkout must succeed, or
# the hook is NOT RUN — never the worktree's own copy, which is exactly what this refuses to trust. NOT RUN when:
#   - `.git` names no gitdir, or cannot be read;
#   - the gitdir or its `commondir` holds a newline (`.git` is read to EOF, never to its first line, which once
#     truncated `main<newline>name/...` to a path whose missing commondir fell through to the worktree's copy);
#   - the gitdir is missing or unreadable (a renamed main checkout, a pruned worktree);
#   - there is no `commondir` and the gitdir's PATH is a worktree's, `<common>/worktrees/<name>` (r2: decided by
#     that shape, never by what the gitdir holds — an `objects/` made in a worktree's gitdir once ran its own copy);
#   - there is no `commondir` and the gitdir is not a repository (`is_repo`: HEAD, objects/ and refs/). A
#     SUBMODULE's gitdir (`.git/modules/<name>`) and a main checkout's `--separate-git-dir` ARE repositories at a
#     non-worktree path, so they keep their own copy, as before;
#   - the common dir is not named `.git` (a bare repository, a separate git dir under another name);
#   - the common dir is not a repository (`is_repo`; r2: an empty directory named `decoy/.git` once ran the decoy's
#     copy);
#   - the gitdir is not physically `<common>/worktrees/<name>` — the common dir does not CONTAIN this worktree's
#     gitdir, so it is some other repository (r2). This is the back-pointer read from the common dir's side: a
#     decoy passes it only by holding this worktree's gitdir, which makes it, to git too, this worktree's repository.
# ⚠ WHICH CHECKOUT IS "MAIN" (r1 C2): the common dir's parent, which is what `git worktree list` itself names
# first. When the main checkout's `.git` is a SYMLINK, or a separate git dir happens to be named `.git`, that is a
# directory the owner may not think of as main, and nothing on disk or in git distinguishes it. It runs only if
# it holds .claude/hooks/<name>; otherwise NOT RUN. Either way the worktree's own copy is never run.
# A usage hook's NOT RUN is said where the session sees it (r1 C3): exactly as usage-pace-run.sh's `cannot` does,
# a FIXED JSON line on stdout (additionalContext for the prompt hook, a systemMessage otherwise) and exit 0
# (unknown is not a stop); the detail goes to stderr.
# A git repository directory, as git's own discovery requires one: a HEAD file and objects/ and refs/ directories.
is_repo() { [ -f "$1/HEAD" ] && [ -d "$1/objects" ] && [ -d "$1/refs" ]; }
usage_not_run() {
  echo "run-hook: NOT RUN $name — $1" >&2
  if [ "$name" = usage-pace-prompt.sh ]; then
    printf '%s\n' '{"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "⚠ usage pace NOT RUN — run-hook.sh could not locate this hook in the main checkout (backlog #513: the copy in a worktree is not trusted; the reason is on stderr). Treat the usage verdict as NOT RUN; unknown is not a stop."}}'
  else
    printf '%s\n' '{"systemMessage": "⚠ usage pace NOT RUN — run-hook.sh could not locate this hook in the main checkout (backlog #513: the copy in a worktree is not trusted; the reason is on stderr). Treat the usage verdict as NOT RUN; unknown is not a stop."}'
  fi
  exit 0
}
case $name in
  usage-pace-*)
    if [ -f "$root/.git" ]; then
      line=
      IFS= read -r -d '' line < "$root/.git" 2>/dev/null  # to EOF; its status is not read (EOF is not an error)
      line=${line%$'\n'}
      gitdir=${line#gitdir: }
      if [ "$gitdir" = "$line" ] || [ -z "$gitdir" ]; then
        usage_not_run "$root/.git names no gitdir, so its main checkout cannot be located (backlog #513)"
      fi
      case $gitdir in *$'\n'*) usage_not_run "the gitdir named by $root/.git holds a newline (backlog #513)";; esac
      case $gitdir in /*) ;; *) gitdir="$root/$gitdir";; esac
      gitdir=$(cd -P -- "$gitdir" 2>/dev/null && pwd -P && echo .) || gitdir=
      gitdir=${gitdir%.}
      gitdir=${gitdir%$'\n'}
      if [ -z "$gitdir" ]; then
        usage_not_run "the gitdir named by $root/.git is missing or unreadable (backlog #513)"
      fi
      if [ -f "$gitdir/commondir" ]; then
        common=
        IFS= read -r -d '' common < "$gitdir/commondir" 2>/dev/null
        common=${common%$'\n'}
        case $common in *$'\n'*) usage_not_run "the commondir of $gitdir holds a newline (backlog #513)";; esac
        case $common in /*) ;; *) common="$gitdir/$common";; esac
        common=$(cd -P -- "$common" 2>/dev/null && pwd -P && echo .) || common=
        common=${common%.}
        common=${common%$'\n'}
        # The common dir is the main checkout's `.git` directory (a bare repository's is not, and is NOT RUN).
        if [ "${common##*/}" != .git ]; then
          usage_not_run "the main checkout of the worktree $root cannot be located (the worktree's own copy is not used, backlog #513)"
        fi
        if ! is_repo "$common"; then
          usage_not_run "the common dir $common is not a git repository (no HEAD, objects/ or refs/; backlog #513 r2)"
        fi
        if [ "${gitdir%/*}" != "$common/worktrees" ]; then
          usage_not_run "the gitdir $gitdir is not inside its common dir's worktrees/ (backlog #513 r2)"
        fi
        root=${common%/*}
      elif [ "${gitdir%/*/*}/worktrees" = "${gitdir%/*}" ]; then
        usage_not_run "the gitdir $gitdir is a worktree's (…/worktrees/<name>) and has no commondir (backlog #513 r2)"
      elif ! is_repo "$gitdir"; then
        usage_not_run "the gitdir $gitdir has no commondir and is not a repository (backlog #513)"
      fi
    fi;;
esac
hook="$root/.claude/hooks/$name"
if [ ! -f "$hook" ]; then
  case $name in usage-pace-*) usage_not_run "$root has no .claude/hooks/$name (backlog #513)";; esac
  echo "run-hook: NOT RUN $name — $root has no .claude/hooks/$name (no other checkout's copy is used)" >&2
  exit 1
fi
exec bash "$hook"
