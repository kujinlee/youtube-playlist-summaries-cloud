<!-- codex-review: model=gpt-5.5 -->

**Blocking**
None found as a live false green on a guard on disk.

**High**
[ scripts/check-main-drivable.py:867](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-main-drivable.py:867) treats every `ast.Name` as a read, including `Store` names introduced by `NamedExpr`. That makes a walrus restore look like a fresh substitution, so a guard can earn `REBIND` after putting the saved global back.

Concrete falsifier:

```python
ROOT = 1

def main(argv=None):
    if '--self-test' in argv:
        return _self_test()
    return ROOT

def _self_test():
    _sv = ROOT
    globals()['ROOT'] = 2
    globals()['ROOT'] = (_tmp := _sv)
    case('x', main([]), 0)
```

Command/output:

```text
routes simple walrus restore: frozenset({'rebind'})
free_names simple walrus: ['_sv', '_tmp']
routes comp walrus restore: frozenset({'rebind'})
free_names comp walrus: ['_sv', '_tmp']
```

Expected verdict: no route. The value is `_sv`; `_tmp` is bound by the expression, not read from the enclosing case. Blast radius: latent false green. I did not find this exact shape in live guards.

**Medium**
[ scripts/check-main-drivable.py:1434](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-main-drivable.py:1434) uses `world_class(base) is INERT` as “relative base” for `BASE_RELATIVE_PATH_OPS`. But absolute string literals are also `INERT`, so an absolute fixture path passed through a normalizer is misclassified as live cwd.

Concrete falsifier:

```python
case('x', main([], root=os.path.abspath('/tmp/fixture')), 0)
```

Command/output:

```text
scripts/check-absolute-normalized.py DEBT [] 1 True None
world_class abspath abs: live
world_class abspath rel: live
world_class Path abs: built
```

Expected verdict: `param`. `os.path.abspath('/tmp/fixture')` does not read cwd; the base is already absolute. Blast radius: latent false debt / masked paid debt. I found no live guard spelling this exact absolute-normalizer shape.

**Verification**
Ran the required controls at `c07e115e227777e314de0902224241a58f92d785`:

```text
python3 scripts/check-main-drivable.py --self-test
326/326 passed

python3 scripts/check-main-drivable.py --report
44 guards on disk · 7 without main() · 37 in population
10 drive main() over a constructed world
27 pinned as ADR-0014 identity debt
```

I also checked the delivered manifest: `scripts/mutations/check-main-drivable.json` has `130` entries, all with `expect`. Nearby entries cover walrus as a local binding and relative/base path ops, but not walrus restore targets or absolute literals through `BASE_RELATIVE_PATH_OPS`.

Attacked and could not break: the round-6 identity substitution cases for assignment/import/def names; the existing lambda/default and first-comprehension-iterable `free_names` claims; the known relative literal wrappers; live on-disk walrus/global shapes. No live false green on disk found.

**NOT CONVERGED**
