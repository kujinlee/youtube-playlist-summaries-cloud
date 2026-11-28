# Round 1 — `sweep-costs-refresh` (PR #653) — coordinator — CONVERGED (both halves); four findings filed to backlog #754

Both halves reviewed `83cfa335`, which rebuilds `scripts/sweep-costs.json` from the nightly run 46048742954 at
`4e247843`. Each re-ran `scripts/sweep-costs.py` on that run's 38 shard logs and got a byte-identical table. Each
confirmed that all 107 manifest targets are priced, that `cost_coverage` accepts the table, and that the two hash
seeds are divided out. Neither found a gate loosened.

| id | half | severity | finding | disposition |
|---|---|---|---|---|
| C1 | Claude | Medium | check-merge-ready is still priced 18-24% below what PR CI measured; about 260 s of slack against the 1680 s budget | filed (backlog #754): the fix is headroom in the cut, not a price edit |
| C2 | Claude | Low | most rows have one sample; one runner's speed moves a price by about ±25% | filed (backlog #754) |
| C3 | Claude | Low | `ci.yml:1392` and `check-plan-code.py:1665` still name the old source runs | filed (backlog #754) |
| C4 | Claude | Low | the 21 hand-timed `sources` notes were dropped (nothing reads them) | filed (backlog #754) |

Codex: no findings. It applied the slower PR CI prices to the predicted cut and found the largest shard still under budget.

C1 is why this PR's description calls the shard times a prediction. Whether it is enough is measured by the
re-run of PR #651 and PR #652 on the new cut.

```yaml
round: 1
fixes_nontrivial: false
subject: sweep-costs-refresh
halves:
  codex: ran
  claude: ran
findings:
  - {id: C1, severity: Medium, aim: deliverable, fix_induced: false, component: sweep-costs, disposition: filed}
  - {id: C2, severity: Low, aim: deliverable, fix_induced: false, component: sweep-costs, disposition: filed}
  - {id: C3, severity: Low, aim: deliverable, fix_induced: false, component: sweep-costs, disposition: filed}
  - {id: C4, severity: Low, aim: deliverable, fix_induced: false, component: sweep-costs, disposition: filed}
```

Reviews: `docs/reviews/codex/sweep-costs-refresh-r1-codex.md`, `docs/reviews/claude/sweep-costs-refresh-r1-claude.md`.
