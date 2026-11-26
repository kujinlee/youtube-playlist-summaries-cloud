Reviewed head: b1f6ea6af46c4da73a1faecf32149b0b1d1c1f28

# Round 4 (Claude half, final tree) - PR #644, diff 073c9431..HEAD

Round 4 is past the cap: only a BLOCKER folds. I found none.

## Refutation attempts

1. explainer-serve docstring count: `python3 scripts/explainer-serve.py --self-test` prints `self-test: 301/301 passed`. The 298 -> 301 edit matches. Could not refute.
2. check-inventory: `scripts/check-inventory.py` exits rc 3 (the expected D1 checkpoint, "fired over 29 phase-1 rows", Stop: H4). `--self-test` prints 311/311 passed, rc 0. Could not refute.
3. Inventory diff: `git diff --numstat` on `docs/marketplace/inventory.json` is 0 added, 82 deleted. The `+` line count is 0. The only `"id":` lines in the diff are the removed `gen-dashboard` and `hook-regen-dashboard`, with their neighbours `gen-goals-page` and `hook-regen-features-page` as context. So it is a pure deletion of exactly those two rows.
4. Live references to the removed row ids: the remaining hits for `gen-dashboard` or `hook-regen-dashboard` are
   - prose in other rows' `notes` fields in inventory.json;
   - `experiment-tier-a.json` (scenario history);
   - `scan-2026-11-17.json` and `scan-2026-11-21.json` (scan history);
   - `scripts/goal-tree.py:5794`, a script-name comparison unrelated to inventory rows.
   None is a live row id or a `rests_on` reference. check-inventory still parses the file and reaches the checkpoint, and its self-test is green.
5. `scripts/check-decision-scheme.py`: rc 0 (WARN-only output). `scripts/check-docs.py`: rc 0, "Documentation integrity OK".

## Findings

None at BLOCKER, MAJOR or MINOR.

NIT: the `notes` of other inventory rows still describe `gen-dashboard` and `hook-regen-dashboard` as live dependencies. That is historical measurement prose, not a gate. Not folded (past the cap).

Gates:
- explainer-serve --self-test: 301/301 passed
- check-inventory: rc 3 (expected checkpoint)
- check-inventory --self-test: 311/311 passed, rc 0
- check-decision-scheme: rc 0
- check-docs: rc 0, Documentation integrity OK

VERDICT: CONVERGED
