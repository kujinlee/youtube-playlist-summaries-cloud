<!-- codex-review: model=gpt-6.1-sol -->

1. **Low — Round 3’s inaccurate LIMITS count remains.** `docs/backlog.md:355` still says: “Its docstring’s LIMITS name the six shapes it does not stop.” The docstring now names those six round-2 categories **plus four round-3 categories** at `scripts/check-fixture-git-isolation.py:77–86`. Round 3 explicitly identified this sentence as inaccurate.

   **Reproduction:** inspect `git show 8724f7f9:docs/backlog.md` at line 355 and compare its quoted count with the expanded LIMITS section. Remove the count or update the account.

The remaining requested checks pass:

- **Prose-only:** three changed files; the sole changed Python file has an identical AST after docstrings are removed. No executable behavior, rule, or case changed.
- LIMITS names every escape shape from both round-3 reviews. Detector precision names the literal-cwd miss, false refusal, starred argv, shell-option/quoting misses, and all four missing `GIT_SUITES`.
- Rule 3’s narrowed description matches its reach. The corrected `subject_status` account reproduces: **16/17 baseline, 12/17 with victim `GIT_DIR`**.
- Backlog **#380 and #382 each have a concrete FAILS-IF**.
- All **80** derived `scripts/*.py --self-test` children ran under `fixture_git.isolated()`’s environment: **79 passed**, with only the pre-existing `subject_status` failure.
- All **2,303 mutation entries** load without errors; every anchor resolves exactly once.
- Guard: **84/84 cases**. Mutations: **45/45 killed and attributed**, zero survivors. Live guard: **16 suites, zero exemptions, 84 files read**.

Evidence: `/tmp/fixture-r4.YHADK6/`, including `run.py`, `results.json`, suite logs, `subject-planted.log`, and `mutation-r4.log`. Executions used the temporary clone; the repository remains unedited and clean.

VERDICT: NOT CONVERGED
