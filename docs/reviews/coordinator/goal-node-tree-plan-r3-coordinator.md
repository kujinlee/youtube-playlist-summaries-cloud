# Round 3 — `goal-node-tree-plan` — coordinator — CONVERGED (Claude half); 6 fixed, 0 rejected, 0 ESCALATE

```yaml
round: 3
fixes_nontrivial: false
subject: goal-node-tree-plan
halves:
  codex: gap
  claude: ran
findings:
  - {id: F1, severity: Low, aim: deliverable, fix_induced: true, component: batch-ci, disposition: fixed}
  - {id: F2, severity: Low, aim: deliverable, fix_induced: true, component: batch-ci, disposition: fixed}
  - {id: F3, severity: Low, aim: deliverable, fix_induced: true, component: batch-ci, disposition: fixed}
  - {id: F4, severity: Low, aim: deliverable, fix_induced: true, component: ids, disposition: fixed}
  - {id: F5, severity: Low, aim: deliverable, fix_induced: true, component: migration-slices, disposition: fixed}
  - {id: F6, severity: Low, aim: deliverable, fix_induced: true, component: ids, disposition: fixed}
```

REVIEW GAP: codex — alternation (round 3 is the Claude half)

Half: `docs/reviews/claude/goal-node-tree-plan-r3-claude.md` (verdict CONVERGED, six Low; reviewed head `b14eee81`).
Every finding was re-derived against the plan and the code at `b14eee81` before acting. No spec decision changed.

## Findings

| id | Verified? — evidence | Action |
|---|---|---|
| F1 | YES. `postcondition`'s P4 shape (`scripts/batch-ci.py`, `if ho != h0 and ht != h0: … continue`, then `expect = ho if ho != h0 else ht`): P8 copied in that shape, with the both-sides branch severed, falls to ours' parent and still emits a P8 — the other message. `clauses` (`_self_test_body`) returns only the id, so a clause-only assertion lets the mutation live | Task 16 Step 1: the both-sides case asserts `named(got, "P8", "both sides")`, with the reason why |
| F2 | YES. `postcondition` branches on the policy only at `if policy == "rows":` (P6), so `tree` is read as `blocks` today; behaviour 10 is a clean merge that never calls `resolve_text`, and `SECTION` homes give `[]` | Task 16 Step 2: names behaviour 10 as the one case green before Step 3, notes the `[]` second inputs of 8 and 9, and says these controls are proven by their mutations |
| F3 | YES. `scripts/mutations/batch-ci.json`, mutation `C4: the goal threads are unioned as records`, `expect` is exactly the label `the policies: rows for the backlog, blocks for the entries and goal threads, records for the decision log` | Task 16 Step 1: keep the label, or write the new one into that `expect` in the same commit |
| F4 | YES. Task 18's tree (`x`, `fx`, `goal-tree`, `a was: y`) holds no pair G6 refuses, and no mutation was listed. `gen-features-page.py` renders despite problems (a banner, `if problems:` in `render`), so a colliding tree yields a page with real duplicates | Task 18 behaviour 9 and the Task 17 paragraph: the case takes two trees — the near-miss one, and one with `x`/`f-x` and `a was: y`/`goal-y`; it asserts every duplicate `duplicate_ids` finds is a pair `slug_problems` names. Two mutations: G6's `f-` pair dropped, G6's `goal-` + former pair dropped |
| F5 | YES. Task 5's diff read `git show origin/master:docs/features.md`; Task 12's save named no rev | Both read the left side at `git merge-base HEAD origin/master`, with the reason |
| F6 | YES. Task 2 said `/goal-tree` gives `g-s`; Task 17's `second_ids` returns no old id on `/goal-tree` | Task 2's sentence now matches Task 17: `/goal-tree` gives `goal-s` and `goal-<w>` |
