# Round 1 — `reshard-sweep` (PR #445, backlog #231) — coordinator — fixed; CONVERGED on the fold

```yaml
round: 1
fixes_nontrivial: false
subject: reshard-sweep
halves:
  codex: ran
  claude: ran
findings:
  - id: M1
    severity: Major
    aim: deliverable
    disposition: fixed
    fix_induced: false
  - id: m1
    severity: Low
    aim: instrument
    disposition: refuted
    fix_induced: false
  - id: m2
    severity: Low
    aim: deliverable
    disposition: fixed
    fix_induced: false
```

**Codex: CONVERGED, no findings.** It checked:
- the partition: 2,512 entries, each in exactly one of 24 shards;
- the shard count's single source (`strategy.job-total`);
- the required context `mutation-sweep-complete`, which is unchanged;
- every shard under 1,500 s (558–1,032 s).

**Claude: 1 Major and 2 Minor**, with the same measurements.
- **M1, fixed.** The comment's claim that the concurrency limit is at least 35 is refuted by this PR's own run, which held exactly 20 jobs at once (the 35 counted cancelled jobs). So 24 shards run as two waves: 1,473 s end to end against a 1,032 s slowest shard. The comment and the PR body now state the measured 20 and the two-wave cost. 24 is kept for its per-shard headroom. Whether 18 shards (one wave) is faster end to end is a measurement, filed as **backlog #415** with a paired-run FAILS IF.
- **m1, refuted as a defect.** CI's only red is `check-review-recorded`, the pending-review gate this round clears.
- **m2, fixed.** Row #231's text said "14 jobs (12 shards …)"; it now says 26 jobs and 24 shards. Its FAILS IF names a run on master, so #231 is closed by the first master run, not by this branch.

The fold changes only comments, prose and a filed row: no executable line. So no second round is needed; the final-tree gate is CI on the pushed head.
