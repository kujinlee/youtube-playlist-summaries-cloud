<!-- codex-review: model=gpt-5.5 -->

# Codex adversarial review — feature hub PLAN — round 2

## Verdict: FINDINGS

## Re-derivation of the nine claims

1. **Matched.** I assembled the final `check-features.py` from the plan snippets and ran `--self-test`: output was `23/23 self-test cases passed`, rc 0.

2. **Matched.** A real mutant of the built-node fragment rule produced:
   `  [FAIL] a built node with no fragment fails: got False want True`
   and `scripts/check-plan-code.py` `parse_fail_names(...)` returned `['a built node with no fragment fails']`.

3. **Matched.** All four CANNOT-RUN probes returned rc 2: missing `features.md`; no nodes; no anchors parsed; no backlog areas parsed.

4. **Matched.** `CELL_SPLIT` recovers backlog `#90 -> {'(comprehensibility)'}` and `#110 -> {'(tooling)'}`. The total area set did **not** change: escaped splitter and naive splitter both returned 21 distinct area names in today’s backlog.

5. **Matched.** The wrapped `for:` fixture is refused via a parse problem containing `neither a field nor a heading`; it is not silently truncated.

6. **Did not fully match.** The code removes `now`, and the self-test proves it. But the plan/spec prose still lists `now` as banned at `docs/superpowers/plans/2026-09-19-feature-hub.md:24` and `docs/superpowers/specs/2026-09-19-feature-hub-design.md:157`. The remaining runtime list is still useful (`currently`, issue refs, status markers, `planned`, `done`, `TODO`, `in progress`, etc.), but the rule is now contradicted by its own spec.

7. **Did not fully match.** The implementation rule is present and tested in Task 3: unclaimed and double-claimed anchors are covered at `docs/superpowers/plans/2026-09-19-feature-hub.md:399` and `:403`. But old-design prose remains: `docs/superpowers/plans/2026-09-19-feature-hub.md:46`, `:762`, and `docs/superpowers/specs/2026-09-19-feature-hub-design.md:180`.

8. **Did not match.** `POPULATION` uses bare script names, so `check-features.py` / `gen-features-page.py` is the right shape there. `EXPECTED_MUTATIONS` is keyed by full paths like `"scripts/check-anchors.py"` at `scripts/check-plan-code.py:561`; the plan says add bare `"check-features.py": 4` at `docs/superpowers/plans/2026-09-19-feature-hub.md:720`, which is wrong.

9. **Did not match.** Three manifest anchors match the assembled source exactly once. The fourth anchor matches zero times:
   `for area in sorted(areas_in_use - set(claims))`
   The delivered source uses `area_claims`, so `check-plan-code.py` would report anchor NOT FOUND per `scripts/check-plan-code.py:1305`.

## Findings

### [Blocking] 1 — Task 2 depends on Task 3 before Task 3 exists

**Evidence:** Task 2 Step 1 runs `python3 scripts/check-features.py ... grep 'claimed by no node'` at `docs/superpowers/plans/2026-09-19-feature-hub.md:343`. But Task 1’s entry point still returns 0 for bare runs and does no real check at `docs/superpowers/plans/2026-09-19-feature-hub.md:158`; the real `main()` is only added in Task 3 at `docs/superpowers/plans/2026-09-19-feature-hub.md:485`. Task 2 Step 4 also expects `23/23` and a real check at `:366`, but Task 3 has not run yet.

**Introduced by round 1's fix?** yes.

**Why it matters:** Someone executing tasks in order cannot get the area list Task 2 requires, and will see a false/silent bare checker before the real checker exists.

**Fix:** Move Task 3 before the full-tree Task 2, or split Task 2 so the inventory/full-tree work happens after `main()`, `anchor_slugs`, `backlog_areas`, and `check_cross` exist.

### [Blocking] 2 — Task 6 registers `EXPECTED_MUTATIONS` with the wrong key shape

**Evidence:** The plan says add `"check-features.py": 4` at `docs/superpowers/plans/2026-09-19-feature-hub.md:720`. Existing `EXPECTED_MUTATIONS` keys are full manifest target paths, e.g. `"scripts/check-anchors.py"` at `scripts/check-plan-code.py:561`, and the runner compares those keys to manifest `"file"` values at `scripts/check-plan-code.py:1145`.

**Introduced by round 1's fix?** yes.

**Why it matters:** The mutation run will fail before measuring coverage: the manifest target is `"scripts/check-features.py"` but the declared count would be for `"check-features.py"`.

**Fix:** Change the instruction to add `"scripts/check-features.py": 4`. Keep `POPULATION` as bare names; that half is correct.

### [High] 3 — One mutation manifest edit is stale after the fold

**Evidence:** The manifest entry at `docs/superpowers/plans/2026-09-19-feature-hub.md:710` searches for:
`for area in sorted(areas_in_use - set(claims)):`
The Task 3 source at `docs/superpowers/plans/2026-09-19-feature-hub.md:471` now says:
`for area in sorted(areas_in_use - set(area_claims)):`
My exact-match count against the assembled source was `0`.

**Introduced by round 1's fix?** yes.

**Why it matters:** `check-plan-code.py` refuses missing anchors as not measured at `scripts/check-plan-code.py:1305`; Task 6’s `4/4 killed` claim cannot hold.

**Fix:** Update the manifest anchor to the exact delivered line using `area_claims`.

### [Medium] 4 — Spec/plan drift still describes the old design

**Evidence:** The plan still says `docs/anchors.md` “Gains a Feature column” at `docs/superpowers/plans/2026-09-19-feature-hub.md:46`, and the self-review still maps anchors through `Task 2 (Feature column)` at `:762`. The spec enforcement table still says `every Feature: in anchors.md resolves to a node` at `docs/superpowers/specs/2026-09-19-feature-hub-design.md:180`. The status-token prose still bans `now` in both plan and spec while the code intentionally allows it.

**Introduced by round 1's fix?** yes.

**Why it matters:** The executable rule mostly converged, but the documents now give mutually incompatible instructions to implementers and reviewers.

**Fix:** Remove the old Feature-column rows, update the enforcement rule to “every registry anchor is claimed by exactly one node,” and remove `now` from the prose definition of status tokens.

## Things I checked and found correct

The final assembled checker can pass `23/23`. Failure attribution now works. CANNOT-RUN returns rc 2 for all four requested paths. Escaped-pipe backlog parsing recovers rows `#90` and `#110`, while preserving the same distinct area set. Wrapped `for:` lines are refused. The exactly-one anchor rule is implemented in `check_cross` and covered by self-tests.

## What I could not run

I could not run the real repository `scripts/check-features.py` or `scripts/gen-features-page.py` because this is still a plan and those files are not implemented. I ran extracted/assembled plan code in `/tmp` instead.
