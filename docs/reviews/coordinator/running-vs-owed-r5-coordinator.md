# Round 5 — `running-vs-owed` — coordinator — CONVERGED (confirmation of the CI-found fix)

REVIEW GAP: claude — alternation, and weekly usage at 97% (stop 98.4%). Codex: `docs/reviews/codex/running-vs-owed-r5-codex.md`, on `b236146e`.

```yaml
round: 5
fixes_nontrivial: false
subject: running-vs-owed
halves:
  codex: ran
  claude: gap
findings: []
```

PR #512's CI shard 10 found a surviving mutation: round 3's `open_prs` line masked the older `open_pr` line in
`derive`. The two became one; three mutations re-bound. Codex confirmed the merged line names exactly the same PRs and
each re-bound mutation fails by name. Shard 2's red was the known thread-timing flake (backlog #506).
