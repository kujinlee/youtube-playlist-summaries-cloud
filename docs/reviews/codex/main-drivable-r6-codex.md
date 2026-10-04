<!-- codex-review: model=gpt-5.5 -->

**Blocking**

1. `LIVE_WORLD_NAMES` still misses live-repository spellings, so a literal live world is credited as constructed.

Observation: `Path(__cached__)` and `Path(vars()["__file__"])` are ambient module/runtime paths, but both classify as `param`.

Command/output:

```text
$ python3 - <<'PY'
...
print('Path(__cached__):', verdict(live_cached))
print('Path(vars()["__file__"]):', verdict(live_vars))
PY
Path(__cached__): param
Path(vars()["__file__"]): param
```

File: `scripts/check-main-drivable.py:157`, `scripts/check-main-drivable.py:1238`.

Blast radius: latent false green. I did not find this spelling on the ten live compliant guards, but an unpinned guard could satisfy D2 by passing its own cache/source path.

**High**

1. The widened live-reader attribute rule now refuses genuinely built worlds after `.resolve()` / `.absolute()` / `abspath()`.

Observation: a temp path the case built becomes `DEBT` as soon as it is normalized. That is the other B1 direction: a world the case genuinely built is now refused.

Command/output:

```text
$ python3 - <<'PY'
...
p: param
p.resolve(): DEBT
p.absolute(): DEBT
p.parent: param
Path(tempfile.mkdtemp()).resolve(): DEBT
Path(tempfile.mkdtemp()).absolute(): DEBT
os.path.abspath(tempfile.mkdtemp()): DEBT
os.path.realpath(tempfile.mkdtemp()): DEBT
os.path.relpath(tempfile.mkdtemp()): DEBT
PY
```

File: `scripts/check-main-drivable.py:1265-1267`.

Blast radius: latent false debt. Natural ADR-0014 repairs often normalize temp paths; this would keep them pinned even though they drive `main()` over a constructed world.

2. The deleted lambda-parameter subtraction was not dead; its removal changes a verdict.

Observation: restoring through a lambda whose parameter shadows a local case binding is a restore, but it is credited as a live substitution.

Command/output:

```text
$ python3 - <<'PY'
...
lambda-param-shadow restore: rebind
lambda-param-nonshadow restore: DEBT
PY
```

Concrete input shape:

```python
_sv = globals()["ROOT"]
x = tempfile.mkdtemp()
globals()["ROOT"] = tempfile.mkdtemp()
globals()["ROOT"] = (lambda x: x)(_sv)
return main(["--flag"])
```

File: `scripts/check-main-drivable.py:838-849`.

Blast radius: latent false green. The removed clause can distinguish a real restore from a substitution when lambda parameter names collide with enclosing locals.

**Medium**

1. There is still a dying mutation case: severing the subprocess argv shape guard crashes with zero `[FAIL]` lines.

Observation: replacing the guarded argv iteration with `for el in argv.elts` produces a red suite with no attributable failure.

Command/output from temp copy:

```text
$ python3 scripts/check-main-drivable.py --self-test
--- subproc_argv_shape_removed rc 1 ok 272 fail 0
...
File ".../scripts/check-main-drivable.py", line 973, in rec
    for el in argv.elts
              ^^^^^^^^^
AttributeError: 'Name' object has no attribute 'elts'
```

File: `scripts/check-main-drivable.py:973` and same shape at `scripts/check-main-drivable.py:983`.

Blast radius: suite quality, latent. A mutation at this precondition is red but unattributed, so the ratchet cannot file a useful killed case.

**Verification**

Required commands ran:

```text
$ python3 scripts/check-main-drivable.py --self-test
278/278 passed

$ python3 scripts/check-main-drivable.py --report
44 guards on disk · 7 without main() · 37 in population
10 drive main() over a constructed world
27 pinned as ADR-0014 identity debt
```

Tree verified at `fe3c82ce` on `d2-main-drivable`; working tree only had the two pre-existing untracked PDFs.

**NOT CONVERGED**.
