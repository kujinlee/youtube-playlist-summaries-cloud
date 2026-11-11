<!-- codex-review: model=gpt-6.1-sol -->

**CONVERGED — two Low wording findings; no merge defect found.**

- **Low — stdin mutant misclassified.** `scripts/compaction-state.py:988–990` lists “the stdin read’s bound” among mutants killed only by real-time cases. Backlog row 424 likewise places `STDIN_WAIT = 20.0` under that heading, while explicitly acknowledging it survives **both** modes. Move it into the neither-mode category and correct the docstring’s example.

- **Low — CI guard’s documented blind spots remain incomplete.** `scripts/compaction-state.py:1023–1024` names step-level and job-level shell overrides but omits **workflow-level** `defaults.run.shell`. A direct probe with top-level `shell: 'true {0}'` returns `None` (accepted), although that shell bypasses the script. Name this scope too. The actual workflow passes the guard.

Merge verification:

- All **81** `EXPECTED_MUTATIONS` pins match their manifests; AST-computed sum **2,980**, matching the literal. `load_manifests` reports 2,980 entries and no problems.
- Decision log preserves all **150 parent-union identities**, without duplicates, plus one new redesign entry. The existing scaled-deadlines entry updates only `outcome` and `observed`.
- Backlog preserves every parent number, adds only **424**, and has no duplicate numbers. The main numbered sequence remains ordered; earlier ordering exceptions predate this merge.
- `compaction-state.py` changes **only docstrings**: its AST is identical after removing docstrings.

Suites passed: compaction real-time **125/125**, marker **123/123**, check-plan-code **249/249**, stalled-work **183/183**. Full mutation sweep was not rerun. No review file written; `.claude/plans/` was not accessed.
