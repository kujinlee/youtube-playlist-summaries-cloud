<!-- codex-review: model=gpt-5.5 -->

**Blocking**

None.

**High**

None.

**Medium**

None.

**Low**

`prose_exceptions_cover()` treats a workflow glob as “covered” when `CODE_UNDER_PROSE` is only a strict subset of that glob, so a future broadening like `docs/superpowers/specs/**` would not report uncovered `docs/` gate code; `scripts/check-review-recorded.py:224`.

Failure scenario: a later workflow change broadens the schema gate path filter to `docs/superpowers/specs/**` while adding `docs/superpowers/specs/new-gate/run.sh`; CI now guards that new docs subtree, but the classifier still says the new gate file is prose and the anti-drift falsifier returns `[]`.

Verified by execution:

```text
['docs/superpowers/specs/2026-08-03-stable-blob-addressing/**'] -> []
['docs/superpowers/specs/new-gate/**'] -> ['docs/superpowers/specs/new-gate/**']
['docs/superpowers/specs/**'] -> []
['docs/**'] -> []
hypothetical new gate file guarded? False
hypothetical current broad-glob uncovered file guarded? False
```

This is not live against today’s workflow. With the actual quoted globs from `.github/workflows/schema-gates.yml`, the helper returns `[]` correctly:

```text
['docs/superpowers/specs/2026-08-03-stable-blob-addressing/**',
 'docs/superpowers/specs/m4/**',
 'docs/superpowers/specs/2026-08-03-stable-blob-addressing/**',
 'docs/superpowers/specs/m4/**']
[]
```

**What I Ran**

All commands ran from isolated copies under `/tmp/rrt-r16-review`; the first copy was made with `.git` excluded, then initialized as a local-only repo. I did not touch `docs/reviews/`.

```text
python3 scripts/check-review-recorded.py --self-test   -> 134/134 passed
python3 scripts/codex-review.py --self-test            -> 85/85 passed
python3 scripts/check-plan-code.py --self-test         -> 128/128 passed
python3 scripts/check-ratchet-contract.py --self-test  -> self-test: 41/41 passed
python3 scripts/check-fixture-variation.py             -> fixture variation OK
python3 scripts/check-selftest-counts.py               -> 38 script(s) declare a count, every one verified
python3 scripts/check-review-rounds.py                 -> 235 parsed, 0 silent gaps
python3 scripts/check-plan-code.py --mutate .           -> 626 killed, 626 attributed, 0 survivor(s)
```

I re-derived the tracked classifier population from the real worktree’s tracked file list:

```text
tracked 2213
prose 1347
prose_non_md 101
96 docs/reviews/verdicts/*.json
1 .gitignore
1 docs/architecture.html
1 docs/available-skills-print.css
1 docs/available-skills-print.tex
1 docs/available-skills.pdf
```

I verified the r15 repair end to end: a committed edit to `docs/superpowers/specs/2026-08-03-stable-blob-addressing/mutate-schema.py` now fails closed with rc=1 and names that guarded path; a new `.md` under the exception directory remains prose with rc=0; missing `--pr-body-file` returns CANNOT RUN rc=2; empty/whitespace `NO-REVIEW:` does not waive `second_question`.

CONVERGED.
