<!-- codex-review: model=gpt-6.1-sol -->

No actionable findings.

- Corrected wording is true. `_staged_root` (`scripts/check-plan-code.py:627–629`) says:
  ```python
  under = [r for r in roots if path.startswith(r + "/")]
  under += [r for r in roots if path == r]
  return max(under, key=len) if under else None
  ```
  Thus `.claude/settings.json/foo` matches there; the canonical-source predicate is stricter.
- The separate comparison rejected all 35 tested moves, drops, tuple duplicates, and cross-set duplications. Repeating an element within `frozenset` produces no semantic change.
- `is_file()` assumes entries exist; it is not independently an existence check. A missing settings file is classified as a directory and fails the identity case. A missing directory retains its classification, but `check-plan-code.py:8208` separately asserts every harness entry exists. All entries currently exist.
- All 16 mutations returned failure through their declared case, verified using in-memory edits.

Requested commands both exited 0:

```text
33/33 passed
canonical sources OK — 3 mechanism(s) described once each (handoff-path, corpus-search, marketplace-inventory)
```

VERDICT: CONVERGED
