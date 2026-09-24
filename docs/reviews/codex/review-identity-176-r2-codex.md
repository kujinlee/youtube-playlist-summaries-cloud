<!-- codex-review: model=gpt-5.5 -->

**Subject:** `4e60c5d8` on `review-identity-176`, base `origin/master` = `b2e10e39`.

**Verdict: NOT CONVERGED** — 1 High.

**Verified Green**
`python3 scripts/check-review-rounds.py --self-test ; printf 'rc=%s\n' $?`
Output: `61/61 self-test cases passed`, `rc=0`.

`python3 scripts/codex-review.py --self-test ; printf 'rc=%s\n' $?`
Output: `168/168 passed`, `rc=0`.

`python3 scripts/check-plan-code.py --self-test ; printf 'rc=%s\n' $?`
Output: `131/131 passed`, `rc=0`.

Read-only anchor binding audit, using `src.count(find) == 1`:
Output: `entries 1023 edits 1031 problems 0`.

Corpus re-derived by loading JSON:
Output: `total 185`; `schema Counter({'2': 99, '1': 85, '3': 1})`; `gate_ran Counter({'True': 180, 'False': 5})`; `bad [] count 0`.

Counts re-derived by loading manifests and `EXPECTED_MUTATIONS`:
Output: `scripts/check-review-rounds.py 24`, `scripts/codex-review.py 45`, `scripts/check-plan-code.py 77`, `sum 1023`.

**Findings**

**High — present negative `schema` is accepted as pre-cutover, so malformed testimony can still switch the verdict join off.**

Premise: the fold’s L1 says malformed `schema` is CANNOT RUN, and centralizes that in `schema_of`. But the helper only rejects bools and non-ints; a present negative int is accepted as a version. That is not an absent pre-schema record. It is malformed testimony with a schema field.

Code:
`scripts/check-review-rounds.py:196:     if "schema" not in rec:`
`scripts/check-review-rounds.py:197:         return 0`
`scripts/check-review-rounds.py:199:     if isinstance(v, bool) or not isinstance(v, int):`
`scripts/check-review-rounds.py:200:         return None`
`scripts/check-review-rounds.py:201:     return v`
`scripts/check-review-rounds.py:278:         if (schema_of(rec) or 0) < TRUSTED_SCHEMA:`
`scripts/check-review-rounds.py:330:         if schema_of(rec) is None:`

Measurement:
```text
records [('neg.json', {'schema': -1, 'gate_ran': True, 'review': 'missing-r1-codex.md', 'reason': 'r'})]
bad []
era {'total': 1, 'refused': 0, 'pre_cutover': 1, 'checked': 0}
problems []
```

Severity: High. A malformed verdict with `schema: -1`, `gate_ran: true`, and a missing review is read as legacy/pre-cutover instead of unreadable, so the exact join contradiction this change protects can be silenced.

Fix: treat present schema values below the first real schema as malformed. Keep absent schema as `0`, but make present `0` / negative return `None`, and add self-test plus manifest coverage for `-1`.

Type: structural.

**Could Not Measure**

I did not run `python3 scripts/check-plan-code.py --mutate .`, per the brief. Therefore the full mutation sweep is not independently verified here.

`python3 scripts/check-review-rounds.py` is currently red because this requested Codex half is not filed:
```text
FAILED — 1 review round(s) with one half and no stated reason:
  ✗ review-identity-176 round 2: only claude — codex neither ran nor recorded a `REVIEW GAP:` line
rc=1
```
I am not counting that as a subject defect because the prompt explicitly required this review as the final message and no file write.
