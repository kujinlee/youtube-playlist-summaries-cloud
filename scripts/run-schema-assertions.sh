#!/usr/bin/env bash
# Run 05_assert.sql's RE-RUNNABLE assertions against a LIVE, SEEDED schema, then roll back.
#
#   ./scripts/run-schema-assertions.sh
#     exit 0 = the RE-RUNNABLE subset passed
#     exit 1 = an assertion raised
#     exit 2 = could not run (treat as NOT RUN)
#
# ⛔ `05_assert.sql` IS NEVER A MIGRATION. It holds `delete from profiles where id = p;` (:2207) and
#    an unrevoked arbitrary-SQL executor `execute p_sql;` (:37). This script is its home instead.
#
# ⚠ EVERY FAILURE MODE HERE IS SILENT-SUCCESS, so each has an explicit cannot-run branch:
#
#   * 0027 not applied  -> assertions are vacuous or hard-red for the wrong reason.
#   * no @RE-RUNNABLE markers -> the selector picks NOTHING, psql runs an empty script, and the gate
#     reports "passed" having asserted nothing. ⟳ r1 B5 (claude) / B6 (codex): the first selector was
#     `awk '/@RE-RUNNABLE/{p=1} p'`, which has NO STOP CONDITION — on today's unmarked file it
#     selects nothing, and once markers exist it captures everything after the FIRST one, including
#     later @MIGRATION-ONLY blocks. Both failures are silent.
#   * the seed inserting nothing -> the corpus asserts itself; see seed-assertion-corpus.sql step 4.
#
# ⚠ Success is decided by a MARKER IN THE OUTPUT, never by an exit code — the same rule
#   `scripts/codex-review.py` follows, for the same reason.
set -uo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
CONTAINER="${PGCONTAINER:-supabase_db_youtube-playlist-summaries-cloud}"
# ⚠ ASSERT_FILE EXISTS SO THE SUCCESS PATH CAN BE PROVEN BEFORE Task 8 ADDS THE MARKERS.
# `05_assert.sql` carries ZERO `@RE-RUNNABLE` markers today, so without an override the only
# reachable outcomes are the two cannot-run branches — and a harness whose happy path has never
# executed is exactly the artifact this extraction exists to stop shipping. Same reasoning as
# `--database` on check-live-schema.py.
ASSERT="${ASSERT_FILE:-$REPO/docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/05_assert.sql}"
SEED="$REPO/docs/superpowers/specs/m4/seed-assertion-corpus.sql"
DB="${PGDATABASE:-postgres}"

for f in "$ASSERT" "$SEED"; do
  [ -r "$f" ] || { echo "CANNOT RUN — missing $f. Treat this as NOT RUN." >&2; exit 2; }
done

if ! python3 "$REPO/scripts/check-live-schema.py" --database "$DB" --expect-present >/dev/null 2>&1; then
  echo "CANNOT RUN — 0027 is not applied to database '$DB', so every assertion would be vacuous" >&2
  echo "or hard-red for the wrong reason. Treat this as NOT RUN." >&2
  exit 2
fi

ASSERTIONS=$(awk '/@RE-RUNNABLE/{p=1;next} /@MIGRATION-ONLY/{p=0;next} p' "$ASSERT")
if [ -z "$(printf '%s' "$ASSERTIONS" | tr -d '[:space:]')" ]; then
  echo "CANNOT RUN — no @RE-RUNNABLE block found in 05_assert.sql. An empty assertion set must" >&2
  echo "never report success. Task 8 Step 1 adds the markers. Treat this as NOT RUN." >&2
  exit 2
fi

SQL=$(printf 'begin;\n'
      cat "$SEED"
      printf '%s' "$ASSERTIONS"
      printf '\n\\echo ASSERTIONS_OK\nrollback;\n')

OUT=$(printf '%s' "$SQL" | docker exec -i "$CONTAINER" \
        psql -U postgres -d "$DB" -v ON_ERROR_STOP=1 2>&1)

if ! printf '%s' "$OUT" | grep -q ASSERTIONS_OK; then
  printf '%s\n' "$OUT" | tail -25 >&2
  echo "FAILED — an assertion raised, or the seed could not build its corpus." >&2
  exit 1
fi

# The rollback is part of the contract: this must not have persisted anything.
LEFT=$(docker exec -i "$CONTAINER" psql -U postgres -d "$DB" -tAq \
        -c "select count(*) from videos where video_id = 'seedvid001';" 2>/dev/null | tr -d '[:space:]')
if [ "$LEFT" != "0" ]; then
  echo "FAILED — the seed PERSISTED ($LEFT row(s) left behind). It must roll back." >&2
  exit 1
fi

echo "schema assertions: RE-RUNNABLE subset passed against the live schema, and rolled back clean"
