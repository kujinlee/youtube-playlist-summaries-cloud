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
run "1/15  schema + assertions (verify-schema.sh)"      "$SPEC/verify-schema.sh"

# 2. Every guard is mutation-checked — a guard that is never mutated is documentation.
run "2/15  mutation suite (mutate-schema.py)"           "$SPEC/mutate-schema.py"

# 3. COVERAGE, the only gate that looks at what is ABSENT rather than what is present.
#    Enumerates guards from pg_catalog, so a guard added today cannot be skipped.
run "3/15  guard coverage (check-guard-coverage.py)"    ./scripts/check-guard-coverage.py

# 4. COHERENCE, not correctness. Everything above asks "is this right?" — a LOCAL question
#    that can always be answered yes by patching, which is how a wrong shape survives twelve
#    review rounds while the gates get greener. These two compare the design against ITSELF.
run "4/15  sentinel meanings (one NULL, one meaning)"   ./scripts/check-sentinel-meanings.py
run "5/15  vocabulary collisions (one mechanism)"       ./scripts/check-vocabulary-collisions.py

# 6. Docs integrity — cheap, and catches spec/prose drift.
run "6/15  documentation integrity"                     python3 scripts/check-docs.py

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
run "7/15 catalog coverage (no silently narrower digest)" \
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
  run "8/15 schema ASSERTIONS (behaviour, against the live schema)" ./scripts/run-schema-assertions.sh
else
  echo
  echo "═══ 8/15 schema ASSERTIONS — SKIPPED, M4_PHASE=pre ═══"
  echo "    0027 is not applied, so every assertion would be vacuous. NOT a pass."
fi

# 8. Is the manifest the gate trusts still what the schema produces? Without this the gate can be
#    perfectly rigorous about yesterday's shape.
run "9/15 manifest is current (gen-m4-manifest.py --check)" \
    python3 ./scripts/gen-m4-manifest.py --check

# 8. Does the DEPLOYED catalog match, BY DEFINITION and not merely by name?
run "10/15 live catalog matches M4_PHASE=${M4_PHASE:-pre}" \
    python3 ./scripts/check-live-schema.py "$LIVE_FLAG"

# ⭐ ADDED 2026-08-26, FORK (a) STEP 3 — AND IT IS THE POINT OF THE STEP, NOT A DETAIL.
# Session-role access to M4's relations LEFT the live-schema digest (see m4_catalog.SESSION_GRANTEES)
# and moved to RULE 3 in this script. Coverage only actually moves if something RUNS the new home:
# before this line, `check-anon-exposure.py` was named in the roadmap and the plan and invoked by
# NOTHING. Trading an automated gate for a script a human has to remember is not a refactor, it is a
# removal — this repo has shipped a working gate with no caller three times.
# `--local` here because the suite's other nine gates are all local; `--prod` is the M4-β gate and
# belongs to plan Task 9, where the subject that matters is production.
run "11/15 anon exposure + M4 relations are session-role read-only (RULE 3)" \
    python3 ./scripts/check-anon-exposure.py --local

# ⭐⭐ 12. ⟳ r8 M4 (claude) — THE ONLY GATE THAT EXECUTES EITHER FORK-(a) INSTRUMENT AGAINST A
# DATABASE WHERE M4 EXISTS, and until now nothing ran it.
#
# The finding, quoted: *"both destinations of fork (a) are non-executing in the phase the project is
# actually in."* Gate 11 reports `M4 relations present: 0/8` because 0027 has not applied; gate 8 is
# SKIPPED for the same reason. Both say so honestly — and the composition was still that NOTHING in
# the suite could fail on account of RULE 3 or the digest.
#
# This harness builds M4 for real in throwaway databases and sabotages it 25 ways, so it is the
# falsifier the pre-0027 phase otherwise lacks. It is slow (~2 min) and that is the whole price.
#
# ⚠ It writes to the LOCAL cluster. Two of these running at once corrupt each other — see the
# harness header. Do not run this suite concurrently with a reviewer.
run "12/15 the live gate is LOAD-BEARING (mutate-live-schema-check.sh, 29 mutations)" \
    ./scripts/mutate-live-schema-check.sh

# ⭐⭐ 13. THE REASONS THEMSELVES ARE EXECUTED, not re-read — added 2026-08-26.
# `check-catalog-coverage.py` (gate 7) proves the digest is not NARROWING; its own docstring names
# the bound it cannot close: *"a wrong reason here is a real defect that this script will happily
# report as green."* That bound has been hit FIVE times — four in round 7, and a fifth introduced by
# the commit that fixed the fourth, which then survived both halves of rounds 8 AND 9.
# Six of the eighteen rules say "column X is not digested because renderer Y covers it, and Y IS
# digested". That is a claim about a hash: change X, the digest must move. This runs them.
run "13/15 the written EXCLUSION REASONS are true (verify-exclusion-reasons.py)" \
    python3 ./scripts/verify-exclusion-reasons.py

