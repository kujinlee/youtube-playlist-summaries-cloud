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
#
# ⟳ 2026-09-05 — THIS FILE NOW GUARDS TWO PUSH HAZARDS, AND THE FILENAME IS NARROWER
# THAN THE CONTENT. Kept anyway: the name is cited in `.claude/settings.json`, three
# live docs, and FIVE merged review documents. Renaming would mean editing historical
# review records to keep them true, and a record you rewrite is not a record. The
# concern is one — *which pushes are refused* — so it stays one hook rather than two.
#
# RULE 2: bare `--force` / `-f`, and `--no-verify`.
# WHY THESE TWO AND NOTHING ELSE. On 2026-09-05 a background agent armed a watcher to
# push a FEATURE branch automatically, with no human authorisation. Rule 1 does not
# cover that — it guards the default branch only. The obvious repair, gating every
# feature-branch push behind a prefix, was REJECTED BY THE USER and rightly: every
# legitimate push would need it too, the prefix becomes muscle memory, and a warning
# everyone types past is worse than none. This project has already measured that shape.
#
# So the line is drawn at pushes that are never routine:
#   * `--force` / `-f` DESTROYS remote history and is the only push that loses work.
#   * `--no-verify` SKIPS the very checks the push is supposed to clear — including,
#     recursively, any local hook standing between an agent and the remote.
# `--force-with-lease` is deliberately ALLOWED. It is the safe form, it refuses when
# the remote moved under you, and denying it would push people toward bare --force —
# the guard making the dangerous option the convenient one.
#
# ESCAPE: ALLOW_DANGEROUS_PUSH=1, same shape as above. Separate from the branch escape
# on purpose: authorising a force-push is not the same decision as authorising a push
# to master, and one env var for both would let either intent grant the other.
set -uo pipefail

# ── --self-test ─────────────────────────────────────────────────────────────────────
# ⚠ THIS HOOK SHIPPED FOR FIVE WEEKS WITH NO FALSIFIER, and adding a denial rule
# without one would repeat the defect this repo spent 2026-09-05 measuring: a guard
# whose tests do not prove it would notice itself breaking.
#
# Each case feeds the real stdin contract — the Claude Code hook JSON — through this
# very script and asserts on the decision, so the CASES DRIVE THE DELIVERED PATH, not
# a re-implementation of it. A re-implementation is what drifted from the tool by one
# earlier the same day.
if [ "${1:-}" = "--self-test" ]; then
  self="$0"; pass=0; fail=0
  probe() {  # probe "<name>" "<command>" "deny|allow"
    got="$(printf '{"tool_name":"Bash","tool_input":{"command":%s}}' \
            "$(printf '%s' "$2" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))')" \
          | bash "$self" 2>/dev/null)"
    if printf '%s' "$got" | grep -q '"permissionDecision":"deny"'; then act=deny; else act=allow; fi
    if [ "$act" = "$3" ]; then pass=$((pass+1)); printf '  PASS  %s\n' "$1"
    else fail=$((fail+1)); printf '  FAIL  %s  (wanted %s, got %s)\n' "$1" "$3" "$act"; fi
  }

  probe "a bare --force push is denied"                 "git push --force origin feat/x"      deny
  probe "...and its short form -f too"                  "git push -f origin feat/x"           deny
  # ⭐ THE CASE THAT MAKES THE BOUNDARY REAL: --force-with-lease CONTAINS --force, so a
  # substring test denies the safe form. Without this case the guard could invert its
  # own stated rule and every other case would still pass.
  probe "⭐ --force-with-lease is ALLOWED — the safe form must not be pushed away" \
                                                        "git push --force-with-lease origin feat/x" allow
  probe "--no-verify is denied"                         "git push --no-verify origin feat/x"  deny
  probe "an ordinary feature-branch push is allowed"    "git push origin feat/x"              allow
  probe "the dangerous-push escape is honoured"         "ALLOW_DANGEROUS_PUSH=1 git push --force origin feat/x" allow
  # The branch escape must NOT grant the force decision — two intents, two flags.
  probe "the BRANCH escape does not authorise a force push" \
                                                        "ALLOW_DEFAULT_BRANCH_PUSH=1 git push --force origin feat/x" deny
  # A commit message mentioning a flag is not a flag — the measured multi-line defect.
  probe "the word --force inside another command is not a push flag" \
                                                        "git commit -m 'do not --force this' && git push origin feat/x" allow
  probe "a non-push git command is untouched"           "git status"                          allow

  printf '\nself-test: %s/%s passed\n' "$pass" "$((pass+fail))"
  [ "$fail" -eq 0 ] && exit 0 || exit 1
