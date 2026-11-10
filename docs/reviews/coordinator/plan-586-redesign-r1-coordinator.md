# Round 1 — `plan-586-redesign` (backlog #586 plan, after the owner's design D1) — coordinator — both halves NOT CONVERGED; folding

Both halves ran at `18d72977`, scoped to spec §2 and plan slices 6-8. The scope and the meaning of a BLOCKER are
`docs/reviews/architecture-review-2026-11-09-plan-586-ledger-trust.md` §8.

- Codex: `docs/reviews/codex/plan-586-redesign-r1-codex.md` — 2 BLOCKER, 1 MAJOR.
- Claude: `docs/reviews/claude/plan-586-redesign-r1-claude.md` — 1 BLOCKER, 4 MAJOR, 4 MINOR.

```yaml
round: 1
fixes_nontrivial: true
subject: plan-586-redesign
halves:
  claude: ran
  codex: ran
findings:
  - {id: X1, severity: High, aim: deliverable, fix_induced: false, component: ledger-trust, disposition: fixed}
  - {id: X2, severity: High, aim: deliverable, fix_induced: false, component: ledger-trust, disposition: fixed}
  - {id: X3, severity: Medium, aim: deliverable, fix_induced: false, component: ledger-trust, disposition: fixed}
  - {id: F3, severity: Medium, aim: deliverable, fix_induced: false, component: shadow-compare-workflow, disposition: fixed}
  - {id: F4, severity: Medium, aim: deliverable, fix_induced: false, component: shadow-compare-workflow, disposition: fixed}
  - {id: F5, severity: Medium, aim: deliverable, fix_induced: false, component: ledger-trust, disposition: fixed}
  - {id: F6, severity: Low, aim: deliverable, fix_induced: false, component: ledger-trust, disposition: fixed}
  - {id: F7, severity: Low, aim: deliverable, fix_induced: false, component: shadow-compare-workflow, disposition: fixed}
  - {id: F8, severity: Low, aim: deliverable, fix_induced: false, component: plan-text, disposition: fixed}
  - {id: F9, severity: Low, aim: deliverable, fix_induced: false, component: ledger-trust, disposition: fixed}
```

## The two halves agree on the two load-bearing findings

The halves found the same two defects independently, which is the strongest signal a round gives.

- **A miss can fall behind the watermark unabsorbed (X1 + X2 = Claude F1, BLOCKER per §8 rule 1).** Clause 9 reads
  only reports newer than `absorbed_through`. A report can land behind it in four ways:
  - a ledger PR advances only the watermark (Codex X1; the guard checks added content, never omitted content);
  - a report is uploaded late, after an honest absorb (Codex X2, Claude F1c);
  - absorb skips a report because the comparator or selector code changed (Claude F1a);
  - an `ABSORB CONFLICT` is hand-resolved toward the non-miss side (Claude F1b).

  **Root cause:** a timestamp watermark stands in for "this report was absorbed", and publication order is not
  generation order. **The fold:** the ledger records the IDENTITIES of the reports it absorbed. Clause 9 reads every
  unexpired trusted report whose identity is not absorbed, and refuses on any miss in one, regardless of
  timestamp. The guard rebuilds the absorb result from BASE plus the reports, compares it with HEAD, and refuses a
  ledger that drops tightening evidence.
- **A latched miss can never be cleared (Codex X3 = Claude F2, MAJOR).** Rows and events live outside `epoch`, so the
  owner's epoch reset (spec §7 Q5) either keeps them, and clause 4 refuses forever, or removes them, and the guard
  refuses. **The fold:** an archived epoch is a verbatim snapshot of its decisions and events. The guard validates
  the snapshot on reset, and the gate reads only the active epoch. Claude F5 (no row records which selector decided
  it) is the same repair's other half: an epoch names its selector, and a row from another selector does not count.

## The rest

- **F3:** the scheduled-run `if:` reads `github.event.repository`. Verify it against GitHub's documented `schedule`
  payload; if the claim holds, use an expression that does not depend on the payload. A self-test case must
  cover the scheduled run.
- **F4:** `list_reports` pages through every artifact in the repository. List the runs of `shadow-compare.yml`
  instead.
- **F6:** Q1 reads the NEWEST trusted report's `q1_probe_delta`.
- **F7:** spell out `verify`'s full `permissions:` block.
- **F8:** stale `reach_select.switch_gate` name and refusal list in the Global Constraints.
- **F9:** define which decisions count as decided.

Phase 6 is not armed. This is round 1 of a redesign, so no finding can be caused by a previous fold of this subject.
Round 2 runs ONE half (alternation): Codex.

## Fold

