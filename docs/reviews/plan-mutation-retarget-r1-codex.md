<!-- codex-review: model=gpt-5.5 -->

**Findings**

1. **Blocking** — Task 1, Step 2, lines 114-129  
   The pasted `run_mutations` self-test cannot pass as written. Its mutation anchor is `"return 1"`, but the fixture contains that string twice: once in `def f()` and once in `_self_test()`’s failure branch. The current engine correctly refuses ambiguous anchors before applying the mutation.  
   Why it matters: Task 1’s “green after extraction” proof fails for the wrong reason, so implementers cannot complete the plan as written.  
   Concrete fix: make the anchor unique, e.g.:
   ```python
   "edits": [["def f():\n    return 1", "def f():\n    return 2"]]
   ```

2. **Blocking** — Task 6, Step 3, lines 879-884  
   The deletion script removes the mechanical blocks, but its final assertion still fails on the real dashboard plan because a prose table still contains `` `<!-- file: ../escape.py -->` ``. Dry run result: parser sees no remaining assembled files or mutation block, but raw substring check still sees `<!-- file:`.  
   Why it matters: Task 6 cannot complete as written even after the regex has done the intended mechanical deletion.  
   Concrete fix: replace the raw substring assertion with anchored/parser-based checks, e.g. run `extract(s)` and assert `not files and not muts`, or use anchored regexes:
   ```python
   assert not re.search(r"^\s*<!--\s*file:", s, re.M)
   assert not re.search(r"^\s*<!--\s*mutations\s*-->\s*$", s, re.M)
   ```

**Checks Run**

- `python3 scripts/check-plan-code.py --self-test` → `121/121 passed`
- `python3 scripts/check-plan-code.py docs/superpowers/plans/2026-08-28-project-dashboard-plan.md --compare . --verify-evidence` → `OK — compared + evidence-verified: 2 file(s), 43 mutation(s), 0 survivor(s)`
- Temp copy with only `scripts/`: both delivered self-tests pass.
- Standalone temp prototype of proposed delivered-script mutation path: `43 mutation(s), 0 survivor(s)`.
- Task 6 deletion dry run: removes 2,128 lines, leaves no parser-visible file/mutation blocks, but fails the raw `<!-- file:` assertion above.

**Other Reviewed Points**

No missed `files`/`ev`/closed-over variable in Task 1’s extraction table; `ok` being local is fine if returned, and `check()` preserves report ordering. Task 3’s `run_suite(d, "scripts/gen-dashboard.py")` works after copying `scripts/`. Task 4’s exact count catches both fewer and more entries for declared targets; the “unknown target” branch is reachable if a new `scripts/<stem>.py` and manifest are added. Task 2’s round trip is safe for the current JSON-derived data; there are no duplicate `(file, name)` pairs.

NOT CONVERGED — the plan has two paste-time blockers that would stop implementation despite the core retargeting approach checking out.
