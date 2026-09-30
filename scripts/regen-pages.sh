#!/usr/bin/env bash
# Rebuild every DERIVED explainer page from the sources tracked in this repo.
#
# WHY THIS EXISTS. The derived pages are deliberately NOT tracked — they are stale the moment their
# source moves. But until this script existed there was no documented way to produce them, so a
# fresh clone had no dashboard, no goals view, no backlog table and no feature tree, and nothing
# said how to get them. That gap, not the absence of committed HTML, was the real obstacle to a
# teammate using this repo (backlog #194).
#
# MEASURED 2026-09-30: all four rebuild in 21.1s total from tracked sources. `gh` is optional —
# `gen-dashboard` degrades loudly, printing what it could not fetch, and still writes the page.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

[ -e "$HOME/explainers" ] || { echo "REFUSING: ~/explainers does not exist. Run scripts/bootstrap-explainers.sh first." >&2; exit 2; }

rc=0
for g in gen-backlog-page gen-goals-page gen-features-page gen-dashboard; do
  printf '%-20s ' "$g"
  if python3 "scripts/$g.py" > /tmp/regen-$g.log 2>&1; then
    echo "ok"
  else
    echo "FAILED (see /tmp/regen-$g.log)"
    rc=1
  fi
done
exit $rc
