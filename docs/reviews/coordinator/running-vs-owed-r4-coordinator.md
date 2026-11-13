# Round 4 — `running-vs-owed` — coordinator — capped; Medium + Low FILED (backlog #518)

REVIEW GAP: claude — alternation, and weekly usage at 97% (stop 98.4%). Codex: `docs/reviews/codex/running-vs-owed-r4-codex.md`, on `7a365f17`.

```yaml
round: 4
fixes_nontrivial: false
subject: running-vs-owed
halves:
  codex: ran
  claude: gap
findings:
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: false, component: derive-thread, disposition: filed}
  - {id: L1, severity: Low, aim: test, fix_induced: false, component: agenda-digest, disposition: filed}
```

The round cap (§0 Q4c): from round 4 a finding is FILED unless it is a BLOCKER. Neither is: both are rare thread
shapes (a mixed merged/open thread; an entry joining three PR identities), and the cost is a label on the page —
an open PR shown as running when its thread declared a wait — never lost data. Filed as backlog #518. Same theme as
every round: which open PRs a piece of work IS.
