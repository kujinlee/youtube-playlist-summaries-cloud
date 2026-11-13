# Round 1 — `use-it-or-lose-it` — coordinator — 2 × P2: one FIXED, one answered by a shared definition

REVIEW GAP: claude — weekly usage 98%, last day before the reset. Codex: `docs/reviews/codex/use-it-or-lose-it-r1-codex.md`, on `e77279c7`.

```yaml
round: 1
fixes_nontrivial: true
subject: use-it-or-lose-it
halves:
  codex: ran
  claude: gap
findings:
  - {id: P2a, severity: Medium, aim: deliverable, fix_induced: false, component: usage-pace-message, disposition: fixed}
  - {id: P2b, severity: Medium, aim: deliverable, fix_induced: false, component: usage-pace-message, disposition: fixed}
```

- P2a "0% left": a positive room under 0.1 reads "<0.1%". Case + mutation.
- P2b DST: USE IT used `local_midnight(resets − 86400)`, as `cap_at` does — whose spring-forward behaviour backlog #510 r1
  Codex M1 already RULED on, with a case. Not re-litigated: both now read ONE helper, `rise_start`, so USE IT starts at
  exactly the instant the stop starts rising, on every calendar. Case (a minute either side, both) + mutation.
- Checks: a re-bound mutation repeated another's anchor, and the docstring count drifted — both mine, both fixed.
