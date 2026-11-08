#!/usr/bin/env bash
# PreToolUse hook — fires before every Bash tool call whose text CONTAINS `push` (`if: Bash(*push*)`), and
# acts only on one that runs `git … push`.
# ⟳ 2026-10-29 (backlog #393): the filter was `Bash(git push*)`, which a command starting `git -c … push`,
# `ALLOW_PLAN_LEAK=1 git push` or `cd x && git push` does not match, so RULE 3 below could never have fired.
# MEASURED on Claude Code 2.1.309 with a marker hook (not read from docs): `Bash(*push*)` fired on `echo push`,
# `git -c a=b push`, `ALLOW_PLAN_LEAK=1 git push` and `cd . && git push`, and NOT on `ls .` or `pwd .`, which
# an unfiltered control hook saw run. Only a deliberately obfuscated push (`$'\x70ush'`) slips past it — an
# out-of-scope evasion. Unfiltered, the hook cost a median 31 ms on every non-push Bash call.
# ⟳ 2026-11-08 (PR #542 round 1, C-F3): does the filter see `push` once bash has unquoted it? MEASURED on Claude
# Code 2.1.316 with marker hooks (a `claude -p` session in a scratch repository, an unfiltered control hook
# logging each command): `Bash(*push*)` FIRED for `echo git p"u"sh origin feat`, `echo git pu\sh origin feat`
# and `echo pu""sh`, and not for `echo hello`. So the filter matches the UNQUOTED words and launches this hook
# for those forms; it was not widened. Seen in live use the same day, cause not isolated: it also fired on
# commands with no `push` in them that used `$VAR`, `$?` or a pipe (observed, not measured).
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
  # backlog #534: `scripts/batch-ci.py plan --push` pushes `batch/<time>` with an explicit refspec.
  probe "a batch/ branch push is allowed (backlog #534)" "git push origin refs/heads/batch/20261106-1820:refs/heads/batch/20261106-1820" allow
  probe "the dangerous-push escape is honoured"         "ALLOW_DANGEROUS_PUSH=1 git push --force origin feat/x" allow
  # The branch escape must NOT grant the force decision — two intents, two flags.
  probe "the BRANCH escape does not authorise a force push" \
                                                        "ALLOW_DEFAULT_BRANCH_PUSH=1 git push --force origin feat/x" deny
  # A commit message mentioning a flag is not a flag — the measured multi-line defect.
  probe "the word --force inside another command is not a push flag" \
                                                        "git commit -m 'do not --force this' && git push origin feat/x" allow
  probe "a non-push git command is untouched"           "git status"                          allow
  # ── RULE 3 (backlog #393): the plan-leak gate's off-switches ──
  probe "⭐ -c core.hooksPath=… on a push is denied"     "git -c core.hooksPath=/dev/null push origin feat/x" deny
  probe "...and with -C and an odd case too"            "git -C /r -c core.HooksPath=/x push origin feat/x" deny
  probe "--config-env core.hooksPath on a push is denied" "git --config-env=core.hooksPath=HP push origin feat/x" deny
  probe "GIT_CONFIG_* naming core.hooksPath is denied"  "GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=core.hookspath GIT_CONFIG_VALUE_0=/x git push origin feat/x" deny
  probe "⭐ ALLOW_PLAN_LEAK=1 on a push is denied"        "ALLOW_PLAN_LEAK=1 git push origin feat/x" deny
  probe "...unless the owner's ALLOW_DANGEROUS_PUSH=1 is given too" \
                                                        "ALLOW_DANGEROUS_PUSH=1 ALLOW_PLAN_LEAK=1 git push origin feat/x" allow
  probe "⭐ a push behind -c is still SEEN as a push (here: its --force is denied)" \
                                                        "git -c user.name=x push --force origin feat/x" deny
  probe "an ordinary -c on a push is allowed"           "git -c user.name=x push origin feat/x" allow
  probe "a git config of hooksPath with no push is untouched" "git config core.hooksPath .githooks" allow
  probe "⭐ the reviewer's COMMENT form is denied (raw text, not a parse)" "git push origin feat/x # -c core.hooksPath=/dev/null" deny
  probe "⭐ QUOTES do not hide hooksPath"                "git -c \"core.hooks\"Path=/dev/null push origin feat/x" deny
  probe "⭐ nor a BACKSLASH"                              "git -c core.hooks\\Path=/dev/null push origin feat/x" deny
  probe "a QUOTED ALLOW_PLAN_LEAK=1 is denied"            "ALLOW_PLAN_LEAK='1' git push origin feat/x" deny
  probe "...and a quoted NAME"                            "\"ALLOW_PLAN_LEAK\"=1 git push origin feat/x" deny
  probe "ALLOW_PLAN_LEAK in ANY form is denied — even =0" "ALLOW_PLAN_LEAK=0 git push origin feat/x" deny
  probe "an unbalanced quote no longer denies a normal push" "git push origin \"feat/x" allow
  # ── backlog #428: detection reads the QUOTE-STRIPPED form, and FAILS CLOSED ──
  # Rule 1 depends on the CURRENT branch, so these run in a fixture clone whose default branch is
  # master, checked out on a feature branch — not in whatever checkout runs this self-test.
  fx="$(mktemp -d)" || { echo "  FAIL  could not make a fixture directory — NOT RUN"; exit 1; }
  trap 'rm -rf "$fx"' EXIT
  fxgit() { env -u GIT_DIR -u GIT_WORK_TREE -u GIT_INDEX_FILE GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_NOSYSTEM=1 \
              git "$@" >/dev/null 2>&1; }
  { fxgit init -q -b master "$fx/seed" \
    && fxgit -C "$fx/seed" -c user.name=t -c user.email=t@example.invalid commit -q --allow-empty -m seed \
    && fxgit clone -q "$fx/seed" "$fx/work" && fxgit -C "$fx/work" checkout -q -b feat/x; } \
    || { echo "  FAIL  could not build the fixture clone — NOT RUN"; exit 1; }
  self="$(cd "$(dirname "$self")" && pwd)/$(basename "$self")"
  here="$PWD"; cd "$fx/work" || exit 1
  probe "⭐ git \"push\" origin master is refused (backlog #428)"    "git \"push\" origin master"          deny
  probe "⭐ git -c x=y push origin master is refused"                "git -c x=y push origin master"       deny
  probe "⭐ git 'push' origin HEAD:master is refused"                "git 'push' origin HEAD:master"       deny
  probe "a PATH to git is refused (the fail-closed rule)"            "/usr/bin/git push origin master"     deny
  probe "a feature-branch push is allowed in the fixture"            "git push origin feat/x"              allow
  # ⚠ THE BOUND: both controls are ALLOWED here only because the fixture is on a FEATURE branch. On the
  # default branch the fail-closed rule REFUSES them (a segment with < 2 plain arguments pushes the
  # current branch) — measured by `scripts/push-command.py --self-test`, which builds both worlds.
  probe "control: git log --grep push is allowed on a feature branch" "git log --grep push"               allow
  probe "control: echo \"git push later\" is allowed on a feature branch" "echo \"git push later\""     allow
  # ── PR #542 round 1 ──
  # C-F1: bash joins a backslash-newline into one line; the detector must too, or the arguments vanish.
  probe "⭐ a line continuation does not hide the refspec (C-F1)"      "git push \\
  origin master"                                                                                          deny
  probe "...nor a --force on the continuation line"                  "git push \\
  --force origin feat/x"                                                                                  deny
  # C-F2: only real `git … push` segments are read once one is recognised.
  probe "C-F2: a commit message saying push…master, then a feature push, is allowed" \
                              "git commit -m \"push the fix, not master\" && git push origin feat/x"      allow
  probe "C-F2: git stash push naming master is allowed"              "git stash push -m \"before master merge\"" allow
  probe "C-F2: a feature push, then a --title naming push and master, is allowed" \
                              "git push origin feat/x && gh pr create --title \"Do not push to master\" --body-file b" allow
  # C-F4 / X-F2: a `+` refspec is a FORCE push, and names the branch after the `+`.
  probe "⭐ +feat/x is a force push and is refused (C-F4)"            "git push origin +feat/x"            deny
  probe "+master is refused even with the force escape (it is master)" \
                              "ALLOW_DANGEROUS_PUSH=1 git push origin +master"                            deny
  # X-F3 / C-F5: a destination still holding shell syntax is refused, never compared.
  probe "⭐ a subshell push to master is refused (X-F3)"              "(git push origin master)"           deny
  probe "a command-substitution push to master is refused"           "\$(git push origin master)"         deny
  probe "a backtick push to master is refused"                       "\`git push origin master\`"         deny
  probe "a redirection glued to master does not hide it"             "git push origin master>/dev/null"   deny
  probe "control: 2>&1 after a feature push is allowed"              "git push -u origin feat/x 2>&1 | tail -1" allow
  # The default branch itself: HEAD and @ name the current branch.
  fxgit -C "$fx/work" checkout -q master || { echo "  FAIL  could not check out master — NOT RUN"; exit 1; }
  probe "⭐ git push origin HEAD on master is refused (C-F4)"         "git push origin HEAD"               deny
  probe "git push -u origin HEAD on master is refused"               "git push -u origin HEAD"            deny
  probe "git push origin @ on master is refused"                     "git push origin @"                  deny
  probe "C-F2: git stash push -m wip on master is allowed"           "git stash push -m wip"              allow
  cd "$here" || exit 1
  # X-F4 / C-F7: input the hook cannot read REFUSES, saying NOT CHECKED — it was an allow.
  raw() {  # raw "<name>" "<payload>" — the payload as given, not built from a command
    got="$(printf '%s' "$2" | bash "$self" 2>/dev/null)"
    if printf '%s' "$got" | grep -q '"permissionDecision":"deny"' && printf '%s' "$got" | grep -q 'NOT CHECKED'; then
      pass=$((pass+1)); printf '  PASS  %s\n' "$1"
    else fail=$((fail+1)); printf '  FAIL  %s  (wanted a NOT CHECKED deny, got %s)\n' "$1" "${got:-allow}"; fi
  }
  raw "⭐ invalid JSON is refused, NOT CHECKED (X-F4)"                '{'
  raw "a null payload is refused"                                    'null'
  raw "a non-string command is refused"                              '{"tool_input":{"command":42}}'
  # jq missing: the hook must refuse with no jq at all — only `cat` on PATH, bash by absolute path.
  nojq="$fx/nojq"; mkdir -p "$nojq" && ln -s "$(command -v cat)" "$nojq/cat"
  got="$(printf '{"tool_input":{"command":"git push origin master"}}' | PATH="$nojq" "$BASH" "$self" 2>/dev/null)"
  if printf '%s' "$got" | grep -q '"permissionDecision":"deny"' && printf '%s' "$got" | grep -q 'NOT CHECKED'; then
    pass=$((pass+1)); printf '  PASS  %s\n' "⭐ no jq on PATH is refused, NOT CHECKED (C-F7)"
  else fail=$((fail+1)); printf '  FAIL  %s  (got %s)\n' "⭐ no jq on PATH is refused, NOT CHECKED (C-F7)" "${got:-allow}"; fi

  printf '\nself-test: %s/%s passed\n' "$pass" "$((pass+fail))"
  [ "$fail" -eq 0 ] && exit 0 || exit 1
