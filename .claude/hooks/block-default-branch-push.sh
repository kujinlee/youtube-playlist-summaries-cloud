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
  # ⟳ PR #542 round 2: this was ALLOWED (PR #443 dropped a shlex step that refused it). An unbalanced quote is
  # outside the closed language the detector reads exactly (round 3, Phase 6), so it REFUSES. bash itself refuses
  # to run this line, so the refusal costs nothing.
  probe "an unbalanced quote beside a push is refused, NOT CHECKED" "git push origin \"feat/x" deny
  # ── backlog #428: ONE reader, `scripts/push-command.py decide`, exact over a closed language or refusing ──
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
  # ⟳ round 3: `log` is an inert git subcommand and `echo` a text command, so both controls are allowed on the
  # default branch too (the r2 loose layer refused them there) — measured by `scripts/push-command.py --self-test`.
  probe "control: git log --grep push is allowed on a feature branch" "git log --grep push"               allow
  probe "control: echo \"git push later\" is allowed on a feature branch" "echo \"git push later\""     allow
  # ── PR #542 round 1 ──
  # C-F1: bash joins a backslash-newline into one line; the detector must too, or the arguments vanish.
  probe "⭐ a line continuation does not hide the refspec (C-F1)"      "git push \\
  origin master"                                                                                          deny
  probe "...nor a --force on the continuation line"                  "git push \\
  --force origin feat/x"                                                                                  deny
  # C-F2: a commit message or a --title naming push and master is text, never a push.
  probe "C-F2: a commit message saying push…master, then a feature push, is allowed" \
                              "git commit -m \"push the fix, not master\" && git push origin feat/x"      allow
  probe "C-F2: git stash push naming master is allowed"              "git stash push -m \"before master merge\"" allow
  probe "C-F2: a feature push, then a --title naming push and master, is allowed" \
                              "git push origin feat/x && gh pr create --title \"Do not push to master\" --body-file b" allow
  # C-F4 / X-F2: a `+` refspec is a FORCE push, and names the branch after the `+`.
  probe "⭐ +feat/x is a force push and is refused (C-F4)"            "git push origin +feat/x"            deny
  probe "+master is refused even with the force escape (it is master)" \
                              "ALLOW_DANGEROUS_PUSH=1 git push origin +master"                            deny
  # X-F3 / C-F5: a subshell, a substitution and a backtick are outside the closed language: refused.
  probe "⭐ a subshell push to master is refused (X-F3)"              "(git push origin master)"           deny
  probe "a command-substitution push to master is refused"           "\$(git push origin master)"         deny
  probe "a backtick push to master is refused"                       "\`git push origin master\`"         deny
  probe "a redirection glued to master does not hide it"             "git push origin master>/dev/null"   deny
  probe "control: 2>&1 after a feature push is allowed"              "git push -u origin feat/x 2>&1 | tail -1" allow
  # ── PR #542 round 2: quoted text is never shell syntax, and every invocation is judged ──
  # ── PR #542 round 3: the heredoc, --attr-source and bundled-flag forms ──
  probe "⭐ a heredoc body does not hide a push to master (C-F1 r3)" "cat <<EOF
git stash list '
EOF
git push origin master # '"                                                                             deny
  probe "⭐ --attr-source does not make stash the subcommand (C-F2 r3)" "git --attr-source stash push origin master" deny
  probe "⭐ a bundled -uf is refused (C-F5 r3)"                        "git push -uf origin feat/x"         deny
  probe "⭐ a quoted '>' does not eat --force (X-F2 r2)"             "git push origin feat/x --push-option='>' --force" deny
  probe "⭐ a quoted ';git stash' does not exempt a push to master (X-F3 r2)" \
                              "git -c alias.x=';git stash' push origin master"                            deny
  probe "⭐ a push before a # decoy is judged (X-F1 r2)"              "/usr/bin/git push origin master # git push origin feat/x" deny
  # PR #542 round 6, C-F1 control: ONE document stays allowed however it is laid out — spread over lines, with a
  # trailing newline — so the one-document rule cannot pass by refusing every payload.
  got="$(printf '{\n  "tool_name": "Bash",\n  "tool_input": {\n    "command": "git push origin feat/x"\n  }\n}\n' \
          | bash "$self" 2>/dev/null)"
  if [ -z "$got" ]; then pass=$((pass+1)); printf '  PASS  %s\n' "r6 control: ONE multi-line document, a feature push, is allowed"
  else fail=$((fail+1)); printf '  FAIL  %s  (got %s)\n' "r6 control: ONE multi-line document, a feature push, is allowed" "$got"; fi
  probe "...while a one-document push to master is still refused" "git push origin master"             deny
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
  # PR #542 round 6, C-F1: TWO documents. Master's `jq -r` judged both commands' text and refused the first pair
  # (hookspath); the round 5 read dropped the non-string first command and ALLOWED the feature push after it.
  raw "⭐ two JSON documents (a non-string hookspath, then a feature push) are refused (r6 C-F1)" \
