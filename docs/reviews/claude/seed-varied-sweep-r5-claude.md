Reviewed head: 14967cde7cb75cabd86aaca30b65cace44300a7a

Adversarial Claude half, round 5 (capped, §0 Q4c: only a BLOCKER is folded) of `seed-varied-sweep` (backlog #506 remainder, PR #523).
Scope: the commits after the r4 record `42ba2be1`, which are the master merge `437df256` and `14967cde`. `14967cde` drops the racy case name
"outcomes come back in the given order, not completion order" from the `expect` of mutation `#487: outcomes are returned in completion order`
in `scripts/mutations/check-selftest-counts.json`.

## Refutation attempts

1. **Does the remaining `expect` case fail deterministically under the mutant?** It does.
   - The mutant replaces `return [outcomes[name] for name in names]` with `return list(outcomes.values())`.
   - The case monkeypatches `concurrent.futures.as_completed` to return `reversed(list(fs))`. `fs` is the `futures` dict built in `run_suites`. A dict keeps insertion order, so the reversal is fixed at `c, b, a` and does not depend on the scheduler.
   - I applied the mutant to a `git archive HEAD` copy with `HOME` redirected to a scratch dir and ran `check-selftest-counts.py --self-test` 3 times. All 3 runs exited rc 1, and every run showed `[FAIL] backlog #506: ... got ['c', 'b', 'a'] want ['a', 'b', 'c']`.
   - The control on the unmutated tree passed 60/60.
   - I also ran the harness itself, `check-plan-code.py --mutate . --only scripts/check-selftest-counts.py`. It reported 34 mutations, 34 killed, 34 attributed to the case each names, and 0 survivors. This is a diagnostic slice, not the gate.

2. **Did removing the name weaken anything?** No. It removes a false red.
   - The racy case lost the race in my own runs. Run 3 printed `✓ outcomes come back in the given order, not completion order` under the mutant: 59/60 passed, and only the #506 case was red. That is the CI failure reproduced locally, 1 in 3.
   - `seed_outcome` (in `check-plan-code.py`) compares the NAMED red cases across seeds. A name in `expect` that goes red only sometimes therefore produces a false NONDETERMINISTIC red, not just a flaky kill.
   - The racy case is still in the suite (line 965) as a check on the real implementation, which always returns the given order. Only its role as this mutation's attribution was removed. No other manifest entry names it; I grepped `scripts/mutations/` and found 0 hits.

3. **Does the anchor still match exactly once?** Yes. `    return [outcomes[name] for name in names]` occurs 1 time in `scripts/check-selftest-counts.py` at HEAD. The harness run above bound and killed it.

4. **Conflict residue from the master merge `437df256`:**
   - I re-ran `git merge-tree --write-tree 42ba2be1 319bd152`. The only conflicts are in `docs/dashboard-entries.md` and `docs/reviews/decision-scheme/decision-log.jsonl`.
   - `437df256` differs from the auto-merge tree only in those two files, and in each the difference is the removal of the `<<<<<<<`/`=======`/`>>>>>>>` markers with both sides kept.
   - No conflict markers remain in either file. Every line of `decision-log.jsonl` parses as JSON. The 19 files master brought in (`goal-tree.py`, `check-plan-code.py` pin line, `goal-tree.json`, open-prs-mixed review records) arrived exactly as master had them.

## Findings

None.

Observation, not a finding: the case "two suites run AT ONCE in a pool of two" also reads `got[0]`, which goes red only by luck under the completion-order mutant (red in 2 of my 3 runs). It is not named by this mutation. The mutation that does name it (`max_workers=1`) kills it deterministically, because `a` waits on an event that a serial pool never sets.

VERDICT: CONVERGED
