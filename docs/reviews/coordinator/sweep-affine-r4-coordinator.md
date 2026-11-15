# Round 4 — `sweep-affine` (backlog #588, PR #590) — coordinator — ✅ CONVERGED (final-tree gate round)

```yaml
round: 4
fixes_nontrivial: false
subject: sweep-affine
halves:
  codex: ran
  claude: skipped
findings: []
```

REVIEW GAP: claude — alternation (round 4 runs one half; owner 2026-10-28).

**Why a round after STOPPED at r3.** `check-merge-ready` held the r3 head 13fddf33: five lines in `shard_refusal`
and its call were flagged as possible loosenings, and their r2 answers were recorded against an older
`scripts/check-plan-code.py`, so they did not count on this tree.

Codex reviewed head 13fddf33 (`docs/reviews/codex/sweep-affine-r4-codex.md`): no findings; 5,250 master-vs-branch
refusal comparisons (counts 0–24, totals 1–14, every valid index, cost and fallback partitions) all matched; the
direct-helper `IndexError` on an invalid index is unreachable because `parse_shard` refuses it first on both. All 5
flagged lines answered `not a loosening`. The round cap would have filed any non-BLOCKER finding; there were none.