'{"tool_input":{"command":["hookspath"]}}
{"tool_name":"Bash","tool_input":{"command":"git push origin feat/x"}}'
  raw "two JSON documents (an object command, then a bare git push) are refused" \
'{"tool_input":{"command":{"a":"origin master"}}}
{"tool_name":"Bash","tool_input":{"command":"git push"}}'
  raw "two documents that are BOTH plain feature pushes are refused too (one document, exactly)" \
'{"tool_name":"Bash","tool_input":{"command":"git push origin feat/x"}}{"tool_name":"Bash","tool_input":{"command":"git push origin feat/x"}}'
  raw "an empty payload (zero documents) is refused"                 ''
  # jq missing: the hook must refuse with no jq at all — only `cat` on PATH, bash by absolute path.
  nojq="$fx/nojq"; mkdir -p "$nojq" && ln -s "$(command -v cat)" "$nojq/cat"
  got="$(printf '{"tool_input":{"command":"git push origin master"}}' | PATH="$nojq" "$BASH" "$self" 2>/dev/null)"
  if printf '%s' "$got" | grep -q '"permissionDecision":"deny"' && printf '%s' "$got" | grep -q 'NOT CHECKED'; then
    pass=$((pass+1)); printf '  PASS  %s\n' "⭐ no jq on PATH is refused, NOT CHECKED (C-F7)"
  else fail=$((fail+1)); printf '  FAIL  %s  (got %s)\n' "⭐ no jq on PATH is refused, NOT CHECKED (C-F7)" "${got:-allow}"; fi
  # ── PR #542 round 8, X-F1: an OVERSIZED reason. Codex's four repro payloads, ~1.1 MB each, built as FILES (an argv
  # would hit the very limit under test). The detector refuses each (`option`, quoting the unknown option in full);
  # the old `deny` put that reason in jq's argv, jq never ran, and the hook printed NOTHING — an allow.
  # `git push origin feat/x --zzz…` then the tail, through the delivered hook. A hook run over 1.1 MB costs ~1.7 s
  # (bash copies the string several times), so the four run CONCURRENTLY: ~2 s of wall time, not ~7.
  python3 -c 'import json,sys
