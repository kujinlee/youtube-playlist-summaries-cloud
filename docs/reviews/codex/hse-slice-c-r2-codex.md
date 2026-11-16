<!-- codex-review: model=gpt-6.1-sol -->

- **MAJOR — scripts/check-shipping-sets.py:374:** Keyword module loads escape the new AST reader despite its stated coverage. Concrete input: mapped and declared `scripts/a.py` contains `import importlib; importlib.import_module(name='secret')`; `scripts/secret.py` exists but is omitted. Observed: `exec_edges()` returns an empty set, map gaps are empty, and closure returns rc 0, `0 gaps`.

- **MAJOR — scripts/check-shipping-sets.py:278:** Constant f-strings with conversions are silently discarded although the docstring claims f-string paths are followed. Concrete input: `NAME='secret'; runpy.run_path(f'{NAME!s}.py')` in shipped `scripts/a.py`, with sibling `secret.py` present only in the repository. Observed: no executable edge; closure returns rc 0, `0 gaps`.

- **MAJOR — scripts/check-shipping-sets.py:879:** Optionality is taken on trust and can hide a required dependency. Concrete input: shipped `a.py` unconditionally calls `runpy.run_path('scripts/secret.py')`; the map waives that edge with reason `"guarded by existence"`, while omitting `secret.py`. Observed: closure returns rc 0, `0 gaps`, claiming “loaded only when present”; executing the materialized script returns rc 1, `FileNotFoundError`. The docstring acknowledges this trust boundary, but the waiver still permits a broken package to pass.

- **MAJOR — scripts/check-shipping-sets.py:885:** Waiver validation checks the target globally, losing the source identity. Concrete input: shipped `a.py` has no load; shipped `b.py` loads `scripts/secret.py`; waive both `a.py → secret.py` and `b.py → secret.py`. Observed: closure returns rc 0, `0 gaps`; the nonexistent edge from `a.py` is accepted because `b.py` produced the same `optional:` marker. This contradicts the stated guarantee that a waiver for an edge the file lacks is a gap.

- **MINOR — scripts/check-shipping-sets.py:802:** Malformed file elements escape the promised CANNOT RUN path. Concrete input: append `{}` to the real declaration’s `recall.installed_files`. Observed: CLI exits rc 1 with an uncaught `TypeError: cannot use 'dict' as a set element (unhashable type: 'dict')`, instead of CANNOT RUN, rc 2.

- **MINOR — scripts/check-shipping-sets.py:871:** Reusable-workflow component arithmetic is never checked. Concrete input: change one real `ci-layer` component’s `expected_count` to `999`, leaving its files unchanged. Observed: closure returns rc 0, `0 gaps`, despite the docstring promising refusal when `expected_count` disagrees with files. Requested baseline final lines remain `117/117 self-test cases passed`, `119/119 self-test cases passed`, and `0 gaps` for both map and closure; all four commands return rc 0.

VERDICT: NOT CONVERGED
