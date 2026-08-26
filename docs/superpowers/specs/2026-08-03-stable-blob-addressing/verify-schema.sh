#!/usr/bin/env bash
# Execute the proposed schema against the LIVE local Postgres inside a transaction that always
# rolls back, then run the assertion suite against it. Verifies the DDL runs against real, populated
# tables — the class of defect that cost rounds 2, 3 and 4 (a physical rule fixed at one site and
# recurring at a sibling).
#
#   ./verify-schema.sh          -> exit 0 = every statement executed; 1 = first error, quoted
#                                  exit 2 = CANNOT RUN (never a pass)
#
# ⟳ T4 (2026-08-26) — THE SCHEMA SOURCE IS NOW A VARIABLE: `0027` when it exists, the spec files
# when it does not. ⚠ ONLY the file list changed. The `$(printf; cat; printf)` composition below is
# the ORIGINAL, kept verbatim on purpose — see the note at the bottom of this header.
#
# ⛔⛔ THE ASSERTIONS ARE CAT'D IN BOTH BRANCHES, WHICH IS A CORRECTION TO THE PLAN.
# Task 4 Step 1 says to select `0[134]*.sql` instead of `0*.sql`, because `05_assert.sql` "must never
# execute as schema". The first half is right — 05 is NOT schema and must not enter a migration
# (`run-schema-assertions.sh` documents why: it holds `delete from profiles`). The CONCLUSION does
# not follow, and MEASURED 2026-08-26 it would have been a silent gutting:
#
#     05_assert.sql                    2517 lines, 122 assertion sites
#     ...marked @RE-RUNNABLE              3
#     gate 8 (run-schema-assertions.sh)   SKIPPED when M4_PHASE=pre, and only ever runs those 3
#     gate 1 (this script)                runs all 122, and is the ONLY thing that does
#
# So dropping 05 here leaves 122 assertions executing NOWHERE before 0027, and 3 of 122 after it.
# This gate is named "1/13 schema + assertions"; the second noun is not decoration. Within the hour
# this was written, this suite caught a T2 defect that both of the plan's textual sweeps had missed.
# The distinction the plan needed: 05 must never be part of the SCHEMA SOURCE (it would ship inside a
# migration); it must always be part of what this gate EXECUTES. The glob answered only the first.
#
# ⛔⛔ AND A WARNING ABOUT THIS FILE'S SHAPE, PAID FOR IN A 10-MINUTE HANG (2026-08-26).
# The first T4 draft rebuilt the SQL "more clearly" as
#     SCHEMA_SRC=$(cat …); ASSERT_SRC=$(cat …); SQL=$(printf 'begin;\n%s\n%s\n…' "$A" "$B")
# and that version HANGS — bash alive, no children, empty log, nothing in pg_stat_activity, i.e.
# indistinguishable from "slow" until you inspect the process tree. The committed one-line
# `$(printf; cat; printf)` form runs in TWO SECONDS. The control is what settled it: restoring the
# original and timing it proved the environment was fine and the rewrite was the defect.
# ⚠ So: change the FILE LIST, never the composition. A "clearer" rewrite of a working pipeline is a
# change to a load-bearing mechanism, and this one had no test that would have caught it.
set -uo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)/schema"
# ⛔ FOUR levels: <spec-dir>/.. = specs, /../.. = superpowers, /../../.. = docs, /../../../.. = REPO.
# A first draft used three and resolved REPO to `docs/`, which made `$REPO/scripts/...` and
# `$REPO/supabase/...` both nonexistent — so the already-applied branch was DEAD and the 0027
# detection would have silently kept reading spec files after promotion. It reported PASS throughout.
# Asserted below rather than trusted, because a wrong path here fails by doing nothing.
#
# ⛔ TWO ENV OVERRIDES, AND THEY EXIST FOR ONE CALLER: `mutate-schema.py` copies this script and the
# schema into a temp dir and runs the COPY (round 8 M3 — so concurrent agents cannot see each
# other's mutations). From there, path-relative resolution lands outside the repo, and the assertion
# below would turn EVERY mutation into INVALID — a gate reporting "could not run" 58 times.
#   M4_REPO       — where scripts/ and supabase/ actually live.
#   M4_MIGRATION  — the migration to read. The harness must point this at its OWN COPY once 0027
#                   exists, or it would mutate a temp file and verify the real one.
REPO="${M4_REPO:-$(cd "$(dirname "$0")/../../../.." && pwd)}"
if [ ! -d "$REPO/supabase/migrations" ] || [ ! -f "$REPO/scripts/check-live-schema.py" ]; then
  echo "CANNOT RUN — REPO resolved to '$REPO', which has no supabase/migrations or" >&2
  echo "  scripts/check-live-schema.py. The 0027 detection would silently never fire." >&2
  echo "  Set M4_REPO if you are running a copy of this script from outside the repo." >&2
  exit 2
