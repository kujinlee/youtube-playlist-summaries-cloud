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

## Fold

Plan code extracted and run (`absorb_epoch`, `absorb_errors`, `held_by_archive`, `new_start_errors`, `decide_pr`,
`runs_from_listing`, `report_identity_ok`): every case below passes, the r2 regression scripts still pass, and the
reviewer's `reset.py` scenario now ends with an empty new epoch.

- **F1** — Task 7.3 (`held_by_archive`; `absorb_epoch`/`absorb_errors` take `archived` = BASE's `previous_epochs`;
  the epoch-change clause "What a reset clears, precisely"), Task 7.2 (`report()` omits held events), Task 8.1
  clause 9 text, Task 8.2 latch step (3); spec §2 *The ledger* and §8.6. Pinned by Task 7.3 "(r3 F1, the reviewer's
  `reset.py`)" (R11 → no event, HEAD carrying E refused; adjacent: unseen #610 miss latches, new target latches,
  sweep 91 re-blame held), Task 8.1 "(r3 F1)", Task 8.2 "(r3 F1, live loop)". ⚠ **Not the property above as
  worded:** "evidence counts only if its event happened at or after `start`" would absorb-and-drop an UNSEEN
  pre-reset miss (a report published after the reset PR's `verify`), which §8.6 lists as a failure and which
  loosens the latch, so that form was declined (STOP rule). The fold reaches the property's intent precisely: a
  reset clears exactly what it ARCHIVED. The reviewer's option (a) was declined too: it leaves the window between
  the reset PR's `verify` and its merge.
- **F2** — Task 7.3 `new_start_errors` (later than the old start, not before the newest absorbed `generated_at` in
  any epoch, not after today); spec §2. Pinned by Task 7.3 "(r3 F2, a backdated epoch start)".
- **F3** — Task 7.2 the attempt VIEW (own artifact, else the latest earlier attempt's), `no would-skip`,
  `decide_pr(pushes)` code. Pinned by Task 7.2 "(r3 F3, Re-run failed jobs)" and the `decide_pr` table cases.
- **F4** — Task 7.2 step 3 NO-REPORT STUB; Task 7.3 schema (`null` value) and `absorb_epoch`; spec §2. Pinned by
  Task 7.2 "(r3 F4, no-report attempts)" (zero calls once absorbed) and Task 7.3 "(r3 F4)". Same property as the
  coordinator's "goes to `skip`": an absorbed stub IS in `skip`.
- **F5** — Task 7.2 step 3 `report_identity_ok`, a mismatch RAISES. Pinned by Task 7.2 "(r3 F5, a body naming
  another run)".
- **F6** — Task 7.2 listing step 2 `--paginate --slurp` + `runs_from_listing` (chosen over `--jq`: one parse, and
  a dropped `--slurp` fails LOUDLY on `}{`). Pinned by Task 7.2 "(r3 F6, the real page shape)".
- **F7** — Global Constraints identity; spec §7 row (`shadow-report-<run_id>-<run_attempt>`); Task 7.3 cost
  restated as one re-absorb per PUSH whose `verify` follows an unseen schedule, `--absorb` before each push.
  Prose; checked by `check-docs.py`.

**Class search (evidence from before an epoch start counting in it), slices 6-8 and spec §2:** (1) an old-epoch
report absorbed after a reset → F1; (2) a backdated start → F2; (3) a post-reset sweep re-blaming a pre-reset PR →
`held_by_archive` by PR + targets (Task 8.2 live-loop case); (4) rows of a PR merged after `start` whose pushes ran
before it → bounded by `selector_blob` equality, not time; no change; (5) `q1_probe_delta` → only from `may_loosen`
reports of the active epoch; no change; (6) clause 9 reading a pre-reset unabsorbed report → closes only, cost
stated; (7) the absorb-gap clause after a reset reads `epoch.start`, sound given F2.
