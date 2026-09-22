<!-- codex-review: model=gpt-5.5 -->

VERDICT: NOT CONVERGED — 1 Blocking, 1 High.

**Blocking — the mutation-anchor transfer number is false for the recommendation as written.**

The document says extracting `_structural()` + `_steps()` moves 8 anchors, so `check-python-pin.py` goes `39 -> 31` and new `workflow_structure.py = 8`. Re-derived: 12 existing anchors bind inside `_steps`/`_structural`, so extracting both is `39 -> 27` and `workflow_structure.py = 12`.

Evidence:

```bash
python3 - <<'PY'
from pathlib import Path
import json,re
text=Path('scripts/check-python-pin.py').read_text()
lines=text.splitlines()
starts=[]
for i,l in enumerate(lines,1):
    m=re.match(r'def (\w+)\(', l)
    if m: starts.append((m.group(1),i))
ranges=[]
for idx,(name,start) in enumerate(starts):
    end=starts[idx+1][1]-1 if idx+1<len(starts) else len(lines)
    ranges.append((name,start,end))
entries=json.load(open('scripts/mutations/check-python-pin.json'))
for idx,e in enumerate(entries,1):
    old=e['edits'][0][0]
    pos=text.find(old)
    line=text[:pos].count('\n')+1 if pos>=0 else -1
    func='?'
    for name,s,en in ranges:
        if s<=line<=en: func=name
    if func in {'_steps','_structural'}:
        print(f'{idx:02d} {func} line={line} {e["name"]}')
PY
```

Output:

```text
27 _steps line=264 the dash line is dropped from the step body, so a pin written ON the dash becomes invisible
28 _steps line=232 the block-scalar mask is removed from the SPLITTER, so a dash line in a heredoc manufactures a phantom step (Codex r3 High) [r4 codex Medium: expect re-pointed — after the sibling rewrite the dashed fixture no longer discriminates]
29 _steps line=298 the block-scalar opener stops recognising FOLDED scalars, so `>` content is read as structure
30 _steps line=263 a sibling dash stops starting a new step, so the second of two steps is silently discarded (r3 F4)
31 _steps line=278 a blank line ends a step, so a pin written after one vanishes (r3 F4)
32 _structural line=349 comments are read as structure again, so one at the dash indent ends the step and the pin vanishes (r3 F4 follow-through)
33 _steps line=249 the steps: scope starts OPEN, so any YAML list of mappings is read as steps again — a matrix.include entry pins an unpinned job (r4 codex High)
34 _steps line=245 the job's steps: is taken as the DEEPEST rather than the shallowest, so a matrix dimension named steps wins (r5 F1)
35 _steps line=254 any steps: key re-scopes, so a nested one named steps eats the real step's body (r5 F2 regression)
36 _steps line=260 the steps block never closes on dedent, so a later list is read as steps (r5 F3)
37 _steps line=295 the steps: opener stops accepting YAML node properties, so an anchored step list is invisible (r5 codex Medium)
38 _steps line=244 job keys stop being excluded from the depth scan, so a job named steps becomes its own step list (r6 codex High) [both guards: the depth scan AND the opener, since either alone masks the other]
```

Specific repair: correct the recommendation and mutation plan. If both functions move, transfer all 12 entries and set `EXPECTED_MUTATIONS` to `check-python-pin.py: 27` plus `workflow_structure.py: 12`. If only 8 should move, the document must name which code is *not* moving and stop recommending extraction of both functions wholesale.

**High — the recommended extraction does not fix one of the document’s own R3 false greens.**

`_structural()`/`_steps()` remove comments and some block-scalar content. They do not answer whether a workflow step executes. The document’s own transcript says `if: false` satisfies R3; after applying the proposed reader, it still satisfies R3.

Evidence:

```bash
python3 - <<'PY'
from pathlib import Path
import importlib.util, sys
def load(name, path):
    spec=importlib.util.spec_from_file_location(name, path)
    mod=importlib.util.module_from_spec(spec); sys.modules[name]=mod; spec.loader.exec_module(mod); return mod
rat=load('rat','scripts/check-ratchet-contract.py')
pin=load('pin','scripts/check-python-pin.py')
script='''#!/usr/bin/env python3
"""Usage:
    python3 scripts/check-x.py --self-test
"""
'''
fixtures={
'comment':'# python3 scripts/check-x.py\n',
'block_named_run':'steps:\n  - name: fixture\n    run: |\n      python3 scripts/check-x.py\n',
'if_false':'steps:\n  - if: false\n    run: python3 scripts/check-x.py\n',
'control':'steps:\n  - run: python3 scripts/check-x.py\n',
}
for name, blob in fixtures.items():
    raw = not rat.check_caller('scripts/check-x.py', script, blob)
    structural_blob='\n'.join(pin._structural(blob.split('\n')))
    via_steps_blob='\n'.join('\n'.join(step.body) for step in pin._steps(blob))
    structural = not rat.check_caller('scripts/check-x.py', script, structural_blob)
    via_steps = not rat.check_caller('scripts/check-x.py', script, via_steps_blob)
    print(f'{name}: raw={"SATISFIED" if raw else "VIOLATION"} structural_whole_file={"SATISFIED" if structural else "VIOLATION"} via_steps={"SATISFIED" if via_steps else "VIOLATION"}')
PY
```

