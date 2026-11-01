#!/usr/bin/env bash
# PreCompact (auto): defer an AUTO compaction while work is in flight, up to 1.5 x W (backlog #440).
# `scripts/check-compaction-boundary.py --hook` decides, logs the verdict to the main checkout's gitignored
# `.claude/compaction-boundary.log`, and on ALLOW runs `precompact-snapshot.sh` with the same payload — the
# snapshot is chained here, not registered beside it, so a BLOCKED call does not take a snapshot each time.
#
# ⛔ ALWAYS EXIT 0. Exit 2 would block compaction on this hook's OWN failure and wedge the session. If the check
# dies (rc != 0) its output is dropped — never a half-printed decision — and the snapshot runs here instead,
# with no payload, so it records its own CANNOT RUN rather than nothing.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
out="$(python3 "$REPO_ROOT/scripts/check-compaction-boundary.py" --hook)"
rc=$?
if [ "$rc" -eq 0 ]; then
  [ -n "$out" ] && printf '%s\n' "$out"
else
  echo "compaction-boundary: CANNOT RUN (exit $rc) — compaction ALLOWED, snapshot taken without a payload" >&2
  bash "$REPO_ROOT/.claude/hooks/precompact-snapshot.sh" </dev/null
fi
exit 0
