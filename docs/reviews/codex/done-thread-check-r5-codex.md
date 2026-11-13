<!-- codex-review: model=gpt-6.1-sol -->

Reviewed HEAD `f8777491` against `1b0d3eac`. No BLOCKER findings.

Each changed file:

- `scripts/check-review-decision.py`: adds a deterministic reverse-order tie case; count becomes 119.
- `scripts/check-selftest-counts.py`: adds a forced reverse-completion case with patch restoration; count becomes 60.
- `scripts/mutations/check-review-decision.json`: includes the deterministic tie case in expected failures.
- `scripts/mutations/check-selftest-counts.json`: includes the forced-completion case in expected failures.
- `scripts/mutations/session-state.json`: re-anchors the kind-blind comparison mutation to the intersection check.
- `scripts/session-state.py`: adds `main` and `gt` parameter cases, imports `types`, and updates the count to 129.
- `docs/backlog.md`: records both known #506 instances fixed, with the broader sweep remaining open.
- `docs/dashboard-entries.md`: records #506 fixes and updates #507’s test count.
- `docs/goal-threads.md`: updates #506’s progress.
- `docs/reviews/codex/seed-stable-mutants-r1-codex.md`: adds first-round review evidence.
- `docs/reviews/codex/seed-stable-mutants-r2-codex.md`: adds confirmation after rebase.
- `docs/reviews/coordinator/seed-stable-mutants-r1-coordinator.md`: records first-round convergence and review gap.
- `docs/reviews/coordinator/seed-stable-mutants-r2-coordinator.md`: records second-round convergence and review gap.
- `docs/reviews/decision-scheme/decision-log.jsonl`: records the seed-stable-mutants outcome.
- `docs/reviews/verdicts/seed-stable-mutants-r1-codex.verdict.json`: adds first-round verdict metadata.
- `docs/reviews/verdicts/seed-stable-mutants-r2-codex.verdict.json`: adds second-round verdict metadata.

Confirmed through in-memory mutations: ignoring `main` fails its new case (`[False, False]` versus `[True, False]`); ignoring `gt` fails its new case (`False` versus `True`). Each exits 1 with 128/129 passing. Both other changed suites pass: 119/119 and 60/60.

`python3 scripts/session-state.py --self-test` exits 0:

```text
129/129 self-test cases passed
```

VERDICT: CONVERGED
