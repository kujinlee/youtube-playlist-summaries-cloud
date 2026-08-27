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
# ⚠ ASSERT_FILE EXISTS SO THE SUCCESS PATH CAN BE PROVEN INDEPENDENTLY OF THE REAL CORPUS.
# It was added when `05_assert.sql` carried ZERO markers and the only reachable outcomes were the
# two cannot-run branches. Task 8 has since classified the file (see below), so the default path
# now runs for real — but the override stays, because the self-test's RED and GREEN cases need a
# file whose invariant they control.
ASSERT="${ASSERT_FILE:-$REPO/docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/05_assert.sql}"
SEED="$REPO/docs/superpowers/specs/m4/seed-assertion-corpus.sql"
DB="${PGDATABASE:-postgres}"

# ⭐ THE ASSERTION FLOOR — WHAT MAKES "the subset passed" MEAN SOMETHING.
#
# Task 8 classified `05_assert.sql` as re-runnable IN ONE RANGE, from the top of the file. That is
# only safe because a shrunken range now goes RED: the selector is a toggle, so a future author who
# adds `-- @MIGRATION-ONLY` mid-file and forgets to resume would silently drop every assertion after
# it, and the gate would report success over the remainder. Nothing syntactic can see that; a COUNT
# can. MEASURED 2026-08-26 against the applied 0027, identical on three consecutive runs:
#
#   docker exec … psql < (seed + 05_assert.sql) | grep -cE 'NOTICE:.*\bok\b'   ->  120
#
# ⟳ r10 L3 — WHY THE NUMBER IS NOT THE COUNT OF `raise notice` SITES. 05_assert.sql has 60 static
#   ok-sites but emits 120 notices, because the population-coverage instrument LOOPS over
#   artifact_kind × free/paid. So the floor also moves if the enum gains a value (upward, harmlessly)
#   and it cannot tell "an assertion was deleted" from "the enum shrank and a loop ran fewer times".
#   Not a defect; recorded so the next person to see this number move looks in the right place.
# ⟳ r10 M3 — 119 -> 120: the fixtures block now asserts t_ws <> t_w2 and says which tenants it
#   resolved, which is one more ok-notice. Raising a floor because a real assertion was ADDED is the
#   routine direction.
#
# ⚠ Raising it is routine (add assertions). LOWERING it is a deliberate act — ADR-0011 deleted seven
#   blocks and that is exactly the direction this floor exists to make visible. Do not lower it to
#   make a red gate green; find out which assertions stopped running first.
#
# The two env overrides exist ONLY for `--self-test`, which has to watch the floor fire in both
# directions against a fixture whose assertion count it controls. They are deliberately not the
# `ASSERT_FLOOR`/`FORCE` names a caller would guess, and the real run announces when a floor was
# skipped, so neither can quietly disable the ratchet in a gate.
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
  #
  # ⛔ AND DO NOT REINTRODUCE `printf … | grep -q` HERE. MEASURED 2026-08-26:
  #
  #     set -o pipefail; printf '%s' "$big" | grep -Eqi 'raise exception'   ->  rc 141
  #     set -o pipefail; printf '%s' "$small" | grep -Eqi 'raise exception' ->  rc 0
  #
  # `grep -q` exits on the FIRST match; once the block exceeds the pipe buffer, `printf` is still
  # writing and dies of SIGPIPE (141), and `pipefail` reports the PRODUCER. So the check inverted
  # on SIZE ALONE: this gate ran green over a 301-line block and would have become a permanent
  # CANNOT RUN the moment Task 8 widened the selection to the whole 2,517-line file. Fail-closed,
  # so it would have been honest — and it would still have removed the gate. `grep -c` reads all of
  # its input, so there is no early exit to race. Capture first, match second.
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
  local loud
  loud=$(printf '%s' "$sql" | grep -Eci "$FAILS_LOUDLY")
  if [ "${loud:-0}" -eq 0 ]; then
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

  # ⭐ THE SIZE CASE. Every case above is a handful of lines, which is exactly why the SIGPIPE
  # defect survived: `printf … | grep -q` inverts only once the block outgrows the pipe buffer, so a
  # suite of small fixtures certifies a check that fails on the real 2,517-line corpus. The match is
  # deliberately on the FIRST line — grep must exit while printf still has hundreds of KB to write.
  #
  # ⚠ THE PADDING MUST SURVIVE `check_block`'s STRIPPING, and the first draft did not: it was 4,000
  # COMMENT lines, which the comment-stripping `sed` reduced to 4,000 empty ones — 4 KB, under the
  # pipe buffer. The case passed against the mutated (buggy) script, which is how it was caught.
  # Measured after this fix: mutating `grep -Eci` back to `grep -Eqi` makes exactly this case fail.
  { printf -- '-- @RE-RUNNABLE\ndo $$ begin raise exception %s; end $$;\n' "'boom'"
    awk 'BEGIN { for (i = 0; i < 4000; i++)
                   print "select padding_identifier_that_survives_comment_and_literal_stripping;" }'
  } > "$TMP/big.sql"
  ASSERT_FILE="$TMP/big.sql" "$0" --print-block >/dev/null 2>&1
  ck "a BLOCK LARGER THAN THE PIPE BUFFER is still selected (SIGPIPE regression)" 0 "$?"
  out=$(ASSERT_FILE="$TMP/real.sql" "$0" --print-block 2>/dev/null)
  case "$out" in *"1/0"*) echo "  ✗ the @MIGRATION-ONLY block leaked into the selection"; bad=$((bad + 1));;
                  *)      echo "  ✓ the @MIGRATION-ONLY block is excluded";; esac
  cases=$((cases + 1))

  echo "── ⭐ THE BEHAVIOURAL PROOF: does a selected block actually go RED? (needs Docker)"
  # This is the case four rounds of syntactic guards never established. Without it, "the block can
  # fail" is a claim about characters.
  # ⚠ THE SUBJECT DATABASE IS PHASE-DEPENDENT, AND GETTING THAT WRONG MADE THIS SELF-TEST RED
  #   WITHOUT ANYONE NOTICING (measured 2026-08-26: "9 of 10", and nothing in
  #   `check-schema-gates.sh` runs `--self-test`, so the red never reached a gate).
  #
  #   The scratch build dumps `postgres` and then applies M4 on top. Before 0027 that composed;
  #   after 0027 the dump ALREADY CONTAINS M4, so the apply died on
  #   `relation "workspaces" already exists`. Same phase boundary as gates 1 and 2 — and the fix is
  #   the same one Task 4 used there: pick the SOURCE from what is actually true of the database,
  #   rather than assuming a phase.
  #
  #   Post-0027 the live database IS an M4 database, so it needs no scratch copy: the harness runs
  #   inside a transaction and rolls back, which is exactly what the real run already does to it.
  if ! docker exec -i "$CONTAINER" psql -U postgres -d postgres -tAq -c "select 1" >/dev/null 2>&1; then
    echo "  ⚠ NOT RUN — no Postgres at container $CONTAINER. The RED proof did NOT execute."
    bad=$((bad + 1))
  else
    PROOF_DB=""
    if python3 "$REPO/scripts/check-live-schema.py" --database "$DB" --expect-present >/dev/null 2>&1; then
      PROOF_DB="$DB"
      echo "  · 0027 is applied to '$DB' — proving RED there directly (transaction + rollback)"
    else
      echo "  · 0027 is not applied to '$DB' — building scratch database $SCRATCH"
      docker exec -i "$CONTAINER" psql -U postgres -d postgres -tAq \
        -c "drop database if exists $SCRATCH (force);" >/dev/null 2>&1
      docker exec -i "$CONTAINER" psql -U postgres -d postgres -tAq \
        -c "create database $SCRATCH;" >/dev/null 2>&1
      docker exec -i "$CONTAINER" sh -c \
        "pg_dump -U postgres -d postgres --schema-only --no-owner --no-privileges | psql -U postgres -d $SCRATCH -q" \
        >/dev/null 2>&1
      python3 "$REPO/scripts/build-m4-schema.py" --quiet --out "$TMP/m4.sql" >/dev/null 2>&1
      if docker exec -i "$CONTAINER" psql -U postgres -d "$SCRATCH" -tAq -v ON_ERROR_STOP=1 \
           < "$TMP/m4.sql" >/dev/null 2>&1; then PROOF_DB="$SCRATCH"; fi
    fi
    if [ -z "$PROOF_DB" ]; then
      echo "  ⚠ NOT RUN — could not reach an M4 database to prove RED against."
      bad=$((bad + 1))
    else
      printf -- '-- @RE-RUNNABLE\ndo $$ begin if true then raise exception %s; end if; end $$;\n' \
             "'the invariant is violated'" > "$TMP/red.sql"
      PGDATABASE="$PROOF_DB" ASSERT_FILE="$TMP/red.sql" "$0" >/dev/null 2>&1
      ck "a VIOLATED invariant makes the harness exit 1" 1 "$?"
      printf -- '-- @RE-RUNNABLE\ndo $$ begin if false then raise exception %s; end if; end $$;\n' \
             "'never'" > "$TMP/green.sql"
      PGDATABASE="$PROOF_DB" ASSERT_FILE="$TMP/green.sql" "$0" >/dev/null 2>&1
      ck "a HOLDING invariant makes the harness exit 0" 0 "$?"

      # ⭐ THE FLOOR'S OWN RED PATH — BOTH SIDES OF IT. A ratchet nobody has watched fire is a
      # number in a file, and a ratchet that only ever fires is a disabled gate. This block emits
      # EXACTLY ONE ok-notice while still holding, so floor 1 must pass and floor 2 must fail:
      # that pair is what proves the floor discriminates on COUNT, rather than on the much weaker
      # "did anything run at all", which a zero-notice fixture cannot tell apart.
      printf -- '-- @RE-RUNNABLE\ndo $$ begin raise notice %s; if false then raise exception %s; end if; end $$;\n' \
             "'ok (floor self-test)'" "'never'" > "$TMP/one.sql"
      M4_ASSERTION_FLOOR=1 M4_ASSERTION_FLOOR_FORCE=1 PGDATABASE="$PROOF_DB" \
        ASSERT_FILE="$TMP/one.sql" "$0" >/dev/null 2>&1
      ck "the floor PASSES when the count meets it (1 of 1)" 0 "$?"
      M4_ASSERTION_FLOOR=2 M4_ASSERTION_FLOOR_FORCE=1 PGDATABASE="$PROOF_DB" \
        ASSERT_FILE="$TMP/one.sql" "$0" >/dev/null 2>&1
      ck "the floor FAILS when the selection shrank (1 of 2)" 1 "$?"
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

