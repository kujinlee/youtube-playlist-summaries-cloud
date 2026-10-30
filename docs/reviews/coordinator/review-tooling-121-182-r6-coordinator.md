# Round 6 — `review-tooling-121-182` (PR #439, backlog #121) — coordinator — the recorded final-tree round finds a REGRESSION against master

REVIEW GAP: claude — the rounds gate counts only Codex-verdict rounds; round 5 was the Claude half, so this Codex round is the recorded final-tree round (filed as a process finding).

```yaml
round: 6
fixes_nontrivial: true
subject: review-tooling-121-182
halves:
  codex: ran
  claude: "GAP: round 5 was the Claude half; this round exists because the rounds gate reads only Codex verdicts"
findings:
  - {id: X1, severity: High, aim: deliverable, fix_induced: true, component: out-path, disposition: fixed}
```

Codex reviewed `f7d2c932`, the exact merging tree.

**X1:** when `B/docs/reviews` is ALREADY a symlink to a directory outside the checkout, an `--out` through it passes the identity rule and overwrites a filed review. The DEFER fold deleted the comparison against the RESOLVED `docs/reviews` root. That comparison refuses this input on master and at `c9dcc13c`. So this is a regression against master, caused by this PR.

**Why it is folded although the route was DEFER.** DEFER files new findings so that a PR can close. It cannot ship a regression that master does not have. This is ONE minimal fold: keep the identity rule, and also refuse any destination inside either checkout's resolved `docs/reviews`, with the reviewer's static-symlink layout as a regression case. Then ONE Codex round scoped to that fold, whose further findings are filed. The decision log records it as a new unit, so `check-decision-scheme`'s ladder-restarted warning shows it rather than hiding it. The round-5 findings stay filed as backlog #400.
