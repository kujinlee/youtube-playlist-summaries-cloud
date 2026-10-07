<!-- codex-review: model=gpt-5.5 -->

**Findings**

Blocking: local aliases still let the live world earn credit as “constructed.” Classification: **(b) PRE-EXISTING**, but round 2’s `reads_the_live_world` fix did not close it. In [scripts/check-main-drivable.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-main-drivable.py:1001), the live-world check runs before resolving a local name, and the resolved assigned value then falls through as constructed:

```python
if reads_the_live_world(el, set(guard_globals)):
    return False
...
if isinstance(el, ast.Name):
    value = _last_assigned_value(el.id, fn)
...
    return True
```

Concrete fail I ran:

```python
p = str(ROOT);       main([], root=p)      -> ['param']
p = os.getcwd();     main([p])             -> ['argv']
p = Path(__file__);  main([], root=p)      -> ['param']
p = sys.argv[1];     main([], root=p)      -> ['param']
```

The direct forms are refused, but one local assignment restores the false credit. That is the same property failure round 2 claims to fix: the live repo/process state wearing a computed spelling.

High: globals alias lifetime still misses binding forms, so a rebound `g` can still be credited as `globals()`. Classification: **(b) PRE-EXISTING**; round 2 fixed several spellings but not the class. The new lifetime scan handles only selected targets in [scripts/check-main-drivable.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-main-drivable.py:535):

```python
if isinstance(node, ast.NamedExpr) and isinstance(node.target, ast.Name):
...
if isinstance(node, (ast.For, ast.AsyncFor)) and isinstance(node.target, ast.Name):
...
if isinstance(node, ast.withitem) and isinstance(node.optional_vars, ast.Name):
```

Concrete fail I ran: each classified as `['rebind']`, although `g` no longer names module globals at the write:

```python
g = globals(); import os as g; g["X"] = 2
g = globals(); from pathlib import Path as g; g["X"] = 2
g = globals(); for (g,) in [({},)]: pass; g["X"] = 2
g = globals(); [(0) for (g,) in [({},)]]; g["X"] = 2
g = globals(); with cm() as (g,): pass; g["X"] = 2
```

Medium: `LIVE_WORLD_READERS` causes lost credit for case-built locals named like live readers. Classification: **(a) INTRODUCED BY A ROUND-2 FIX**. [scripts/check-main-drivable.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-main-drivable.py:157) adds names such as `cwd`, `home`, and `argv`, and [scripts/check-main-drivable.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-main-drivable.py:973) rejects any expression whose leaves include them:

```python
LIVE_WORLD_READERS = {"getcwd", "getenv", "environ", "cwd", "home", ...}
...
return bool(attrs & LIVE_WORLD_READERS) or bool(names & LIVE_WORLD_READERS)
```

Concrete fail I ran:

```python
home = tempfile.mkdtemp(); main([], root=home)  -> []
cwd = tempfile.mkdtemp();  main([], root=cwd)   -> []
argv = tempfile.mkdtemp(); main([], root=argv)  -> []
td = tempfile.mkdtemp();   main([], root=td)    -> ['param']
```

This is the safe direction, but it is still a round-2 regression in the “built world now refused” half the prompt asked to attack.

Low: the HEAD commit claim “TWELVE existing anchors were ORPHANED” does not re-derive from the committed manifest. Classification: **(a) INTRODUCED BY A ROUND-2 FIX**. Comparing `HEAD^:scripts/mutations/check-main-drivable.json` against the current script, I found 40 old edit anchors and **6** whose `find` text is absent, not 12. The six old entries are manifest entries 1, 22, 27, 28, 29, and 35. This is a claim accuracy defect, not a gate defect.

**Checks Run**

Executed:
`git log --oneline master..HEAD`; `git show HEAD`; both round-2 reviews; ADR-0014; `python3 scripts/check-main-drivable.py --report`; `python3 scripts/check-main-drivable.py --self-test`; `python3 ~/.claude/projects/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/tools/partial-sweep.py scripts/check-main-drivable.py`; synthetic `classify()` probes; credited-call-site audit for all 10 compliant guards; pinned-set call audit for all 27 pinned guards; dying-case search over indexing/`[-1]`/`next()`/raise-prone self-test sites; manifest/claim re-derivation.

Observed:
`--report` says 44 guards, 37 with `main`, 10 compliant, 27 pinned. Self-test is `171/171 passed`. Partial sweep covered 61 entries; all went red via the named case, with green control and after-control. The 10 credited guards all have reachable credited call sites; I did not find a current false-green guard. The 27 pinned guards all have zero reachable suite calls to `main()` under the current detector; I did not find an actually compliant pinned guard. Worktree unchanged except the two pre-existing untracked PDFs.

Only read:
I read but did not independently re-run full repo-wide `--mutate .`.

**Verdict**

NOT CONVERGED.

Per-finding classification: Blocking (b), High (b), Medium (a), Low (a).
