Reviewed head: 4935fa11fac2342cf07b66bc040dcb4e3737c312

# suite-cost-a round 5, Claude half (scope: commit 4935fa11)

Mandate: REFUTE. Result: no refutation found.

1. Can the spy case pass with the skip removed? No. The edit is `if '"seven_day"' not in line:` to `if False:`
   (scripts/check-usage-pace.py:370). I ran the whole suite in a staged copy of `scripts/` and `.claude/hooks/` with that edit.
   Result: rc 1, 393/394, and the one `[FAIL]` line is the new case. The recorded value is `['', '', '{"garbage": 0}', ...]`.
   `pace_line` looks `meter_row` up as a module global at call time (line 372), so the spy sees every call. The spy sits outside the
   `lru_cache`, so a cache hit still counts. This is the point of the commit.
2. Can it fail on correct code? No. The unmutated suite passes 394/394 (25 s). The junk lines are blank or `{"garbage": i}`, and none
   contains `"seven_day"`. The only call site of `meter_row` outside the self-test's own memo case is `pace_line:372`. The spy records
   the line before delegating, so cache state left by earlier cases cannot change `_seen`. The `_skipped` side compares with
   `pace_line(_row + "\n", ...)`, which is the answer the single row gives alone.
3. Does the spy restore the global on every path? Yes. `meter_row` is restored in a `finally` (lines 1082-1085), and `_real_row` is
   captured before the `try`. A raise inside leaves the module clean.
4. Harness rule. `parse_fail_names` (from `scripts/check-plan-code.py`), fed the mutant's output, returns exactly
   `['⭐ #500 r3 C1: blank and garbage meter lines never reach the parse — only the seven_day row does']`. That equals the manifest
   `expect` at `scripts/mutations/check-usage-pace.json:1641`. The name contains no `": got "`, so it is not truncated. The mutation
   count is unchanged at 175. The case pin 394 matches the suite's printed count. No other manifest entry edits `meter_row` bodies or the
   skip. The memo-removal entry removes only the decorator, and the spy sits outside it.
5. Production change: none. The diff to `scripts/check-usage-pace.py` is the usage docstring count plus the self-test case. The other
   changes are the manifest `expect`, `docs/backlog.md` and `docs/dashboard-entries.md`.

## Findings

None at Blocker, High or Medium.

### R5-F1 — Low — the old timing case now only backstops (not fixed, informational)
scripts/check-usage-pace.py:1069. With the skip removed it still passes on this branch's code (0.36-0.52 s, per the commit). It is
now a backstop for the case where `meter_row` is called but the skip is removed on master-like code without the memo. Nothing to
fix; the commit message already says this.

VERDICT: CONVERGED
