<!-- codex-review: model=gpt-5.5 -->

# Codex adversarial review — feature hub PLAN — round 3

## Verdict: FINDINGS

## Re-derivation of the six claims

1. **Final checker runs 24/24:** yes. I assembled `check-features.py` from the plan snippets in task order and got `24/24 self-test cases passed`, rc 0.
2. **`built` + `expected-because:` now fails:** yes. The new rule is in `docs/superpowers/plans/2026-09-19-feature-hub.md:259`, covered by the new case at `:146`, and the mutant kills through `a built node carrying expected-because fails`.
3. **All five mutation entries kill and attribute:** yes. I applied all five manifest edits over a green control; each anchor matched once and each mutant printed exactly its named `[FAIL]` case.
4. **Spec `absent` example and plan `dig-job-recovery` parse clean:** yes. Both produced zero `parse_features + check_nodes` problems.
5. **Post-swap task numbering is consistent:** no. See Finding 2.
6. **Unowned numbers:** not all gone. See Finding 3.

## Findings

### [High] 1 — Feature page staleness sources omit fragments the page is required to derive

**Evidence:** Task 4 requires `/features` to resolve backlog rows, ADRs/specs/plans, recent changes, and reviews at `docs/superpowers/plans/2026-09-19-feature-hub.md:603`. The spec’s fragment table likewise includes specs/plans, ADRs, backlog rows, review documents, and recent changes at `docs/superpowers/specs/2026-09-19-feature-hub-design.md:113`.

But Task 4 registers stale sources as only `docs/features.md`, `docs/anchors.md`, and `docs/backlog.md` at `docs/superpowers/plans/2026-09-19-feature-hub.md:624`, and Task 5 tells the hook to watch only those same three paths at `:649`.

**Introduced by an earlier round's fix?** No. This looks pre-existing; Task 4/5 just had not been attacked hard enough.

**Why it matters:** A spec, plan, ADR, or review can change while `/features` remains marked fresh and the hook stays silent. That violates the page’s core “derived, never hand-maintained” promise and the Task 5 title: “so the page cannot go quietly stale.”

**Fix:** Include every file family the renderer derives from in both `PAGE_SOURCES` and the hook case list: at minimum `docs/adr/*.md`, `docs/superpowers/specs/*.md`, `docs/superpowers/plans/*.md`, and `docs/reviews/**` if reviews are rendered. For `git log`, either document that commits require manual/CI regeneration or wire generation into a place that runs after commits.

### [Medium] 2 — Post-swap numbering still has stale references and a skipped step

**Evidence:** Task 1 says the minimal tree is “expanded in Task 2” at `docs/superpowers/plans/2026-09-19-feature-hub.md:56`, but the full tree is Task 3 at `:499`. The self-review says “Task 2’s tree contents” at `:790`, also wrong. Task 3 steps go Step 1, Step 2, Step 4, Step 5 at `:510`, `:519`, `:534`, `:541`.

**Introduced by an earlier round's fix?** Yes, by the Task 2/3 swap from round 2.

**Why it matters:** This does not break code execution, but it falsifies claim 5 and makes the plan’s own coverage map less reliable.

**Fix:** Change the two stale “Task 2” tree references to Task 3 and renumber Task 3’s steps to 1-4.

### [Low] 3 — More unowned numeric claims remain

**Evidence:** Task 1 Step 6 still expects `15/15` at `docs/superpowers/plans/2026-09-19-feature-hub.md:308`, but after the latest fold Task 1 has 16 cases and Step 4 correctly expects `16/16` at `:275`. The code-comment snippet still says “39 suites” at `:106`, despite the global prose deleting that number. The spec says “not 140 row edits” at `docs/superpowers/specs/2026-09-19-feature-hub-design.md:117`; I measured 142 backlog rows.

**Introduced by an earlier round's fix?** Yes for `15/15` and `39`; the `140` looks older.

**Why it matters:** Low operational risk, but this repo explicitly treats prose counts as drift-prone unless something owns them.

**Fix:** `15/15` → `16/16`; remove the `39` from the snippet comment; change `140` to “every backlog row” or the measured `142`.

## Does this round add any new Blocking or High? — yes

One new High: the stale-source/hook coverage gap for Task 4/5.

## Things I checked and found correct

The assembled checker runs `24/24`. The new `built` plus `expected-because:` rule is enforced. All five mutation anchors match exactly once and kill through the expected case. `EXPECTED_MUTATIONS` now uses `"scripts/check-features.py": 5`, matching the manifest target shape. The corrected spec absent example and plan `dig-job-recovery` example parse with zero problems. The real starter-tree run fails as expected, with 13 anchors and 21 backlog areas measured from the repo.

## What I could not run

Nothing is implemented in the checkout, so I could not run the real `scripts/check-features.py`, `scripts/gen-features-page.py`, the hook, CI, or end-to-end `check-plan-code.py --mutate .`. I ran extracted plan code in `/tmp/fh-r3` instead.
