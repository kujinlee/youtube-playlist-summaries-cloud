# Round 1 — `refresh-say-502` (backlog #502, PR #501) — coordinator — NOT CONVERGED (Codex)

```yaml
round: 1
fixes_nontrivial: true
subject: refresh-say-502
halves:
  codex: ran
  claude: gap
findings:
  - {id: X1, severity: Medium, aim: deliverable, fix_induced: false, component: scripts/explainer-serve.py, disposition: fixed}
  - {id: X2, severity: Low, aim: deliverable, fix_induced: false, component: docs, disposition: fixed}
```

REVIEW GAP: claude — budget (weekly usage 90% at 14:41, new agents refused at 94.6%; the Codex half does not draw on it).

- **X1 (Medium, FIXED):** the Refresh claim outranked `serverMsg`, and a claim never expires, so a hung or failed
  rebuild hid "server not responding" for as long as the page stayed open. Codex reproduced it under the real
  `RELOAD_JS`. Fixed by the order Codex proposed: `serverMsg || claim || staleMsg`. The node-run case gains a fifth
  world (server down, claimed, stale → "server not responding"), and a third explainer-serve mutation (claim above the
  outage) is killed by it.
- **X2 (Low, FIXED):** the goal-thread line and dashboard entry said "until the page reloads"; a failure or a warning
  replaces "rebuilding…". Both are qualified.
- Codex also noted a pre-existing race: the poller's own `location.reload()` on a rev change can fire before the POST
  answers, abandoning a warning. Not introduced or worsened by this diff; not filed (the warning path is rare and the
  reload shows the rebuilt page).
- During the fold, the two reload mutations' shared anchor was split into distinct anchors (a duplicate anchor put
  PR #500's CI red).

Fold head: `9e8d80cb`. Self-tests 233/233 and 234/234; all five #502 mutations killed by hand on a `git archive HEAD` copy.
