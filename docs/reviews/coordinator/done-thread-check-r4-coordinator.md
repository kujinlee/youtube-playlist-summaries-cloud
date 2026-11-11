# Round 4 — `done-thread-check` (backlog #507) — coordinator — CONVERGED

REVIEW GAP: claude — weekly usage 99% on the last night before the reset. Codex: `docs/reviews/codex/done-thread-check-r4-codex.md`, on `30939f90`.

```yaml
round: 4
fixes_nontrivial: false
subject: done-thread-check
halves:
  codex: ran
  claude: gap
findings: []
```

The capped round (BLOCKERs only) confirmed round 3's fixes: `--done` checks the entry it removes; untracked threads warn, tracked
ones are silent, and an unreadable or malformed threads file is NOT CHECKED. 127 cases.
