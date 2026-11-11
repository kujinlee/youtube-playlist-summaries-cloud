<!-- codex-review: model=gpt-6.1-sol -->

BLOCKER: None. MAJOR: None. MINOR: None.

Verified on HEAD `1cdc8e4e`:

- Loader accepts all 178 manifest entries, matching pin 178. Every edit anchor matches exactly once.
- Both mutations are killed and attributed to their named cases; zero survivors.
- Temporary-tree controls pass before and after: 310/310.
- `python3 scripts/check-plan-code.py --self-test`: 310/310 passed, matching the corrected declaration.

VERDICT: CONVERGED
