# Round 1 — `reshard-18` (PR #484, backlog #415) — coordinator — CONVERGED (both halves); three Low prose findings fixed

Codex half: `docs/reviews/codex/reshard-18-r1-codex.md`. Claude half: `docs/reviews/claude/reshard-18-r1-claude.md`. Both reviewed `0b4f691a`.

```yaml
round: 1
fixes_nontrivial: false
subject: reshard-18
halves:
  codex: ran
  claude: ran
findings:
  - {id: L1, severity: Low, aim: deliverable, fix_induced: false, component: backlog-prose, disposition: fixed}
  - {id: L2, severity: Low, aim: deliverable, fix_induced: false, component: register-prose, disposition: fixed}
  - {id: L3, severity: Low, aim: deliverable, fix_induced: false, component: dashboard-prose, disposition: fixed}
```

**Both halves converge on the code.** Each checked the partition independently over all 3,313 manifest entries at N=18:
every entry is assigned exactly once, and no shard is empty. Both found that only the matrix list encodes N, and that
`mutation-sweep-complete` aggregates without encoding it. Both reproduced the measured figures: 1,194 s against 1,704 s
end to end, a slowest shard of 1,184 s, and 1.52x inside the timeout.

**L1 — fixed.** Backlog #231 repeated the refuted figure "35 jobs ran at once" (it counted cancelled jobs) and "26 jobs
per run". The row now states 20 jobs per PR run at 18 shards, and points to the refutation in `ci.yml` beside the matrix.

**L2 — fixed.** In optimization-register row 10, the body says 12 -> 24 -> 18 and Status names PR #484. The MEASURED
cell carries the paired pair, with run ids and slowest shards, in place of the stale 24-shard prediction.

**L3 — fixed.** The dashboard entry's first sentence is scoped to "when nothing else is running". The backlog #415
DONE cell now says the busy-queue case is NOT MEASURED: a lone PR run uses 20 of 20 slots, so any concurrent run queues
shards at either N.

**Self-test note.** Both halves saw 278/281 without `node_modules` and 281/281 with it (Claude, EXECUTED). The three
failures are the fresh checkout's missing `node_modules/typescript`, not this diff.
