#!/usr/bin/env bash
# Run 05_assert.sql's RE-RUNNABLE assertions against a LIVE, SEEDED schema, then roll back.
#
#   ./scripts/run-schema-assertions.sh
#     exit 0 = the RE-RUNNABLE subset passed
#     exit 1 = an assertion raised
#     exit 2 = could not run (treat as NOT RUN)
#
#   ./scripts/run-schema-assertions.sh --print-block   # selection only, no database, prints the block
#   ./scripts/run-schema-assertions.sh --self-test     # the selector's cases, INCLUDING a live RED proof
#
# ⛔ `05_assert.sql` IS NEVER A MIGRATION. It holds `delete from profiles where id = p;` (:2207) and
#    an unrevoked arbitrary-SQL executor `execute p_sql;` (:37). This script is its home instead.
#
# ⚠ EVERY FAILURE MODE HERE IS SILENT-SUCCESS, so each has an explicit cannot-run branch:
#
#   * 0027 not applied  -> assertions are vacuous or hard-red for the wrong reason.
#   * no @RE-RUNNABLE markers -> the selector picks NOTHING, psql runs an empty script, and the gate
#     reports "passed" having asserted nothing.
#   * the seed inserting nothing -> the corpus asserts itself; see seed-assertion-corpus.sql step 4.
#
# ⚠ Success is decided by a MARKER IN THE OUTPUT, never by an exit code — the same rule
#   `scripts/codex-review.py` follows, for the same reason.
#
# ⭐⭐ FOUR ROUNDS OF MOVING THE SAME SYNTACTIC PROXY ONE NOTCH — READ THIS BEFORE TOUCHING THE GUARD.
#
#     r1  "anything after the marker"      -> no stop condition; captured later @MIGRATION-ONLY blocks
#     r2  a stop condition                 -> a marker inside a STRING LITERAL still steered it
#     r3  "must contain a non-comment"     -> a block whose only content is `;` passed
#     r4  "must contain an alphanumeric"   -> `select 1;` is alphanumeric, and PASSED (r5 H3, MEASURED)
#
# Each fix asked *"what did the last counter-example have that a real assertion does not?"*, which is
# a question about SYNTAX and has an unbounded supply of answers. The property that actually matters
# is **"the selected block goes RED when its invariant is violated"** — which is behavioural, so
# `--self-test` now BUILDS AN M4 DATABASE AND PROVES IT, rather than reasoning about characters.
# The syntactic guard below is kept only as a cheap floor, and it is deliberately fail-CLOSED: a
# block using a failure mechanism not listed in FAILS_LOUDLY is a CANNOT RUN, not a pass.
set -uo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
CONTAINER="${PGCONTAINER:-supabase_db_youtube-playlist-summaries-cloud}"
# ⚠ ASSERT_FILE EXISTS SO THE SUCCESS PATH CAN BE PROVEN BEFORE Task 8 ADDS THE MARKERS.
# `05_assert.sql` carries ZERO `@RE-RUNNABLE` markers today, so without an override the only
# reachable outcomes are the two cannot-run branches — and a harness whose happy path has never
# executed is exactly the artifact this extraction exists to stop shipping.
ASSERT="${ASSERT_FILE:-$REPO/docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/05_assert.sql}"
SEED="$REPO/docs/superpowers/specs/m4/seed-assertion-corpus.sql"
DB="${PGDATABASE:-postgres}"

# The ways an assertion in this corpus can FAIL. Every real one is a `do $$ … raise exception … $$;`.
# Adding a mechanism here is a deliberate act; NOT adding it makes the block a loud CANNOT RUN.
FAILS_LOUDLY='raise exception|raise_exception|[^a-z_]assert[^a-z_]'

# ── selection ────────────────────────────────────────────────────────────────────────────────────
# ⟳ r3 HIGH (codex): both fixes here are STRUCTURAL, not pattern tweaks —
#   * a marker only counts ON A COMMENT LINE, so SQL text can never steer the selector;
#   * @MIGRATION-ONLY stops it, so later blocks are not swept in.
select_block() { # <file> -> block on stdout, or empty
  awk '
    /^[[:space:]]*--.*@RE-RUNNABLE/    { p = 1; next }
    /^[[:space:]]*--.*@MIGRATION-ONLY/ { p = 0; next }
    p' "$1"
}

