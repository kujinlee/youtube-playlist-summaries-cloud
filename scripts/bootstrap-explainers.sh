#!/usr/bin/env bash
# Point this machine's ~/explainers at the pages tracked in this repo.
#
# WHY. The AUTHORED explainer pages — topic and brief write-ups, 56 of them — have NO source in git.
# The HTML IS the artefact, so losing the file loses the work. They now live in `docs/explainers/`
# and are tracked. ⛔ The DERIVED pages (dashboard, goals, backlog-table, features) are gitignored
# inside that same directory: generators rebuild them in 21.1s from sources already in the repo, and
# a committed copy is stale the moment its source moves — the defect the `regen-*` hooks exist to
# prevent. Run `scripts/regen-pages.sh` after this to produce them.
#
# ⛔ WHY A SYMLINK. `scripts/explainer-serve.py` hardcodes `Path.home()/"explainers"` as its root,
# and every generator writes there. Linking keeps one home: the server and the generators need no
# change, and authored pages land in git as they are written.
#
# ⚠ The server reads its root once at start-up. If it is running, restart it after this.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TRACKED="$REPO/docs/explainers"
LINK="$HOME/explainers"

[ -d "$TRACKED" ] || { echo "REFUSING: $TRACKED does not exist — wrong repo, or not checked out." >&2; exit 2; }

if [ -L "$LINK" ]; then
  current="$(readlink "$LINK")"
  if [ "$current" = "$TRACKED" ]; then echo "already linked: $LINK -> $TRACKED"; exit 0; fi
  echo "re-pointing an existing symlink (was: $current)"
  rm "$LINK"
elif [ -e "$LINK" ]; then
  # ⛔ NEVER destroy a real directory: it may hold authored pages never committed, plus
  # `questions.md`, which is where readers' questions accumulate.
  keep="$LINK.pre-symlink-$(date +%Y%m%d-%H%M%S)"
  echo "a REAL directory is in the way. Preserving it at: $keep"
  echo "⚠ Compare it against $TRACKED — check for authored pages, _explainer-style.css and questions.md."
  mv "$LINK" "$keep"
fi

ln -s "$TRACKED" "$LINK"
echo "linked: $LINK -> $TRACKED"
echo "pages now visible: $(find -L "$LINK" -maxdepth 1 -name '*.html' | wc -l | tr -d ' ')"
