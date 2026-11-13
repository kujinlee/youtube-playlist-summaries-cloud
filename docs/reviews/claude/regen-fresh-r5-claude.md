Reviewed head: 8d1327f8098d4b7bed04e8d2f829a55b76fb5356

# regen-fresh — review round 5, Claude half (mandate: REFUTE)

Scope: `git diff f9881e0b..8d1327f8` (the one commit after Codex r4 CONVERGED). It touches the test code in
`scripts/regen-pages.py`, `scripts/mutations/regen-pages.json` (+2 entries), `scripts/mutations/expected_mutations.py`
(58 -> 60), `docs/backlog.md` and `docs/dashboard-entries.md`.

## What was measured (all at 8d1327f8 unless marked base)

| Check | Result |
|---|---|
| `python3 scripts/regen-pages.py --self-test` | rc 0, `107/107 self-test cases passed`, 0 `[FAIL]`/`NOT RUN` lines (26 s) |
| `python3 scripts/check-selftest-counts.py --only regen-pages.py` | rc 0 (read directly, not through a pipe) |
| The 2 new mutations (manifest idx 58, 59), staged with `check-plan-code.stage_tree`, run with `run_suite`, read with `parse_fail_names` | both rc 1; 1 red case each; their `expect` matches exactly 1 red name |
| The 4 formerly unattributed mutations (idx 36, 50, 18, 52), same driver | all rc 1; every `expect` entry matches exactly 1 red name (18: [1,1]; 36: [1]; 50: [1]; 52: [1,1]) |
| The same 4 at **base f9881e0b** (staged from `git archive` of the full `HARNESS_TREE`) | 36: 0 `[FAIL]` lines, `FileNotFoundError`; 50: 0 `[FAIL]`, `AttributeError: 'tuple' object has no attribute 'split'`; 18 and 52: the step-case `AttributeError`, the ⭐⭐ `expect` matched 0. This confirms the commit message's diagnosis, and that HEAD fixes it |
| Mutations 0-11 (a partial sweep that the coordinator stopped; no full sweep was run) | all rc 1, each `expect` matched exactly once |

The driver I used is my own wrapper around the harness's own `stage_tree`, `run_suite` (so the env is `mutation_env`) and
`parse_fail_names`. Attribution follows the harness's rule: rc 1, and each `expect` matches exactly one red name.

## Refutation attempts

1. **Red to green through the guard.** `_crash_guarded` (`scripts/regen-pages.py:700-713`) returns `body()`
   unchanged on a normal return. So a body that recorded failures still returns 1. Every caught exception
   returns 1, never 0. `KeyboardInterrupt` is not caught (only `Exception` and `SystemExit` are). `SystemExit(False)`
   counts as code 0 and is re-raised, which matches its exit status. The guard case's own nested `[FAIL]` output
   goes into a `StringIO`, so a green run prints no `CRASH_CASE` line (checked: 0 `[FAIL]` at HEAD). The case
   count goes to 107 only by the one new `case()`. If `check-plan-code.py` were absent, the case would print
   `NOT RUN` and the count would be 106, which `check-selftest-counts` reports as drift. That is loud, not silent.
2. **`outcome()` returning `("CRASHED", …)`** (`:967-975`). I read all 20 call sites (lines 992-1732). Each one
   compares `[0]` against a literal `"ok"` or `"CANNOT RUN"`, or compares the whole tuple against an `("ok", …)`
   want. No want contains `"CRASHED"`, and no want is derived from the got value. So a crash cannot satisfy any
   comparison, and every crash reddens the case that reads it.
3. **The first `fresh()` block's `except Exception`** (`:996-1007`) replaces `seen_in_block` with six `CRASHED` strings.
   Its case can never equal the six-element want, so that case goes red by name (measured: mutant 36's `expect`
   hit). The sentinel `t0_tree` may let some later cases compute "green" values, but the run is already red.
   It cannot reach rc 0.
4. **Production behaviour.** Every hunk is inside `_self_test*`, the module docstring's case count, or the new
   `CRASH_CASE`/`_LAST_CASE`/`_crash_guarded` definitions. The only caller of those definitions is the self-test.
   `main()` and the `--hook`/`--all`/`--page` paths are untouched. I found no production change.
5. **Anchors.** Each new mutation's find-text occurs exactly once in the file (the driver refuses otherwise, and both
   were applied).

## Findings

### R5-F1 — Low — the guard re-raises `SystemExit(0)`/`SystemExit(None)`, so a suite truncated by a clean exit still exits 0 and names nothing; the docstring says "SystemExit included"

`scripts/regen-pages.py:707-709`: `if isinstance(exc, SystemExit) and exc.code in (0, None): raise`.

- **Input:** a mutant or bug that makes a code path reached from a case call `sys.exit()` or `sys.exit(0)` mid-body.
- **Result:** the process exits 0 before the `N/M self-test cases passed` line, with no `[FAIL]`. The harness reads
  rc 0 as a survivor, which is loud. A plain `--self-test` run in CI also reads green, and only the outside observer
  `check-selftest-counts` would catch it, from the missing count.
- `_self_test_cases` never legitimately exits, so a clean `SystemExit` escaping it is always a truncation. The
  carve-out is not the gap this commit set out to close (non-zero exits), and the behaviour existed before this
  commit, so this is not a regression.
- Two smaller points:
  - the docstring at `:701` ("anything it raises (SystemExit included, KeyboardInterrupt not)") overstates what the
    code does, since only a non-zero exit is caught;
  - no case pins the zero-exit pass-through, so deleting the `raise` line survives (inferred, not run).
- **Suggested (FILE, not fix):** treat any `SystemExit` escaping the body as `CRASH_CASE`, or reword the docstring to
  "a non-zero SystemExit".

### Observation (not a finding)

Under mutant 36, the suite still stops early: a later bare `fresh()` block (`swapped`, `:1181`) raises. `CRASH_CASE`
now names the stop (`after case: …R3-F3…`, which is textually correct at `:1171`), and the named `expect` case went
red first. So attribution holds. Every case after `:1190` simply does not run for that mutant. That is acceptable
for a red run.

VERDICT: CONVERGED
