<!-- codex-review: model=gpt-5.5 -->

**Control**

Ran at `9e5e5967`.

`python3 scripts/check-main-drivable.py --self-test`:
```text
375/375 passed
```

`python3 scripts/check-main-drivable.py --report`:
```text
44 guards on disk · 7 without main() (outside the population) · 37 in population
  10 drive main() over a constructed world — param 3, argv 3, rebind 8, subproc 1 (a guard may take more than one route, so these need not sum)
  27 pinned as ADR-0014 identity debt
```

**High**

1. `relpath` with an explicit relative `start` is credited as constructed.

At [scripts/check-main-drivable.py:1568](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-main-drivable.py:1568), `relpath` is LIVE only when `start` is omitted. But `os.path.relpath(target, start="sub")` still resolves `start` against the live cwd.

Concrete input:
```python
other = os.path.relpath(tempfile.mkdtemp(), start="sub")
main([], root=other)
```

Observed:
```text
os.path.relpath(tempfile.mkdtemp(), start='sub') => ('param', True, 1)
os.path.relpath(tempfile.mkdtemp(), 'sub') => ('param', True, 1)
```

Runtime premise:
```text
a ../../../../../../../../../.../target
deep/b ../../../../../../../../../../.../target
```

Verdict should be `DEBT`; it currently earns `param`.

Aim: deliverable.  
Previous round’s fix caused it: yes, this is in the new `CWD_DEFAULTED_OPS`/`relpath` repair surface from round 8.  
Blast radius: candidate fix in a `stage_tree` temp copy produced `classify diffs 0` over all 44 guards; report still ended with `27 pinned as ADR-0014 identity debt`. Latent, not live on disk.

2. A method that returns the global still earns `rebind`.

At [scripts/check-main-drivable.py:1636](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-main-drivable.py:1636), one-hop helper resolution only follows `ast.Name` calls to top-level functions. A method call over a constructed receiver is therefore classified as built, even when the method returns `ROOT`.

Concrete input:
```python
class C:
    def same(self):
        return ROOT

def _self_test():
    globals()["ROOT"] = C().same()
    main([])
```

Observed:
```text
C().same() identity rebind => ('rebind', True, 1)
```

Verdict should be `DEBT`; runtime hands `main` the same global.

Aim: deliverable.  
Previous round’s fix caused it: no. The round 8 helper fix did not introduce the shape; it left the “method helper” hole open.  
Blast radius: candidate method-return resolution in a `stage_tree` temp copy produced `classify diffs 0` over all 44 guards; report still ended with `27 pinned as ADR-0014 identity debt`. Latent, not live on disk.

**Medium**

3. Module-dict `.get()` is not key-sensitive, so a real different-global substitution is lost.

At [scripts/check-main-drivable.py:1117](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-main-drivable.py:1117), key-sensitive module dict reads handle only subscript form. `globals().get("ROOT")` and `globals().get("OTHER")` both fall through to the same LIVE-with-no-case-leaf refusal, but the second is a real change by this rule’s own `g["OTHER"]` precedent.

Concrete input:
```python
ROOT = os.getcwd()
OTHER = "/tmp/fixture"

def _self_test():
    globals()["ROOT"] = globals().get("OTHER")
    main([])
```

Observed:
```text
globals().get('ROOT') => ('DEBT', False, 1)
globals().get('OTHER') => ('DEBT', False, 1)
```

`globals().get("ROOT")` should be `DEBT`; `globals().get("OTHER")` should earn `rebind`.

Aim: deliverable.  
Previous round’s fix caused it: yes, this is directly inside the round 8 “module dict by key” repair, which covered subscript but not `.get`.  
Blast radius: candidate `.get` key handling in a `stage_tree` temp copy produced `classify diffs 0` over all 44 guards; report still ended with `27 pinned as ADR-0014 identity debt`. Latent, not live on disk.

**Could Not Break**

I attacked these and did not get a finding:

- Bare/global identity substitution after the round 6/r7 leaf test: direct names and simple wrappers refused as intended.
- Module-level lambda, `functools.partial`, and decorated plain helper cases where the body itself returns the global: all refused or stayed conservative in the concrete probes I ran.
- `free_names` around lambda defaults, nested comprehensions, and walrus scoping: I did not find a CPython-symtable disagreement.
- Zero-argument path ops already covered by the current default-base rule.
- Manifest/count control for this file: the requested self-test and report controls are green; I did not find a sixth masking pair, fifteenth dying case, or third bad deletion in this pass.

NOT CONVERGED.