fi

payload="$(cat)"

# ⛔ NO jq, NO DECISION (PR #542 round 1, C-F7): jq both reads the command and prints `deny`, so without it every
# rule failed OPEN (rc 0, empty stdout = allow). The refusal is a literal, the only output that needs no jq.
command -v jq >/dev/null 2>&1 || {
  printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Blocked: the push gate needs jq to read the command, and jq is not on PATH — NOT CHECKED. A gate that cannot run refuses; it never passes. Install jq, then re-run."}}'
  exit 0
}

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

# ⛔ A payload this cannot read is REFUSED (PR #542 round 1, X-F4): invalid JSON, or a command that is not a
# string, used to become `""` and an allow. `strings` yields nothing for a non-string, so `-e` exits non-zero.
cmd="$(printf '%s' "$payload" | jq -er '.tool_input.command | strings' 2>/dev/null)" \
  || deny "Blocked: the push gate could not read a string command from the hook payload — NOT CHECKED.
A gate that cannot read its input refuses; it never passes."

# ── IS THIS A PUSH? — `scripts/push-command.py`, FAIL CLOSED (backlog #428) ─────────────────────────
# ⟳ 2026-11-08: this was a `grep` over the RAW command, so `git "push" origin master` was not a push and
# every rule below was skipped. The detector deletes quotes and backslashes first (rule 3's form) and,
# when the words `git` and `push` both appear but no `git … push` invocation is recognised, reads the
# command as a push ANYWAY (mode `loose`). Its output: the mode, then one `push <args>` line per push
# segment, up to the next `;`, `&`, `|` or line end, redirections removed. The rules below read ONLY those.
# ⟳ PR #542 round 1: once a real `git … push` is recognised, only real push segments are read (C-F2), and
# `git commit` / `git stash` push words are arguments, never a push. A backslash-newline is one line (C-F1).
# ⚠ THE BOUND, the detector's docstring word for word in substance, measured by its `--self-test`: REFUSED —
# on the DEFAULT branch `git log --grep push`, `echo "git push later"` and `echo push; git status`; on ANY
# branch `gh pr create --title "git push origin master"`, `git log --oneline --grep "push to master"`, and
# a push whose arguments keep `(`, `)`, a backtick, `$(`, `<` or `>` (`(cd x && git push origin feat/x)`).
# ALLOWED — `git commit -m "push the fix, not master" && git push origin feat/x`, `git stash push -m …` on
# any branch, a feature push then `--title "Do not push to master"`, and `git push -u origin feat/x 2>&1`.
# ⛔ The detector not running is a REFUSAL, never a pass: a push gate that cannot tell is not a gate.
detector="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null && pwd)/scripts/push-command.py"
detected="$(printf '%s' "$cmd" | python3 "$detector" segments 2>/dev/null)"
detect_rc=$?
mode="$(printf '%s\n' "$detected" | head -1)"
case "$detect_rc:$mode" in
  0:none) allow ;;
  0:strict) loose_note="" ;;
  0:loose) loose_note="

