# Round 1 — `sweep-timeout-754` (backlog #754) — coordinator — both halves NOT CONVERGED; five findings, four fixed, one answered

Subject: `66590fea` raises the mutation sweep shard job's `timeout-minutes` (`&sweep-limit`) from 30 to 40 on every
event except the schedule, and moves check-merge-ready's accounted-mentions key to the line's new text.

| id | half | severity | finding | disposition |
|---|---|---|---|---|
| X1 | codex | Medium | the longer limit is a loosening that check-merge-ready does not classify as one: a shard finishing at 35 min now passes, and a hang holds a runner 10 min longer | answered, not a gate loosening. The limit is a resource ceiling, not a verdict. A mutation that runs out of budget is still CANNOT RUN, and the per-suite 600 s cap and 120 s headroom are unchanged, so each mutation is judged exactly as before. A longer limit makes MORE mutations reach a verdict. The hang cost is real, and the comment now states it |
| X2 | codex | Low | the comment treats a soft concurrency boundary (20 runners) as a full extra wave | fixed: the comment now says extra shards wait for a free slot, and that `verify`/`schema-gates` free theirs early |
| C1 | claude | Medium | subject `(backlog #754)` reads as closing the row, which this change does not | fixed: the PR title says "toward backlog #754", and row 754 gains a PARTLY ANSWERED note naming what stays open |
| C2 | claude | Low | comments still state 30 min / 1,680 s as the live PR budget | fixed where they describe the live budget (`ci.yml` schedule note, `check-plan-code.py` ceiling note). The dated ⟳ history notes and the self-test case NAMES are left alone: they record what was true, and the mutation manifests bind case names |
| C3 | claude | Low | "~1,330 s" is unsourced; master's cut predicts at most 1,133 s | fixed: the comment gives both figures (master 1,093-1,133 s, PR #651 1,314-1,335 s), says they are PREDICTED by `sweep_shard` + `shard_estimate`, and gives the ratio for each |

Round 2 goes to the Codex half, the one that raised X1, so it can accept or reject the answer.

```yaml
round: 1
fixes_nontrivial: false
subject: sweep-timeout-754
halves:
  codex: ran
  claude: ran
findings:
  - {id: X1, severity: Medium, aim: deliverable, fix_induced: false, component: sweep-limit, disposition: answered}
  - {id: X2, severity: Low, aim: deliverable, fix_induced: false, component: sweep-limit, disposition: fixed}
  - {id: C1, severity: Medium, aim: deliverable, fix_induced: false, component: backlog, disposition: fixed}
  - {id: C2, severity: Low, aim: deliverable, fix_induced: false, component: sweep-limit, disposition: fixed}
  - {id: C3, severity: Low, aim: deliverable, fix_induced: false, component: sweep-limit, disposition: fixed}
```

Reviews: `docs/reviews/codex/sweep-timeout-754-r1-codex.md`, `docs/reviews/claude/sweep-timeout-754-r1-claude.md`.
