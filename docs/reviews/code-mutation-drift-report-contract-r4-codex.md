# Code review round 4 - Codex half - scoped to round 3's fix

**Subject:** commit `87ea0001`, limited to the round-3 changes in
`scripts/check-plan-code.py` and `scripts/mutations/check-plan-code.json`.
**Date:** 2026-09-04. **Model:** `gpt-5`.

## Findings

No defects found in round 3's own fix.

## Executed Checks

- `git status --porcelain`
  Result before review: clean.

- `python3 scripts/check-plan-code.py --self-test`
  Result: `177/177 passed`.

- `python3 scripts/check-plan-code.py --mutate .`
  Result: `OK — delivered scripts mutated: 7 file(s), 173 mutation(s), 0 survivor(s)`, exit 0.

- Manifest and count audit:
  `scripts/mutations/check-plan-code.json` has 32 entries, 32 unique names, and 32 unique edit-anchor
  tuples. `EXPECTED_MUTATIONS` has 7 targets and sums to 173. The `check-plan-code.py` entry is 32.

- Anchor-location audit over all 32 manifest entries:
  every edit anchor bound exactly once. The bound locations were printed with line number and owning
  function; entries 22-32 land on the round-3 constructs they name:
  `mutate_delivered` after-control `controls_green = False`, `verdicts_are_trustworthy`'s measured,
  control, and cardinality clauses, `check()`'s initializer and predicate call, `main()`'s plan-mode
  gate, `evidence()`'s block gate and cannot-run renderer, and `not_measured_line()`'s shortfall
  arithmetic. I did not find a third orphaned mutation whose anchor still binds to the wrong construct.

- Hand-applied changed-manifest entries 22-32 in a temp copy outside the repo:
  each mutation made `--self-test` exit 1 and each named `expect` case appeared exactly once in the
  red case list. Neighboring assertions also failed for some broader predicate mutations, but the
  named case was always present and singular.

- Companion-case vacuity sweep in a temp copy:
  I separately broke the companion properties not directly named by entries 22-32. The targeted cases
  reddened: green controls earning trust, same-entry declared-count trust, delivered complete-run
  trust, timeout report text, real-survivor rendering, and the trustworthy evidence header.

- `mutate_delivered` before-control path:
  imported the module, built a mini delivered tree in `/tmp`, monkeypatched `run_suite` to return red
  on the first control, and scoped `EXPECTED_MUTATIONS` to the fixture. Result:
  `ok=False`, `run_suite_calls=['scripts/thing.py']`, `declared=None`, `mutations=0`,
  `trustworthy=False`, with report text beginning `CANNOT RUN — control run ... BEFORE any mutation`.
  This proves the path reaching `controls_green = True` has already passed the before-control return.

- `check()` red-control path and caller behavior:
  imported the module, built a plan whose control is red before mutation and whose mutation still
  applies and is recorded caught. Result: direct `check()` returned `ok=False`, `trustworthy=False`,
  `declared=1`, `mutations=1`, `caught=[True]`, and `survivors=0`. `evidence(ev)` contained
  `NOT MEASURED` and did not contain `mutations declared and run`. `main([plan])` returned 1 and its
  final line was `NOT MEASURED — plan's copy only, NOT compared: ...`; `main([plan, '--evidence'])`
  returned 1 and printed `NOT MEASURED` in both the evidence block and final line. I found no internal
  caller that still acts on this as a coverage verdict.

- F2-S3 executed for `--mutate` mode:
  running raw CLI against an arbitrary mini root correctly refused on `EXPECTED_MUTATIONS`, so I used
  the same imported-main, scoped-count shape as the self-test. Green fixture:
  `rc=0`, final line `OK — delivered scripts mutated: 1 file(s), 1 mutation(s), 0 survivor(s)`.
  After-control-red fixture:
  `rc=1`, final line `NOT MEASURED — the mutation harness produced no coverage verdict. Treat this as NOT CHECKED.`,
  with `NOT MEASURED=True` and `survivor(s)=False`.

- `not_measured_line` call-site text:
  direct/evidence call produces
  `NOT MEASURED — the mutation harness produced no coverage verdict (1 of 3 declared mutation(s) produced a verdict). Treat this as NOT CHECKED.`
  Plan-mode subject call produces
  `NOT MEASURED — plan's copy only, NOT compared: the mutation harness produced no coverage verdict ...`.
  The difference is exactly the intended subject prefix; I did not observe an unintended sentence drift.

- Consumer scan:
  `rg` over non-JSON repo files found the relevant live consumers in `main()`, `evidence()`, and
  `verify_evidence()`; the rest are docs or unrelated functions. `verify_evidence()` re-derives via
  `evidence(ev)`, so it inherits the `NOT MEASURED` block gate.

- `git status --porcelain`
  Result after review actions, before this file was added: clean.

## Not Checked

I did not re-review unrelated historical behavior guarded by entries 1-21 beyond verifying their
current anchors still bind uniquely to the named functions and the full delivered mutation run is green.

CONVERGED.
