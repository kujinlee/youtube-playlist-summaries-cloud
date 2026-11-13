# Round 4 — `key-link` (PR #489, backlog #470) — coordinator — CONVERGED (Codex); final-tree check under the cap, and the thrashing-armed architecture review FILED as backlog #494

REVIEW GAP: claude — alternation. Round 4 runs ONE half; round 3 ran the Claude half.

Codex half: `docs/reviews/codex/key-link-r4-codex.md`, on `ac71e3f4`.

```yaml
round: 4
fixes_nontrivial: false
subject: key-link
halves:
  codex: ran
  claude: skipped
findings: []
```

**Codex CONVERGED, no findings.** `check-page-links --build` passed over all five pages (7,995 fragment links, 11
inline scripts); `--build --ci` passed on Python 3.12.9; its own property run found 0 failures over 19,334 inputs × 8
renderers, including real backlog, dashboard and goal-thread lines; its own parse5 differential found 0 disagreements
over 6,400 pages. `check-plan-code --self-test` 278/281, the three failures being the worktree's missing
`node_modules/typescript` (environment, not the PR).

**The architecture review** (Phase 6, armed by thrashing: r2 and r3 each carried fix-induced findings in
`page-reading`) is `docs/reviews/architecture-review-2026-11-03-key-link.md`. Verdict: thrashing, class "a writer that
depends on a reader reproducing a browser"; the removal is render-time linking, which the spec already describes and
the renderers already mostly do. No BLOCKER is open, so it is FILED as backlog #494 under the round cap
(`docs/review-method.md` §0 Q4c) rather than folded. Backlog #493 files the regen hooks' weak failure channel.

**Decision log.** The r2 SPLIT row is scored `continued` (r3's C-F3 is its failure observation), and a DEFER row
closes the unit at round 4 with r4's result as its observation. The loop terminates at round 4.