# Same SIGPIPE trap as check_block, one buffer size away from firing: `$OUT` is ~15 KB today
# because the corpus emits 120 notices. Counted, not `-q`-ed, for that reason.
if [ "$(printf '%s' "$OUT" | grep -c ASSERTIONS_OK)" -eq 0 ]; then
  printf '%s\n' "$OUT" | tail -25 >&2
  echo "FAILED — an assertion raised, or the seed could not build its corpus." >&2
  exit 1
fi

# ⭐ THE FLOOR. `ASSERTIONS_OK` proves nothing RAISED; it cannot prove anything RAN. psql reaches
# the marker just as happily over an empty selection, which is the failure this whole script was
# extracted to stop. Only applied to the real corpus — under ASSERT_FILE the subject is a synthetic
# file whose assertion count the caller chose, so a corpus floor would be meaningless there. Said
# out loud either way: a silently skipped ratchet is the thing being guarded against.
RAN=$(printf '%s' "$OUT" | grep -cE 'NOTICE:.*\bok\b')
if [ -n "${ASSERT_FILE:-}" ] && [ -z "${M4_ASSERTION_FLOOR_FORCE:-}" ]; then
  echo "note: ASSERT_FILE is set, so the corpus floor ($ASSERTION_FLOOR) does NOT apply; $RAN assertion(s) ran."
elif [ "$RAN" -lt "$ASSERTION_FLOOR" ]; then
  echo "FAILED — only $RAN assertions reported ok; the floor is $ASSERTION_FLOOR." >&2
  echo "Nothing raised, so this is not a broken invariant: assertions STOPPED BEING SELECTED." >&2
  echo "Look for an '@MIGRATION-ONLY' marker added without a following '@RE-RUNNABLE' to resume," >&2
  echo "or assertions deleted. If the deletion was deliberate, lower ASSERTION_FLOOR deliberately." >&2
  exit 1
fi

# The rollback is part of the contract: this must not have persisted anything.
LEFT=$(docker exec -i "$CONTAINER" psql -U postgres -d "$DB" -tAq \
        -c "select count(*) from videos where video_id = 'seedvid001';" 2>/dev/null | tr -d '[:space:]')
if [ "$LEFT" != "0" ]; then
  echo "FAILED — the seed PERSISTED ($LEFT row(s) left behind). It must roll back." >&2
  exit 1
fi

echo "schema assertions: $RAN assertions passed against the live schema (floor $ASSERTION_FLOOR), rolled back clean"
