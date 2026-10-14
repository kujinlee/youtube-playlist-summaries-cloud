#!/usr/bin/env bash
# SessionStart + Stop hook — snapshots the session-memory store into ITS OWN local git repo.
#
# WHY THIS EXISTS
# ---------------
# Measured 2026-10-14: `.remember/` held 96 days of dailies, the handoff, the archives and
# `core-memories.md` with NO git and NO backup of any kind. The project repo's only remote is
# PUBLIC, so committing them there was not an option; losing them was not either. `.remember/`
# is ignored by the project repo, so a repository INSIDE it has no path to that remote by
# construction — the outer repo's dirty-path count was identical before and after creating one,
# and the outer repo cannot see it at all.
#
# WHY BOTH EVENTS, NOT JUST SessionStart
# --------------------------------------
# SessionStart alone snapshots what the PREVIOUS session left, so everything the CURRENT session
# writes stays uncommitted until some later session happens to begin. Measured: `now.md` and the
# daily note are rewritten repeatedly WITHIN a session (both at 04:03 on 2026-10-14), and activity
# is bursty — 240 log files on 2026-10-13, then zero on three consecutive days. The incident this
# whole mechanism answers destroyed a file WITHIN one session, which SessionStart-only would not
# have caught. Stop closes that window to one session.
#
# ⛔ WHY IT RESOLVES THE MAIN CHECKOUT RATHER THAN ITS OWN REPO ROOT
# -----------------------------------------------------------------
# A session running in a linked WORKTREE writes to the MAIN checkout's `.remember/` — the vendor
# redirects it (`_resolve_memory_project_dir`, `lib-memory-dir.sh`). A hook resolving its own
# location would look in the worktree, find nothing, and silently never snapshot — a hook that
# reports success while protecting nothing. `--git-common-dir`'s parent is the main checkout from
# BOTH a worktree and a main checkout; verified in both before this was written.
#
# ⚠ IT ALWAYS EXITS 0, DELIBERATELY. A backup must never block a session, and `Stop` treats a
# non-zero exit as a refusal. Every failure path is therefore silent-and-zero — which means this
# cannot tell you it is broken. `--self-test` is the only thing that can, so run it after edits.
#
#   --self-test   6 cases, including that each silent-failure path is actually taken.
set -uo pipefail

snapshot() {
    # $1 = a directory that may contain a `.remember/` store with its own git repo.
    local main="$1" store
    store="$main/.remember"
    [ -d "$store/.git" ] || return 3            # not set up on this machine — nothing to do
    git -C "$store" add -A >/dev/null 2>&1 || return 4
    git -C "$store" diff --cached --quiet >/dev/null 2>&1 && return 5   # nothing changed
    git -C "$store" -c user.useConfigOnly=false \
        commit -q -m "snapshot: ${SNAPSHOT_EVENT:-hook} $(date '+%Y-%m-%d %H:%M:%S %Z')" \
        >/dev/null 2>&1 || return 4
    return 0
}

main_checkout() {
    local here common
    here="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)" || return 1
    common="$(git -C "$here" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)" || return 1
    (cd "$common/.." && pwd) || return 1
}

self_test() {
    local pass=0 fail=0 tmp
    check() { # name expected actual
        if [ "$2" = "$3" ]; then pass=$((pass+1));
        else fail=$((fail+1)); printf '  [FAIL] %s: got %s want %s\n' "$1" "$3" "$2"; fi; }

    tmp="$(mktemp -d)"
    mkdir -p "$tmp/norepo/.remember"
    snapshot "$tmp/norepo"; check "a store with no git repo is skipped" 3 "$?"

    mkdir -p "$tmp/none"
    snapshot "$tmp/none"; check "a directory with no store at all is skipped" 3 "$?"

    mkdir -p "$tmp/live/.remember"
    git -C "$tmp/live/.remember" init -q .
    git -C "$tmp/live/.remember" config user.email t@t
    git -C "$tmp/live/.remember" config user.name t
    echo one > "$tmp/live/.remember/a.md"
    snapshot "$tmp/live"; check "a changed store COMMITS" 0 "$?"
    check "and the commit really landed" 1 "$(git -C "$tmp/live/.remember" rev-list --count HEAD)"

    snapshot "$tmp/live"; check "an unchanged store does NOT commit" 5 "$?"
    check "so the history did not grow" 1 "$(git -C "$tmp/live/.remember" rev-list --count HEAD)"

    rm -rf "$tmp"
    printf '%s/%s passed\n' "$pass" "$((pass+fail))"
    [ "$fail" -eq 0 ] || return 1
}

if [ "${1:-}" = "--self-test" ]; then
    self_test
    exit $?
fi

# Hook path. Consume stdin so the caller never blocks on a full pipe, then always succeed.
cat >/dev/null 2>&1 || true
SNAPSHOT_EVENT="${SNAPSHOT_EVENT:-hook}"
if MAIN="$(main_checkout)"; then snapshot "$MAIN" || true; fi
exit 0