# Returns 0 if the block can fail, 2 with a reason on stderr otherwise.
check_block() { # <block>
  # ⟳ r6 H2 (claude): this used to be `grep -v '^[[:space:]]*--'`, which strips WHOLE COMMENT LINES
  # only. MEASURED — all three of these were accepted, and the first is `select 1;`, the literal
  # counter-example FAILS_LOUDLY was written for, re-admitted by appending a comment to it:
  #
  #     select 1; -- this would raise exception if the invariant broke
  #     select 1; /* raise exception */
  #     select 'raise exception' as note;
  #
  # ⚠ The file already knew this. Its own selector comment says "a marker only counts ON A COMMENT
  # LINE, so SQL text can never steer the selector" — round 2's lesson, applied to the selector and
  # not to the failure check eight lines below it. Same file, same commit, one direction; which is
  # r5 B1's sentence verbatim.
  #
  # Order matters: literals FIRST (so a literal containing `--` cannot truncate the line), then
  # block comments, then trailing line comments.
  local sql
  sql=$(printf '%s\n' "$1" \
        | sed -E "s@'[^']*'@''@g" \
        | sed -E 's@/\*[^*]*\*/@@g' \
        | sed -E 's@--.*$@@')
  if [ -z "$(printf '%s' "$sql" | tr -cd '[:alnum:]')" ]; then
    echo "CANNOT RUN — no @RE-RUNNABLE block with EXECUTABLE SQL in $ASSERT." >&2
    echo "Comments alone are not assertions, and neither is punctuation: a lone ';' parses and" >&2
    echo "asserts nothing, which would run the seed and report success over ZERO assertions." >&2
    echo "Treat this as NOT RUN." >&2
    return 2
  fi
  if ! printf '%s' "$sql" | grep -Eqi "$FAILS_LOUDLY"; then
    echo "CANNOT RUN — the @RE-RUNNABLE block in $ASSERT contains no construct that can FAIL." >&2
    echo "It parses and executes, and would report success having asserted nothing — which is what" >&2
    echo "'select 1;' did (MEASURED, r5 H3). An assertion must be able to go RED; in this corpus" >&2
    echo "that means 'raise exception' or 'assert'. If you are introducing a THIRD mechanism, add" >&2
    echo "it to FAILS_LOUDLY deliberately. Treat this as NOT RUN." >&2
    return 2
  fi
  return 0
}

# ── modes ────────────────────────────────────────────────────────────────────────────────────────
if [ "${1:-}" = "--print-block" ]; then
  [ -r "$ASSERT" ] || { echo "CANNOT RUN — missing $ASSERT." >&2; exit 2; }
  BLOCK=$(select_block "$ASSERT")
  check_block "$BLOCK" || exit 2
  printf '%s\n' "$BLOCK"
  exit 0
fi