fi
MIGRATION="${M4_MIGRATION:-$REPO/supabase/migrations/0027_stable_blob_addressing.sql}"
CONTAINER="${PGCONTAINER:-supabase_db_youtube-playlist-summaries-cloud}"

# ── the already-applied branch ───────────────────────────────────────────────────────────────────
# This gate REBUILDS from source by design, so against a database that already carries M4 it can only
# fail with `relation "workspaces" already exists` — an error about our method, not about the schema.
# ⚠ ONLY exit 0 means "applied". check-live-schema.py exits 2 when it cannot reach a database, and
# treating that as "not applied" is right: the rebuild then fails loudly on its own terms.
# ⚠ `</dev/null` because the child reaches Postgres through `docker exec -i`, which holds stdin open.
if [ -f "$REPO/scripts/check-live-schema.py" ] \
   && python3 "$REPO/scripts/check-live-schema.py" --expect-present </dev/null >/dev/null 2>&1; then
  echo "CANNOT RUN — 0027 is already applied to this database, so rebuilding it will fail with"
  echo "  'relation \"workspaces\" already exists'. This gate rebuilds from source by design."
  echo "  Use scripts/check-live-schema.py for an applied database. Treat this as NOT RUN."
  exit 2
fi

# ── the source list: migration if promoted, spec files if not; 05 ALWAYS last ───────────────────
if [ -f "$MIGRATION" ]; then
  SRC_FILES=("$MIGRATION" "$DIR/05_assert.sql")
  SRC_LABEL="supabase/migrations/$(basename "$MIGRATION") + 05_assert.sql"
else
  # ⚠ `0[134]*.sql`, NOT `0*.sql` — the half of the plan's Step 1 that IS right: 05 is named
  # explicitly below rather than swept in, so the schema half can become a migration without it.
  SRC_FILES=("$DIR"/0[134]*.sql "$DIR/05_assert.sql")
  SRC_LABEL="$DIR/0[134]*.sql + 05_assert.sql (pre-promotion)"
fi

# ⛔ A GATE THAT READS AN EMPTY SET PASSES — measured twice in this repo.
for f in "${SRC_FILES[@]}"; do
  if [ ! -s "$f" ]; then
    echo "CANNOT RUN — source file missing or EMPTY: $f. Treat this as NOT RUN." >&2; exit 2
  fi
done
echo "source: $SRC_LABEL"

SQL=$(printf 'begin;\n'; cat "${SRC_FILES[@]}"; printf '\n\\echo ALL_STATEMENTS_OK\nrollback;\n')
OUT=$(printf '%s' "$SQL" | docker exec -i "$CONTAINER" \
        psql -U postgres -d postgres -v ON_ERROR_STOP=1 2>&1)
echo "$OUT"
if grep -q ALL_STATEMENTS_OK <<<"$OUT"; then echo "✅ schema verified (rolled back)"; exit 0; fi
echo "❌ schema FAILED"; exit 1
