# Round 3 — `goal-tree-superseded` (PR #480, backlog #484) — coordinator — NOT CONVERGED (Claude half); no BLOCKER, findings FILED under the round cap

Claude half: `docs/reviews/claude/goal-tree-superseded-r3-claude.md`, which reviewed `c6e84c07`.
REVIEW GAP: codex — alternation (rounds 2+ run ONE half per round, `docs/review-method.md` → *Round topology*).

```yaml
round: 3
fixes_nontrivial: false
subject: goal-tree-superseded
halves:
  codex: skipped
  claude: ran
findings:
  - {id: C3-M1, severity: Medium, aim: deliverable, fix_induced: true, component: fate-read, disposition: filed}
  - {id: C3-L1, severity: Low, aim: deliverable, fix_induced: false, component: fate-read, disposition: filed}
  - {id: C3-L2, severity: Low, aim: deliverable, fix_induced: true, component: fate-read, disposition: filed}
  - {id: C3-L3, severity: Low, aim: deliverable, fix_induced: true, component: fate-read, disposition: filed}
  - {id: C3-L4, severity: Low, aim: deliverable, fix_induced: true, component: fate-read, disposition: filed}
  - {id: C3-L5.1, severity: Low, aim: deliverable, fix_induced: true, component: docs, disposition: fixed}
  - {id: C3-L5.2, severity: Low, aim: deliverable, fix_induced: true, component: docs, disposition: filed}
```

No BLOCKER. Every finding fails back toward the old behaviour (a ✅ or an earlier pointer); none makes a leaf
CANNOT RUN wrongly or crash, and none is reachable on today's backlog. The fated set is unchanged
(124, 125, 127, 189, 213, 405 → backlog #481).

**Why filed, not fixed.** This is the last round in which findings are fixed. A code change after it would need a
fourth round, where only a BLOCKER is fixed. C3-L3's one-case fix is code, so it is filed too, and so is
everything else touching `scripts/goal-tree.py`. All are in **backlog #485** with the review's inputs.

**C3-L5.1 — fixed (docs only).** This PR's technical dashboard paragraph described the r0 design: the
"(method refuted, goal moved)" suffix, any-WITHDRAWN matching, and 176 cases / 83 mutations. It now describes
the shipped design and its counts.
