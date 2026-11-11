<!-- codex-review: model=gpt-6.1-sol -->

NO FINDINGS.

Applied both mutants independently to scratch copies and ran `python3 scripts/check-stalled-work.py --self-test`.

- Control: 183/183 passed.
- Each changed `expect` matched exactly one printed failing case name, character for character.
- Both named cases directly exercise the mutated requirement.
- The removed R2-3 case still passes under that mutant: `merge-tree` rejects the whitespace-divergent branch before the mutated patch-ID check. Removing its expectation loses no distinct behavior coverage.