# 14. ⛔ 05_assert.sql IS NOT A MIGRATION, AND THIS IS THE MECHANICAL PROOF.
#     It holds `execute p_sql` (an arbitrary-SQL executor) and `delete from profiles`. If either
#     reaches supabase/migrations/, both are queued for PRODUCTION.
#
# ⚠ THE PLAN'S VERSION OF THIS GUARD IS A FALSE POSITIVE, MEASURED 2026-08-26 against the real 0027:
#       ! grep -qE "execute p_sql|delete from profiles" supabase/migrations/*.sql   ->  FAILS
#     All four matches are COMMENT LINES in 04_artifacts.sql discussing the account-erasure cascade.
#     A gate that is red when nothing is wrong gets disabled, so the comment lines are stripped first.
#     It was also weak the other way: 05_assert.sql matches those two strings only 3 times in 2517
#     lines, so a rename would slip past. The signature below adds the assertion vocabulary.
#
#     MUTATION-TESTED BOTH DIRECTIONS, which is the only reason to trust a rewritten guard:
#       0027 as built .................. 0     (control — must pass)
#       05_assert.sql alone ............ 164
#       0027 with 05 appended .......... 164   (must catch it)
#       the plan's version:  4  vs  7          (cannot discriminate)
#
# ⟳⟳ r10 H2 + M2 — THIS GATE PASSED OVER ZERO INPUT, AND ITS MARGIN RESTED ON AN UNCHECKED PROPERTY.
#
# H2, MEASURED three ways: with the glob unmatched (empty dir), with `supabase/migrations/` missing
# entirely, and with the assertion file placed in a subdirectory, the pipeline returned rc=0 — GREEN.
# An unmatched glob makes `grep` print "No such file or directory", the second `grep` reads empty
# input and exits 1, and `!` turns that into success. **And it is reachable from inside this very
# script**: line 18 is `cd "$(dirname "$0")/.."` under `set -uo pipefail` with NO `-e`, so a failed
# `cd` runs all fourteen gates from the wrong directory and this is the one that answers green.
# Its own sibling shouts the rule — verify-schema.sh: "⛔ A GATE THAT READS AN EMPTY SET PASSES —
# measured twice in this repo" — and it was applied there and not here, in the same commit.
#
# M2: the mutation numbers below (0 / 164 / 164) decompose as `execute p_sql` 1 + `delete from
# profiles` 1 + `assert_raises` 62 + `ASSERTION FAILED` 100. **162 of the 164 are assertion
# VOCABULARY**, and nothing asserted that vocabulary still existed. Two ordinary renames
# (`assert_raises`→`expect_raises`, and the message prefix) drop the margin from 164 to 2 without
# touching either dangerous construct. That is the same rot `check-paid-caller-arrival.py` builds an
# anti-rot canary for — again, one site done and the sibling not.
#
# So the signature is named ONCE and used by both the subject check and the gate.
M4_ASSERT_SIG='execute p_sql|delete from profiles|assert_raises|ASSERTION FAILED'
export M4_ASSERT_SIG
run "14/15 05_assert.sql is NOT in any migration (arbitrary-SQL executor + profile deleter)" \
    bash -c '
      set -uo pipefail
      # (a) the SUBJECT must exist and still match the signature — else the gate has no margin.
      assert_src="'"$SPEC"'/schema/05_assert.sql"
      [ -s "$assert_src" ] || { echo "CANNOT RUN — missing or empty $assert_src"; exit 2; }
      hits=$(grep -hv "^[[:space:]]*--" "$assert_src" | grep -cE "$M4_ASSERT_SIG")
      if [ "$hits" -lt 100 ]; then
        echo "CANNOT RUN — the signature matches 05_assert.sql only $hits times (was 164)."
        echo "  The vocabulary was renamed, so this gate no longer discriminates. TREAT AS NOT RUN."
        exit 2
      fi
      # (b) the CORPUS must be non-empty — a glob that matches nothing is not a clean bill of health.
      #
      # ⟳ r11 M1: the floor used to be `-lt 27`, which is TODAY'"'"'S COUNT WITH ZERO MARGIN in the only
      # direction it can move. Measured: master has 26, so gate 14 was a hard CANNOT RUN on any
      # pre-0027 checkout — and this script has an explicit M4_PHASE=pre branch. `squash` would do
      # the same on any branch. The failure to guard against is an UNMATCHED GLOB, so that is what is
      # tested, plus a sentinel proving the directory is the real migrations directory.
      # `hardcode-only-what-fails-loudly`: a count that legitimately changes is not that.
      shopt -s nullglob
      migs=(supabase/migrations/*.sql)
      if [ "${#migs[@]}" -eq 0 ] || [ ! -f supabase/migrations/0001_core_schema.sql ]; then
        echo "CANNOT RUN — read ${#migs[@]} migration(s) from $(pwd), or 0001_core_schema.sql is absent."
        echo "  An unmatched glob feeds this gate empty input and it reports GREEN. TREAT AS NOT RUN."
        exit 2
      fi
      # ⛔⛔ r11 B1 — DO NOT WRITE `| grep -q` HERE. THE PREVIOUS LINE DID, AND IT WAS A FALSE GREEN
      # OVER THE EXACT VIOLATION THIS GATE EXISTS TO DETECT.
      #
      # `grep -q` exits on the FIRST match and closes the pipe; the producer `grep -hv`, still
      # writing, dies of SIGPIPE (141); `pipefail` — added by the r10 fix on the line above — reports
      # the PRODUCER; and the leading `!` inverts that non-zero into SUCCESS. MEASURED, same tree,
      # same corpus, 8 runs each: WITH pipefail 0 0 0 0 0 0 0 0 (false green), WITHOUT 1 1 1 1 1 1 1 1.
      #
      # It only caught violations near the END of the corpus. A full `05_assert.sql` appended to
      # `0027` PASSED; one `assert_raises` line added to `0001_core_schema.sql` PASSED. The header'"'"'s
      # own mutation table below ("0027 with 05 appended … 164, must catch it") had stopped holding
      # against the committed code, and nothing re-ran it.
      #
      # ⚠ AND THE REPO HAD ALREADY MEASURED THIS, THE SAME DAY, IN THE SIBLING FILE:
      # `run-schema-assertions.sh` carries a ⛔ block saying "DO NOT REINTRODUCE `printf … | grep -q`"
      # with the identical 141/pipefail explanation. r10 fixed it there and reintroduced it here in
      # the very next commit. Not un-generalised — written down, dated, and violated.
      # `grep -c` reads all of its input, so there is no early exit to race. Capture first, match second.
      hits=$(grep -hv "^[[:space:]]*--" "${migs[@]}" | grep -cE "$M4_ASSERT_SIG")
      if [ "${hits:-0}" -ne 0 ]; then
        echo "05_assert.sql'"'"'s signature matched ${hits} time(s) across ${#migs[@]} migration(s)."
        echo "  An arbitrary-SQL executor and/or a profile deleter is queued for PRODUCTION."
        grep -lE "$M4_ASSERT_SIG" "${migs[@]}" | sed "s/^/    /"
        exit 1
      fi
      exit 0'

# 15. ⭐⭐ THE MONEY TRIGGER, AND IT HAD NO CALLER UNTIL NOW — r12 BLOCKING (claude half).
#
# `check-paid-caller-arrival.py` is backlog 26's trigger: it fails the moment a non-test caller
# reaches `record_artifact`, because that is the instant a 5x spend ceiling nobody chose becomes
# real. It was written, self-tested (32 cases), mutation-checked, cited by `dev-process.md:142`
# under "What is mechanically enforced" — and executed by NOTHING. Measured:
#
#   grep -rn "paid-caller" --include=*.sh --include=*.py --include=*.json --include=*.yml .
#   -> 3 hits: two are its own usage lines, and the third is a COMMENT in THIS FILE (:175)
#      admiring its design, 6 lines above the gate list that omitted it.
#
# So a caller could have landed in `lib/` and every gate, CI job and hook stayed green.
#
# ⛔ THIS IS THE FOURTH "live gate with NO CALLER" in this repo, and the r4 BLOCKING that named the
# class — "A gate with no caller is a script, not a gate" — is at :52-55 of this same file, 120
# lines above the list. Writing the lesson down did not wire the gate in. Only this line does.
#
# Runs in BOTH phases: it reads the migration ledger and only consults a live catalog if one happens
# to be reachable, so it needs no database. exit 0 dormant - 1 a paid caller ARRIVED - 2 CANNOT RUN.
run "15/15 backlog 26's money trigger (no non-test caller reaches record_artifact)" \
    python3 scripts/check-paid-caller-arrival.py

echo
if [ "$fail" -eq 0 ]; then
  echo "✅ all schema gates green"
else
  echo "❌ at least one schema gate failed — the work is NOT done"
fi
exit "$fail"
