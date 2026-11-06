# Round 1 — `last-night-spend` (backlog #523) — coordinator — CONVERGED

REVIEW GAP: claude — weekly usage 99% on the last night before the reset. Codex: `docs/reviews/codex/last-night-spend-r1-codex.md`, on `cdb2c3d8`.

```yaml
round: 1
fixes_nontrivial: false
subject: last-night-spend
halves:
  codex: ran
  claude: gap
findings: []
```

Codex ran 2,205 boundary, DST and reset-hour combinations (early-morning and 10:00 resets among them): the spawn and wake hooks
allow below 100% on the last night and refuse at exactly 100%; no last-night message keeps "fit the room" or "under the stop";
each of the 4 new cases fails under a deliberate regression.