(Read as a push by the fail-closed rule, backlog #428: the words \`git\` and \`push\` both appear, but no
\`git … push\` invocation was recognised. If this command does not push, reword it or put the text in a file.)" ;;
  142:*) deny "Blocked: the push gate's detector ran past its deadline and was stopped — NOT CHECKED.
\`scripts/push-command.py segments\` arms a deadline (\`DEADLINE_S\`) and the kernel ended it (exit 142, SIGALRM).
A gate that cannot finish refuses; it never passes. Shorten or split the command, then re-run." ;;
  *) deny "Blocked: the push gate could not tell whether this command pushes — NOT CHECKED.
\`scripts/push-command.py segments\` (beside this hook's checkout) exited ${detect_rc} with mode '${mode}'.
A gate that cannot run refuses; it never passes. Fix the detector, then re-run." ;;
esac
# One `push <args>` line per segment; rule 1 strips the leading word.
push_segs="$(printf '%s\n' "$detected" | tail -n +2)"

# ── RULE 2: never-routine push forms, checked BEFORE the branch rule ────────────────
# Ordering matters: `git push --force origin master` is dangerous for BOTH reasons, and
# the force message is the more useful one to show — it names the irreversible part.
if ! printf '%s' "$cmd" | grep -q 'ALLOW_DANGEROUS_PUSH=1'; then
  # ⚠ ONLY THE PUSH SEGMENTS, exactly as the branch rule does below and for the same
  # measured reason: a commit message or a quoted string elsewhere in a multi-line command
  # must not be read as a push flag. Each segment stops at a line end or a command separator.
  push_only="$push_segs"

  # ⚠ `--force-with-lease` CONTAINS `--force`, so a substring test would deny the safe
  # form while claiming to allow it. Match the flag as a whole word: end-of-string, or
  # followed by whitespace or `=`. Measured: without the `=` case, `--force-with-lease`
  # is correctly spared but `--force=` style would slip; without the boundary at all,
  # the guard does the opposite of what its own comment promises.
  # ⟳ PR #542 round 1 (C-F4): a refspec with a leading `+` (`git push origin +feat/x`) IS a force push of that
  # ref, with no flag at all, so it is refused here exactly as `--force` is.
  if printf '%s' "$push_only" | grep -qE '(^|[[:space:]])((--force|-f)([[:space:]=]|$)|\+[^[:space:]])'; then
    deny "Blocked: this is a bare \`--force\` push (or a \`+<refspec>\`, the same force), which DESTROYS remote history.

It is the only push that can lose work that is already on the remote, and nothing
on this branch has asked for it.

Instead:
  git push --force-with-lease ...    # refuses if the remote moved under you

That form is allowed by this hook and needs no flag.

Deliberate exception: re-run prefixed with ALLOW_DANGEROUS_PUSH=1${loose_note}"
  fi

  # ── RULE 3 (backlog #393): the plan-leak gate's two off-switches ──────────────────────────────────
  # The plan-leak gate is git's own pre-push hook (`.githooks/pre-push`); IT OWNS THE DECISION. This rule
  # refuses a push command whose RAW text mentions `hookspath` or `allow_plan_leak` ANYWHERE — casefolded,
  # with quotes and backslashes deleted first — unless the owner's ALLOW_DANGEROUS_PUSH=1 is also given.
  # ⛔ DELIBERATELY NOT A PARSER (PR #443, the coordinator's final rule after a third security pass). A shlex
  # step was tried and each refinement opened a new differential with bash (`#` comments, exact tokens) —
  # the wall. A substring over-denies, and a false denial costs a moment where a false pass costs a leak.
  # ⛔ THE BOUND, SAID PLAINLY: this reads command TEXT and is defence in depth only. The gate exists to
  # prevent ACCIDENTAL publication; an agent with a shell can always bypass git hooks (`--no-verify` behind
  # an alias, another clone, plumbing such as `git send-pack`, an exported variable). It is NOT a boundary
  # against a determined agent.
  # Known, OUT-OF-SCOPE evasions (a fourth security pass, declined deliberately): shell expansions (`$'…'`,
  # `${…}`), config includes (`include.path`, `includeIf`) and `GIT_CONFIG_*` set outside the command reach
  # `core.hooksPath` without the word appearing; they are deliberate, never accidental, and the pre-push
  # hook plus the SessionStart status check own the decision.
  norm="$(printf '%s' "$cmd" | tr -d "\"'\\\\" | tr '[:upper:]' '[:lower:]')"
  if printf '%s' "$norm" | grep -q 'hookspath'; then
    deny "Blocked: this push command mentions \`core.hooksPath\`, which can switch off git's pre-push hooks —
