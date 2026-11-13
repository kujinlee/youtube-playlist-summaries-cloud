<!-- codex-review: model=gpt-6.1-sol -->

Reviewed HEAD `25bbc722`. No findings on the flagged paths.

A hung mutant cannot count as KILLED. Timeouts still return rc 2 / NOT CHECKED, count as survivors, and invalidate measurement. A budget stop exits non-zero and reports unfinished and unreached work before teardown.

`python3 scripts/check-plan-code.py --self-test`: **418/418 passed**. No mutation sweep run.

## Loosening answers
LOOSENING-CHECK 8d2f8bd4cc54: not a loosening
LOOSENING-CHECK 3f833ef4b8d9: not a loosening
LOOSENING-CHECK 38f234e35820: not a loosening
LOOSENING-CHECK 7dd25f6d44c9: not a loosening
LOOSENING-CHECK af4690f3e18e: not a loosening
LOOSENING-CHECK d1158d019edf: not a loosening
LOOSENING-CHECK 2ff4eab35bd1: not a loosening
LOOSENING-CHECK a08be7d2cf13: not a loosening
VERDICT: CONVERGED
