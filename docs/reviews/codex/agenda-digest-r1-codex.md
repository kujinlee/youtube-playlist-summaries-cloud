<!-- codex-review: model=gpt-6.1-sol -->

- **Medium — scripts/goal-tree.py:1360:** The recap excludes unfinished steps without references. With one unticked free step (`restart`), it says “no step of the plan is left,” while All steps still shows that unfinished step. Mixed plans likewise undercount remaining steps.

- **Medium — scripts/goal-tree.py:1333:** Loose in-flight work loses its explanation. Given `{"id":"build-777","what":"working on backlog #777"}`, the digest hardcodes `what: ""`, so its displayed line omits the available purpose.

- **Medium — scripts/goal-tree.py:1742:** Escaping lacks effective regression coverage. Independently removing escaping from goal chips, `what`, window, or change-if leaves **346/346 tests green**. Current code escapes these values, but claim 4 fails: none of these regressions fails by name.

- **Low — scripts/goal-tree.py:1363:** Tie handling is untested. Changing the selection key to `(len(kv[1]), kv[0])`, which chooses lexicographically rather than preserving the first goal on ties, leaves **346/346 tests green**.

Verification: 1,000 generated snapshots produced identical `agenda_context` results against origin/master. All eight added manifest mutations failed under their expected case names. STALE, undeclared counts, and All steps remain rendered. No `.claude/plans/` files were read.

VERDICT: NOT CONVERGED
