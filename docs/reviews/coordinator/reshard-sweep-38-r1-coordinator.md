# Round 1 — `reshard-sweep-38` — coordinator

```yaml
round: 1
fixes_nontrivial: false
subject: reshard-sweep-38
halves:
  codex: ran
  claude: ran
findings:
  - {id: R1-X-F1, severity: Low, aim: deliverable, fix_induced: false, component: sweep-sharding, disposition: fixed}
  - {id: R1-X-F2, severity: Low, aim: deliverable, fix_induced: false, component: sweep-sharding, disposition: fixed}
  - {id: R1-C-F1, severity: Medium, aim: deliverable, fix_induced: false, component: sweep-sharding, disposition: fixed}
  - {id: R1-C-F2, severity: Medium, aim: deliverable, fix_induced: false, component: sweep-sharding, disposition: fixed}
  - {id: R1-C-F3, severity: Low, aim: deliverable, fix_induced: false, component: sweep-sharding, disposition: fixed}
  - {id: R1-C-F4, severity: Low, aim: deliverable, fix_induced: false, component: sweep-sharding, disposition: fixed}
  - {id: R1-C-F5, severity: Low, aim: deliverable, fix_induced: false, component: sweep-sharding, disposition: fixed}
  - {id: R1-C-F6, severity: Low, aim: deliverable, fix_induced: false, component: sweep-sharding, disposition: fixed}
```

Claude half: `docs/reviews/claude/reshard-sweep-38-r1-claude.md`, on `b619b8f0`, CONVERGED (no Blocker or High; 2 Medium, 4 Low).
Codex half: `docs/reviews/codex/reshard-sweep-38-r1-codex.md`, on `b619b8f0`, NOT CONVERGED (2 Low only).

**Fold.** The change itself (the matrix 24 -> 38) was found sound by both halves; every finding is about the decision
record's wording or a figure in it. The fold edits only the `ci.yml` record comment, backlog #231's dated note and the
branch's `## 2026-11-09` dashboard entry, plus one new backlog row. No code, no workflow logic.

| Finding | Disposition |
|---|---|
| Codex F1 / Claude F5 (the two-wave claim) | Fixed. Jobs counted: 38 shards + `verify` + `schema-gates` = 40 compete; `mutation-sweep-complete` runs after. Slots free one at a time and the 20 are shared, so 38 against 40 is a soft choice, not a cliff. |
| Codex F2 / Claude F3 (baseline figures) | Fixed. Model 1,446.6 s; measured 1,450.75 s, as `completedAt - startedAt` over the 24 shards of run 42625034608; the check is stated as in-sample. |
| Claude F1 (flake exposure) | Fixed. Control-suite runs rise ~1.37x (1,620 -> 2,218 target-shard pairs), so the exposure of the after-control check rises too. |
| Claude F2 (lifespan; reverses 11-07) | Fixed. ~200 entries a day; the 1,500 s line returns after ~25% more work, ~5-6 days, PREDICTED. Stated as RELIEF while master is red that reverses the 11-07 note; the structural lever is the new backlog #588. |
| Claude F4 (a measurement exists before merge) | Fixed. PR #550's own run 42660040212 sweeps the full manifest at N=38 and is the first measurement. Its result is not yet read; round 2 or the merge reads it. |
| Claude F6 ("REOPEN" on an open row) | Fixed. Now "close only after two consecutive master runs with every shard under 1,500 s"; the caveat that 1,683 s was cut short by the budget stop is restored. |

**New row.** Backlog #588: the per-shard control floor (~470 s) does not divide by N, so raising N buys days; proposals are
target-affine sharding, reusing the control across seeds, and backlog #565-style per-suite cuts.

**Verdict.** Claude half CONVERGED; Codex half NOT CONVERGED (LOW only). Not both halves converged, so round 2 runs.

**Round 2.** One half, Codex, scoped to the fold (the wording and figures above, and the new row).

REVIEW GAP: claude — alternation
