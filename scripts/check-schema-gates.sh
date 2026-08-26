#!/usr/bin/env bash
# Every gate that gets a vote on the blob-addressing schema, in one command.
#
# WHY ONE SCRIPT. Three separate commands is three chances to run two of them and
# report success. That is the same failure this schema keeps producing in its own
# code — a rule that depends on remembering — so it does not belong in the workflow
# either. One entry point, and it is what the hook and the docs both name.
#
#   ./scripts/check-schema-gates.sh
#     exit 0 = every gate green
#     exit 1 = a gate failed; the failing gate's own output is above
#
# NOTE ON RUNNING THE ASSERTIONS: `05_assert.sql` CANNOT be run standalone
# (`psql -f schema/05_assert.sql` fails). It asserts against tables that only exist
# inside the same transaction, so `verify-schema.sh` concatenates 01/03/04/05 between
# a `begin` and a `rollback`. Gate 1 below is the only correct way to run them.
set -uo pipefail
cd "$(dirname "$0")/.."
SPEC="docs/superpowers/specs/2026-08-03-stable-blob-addressing"
fail=0

run() {
  echo
  echo "═══ $1 ═══"
  shift
  if "$@"; then :; else echo "❌ FAILED: $*"; fail=1; fi
}

# 1. The schema executes against live Postgres, and every behavioural assertion holds.
run "1/10  schema + assertions (verify-schema.sh)"      "$SPEC/verify-schema.sh"

# 2. Every guard is mutation-checked — a guard that is never mutated is documentation.
run "2/10  mutation suite (mutate-schema.py)"           "$SPEC/mutate-schema.py"

# 3. COVERAGE, the only gate that looks at what is ABSENT rather than what is present.
#    Enumerates guards from pg_catalog, so a guard added today cannot be skipped.
run "3/10  guard coverage (check-guard-coverage.py)"    ./scripts/check-guard-coverage.py

# 4. COHERENCE, not correctness. Everything above asks "is this right?" — a LOCAL question
#    that can always be answered yes by patching, which is how a wrong shape survives twelve
#    review rounds while the gates get greener. These two compare the design against ITSELF.
run "4/10  sentinel meanings (one NULL, one meaning)"   ./scripts/check-sentinel-meanings.py
run "5/10  vocabulary collisions (one mechanism)"       ./scripts/check-vocabulary-collisions.py

# 6. Docs integrity — cheap, and catches spec/prose drift.
run "6/10  documentation integrity"                     python3 scripts/check-docs.py

# 7-8. THE SUBJECT AXIS. Everything above rebuilds the schema from the SPEC FILES and asks whether
# the spec is self-consistent. None of it can answer "did the migration APPLY?" — the wrong question
# for the one milestone whose purpose is making the spec execute (architecture review, finding 3).
#
# ⟳ r4 BLOCKING (codex + claude): the live gate existed for a whole day and NOTHING CALLED IT. Not
# this suite, not CI, not a hook, not package.json. Every claim that the promotion gate verifies the
# deployed catalog was true only for a human who typed the command. A gate with no caller is a
# script, not a gate.
#
# ⚠ M4_PHASE is REQUIRED once 0027 exists — `pre` before it is applied, `post` after — because a
# gate that guesses its own polarity is how this plan shipped an unsatisfiable milestone twice.
if [ -f supabase/migrations/0027_stable_blob_addressing.sql ] && [ -z "${M4_PHASE:-}" ]; then
  echo
  echo "⛔ CANNOT RUN — 0027 exists, so this suite needs M4_PHASE=pre|post to know which polarity"
  echo "   the live catalog should satisfy. Refusing to guess. Treat this as NOT RUN."
  exit 2
fi
case "${M4_PHASE:-pre}" in
  pre)  LIVE_FLAG=--expect-absent  ;;
  post) LIVE_FLAG=--expect-present ;;
  *)    echo "M4_PHASE must be pre or post, got '${M4_PHASE}'" >&2; exit 2 ;;
esac

# 7. ⟳ r6: is the DIGEST still as wide as it claims? Enumerates every column of every catalog the
#    digest reads, straight from pg_attribute, and fails unless each is digested or excluded WITH A
#    WRITTEN REASON. r6 found `proisstrict` and `attacl` missing for the same cause: the previous
#    list was assembled from the sabotages someone had already run.
run "7/10 catalog coverage (no silently narrower digest)" \
    python3 ./scripts/check-catalog-coverage.py

# ⭐ 8. BEHAVIOUR, not structure — Phase 6 #2, fork (a) (user decision 2026-08-25).
# `05_assert.sql` carries 104 `raise exception`s and, until this commit, ZERO markers — so this
# harness was a permanent fail-closed CANNOT RUN and 2,239 lines of security assertion had never
# executed. Task 8 was scheduled LAST; Phase 6 #2 moved it first, because round 7 spent a BLOCKING
# finding rediscovering the anon-TRUNCATE hole this file had already found, already fixed and
# already asserted.
#
# ⚠ WIRED IN THE SAME COMMIT THAT MAKES IT RUN. A live gate with no caller is a defect this repo has
# already shipped twice — r4 B4: "the live gate existed for a whole day and NOTHING CALLED IT."
# Skipped in the `pre` phase BY DESIGN: with 0027 unapplied every assertion is vacuous, and the
# harness says so itself rather than passing.
if [ "${M4_PHASE:-pre}" = "post" ]; then
  run "8/10 schema ASSERTIONS (behaviour, against the live schema)" ./scripts/run-schema-assertions.sh
else
  echo
  echo "═══ 8/10 schema ASSERTIONS — SKIPPED, M4_PHASE=pre ═══"
  echo "    0027 is not applied, so every assertion would be vacuous. NOT a pass."
fi

# 8. Is the manifest the gate trusts still what the schema produces? Without this the gate can be
#    perfectly rigorous about yesterday's shape.
run "9/10 manifest is current (gen-m4-manifest.py --check)" \
    python3 ./scripts/gen-m4-manifest.py --check

# 8. Does the DEPLOYED catalog match, BY DEFINITION and not merely by name?
run "10/10 live catalog matches M4_PHASE=${M4_PHASE:-pre}" \
    python3 ./scripts/check-live-schema.py "$LIVE_FLAG"

echo
if [ "$fail" -eq 0 ]; then
  echo "✅ all schema gates green"
else
  echo "❌ at least one schema gate failed — the work is NOT done"
fi
exit "$fail"
