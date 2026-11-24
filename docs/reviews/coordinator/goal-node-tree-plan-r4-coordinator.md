# Round 4 — `goal-node-tree-plan` — coordinator — CONVERGED (Codex half); 1 fixed, 0 rejected, 0 ESCALATE

```yaml
round: 4
fixes_nontrivial: false
subject: goal-node-tree-plan
halves:
  codex: ran
  claude: gap
findings:
  - {id: XN1, severity: Low, aim: deliverable, fix_induced: true, component: batch-ci, disposition: fixed}
```

REVIEW GAP: claude — alternation (round 4 is the Codex half)

Half: `docs/reviews/codex/goal-node-tree-plan-r4-codex.md` (verdict CONVERGED, one Minor; reviewed head
`5b41004d`, the Phase 6 fold). Severity mapped Minor → Low. Round 4 is past the round cap
(`docs/review-method.md` §0 Q4c): a finding is FILED unless it is a BLOCKER. This one is not a blocker; it is a
one-sentence clarification of the plan's own Task 16, so it was FIXED in the plan rather than filed — the fix is
smaller than a backlog row, and a row would leave Task 16 ambiguous for its builder. No spec decision changed.

`fix_induced: true`: Task 16's step 1 ("the result reports a problem → eject") was written by the Phase 6 fold,
and the gap is in what that sentence left out.

## Findings

| id | Verified? — evidence | Action |
|---|---|---|
| XN1 | YES. Task 16, `postcondition(…, "tree")` step 1 names a problem in `_tree_map` of the RESULT only; `_tree_map` also returns problems for base, ours and theirs, and step 2 compares those maps with nothing saying what a partly-read input means | FIXED (the coordinator's choice: **eject**, not `CannotRun`). Step 1 now says a problem in the map of base, ours or theirs → `P8 the <side> tree does not parse: <problem>`, an ejection. Why eject: it is consistent with P8's "result refused ejects" — a refused line is data no attribute holds, so its placement cannot be judged, in an input exactly as in the result — and `CannotRun` stays reserved for the instrument failing (`_features()` raises), not for a text it reads. Behaviour 13 gains a third input (the BASE holds the refused line and ours deletes it, so the result parses — the case asserts `named(got, "P8", "base tree does not parse")`, since P3 also fires on the deleted line); Step 1's case description says so |

## The round cap: thrashing or prose floor?

**Prose floor.** The thrashing this subject carried (component `batch-ci`, fix-induced in r2 and r3) was
answered by the Phase 6 review `docs/reviews/coordinator/architecture-review-2026-11-24-batch-ci-tree.md`,
which ran on it: real thrashing, because the r2 fix built a second reader of the node grammar inside
`scripts/batch-ci.py`; it redesigned Task 16's judge to ask `parse_features` instead (P8, attribute by
attribute), and its §1 judged r3's three Low findings alone to be the floor. Round 4 reviewed that redesign and
found one Low: a missing sentence about inputs, not a defect of the mechanism — no reshaping removes the need to
say what an unparsable input means, and the fix touches no mechanism the redesign introduced. The trajectory
since the redesign is one Low on a CONVERGED verdict. Per-finding evidence: the table above.

`fix_induced: true` on a `batch-ci` finding makes `check-review-decision.py`'s `thrashing_component` read r3 and
r4 as consecutive fix-induced rounds in one component. That is the counter, not a new arming: the Phase 6 review
for this component is in this branch's range, and the r4 finding is the floor that review predicted.

## The decision log

`check-decision-scheme.py` trigger 1 named `goal-node-tree-plan` (≥2 rounds, no row). Two retroactive rows were
appended to `docs/reviews/decision-scheme/decision-log.jsonl` for the unit Task 16 / C7: `accrete` (the r1 fold's
adopted `blocks`, then the r2 fold's `tree` policy with its own heading reader; bet LOST at r3, `continued`) and
`redesign` (the Phase 6 judge through `parse_features`; bet WON at r4, `stopped`, `rounds_at_termination: 4`).
The check exits 0 with no FAIL.

## Gates run on the folded plan

`check-docs.py`, `check-anchors.py`, `check-plan-file-tags.py`, `check-plan-task-order.py`,
`check-review-rounds.py`, `check-doc-citations.py --base origin/master` (after staging) and
`check-reference-namespace.py --base origin/master`: all exit 0.
