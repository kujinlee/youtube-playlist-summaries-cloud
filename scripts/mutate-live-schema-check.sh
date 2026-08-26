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
# ⛔ NOT `cat 01 03 04`. MEASURED 2026-08-25 — that is what this harness used to do, and it built a
# PRE-ADR-0011 schema: `sync_corrections_to_workspace_video()` plus both `videos_corrections_sync_*`
# triggers, none of which M4 ships. The gate was therefore being mutation-proven against a schema
# that will never exist, and the rollback left all three behind while the gate reported ABSENT.
# `build-m4-schema.py` applies Tasks 1-2 and ASSERTS the end state.
if ! python3 ./scripts/build-m4-schema.py --quiet --out /tmp/m4-mutation-schema.sql; then
  echo "CANNOT RUN — could not build the post-ADR-0011 schema. Treat this as NOT RUN." >&2
  exit 2
fi
if ! docker exec -i "$CONTAINER" psql -U postgres -d "$SCRATCH" -tAq -v ON_ERROR_STOP=1 \
     < /tmp/m4-mutation-schema.sql >/dev/null 2>&1; then
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

echo "═══ mutation 4 ⭐⭐ r3 B2: DROP EVERY OWN-TABLE GUARD TRIGGER, --expect-present must go RED ═══"
# THE CASE THE 29-OBJECT GATE COULD NOT SEE. `M4_LIVE_TRIGGERS` named only the seven triggers on
# LIVE tables, so a database with every append-only / freeze / immutability guard dropped reported
# "M4 is PRESENT as expected", exit 0. The manifest names all 14.
docker exec -i "$CONTAINER" psql -U postgres -d postgres -tAq \
  -c "drop database if exists ${SCRATCH}_guard (force);" >/dev/null 2>&1
docker exec -i "$CONTAINER" psql -U postgres -d postgres -tAq \
  -c "create database ${SCRATCH}_guard;" >/dev/null 2>&1
docker exec -i "$CONTAINER" sh -c \
  "pg_dump -U postgres -d postgres --schema-only --no-owner --no-privileges | psql -U postgres -d ${SCRATCH}_guard -q" \
  >/dev/null 2>&1
python3 ./scripts/build-m4-schema.py --quiet --out /tmp/m4-guard-mutation.sql >/dev/null 2>&1
docker exec -i "$CONTAINER" psql -U postgres -d "${SCRATCH}_guard" -tAq -v ON_ERROR_STOP=1 \
  < /tmp/m4-guard-mutation.sql >/dev/null 2>&1

python3 ./scripts/check-live-schema.py --database "${SCRATCH}_guard" --expect-present \
  >/dev/null 2>&1 && r=pass || r=fail
report "M4 applied to the guard scratch db -> --expect-present passes" pass "$r"

docker exec -i "$CONTAINER" psql -U postgres -d "${SCRATCH}_guard" -tAq >/dev/null 2>&1 <<'SQL'
drop trigger if exists video_generations_freeze_trg              on video_generations;
drop trigger if exists forbid_collecting_current_trg             on video_generations;
drop trigger if exists video_artifacts_append_only_trg           on video_artifacts;
drop trigger if exists video_artifacts_generation_complete_trg   on video_artifacts;
drop trigger if exists video_artifact_sources_append_only_trg    on video_artifact_sources;
drop trigger if exists video_artifact_sources_insert_once_trg    on video_artifact_sources;
drop trigger if exists art_summary_has_no_source_trg             on video_artifact_sources;
SQL
python3 ./scripts/check-live-schema.py --database "${SCRATCH}_guard" --expect-present \
  >/dev/null 2>&1 && r=pass || r=fail
report "ALL SEVEN own-table guards dropped -> --expect-present FAILS" fail "$r"
echo "     tables and columns are all still there; only the guards are gone —"
echo "     that is precisely the state the 29-object gate blessed with exit 0."
docker exec -i "$CONTAINER" psql -U postgres -d postgres -tAq \
  -c "drop database if exists ${SCRATCH}_guard (force);" >/dev/null 2>&1

echo "═══ mutation 5 ⭐⭐⭐ r4 B1: DISABLE, do not drop — the name stays, the rule dies ═══"
# THE MUTATION THIS HARNESS WAS ONE WORD FROM CATCHING. Mutation 4 DROPS the guards; a gate that
# compares names catches that. `alter table … disable trigger` leaves every name in place and every
# rule inert, and the name-only gate returned exit 0 over it — measured on a real database.
docker exec -i "$CONTAINER" psql -U postgres -d postgres -tAq \
  -c "drop database if exists ${SCRATCH}_dis (force);" >/dev/null 2>&1
docker exec -i "$CONTAINER" psql -U postgres -d postgres -tAq \
  -c "create database ${SCRATCH}_dis;" >/dev/null 2>&1
docker exec -i "$CONTAINER" sh -c \
  "pg_dump -U postgres -d postgres --schema-only --no-owner --no-privileges | psql -U postgres -d ${SCRATCH}_dis -q" \
  >/dev/null 2>&1
