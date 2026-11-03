<!-- codex-review: model=gpt-6.1-sol -->

CONVERGED — no actionable defects found.

- F5’s open descriptor keeps the original inode alive. `samestat` compares both device and inode, so writing in place fails the assertion.
- The STOPPED branch always returns 1; it cannot turn a failing run green. No unrelated production defect was found that newly suppresses its named case.
- Both mutation entries bind exactly once. Applying each independently produced exit 1, STOPPED, and failures attributed to both named lifetime cases.
- All 455 cases still run on the unmodified code; no assertion was removed.

Self-tests passed: backfill **268/268**, check-main-drivable **455/455**. No full mutation slice run.
