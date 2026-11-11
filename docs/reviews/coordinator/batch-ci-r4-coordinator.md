# Round 4 — `batch-ci` (PR #529, backlog #534) — coordinator — Claude half CONVERGED; 3 findings FILED under the round cap

REVIEW GAP: codex — alternation (round 4 runs the Claude half)

```yaml
round: 4
fixes_nontrivial: false
subject: batch-ci
halves:
  claude: ran
  codex: gap
findings:
  - {id: R4-F1, severity: Low, aim: deliverable, fix_induced: false, component: union, disposition: filed}
  - {id: R4-F2, severity: Medium, aim: deliverable, fix_induced: false, component: union, disposition: filed}
  - {id: R4-F3, severity: Low, aim: deliverable, fix_induced: false, component: union, disposition: filed}
```

Claude (`docs/reviews/claude/batch-ci-r4-claude.md`, on `8fd71df9`) reviewed the Phase 6 redesign. CONVERGED: no
finding lets `land` merge a tree other than the one CI swept, or merge a HOLD PR. Under the round cap and the adopted
stop condition (a union finding is a BLOCKER only if the postcondition HOLDS on a wrong tree that can land), all three
are FILED: backlog 550 (R4-F1, line endings), 551 (R4-F2, an added section's position is unchecked by the pure
postcondition), 552 (R4-F3, the prefix cut changes no verdict).

**R4-F2 and the decision-log bet.** The bet reads "refuted if r4 shows the postcondition passing a wrong tree". The
reviewer showed the PURE function accepting a wrong placement, but could not produce that tree through `merge_into`:
six real-git merges placed theirs' section correctly, because git keeps theirs' insertion where theirs put it and the
`blocks` resolver only ever moves theirs' sections later. Read at the level of a tree that can land, the bet held; at
the level of the pure function it did not. The decision-log row records both, and backlog 551 closes the gap with a
P8 clause.

Fixture-free self-tests at the reviewed head: batch-ci 168/168, check-merge-ready 348/348; all 14 new mutations
applied by hand were red on their named cases. The review loop terminates here.
