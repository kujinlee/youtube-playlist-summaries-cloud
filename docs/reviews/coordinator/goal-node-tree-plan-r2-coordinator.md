# Round 2 — `goal-node-tree-plan` — coordinator — ⟳ NOT CONVERGED (Codex half); 3 fixed, 0 rejected, 0 ESCALATE

```yaml
round: 2
fixes_nontrivial: true
subject: goal-node-tree-plan
halves:
  codex: ran
  claude: gap
findings:
  - {id: XM1, severity: Medium, aim: deliverable, fix_induced: true, component: ids, disposition: fixed}
  - {id: XM2, severity: Medium, aim: deliverable, fix_induced: true, component: batch-ci, disposition: fixed}
  - {id: Xm1, severity: Low, aim: deliverable, fix_induced: true, component: migration-slices, disposition: fixed}
```

REVIEW GAP: claude — alternation (round 2 is the Codex half; the Claude half reviews round 3)

Half: `docs/reviews/codex/goal-node-tree-plan-r2-codex.md` (2 Major, 1 Minor; reviewed head `e5f4bf96`).
Severity mapped Major → Medium, Minor → Low. All three are `fix_induced: true`: each sits on a round-1 fix
(XM5's bare ids, XM1's adopted `blocks` policy, CM3's parent diff).

Every finding was re-derived against the files at `e5f4bf96` before acting. No spec decision was changed, so
nothing is ESCALATE: the bare ids spec §3.5 requires are kept; the new refusal is on slug PAIRS the spec does
not mention.

## Findings

| id | Verified? — evidence | Action |
|---|---|---|
| XM1 | YES. Task 17's `second_ids` gives `/features` the ids `goal-s`, `s`, `f-s` and `goal-<was>`; slugs `x` and `f-x` both yield `f-x`, `x` and `goal-x` both yield `goal-x`, and a former `x` with a live `goal-x` likewise. Only chrome collisions were filtered. A PREFIX ban is impossible: the live node `goal-tree` begins with `goal-`. Checked at the base: no slug in `docs/features.md`, no `## GOAL` name in `docs/goal-threads.md`, no registry row in `docs/anchors.md`, and none of the slugs or `was:` entries Tasks 5 and 12 add, is `f-`/`goal-` plus another | FIXED in the grammar (lead's preferred option, since nothing live collides): Task 2 G6 gains behaviours 17–20 (three refused pair kinds; `goal-tree` without `tree` passes), a paragraph deriving the pairs from the ids each view emits, four cases (each refusal at two pairs), four mutations incl. pair-test → prefix-test, FAILS IF extended. Task 17 states G6 owns node-to-node collisions; Task 18 gains behaviour 9 / case `ids: no two nodes share an id`. C8 updated |
| XM2 | YES. `SECTION = re.compile(r"^#{1,2} ")`; `_homes` and so P4 read homes through it; `_union_violation` runs `postcondition` over clean merges too. So for `docs/features.md` a merged `###` above `####` nodes (clean when the two additions are separated by base lines) re-parents them with every clause green; and `resolve_hunk`'s `blocks` arm places theirs' headless prefix only before ours' first `SECTION` heading, so theirs' added field line lands under ours' added `####` with P4 green | FIXED by changing `batch-ci.py` (our script; the lead's ruling): a new policy `tree` — `blocks` resolution unchanged; postcondition P4 homes via `NODE_HEADING` (`^#{1,6} `) and a new clause P8 (every heading keeps its parent from the side it came from; one-sided re-parenting follows that side; both sides refused), pure `_parents`; prefix cut stays on `SECTION` with the argument why no verdict depends on a dropped line. Behaviours 8–12, five cases (two inputs each where a value is derived), six new mutations, `the policies:` case updated. C7, the File map row and Review Focus 4 rewritten. `blocks` and its two files untouched |
| Xm1 | YES. Task 5's table adds `cloud-publishing` and `serve-money-guard` and renames `harness-speed` → `dev-speed`, so the sorted-pairs diff necessarily carries `< harness-speed guard-and-gate-harness`; the condition "only dev-speed and three NEW nodes" could not be met. Task 12's allowed list also named `feature-map`/`goal-tree`/`work-lines` as changed, though their parent stays `status-visibility` | FIXED: Task 5 states the exact four `<`/`>` lines (diff piped through `grep '^[<>]'`), with removed / added / changed (none) spelled out. Task 12 states its exact diff: removed none, added the eight new nodes with their parents, changed only `status-visibility`, `explanation-on-demand` and the trunks' `###` children; the three `#####` moves print nothing; the expected lines are written to a file before Step 1 and diffed |

## Gates run on the folded plan

`check-docs.py`, `check-anchors.py`, `check-plan-file-tags.py`, `check-plan-task-order.py` (this plan: 22 tasks
produce, 22 consume, no forward references), `check-doc-citations.py --base origin/master` (after staging) and
`check-reference-namespace.py --base origin/master`: all exit 0.
