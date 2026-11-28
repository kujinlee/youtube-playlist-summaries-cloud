Reviewed head: 9db233067e2c8f1bf469c2ba2da7d35a6d6c2e1a

# Round 3: `subject-status-386`, Claude half

Subject: `git diff 3b924595 9db23306`, which holds the r1 and r2 folds in `scripts/check-shipping-sets.py`,
`scripts/subject_status.py`, `scripts/mutations/check-shipping-sets.json` and `expected_mutations.py`.
Mandate: try to REFUTE what the folds claim.

## What was run

| Check | python3.12 (CI pin) | python3 (3.14.4) |
|---|---|---|
| `check-shipping-sets.py --self-test` in the worktree | 176/176 | 176/176 |
| `subject_status.py --self-test` in the worktree | 18/18 | 18/18 |
| Mutation "non-string shared_with" → the case its `expect` names goes red | red (`[('shared_with','[[]]'),('shared_with','[{}]')]`) | red |
| Mutation "no depth bound" → the case its `expect` names goes red | red (`got False`) | red |
| Mutation "non-string measured_at" → the case its `expect` names goes red | red (the accepted set gains `measured_at` 1.5, `[[]]`, …) | red |
| Off-manifest: delete `except RecursionError` (`check-shipping-sets.py:781-782`) | killed by the 200,000 case (`RAISED RecursionError`) | killed by the 200,000 case (`RAISED RecursionError: Stack overflow (used 16352 kB)`) |
| Off-manifest: change the parse-path message to the walk's | **survives** (no new red) | **survives** |
| `subject_tables` mutant that also counts `alter table` names | 16/18 (red) | 16/18 (red) |
| `subject_tables` mutant that also counts `references` names | 17/18 (red) | 17/18 (red) |
| Manifest entries for the script vs the pin in `expected_mutations.py` | 220 = 220 | n/a |

How the mutations were run: each one on a clone of `git archive HEAD` under the session scratchpad, deleted
afterwards. The repository was not touched. The clone has no `node_modules`, so 40 CLI and XM cases are red in
every run, mutated or not. A mutation counts as killed only when the case its `expect` names is red, and that
case is green on the unmutated tree.

Depth probe, `json.loads('['*n + ']'*n)`: python3.12 parses n=5,000 and raises `RecursionError` at n=100,000.
python3.14 parses n=100,000 and raises at n=200,000. So the 50-level case reaches the walk on both
interpreters (r2's D1 fold holds), and the 200,000 case reaches the parse path on both, on this machine.

What held under the refutation attempts:
- The walk runs before any `repr`.
- The `measured_at` check runs after the `isinstance(data, dict)` check, so `data['measured_at']` cannot
  raise a `KeyError`. A missing `measured_at` defaults to `""` and is accepted, as before.
- No two `json.dumps(v)` keys in the accepted-set pin collide.
- The UNSHIPPED fixture now separates "creates" from "references" and "alters" in both directions.
- D2 (declined by design) is a reasonable call, consistent with `check-inventory._read_json`.

## Findings

### MINOR M1: the 200,000 case does not test what its name says, and the clause it protects has no manifest entry

`scripts/check-shipping-sets.py:1554` (case), `:781-782` (clause)

- **What the case asserts.** The case is named "a map nested 200,000 deep fails inside json.loads and is
  CANNOT RUN". It only asserts the prefix `CANNOT RUN: cannot read the map`. The depth walk's message starts
  with the same prefix, so the case cannot tell which path refused the map.
- **Reproduction.** Replace `nested too deep to parse"` with `nested deeper than 32 levels"`. Both
  interpreters stay green: no new red.
- **Why it matters.** On 3.14 the parse limit depends on stack size ("Stack overflow (used 16352 kB)"). A
  runner with a larger stack would parse 200,000 levels and refuse them in the walk instead. The case would
  stay green while its name became false. On 3.12 the limit is a fixed counter, so CI is not affected today.
- **The clause works.** Deleting the `except RecursionError` clause IS killed by this case on both
  interpreters. The gap is that no manifest entry records that mutation, so the pin of 220 does not cover the
  clause.
- **Fix.**
  1. Assert `"nested too deep to parse" in ...`, mirroring the 50-level case's `"nested deeper than 32"`.
  2. Add a mutation that deletes the clause, with `expect` set to this case, and pin 221.

Filing this is acceptable under the round cap. It is not a blocker.

### NIT N1: one sentence in the docstring is still stale, and the folded line is very long

`scripts/subject_status.py:9`

- **Stale claim.** "Two of them exit 1." is still in the present tense, next to the corrected sentences. The
  fold itself says the schema shipped as migration 0027 and that the schema gates run in CI. A gate in
  `schema-gates.yml` that exited 1 would leave every PR red, so the sentence describes 2026-08, not now.
- **Line length.** The folded line is 171 characters, against roughly 100 for its neighbours.
- **Fix.** "Two of them exited 1 from `1a7c076` …", and rewrap the line.

VERDICT: CONVERGED
