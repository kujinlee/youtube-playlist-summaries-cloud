<!-- codex-review: model=gpt-5.5 -->

**Blocking**

None.

**High**

None.

**Medium**

None.

**Low**

None.

Verified from an isolated copy at `/tmp/review15.UuDcNC/subject`; the copied tree had no inherited `.git`, then I initialized a local-only repo there for scenarios.

Requested checks:

```text
check-review-recorded.py --self-test: 122/122 passed
codex-review.py --self-test: 85/85 passed
check-plan-code.py --self-test: 128/128 passed
check-ratchet-contract.py --self-test: 41/41 passed
check-fixture-variation.py: fixture variation OK — 513 parameter(s), 50 file(s)
check-selftest-counts.py: 38 script(s) declare a count, every one verified
check-review-rounds.py: 234 parsed, 0 silent gaps
```

`diff_argv` is the only path-producing `git diff --name-only` builder in `scripts/check-review-recorded.py`: `_changed_since` uses it at `scripts/check-review-recorded.py:505`, `changed_paths` at `:663`, and `added_paths` at `:722`. `--diff-filter=A` appears only through `diff_argv(..., added_only=True)` at `:722-723`.

Rename repair scenarios, verified by execution:

```text
guarded file renamed to prose:
git diff --name-status --no-renames -> A docs/x.ts, D lib/x.ts
git diff --name-status              -> R055 lib/x.ts docs/x.ts
gate -> FAILED ... lib/x.ts, rc=1

review doc renamed into docs/reviews:
git diff --name-status              -> R100 docs/old-r1-codex.md docs/reviews/codex/subject-r1-codex.md
git diff --name-only --diff-filter=A              -> empty
git diff --name-only --no-renames --diff-filter=A -> docs/reviews/codex/subject-r1-codex.md
gate -> ok review recorded + REVIEW GAP named, rc=0
```

Third directions checked: copy-only to prose stayed `rc=0` because no guarded path changed; rename+mode, rename+edit, and case-only guarded rename all failed closed with the guarded source/destination named. No defect found there.

Mutation/count checks:

```text
EXPECTED_MUTATIONS: 44 files, sum 622
manifest files:     44 files, sum 622
mismatches: []
check-review-recorded manifest: 36
codex-review manifest: 12
```

Targeted mutation run for the r14 entries and adjacent `case_line` entries:

```text
selected 4
ok True
survivors []
killed 4 attributed 4 total 4
```

The deliberately garbled `case_line` expect is honest: parsing the mutant line

```text
[FAIL] the line keeps the canonical shape the harness documents: got=False
```

returns exactly:

```text
['the line keeps the canonical shape the harness documents: got=False']
```

I started an optional full `check-plan-code.py --mutate .` sweep, but stopped it at 234/622 because it was not part of the requested command list and the targeted new-entry run answered the r14 repair question directly. I am not treating that interrupted sweep as evidence.

CONVERGED
