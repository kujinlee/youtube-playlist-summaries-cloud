# Round 7 — `plan-leak-guard` (PR #443) — coordinator — NOT CONVERGED; route ACCRETE

REVIEW GAP: codex — alternation; one reviewer per round in rounds 2+, the owner's 2026-10-28 answer to backlog #339.

```yaml
round: 7
fixes_nontrivial: true
subject: plan-leak-guard
halves:
  claude: ran
  codex: "GAP: alternation, one reviewer per round in rounds 2+ (backlog #339)"
findings:
  - id: M1
    severity: Medium
    aim: deliverable
    disposition: fixed
    fix_induced: true
  - id: L1
    severity: Low
    aim: deliverable
    disposition: fixed
    fix_induced: true
  - id: L2
    severity: Low
    aim: deliverable
    disposition: fixed
    fix_induced: true
```

Claude reviewed the wall-clock deadline added to the live reconcile in `scripts/check-main-drivable.py` (head `c528f6f2`). The core claim held: on the CI Python the memo-key mutant becomes a named red case in 47.9 s, the deadline never fires on the healthy tree, and no existing mutation attribution weakens. Three gaps remained, all caused by the previous fold.

**Route: ACCRETE.** Each finding is a missing assertion or a missing catch beside the code the last fold added. Nothing in the design moves.

**Fold, each shown red before its fix:**
- **M1** (Minor in the review's own wording; Medium in the YAML scale): `live_reconcile` records the deadline it armed, and a case pins it to `LIVE_DEADLINE_S`. Red first: the case saw `None`. Two new mutation entries on the call site, the call passing `100000` and the call reverted to an undeadlined `assess`; each goes red via that case only.
- **L1:** `with_deadline` restores the handler in an OUTER `finally`, and `live_reconcile` catches `DeadlineExceeded` as a timeout. The late alarm is made deterministic by raising from the disarm call itself. Red first: the case saw `ESCAPED`. One mutation entry deletes the catch.
- **L2:** one case asserts `signal.getsignal(SIGALRM)` is the prior handler after a normal, a timed-out and a late-alarm reconcile. One mutation entry deletes the restore.

Self-test 452 to 455; `EXPECTED_MUTATIONS` for `check-main-drivable.py` 197 to 201. Each of the four new mutants was applied by hand and the suite run: rc 1, exactly the one named case red, no crash.
