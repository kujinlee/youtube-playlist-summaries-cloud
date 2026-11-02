<!-- codex-review: model=gpt-6.1-sol -->

1. **Medium — Git path syntax bypasses the redesigned parser.** `scripts/check-merge-ready.py:514–526`. Executed real Git diffs in a temporary repository:
   - Deleting `.github/workflows/gaté.yml` produces quoted, octal-escaped paths. `diff_files()` returns both paths as `None`; `diff_lines()` returns `{}`; `hold_reasons()` returns `[]`.
   - Changing `return 1` to `return 0` in `scripts/check-space name.py` produces an unquoted filename followed by a tab in `---`/`+++`. The parser retains that tab, so `GATE_CODE` rejects the path and the failure removal is missed.

   Both yield **READY** despite deleting a workflow or weakening a gate. Decode Git’s quoted paths and remove header delimiters correctly.

2. **Medium — binary-format deletion is parsed as an existing file.** `scripts/check-merge-ready.py:513–526`. The parser ignores `deleted file mode` and depends on `+++ /dev/null`, which binary diffs omit. Executed deletion of a workflow marked `-diff` through `.gitattributes`: Git emitted `deleted file mode 100644` and `Binary files … and /dev/null differ`. The parser retained identical old/new paths; `scope_exits()` and `hold_reasons()` returned `[]`, yielding **READY**. Binary representation must preserve deletion status.

3. **Medium — moving a workflow into another gate category disables it without HOLD.** `scripts/check-merge-ready.py:626–629`. Executed a pure rename from `.github/workflows/gate.yml` to `scripts/check-disabled.py`, preserving its check invocation. Git emitted a 100% rename without hunks. `scope_exits()` returned `[]` because both paths satisfy the combined gate predicate; `hold_reasons()` returned `[]`; the verdict was **READY**. The workflow stops running outside `.github/workflows/` regardless of whether its destination matches another gate category. Scope must preserve the source’s execution role.

4. **Low — copies are reported as destructive renames.** `scripts/check-merge-ready.py:513–522`, `:628–629`. Fed a real `git diff -C --find-copies-harder` copying `.github/workflows/gate.yml` to `docs/gate.yml`. The original workflow remained intact, but HOLD claimed it was “renamed … so nothing runs it as a gate any more.” This affects the parser’s stated interface; `main()` currently requests `-M`, so the demonstrated copy representation is outside its normal invocation.

Executed verification:

- Required self-test: **138/138 passed**.
- All **45 mutations**, including the 11 from r1, independently failed every named expected case over a green control.
- Historical replay reproduced **8/40** holds: #398, #387, #386, #382, #381, #367, #366, #360.
- Tested mode-only sections, added-only hunks, newline markers, hunk content beginning `---`/`+++`, edited renames, deleted settings, and multiple files including a hunkless section. Those probes exposed no additional findings.
- Old-side distance and comment filtering behaved consistently with their stated bounds. The dashboard’s eight-hold claim reproduces, but its deleted/out-of-scope gate claim exceeds the implementation demonstrated above.

No review file was written; the working tree remains clean.

VERDICT: NOT CONVERGED
