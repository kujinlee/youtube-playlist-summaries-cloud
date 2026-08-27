#!/usr/bin/env bash
# Build a PRE-M4 base database: a faithful clone of the local stack with 0027 NOT in it.
#
#   ./scripts/m4-base-db.sh <dbname>
#     exit 0 = <dbname> exists, is a clone of `postgres`, and M4 is ABSENT from it
#     exit 2 = CANNOT RUN (treat as NOT RUN — never a pass)
#
#   ./scripts/m4-base-db.sh --self-test    # 6 cases, including the two fail-closed post-conditions
#
# ⭐⭐ WHY THIS EXISTS — ONE DEFECT WITH SEVEN FACES, MEASURED 2026-08-26.
#
# `M4_PHASE=post ./scripts/check-schema-gates.sh` failed SEVEN of its fourteen gates, every one of
# them with the same error:
#
#     ERROR:  relation "workspaces" already exists
#
# Gates 1, 2, 3, 4, 5, 12 and 13 all rebuild M4 from source onto a clone of the local `postgres`
# database (or onto `postgres` itself, inside a rolled-back transaction). `workspaces` is an M4
# object, so once 0027 is applied to `postgres` every one of those rebuilds collides with itself.
#
# ⚠ THE SHAPES DIFFERED, AND ONE OF THEM WAS DISHONEST:
#     gate 1  refused cleanly, rc=2 CANNOT RUN
#     gate 2  reported 58 mutations as `INVALID / no error captured; SQL did not run` — a VERDICT
#             LIST built from a gate that never ran, and INVALID reads as *untested*
#     3/4/5   "could not read the catalog"
#     12/13   "could not build the M4 template"
#
# ⛔ AND THE STRUCTURAL POINT IS BIGGER THAN THE SEVEN: without this helper the suite cannot be
#    all-green in EITHER phase. In `pre`, gate 8 is skipped by design and gates 10/11 assert
#    ABSENCE, so the live-behaviour half is vacuous. In `post`, the rebuild half is dead. That is an
#    unsatisfiable bar — the exact failure `check-schema-gates.sh` warns about in its own header
#    ("this plan shipped an unsatisfiable milestone twice"). Giving the rebuild gates their own
#    pre-M4 base dissolves it: both halves can be green at once, in the phase the project is in.
#
# THE ROLLBACK IS THE INSTRUMENT, AND IT ALREADY EXISTED (committed 322d411). It is deliberately
# NOT a migration — `supabase migration up` applies every pending file in one pass, so a rollback
# filed as 0028 would compose with 0027 to a no-op (measured, plan Task 9).
#
# MEASURED on a throwaway clone before writing a line of this:
#     clone `postgres`        -> video_artifacts present (1)
#     apply the rollback      -> rc=0, skipping-notices 0, video_artifacts present (0)
#     rebuild M4 from source  -> rc=0
#
# ⛔ `skipping-notices: 0` IS THE FALSIFIER, NOT THE EXIT CODE. A wrong `drop function` signature is
#    a SILENT NO-OP under `if exists`: the statement succeeds, the function survives, nothing
#    reports it. The plan's own first draft got two of thirteen signatures wrong. So this script
#    greps for `NOTICE … skipping` and fails on any, and then asserts ABSENCE with the derived
#    manifest rather than trusting either.
set -uo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
CONTAINER="${PGCONTAINER:-supabase_db_youtube-playlist-summaries-cloud}"
ROLLBACK="$REPO/supabase/rollback/rollback_0027_stable_blob_addressing.sql"
SOURCE_DB="${M4_CLONE_SOURCE:-postgres}"

adm() { docker exec -i "$CONTAINER" psql -U postgres -d postgres -tAq "$@"; }

