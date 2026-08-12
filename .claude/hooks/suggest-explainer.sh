#!/usr/bin/env bash
# Suggest /explain-diff before a PR is opened. A REMINDER, NEVER A GATE — always exits 0.
#
# WHY THIS EXISTS
# ---------------
# The explain-diff skill shipped with no activation path (round-2 Blocking, 2026-08-12). The rule
# "generate an explainer before opening a code PR" was routed to docs/process-checklists.md, which
# CLAUDE.md does not @-include and whose read-trigger is "when you are working a gate" — and the
# skill is explicitly not a gate. So the rule lived in a file nobody opens for a thing that never
# triggers it. `gh pr create` is the machine-observable moment the rule describes.
#
# THE SCOPE RULE, AND WHY IT IS HERE RATHER THAN IN PROSE
# -------------------------------------------------------
# The first version keyed on PATHS TOUCHED — "lib/ app/ components/ …". Measured on PR #84, that
# rule fires on a comment-only edit to lib/ (zero added non-comment lines) where the explainer's
# load-bearing section, Boundaries touched, would have been one sentence saying "none". The right
# question is not which directories changed but WHETHER BEHAVIOUR OR A BOUNDARY MOVED — the same
# "blast radius, not size" distinction docs/dev-process.md Phase 5 already makes.
#
# WHAT THIS CAN AND CANNOT DO — read before trusting silence.
# Comment detection is textual: leading //, /*, *, #, --. It therefore MISSES a behavioural change
# hidden inside a block-comment continuation line, and MISCOUNTS a code line whose content merely
# starts with those characters. Both are tolerable because this is a reminder: a false negative
# costs a nudge you did not get, a false positive costs a nudge you ignore. It is NOT evidence that
# a change is behaviour-free, and nothing should cite it as such.
set -uo pipefail

CODE_PATHS=(lib app components worker supabase scripts tests)
CONFIG_GLOBS=('*.json' '*.yml' '*.yaml' 'Dockerfile' 'fly.toml' '*.config.*')
EXPLAINER_DIR="${EXPLAINER_DIR:-$HOME/explainers}"

note() { printf '%s\n' "$*"; }

root=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
cd "$root" || exit 0

branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null) || exit 0
base=$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|^origin/||')
base=${EXPLAIN_DIFF_BASE:-${base:-master}}   # override exists so the three branches below are testable
[ "$branch" = "$base" ] && exit 0

# "Cannot run" does not fail a reminder the way it fails a gate — but it must not pass as silence
# either, so say so instead of returning quietly.
if ! git rev-parse --verify --quiet "$base" >/dev/null; then
  note "ℹ️  explain-diff: could not resolve base branch '$base' — did NOT check whether this PR wants an explainer."
  exit 0
fi

diff_out=$(git diff "$base...HEAD" -- "${CODE_PATHS[@]}" "${CONFIG_GLOBS[@]}" 2>/dev/null) || {
  note "ℹ️  explain-diff: could not read the diff against '$base' — did NOT check whether this PR wants an explainer."
  exit 0
}

# Added/removed lines that are neither blank nor comment-only. Diff markers stripped first.
moved=$(printf '%s\n' "$diff_out" \
  | grep -E '^[+-]' \
  | grep -vE '^(\+\+\+|---)' \
  | sed -E 's/^[+-][[:space:]]*//' \
  | grep -vE '^$' \
  | grep -cvE '^(//|/\*|\*|#|--)' || true)

[ "${moved:-0}" -eq 0 ] && exit 0

sha=$(git rev-parse --short HEAD 2>/dev/null || echo unknown)
if compgen -G "$EXPLAINER_DIR/*-${sha}.html" >/dev/null 2>&1; then
  exit 0   # already explained at this exact head
fi

note ""
note "💡 explain-diff: this branch moves behaviour — ${moved} added/removed non-comment lines in code paths,"
note "   and no explainer exists for ${sha} in ${EXPLAINER_DIR}/."
note "   Want one before opening the PR?  /explain-diff"
note "   (A reminder, not a gate. Skip it freely — nothing checks. docs/explainer-spec.md)"
note ""
exit 0
