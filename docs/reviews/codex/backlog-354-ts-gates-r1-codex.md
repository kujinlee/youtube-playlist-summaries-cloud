<!-- codex-review: model=gpt-6.1-sol -->

1. **High — ordinary call whitespace yields false READY.** [scripts/check-merge-ready.py:513](scripts/check-merge-ready.py:513) requires `process.exit(` without whitespace. In a temporary real Git repository, changing `scripts/check-space.ts` from `process.exit (1);` to `process.exit (0);` produced no holds and `(0, 'READY')` through `gather → hold_reasons → final_verdict`. Executing both with Node returned **1 → 0**. This is ordinary syntax, distance zero, requiring no semantic inference. Allow whitespace before `(` and add a regression case.

2. **Medium — equality comparisons are mistaken for failure assignments.** [scripts/check-merge-ready.py:513](scripts/check-merge-ready.py:513) matches the first `=` in `process.exitCode === 0`: the next character is `=`, so the zero exclusion does not apply. Executed probe:

   ```diff
    if (process.exitCode === 0) {
   -  console.log("complete");
   +  console.log("done");
    }
   ```

   Under `scripts/cloud-sync.ts`, `hold_reasons` reports a removed failure-path line. This changes only logging beside a success comparison. Require an assignment operator rather than accepting `==` or `===`.

Executed verification:

- `python3 scripts/check-merge-ready.py --self-test`: **206/206 passed**.
- Applied all **seven new mutations and three re-bound mutations** in memory, preserving the repository context: each returned failure and reddened **every named expected case**. No ambient-only kills found.
- Replayed the latest **40 merged PRs** against `origin/master` and HEAD, with app tests attested and no waiver: **11 held in both, identical PRs**, no collection errors. This supports the documented replay claim.
- Adjacent variable changes before `process.exit(code)`, compact `process.exitCode=1`, rethrows, `return 1`, `.claude/hooks/*.ts`, and `scripts/ci/*.ts` were held. A real Git symlinked `.ts` gate also held its target’s weakening.
- Node template strings still trigger textual false holds; extension scoping prevents the Python-stub instance, not strings generally. That is consistent with the stated syntactic bound.
- Backlog, dashboard, and PR #402 agree on the inspected changes and replay count. I independently checked the ten relevant mutations, not the entire claimed 82-entry sweep.

VERDICT: NOT CONVERGED