for i,t in enumerate(sys.argv[2:]):
    c="git push origin feat/x --"+"z"*1100000+" "+t
    open("%s/big%d.json"%(sys.argv[1],i),"w").write(json.dumps({"tool_name":"Bash","tool_input":{"command":c}}))' \
    "$fx" "--force" "--no-verify" "master" "HEAD:master" \
    || { echo "  FAIL  could not build the ~1.1 MB payloads — NOT RUN"; exit 1; }
  for i in 0 1 2 3; do bash "$self" < "$fx/big$i.json" > "$fx/big$i.out" 2>/dev/null & done; wait
  i=0
  for t in "--force" "--no-verify" "master" "HEAD:master"; do
    got="$(cat "$fx/big$i.out")"; i=$((i+1))
    if printf '%s' "$got" | grep -q '"permissionDecision":"deny"'; then
      pass=$((pass+1)); printf '  PASS  %s\n' "⭐ a ~1.1 MB unknown option, then $t, is refused (r8 X-F1)"
    else fail=$((fail+1)); printf '  FAIL  %s  (wanted deny, got %s)\n' "⭐ a ~1.1 MB unknown option, then $t, is refused (r8 X-F1)" "${got:-allow}"; fi
  done
  # The refusal is still READABLE: bounded to REASON_MAX characters with a marker, not the 1.1 MB option.
  if [ "${#got}" -lt 6000 ] && printf '%s' "$got" | grep -q 'reason truncated by the push gate'; then
    pass=$((pass+1)); printf '  PASS  %s\n' "the oversized reason is truncated with a marker (r8 X-F1)"
  else fail=$((fail+1)); printf '  FAIL  %s  (got %s characters)\n' "the oversized reason is truncated with a marker (r8 X-F1)" "${#got}"; fi
  # ⚠ A ~1.1 MB FEATURE push with NO unknown option is REFUSED, and that is accepted, not wanted: MASTER'S hook (the
  # floor, run when the reader allows) does not finish a 50 KB push line inside its 2.5 s budget (`floor-not-run`,
  # measured 2026-11-08), and at 1.1 MB `decide` itself passes its 3 s deadline (exit 142). Either way NOT CHECKED.
  # Not cased here: it costs the full 3 s deadline. `push-command.py --self-test` cases the deadline and the floor
  # budget. What IS cased: serialization itself failing — a jq that reads the payload but cannot print — still denies.
  fakejq="$fx/fakejq"; mkdir -p "$fakejq"
  printf '#!/bin/sh\ncase "$1" in -Rsc) exit 1 ;; esac\nexec %s "$@"\n' "$(command -v jq)" > "$fakejq/jq" && chmod +x "$fakejq/jq"
  got="$(printf '{"tool_input":{"command":"git push --force origin feat/x"}}' | PATH="$fakejq:$PATH" bash "$self" 2>/dev/null)"
  if printf '%s' "$got" | grep -q '"permissionDecision":"deny"' && printf '%s' "$got" | grep -q 'could not print its reason'; then
    pass=$((pass+1)); printf '  PASS  %s\n' "⭐ a jq that cannot serialize the reason still yields the literal deny (r8 X-F1)"
  else fail=$((fail+1)); printf '  FAIL  %s  (got %s)\n' "⭐ a jq that cannot serialize the reason still yields the literal deny (r8 X-F1)" "${got:-allow}"; fi

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

# ⛔ EVERY EXIT FROM deny EMITS A DENY (PR #542 round 8, X-F1). It was `jq -nc --arg reason "$1"`: a reason that
# quotes a ~1.1 MB unknown option put the reason in jq's ARGUMENT LIST, past the OS limit, so jq never ran, deny
# exited 0 with empty stdout, and empty stdout is ALLOW (Codex's repro: master refused all four payloads). So:
#   1. the reason never goes in an argv — it reaches jq on STDIN (`-R` raw, `-s` one string), and it is bounded
#      first, to REASON_MAX characters with a marker, so the message stays readable as well as deliverable;
#   2. whatever jq does — fails, is killed, prints nothing or prints something else — if its output is not a deny,
#      a FIXED LITERAL deny is printed instead, the same shape as the no-jq refusal above. Printing is `printf`, a
#      builtin: no argv limit applies to it.
REASON_MAX=4000
deny() {
  local r="$1" out len
  len="${#r}"
  if [ "$len" -gt "$REASON_MAX" ]; then
    r="${r:0:$REASON_MAX}
… [reason truncated by the push gate: $len characters, the first $REASON_MAX shown]"
  fi
  out="$(printf '%s' "$r" | jq -Rsc '{hookSpecificOutput: {hookEventName: "PreToolUse",
          permissionDecision: "deny", permissionDecisionReason: .}}' 2>/dev/null)"
  case "$out" in
    '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny",'*) printf '%s\n' "$out" ;;
    *) printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny","permissionDecisionReason":"Blocked: the push gate refused this command but could not print its reason (serializing it failed) — NOT CHECKED. A refusal that cannot be explained is still a refusal (PR #542 round 8). Shorten or split the command, then re-run."}}' ;;
  esac
  exit 0
}

# ⛔ A payload this cannot read is REFUSED (PR #542 round 1, X-F4): invalid JSON, or a command that is not a
# string, used to become `""` and an allow. `strings` yields nothing for a non-string, so `-e` exits non-zero.
# ⟳ PR #542 round 6 (C-F1): the payload must be EXACTLY ONE JSON document. `jq -r` reads a stream, so on two
# documents master's hook printed both commands into one string, while `strings` dropped a non-string first one
# and judged only the second: master refused `{"tool_input":{"command":["hookspath"]}}` + a feature push, and this
# allowed it. `-s` slurps the stream into an array, and anything but one document yields nothing: refused. Claude
# Code sends one object per call, so this refuses only input it never sends — stricter than both readers.
cmd="$(printf '%s' "$payload" | jq -ser 'if length == 1 then .[0].tool_input.command | strings else empty end' \
        2>/dev/null)" \
  || deny "Blocked: the push gate could not read a string command from the hook payload (exactly one JSON document) — NOT CHECKED.
