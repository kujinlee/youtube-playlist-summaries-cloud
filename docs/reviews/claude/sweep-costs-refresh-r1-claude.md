Reviewed head: 83cfa335e53e073527548af8a454af9133bf5f1c

# sweep-costs-refresh — round 1, Claude half (adversarial)

Scope: `git diff origin/master...HEAD`, which changes one file, `scripts/sweep-costs.json` (PR #653).

## What I tried to refute, and what held

| Claim | How I attacked it | Result |
|---|---|---|
| The table was produced by the tool from the run it names | Re-ran `scripts/sweep-costs.py --run 46048742954@4e247843 <tree> <logs> --out <scratch> --predict 38` | **Byte-identical** (`cmp`). 38 shards, 6805 mutations attributed, 107 targets, predicted 1093-1133 s |
| The logs come from run 46048742954 at 4e247843 | The tree's `HEAD` is 4e2478437842…; every shard log checks out that sha; every verdict lists seeds `0, 3099070005`, and ci.yml derives seed 2 as `1 + RUN_ID % 4294967295`, which is 3099070005 for 46048742954 | Holds (no GitHub call made) |
| The prices are ONE seed's seconds | `seed_runs` runs the seeds one after another (`check-plan-code.py` `seed_runs`, a list comprehension), so dividing each gap by 2 is right in form. Measured: for the 60 targets whose file did not change between 033fe20c and 4e247843 and whose old row had at least 10 one-seed samples, the median new/old per-mutation ratio is 1.04 (1.02 over targets above 1 s) | No bias from the division |
| Nothing is lost | Old and new tables price the same 107 targets; every target in the HEAD manifest (6810 entries) is priced; `cost_coverage(.., 38)` is None; `parse_sweep_costs` accepts it. Only the hand-timed `sources` notes are gone (C4) | Holds |
| Nightly prices taken from a run that stopped early | No shard's log reports a suite STOPPED by the time budget, and every shard's verdict is `OK … 0 survivor(s)`. The slowest shard used 3280 s of its 3445 s | Holds |
| No gate is loosened | `defaults` rose (mutation 10.162 → 11.656, fixed 20.181 → 24.192). No consumer reads `samples` or `mutations` | Holds |
| Self-tests | `sweep-costs.py --self-test` 36/36. `check-plan-code.py --self-test` 503/506: the 3 reds are `node_modules/typescript` and `markdown-it` missing from this worktree. That is environmental and unrelated to the table | Not caused by the change |

## Findings

**C1 — Medium — scripts/sweep-costs.json (`scripts/check-merge-ready.py` row, `"mutation": 22.6`).**
The table is still below the PR-CI rates cited in its own commit message (26.6-28.0 s per mutation), so "PR shards stop running out of their time budget" has not been shown; it is only predicted.
- At N=38 the new cut puts check-merge-ready ALONE on shards 9-12, 47 mutations each, estimated at 1112 s apiece.
- I re-priced the partition at the PR-measured rates (check-merge-ready ×28.0/22.6, check-plan-code ×17.7/16.08, session-state ×13.3/12.111), with the partition left unchanged. Shards 10-12 come to **1378 s**.
- A PR job's budget is 1680 s (30 min less `SWEEP_HEADROOM` 120 s), counted from the job's first step. About 20-40 s of that goes before the first progress line (measured on the nightly: 19-38 s from job start to the TIME BUDGET line). That leaves about 260 s of slack.
- With a further 10% runner slowdown on every target the worst shard is 1516 s, which still fits. At 20% it is 1654 s, and with setup added it overruns.
- Failure scenario: a PR whose suite selection is large (unplaceable or harness: the full manifest or a big sample) lands on a slow runner, or lands after check-merge-ready gains more cases (the PR-measured 26.6-28.0 s may already reflect suites grown on #651/#652 branches past 4e247843). Shards 9-12 then stop with mutations not reached, which is the symptom this PR claims to fix.
- This is not a blocker: the new table is strictly closer to CI than the old one, and it fits at the measured rates. But the commit message should say "prediction" rather than claim a fix, and the trigger for the next refresh should be stated.

**C2 — Low — scripts/sweep-costs.json (every row, `"samples": 1` for most targets).**
Each target's price now comes from ONE nightly run, in practice from one or two runners, because the cost cut keeps a target on 1-2 shards. The old table pooled 76 shard samples over two runs.
- Measured noise: among unchanged targets priced above 1 s, the new/old ratio ranges from 0.78 (`sweep-red-alert.py`) to 1.26 (`check-paid-caller-arrival.py`). One runner's speed can move a price by about ±25%.
- Failure scenario: a heavy target priced on a fast runner is under-priced by about 20%, and that compounds with C1.
- Mitigation available: `sweep-costs.py` accepts several `--run`s. Pooling this run with the next nightly would cut the noise.

**C3 — Low — .github/workflows/ci.yml:1392 and scripts/check-plan-code.py:1665.**
Both comments still describe the committed table as "built from runs 43662666915 (033fe20c) and 43625371110 (26a04323)". After this PR, neither run is in `sources`.
- Each comment is dated as a #588 prediction, so it is history rather than a false claim about now.
- But a reader looking for the table's provenance is pointed at runs it no longer contains.

**C4 — Low — scripts/sweep-costs.json `sources` (old lines 4-23 removed).**
The 21 `hand-timed:` provenance notes are dropped. They are now moot, because every target has a CI sample. They are recoverable from git history.
- Nothing reads them, so nothing breaks.
- Recorded so the loss is a known choice and not an accident: for example, the `check-run-hook.py` note recorded that a 36-sample price predated a 163-case suite.

VERDICT: CONVERGED
