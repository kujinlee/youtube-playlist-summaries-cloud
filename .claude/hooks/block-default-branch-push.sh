#!/usr/bin/env bash
# PreToolUse hook — fires before every Bash tool call matching `git push`.
#
# Enforces the branch+PR rule in docs/dev-process.md Phase 5: work goes on a
# branch and merges through a PR. Direct pushes to the default branch are the
# exception, allowed only when the repo has no remote (a PR is impossible then).
#
# WHY A HOOK, NOT PROSE: the rule was written on 2026-07-30 after the assistant
# pushed three commits — including a new lib/ module — straight to master. Prose
# in a 400-line always-loaded document did not prevent it and would not prevent
# a repeat. This is the enforcement.
#
# WHY PreToolUse RATHER THAN A GIT pre-push HOOK: a git hook lives in .git/hooks
# (not version-controlled, needs `git config core.hooksPath` per clone) and is
# bypassed by `git push --no-verify`. This one is committed, needs no per-clone
# setup, and the assistant cannot skip it.
#
# Contract: reads the Claude Code hook JSON on stdin, prints a permissionDecision
# on stdout. Silence = allow.
#
#   { "tool_name": "Bash", "tool_input": { "command": "git push origin master" } }
#
# ESCAPE HATCH: prefix the command with ALLOW_DEFAULT_BRANCH_PUSH=1. Deliberate
# and greppable — "I know, and I mean it" — rather than a silent bypass flag.
set -uo pipefail

payload="$(cat)"
cmd="$(printf '%s' "$payload" | jq -r '.tool_input.command // ""' 2>/dev/null || echo "")"

allow() { exit 0; }   # silence = allow

deny() {
  jq -nc --arg reason "$1" '{
    hookSpecificOutput: {
      hookEventName: "PreToolUse",
      permissionDecision: "deny",
      permissionDecisionReason: $reason
    }
  }'
  exit 0
}

# Not a push at all (the `if` filter should prevent this, but be defensive).
printf '%s' "$cmd" | grep -Eq '(^|[;&|[:space:]])git[[:space:]]+(-[^[:space:]]+[[:space:]]+)*push([[:space:]]|$)' || allow

# Explicit opt-out.
printf '%s' "$cmd" | grep -q 'ALLOW_DEFAULT_BRANCH_PUSH=1' && allow

# No remote -> a PR is impossible, so a direct commit is the sanctioned path.
[ -n "$(git remote 2>/dev/null)" ] || allow

# Resolve the default branch rather than hardcoding "master": prefer the remote
# HEAD, fall back to whichever of main/master exists.
default_branch="$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|^origin/||')"
if [ -z "$default_branch" ]; then
  for b in main master; do
    git show-ref --verify --quiet "refs/heads/$b" && { default_branch="$b"; break; }
  done
fi
[ -n "$default_branch" ] || allow

current_branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")"

# Strip the leading `git push` and its flags to inspect the refspec arguments.
args="$(printf '%s' "$cmd" | sed -E 's/.*git[[:space:]]+(-[^[:space:]]+[[:space:]]+)*push[[:space:]]*//')"
refspecs="$(printf '%s' "$args" | tr ' ' '\n' | grep -v '^-' | grep -v '^$' || true)"
# Drop the remote name (first non-flag token) to leave only refspecs.
positional_count="$(printf '%s' "$refspecs" | grep -c . || true)"

targets_default=0
if [ "$positional_count" -ge 2 ]; then
  # `git push <remote> <refspec>...` — check the refspec's DESTINATION (after ':').
  for r in $(printf '%s' "$refspecs" | tail -n +2); do
    dest="${r##*:}"                      # HEAD:master -> master ; master -> master
    dest="${dest#refs/heads/}"
    [ "$dest" = "$default_branch" ] && targets_default=1
  done
else
  # `git push` or `git push <remote>` — pushes the CURRENT branch.
  [ "$current_branch" = "$default_branch" ] && targets_default=1
fi

[ "$targets_default" -eq 1 ] || allow

deny "Blocked: this pushes to '${default_branch}', the default branch.

docs/dev-process.md Phase 5 — branch + PR is the standard path, and the axis is
blast radius, not size. Direct pushes are the exception only when the repo has
no remote; this one has '$(git remote | head -1)'.

Instead:
  git checkout -b <feat|fix|chore>/<slug>     # commits already made? branch here,
  git reset --hard origin/${default_branch}   # then rewind ${default_branch}
  git push -u origin <branch>
  gh pr create --repo kujinlee/youtube-playlist-summaries-cloud ...

Merging stays a human gate — open the PR, do not merge.

Deliberate exception: re-run prefixed with ALLOW_DEFAULT_BRANCH_PUSH=1"
