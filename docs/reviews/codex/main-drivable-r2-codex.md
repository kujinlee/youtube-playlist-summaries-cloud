<!-- codex-review: model=gpt-5.5 -->

**Findings**

High: `suite_entries()` still credits `_self_test` / `self_test` even when `main --self-test` cannot reach them. The fold claims reachability is based on `main`’s dispatch branch, but the unconditional fallback remains:

[scripts/check-main-drivable.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-main-drivable.py:320)
```python
if isinstance(node, ast.If) and _mentions_self_test(node.test):
...
out |= {n for n in SUITE_ENTRY_NAMES if n in funcs}
```

Concrete fail: this synthetic guard classifies as `argv` with one suite call even though `main()` has no `--self-test` branch, so the suite cannot observe `main` wiring through the shipped entry point:

```python
ROOT=1
def main(argv=None):
    return ROOT
def _self_test():
    case('x', main([str(tmp)]), 0)
```

Measured: `routes=['argv']`, `entries=['_self_test']`, `reachable=['_self_test', 'main']`.

High: the `subproc` route treats the mere presence of `input=`, `env=`, `cwd=`, or `stdin=` as a constructed world. The doc says the subprocess must run over a world the case built, but the implementation does not inspect the keyword value:

[scripts/check-main-drivable.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-main-drivable.py:711)
```python
built = any(kw.arg in WORLD_KWARGS for kw in node.keywords) or any(
```

Concrete fail: both of these classify as `subproc`, although neither passes a case-built world:

```python
subprocess.run([sys.executable, __file__], stdin=sys.stdin)
subprocess.run([sys.executable, __file__], cwd=ROOT)
```

That admits a guard that merely re-runs itself as part of normal work over the live process state.

High: `globals()` alias tracking has no lifetime, so a rebound alias still writes as if it were `globals()`. The alias set records every assignment target bound to `globals()` and never kills it:

[scripts/check-main-drivable.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-main-drivable.py:451)
```python
for node in ast.walk(fn):
    if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
        f = node.value.func
        if isinstance(f, ast.Name) and f.id == "globals" and not node.value.args:
            out |= {n.id for tgt in node.targets for n in ast.walk(tgt)
```

Concrete fail:

```python
g = globals()
g = {}
g["X"] = 2
case("x", main([]), 0)
```

Measured: `routes=['rebind']`. That is a false credit: the write is to a local dict, not the module globals `main` reads.

Medium: alias tracking misses imported spellings of `globals()`. The same quoted matcher only accepts `f.id == "globals"`, so both `from builtins import globals as gl; g = gl()` and `gl()["X"] = 2` classify with no `rebind` route. That is a lost-credit direction, not a false green, but it is exactly the spelling family the round-2 prompt asked to attack.

**Checks Run**

Executed:

`python3 scripts/check-main-drivable.py --self-test` -> `134/134 passed`.

`python3 scripts/check-main-drivable.py --report` -> 44 guards, 37 in population, 10 compliant, 27 pinned; routes param 3, argv 3, rebind 8, subproc 1.

`python3 ~/.claude/projects/-Users-kujinlee-code-agentic-ai-docs-youtube-playlist-summaries-cloud/tools/partial-sweep.py scripts/check-main-drivable.py` -> all 40 mutations red via named cases; after-control green; 1.8 min.

Credited live call sites: inspected all 10 compliant guards. I did not find a current false-compliant guard among them.

Pinned guards: re-derived all 27 pinned names; all have zero suite calls to `main()` under the current detector.

Claims: re-derived 134 cases, 40 mutations, 10 of 37, route split, 27 debt, 163 lines, and `__main__` exclusion 0 of 44 by monkey-patching the old skip back in. Severed five fold rules in a temp copy; four went red, but the suite-name fallback issue above remains a live unasserted negative shape.

Working tree: left unchanged; only pre-existing untracked PDFs remain.

NOT CONVERGED. Executed against the report, mutation sweep, credited call sites, pinned set, severance, and claims-vs-code questions; read the ADR and both round-1 reviews. Full repo-wide `--mutate .` was not run.