# ⚠ A NAME THAT CAN REACH `postgres` IS A DESTRUCTIVE BUG, and this script's first act is a DROP.
# Refuse anything that is not an obvious throwaway. The shared local database is the one thing in
# this repo that other agents' work lives in.
valid_name() {
  case "$1" in
    postgres|template0|template1|"") return 1 ;;
    m4_*|xr_*|mls_*)                 return 0 ;;
    *)                               return 1 ;;
  esac
}

build() { # <dbname>
  local db="$1" out rc
  if ! valid_name "$db"; then
    echo "CANNOT RUN — refusing to build base database '$db'." >&2
    echo "  Name must start with m4_, xr_ or mls_ so a typo cannot reach a real database." >&2
    return 2
  fi
  if ! adm -c "select 1" >/dev/null 2>&1; then
    echo "CANNOT RUN — no Postgres at container $CONTAINER. Treat this as NOT RUN." >&2
    return 2
  fi
  [ -r "$ROLLBACK" ] || { echo "CANNOT RUN — missing $ROLLBACK." >&2; return 2; }

  adm -c "drop database if exists $db (force);" >/dev/null 2>&1
  if ! adm -c "create database $db;" >/dev/null 2>&1; then
    echo "CANNOT RUN — could not create $db." >&2; return 2
  fi
  # ⛔ WITH DATA, AND NOT `--schema-only`. MEASURED 2026-08-26: a schema-only base made gate 1 fail
  # with `null value in column "workspace_id" … violates not-null`, because `01_workspaces.sql`
  # DERIVES workspaces from `profiles` and an empty clone has none — so 05_assert.sql's fixtures
  # resolved `(select id from t_ws)` to NULL. The seductive repair is to seed two synthetic
  # profiles; it would have been a SILENT LOSS OF COVERAGE. This gate's own header says it exists to
  # verify "the DDL runs against real, POPULATED tables — the class of defect that cost rounds 2, 3
  # and 4", and every backfill in the migration is exactly that. A base with no rows makes each of
  # them vacuous while the gate still reports green.
  #
  # The cost is 5.4 s for 21 MB and 7,864 profiles, measured. `--no-privileges` is kept deliberately:
  # `m4_catalog.py` records the ACL Postgres assigns when no default grant is carried over, so
  # dropping the flag would move the digest for reasons that are not about M4.
  if ! docker exec -i "$CONTAINER" sh -c \
        "pg_dump -U postgres -d $SOURCE_DB --no-owner --no-privileges | psql -U postgres -d $db -q" \
        >/dev/null 2>&1; then
    echo "CANNOT RUN — could not clone $SOURCE_DB into $db." >&2; return 2
  fi

  # Only roll back if M4 is actually there. A source database that never had 0027 is already a
  # valid base, and running the rollback against it would emit `skipping` for all thirteen
  # functions — indistinguishable from the silent-no-op defect this script exists to catch.
  if python3 "$REPO/scripts/check-live-schema.py" --database "$db" --expect-present \
       </dev/null >/dev/null 2>&1; then
    out=$(docker exec -i "$CONTAINER" psql -U postgres -d "$db" -v ON_ERROR_STOP=1 \
            < "$ROLLBACK" 2>&1); rc=$?
    if [ "$rc" -ne 0 ]; then
      printf '%s\n' "$out" | tail -10 >&2
      echo "CANNOT RUN — the rollback did not apply to $db." >&2; return 2
    fi
    if [ "$(printf '%s' "$out" | grep -c skipping)" -ne 0 ]; then
      printf '%s\n' "$out" | grep skipping | head -5 >&2
      echo "CANNOT RUN — the rollback emitted 'skipping' NOTICEs, so a drop was a SILENT NO-OP." >&2
      echo "  A wrong 'drop function' signature succeeds and leaves the function behind." >&2
      return 2
    fi
  fi

  # ⛔ THE POST-CONDITION IS ASSERTED, NOT ASSUMED. Everything above can succeed and still leave M4
  # partly present — that is the whole reason `check-live-schema.py` grew past tables and columns.
  if ! python3 "$REPO/scripts/check-live-schema.py" --database "$db" --expect-absent \
         </dev/null >/dev/null 2>&1; then
    echo "CANNOT RUN — $db still carries M4 objects after the rollback. Treat this as NOT RUN." >&2
    python3 "$REPO/scripts/check-live-schema.py" --database "$db" --expect-absent </dev/null 2>&1 \
      | tail -8 >&2
    return 2
  fi
  return 0
}

