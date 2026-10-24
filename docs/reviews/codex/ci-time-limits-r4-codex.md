<!-- codex-review: model=gpt-6.1-sol -->

One finding remains.

**Medium — `.github/workflows/ci.yml:181`: exit 137 still triggers cause-guessing.**

- **Input:** On Ubuntu 26.04 with real sudo-rs 0.2.13 and uutils timeout 0.10.0, replace apt-get with a wrapper that immediately executes `kill -KILL $$`. Keep the update bound at 120 seconds and kill grace at 10 seconds.
- **Observed:** All three attempts finished within one second, but printed:
  ```text
  ::warning::attempt 1 of 3: apt-get update (network): ignored SIGTERM at its 120s bound and was SIGKILLed 10s later (exit 137)
  ```
  The final `CANNOT RUN` repeats that claim; the step exits 1.
- **What happens:** Exit 137 does not establish that the deadline elapsed or SIGTERM was ignored. An independently SIGKILLed process produces the same status. The step fails closed, but its diagnostic invents both timing and cause.
- **Fix:** Report “exit 137: SIGKILL termination; the status alone does not establish whether timeout’s kill grace expired.” Correct the equivalent claims in the workflow comments, backlog #343, and dashboard.

Other checks passed:

- Reran M1: rc=1, 122 seconds; all three warnings correctly named the download’s 30-second timeout.
- Reran M2: initial update exit 100, then recovery; rc=0 in 42 seconds.
- Healthy install with delivered limits: rc=0 in 30 seconds.
- Held-lock, download-hang, and install-hang cases failed closed, named the correct phase, and printed available logs.
- The 1,090-second operation budget is a conservative upper bound; lock waits are inside those bounds. It fits the 1,200-second step cap. The remaining job duration is historically about five minutes, leaving headroom under 30 minutes; worst-case total duration remains unmeasured.
- All 2,003 mutations partitioned exactly once across 12 shards: eleven slices of 167 and one of 166.
- Guard self-tests passed: `check-ci-watched` 82/82, `check-merge-ready` 74/74, `check-python-pin` 111/111.
- Required-check names remain unchanged. The aggregator requires the matrix result to be `success`; no eight-shard count is embedded there.
- #231’s after-numbers are explicitly predictions.

No worktree files or Git state were written.

VERDICT: NOT CONVERGED