if [ "${1:-}" = "--self-test" ]; then
  TMP=$(mktemp -d) || exit 2
  SCRATCH="m4_assert_selftest_$$"   # ⟳ r6 L1: per-process
  cases=0; bad=0
  cleanup_st() {
    rm -rf "$TMP"
    docker exec -i "$CONTAINER" psql -U postgres -d postgres -tAq \
      -c "drop database if exists $SCRATCH (force);" >/dev/null 2>&1
  }
  trap cleanup_st EXIT
  ck() { # <name> <want-exit> <got-exit>
    cases=$((cases + 1))
    if [ "$2" = "$3" ]; then echo "  ✓ $1"; else echo "  ✗ $1 — wanted exit $2, got $3"; bad=$((bad + 1)); fi
  }

  echo "── selection and the fail-closed floor (no database needed)"
  # Every one of these families reported "RE-RUNNABLE subset passed" in some round of this file.
  printf 'select 1;\n'                                             > "$TMP/no-marker.sql"
  printf -- '-- @RE-RUNNABLE\n-- just a comment\n'                  > "$TMP/comment-only.sql"
  printf -- '-- @RE-RUNNABLE\n;\n'                                  > "$TMP/semicolon.sql"
  printf -- '-- @RE-RUNNABLE\nselect 1;\n'                          > "$TMP/select1.sql"
  printf -- "-- @RE-RUNNABLE\nselect '@MIGRATION-ONLY' as m;\ndo \$\$ begin raise exception 'x'; end \$\$;\n" \
                                                                    > "$TMP/literal.sql"
  printf -- '-- @RE-RUNNABLE\ndo $$ begin raise exception %s; end $$;\n-- @MIGRATION-ONLY\nselect 1/0;\n' \
         "'boom'"                                                   > "$TMP/real.sql"
  for f in no-marker comment-only semicolon select1; do
    ASSERT_FILE="$TMP/$f.sql" "$0" --print-block >/dev/null 2>&1
    ck "'$f' is CANNOT RUN, not a silent pass" 2 "$?"
  done
  ASSERT_FILE="$TMP/literal.sql" "$0" --print-block >/dev/null 2>&1
  ck "a marker inside a STRING LITERAL does not stop the selector" 0 "$?"

  # ⟳ r6 H2 — a fake failure mechanism hiding in a comment or a literal must NOT count.
  printf -- '-- @RE-RUNNABLE\nselect 1; -- this would raise exception if the invariant broke\n' \
                                                                    > "$TMP/trailing.sql"
  printf -- '-- @RE-RUNNABLE\nselect 1; /* raise exception */\n'    > "$TMP/cstyle.sql"
  printf -- "-- @RE-RUNNABLE\nselect 'raise exception' as note;\n"  > "$TMP/litfake.sql"
  for f in trailing cstyle litfake; do
    ASSERT_FILE="$TMP/$f.sql" "$0" --print-block >/dev/null 2>&1
    ck "'$f': a fake 'raise exception' in a comment or literal is CANNOT RUN (r6 H2)" 2 "$?"
  done
  ASSERT_FILE="$TMP/real.sql" "$0" --print-block >/dev/null 2>&1
  ck "a real 'raise exception' block IS selected" 0 "$?"
  out=$(ASSERT_FILE="$TMP/real.sql" "$0" --print-block 2>/dev/null)
  case "$out" in *"1/0"*) echo "  ✗ the @MIGRATION-ONLY block leaked into the selection"; bad=$((bad + 1));;
                  *)      echo "  ✓ the @MIGRATION-ONLY block is excluded";; esac
  cases=$((cases + 1))

  echo "── ⭐ THE BEHAVIOURAL PROOF: does a selected block actually go RED? (needs Docker)"
  # This is the case four rounds of syntactic guards never established. Without it, "the block can
  # fail" is a claim about characters.
  if ! docker exec -i "$CONTAINER" psql -U postgres -d postgres -tAq -c "select 1" >/dev/null 2>&1; then
    echo "  ⚠ NOT RUN — no Postgres at container $CONTAINER. The RED proof did NOT execute."
    bad=$((bad + 1))
  else
    docker exec -i "$CONTAINER" psql -U postgres -d postgres -tAq \
      -c "drop database if exists $SCRATCH (force);" >/dev/null 2>&1
    docker exec -i "$CONTAINER" psql -U postgres -d postgres -tAq \
      -c "create database $SCRATCH;" >/dev/null 2>&1
    docker exec -i "$CONTAINER" sh -c \
      "pg_dump -U postgres -d postgres --schema-only --no-owner --no-privileges | psql -U postgres -d $SCRATCH -q" \
      >/dev/null 2>&1
    python3 "$REPO/scripts/build-m4-schema.py" --quiet --out "$TMP/m4.sql" >/dev/null 2>&1
    if ! docker exec -i "$CONTAINER" psql -U postgres -d "$SCRATCH" -tAq -v ON_ERROR_STOP=1 \
         < "$TMP/m4.sql" >/dev/null 2>&1; then
      echo "  ⚠ NOT RUN — could not build an M4 database to prove RED against."
      bad=$((bad + 1))
    else
      printf -- '-- @RE-RUNNABLE\ndo $$ begin if true then raise exception %s; end if; end $$;\n' \
             "'the invariant is violated'" > "$TMP/red.sql"
      PGDATABASE="$SCRATCH" ASSERT_FILE="$TMP/red.sql" "$0" >/dev/null 2>&1
      ck "a VIOLATED invariant makes the harness exit 1" 1 "$?"
      printf -- '-- @RE-RUNNABLE\ndo $$ begin if false then raise exception %s; end if; end $$;\n' \
             "'never'" > "$TMP/green.sql"
      PGDATABASE="$SCRATCH" ASSERT_FILE="$TMP/green.sql" "$0" >/dev/null 2>&1
      ck "a HOLDING invariant makes the harness exit 0" 0 "$?"
    fi
  fi

  echo
  echo "$((cases - bad)) of $cases self-test cases passed"
  [ "$bad" = 0 ] || echo "⚠ a NOT RUN above counts as a FAILURE here: an unproven RED path is the"
  [ "$bad" = 0 ] || echo "  exact artifact this self-test exists to stop shipping."
  exit "$bad"
fi

# ── the real run ─────────────────────────────────────────────────────────────────────────────────
for f in "$ASSERT" "$SEED"; do
  [ -r "$f" ] || { echo "CANNOT RUN — missing $f. Treat this as NOT RUN." >&2; exit 2; }
done

if ! python3 "$REPO/scripts/check-live-schema.py" --database "$DB" --expect-present >/dev/null 2>&1; then
  echo "CANNOT RUN — 0027 is not applied to database '$DB', so every assertion would be vacuous" >&2
  echo "or hard-red for the wrong reason. Treat this as NOT RUN." >&2
  exit 2
fi

ASSERTIONS=$(select_block "$ASSERT")
check_block "$ASSERTIONS" || exit 2

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
