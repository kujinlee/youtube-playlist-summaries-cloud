# Round 1 — `seed-stable-mutants` (part of backlog #506) — coordinator — CONVERGED

REVIEW GAP: claude — weekly usage 98% on the last day before the reset. Codex: `docs/reviews/codex/seed-stable-mutants-r1-codex.md`, on `3f0d8461`.

```yaml
round: 1
fixes_nontrivial: false
subject: seed-stable-mutants
halves:
  codex: ran
  claude: gap
findings: []
```

Codex measured the tied-name case killing its mutant at nine seeds (266, 312, 342, 449 among them) and the forced-order case
in 8 of 8 runs, and confirmed the patch is restored after an exception and does not leak into later cases.
