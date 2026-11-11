<!-- codex-review: model=gpt-6.1-sol -->

**F1 — High — exception formatting escapes the fail-closed boundary**

**Locations:** `scripts/check-merge-ready.py:487`, `:935`, `:1028–1029`.

The handlers interpolate `{exc}` outside their protected `try`. That calls sibling-defined `__str__` without a fail-closed wrapper.

**Concrete input:** add this exception to either sibling:

```python
class Broken(Exception):
    def __str__(self):
        raise SystemExit(0)
```

Then raise `Broken()` at module level, or from `exemption_reason(body, marker)` or `pin_display(src)`.

Measured through the real `main()` with its existing fake runner, green gates, and a pin falling **5 → 4**:

| Input | Exit | Verdict |
|---|---:|---|
| Well-behaved dashboard control | 3 | HOLD |
| Dashboard import raises `Broken()` | **0** | **None** |
| Dashboard matcher raises `Broken()` | **0** | **None** |
| Pins reader call raises `Broken()` | **0** | **None** |

This uses synchronous raises only; it requires no global rebinding, process hooks, or surviving side effects.

**Fix-induced:** yes for the new dashboard wrappers; the pins-reader formatting vulnerability already existed at `0eec9d38`. The shared helper carries that vulnerability forward.

Avoid invoking sibling-controlled exception formatting when constructing the replacement error, or protect that formatting too. Add witnesses for both import and call failures.

Other requested checks:

- Both in-process sibling importers use `_import_sibling`. No additional explicit sibling call bypass was found; F1 is an implicit call in error reporting.
- No sibling raise reaching a bare `except Exception` produced a pass value. The escape cross-check preserves an already-failing gate result.
- Failed imports are not cached. Changing `DASHBOARD_GATE` to a distinct path selects another cache entry. Same-path edits remain cached, as before.
- Neither deletion yielded an independent, in-bound production defect.
- **The r5 HOLD triage remains accurate:** `failure_path_removals` against `origin/master` reports the same five merge-ready lines and one plan-code line. Actual pin comparison reports no falls. Those six rewrites remain false HOLDs.

Foreground self-tests passed: **237/237** merge-ready; **281/281** plan-code.

**NOT CONVERGED.**
