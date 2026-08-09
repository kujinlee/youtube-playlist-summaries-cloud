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
run "1/6  schema + assertions (verify-schema.sh)"      "$SPEC/verify-schema.sh"

# 2. Every guard is mutation-checked — a guard that is never mutated is documentation.
run "2/6  mutation suite (mutate-schema.py)"           "$SPEC/mutate-schema.py"

# 3. COVERAGE, the only gate that looks at what is ABSENT rather than what is present.
#    Enumerates guards from pg_catalog, so a guard added today cannot be skipped.
run "3/6  guard coverage (check-guard-coverage.py)"    ./scripts/check-guard-coverage.py

# 4. COHERENCE, not correctness. Everything above asks "is this right?" — a LOCAL question
#    that can always be answered yes by patching, which is how a wrong shape survives twelve
#    review rounds while the gates get greener. These two compare the design against ITSELF.
run "4/6  sentinel meanings (one NULL, one meaning)"   ./scripts/check-sentinel-meanings.py
run "5/6  vocabulary collisions (one mechanism)"       ./scripts/check-vocabulary-collisions.py

# 6. Docs integrity — cheap, and catches spec/prose drift.
run "6/6  documentation integrity"                     python3 scripts/check-docs.py

echo
if [ "$fail" -eq 0 ]; then
  echo "✅ all schema gates green"
else
  echo "❌ at least one schema gate failed — the work is NOT done"
fi
exit "$fail"
