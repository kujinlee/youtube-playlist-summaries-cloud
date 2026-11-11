---
name: review-rounds-capped-at-r3
description: "Owner decision 10-31 (card A) — review rounds are capped; both halves at r1, alternate r2-r3, from r4 FILE findings unless BLOCKER; Claude halves write verdict files"
metadata:
  node_type: memory
  type: feedback
  originSessionId: a6abe358-4c0b-44cb-a058-5446372998ef
  modified: 2026-11-01T04:00:13.800Z
---

Owner chose option A on 2026-10-31 14:5x after a 14-day measurement (273 rounds, 54 subjects):
round 1 found 58% of fixed Blocking/High, r1–r2 78%, r1–r3 83%; r4+ was 129 rounds for 17%, half
fix-induced. 31 rounds were Codex runs only to produce a verdict file (~7.4% of Codex weekly).
Halves overlap only ~25–35% on Blocking/High at r1, so both stay at r1.

The rule: both halves at r1; r2–r3 alternate one half; from r4 findings are FILED as backlog rows
unless one is a BLOCKER (an ordinary defect nothing else catches). The stop is pre-committed at r1.
A Claude half writes the same verdict file Codex does, so no Codex round runs only for
check-review-recorded.

**Why:** both the Claude and Codex budgets are finite (owner 10-31: Codex weekly 54% left), and the
round COUNT, not the model, drove the cost. Switching rounds to Claude only moves the cost to the
shared meter. PR #455 took 10 rounds; after r3 the findings were mostly hostile-sibling cases.

**How to apply:** state the r3 stop in every round-1 brief. At r4+, file rather than fold unless
BLOCKER. Check the Codex limit before each Codex run. Rule lives in docs/review-method.md once the
`review-round-cap` PR merges. Related: [[dual-review-what-it-catches]], [[cost-is-not-the-objective-improvement-is]].
