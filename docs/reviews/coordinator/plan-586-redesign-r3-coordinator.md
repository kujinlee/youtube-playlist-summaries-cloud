# Round 3 — `plan-586-redesign` — coordinator — Claude NOT CONVERGED (no BLOCKER); folding, the cap round

REVIEW GAP: codex — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

Subject: the round-2 fold, `git diff 6d3e88ef 8a2fd165`, reviewed by Claude at head `cf19b684`,
`docs/reviews/claude/plan-586-redesign-r3-claude.md` (0 BLOCKER, 1 MAJOR, 6 MINOR).

```yaml
round: 3
fixes_nontrivial: true
subject: plan-586-redesign
halves:
  claude: ran
  codex: "GAP: alternation, one reviewer per round in rounds 2+ (backlog #339)"
findings:
  - {id: F1, severity: High, aim: deliverable, fix_induced: true, component: ledger-trust, disposition: fixed}
  - {id: F2, severity: Low, aim: deliverable, fix_induced: false, component: ledger-trust, disposition: fixed}
  - {id: F3, severity: Low, aim: deliverable, fix_induced: true, component: shadow-compare-workflow, disposition: fixed}
  - {id: F4, severity: Low, aim: deliverable, fix_induced: true, component: shadow-compare-workflow, disposition: fixed}
  - {id: F5, severity: Low, aim: deliverable, fix_induced: true, component: ledger-trust, disposition: fixed}
  - {id: F6, severity: Low, aim: deliverable, fix_induced: false, component: shadow-compare-workflow, disposition: fixed}
  - {id: F7, severity: Low, aim: deliverable, fix_induced: false, component: plan-text, disposition: fixed}
```

## Thrashing or prose floor? (the round-3 question, `docs/review-method.md` §0 Q4c)

**The arming shape is met, and the test says FIX.** Round 2 (C1) and round 3 (F1) both carry fold-caused findings
in `ledger-trust`, which is the arming condition. The stop condition's one test is *can a redesign remove it?*
- **F1:** the r2 fold's class-search rule sends an old-epoch report's events into the NEW epoch, so a reset
  re-closes itself. This is a missing rule about WHICH evidence an epoch counts, inside the D1 ledger shape. Any
  reshaping keeps the question "does evidence older than a reset count after it", and one clause answers it. It
  fails CLOSED (the switch stays shut, the sweep stays full), so it costs liveness, never correctness. That puts it
  on the *branch-coverage* row, not the *mechanism* row.
- **The r2 findings (C1, a subset absorb; C2, a status filter)** were the same kind: coverage of cases the identity
  design governs. Neither the halves nor this round found a way to open the switch on non-BASE input, which is the
  rule the Phase 6 review (`docs/reviews/architecture-review-2026-11-09-plan-586-ledger-trust.md` §8) made the shape.

So no second Phase 6 is convened, and the redesign is not re-litigated. **The decision-log bet held:** no §8 BLOCKER.

## The fold (the property first; the reviewer's suggested fix is a hypothesis)

- **F1 + F2, one property: a reset clears everything that happened before it.** Evidence counts in an epoch only
  if the EVENT it records happened at or after that epoch's `start`. That covers a post-switch event repeated by a
  daily report, and a miss generated before the reset, whenever the report is absorbed. `start` may not be earlier
  than the newest absorbed report's `generated_at` (F2: no backdating). The reviewer's alternative, refusing an
  epoch change while any listed report is unabsorbed, is acceptable if simpler, provided F2's repeat case is also
  closed. Cases: the reviewer's `reset.py` scenario, a backdated start, and the adjacent pass (an event after the
  reset still latches).
- **F3:** define `decide_pr` for clean CI runs mixed with `not a sample` attempts (a rerun without a selection
  artifact is skipped, never decisive either way), with a case.
- **F4:** a failed or cancelled attempt with no report goes to `skip` (it can never publish one later). Restate
  the call bound from the code, not from memory.
- **F5:** refuse a report whose body `run_id`/`run_attempt` differ from the run it was downloaded from.
- **F6:** `gh api --paginate --jq '.workflow_runs[]'`, and the fake `gh` emits the real multi-page shape.
- **F7:** fix Global Constraints line 68 and spec line 572 (identity is `<run_id>.<run_attempt>`). Restate the race
  cost as one re-absorb per branch update that crosses a schedule.

After round 3 the cap governs: a further round FILES anything that is not a BLOCKER.
