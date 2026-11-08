<!-- codex-review: model=gpt-6.1-sol -->

### R1-F1 — Medium — Refused blocks change an initially unset tempfile cache

**File:line:** `scripts/fixture_git.py:103–116`

**Scenario:** With `tempfile.tempdir is None`, entering `isolated(GIT_DIR="x")` initializes Python’s temp-directory cache while creating `scratch`. Validation then raises before reaching the inner `finally` that restores the cache. The outer `finally` removes the directory but leaves `tempfile.tempdir` changed. This violates exact restoration and can make later `TMPDIR` changes ineffective.

**Repro:**

```python
import tempfile
from fixture_git import isolated

tempfile.tempdir = None
try:
    with isolated(GIT_DIR="x"):
        pass
except ValueError:
    pass

assert tempfile.tempdir is None  # FAILS
```

Reproduced with `TMPDIR` unset: it remained unset, but `tempfile.tempdir` became the host temp path. Normal exits and nested blocks restored correctly.

**Fix:** Restore `tempfile.tempdir` in the outermost `finally`, covering scratch creation and validation failures. Add a refusal case starting with `tempfile.tempdir = None`; current tests start with an initialized cache.

Validation completed: `fixture_git` **52/52**, `check-compaction-boundary` **106/106**, `check-selftest-counts` **60/60**, `check-run-hook` **79/79**, and `check-fixture-git-isolation` **141/141**. Removing cleanup in a temporary copy produced exit **1**, including failure of the named leak guard. The historical 95-suite measurement was not independently repeated.

VERDICT: NOT CONVERGED
