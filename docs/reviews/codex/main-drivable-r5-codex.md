<!-- codex-review: model=gpt-5.5 -->

**Findings**

Medium: `_constructed_at_call_sites()` has an unexercised keyword-call branch; deleting it leaves the suite green.  
Observation that makes it fail: `_drive(root=tempfile.mkdtemp())` currently classifies as `param`, but replacing the keyword fallback with `None` leaves `222/222 passed`. That means the line can rot without a case noticing.  
Quote: [scripts/check-main-drivable.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-main-drivable.py:1190): `arg = sub.args[idx] if len(sub.args) > idx else next(`

Medium: `computed_argv()`’s non-list precondition still dies rather than reports when severed.  
Observation that makes it fail: removing the `List`/`Tuple` guard raises `AttributeError: 'Name' object has no attribute 'elts'` after 36 `[ok]` lines and zero `[FAIL]` lines. The mutation is red, but unattributed.  
Quote: [scripts/check-main-drivable.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-main-drivable.py:1153): `if not isinstance(expr, (ast.List, ast.Tuple)):`

**Checks Run**

`git rev-parse HEAD` → `b17a34f6`; working tree unchanged except the two pre-existing untracked PDFs.

`python3 scripts/check-main-drivable.py --self-test` → `222/222 passed`.

`python3 scripts/check-main-drivable.py --report` → 44 guards, 7 without `main`, 37 in population, 10 compliant, 27 pinned.

Credited call-site census: opened the 10 compliant guards’ credited sites. I found no current false-green among them.

Pinned debt check: `assess()` reports `problems []`, `pins complying []`, `un-pinned debt []`. I found no compliant guard among the 27 pins.

`partial-sweep.py scripts/check-main-drivable.py` → green control, all `81/81` entries red via their named case, green after-control, 17.0 min.

Severance in archive copies: 11/12 severed rules went red by named `[FAIL]`; `computed_argv_no_list_guard` died with zero `[FAIL]`, which is filed above.

Claims vs code: confirmed `222` self-test cases, `81` manifest entries, `check-plan-code.py` expects `81`, total declared mutations `1259`, and `_last_assigned_value` is gone from current code. I validated the r4 falsifier cells directly, but did not reconstruct the entire old 20×6 matrix or independently run “48 of 48 CI guards”.

Explicit falsifier answer: I did **not** land the grammar-category falsifier again. The fixed `_expr_children` sees lambda defaults, comprehension machinery, keyword values, and the adversarial wrapper cells I probed. The surviving issues are an untested helper keyword branch and an unattributed crash mutation, not “add a node kind to the world traversal list.”

NOT CONVERGED.
