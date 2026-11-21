# Round 5 — `usage-hook-master` — coordinator — CONVERGED (Claude): the sweep cost-table re-price

Round 5 reviews one commit made after round 4, because CI's mutation-sweep shard 17 ran out of its 1680 s budget
at mutation 182 of 297 (job 136801140835). No mutant survived. The partitioner had packed `check-run-hook.py`'s
mutations on a stale price: 1.9 s, from 36 samples older than the 163-case self-test. The commit re-prices them to
52 s for the control and 42 s for a mutation, measured in that job. The Claude half,
`docs/reviews/claude/usage-hook-master-r5-claude.md`, is CONVERGED, with two MINOR findings and no code defect.
The Codex half is a gap by alternation, because round 4 was Codex's.

REVIEW GAP: codex — alternation.

```yaml
round: 5
fixes_nontrivial: false
subject: usage-hook-master
halves:
  codex: gap
  claude: ran
findings:
  - {id: C1, severity: Minor, aim: deliverable, fix_induced: false, component: sweep-costs, disposition: rejected}
  - {id: C2, severity: Minor, aim: deliverable, fix_induced: false, component: sweep-costs, disposition: rejected}
```

| # | Severity | Finding | Disposition |
|---|---|---|---|
| C1 | MINOR | The row still carries `samples: 36` / `mutations: 36` from the old CI table. | **Rejected.** Nothing reads them, and the next `sweep-costs.py --run` regeneration rewrites the row from CI logs. |
| C2 | MINOR | The mutation costs fall into two groups, about 25 s and about 52 s, so 42 s is a mean. | **Rejected.** The partition balances means, and the reviewer showed that the worst-case shard (20 mutations at 52 s, about 1144 s) is under budget. |

The evidence is the reviewer's: `sweep-costs.py --self-test` 36/36 and `check-plan-code.py --self-test` 506/506.
`sweep_partition` over the full tree puts the `check-run-hook.py` mutations across shards 19–21, and its slowest
shard is estimated at 950 s.
