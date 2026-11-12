<!-- codex-review: model=gpt-6.1-sol -->

Reviewed `46684991`. **Three MAJOR findings; no BLOCKER.** Worktree unchanged; no GitHub operations.

1. **MAJOR — fresh retries still share state through absolute symlinks.**  
   `scripts/check-plan-code.py:2249`, `:2272` preserve symlinks in both copies. Reproduced with a green control creating an absolute link to a counter beside the suite. The first mutant run increments it to 1 and survives; the retry follows the link into the original tree, increments it to 2, and reports **`ok=True`, FLAKY**. With dereferenced copies, the same probe remains **SURVIVED, `ok=False`**, and the original counter stays 1.  
   **Fold-caused:** the new isolation implementation retains this route to r1 X2/CL-m1’s contamination defect; that disposition is only partially closed.

2. **MAJOR — missing shard artifacts silently count as no FLAKY.**  
   `scripts/sweep-red-alert.py:78–81`; `.github/workflows/ci.yml:1505`. The reader checks directory existence, not shard completeness; download errors are also allowed to continue. With fake `gh`, both an existing empty directory and a directory containing only empty `shard-0.txt` returned **rc 0**, printed **“no FLAKY mutation in this sweep”**, and wrote no issue. Missing files from the other 37 shards were undetected. A partial download can therefore lose FLAKY evidence silently.  
   **Fold-caused:** yes. The absent-directory test passes, but does not cover a missing artifact within a partial download.

3. **MAJOR — filing truncates real mutation names and merges distinct mutants.**  
   `scripts/sweep-red-alert.py:62–64`. The parser splits at the first `: `, which occurs inside many manifest names. Ran three actual names beginning `#495:`, including “a survivor is never re-run” and “a FLAKY mutant turns the run red”: the parser returned only **`['#495']`**. The resulting issue cannot identify which mutants were flaky and undercounts them.  
   **Fold-caused:** yes. The new parser’s self-test explicitly accepts this truncation.

Validation and remaining dispositions:

- Self-tests passed: **check-plan-code 441/441; sweep-red-alert 24/24; batch-ci 169/169; check-merge-ready 400/400; check-selftest-counts 60/60**.
- Crash, timeout, unrelated-case red, retry seed split, and exhausted-budget fixtures remain red SURVIVED. Ordinary-file isolation passes; symlink isolation fails as above.
- FLAKY stays outside killed/attributed totals. Batch attribution ejects only the real SURVIVED owner.
- Executed **27 changed/rebound mutation pins** on temporary copies: every declared expectation failed. Reduced mutation fixtures also produced unrelated missing-tree failures; named failures were checked explicitly.
- Completion-order mutant failed both named ordering assertions; the serial-pool mutant also failed.
- Ran the shard shell with 38 indices: **38 unique filenames**, including 37 valid empty files; no collision. Harness rc 1 remained rc 1.
- Green FLAKY filing and repeat commenting work with fake `gh` for intact inputs. Failure does not skip upload/download/filing because `!cancelled()` supplies a status condition; cancellation deliberately skips them under the existing #482 policy.
- New `ACCOUNTED_MENTIONS` entries exclude PRs, and their allowances are fully consumed. Appending another copy was refused. No fold-caused gate escape found there.
- Dashboard attribution correction and incidental-case attribution fix are consistent with the coordinator’s dispositions.

Evidence is under `/tmp/review495.94074Z/`.

## Loosening answers
LOOSENING-CHECK 3658aa4ac1f3: finding: first-run survivors can pass green as FLAKY when the retry kills through shared symlinked state; master refused those survivors
LOOSENING-CHECK 6aad9d611ea7: not a loosening

VERDICT: NOT CONVERGED
