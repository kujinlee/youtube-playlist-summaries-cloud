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

# ⟳ r3 HIGH (codex) — THE SELECTOR WAS STILL FAIL-OPEN, TWICE, AND MY OWN PROOF MISSED BOTH.
# The r2 fix added a stop condition, and I demonstrated it with a synthetic file whose traps were
# real markers on comment lines. Codex executed two shapes that test did not cover, and BOTH
# reported "RE-RUNNABLE subset passed":
#
#   1. A marker-only block with no SQL:            -- @RE-RUNNABLE
#                                                  -- comment, no assertion
#      -> `$ASSERTIONS` is non-empty (it holds comment text), the emptiness guard passes, psql runs
#         the seed and nothing else, and ASSERTIONS_OK prints. Success over zero assertions.
#
#   2. A marker inside a STRING LITERAL:           select '@MIGRATION-ONLY' as marker;
#                                                  select 1/0 as should_have_failed;
#      -> the old pattern matched anywhere on the line, so selection stopped at the literal and the
#         failing assertion was never sent.
#
# Both fixes below are structural, not pattern tweaks:
#   * a marker only counts ON A COMMENT LINE, so SQL text can never steer the selector;
#   * the block must contain at least one NON-COMMENT line, so comments alone cannot stand in for
#     assertions.
ASSERTIONS=$(awk '
  /^[[:space:]]*--.*@RE-RUNNABLE/    { p = 1; next }
  /^[[:space:]]*--.*@MIGRATION-ONLY/ { p = 0; next }
  p' "$ASSERT")

# ⟳ r4 HIGH (codex), THIRD ROUND FOR THIS SELECTOR. The r3 fix required a non-comment,
# non-whitespace character. MEASURED: a block whose only content is `;` satisfies that, parses
# cleanly, asserts NOTHING, and the harness printed "RE-RUNNABLE subset passed", exit 0.
#
# Punctuation is not an assertion. The block must contain a WORD — every real assertion here is a
# `do $$ … raise exception … $$;`, so requiring one alphanumeric character costs nothing and closes
# the `;`, `;;`, `()` and `--`-only families in one predicate.
EXECUTABLE=$(printf '%s\n' "$ASSERTIONS" | grep -v '^[[:space:]]*--' | tr -cd '[:alnum:]')
if [ -z "$EXECUTABLE" ]; then
  echo "CANNOT RUN — no @RE-RUNNABLE block with EXECUTABLE SQL in $ASSERT." >&2
  echo "The block must contain at least one alphanumeric character. Comments alone are not" >&2
  echo "assertions, and neither is punctuation: a lone ';' parses and asserts nothing, which" >&2
  echo "would run the seed and report success over ZERO assertions. Treat this as NOT RUN." >&2
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
