<!-- codex-review: model=gpt-5.5 -->

**Blocking**
`substitution_changes_the_world` still gives REBIND for an unchanged world hidden behind a module helper. A case can write `globals()['ROOT'] = same_root()` where `same_root()` just returns `ROOT`; no constructed world reaches `main`, but the guard reports `rebind`.

Command output from staged temp tree:

```text
routes= ['rebind']
changes= True
world_class= built
free= ['same_root']
```

Relevant code: [scripts/check-main-drivable.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-main-drivable.py:1059) and [scripts/check-main-drivable.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-main-drivable.py:1489).

Concrete input:

```python
ROOT = {"a": 1}
def same_root():
    return ROOT
def main(argv=None):
    return ROOT
def _self_test():
    globals()["ROOT"] = same_root()
    case("x", main([]), 0)
```

Blast radius: latent false green for the deliverable. An unpinned guard could satisfy D2 without driving `main` over a case-built world.

Deliverable or instrument? Deliverable.

Did the previous round’s fix cause it? No. It is an unclosed sibling of the r7 leaf-identity fix: the inline leaf test catches `(lambda: ROOT)()` but not the same identity through a named module helper.

**High**
`BASE_RELATIVE_PATH_OPS` treats `os.path.relpath(td)` as “as live as its base,” but `relpath(path)` reads the current directory through its default `start=os.curdir`. That means it can credit a path value that is ambient-cwd-dependent.

Command output:

```text
os.path.abspath(td)                 routes=['param'] world_class=built
os.path.realpath(td)                routes=['param'] world_class=built
os.path.relpath(td)                 routes=['param'] world_class=built
os.path.relpath(td, start=td)       routes=['param'] world_class=built
os.path.relpath('/tmp/fixture')     routes=['param'] world_class=built
```

Runtime check:

```text
same target: /var/.../tmphtad1afx/target
from cwd A: ../../../../../../../../var/.../tmphtad1afx/target
from cwd B: ../../../../../../../../../var/.../tmphtad1afx/target
depends_on_cwd: True
```

Relevant code: [scripts/check-main-drivable.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-main-drivable.py:238) and [scripts/check-main-drivable.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-main-drivable.py:1508).

Concrete input:

```python
td = tempfile.mkdtemp()
case("x", main([], root=os.path.relpath(td)), 0)
```

Observed verdict: `param`. Expected: no route unless `start` is also constructed/nonambient.

Blast radius: latent false green for the deliverable.

Deliverable or instrument? Deliverable.

Did the previous round’s fix cause it? Partly. This comes from the normalizer/base-relative repair that grouped `relpath` with `abspath`/`realpath`; r7’s absolute-literal tightening did not distinguish `relpath`’s cwd-reading default.

**Medium**
The new `free_names` symtable assertion is overclaimed. A lambda inside a comprehension body that closes over the comprehension target disagrees with the suite’s “CPython symtable” oracle:

```text
[(lambda: x) for x in src]
  free_names: ['src']
  symtable:   ['src', 'x']
[(lambda: x)() for x in src]
  free_names: ['src']
  symtable:   ['src', 'x']
```

Adding the fifteenth shape to `_SHAPES` in a temp copy makes the self-test fail:

```text
[FAIL] ⭐ free_names agrees with CPython's own symbol table on every binding form it claims to read off the grammar ...
        got:  ['[(lambda: x)() for x in src]']
        want: []

355/356 passed
```

Relevant code: [scripts/check-main-drivable.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-main-drivable.py:849) and [scripts/check-main-drivable.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-main-drivable.py:3104).

Blast radius: instrument, not a live D2 false green. `free_names` looks right for expression provenance here; the suite’s symtable comparison is the brittle piece.

Deliverable or instrument? Instrument.

Did the previous round’s fix cause it? Yes, the r7 symtable-oracle assertion introduced the overbroad claim.

**Controls Run**
I did run the required controls in the real tree:

```text
python3 scripts/check-main-drivable.py --self-test
356/356 passed
```

```text
python3 scripts/check-main-drivable.py --report
44 guards on disk · 7 without main() · 37 in population
10 drive main() over a constructed world ...
27 pinned as ADR-0014 identity debt
```

I also staged a temp tree with `stage_tree`/`child_env`; staged control reproduced `356/356` and the same `10/37`, `MAIN_DEBT 27` report.

Attacked and could not break: no live guard on disk matched the helper-identity false green; no live guard on disk uses `relpath` in a D2-crediting shape. I did not find a sixth masking pair, fifteenth dying case, or third bad deletion in this pass.

**NOT CONVERGED**
