Reviewed head: 1652618487bcec4ff3eac86b1b9b9f52a4286b95

# PR #641 (backlog #687), round 1, Claude half

Mandate: refute that each new mutation is load-bearing and bound to the right case.

## What was run (all foreground)

- `python3 scripts/goal-tree.py --self-test` on HEAD: **606/606 passed** (4.7 s).
- A `git archive HEAD` copy at `scratchpad/b687r1c/tree` with node_modules symlinked. For each of the two `backlog #687` entries in `scripts/mutations/goal-tree.json`, the script asserted that the find string occurs exactly once (it did, 1 and 1), applied the edit, ran the goal-tree self-test, and reverted.
  - Mutation 1 (CANNOT RUN branch, `scripts/goal-tree.py:910`): rc 1, **605/606**. The only `[FAIL]` is the r2 Codex M1 case, which is the entry's `expect`.
  - Mutation 2 (merged branch, `scripts/goal-tree.py:929`): rc 1, **605/606**. The only `[FAIL]` is the r2 Codex M1 case, which is the entry's `expect`.
  - A clean re-run after both reverts: 606/606.
- Reachability, read at `scripts/goal-tree.py:901-929`: `cells_held` forces `by_cells` False at :902. So on the unread path, `not by_cells` alone is True, and :910 needs its `not cells_held` to avoid CANNOT RUN. On the read path with a `hit` and no `row_open`, :929 needs its clause to avoid `merged`. Neither clause is redundant, and each mutation deletes exactly one of them. No refutation found.
- Pin: entries with `file == scripts/goal-tree.py` across `scripts/mutations/*.json` number 528 at HEAD and 526 on origin/master, against a pin of 526 on master and 528 at HEAD. The arithmetic is correct. No duplicate names in the manifest.
- `check-plan-code.py --mutate` was NOT RUN, as the brief instructed. The per-entry kill above is a hand reproduction of what the harness checks for these two entries only.

## Findings

**F1 (MINOR): the backlog row's numbers are stale from before the master merge** (`docs/backlog.md:632`). The DONE cell says "measured: 607/608 for each" and "pin 528 -> 530". At this head the measurement is 605/606 for each (606 cases total) and the pin moves 526 -> 528, which is what `scripts/mutations/expected_mutations.py:490` correctly says. The row and the pin comment now disagree. Fix: change the cell to "605/606 for each" and "pin 526 -> 528", or drop the case totals and keep only "the only case either deletion turns red". The rest of the row's claims hold: two entries, one per clause, each removing that clause alone, each with `expect` exactly the M1 case, and that case is the only one either deletion turns red.

No other findings. The mutations are load-bearing, uniquely anchored and bound to the correct case.

VERDICT: NOT CONVERGED
