# Round 2 — `stop-rise-510` (PR #508, backlog #510) — coordinator — NOT CONVERGED (Codex half)

REVIEW GAP: claude — alternation, and weekly usage at 95% of the cap. Codex half:
`docs/reviews/codex/stop-rise-510-r2-codex.md`.

```yaml
round: 2
fixes_nontrivial: false
subject: stop-rise-510
halves:
  codex: ran
  claude: gap
findings:
  - {id: X1, severity: Low, aim: deliverable, fix_induced: true, component: stop-prose, disposition: fixed}
```

- **X1** — the message called a stop "rising" when the reserve bound it above 97 (a Sat 10:00 reset, Fri 18:00:
  reserve 97.92, rising cap 98.09). The note now names the reserve whenever `stop < cap_at(now, resets)`. Codex's case
  is added, with a mutation restoring the old `stop < STOP_CAP` test, which fails it (temp copy). The verdict was
  always right; only the explanation was wrong. Fix-induced: round 1's change added the rising branch.

Round 1's three folds verified by Codex. Its note on the memory file is addressed: `a-budget-stop-is-soft-with-a-reserve.md`
now separates the pace line (a guide) from the hard stop and its last-day rise. 312/312; pin 134.
