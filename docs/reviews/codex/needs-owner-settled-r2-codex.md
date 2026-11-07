<!-- codex-review: model=gpt-6.1-sol -->

- **R2-1 — Medium — `scripts/goal-tree.py:739`**: `--first-parent` loses marker history imported from master. Reproduced: fork a feature branch before an ask exists; on master, introduce the marker under `OPEN`, then rewrite the head to `SPEC MERGED`; merge master into the feature branch. The reader treats the merge as the marker’s introduction, records `SPEC MERGED` as its original head, and returns no flag. The settled ask silently remains unflagged.

- **R2-2 — Low — `scripts/goal-tree.py:773`**: Renumbering silently resets the marker’s baseline. Reproduced: introduce row #5’s marker under `OPEN`, rewrite its head to `SPEC MERGED`, then renumber the unchanged row to #9. The lookup treats #9’s addition as a fresh marker introduction and returns no flag, losing the previously detectable settlement.

Validation: **450/450 self-tests passed**. Real-git corpus recheck at `11a70deb` confirmed #306/#384 flagged and #2/#86/#198/#307 unflagged. Movement, adjacent edits, embedded row-number text, CRLF, escaped pipes, failure-cache isolation, and the specified affirmative decision phrases passed probes. All 481 current backlog rows matched the last-cell status rule.

VERDICT: NOT CONVERGED
