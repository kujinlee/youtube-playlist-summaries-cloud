<!-- codex-review: model=gpt-5.5 -->

**Findings**

Blocking: `_bound_values()` is scope- and branch-insensitive, so a case can be credited for a built world that `main()` never receives.  
Observation that makes it fail: a wired guard with `if True: p = ROOT; else: p = tempfile.mkdtemp(); main([], root=p)` classifies as `param`, even though runtime passes the live `ROOT`. Same for `p = ROOT` followed by a nested function assigning `p = tempfile.mkdtemp()`.  
Quote: [scripts/check-main-drivable.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-main-drivable.py:903): `for node in ast.walk(fn) if fn is not None else ():` and [scripts/check-main-drivable.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-main-drivable.py:927): `_last_assigned_value`.

High: the subprocess extra-argv path dies with `NameError`.  
Observation that makes it fail: a reachable self-subprocess like `subprocess.run([sys.executable, __file__, p])` where `p = tempfile.mkdtemp()` raises `NameError: name 'guard_world' is not defined` instead of returning a verdict.  
Quote: [scripts/check-main-drivable.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-main-drivable.py:837): `_element_is_constructed(el, fn, tree, 0, guard_world)`.

High: a name bound to a computed literal can become `BUILT`, so a flag vector can earn `argv`.  
Observation that makes it fail: `flag = "--" + "self-test"; main([flag])` classifies as `argv`. That is still a computed flag over the live world, not a constructed world.  
Quote: [scripts/check-main-drivable.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-main-drivable.py:1003): `return INERT if isinstance(bound, (ast.Constant, ast.Name)) else BUILT`.

Medium: some built worlds are refused because provenance does not reach non-enumerated binding/call-site forms.  
Observation that makes it fail: `kw = {"root": tempfile.mkdtemp()}; main([], **kw)` is `DEBT`; `match tempfile.mkdtemp(): case p: main([], root=p)` is `DEBT`; `functools.partial(main, root=tempfile.mkdtemp())([])` has zero suite calls.  
Quote: [scripts/check-main-drivable.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-main-drivable.py:886): `kw.arg in declared_world`; [scripts/check-main-drivable.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-main-drivable.py:915) and :920 show only `with` and `for` binding forms added.

**Checks Run**

`--report`: 44 guards, 37 with `main`, 10 compliant, 27 pinned. I did not find a current false-green among the 10 credited guards, and did not find a compliant guard among the 27 pins.

`--self-test`: `199/199 passed`.

`partial-sweep.py scripts/check-main-drivable.py`: 71/71 went red via the named case; after-control green; 7.2 min.

Severed eight rewrite-added rules in a disposable archive copy; all eight went red. No green severance reproduced.

Manifest count re-derived: repo total 1249 entries; `check-main-drivable.json` has 71 entries.

Working tree left unchanged except the two pre-existing untracked PDFs.

NOT CONVERGED.

Explicit falsifier answer: I did not find a defect whose fix is “add a node kind to a list inside `world_class`.” The defects above are provenance, scope/control-flow, call-site, and traversal/name errors. So this round does not trigger the pre-committed falsifier as stated.
