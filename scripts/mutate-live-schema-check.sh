#!/usr/bin/env bash
# MUTATION HARNESS for check-live-schema.py — proves the gate goes RED on the state that matters.
#
#   ./scripts/mutate-live-schema-check.sh
#     exit 0 = every mutation was caught
#     exit 1 = a mutation SURVIVED — the gate is not load-bearing
#     exit 2 = could not run (treat as NOT RUN)
#
# WHY A SCRATCH DATABASE AND NOT A ROLLED-BACK TRANSACTION.
# `check-live-schema.py` opens its OWN connection, so it cannot see an uncommitted transaction in
# another session. The obvious proof — create the object in a transaction, run the gate, roll back —
# is therefore impossible, and an earlier draft of the M4 plan specified exactly that impossible
# proof. This builds the state FOR REAL in a throwaway database and drops it afterwards. The shared
# stack is never touched: `an-instrument-that-edits-the-repo-corrupts-its-peers`.
#
# THE MUTATION THAT MATTERS is #2: the measured post-`drop table … cascade` state. Every M4 table and
# column is gone, so a gate checking only those two kinds returns PASS — over a database where
# `ensure_workspace_for_profile()` still fires on signup and calls a table that no longer exists.
# That is a live outage the gate would have blessed, and it is why the gate checks five kinds.
set -uo pipefail
cd "$(dirname "$0")/.."
CONTAINER="${PGCONTAINER:-supabase_db_youtube-playlist-summaries-cloud}"
SCRATCH="m4_gate_mutation_probe"
SPEC="docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema"

psql_scratch() { docker exec -i "$CONTAINER" psql -U postgres -d "$SCRATCH" -tAq "$@"; }
gate() { python3 ./scripts/check-live-schema.py --database "$SCRATCH" "$1" >/dev/null 2>&1; }

cleanup() {
  docker exec -i "$CONTAINER" psql -U postgres -d postgres -tAq \
    -c "drop database if exists $SCRATCH (force);" >/dev/null 2>&1
}
trap cleanup EXIT

if ! docker exec -i "$CONTAINER" psql -U postgres -d postgres -tAq -c "select 1" >/dev/null 2>&1; then
  echo "CANNOT RUN — no Postgres at container $CONTAINER. Treat this as NOT RUN." >&2
  exit 2
fi

cleanup
docker exec -i "$CONTAINER" psql -U postgres -d postgres -tAq \
  -c "create database $SCRATCH;" >/dev/null 2>&1 || { echo "CANNOT RUN — could not create scratch db" >&2; exit 2; }

fail=0
report() { # name expected_exit actual_ok
  if [ "$2" = "$3" ]; then echo "  ✓ $1"; else echo "  ✗ $1 — MUTATION SURVIVED"; fail=1; fi
}

echo "═══ mutation 1: an EMPTY database must read ABSENT ═══"
gate --expect-absent && r=pass || r=fail
report "empty db -> --expect-absent passes" pass "$r"

echo "═══ building the REAL pre-M4 schema into the scratch db ═══"
# ⟳ MEASURED: hand-written stand-in tables are NOT enough — the spec needs the `auth` schema,
# `handle_new_user`, pgcrypto in `extensions`, and the real constraint shapes. The faithful and
# simpler route is to clone the live pre-M4 schema, then apply the spec on top.
if ! docker exec -i "$CONTAINER" sh -c \
      "pg_dump -U postgres -d postgres --schema-only --no-owner --no-privileges | psql -U postgres -d $SCRATCH -q" \
      >/dev/null 2>&1; then
  echo "CANNOT RUN — could not clone the live schema into the scratch db. Treat this as NOT RUN." >&2
  exit 2
fi
if ! { cat "$SPEC"/01_workspaces.sql "$SPEC"/03_generations.sql "$SPEC"/04_artifacts.sql; } \
     | docker exec -i "$CONTAINER" psql -U postgres -d "$SCRATCH" -tAq -v ON_ERROR_STOP=1 >/dev/null 2>&1; then
  echo "CANNOT RUN — the spec did not apply to the cloned schema. Treat this as NOT RUN." >&2
  exit 2
fi
gate --expect-present && r=pass || r=fail
report "M4 applied -> --expect-present passes" pass "$r"

echo "═══ mutation 2 ⭐ THE ONE THAT MATTERS: drop table … cascade ═══"
psql_scratch -c "drop table workspaces cascade;" >/dev/null 2>&1
gate --expect-absent && r=pass || r=fail
report "post-cascade residue -> --expect-absent FAILS (triggers survive)" fail "$r"
echo "     surviving live-table triggers, for the record:"
psql_scratch -c "select '       '||t.tgname from pg_trigger t join pg_class c on c.oid=t.tgrelid
                  where not t.tgisinternal and c.relname in ('profiles','playlists','videos','jobs')
                  order by 1;" 2>/dev/null

echo
if [ "$fail" -eq 0 ]; then
  echo "✅ every mutation caught — check-live-schema.py is load-bearing"
else
  echo "❌ a mutation survived — the gate does not detect what it claims to"
fi
exit "$fail"
