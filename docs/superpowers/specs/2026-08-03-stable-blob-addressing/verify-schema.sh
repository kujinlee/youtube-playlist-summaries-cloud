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
#     ...marked re-runnable               3
#     gate 8 (run-schema-assertions.sh)   SKIPPED when M4_PHASE=pre, and only ever runs those 3
#     gate 1 (this script)                runs all 122, and is the ONLY thing that does
#
# So dropping 05 here leaves 122 assertions executing NOWHERE before 0027, and 3 of 122 after it.
#
# ⟳ TASK 8 (2026-08-26) — THE SECOND ROW OF THAT TABLE IS NOW THE WHOLE FILE, and the conclusion is
# unchanged. Measurement found no migration-only assertion left (ADR-0011 deleted the one there was),
# so 05 carries a single re-runnable marker at the top and gate 8 runs all 119 of its ok-reporting
# assertions against the APPLIED catalog. Gate 1 is still the only thing that runs them against a
# schema rebuilt from source — the two subjects are different, and neither replaces the other.
# ⚠ The counts above are hand-maintained and were already stale once. `run-schema-assertions.sh`
# now carries a floor that fails when the count drops, which is the mechanical half of this note.
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

# ── the SUBJECT DATABASE ─────────────────────────────────────────────────────────────────────────
# This gate REBUILDS from source by design, so against a database that already carries M4 it can only
# fail with `relation "workspaces" already exists` — an error about our method, not about the schema.
#
# ⟳ 2026-08-26 — IT USED TO STOP HERE, AND THAT WAS SIX OTHER GATES' BUG TOO. Refusing was honest,
# and it made this gate (plus 2, 3, 4, 5, 12 and 13) permanently dead in the phase the project is
# actually in, which meant the fourteen-gate suite could not be green in EITHER phase. It does not
# need `postgres` to be pre-M4; it needs A pre-M4 database, and `scripts/m4-base-db.sh` builds one
# by cloning and applying the committed rollback. See that script's header for the measurement.
#
# ⚠ ONLY exit 0 from check-live-schema.py means "applied". It exits 2 when it cannot reach a
# database, and treating that as "not applied" is right: the rebuild then fails loudly on its own.
# ⚠ `</dev/null` because the child reaches Postgres through `docker exec -i`, which holds stdin open.
#
# `M4_DB` lets a caller supply its own base — `mutate-schema.py` builds ONE and reuses it across 58
# mutations, because a fresh clone per mutation would add four minutes to that gate. When it is
# unset we own the lifecycle: build on entry, drop on exit.
DB="${M4_DB:-postgres}"
OWN_BASE=""
if [ -z "${M4_DB:-}" ] && [ -f "$REPO/scripts/check-live-schema.py" ] \
   && python3 "$REPO/scripts/check-live-schema.py" --expect-present </dev/null >/dev/null 2>&1; then
  OWN_BASE="m4_verify_base_$$"
  if ! "$REPO/scripts/m4-base-db.sh" "$OWN_BASE"; then
    echo "CANNOT RUN — 0027 is applied to 'postgres' and no pre-M4 base could be built." >&2
    echo "  This gate rebuilds from source by design. Treat this as NOT RUN." >&2
    exit 2
  fi
  DB="$OWN_BASE"
  trap 'docker exec -i "$CONTAINER" psql -U postgres -d postgres -tAq \
          -c "drop database if exists '"$OWN_BASE"' (force);" >/dev/null 2>&1' EXIT
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
echo "subject database: $DB"

# ⛔ ONLY the `-d` argument changed here. The `$(printf; cat; printf)` composition is the original —
# see the 10-minute-hang warning in the header. Change the file list and the database, never the shape.
SQL=$(printf 'begin;\n'; cat "${SRC_FILES[@]}"; printf '\n\\echo ALL_STATEMENTS_OK\nrollback;\n')
OUT=$(printf '%s' "$SQL" | docker exec -i "$CONTAINER" \
        psql -U postgres -d "$DB" -v ON_ERROR_STOP=1 2>&1)
