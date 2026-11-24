# Round 3 — `goal-node-tree-plan` — Claude half

Reviewed head: `b14eee81` (branch `goal-node-tree-plan`, PR #630). Plan
`docs/superpowers/plans/2026-11-24-goal-node-tree.md`; spec decisions not reopened.
Mandate: try to REFUTE the r2 fold (G6 slug pairs, the `tree` batch-ci policy with P8, the exact parent diffs),
task order across all 22 tasks, and whether any named case cannot fail.

## What was checked and held

- **G6 slug pairs against live data (Task 2, behaviours 17–20).** Live slugs (`grep '^#' docs/features.md`):
  none begins `f-`; the only `goal-`-prefixed slug is `goal-tree`, and no slug or planned `was:` entry is `tree`.
  `## GOAL` names in `docs/goal-threads.md` (`guard-harness-audit`, `comprehensibility-suite`, `compaction-guards`,
  `dashboard-decisions`, `token-usage-first`, `dev-speed-first`, `product`, `memory-hygiene`,
  `harness-ships-elsewhere`) and the slugs/`was:` entries Tasks 5 and 12 add (`cloud-publishing`,
  `serve-money-guard`, `dev-speed`, `harness-speed`, `product`, `platform`, `dev-infrastructure`, `token-usage`,
  `memory-recall`, `memory-hygiene`, `comprehensibility-suite`, `dashboard-decisions`, `guard-harness-audit`,
  `compaction-guards`) form no `x`/`f-x`, `x`/`goal-x` or former-`x`/`goal-x` pair. Nothing live trips it.
  The pair enumeration is complete: over `/features` ids `{goal-s, s, f-s, goal-w…}` every cross-node equality
  is one of 17–19, behaviour 6 (former = current) or behaviour 7 (a former slug on two nodes); `f-…` vs `goal-…`
  can never meet. On `/goals` (`goal-s`, `g-s` from `page_markup.goal_id`, `goal-w`) no pair can meet.
- **Task 16 buildability against `scripts/batch-ci.py`.** Traced `resolve_hunk`'s `blocks` arm for the `tree`
  inputs: a `###`/`####` addition never starts with `"## "`, so theirs' whole addition is the "headless prefix",
  and `at` (first `SECTION` line of ours) is `len(to)` when ours adds only `###`/`####` — so the result is
  ours-then-theirs. That reproduces behaviour 9 forward (`a2` after `B`, P8 ejects) and reversed (`[]`), and
  behaviour 12 (`adrs: 0003` lands after ours' `#### o`; P4 under `NODE_HEADING` names it, under `SECTION` both
  homes are the `##` trunk so `blocks` returns `[]`). Behaviours 8, 10, 11 traced through the P4-style
  "exactly one side changed" rule with `_parents` = nearest preceding heading with fewer `#`: the stated verdicts
  hold. The prefix-cut argument holds: walking back from any heading after the cut, the `##` at the cut is
  reached before anything dropped. `_blob` returns `""` for a file a rev lacks, so the existing real-git cases
  (repos with no `docs/features.md`) skip the new entry (`o == b`). Behaviour 8's `git merge-file` runs inside
  the suite's existing `fixture_git.isolated()` (`_self_test`), as the PC15–PC17 real-git cases already do.
  No existing mutation in `scripts/mutations/batch-ci.json` anchors to a line Task 16 rewrites
  (`if policy == "blocks":`, `_homes`' `SECTION.match`, the cut); the C4 anchor
  `"docs/goal-threads.md": "blocks",` survives an inserted dict line.
- **Task 5 parent diff, re-derived.** Current tree: 35 nodes, 35 `state:` lines; `harness-speed` is a `####`
  under `guard-and-gate-harness`. Moving it to a `###` after `guard-soundness` and renaming gives exactly
  `< harness-speed guard-and-gate-harness`, `> dev-speed None` (slugless trunk), and the two `####` additions —
  the four lines the plan states.
- **Task 12 parent diff, re-derived.** 37 nodes + 8 new = 45; 34 `state:` lines = 45 − 11 stateless. ADDED: the
  3 trunks (`None`), `token-usage`/`memory-recall`/`comprehensibility-suite` (`dev-infrastructure`),
  `memory-hygiene memory-recall`, `dashboard-decisions status-visibility`. CHANGED: the 18 `###` under the three
  trunks (6 each, `dev-speed` among DEV INFRASTRUCTURE's) `None` → trunk slug, and `status-visibility`,
  `explanation-on-demand` → `comprehensibility-suite`. UNCHANGED: `feature-map`, `goal-tree`, `work-lines`
  (still `status-visibility`). `explanation-on-demand` has no children, so the insertion above
  `status-visibility` adopts exactly the run the plan names. Matches the paragraph.
- **Order.** The r2 additions consume only earlier artefacts: Task 18's `ids: no two nodes share an id` uses G6
  (Task 2) and `check-page-links.py:duplicate_ids` (exists, line 332). No CI step in `.github/workflows/ci.yml`
  newly runs at a commit before its producer. `batch-ci.py --self-test` is reached through the sweep and
  `check-selftest-counts.py`, both covered by W1–W6.

## Findings

### F1 — Low — Task 16: the both-sides mutation survives a clause-only assertion
`tree P8: both sides re-parenting one node is refused` is named as the case that reddens "P8's both-sides
refusal severed". Severing it in the P4 shape (drop the `if ho != h0 and ht != h0: …; continue`) leaves
`expect = ours' parent (B)`; the result's parent of `a1` is `C` (A, B, C, a1), so P8 still fires — with the
OTHER message, `P8 a node's parent changed and neither side made that change`. If the case asserts
`clauses(got) == ["P8"]` (the suite's usual form, `clauses` in `_self_test_body`), the mutation survives. Fix:
state that the case asserts the reason text (`named(got, "P8", "both sides")`), not the clause id alone.

### F2 — Low — Task 16 Step 2: "every `tree P…` case fails" is false for the negative controls
Behaviour 10 (`a tree P8: a one-sided re-parenting survives`, expected `[]`) goes straight to `postcondition`
(a clean merge, no `resolve_text`), and today's `postcondition` treats an unknown policy as `blocks`
(only `policy == "rows"` branches): `SECTION` homes give `[]`, so the case is GREEN before Step 3. Likewise the
second inputs of behaviours 8 and 9. A builder told every new case is red will hunt a non-existent defect.
Fix: say these controls are green before implementation and are killed by their mutations instead (the
"base parent always" mutation does redden behaviour 10).

### F3 — Low — Task 16: the `the policies: …` case's label is a mutation's `expect`
The C4 mutation `"C4: the goal threads are unioned as records"` expects the case label
`the policies: rows for the backlog, blocks for the entries and goal threads, records for the decision log`.
Step 1 says the case "gains `("docs/features.md", "tree")`" but not whether its label changes; rewording it to
mention `tree` unbinds the C4 mutation. W1–W6 would surface it, so Low. Fix: say "keep the label, or update the
C4 `expect` with it".

### F4 — Low — Task 18: `ids: no two nodes share an id` cannot fail for the property it names
Its tree (`x`, `fx`, `goal-tree`, `a was: y`) holds no colliding pair by construction, so no node-to-node
duplicate can arise from it whatever `second_ids` does about collisions; it fails only if one node's own ids
duplicate. No mutation is listed for it. Either rename it to what it witnesses (near-miss slugs produce
distinct ids) or name a mutation that reddens it (e.g. `second_ids` emitting the bare id with the `f-` prefix
stripped from the slug).

### F5 — Low — Task 5: the parent diff's left side is a moving `origin/master`
`diff <(git show origin/master:docs/features.md | pairs …)` is exact only while master's `docs/features.md`
equals the slice's base. Any PR touching the tree between the cut and Task 5's check (the `features-tree`
work is live) adds lines and fails "EXACTLY these four". Fix: read the left side at
`$(git merge-base HEAD origin/master)`, which Task 12's "save the pairs before Step 1" already effectively does.

### F6 — Low (prose) — Task 2 vs Task 17: `/goal-tree`'s ids stated two ways
Task 2's r2 paragraph says "`/goals` and `/goal-tree` give `goal-s`, `g-s` and `goal-<w>`"; Task 17's
`second_ids` returns "none on `/goal-tree`" (only former slugs). No collision depends on it; align the sentence.

No BLOCKER and no Medium: every slice is buildable as written and no CI step goes red at a task's commit by
the traces above.

VERDICT: CONVERGED
