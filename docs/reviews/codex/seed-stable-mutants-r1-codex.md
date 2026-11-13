<!-- codex-review: model=gpt-6.1-sol -->

No findings on HEAD `3f0d8461`.

- Both self-tests pass: **119/119** and **60/60**.
- The new tied-name case kills its mutation at seeds **0, 1, 2, 42, 266, 312, 342, 449, 599**. Singleton sets fix insertion order to `c, b, a`, independent of hash seed.
- The new completion-order case kills its mutation in **8/8 repeated runs**. Reversing the submitted futures fixes the observed order.
- The monkeypatch restores the original function after normal execution and injected exceptions inside both `run_suites` and the patched iterator. Instrumentation confirmed subsequent cases use the original function; no patch leakage occurred.

The seed-varied sweep remains explicitly outside this change in #506. Working tree unchanged; no GitHub actions taken.

VERDICT: CONVERGED
