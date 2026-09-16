#!/usr/bin/env bash
# "You changed one member of an enumerable set — here are the others." A REMINDER, NEVER A GATE.
# Fires before `git commit`, always exits 0.
#
# WHY THIS EXISTS
# ---------------
# r1 High (P2). `scripts/peer-sites.py` shipped with **no caller at all** — no hook, no CI step, no
# skill. The branch's whole premise is *"fix the instance, miss the sibling"* is a failure a written
# rule could not stop, "so this is the attempt at a mechanism". A script a human must remember to
# run is not a mechanism; it is the same rule with an executable attached, and it would have failed
# the same way. The reviewer's words, and they are right.
#
# WHY `git commit` AND NOT PR-OPEN TIME
# -------------------------------------
# The question this asks — *did you fix one arm of something and leave its siblings?* — is only
# actionable while the fix is still in your hands. `suggest-explainer.sh` keys on `gh pr create`
# because an explainer describes a finished branch; a sibling check that arrives after the branch is
# finished arrives after the moment it was for. Commit is the machine-observable instant the rule
# describes. It fires more often than once per branch; that is the point, and the script is silent
# on ~70% of python-touching commits (measured over 200 master commits), so the cost is bounded.
#
# ⛔ WHAT THIS IS NOT, STATED SO NOTHING CITES IT AS MORE.
# Silence here is NOT evidence that siblings were searched for. The script reads **python only**,
# **three container shapes**, and **only where the edit lands on a member's HEAD line** — an edit
# inside an arm's body is invisible, which was 79 of 84 partially-touched containers in the replay.
# `docs/review-method.md` Q2 step 5 is the obligation; this is one cheap input to it.
set -uo pipefail

[ "${PEER_SITES_HOOK_DISABLE:-}" = "1" ] && exit 0

note() { printf '%s\n' "$*"; }

# ── --self-test: the RULE (does this command warrant a look?), separated from the FETCH ──────
# ⚠ SEPARATED DELIBERATELY. Three ratchets in this repo went eight days untestable because their
# entry point needed a world. `_wants_check` is pure string work and is cased below; everything
# that needs a git lives past it.
_wants_check() {
  case "$1" in
    *"git commit"*|*"git"*"commit"*) ;;
    *) return 1 ;;
  esac
  # A commit that only records a message change or an amend of nothing still diffs, so no further
  # filtering here — the script's own silence is the filter.
  case "$1" in
    *--dry-run*) return 1 ;;
    *) return 0 ;;
  esac
}

if [ "${1:-}" = "--self-test" ]; then
  ok=0; fail=0
  t() { # name, command-string, expected rc
    if _wants_check "$2"; then got=0; else got=1; fi
    if [ "$got" = "$3" ]; then ok=$((ok+1)); else fail=$((fail+1)); note "  [FAIL] $1: got $got want $3"; fi
  }
  t "a plain commit is checked"              'git commit -m "x"'            0
  t "a commit with -F is checked"            'git commit -F /tmp/msg'       0
  t "an amend is checked"                    'git commit --amend --no-edit' 0
  t "a -C flagged commit is checked"         'git -C /repo commit -m "x"'   0
  t "a DRY RUN is not checked"               'git commit --dry-run'         1
  t "a push is not a commit"                 'git push origin peer-sites'   1
  t "a status is not a commit"               'git status --short'           1
  t "an unrelated command is not checked"    'ls -la'                       1
  t "a commit named inside a MESSAGE still checks — a false positive costs a nudge" \
                                             'git commit -m "git commit"'   0
  note "$((ok+fail)) cases: $ok passed, $fail failed"
  [ "$fail" -eq 0 ] || exit 1
  exit 0
fi

payload=$(cat 2>/dev/null || true)
cmd=$(printf '%s' "$payload" | python3 -c \
  'import json,sys
try: print(json.load(sys.stdin).get("tool_input", {}).get("command", ""))
except Exception: print("")' 2>/dev/null || true)

_wants_check "$cmd" || exit 0

root=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
cd "$root" || exit 0
[ -x scripts/peer-sites.py ] || [ -f scripts/peer-sites.py ] || exit 0

branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null) || exit 0
base=$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|^origin/||')
base=${PEER_SITES_BASE:-${base:-master}}
[ "$branch" = "$base" ] && exit 0

# ⛔ "CANNOT RUN" IS SAID OUT LOUD, NOT SWALLOWED. It does not fail a reminder the way it fails a
# gate, but silence here is indistinguishable from "no siblings found", which is the one reading
# this must never invite.
if ! git rev-parse --verify --quiet "$base" >/dev/null; then
  note "ℹ️  peer-sites: could not resolve base '$base' — did NOT check for sibling sites."
  exit 0
fi

# ⚠ `timeout` IS NOT ON macOS, and the first version assumed it was. Caught by live-firing the hook
# rather than by reading it: the run exited 127 and the CANNOT-RUN branch above reported it — the
# design working, but on every commit, for everyone on a Mac. coreutils ships it as `gtimeout`;
# absent both, run bare — `peer-sites.py` already bounds its own `subprocess.run` at 30s.
if command -v timeout >/dev/null 2>&1; then _tmo=(timeout 20)
elif command -v gtimeout >/dev/null 2>&1; then _tmo=(gtimeout 20)
else _tmo=(); fi
# ⚠ `${a[@]+"${a[@]}"}` — an EMPTY array under `set -u` is an unbound variable, not an empty list.
out=$(${_tmo[@]+"${_tmo[@]}"} python3 scripts/peer-sites.py --diff "$base" 2>&1)
rc=$?
# ⛔⛔ ONLY rc=0 IS A COMPLETED RUN, AND THE FIRST VERSION ALSO ACCEPTED rc=1 FOR NO REASON — which
# made this hook FAIL OPEN. Measured, on its own second live-fire: the bash error above exited 1,
# the error text landed in `$out`, `grep 'you changed'` found nothing, and the hook exited silently.
# A broken advisory that looks exactly like "no siblings found" is the precise failure this file's
# header warns nothing should cite it as. rc=2 is `peer-sites.py`'s own CANNOT RUN (a file git could
# not diff); anything else is this hook being broken. Both must SPEAK.
if [ "$rc" -ne 0 ]; then
  note "ℹ️  peer-sites: exited $rc — treat this as NOT CHECKED, not as 'no siblings'."
  note "$out"
  exit 0
fi
printf '%s' "$out" | grep -q 'you changed' || exit 0

note ""
note "💡 peer-sites — you changed SOME members of an enumerable set. The others:"
note ""
note "$out"
note "   Fix the siblings too, or say why not. A reminder, not a gate — nothing checks."
note "   ⚠ Silence from this script is NOT a sibling search: python only, three shapes, head"
note "     lines only. docs/review-method.md Q2 step 5 is the actual obligation."
note ""
exit 0
