<!-- codex-review: model=gpt-6.1-sol -->

1. **[P2] Anchors ending in a newline falsely cover the following decision line.** In `scripts/check-diff-coverage.py:143`, `a.count("\n") + 1` includes the next line even when the anchor ends before its text. Executed fixture: anchor `"PIN = 1\n"`, then change the following `if good:` to `if bad:`. Result: exit 0, **“every one is reached.”** This also reproduces against real manifests: changing `scripts/check-plan-code.py:195` from `return env` to `return {}` produces zero warnings. There are **230** trailing-newline anchors in the delivered manifests. Calculate the final covered line from the anchor’s last included character.

2. **[P2] Multiline decisions can change without warning.** At `scripts/check-diff-coverage.py:122–130`, `return`, `raise`, `assert`, `except`, and `exit` record only their starting line; `if`/`while` record only their test span. Committed fixtures changing solely:
   - a multiline return or assertion predicate;
   - `ValueError` to `TypeError` in a multiline exception handler;
   - an exit status from 0 to 1;
   - multiline `if (` to `while (`;

   all returned exit 0 with **“every one is reached,”** despite having no anchor touching the edit. Include decision headers and their relevant expression spans, while excluding unrelated statement bodies.

3. **[P2] Filenames containing spaces silently disappear from coverage.** `scripts/check-diff-coverage.py:70–71` treats the complete `+++` payload as the filename. Git emits `+++ b/scripts/a b.py<TAB>`; the retained tab prevents matching `scripts/a b.py` in the manifest map. A committed `if good:` → `if bad:` fixture reported **zero manifested scripts changed** and “every one is reached.” Tab-containing filenames also fail because Git quotes and escapes them. Parse Git paths correctly and add real Git fixtures.

4. **[P3] Missing Git violates the documented CANNOT RUN contract.** `scripts/check-diff-coverage.py:165` invokes Git outside exception handling. Executing the checker with an absolute Python path and `PATH=/nonexistent` produced **exit 1 and a `FileNotFoundError` traceback**, rather than exit 2 and CANNOT RUN. The existing “no git” case tests a non-repository directory with Git still installed. Catch process-launch failures and test executable absence explicitly.

5. **[P3] The dashboard overstates what a warning establishes.** `docs/dashboard-entries.md:17755–17756` says warned lines are ones “where none of the project's planted-fault tests would notice if that line were undone.” The implementation measures anchor reach, not test sensitivity. Executed counterexample: an unanchored changed `return 1` warns, its assertion passes, and reverting only that return makes the assertion fail. Describe missing mutation anchors instead of claiming tests cannot notice the change.

Validation performed entirely in temporary copies:

- **23/23 self-tests passed; all 10 mutations applied uniquely and failed their named cases.**
- **211/211 merge-ready self-tests passed.** Live `--pr 409` executions on base and branch both returned CANNOT RUN because GitHub reported UNKNOWN mergeability; this does **not** establish READY-verdict equivalence.
- Rename-with-edit, re-indentation, delete/re-add, missing final newline, multiline condition operands, and cross-file anchor isolation behaved as expected.
- Shallow history without a merge base and missing origin/base returned exit 2.
- Ternaries, comprehensions, decorators, and match statements were omitted; nested functions within `self_test` were exempt, consistent with the documented exclusions.
- Binary and syntactically invalid Python fixtures returned a clean zero rather than identifying an unmeasured file.
- CI contains the unconditional self-test, PR-only warning step, full-history checkout, and updated five-step accounting. The advertised 36 warnings on this branch reproduced.

The source repository remained unchanged.

VERDICT: NOT CONVERGED