Every case below names a scenario that PASSED the r1 design. The ledger rule (`absorb_epoch`, `ledger_change_errors`,
clause 9, clause 5) was transcribed and run against 24 such scenarios before it was written into the plan; the
plan's `absorb_epoch` block was then extracted from the plan and re-run against the same 24 (all pass).

- **X1** (watermark-only advance): Task 7.3, the guard REBUILDS `absorb_epoch(BASE, new ids)` and requires HEAD to
  equal it; absorption is by identity (`epoch.absorbed_reports`). Case: *(X1, watermark-only)* HEAD advances only
  `absorbed_through` past a listed miss report → refused; *(X1, dropped evidence)* the report's id absorbed, its miss
  row omitted or turned `clean` → refused.
- **X2** (late upload across an absorb): Task 8.1 clause 9 reads every listed report whose `run_id` is not absorbed,
  whatever its `generated_at`; Task 7.2 `list_reports(skip=…)`. Case: *(X2, a late upload across an absorb)* R2
  (10:01) absorbed, R1 (10:00, a miss) listed afterwards → `unabsorbed miss`.
- **X3** (an epoch reset cannot clear a latch): Task 7.3 schema (rows, events, ids, Q1 inside `epoch`), the guard's
  epoch-change clause (old epoch appended verbatim, new epoch empty), Task 8.1 (active epoch only), Task 8.2 latch
  text. Case: *(X3, a reset from an actual latch)* in Task 7.3, and the Task 8.2 case starting from a latched
  post-switch event.
- **F3** (the `if:` skipped every scheduled run): Task 7.2 *The workflow*, a two-job design whose first job reads
  `default_branch` from the API under `bash -e`; no `if:` reads `github.event`. Case: *(F3, the scheduled run)* the
  `shadow-compare.yml` read refuses any `if:` containing `github.event.`, and the step against a fake `gh` writes
  `on_default=true` for `refs/heads/master`; merge gate: the FIRST SCHEDULED run uploads a report. GitHub's docs
  confirmed the claim (the `schedule` payload is "Not applicable"; the `workflow_dispatch` payload has no
  `repository` either).
- **F4** (`list_reports` paged every repository artifact): Task 7.2, runs of `shadow-compare.yml` only, one artifact
  lookup per unabsorbed run; Task 8.1, reports fetched only when clauses 1-7 pass. Cases: *(F4)* 150 runs, 140 in
  `skip` → exactly 1 + 2 + 2 × 10 calls and never `actions/artifacts`; a ledger refused at clause 5 →
  `fetch_reports` called zero times.
- **F5** (a row decided by the previous selector): Task 7.3 (each row carries `selector_blob`), Task 8.1 clause 5.
  Case: *(F5, a row decided by the previous selector)* 20 clean rows under blob X, epoch keyed to Y → `0 of 20`.
- **F6** (Q1 from any report): Task 7.3 (`q1_probe_delta` = `{value, generated_at}`, newest by `generated_at`, only
  from a report that `may_loosen`), Task 8.1 clause 6. Case: *(F6)* HEAD's Q1 4 from the older report when the newer
  says 7 → refused by the guard; the gate reads 7.
- **F7** (`verify` permissions): Global Constraints and Task 7.3, the whole block `{contents: read, actions: read}`.
  Case: *(F7)* the `ci.yml` read fails on a block holding `actions: read` alone.
- **F8** (stale name and refusal list): Global Constraints now name `reach_gate.switch_gate` and point to Task 8.1
  for the refusals, keeping no second copy of the list. Case: none is a test; `check-docs.py` and the class search
  below found no other `reach_select.switch_gate`.
- **F9** (`decided` undefined): Task 7.2 defines `DECIDED` (`pending` is never decided and never written). Cases:
  *(F9)* a report row `pending` → no row written, `inconclusive` → written; a PR decided `inconclusive` is absent
  from the next report.

**Beyond the dispositions.** Claude F1a and F1b, folded under X1/X2, change the absorb itself:
- **F1a.** A report from other code no longer gets `ABSORB SKIPPED` as a whole. Its misses and events are
  absorbed (`ABSORB MISSES ONLY`), because a miss only tightens.
- **F1b.** The r1 `ABSORB CONFLICT` refusal is REMOVED. Its only resolution was a hand edit that chose a side.
  The guard's rebuild now refuses every hand edit, and "a miss always wins" is the one resolution that never
  loosens. A hand-picked subset of the listed reports is refused by its own clause.

**Stated bound.** A miss can be lost only if no absorb runs for 76 days. The guard then refuses every absorb, so
the ledger cannot advance until the owner resets the epoch.

The YAML above is unchanged: every disposition held.
