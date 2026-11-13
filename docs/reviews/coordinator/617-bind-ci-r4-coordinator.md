# Round 4 — `617-bind-ci` (backlog #617 part 1) — coordinator — round-capped: 1 MAJOR FILED, no BLOCKER

REVIEW GAP: claude — alternation (round 4 is Codex's half; under the round cap its findings are FILED unless a BLOCKER).

```yaml
round: 4
fixes_nontrivial: false
subject: 617-bind-ci
halves:
  codex: ran
  claude: gap
findings:
  - {id: XM1, severity: Major, aim: deliverable, fix_induced: true, component: contract-parser, disposition: filed}
```

Codex on `ded10459` (52/52, 39/39 re-run by the reviewer). Flagged line `bc5e0abc80bf`: not a loosening.

- **XM1** (fold-induced: the r3 allow-list) `unset -v "${!SHARD_@}"` followed by `: "${SHARD_INDEX=38}"` makes every
  shard write `shard-38.txt` while the contract says ok. `ded10459^` refused it. FILED into backlog #629, the Phase 6
  review this round's thrashing already armed. Not a BLOCKER: the drift needs a deliberately obscure edit to `ci.yml`,
  and `read_flaky`'s missing-file red still reports `shard-0.txt` missing as NOT RUN on the first master sweep.

The change still beats master. Master has no contract at all, so every drift the contract catches is new protection.
The review is closed at the cap; the design question belongs to Phase 6 (#629).