fi

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

# ── RULE 2: never-routine push forms, checked BEFORE the branch rule ────────────────
# Ordering matters: `git push --force origin master` is dangerous for BOTH reasons, and
# the force message is the more useful one to show — it names the irreversible part.
if ! printf '%s' "$cmd" | grep -q 'ALLOW_DANGEROUS_PUSH=1'; then
  # ⚠ ISOLATE THE PUSH INVOCATION FIRST, exactly as the branch rule does below and for
  # the same measured reason: a commit message or a quoted string elsewhere in a
  # multi-line command must not be read as a push flag. `grep -o` is per-line and
  # `[^;&|]*` stops at a command separator.
  push_only="$(printf '%s' "$cmd" \
    | grep -oE 'git[[:space:]]+(-[^[:space:]]+[[:space:]]+)*push([[:space:]]+[^;&|]*)?' || true)"

  # ⚠ `--force-with-lease` CONTAINS `--force`, so a substring test would deny the safe
  # form while claiming to allow it. Match the flag as a whole word: end-of-string, or
  # followed by whitespace or `=`. Measured: without the `=` case, `--force-with-lease`
  # is correctly spared but `--force=` style would slip; without the boundary at all,
  # the guard does the opposite of what its own comment promises.
  if printf '%s' "$push_only" | grep -qE '(^|[[:space:]])(--force|-f)([[:space:]=]|$)'; then
    deny "Blocked: this is a bare \`--force\` push, which DESTROYS remote history.

It is the only push that can lose work that is already on the remote, and nothing
on this branch has asked for it.

Instead:
  git push --force-with-lease ...    # refuses if the remote moved under you

That form is allowed by this hook and needs no flag.

Deliberate exception: re-run prefixed with ALLOW_DANGEROUS_PUSH=1"
  fi

  if printf '%s' "$push_only" | grep -qE '(^|[[:space:]])--no-verify([[:space:]=]|$)'; then
    deny "Blocked: \`--no-verify\` skips the checks this push is supposed to clear.

That includes any local pre-push hook — so it is also the flag that would step over a
deliberate, temporary block someone put in place.

If a check is wrong, fix the check or say why in the PR. If you genuinely mean to
skip it: re-run prefixed with ALLOW_DANGEROUS_PUSH=1"
  fi
fi

# ── RULE 1: the default branch ──────────────────────────────────────────────────────
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

# Isolate ONLY the push invocation(s) before parsing refspecs.
#
# REGRESSION (found in live use, 2026-07-30): an earlier version ran the strip
# over the WHOLE command with `sed`, which is line-oriented — so in a multi-line
# command only the `git push` line was stripped and every other line survived
# into the refspec list. A commit message containing the word "master" was then
# read as a refspec, and the hook blocked a legitimate feature-branch push.
#
# `grep -o` is per-line and `[^;&|]*` stops at a command separator, so only the
# real push invocation and its own arguments are ever inspected.
push_cmds="$(printf '%s' "$cmd" \
  | grep -oE 'git[[:space:]]+(-[^[:space:]]+[[:space:]]+)*push([[:space:]]+[^;&|]*)?' || true)"
[ -n "$push_cmds" ] || allow

targets_default=0
while IFS= read -r one; do
  [ -n "$one" ] || continue
  args="$(printf '%s' "$one" | sed -E 's/^git[[:space:]]+(-[^[:space:]]+[[:space:]]+)*push[[:space:]]*//')"
  toks="$(printf '%s' "$args" | tr ' \t' '\n\n' | grep -v '^-' | grep -v '^$' || true)"
  n="$(printf '%s\n' "$toks" | grep -c . || true)"
  if [ "$n" -ge 2 ]; then
    # `git push <remote> <refspec>...` — check each refspec's DESTINATION (after ':').
    for r in $(printf '%s\n' "$toks" | tail -n +2); do
      dest="${r##*:}"                    # HEAD:master -> master ; master -> master
      dest="${dest#refs/heads/}"
      [ "$dest" = "$default_branch" ] && targets_default=1
    done
  else
    # `git push` or `git push <remote>` — pushes the CURRENT branch.
    [ "$current_branch" = "$default_branch" ] && targets_default=1
  fi
done <<EOF
$push_cmds
EOF

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
