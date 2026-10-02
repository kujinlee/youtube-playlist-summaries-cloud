#!/usr/bin/env bash
# Point this machine's assistant-memory path at the corpus tracked in this repo.
#
# WHY THIS EXISTS. The memory corpus is 146 files of hard-won project and craft knowledge — measured
# 2026-09-29 at 86% project-or-craft against 14% personal preference. It used to live OUTSIDE any
# repository, on one machine, with no remote, and NO TEAMMATE COULD OBTAIN IT. The user's ruling
# (2026-09-30): anything needed for proper team-work belongs inside the repo. It now lives at
# `docs/memory/` and is tracked like everything else.
#
# ⛔ WHY A SYMLINK AND NOT A COPY. The harness reads a path it DERIVES from the absolute repo path:
# `~/.claude/projects/<slug>/memory`, where `<slug>` is that path with every non-alphanumeric
# character replaced by `-` (see `scripts/recall-llm.py`, `memory_dir`). So the slug differs on every
# machine, and simply committing the files does NOT make the harness find them. A symlink makes the
# harness write straight into the repo: one home, no sync step, and every knowledge change shows up
# in `git status` as it happens.
#
# ⚠ AND THE FAILURE MODE THIS GUARDS. If the symlink is absent, nothing breaks loudly — the harness
# quietly creates a fresh empty directory at that path and the corpus silently stops being shared,
# which is the exact state this replaced. `scripts/check-memory-link.py` is the falsifier; run it in
# CI and locally. Being idempotent, this script is safe to re-run.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TRACKED="$REPO/docs/memory"
SLUG="$(printf '%s' "$REPO" | sed 's/[^A-Za-z0-9]/-/g')"
LINK="$HOME/.claude/projects/$SLUG/memory"

[ -d "$TRACKED" ] || { echo "REFUSING: $TRACKED does not exist — wrong repo, or the corpus is not checked out." >&2; exit 2; }

mkdir -p "$(dirname "$LINK")"

if [ -L "$LINK" ]; then
  current="$(readlink "$LINK")"
  if [ "$current" = "$TRACKED" ]; then echo "already linked: $LINK -> $TRACKED"; exit 0; fi
  echo "re-pointing an existing symlink (was: $current)"
  rm "$LINK"
elif [ -e "$LINK" ]; then
  # ⛔ NEVER destroy a real directory. It may hold entries that were never committed.
  keep="$LINK.pre-symlink-$(date +%Y%m%d-%H%M%S)"
  echo "a REAL directory is in the way. Preserving it at: $keep"
  echo "⚠ Compare it against $TRACKED and copy across anything it has that the repo does not."
  mv "$LINK" "$keep"
fi

ln -s "$TRACKED" "$LINK"
echo "linked: $LINK -> $TRACKED"
echo "entries now visible to the harness: $(find -L "$LINK" -maxdepth 1 -name '*.md' | wc -l | tr -d ' ')"