A gate that cannot read its input refuses; it never passes."


# ── THE DECISION — `scripts/push-command.py decide`, ONE reader for every rule (backlog #428) ───────────
# ⟳ PR #542 round 3, Phase 6 (`docs/reviews/architecture-review-2026-11-08-push-detector.md`): this hook used to
# read the command three times — the detector's segments, a regex for rule 2 over them, and a token loop for rule
# 1 — and an early `none -> allow` put rules 2 and 3 behind the detector's reading. Each round's leak lived in a
# gap between two readers. Now the detector reads the command ONCE, over a closed language it reads exactly
# (anything outside it is refused), and judges all three rules; this hook only resolves the branches and prints
# the refusal. The rules, the bound and what is out of scope are in that file's docstring, not restated here.
# ⟳ PR #542 round 5: NO WORSE THAN MASTER, by construction. When the reader allows, the detector runs MASTER'S OWN
# HOOK (`scripts/push-floor-master.sh`, git blob `ddb129b5`, verified before each run) as a floor: rule `floor` is
# master's refusal with master's message; `floor-not-run` is the floor failing, and refuses.
#
# Resolve the default branch rather than hardcoding "master": prefer the remote HEAD, fall back to whichever of
# main/master exists. No remote -> a PR is impossible, so rule 1 does not apply (the detector is told).
has_remote=0
[ -n "$(git remote 2>/dev/null)" ] && has_remote=1
default_branch="$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|^origin/||')"
if [ -z "$default_branch" ]; then
  for b in main master; do
    git show-ref --verify --quiet "refs/heads/$b" && { default_branch="$b"; break; }
  done
fi
current_branch="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")"

# ⛔ The detector not running is a REFUSAL, never a pass: a push gate that cannot tell is not a gate.
detector="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." 2>/dev/null && pwd)/scripts/push-command.py"
detected="$(printf '%s' "$cmd" | python3 "$detector" decide "$current_branch" "$default_branch" "$has_remote" 2>/dev/null)"
detect_rc=$?
rule=""
case "$detect_rc:$detected" in
  0:allow) allow ;;
  "0:deny "?*" "?*) rule="${detected#deny }"; reason="${rule#* }"; rule="${rule%% *}" ;;
  142:*) deny "Blocked: the push gate's detector ran past its deadline and was stopped — NOT CHECKED.
