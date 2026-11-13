<!-- codex-review: model=gpt-6.1-sol -->

No findings outside the approved loosening. All three flipped cases match that decision; all 11 changed mutations fail at their named assertions.

Self-tests passed: merge-ready 363/363; plan-code 418/418. Worktree clean.

## Loosening answers
LOOSENING-CHECK f420a0304250: finding: answers now survive changes to other files when their bound entries match, as approved
LOOSENING-CHECK 6f2121cd3021: finding: answers now survive changes to other files when their bound entries match, as approved
LOOSENING-CHECK 10f587a01725: not a loosening
LOOSENING-CHECK 1d9326b385a7: finding: a merge changing only a doc now preserves the answer, as approved
LOOSENING-CHECK 766bf98f8fce: finding: a merge changing only a doc now preserves the answer, as approved
LOOSENING-CHECK 7895f28f4d34: finding: a merge changing only a doc now preserves the answer, as approved
LOOSENING-CHECK 78c781c7b7fc: finding: a merge changing only a doc now preserves the answer, as approved
VERDICT: CONVERGED
