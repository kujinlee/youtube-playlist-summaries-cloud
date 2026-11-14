# Round 4 — `correction-spend-on-failure` — coordinator — ✅ CONVERGED (both halves; 2 Low)

```yaml
round: 4
fixes_nontrivial: false
subject: correction-spend-on-failure
halves:
  codex: ran
  claude: ran
findings: [overcount-understated, meter-optional]
```

Both halves CONVERGED over `f67683b9`. Codex: every dispatched attempt metered exactly once, retries bounded
(≤ 9¢), real-SDK suites green, integration 23/23, schema gates 15/15. Claude: the live 0028 confirmed from the
catalog (SECURITY DEFINER, `search_path` pinned, anon EXECUTE false); a rolled-back probe shows 0028 reads the
row and UTC day 0026 writes; the 3-second record bounds fit the route's `maxDuration` budget.

Dispositions (§Q3): F1 Low (a comment and the dashboard said the accepted over-count "only spends the owner's
allowance sooner"; it also feeds the GLOBAL `spend_ledger`) — FIX, wording only. F2 Low (`meter` optional on
`fixSummary`) — a contract change, FILED as backlog #346. The decision ladder is exhausted, so the unit closes
at round 4 and `check-decision-scheme` warns (trigger 11): the F1 fold is verified by `tsc` and the docs gates,
not a fifth round.

⛔ MERGE HELD FOR THE OWNER: migration 0028 must be applied to production BEFORE this code deploys (deployed
alone, the route fails closed and refuses every correction), and merging puts master ahead of production's
schema, which the nightly `prod-drift` would report.
