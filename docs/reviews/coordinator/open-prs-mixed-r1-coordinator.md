# Round 1 — `open-prs-mixed` (backlog #518) — coordinator — CONVERGED

REVIEW GAP: claude — weekly usage 98% on the last day before the reset. Codex: `docs/reviews/codex/open-prs-mixed-r1-codex.md`, on `552df333`.

```yaml
round: 1
fixes_nontrivial: false
subject: open-prs-mixed
halves:
  codex: ran
  claude: gap
findings: []
```

No findings: fated rows stay out of title resolution, closed PRs are never collected, a finished leaf needs `open_prs` (a stale
ledger flag alone does not resurrect it), parked leaves stay excluded; Codex confirmed each new case fails when its clause is reverted.
