<!-- codex-review: model=gpt-6.1-sol -->

### R1-F1 — Medium — A commit status suppresses the warning without any check run

`scripts/check-stalled-work.py:390`

**Input:** An open, non-draft `CONFLICTING` PR whose matching head has zero check runs and one pending commit status. The query returns `statusCheckRollup: {"state":"PENDING"}`.

**Result:** Through the self-test’s stubbed-gh seam, the script returns rc 0, `OK … nothing to do`, and `0 stalled`. The hook therefore prints nothing.

GitHub’s rollup combines statuses and check runs; its presence does not establish that a check run exists. [GitHub schema documentation](https://docs.github.com/en/graphql/reference/commits). This misses the specified DIRTY-with-no-check-run case. Query the rollup’s `checkRunCount` and distinguish zero from unknown.

Validation: 203/203 self-tests passed, including the scratch fixture run. Both hand mutations were killed: treating `UNKNOWN` as conflicting, and exempting drafts.

Other probes: `UNKNOWN` is caught on a later turn once `CONFLICTING`; cancelled, skipped, and push-event runs suppress reporting, consistent with the any-check-run rule. No check-context pagination is involved. Future dates display `0m ago`; missing dates remain reported as unknown. Exercised failure paths produced CANNOT RUN. The single live run completed in 3.38 seconds with six open PRs.

## Loosening answers
LOOSENING-CHECK 05fea72e743c: not a loosening
VERDICT: NOT CONVERGED
