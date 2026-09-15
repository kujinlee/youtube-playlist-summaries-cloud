<!-- codex-review: model=gpt-5.5 -->

**Blocking**

Claim: the 21 new mutation entries are valid and were verified by execution.

Evidence: `scripts/check-plan-code.py:966-968` refuses a manifest entry that repeats another entry’s edit anchors. The r11 entries do exactly that in both new/changed manifests: `scripts/mutations/check-review-recorded.json:290-309` repeats the same `tail_candidates` anchor for entries 24 and 25, and `scripts/mutations/codex-review.json:47-66` repeats the same `dirty[path] = ...` anchor for entries 5 and 6. CI runs this check at `.github/workflows/ci.yml:389-390`.

Concrete failure scenario: CI’s delivered mutation-manifest step exits before mutation coverage is measured, so the branch cannot substantiate the “21 new mutations verified” claim and would red on the committed tree.

Command and output, run in an isolated copy with `.git` removed:

```text
$ python3 scripts/check-plan-code.py --mutate .
rc 1
  ✗ check-review-recorded.json: entry "the tail is charged over the base's commits again" repeats the edit anchors of an earlier entry — it measures nothing new
  ✗ codex-review.json: entry 'the SOURCE mode is recorded instead of the destination mode' repeats the edit anchors of an earlier entry — it measures nothing new
NOT MEASURED — the mutation harness produced no coverage verdict. Treat this as NOT CHECKED.
```

I also bypassed that preflight by running only the r11 subsets through `run_mutations()` in an isolated copy. The suites went red, but the new `expect` strings are mostly fragments, not exact case names, so the harness marked them unattributed. Example output:

```text
mutation 'a reverted dirty overlay is compared by nobody': `expect` 'a REVERTED dirty overlay is STILL a candidate' matched 0 red case(s) — it was caught by something else: ['a REVERTED dirty overlay is STILL a candidate, though nothing changed since the round', ...]
mutation 'repository redirection is left in the environment': `expect` 'git -C means what it says' matched 0 red case(s) — it was caught by something else: ["git -C means what it says: GIT_DIR, GIT_WORK_TREE and GIT_COMMON_DIR are removed: got=[...]"]
```

So claim 6 is not verified; the committed manifests are not measurable by the project’s own mutation contract.

**High**

None found beyond the Blocking mutation-manifest failure.

**Medium**

None found.

**Low**

None found.

**Execution Coverage**

I ran the required suites:

```text
python3 scripts/check-review-recorded.py --self-test      -> 117/117 passed
python3 scripts/codex-review.py --self-test               -> 92/92 passed
python3 scripts/check-plan-code.py --self-test            -> 128/128 passed
python3 scripts/check-ratchet-contract.py --self-test     -> 41/41 passed
python3 scripts/check-fixture-variation.py                -> OK, 506 parameters
python3 scripts/check-selftest-counts.py                  -> 38 script(s) verified
```

Claims 1-5: read and exercised through the self-tests / grep checks; I did not find a live defect in the tail union/intersection, pure-rule extraction, `dirty: null` handling, git redirection stripping, or pass-message/prompt-field change.

Claim 6: verified by execution and failed, as above.

NOT CONVERGED.
