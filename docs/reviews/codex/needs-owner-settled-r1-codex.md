<!-- codex-review: model=gpt-6.1-sol -->

Reviewed head `435ef151` against `origin/master`.

- **R1 — Medium — scripts/goal-tree.py:716:** Pickaxe searches the entire file, without row identity. Reproduced: row 1 introduces a marker segment; row 2 later uses identical text, then its head becomes `SPEC MERGED`. Lookup selects row 1’s introduction commit, where row 2 is absent, returns `None`, and silently misses row 2’s settlement.

- **R2 — Medium — scripts/goal-tree.py:721:** Removing and re-adding the same marker reuses its oldest occurrence. Reproduced an old ask removed, then renewed under `NEW OPEN QUESTION`. The genuinely open question is flagged as possibly settled because its head differs from the previous ask’s head.

- **R3 — Medium — scripts/goal-tree.py:716:** Shallow history silently defeats clause 2. In a depth-one clone containing the rewritten head, Git treats the boundary commit as the marker’s introduction. The comparison reports unchanged, with no `NOT READ`. Reproduced a settled `SPEC MERGED` row receiving no flag. Empty successful history likewise silently returns `None` at line 720.

- **R4 — Low — scripts/goal-tree.py:689:** Negated decision words produce false flags. Both `NEEDS-OWNER — not DECIDED; still choose A or B` and `NEEDS-OWNER — not yet answered by the owner` receive the settlement warning and clearing remedy.

- **R5 — Low — scripts/goal-tree.py:706:** Any unrelated head edit triggers the settlement warning. Reproduced correcting `OPNE` to `OPEN (typo corrected)` while leaving the question open. This is an acknowledged heuristic limitation, but the adversarial false positive is real.

Validation: **430/430 self-tests pass; all 13 new mutations are killed by their expected cases.** Those tests do not cover the Git scenarios above. Explicit history exceptions remain visible on listed items; I found no path from those exceptions to “nothing waits on you.”

VERDICT: NOT CONVERGED
