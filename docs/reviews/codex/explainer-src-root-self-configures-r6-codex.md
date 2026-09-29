<!-- codex-review: model=gpt-5.5 -->

## Verdict
CONVERGED

No new Blocking or High found.

## Findings
None.

I re-ran the guard and self-test, checked the duplicate-key parser against real and constructed sources, verified CI runs both `check-fixture-variation.py` and its `--self-test`, confirmed `-OO` reports CANNOT RUN instead of crashing, and falsified the two r5 regressions on scratch copies. Deleting `repo_root.start` and `src_root_help.pidfile` now fails by name.
