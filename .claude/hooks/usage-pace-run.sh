#!/usr/bin/env bash
# The ONE launcher of scripts/check-usage-pace.py for the three usage-pace hooks (backlog #522):
#
#     bash usage-pace-run.sh <prompt|spawn|wake>
#
# It runs the guard as it is on `origin/master`, NEVER the checked-out copy. A guard that governs the session's
# spending must not follow the branch: measured 2026-11-05 19:58, the prompt hook printed an unreviewed branch's new
# text from a worktree the session had cd'd into, and at 20:38 the old text again from a branch cut from master. A
# branch that loosened the stop would have loosened it for the session that wrote it.
#
# ⛔ CANNOT READ origin/master IS SAID, NEVER FALLEN BACK FROM: the checkout's copy is exactly what this refuses to
# trust. The prompt hook says so in context; spawn and wake allow with a systemMessage (unknown is not a stop).
# Bounds: the guard is read from THIS checkout's `refs/remotes/origin/master`, as last fetched — a stale fetch runs an older
# reviewed guard, never an unreviewed one. ⚠ THE THREAT IS ACCIDENT, NOT A HOSTILE BRANCH: this launcher, and
# the three hooks calling it, still come from the checkout (run-hook.sh's limit L2), so a branch editing THEM runs its
# edit; and the ref is locally writable. What it closes is the measured case — a branch's GUARD governing its session.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
mode="$1"
# ⛔ EVERY failure to run origin/master's guard goes through `cannot`, never a bare exit (r4 Codex BLOCKER: a TMPDIR
# naming a missing directory exited 1 with stderr only — a silent allow).
cannot() {
    msg="⚠ usage pace CANNOT RUN — $1 (backlog #522: the checkout's own copy is not trusted). Treat the usage verdict as NOT RUN; unknown is not a stop."
    if [ "$mode" = prompt ]; then
        python3 -c 'import json,sys; print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": sys.argv[1]}}))' "$msg"
    else
        # security review 11-05: stderr alone is not seen — say it as a systemMessage, and ALLOW (unknown is not a stop)
        python3 -c 'import json,sys; print(json.dumps({"systemMessage": sys.argv[1]}))' "$msg"
    fi
    exit 0
}
# hook-master-guard r1 Codex: the ref is FULLY QUALIFIED (a local branch named `origin/master` shadowed the short name),
# and every inherited GIT_* variable is unset for the read (a GIT_DIR pointed it at another repository's guard).
# r2 Codex: `--no-replace-objects`, since a `refs/replace` entry swapped the guard's blob while the ref stayed put.
if ! src="$(for v in $(compgen -e | grep '^GIT_'); do unset "$v"; done
            git --no-replace-objects -C "$REPO_ROOT" show refs/remotes/origin/master:scripts/check-usage-pace.py 2>/dev/null)" || [ -z "$src" ]; then
    cannot "refs/remotes/origin/master:scripts/check-usage-pace.py could not be read in $REPO_ROOT"
fi
# Run from a file NAMED check-usage-pace.py, not `python3 <(…)`: the ratchet contract finds a guard's caller by its
# invocation, and a process substitution hid the only one (the guard runs nowhere else). The file is per-call and removed.
tmp="$(mktemp -d "${TMPDIR:-/tmp}/usage-pace.XXXXXX" 2>/dev/null)" || cannot "no temp directory under ${TMPDIR:-/tmp}"
trap 'rm -rf "$tmp"' EXIT
printf '%s\n' "$src" > "$tmp/check-usage-pace.py" 2>/dev/null || cannot "the guard could not be written to $tmp"
python3 "$tmp/check-usage-pace.py" --hook "$mode" --root "$REPO_ROOT"