python3 ./scripts/build-m4-schema.py --quiet --out /tmp/m4-disable-mutation.sql >/dev/null 2>&1
docker exec -i "$CONTAINER" psql -U postgres -d "${SCRATCH}_dis" -tAq -v ON_ERROR_STOP=1 \
  < /tmp/m4-disable-mutation.sql >/dev/null 2>&1

docker exec -i "$CONTAINER" psql -U postgres -d "${SCRATCH}_dis" -tAq >/dev/null 2>&1 <<'SQL'
alter table video_artifacts        disable trigger video_artifacts_append_only_trg;
alter table video_artifacts        disable trigger video_artifacts_generation_complete_trg;
alter table video_generations      disable trigger video_generations_freeze_trg;
alter table video_generations      disable trigger forbid_collecting_current_trg;
alter table video_artifact_sources disable trigger video_artifact_sources_append_only_trg;
alter table video_artifact_sources disable trigger video_artifact_sources_insert_once_trg;
alter table video_artifact_sources disable trigger art_summary_has_no_source_trg;
SQL
n_dis=$(docker exec -i "$CONTAINER" psql -U postgres -d "${SCRATCH}_dis" -tAq \
  -c "select count(*) from pg_trigger where tgenabled='D' and not tgisinternal;" | tr -d '[:space:]')
echo "     triggers now DISABLED (tgenabled='D'): $n_dis  — every NAME still present"
python3 ./scripts/check-live-schema.py --database "${SCRATCH}_dis" --expect-present \
  >/dev/null 2>&1 && r=pass || r=fail
report "7 guards DISABLED (not dropped) -> --expect-present FAILS" fail "$r"

echo "═══ mutation 6 ⭐ a guard FUNCTION BODY replaced with a no-op ═══"
docker exec -i "$CONTAINER" psql -U postgres -d "${SCRATCH}_dis" -tAq >/dev/null 2>&1 <<'SQL'
alter table video_artifacts enable trigger video_artifacts_append_only_trg;
alter table video_artifacts enable trigger video_artifacts_generation_complete_trg;
alter table video_generations enable trigger video_generations_freeze_trg;
alter table video_generations enable trigger forbid_collecting_current_trg;
alter table video_artifact_sources enable trigger video_artifact_sources_append_only_trg;
alter table video_artifact_sources enable trigger video_artifact_sources_insert_once_trg;
alter table video_artifact_sources enable trigger art_summary_has_no_source_trg;
create or replace function video_artifacts_append_only() returns trigger
  language plpgsql as $$ begin return new; end $$;
SQL
python3 ./scripts/check-live-schema.py --database "${SCRATCH}_dis" --expect-present \
  >/dev/null 2>&1 && r=pass || r=fail
report "guard body replaced by 'return new' -> --expect-present FAILS" fail "$r"
docker exec -i "$CONTAINER" psql -U postgres -d postgres -tAq \
  -c "drop database if exists ${SCRATCH}_dis (force);" >/dev/null 2>&1

echo "═══ mutation 3 ⭐ the ADR-0011 RESIDUE: a Task 1 that never landed ═══"
# MEASURED 2026-08-25: with the raw spec applied, the rollback left three objects behind and
# `--expect-absent` reported ABSENT — because the gate's inventory is post-ADR-0011 and could not
# see them. `--expect-present` must now REJECT this schema: it is not a valid M4.
docker exec -i "$CONTAINER" psql -U postgres -d postgres -tAq \
  -c "drop database if exists ${SCRATCH}_raw (force);" >/dev/null 2>&1
docker exec -i "$CONTAINER" psql -U postgres -d postgres -tAq \
  -c "create database ${SCRATCH}_raw;" >/dev/null 2>&1
docker exec -i "$CONTAINER" sh -c \
  "pg_dump -U postgres -d postgres --schema-only --no-owner --no-privileges | psql -U postgres -d ${SCRATCH}_raw -q" \
  >/dev/null 2>&1
if { cat "$SPEC"/01_workspaces.sql "$SPEC"/03_generations.sql "$SPEC"/04_artifacts.sql; } \
   | docker exec -i "$CONTAINER" psql -U postgres -d "${SCRATCH}_raw" -tAq -v ON_ERROR_STOP=1 \
   >/dev/null 2>&1; then
  python3 ./scripts/check-live-schema.py --database "${SCRATCH}_raw" --expect-present \
    >/dev/null 2>&1 && r=pass || r=fail
  report "pre-ADR-0011 schema -> --expect-present FAILS (sync fn + 2 triggers)" fail "$r"
else
  echo "  ✗ could not build the raw pre-ADR-0011 schema — treat mutation 3 as NOT RUN"; fail=1
fi
docker exec -i "$CONTAINER" psql -U postgres -d postgres -tAq \
  -c "drop database if exists ${SCRATCH}_raw (force);" >/dev/null 2>&1

echo
if [ "$fail" -eq 0 ]; then
  echo "✅ every mutation caught — check-live-schema.py is load-bearing"
else
  echo "❌ a mutation survived — the gate does not detect what it claims to"
fi
exit "$fail"