Output:

```text
comment: raw=SATISFIED structural_whole_file=VIOLATION via_steps=VIOLATION
block_named_run: raw=SATISFIED structural_whole_file=VIOLATION via_steps=VIOLATION
if_false: raw=SATISFIED structural_whole_file=SATISFIED via_steps=SATISFIED
control: raw=SATISFIED structural_whole_file=SATISFIED via_steps=SATISFIED
```

Specific repair: either narrow the document’s claim to “fixes comment/prose and block-scalar prose only; disabled steps remain out of scope,” or change the recommendation to a workflow execution reader for R3 that excludes statically disabled steps, with tests for comment, block scalar, `if: false`, and control.

**Medium — the block-scalar bound is understated for dash-opened steps.**

A valid GitHub Actions shorthand step can be `- run: |`. `_structural()` does not mask that opener when applied to the whole file, and `_steps()` cannot recover because its pre-split structural pass has already kept the block content. The document’s “read `ci.yml` through it” instruction is therefore underspecified.

Evidence from the same probe, with this fixture added:

```text
block_dash_run: raw=SATISFIED structural_whole_file=SATISFIED via_steps=SATISFIED
block_named_run: raw=SATISFIED structural_whole_file=VIOLATION via_steps=VIOLATION
```

Specific repair: define the library API by contract, not by exporting two private helpers. Add a whole-workflow fixture for `steps:\n  - run: |\n      python3 scripts/check-x.py` and decide whether the reader masks dash-opened block scalars or refuses them loudly.

**Low — “every guard is stdlib-only” is imprecise.**

The true load-bearing claim is “no third-party YAML parser/dependency is available.” Literal “every guard is stdlib-only” is false if local helper modules count.

Evidence:

```bash
python3 - <<'PY'
from pathlib import Path
import ast, re, sys
stdlib=set(getattr(sys,'stdlib_module_names',()))
external=[]
for path in sorted(Path('scripts').glob('*.py')):
    tree=ast.parse(path.read_text())
    mods=[]
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            mods += [a.name.split('.')[0] for a in n.names]
        elif isinstance(n, ast.ImportFrom) and n.module:
            mods.append(n.module.split('.')[0])
    ext=sorted({m for m in mods if m not in stdlib and m not in {'__future__'}})
    if path.name.startswith('check-') and ext:
        external.append((path.name, ext))
print('guard_external_imports', external)
try:
    import yaml
    print('import_yaml OK')
except Exception as e:
    print('import_yaml', type(e).__name__, str(e))
PY
```

Output:

```text
guard_external_imports [('check-anon-exposure.py', ['m4_base_db', 'm4_catalog']), ('check-catalog-coverage.py', ['m4_catalog']), ('check-guard-coverage.py', ['m4_base_db', 'subject_status']), ('check-live-schema.py', ['m4_catalog']), ('check-paid-caller-arrival.py', ['m4_base_db']), ('check-plan-code.py', ['coverage_verdict']), ('check-sentinel-meanings.py', ['m4_base_db', 'subject_status']), ('check-vocabulary-collisions.py', ['m4_base_db', 'subject_status'])]
import_yaml ModuleNotFoundError No module named 'yaml'
```

Specific repair: say “no guard imports a third-party YAML parser; PyYAML is not installed; several guards do import local helper modules.”

**Checked And Sound**

The population correction is sound: `check-ci-watched.py` reads no workflow, and the real omitted sibling is `check-ratchet-contract.py`.

```text
guards 40
workflow_subject_readers ['check-merge-ready.py', 'check-python-pin.py', 'check-ratchet-contract.py']
check_ci_watched_has_workflow_literal False
```

The 284/480 figure is sound under `split("\n")` counting:

```text
split_lines 480
physical_lines_wc_equivalent 479
structural_lines 196
masked_lines 284
masked_pct 59
```

The “0 of 40 currently depend on the R3 false green” claim is sound with an instrument that mirrors `check-ratchet-contract.py`’s caller corpus and replaces only `ci.yml` with `_structural(ci)`:

```text
ratchets 40
raw_satisfied 40
structural_satisfied 40
flips []
```

The flow-mapping transcript is sound:

```text
declared_pins []
unpinned_jobs ['w.yml:verify']
verdict_rc 2
verdict_msg CANNOT RUN — no `python-version:` was found in any workflow, so the interpreter
```

Current self-tests for the two central scripts are green:

```text
self-test: 41/41 passed
84/84 passed
```

I started `python3 scripts/check-plan-code.py --mutate .` as a control, but stopped it at 227/868 mutations because the direct anchor attribution above is the decisive evidence for the transfer-count defect.