\`scripts/push-command.py decide\` arms a deadline (\`DEADLINE_S\`) and the kernel ended it (exit 142, SIGALRM).
A gate that cannot finish refuses; it never passes. Shorten or split the command, then re-run." ;;
esac
[ -n "$rule" ] || deny "Blocked: the push gate could not tell whether this command pushes — NOT CHECKED.
\`scripts/push-command.py decide\` (beside this hook's checkout) exited ${detect_rc} and printed '${detected}'.
A gate that cannot run refuses; it never passes. Fix the detector, then re-run."

PLAIN="Run the push as its own plain command: git push -u origin <branch>"
case "$rule" in
  # ── RULE 2: never-routine push forms ──
  force) deny "Blocked: this is a bare \`--force\` push (or a \`+<refspec>\`, the same force), which DESTROYS remote
history (${reason}).

It is the only push that can lose work that is already on the remote, and nothing
on this branch has asked for it.

Instead:
  git push --force-with-lease ...    # refuses if the remote moved under you

That form is allowed by this hook and needs no flag.

Deliberate exception: re-run prefixed with ALLOW_DANGEROUS_PUSH=1" ;;
  no-verify) deny "Blocked: \`--no-verify\` skips the checks this push is supposed to clear.

That includes any local pre-push hook — so it is also the flag that would step over a
deliberate, temporary block someone put in place.

If a check is wrong, fix the check or say why in the PR. If you genuinely mean to
skip it: re-run prefixed with ALLOW_DANGEROUS_PUSH=1" ;;
  # ── RULE 3 (backlog #393): the plan-leak gate's two off-switches ──
  # The plan-leak gate is git's own pre-push hook (`.githooks/pre-push`); IT OWNS THE DECISION. The detector refuses
  # a command mentioning `hookspath` or `allow_plan_leak` ANYWHERE (quote-blind, casefolded) BEFORE it lexes, so no
  # reading can put this rule behind an allow. ⛔ DELIBERATELY NOT A PARSE (PR #443): a substring over-denies, and a
  # false denial costs a moment where a false pass costs a leak. Config includes, `GIT_CONFIG_*` set outside the
  # command and shell expansions reach `core.hooksPath` without the word: out of scope, owned by pre-push and the
  # SessionStart status check.
  hookspath) deny "Blocked: this push command mentions \`core.hooksPath\`, which can switch off git's pre-push hooks —
including the plan-leak gate (.githooks/pre-push, backlog #393), which refuses pushes that quote a private plan.

Push without it. If the owner means it: re-run prefixed with ALLOW_DANGEROUS_PUSH=1" ;;
  plan-leak) deny "Blocked: this push command mentions ALLOW_PLAN_LEAK, the plan-leak gate's escape (backlog #393).
Skipping that gate is the owner's call, not an agent's: reword the commits it named instead.

If the owner has judged the hit a coincidence: re-run prefixed with ALLOW_DANGEROUS_PUSH=1 as well" ;;
  # ── RULE 1: the default branch ──
  # REGRESSION (found in live use, 2026-07-30): an earlier version stripped the push line with `sed` over the WHOLE
  # command, so a commit message containing "master" was read as a refspec. The detector judges each command's
  # own words only.
  default-branch) deny "Blocked: this pushes to '${default_branch}', the default branch (${reason}).

docs/dev-process.md Phase 5 — branch + PR is the standard path, and the axis is
blast radius, not size. Direct pushes are the exception only when the repo has
no remote; this one has '$(git remote | head -1)'.

Instead:
  git checkout -b <feat|fix|chore>/<slug>     # commits already made? branch here,
  git reset --hard origin/${default_branch}   # then rewind ${default_branch}
  git push -u origin <branch>
  gh pr create --repo kujinlee/youtube-playlist-summaries-cloud ...

Merge only on scripts/check-merge-ready.py READY; a HOLD goes to the owner.

Deliberate exception: re-run prefixed with ALLOW_DEFAULT_BRANCH_PUSH=1" ;;
  # ── RULE 1, composed (PR #542 round 4, X-F2): this hook resolves the current branch BEFORE the command runs, so a
  # `checkout`/`switch`/`cd`/… beside a push could make it push a branch this gate never judged ──
  branch-change) deny "Blocked: this command changes the branch or the repository a push acts on, in the same command
as the push (${reason}). The push gate resolved the current branch before any of it runs, so it
cannot tell where that push would land — NOT CHECKED (backlog #428).

Run the branch change first, then the push as its own plain command: git push -u origin <branch>" ;;
  # ── PR #542 round 5: master's own hook, kept as a floor — the branch refuses whatever master refused ──
  floor) deny "${reason}

(This is the previous push hook's rule, kept as a floor: PR #542 round 5, backlog #428.)" ;;
  floor-not-run) deny "Blocked: the push gate's floor (master's own push hook, \`scripts/push-floor-master.sh\`) did not
run cleanly: ${reason} — NOT CHECKED. A gate that cannot run refuses; it never passes (PR #542 round 5)." ;;
  # ── the reading itself: a command the push gate cannot read exactly ──
  outside) deny "Blocked: this command mentions push and uses shell syntax outside what the push gate reads exactly
(${reason}) — NOT CHECKED. Bash could run a push this gate cannot see, so it refuses rather than guess
(PR #542 round 3, backlog #428).

${PLAIN}" ;;
  option|code-runner|unjudged) deny "Blocked: the push gate cannot judge this command: ${reason} — NOT CHECKED.
It reads only plain \`git push\` commands and known options, so it refuses rather than guess (backlog #428).

${PLAIN}" ;;
  *) deny "Blocked: the push gate's detector gave a rule this hook does not know ('${rule}') — NOT CHECKED.
A gate that cannot read its own verdict refuses; it never passes." ;;
esac
