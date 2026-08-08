#!/usr/bin/env bash
# PostToolUse hook — fires after any Edit/Write touching the blob-addressing schema.
#
# WHY A HOOK RATHER THAN A WRITTEN RULE. The obvious version of this is a directive
# in an always-loaded doc: "when you change schema, run the gates; do not report
# done if one fails." That is a rule which depends on remembering — precisely the
# shape this project's own reviews keep finding as defects in the CODE, and which
# `docs/dev-process.md` had grown 576 lines of. A rule that fires exactly when it is
# relevant beats a rule sitting in a document nobody re-reads.
#
# WHY PostToolUse AND NOT PreToolUse: nothing here should be BLOCKED. Editing schema
# is the work. What must not happen is editing it and then reporting success without
# running the gates — so the right moment is immediately after the edit, while there
# is still a turn left to act on it.
#
# THE GATE THAT MATTERS MOST is guard coverage. The other three check that what
# exists is correct; only that one enumerates the population from `pg_catalog` and
# notices what is ABSENT. Two defects survived seven adversarial review rounds
# because every other instrument here is opt-in and they therefore share one blind
# spot. See docs/review-method.md.
set -uo pipefail

FILE_PATH=$(cat | python3 -c "
import json, sys
try:
    print(json.load(sys.stdin).get('tool_input', {}).get('file_path', ''))
except Exception:
    pass
" 2>/dev/null) || FILE_PATH=""

case "$FILE_PATH" in
  *2026-08-03-stable-blob-addressing/schema/*.sql|*2026-08-03-stable-blob-addressing/mutate-schema.py)
    cat <<'EOF'

╔══════════════════════════════════════════════════════════════════════════╗
║  ⚠️  SCHEMA GATES — run before reporting this task done                  ║
╠══════════════════════════════════════════════════════════════════════════╣
║                                                                          ║
║      ./scripts/check-schema-gates.sh                                     ║
║                                                                          ║
║  Runs all four: schema+assertions, mutations, GUARD COVERAGE, docs.      ║
║                                                                          ║
║  Note: `psql -f schema/05_assert.sql` does NOT work standalone — the     ║
║  assertions need the schema loaded in the SAME transaction.              ║
║                                                                          ║
║  If you added a constraint, index or trigger, guard coverage will fail   ║
║  until it is classified SHAPE or SEQUENCE in check-guard-coverage.py.    ║
║  The question is not "is this guard correct?" — both defects it was      ║
║  built for were plainly correct guards — but:                            ║
║                                                                          ║
║      WHAT DOES IT DO WHEN THE CALLER IS MERELY *SECOND*?                 ║
║                                                                          ║
║  SHAPE    → the caller is wrong. Reject.                                 ║
║  SEQUENCE → concurrency; the caller may already have spent money.        ║
║             Reconcile: upsert, no-op, or typed outcome. Never a raw      ║
║             rejection.                                                   ║
╚══════════════════════════════════════════════════════════════════════════╝
EOF
    ;;
esac

exit 0