including the plan-leak gate (.githooks/pre-push, backlog #393), which refuses pushes that quote a private plan.

Push without it. If the owner means it: re-run prefixed with ALLOW_DANGEROUS_PUSH=1${loose_note}"
  fi
  if printf '%s' "$norm" | grep -q 'allow_plan_leak'; then
    deny "Blocked: this push command mentions ALLOW_PLAN_LEAK, the plan-leak gate's escape (backlog #393).
Skipping that gate is the owner's call, not an agent's: reword the commits it named instead.

If the owner has judged the hit a coincidence: re-run prefixed with ALLOW_DANGEROUS_PUSH=1 as well${loose_note}"
  fi

  if printf '%s' "$push_only" | grep -qE '(^|[[:space:]])--no-verify([[:space:]=]|$)'; then
    deny "Blocked: \`--no-verify\` skips the checks this push is supposed to clear.

That includes any local pre-push hook — so it is also the flag that would step over a
deliberate, temporary block someone put in place.

If a check is wrong, fix the check or say why in the PR. If you genuinely mean to
skip it: re-run prefixed with ALLOW_DANGEROUS_PUSH=1${loose_note}"
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
# The detector's segments stop at a line end and at a command separator, so only
# each push word and its own arguments are ever inspected.
push_cmds="$push_segs"
[ -n "$push_cmds" ] || allow

targets_default=0
unresolved=""
while IFS= read -r one; do
  [ -n "$one" ] || continue
  args="$(printf '%s' "$one" | sed -E 's/^push[[:space:]]*//')"
  toks="$(printf '%s' "$args" | tr ' \t' '\n\n' | grep -v '^-' | grep -v '^$' || true)"
  n="$(printf '%s\n' "$toks" | grep -c . || true)"
  # ⟳ PR #542 round 1 (X-F3, C-F5): a token that still holds shell syntax was never resolved by bash's
  # rules here — `(git push origin master)` gave `master)`, which compared unequal and was ALLOWED. The
  # detector has already removed redirections, so what is left is a subshell, a substitution or a
  # process substitution: refuse it rather than guess what it names.
  while IFS= read -r r; do
    case "$r" in *'('*|*')'*|*'`'*|*'$('*|*'<'*|*'>'*) unresolved="$r" ;; esac
  done <<< "$toks"
  if [ "$n" -ge 2 ]; then
    # `git push <remote> <refspec>...` — check each refspec's DESTINATION (after ':').
    for r in $(printf '%s\n' "$toks" | tail -n +2); do
      r="${r#+}"                         # +master -> master: the force is rule 2's; the ref is this rule's
      dest="${r##*:}"                    # HEAD:master -> master ; master -> master
      dest="${dest#refs/heads/}"
      # ⟳ PR #542 round 1 (C-F4): `HEAD` and `@` name the CURRENT branch — `git push -u origin HEAD` from
      # master pushes master, and was allowed because nothing resolved it.
      case "$dest" in HEAD|@) dest="$current_branch" ;; esac
      [ "$dest" = "$default_branch" ] && targets_default=1
    done
  else
    # `git push` or `git push <remote>` — pushes the CURRENT branch.
    [ "$current_branch" = "$default_branch" ] && targets_default=1
  fi
done <<EOF
$push_cmds
EOF

[ -z "$unresolved" ] || deny "Blocked: a push argument still holds shell syntax (\`${unresolved}\`), so this gate cannot tell
which branch it names — NOT CHECKED. A subshell \`( … )\`, a substitution (\`\$( … )\` or backticks) or a
process substitution around a push is refused rather than guessed at (PR #542 round 1).

Run the push as a plain command: git push -u origin <branch>${loose_note}"

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

Merge only on scripts/check-merge-ready.py READY; a HOLD goes to the owner.

Deliberate exception: re-run prefixed with ALLOW_DEFAULT_BRANCH_PUSH=1${loose_note}"
