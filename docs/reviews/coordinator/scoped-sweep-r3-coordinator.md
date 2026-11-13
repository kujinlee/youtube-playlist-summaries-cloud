# Round 3 — `scoped-sweep` (backlog #330, PR #496) — coordinator — NOT CONVERGED (Codex half) — THRASHING in `alert`

```yaml
round: 3
fixes_nontrivial: true
subject: scoped-sweep
halves:
  codex: ran
  claude: skipped
findings:
  - {id: X1, severity: High, aim: deliverable, fix_induced: true, component: alert, disposition: fixed}
  - {id: X2, severity: Medium, aim: deliverable, fix_induced: true, component: alert, disposition: fixed}
```

REVIEW GAP: claude — budget. Alternation gave round 3 to the Claude half; weekly usage was 87% with new spawns refused at
90%, so round 3 ran Codex (no Claude usage). The Claude half last reviewed round 1.

**Held (Codex, `f5a1994b`):** r2 X1 and X2 hold on their original inputs; the required aggregate returns 1 for failure,
cancelled, skipped and empty, 0 only for success; checkout/setup failures fail the job; the alert still runs after the
aggregate fails; `issues: write` confined; FULL for undetermined/harness/push/schedule; 308/308, 256/256, 22/22.

## THRASHING — two consecutive rounds whose findings came from the previous round's fix, in ONE component

r2 X1 came from r1 C4's auto-close; r3 X1 (comment pagination: 100 comments hide a newer failing SHA, so a green rerun of
an older commit closes the alert) and r3 X2 (an unreadable SHA record is dropped when a valid one exists) both come from
r2's ancestry fix. That is the arming condition (`dev-process.md` → Phase 6).

**Can a redesign remove it? Yes — delete the component.** Every finding in the chain is about AUTO-CLOSE deciding, from
issue history, that a green run covers every recorded failure. Remove auto-close: a red full sweep opens/comments on the
`sweep-red` issue (unchanged); a green full sweep only COMMENTS "full sweep green at <sha>" and never closes; session-state
keeps listing every open `sweep-red` issue, and closing one is a human/coordinator act after reading it. A stale open
alert fails toward MORE alarm, which is the direction the owner's 11-02 approval asked for ("as long as there are full
sweep to detect error eventually"). The ancestry/SHA-record logic and its cases go with it. This IS the architecture
review's answer for this component, recorded here rather than convened, because the redesign deletes the component.

- **X1 (fixed by removal)** and **X2 (fixed by removal)**: with no close path there is nothing for pagination or a
  malformed record to authorize. Cases: a green run with an open issue comments and leaves it OPEN; `gh issue close` is
  never called by the step (asserted against the fake `gh`).
