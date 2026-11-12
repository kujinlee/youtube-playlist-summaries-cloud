# Round 3 — `marketplace-plan` (the marketplace-inventory implementation plan, PR #562) — coordinator — NOT CONVERGED (Codex half), folded; review closed at the round cap

```yaml
round: 3
fixes_nontrivial: true
subject: marketplace-plan
halves:
  codex: ran
  claude: gap
findings:
  - {id: M1, severity: High, aim: deliverable, fix_induced: true, component: task-4-spike, disposition: fixed}
```

REVIEW GAP: claude — alternation

Plan at `e66e0626`; the Codex half (`docs/reviews/codex/marketplace-plan-r3-codex.md`) filed in `e6241662`:
0 BLOCKER, 1 MAJOR, 0 MINOR, **caused by the r2 fold** (M2's three-condition serve check). Severity map as r1:
MAJOR → High. Codex re-verified every r2 disposition (M1-M5, m1-m4) and found them holding, apart from the
regression below. The fold is deliberately NARROW: this is the last fold, and round 4 would only FILE.

**No `OWNER DECISION NEEDED`.** The fix routes a failure by whose server failed. It does not move the goal or
the spec: spec §4 already separates CANNOT RUN from a component failure, and the r2 fold had blurred that line.

## Findings

- **M1 (High, FIXED; Task 4 Step 3 (b), Step 5; Task 14 scripted half):** the r2 fold sent ANY failed
  ownership/sentinel condition to INCOMPLETE, an H7 wait. But when H7 holds (port free before start, the
  world's pidfile pid IS the listener) and the world's own server then fails, H7 cannot fix it: that is a
  measured component failure. **Codex's evidence**: a scratch copy with an injected `RuntimeError` in
  `index_html()`, with the port free before start, printed `serving <scratch HOME>/explainers`, its pid matched,
  and `GET /` gave `RemoteDisconnected`. The plan prescribed INCOMPLETE for this. Task 14 likewise labelled it
  CANNOT RUN.
  - **Fix:** a failed condition is now routed by WHOSE server failed.
    - **Isolation failure → INCOMPLETE (H7):** 7391 held before start (`--status` rc 0), start printing
      `already serving`, or a pidfile/listener pid mismatch.
    - **The world's verified own server failing → a recorded FAILURE of the component (the NO-GO route,
      H3):** start exiting non-zero on a port preflight confirmed free, or start printing
      `serving <world HOME>/explainers` with a pid match and then `GET /` erroring, non-200, or lacking the
      sentinel. The evidence (start's rc and stdout, both pids, the `GET /` error or body) goes in the record.
  - Step 5's NO-GO and INCOMPLETE clauses now name the same split.
  - Task 14's serve uses the same routing. An isolation failure is CANNOT RUN waiting on H7. The world's own
    server failing is a recorded component failure (a suite defect) with its evidence, never CANNOT RUN and
    never pass.
  - **FAILS IF:** a run in which the world's pidfile pid equals the listener's and `GET /` fails is recorded
    as INCOMPLETE or CANNOT RUN.
  - Nothing else in the plan changed.

## Thrashing — answered

**The arming condition is met.** Rounds 2 and 3 both carried findings caused by the previous round's fold, in
one component: `task-4-spike`.
- r2 M1 and M2 were caused by the r1 fold's serve and H7 text.
- r3 M1 was caused by the r2 fold's three-condition check.

That is the condition in `docs/review-method.md` → *The arming condition — full account*: *"two consecutive
rounds carry findings caused by the previous round's own fix, in one component"*.

**Disposition: no Phase 6 architecture review is convened for a plan document.** The same section says why:
*"on a document rounds can be right forever — go build, do not convene."* What thrashes here is prose about the
spike's routing (GO / INCOMPLETE / NO-GO). The routing's real test is not another reading of the prose. It is
the first thing exercised when Task 4 runs: the spike either installs and serves from the world, or it records
which server failed and why. The prediction this round refutes is the one logged at the r2 fold in
`docs/reviews/decision-scheme/decision-log.jsonl` ("no finding caused by the r2 fold in task-4-spike"). The
row appended at this fold records the closure.

**Backlog rows filed:** none.

Review closed at the round cap: round 4 would only FILE.
