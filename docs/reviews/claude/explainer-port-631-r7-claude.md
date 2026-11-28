Reviewed head: 864e442441598dc0737cc36e32194fddcbc9ccac

# Round 7 — `explainer-port-631` (PR #651) — Claude half — `scripts/sweep-costs.json` after the merge of origin/master

Scope: only `scripts/sweep-costs.json`, as master's PR #653 table plus the branch's explainer-serve re-price.
Mandate: refute that the merged table is correct.

## What was checked, and what it showed

| Check | Result |
|---|---|
| `git diff origin/master -- scripts/sweep-costs.json` | only two hunks: one added `hand-timed:` line in `sources`, and the `scripts/explainer-serve.py` row's control/recontrol/mutation set to 52.0/52.0/55.0. Nothing else differs from master |
| `json.load` | parses |
| `python3 scripts/sweep-costs.py --self-test` | 36/36 passed |
| `python3 scripts/check-plan-code.py --self-test` | 506/506 passed (27 s) |
| `load_sweep_costs` + `cost_coverage(costs, muts, 38)` (module imported with `sys.modules["cpc"]`) | accepted, no reason returned. 6829 manifest entries over 107 targets; every target priced; no table row without a manifest |
| `sweep_plan` for this PR's selection (`select_manifests("pull_request", <diff vs merge-base>, …, sample_key=HEAD)`) | the selection is FULL (`docs/backlog.md is named by 56 of 105 targets — a shared module`), so the PR cuts the whole manifest. The table is used, not round-robin |
| 38-shard cut, estimates (`sweep_partition` + `shard_estimate`) | every shard 1314-1335 s. explainer-serve's 146 mutations spread over shards 25-31: 26-30 hold 22 each (1314 s each), 25 and 31 share it with neighbours |
| Budget | `timeout-minutes: 30` on a PR (`ci.yml`, `&sweep-limit`), less `SWEEP_HEADROOM` = 120 s (`check-plan-code.py:147`, `ci_deadline`) = 1680 s from the job's first step. Setup takes 20-40 s (backlog #754), which leaves about 1640-1660 s for the sweep |
| Explainer-serve price | 55 s/mutation is taken from PR CI itself (job 140943010037, 54.7 s), so the PR-vs-nightly gap does not apply to this row. At 57.4 s (+5%), the worst explainer shard is 1383 s. That fits |

The explainer-serve row itself is correct, and I could not refute it. My refutation attempt landed on what the re-price does to every
other shard. That is R1.

## Findings

### R1 — Medium — `scripts/sweep-costs.json:593-599` (explainer-serve row), and its effect on the check-merge-ready shards

The re-price raises explainer-serve's total weight from about 1,243 s (146 × 8.4 + 16) to about 8,134 s (146 × 55 + 104).
That is right, and it is spread evenly: the cost-weighted cut raises its per-shard target from master's 1093-1133 s
(PR #653's predicted range) to about 1316-1335 s here. Each shard carries about 190 s more by estimate.
The re-price is correct, but it uses up most of the slack that backlog #754 C1 already called too thin.

Failure scenario, using the rates PR CI measured (PR #653's commit message and backlog #754): check-merge-ready is
priced 22.6 s, while PR CI measured 26.6-28.0 s. Shards 8, 9 and 10 each hold 56 check-merge-ready mutations and nothing else.
Each is estimated at 1316 s, which comes to **1549 s at 26.6 s and 1630 s at 28.0 s**. The sweep has about 1640-1660 s.
So at the upper measured rate these three shards finish 10-30 s before `BUDGET_STOP`. A runner a few percent slower than
the slowest one already seen stops them as CANNOT RUN with mutants unreached. That is the same red PR #651 shards 8, 9 and 11 hit on
11-28. On master the same shards would be about 1378 s (#754 C1). Applying a uniform 1.24 to every non-explainer target
(#754's 18-24% upper bound) puts 22 of 38 shards past 1640 s. At 1.20 the worst is 1602 s.

This is not a defect in the row. Lowering the price to buy headroom would reintroduce the packing that blew shard 30's budget twice.
The fix is #754's own: headroom in the cut (a factor on the estimate, or a lower per-shard target, or more shards).
That lives in `check-plan-code.py`/`ci.yml`, outside this scope. Still, this PR is the change that makes #754 urgent, so it should be
stated in the PR and on #754 rather than left implicit. **Not blocking:** the estimate fits the budget at every rate measured so
far, and the outcome of an overrun is a loud CANNOT RUN, not a false pass.

### R2 — Low — `scripts/sweep-costs.json:598-599` (`samples: 2`, `mutations: 127`)

The hand-edited row keeps master's `"samples": 2, "mutations": 127`. The re-price comes from ONE CI job, and this tree's
manifest holds 146 explainer-serve entries; the branch added 19. `recontrol` (52.0) is not a measurement either: it copies
`control`. Nothing reads these fields (`parse_sweep_costs` uses only control/recontrol/mutation; `samples` and `mutations` are
written by `sweep-costs.py:252` only), so the cut is unaffected. But a reader who trusts the row sees two samples over 127
mutations. Suggested: `samples: 1`, `mutations: 146`, or leave it, since the `sources` line already states the provenance.
(The same stale-count shape exists on master for `check-shipping-sets.py`, 215 against 220. That one is master's, not this branch's.)

## Loosening question

Is any change a loosening? Not a loosening. A higher price only moves mutations between shards. It never removes one
from measurement (`partition_line`'s contract: every entry is measured exactly once).

VERDICT: CONVERGED