if [ "${1:-}" = "--self-test" ]; then
  cases=0; bad=0
  ck() { cases=$((cases + 1))
         if [ "$2" = "$3" ]; then echo "  ✓ $1"; else echo "  ✗ $1 — wanted $2, got $3"; bad=$((bad + 1)); fi; }

  echo "── the name guard (no database needed)"
  for n in postgres template1 "" supabase_db mydb; do
    valid_name "$n"; ck "'$n' is REFUSED (a DROP must not be able to reach it)" 1 "$?"
  done
  valid_name m4_selftest_ok; ck "'m4_selftest_ok' is accepted" 0 "$?"

  echo "── ⭐ the build, end to end (needs Docker)"
  if ! adm -c "select 1" >/dev/null 2>&1; then
    echo "  ⚠ NOT RUN — no Postgres at $CONTAINER. This counts as a FAILURE, not a skip."
    bad=$((bad + 1))
  else
    T=m4_base_selftest_$$
    build "$T" >/dev/null 2>&1; ck "a base database builds and reads ABSENT" 0 "$?"
    # The control that gives the case above its meaning: the SOURCE must have differed from the
    # result, or "absent" proves nothing about the rollback. Skipped honestly when 0027 is not
    # applied locally — then the clone was already a valid base and there was nothing to undo.
    if python3 "$REPO/scripts/check-live-schema.py" --database "$SOURCE_DB" --expect-present \
         </dev/null >/dev/null 2>&1; then
      python3 "$REPO/scripts/check-live-schema.py" --database "$T" --expect-present \
        </dev/null >/dev/null 2>&1
      ck "…and the SOURCE did carry M4, so the rollback is what removed it" 1 "$?"
    else
      echo "  · source '$SOURCE_DB' has no M4 — the removal half is not exercised this run"
    fi
    # ⭐ THE POPULATION CASE. A base with no rows makes every backfill in the migration vacuous
    # while the gates still report green — measured, and it is why this clones WITH data.
    n=$(adm -c "select count(*) from profiles;" 2>/dev/null | tr -d '[:space:]')
    src=$(docker exec -i "$CONTAINER" psql -U postgres -d "$SOURCE_DB" -tAq \
            -c "select count(*) from profiles;" 2>/dev/null | tr -d '[:space:]')
    m=$(docker exec -i "$CONTAINER" psql -U postgres -d "$T" -tAq \
          -c "select count(*) from profiles;" 2>/dev/null | tr -d '[:space:]')
    [ "${m:-0}" = "${src:-x}" ] && r=same || r=differs
    ck "the base carries the SOURCE's rows ($m vs $src profiles), not an empty schema" same "$r"
    unset n

    # Rebuilding M4 onto it must now succeed: that is the thing all seven gates need.
    python3 "$REPO/scripts/build-m4-schema.py" --quiet --out "/tmp/m4-base-selftest.sql" >/dev/null 2>&1
    docker exec -i "$CONTAINER" psql -U postgres -d "$T" -tAq -v ON_ERROR_STOP=1 \
      < /tmp/m4-base-selftest.sql >/dev/null 2>&1
    ck "M4 rebuilds from source onto it (the seven gates' actual requirement)" 0 "$?"
    adm -c "drop database if exists $T (force);" >/dev/null 2>&1
    rm -f /tmp/m4-base-selftest.sql
  fi

  echo
  echo "$((cases - bad)) of $cases self-test cases passed"
  exit "$bad"
fi

[ $# -eq 1 ] || { echo "usage: $0 <dbname> | --self-test" >&2; exit 2; }
build "$1"; exit $?
