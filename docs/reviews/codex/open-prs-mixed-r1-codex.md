<!-- codex-review: model=gpt-6.1-sol -->

No findings.

- Fated rows are excluded from title resolution; closed PRs aren’t collected. CANNOT RUN can retain ownership of a known open PR, consistent with existing behavior.
- Finished leaves still require `open_prs`; a stale ledger flag alone cannot resurrect them. Parked leaves remain excluded.
- All three new cases fail when early resolution is reverted. Both mixed-thread cases fail when finished-leaf admission is reverted.
- `python3 scripts/goal-tree.py --self-test`: **394/394 passed**.

VERDICT: CONVERGED
