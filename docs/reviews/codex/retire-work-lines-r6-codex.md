<!-- codex-review: model=gpt-6.1-sol -->

No findings in the scoped diff.

- Every serve/index `resolve()` uses `resolve_or_none()`. Remaining direct calls are startup path discovery and test assertions.
- Real symlink loops reach the same refused/403/unlisted state under Python 3.12 and 3.14.
- The patched RuntimeError case is a real falsifier: removing RuntimeError handling kills its named test.
- Python 3.12: serve suite **228/228**, mutation harness self-test **246/246**.
- Serve mutations: **62/62 killed and correctly attributed**, zero survivors or orphaned anchors.
- Leak scan: **0 hits**.
- Repository unchanged.

VERDICT: CONVERGED
