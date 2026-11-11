# Round 2 — `spawn-line-500` (backlog #500, PR #500) — coordinator — CONVERGED (Codex)

```yaml
round: 2
fixes_nontrivial: false
subject: spawn-line-500
halves:
  codex: ran
  claude: gap
findings: []
```

REVIEW GAP: claude — alternation (rounds 2+ run ONE half; the Claude half ran r1).

Codex reviewed `b7716757`, which includes the r1 fold (`8b602d55..b7716757`), and found nothing new. It tried and failed
to refute X1's declined disposition: below 80% the stop is at least 90, so no verdict depends on the line. Measured by
the reviewer:
- 295/295 self-test cases pass;
- all 18 `#500` mutations, and four older ones (both re-anchored and two moved to 98.5%), are killed by their named
  cases;
- 5,000 randomized readings match the clamped formula;
- hostile meter content (including a 4 MiB log of tiny rows) gives no crash or hang, and 97% is always refused;
- HOME isolation, the skipped meter read and the threaded reason agree with the docs.

The full mutation sweep is CI's (draft PR #500).