echo "$OUT"
if ! grep -q ALL_STATEMENTS_OK <<<"$OUT"; then
  # ⟳ r11 M3 — A RAISED `CANNOT RUN` IS NOT A SCHEMA FAILURE, AND THIS HEADLINE NAMED THE WRONG
  # SUBJECT. 05_assert.sql's fixtures guard (added by r10 M3) raises "CANNOT RUN — only 1
  # workspace(s)…" on a one-workspace database — a state its own comment says a `db reset` plus one
  # signup produces. Any exception suppresses ALL_STATEMENTS_OK, so this branch answered
  # "❌ schema FAILED", exit 1, against a perfectly good schema. r10 M3 replaced a false
  # cross-tenant-leak accusation with a true diagnosis and then routed it through a wrong headline
  # one layer out. This file's own header documents `exit 2 = CANNOT RUN (never a pass)`.
  if grep -q "CANNOT RUN" <<<"$OUT"; then
    echo "⛔ CANNOT RUN — the assertion corpus refused its own preconditions:"
    grep -m3 "CANNOT RUN" <<<"$OUT" | sed "s/^/   /"
    echo "   Treat this as NOT RUN. The schema itself was not judged."
    exit 2
  fi
  echo "❌ schema FAILED"; exit 1
fi

# ⭐⭐ r10 H5 — THIS GATE REPORTED "schema verified" OVER **ZERO** ASSERTIONS.
#
# `ALL_STATEMENTS_OK` is printf'd unconditionally after the `cat`, so it proves nothing RAISED. It
# cannot prove anything RAN — which is the exact sentence the sibling written in the SAME commit
# already carried: `run-schema-assertions.sh` — "⭐ THE FLOOR. ASSERTIONS_OK proves nothing RAISED;
# it cannot prove anything RAN." One site got the floor and this one, which runs the LARGER corpus,
# did not.
#
# MEASURED by the reviewer: replacing `05_assert.sql` with two lines (`-- gutted` / `select 1;`)
# produced `ALL_STATEMENTS_OK` / `ROLLBACK` / `✅ schema verified (rolled back)`, rc 0.
#
# ⚠ IT MATTERS MOST IN THE `pre` PHASE. Gate 8 is SKIPPED when M4_PHASE=pre by design, so before
# 0027 is applied this gate is the ONLY floor on the assertion corpus anywhere in the suite — and it
# had none. The header of this very file says "run-schema-assertions.sh now carries a floor that
# fails when the count drops, which is the mechanical half of this note", describing a mechanism
# that did not cover the gate whose header it is written in.
#
# Same constant as the sibling, same update rule: raising it is routine, LOWERING it is deliberate.
#
# ⟳ r11 L2 — `M4_ASSERTION_FLOOR` NOW DISARMS BOTH FLOORS FROM ONE EXPORT, and this is DELIBERATE:
#   gate 1 and gate 8 run the same corpus and must move together, so two names would be two things
#   to forget. The mitigation is that BOTH announce the floor they used in their success line, so a
#   disarmed run says `floor 0` in its own output rather than looking normal.
# ⟳ r11 L3 — WHAT THE 120th "assertion" IS. The fixtures block's `raise notice 'ok (fixtures): …'`
#   is a PRECONDITION CHECK, not an assertion, and it matches the counted pattern — which is exactly
#   why the floor moved 119 -> 120. So the subject is "119 assertions plus one fixture health check".
#   If a future author makes that guard silent, the floor fails saying "assertions STOPPED
#   EXECUTING" and points at the wrong file; this sentence is what stops that costing an hour.
ASSERTION_FLOOR="${M4_ASSERTION_FLOOR:-120}"
RAN=$(grep -cE 'NOTICE:.*\bok\b' <<<"$OUT")
if [ "$RAN" -lt "$ASSERTION_FLOOR" ]; then
  echo "❌ schema FAILED — only $RAN assertions reported ok; the floor is $ASSERTION_FLOOR." >&2
  echo "   Nothing raised, so this is not a broken invariant: assertions STOPPED EXECUTING." >&2
  echo "   Look for a gutted or truncated 05_assert.sql, or a source list that dropped it." >&2
  exit 1
fi
echo "✅ schema verified (rolled back) — $RAN assertions ran (floor $ASSERTION_FLOOR)"; exit 0
