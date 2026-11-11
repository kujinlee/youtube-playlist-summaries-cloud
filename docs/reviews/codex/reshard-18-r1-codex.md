<!-- codex-review: model=gpt-6.1-sol -->

CONVERGED — no actionable defects found at `0b4f691a`.

- Matrix has 18 jobs. Each passes `strategy.job-index` and `strategy.job-total` to `--shard0`; no hardcoded `/24` remains. The completion job aggregates the matrix without encoding N.
- `shard_slice` uses `muts[index - 1::total]`. Checked all 3,313 manifest entries at N=18: every entry appears exactly once; none dropped or duplicated.
- Timeout headroom: 1,800 − 1,184 = **616 seconds (10m16s)**, or **1.52×** the measured slowest shard. It is also 316 seconds below the 1,500-second reopening trigger.
- Documentation distinguishes measurements from predictions. The claimed reduction is 510 seconds, **29.9%**.
- Self-test: **278/281 passed**. All three failures concern missing `node_modules/typescript` in this checkout, so a fully green self-test remains unverified.

No files under `.claude/plans/` were read.
