<!-- codex-review: model=gpt-6.1-sol -->

No Blocking or Major regression reproduced in the current CI or importer paths.

- **Minor — cache reuse is untested**, `scripts/check-main-drivable.py:333`. Replacing `hit = memo.get(key)` with `hit = None` survives **441/441**, taking 85.4 seconds on Python 3.12. Two calls on the same AST invoke the builder twice. Add a builder-call-count assertion so losing the speedup fails deterministically.

- **Minor — exact name discrimination has a coverage gap**, `scripts/check-main-drivable.py:4493`. Changing non-AST keys to `a.lower()` also survives **441/441**. Concrete input: `def f(): p = first(); P = second()`. After `_bound_values("p", fn)`, the mutant answers `_bound_values("P", fn)` with `first()`.

- **Minor — unbounded retention**, `scripts/check-main-drivable.py:342`. Repeating `note_globals_imports(ast.parse("from builtins import globals as g"))` and discarding each tree retained approximately **7.5 MB after 5,000 trees**, growing to **30.1 MB after 20,000**, even after collection. A long-running importer grows without bound; provide eviction or an analysis-scoped cache lifecycle.

- **Minor — immutable-input precondition is undocumented**, `scripts/check-main-drivable.py:333`. Parse `from builtins import globals as g`, call `note_globals_imports(t)`, then change `t.body[0].names[0].asname` to `"h"`. The cached answer remains `{"g"}` while `.__wrapped__(t)` returns `{"h"}`. No current caller transforms or annotates the trees, so this is an API limitation rather than a reproduced CI regression.

- **Minor — lifetime test depends on ambient allocation behavior**, `scripts/check-main-drivable.py:4487`. With instrumentation retaining every `ast.parse` result, changing entries to `(None, out)` survives **441/441**: addresses never become reusable. Add a direct lifetime assertion rather than relying solely on allocator churn.

Both requested commands completed: **441/441 self-tests passed**; the mutation diagnostic reported **189 killed, 189 attributed, zero registered survivors**. The additional surviving mutants above are outside that manifest.

Local Python **3.12** measurements support the speedup: suite **83.5 → 12.0 seconds**; live run **75.7 → 5.7 seconds**, with peak RSS **106 → 127 MB**. These were local measurements, not CI-runner timings. The importer’s live check and **141/141** self-tests passed. No current cache-key omission, missing argument retention, or frozen-result mutation was found.

**NOT CONVERGED**
