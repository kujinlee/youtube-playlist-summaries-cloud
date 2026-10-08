<!-- codex-review: model=gpt-6.1-sol -->

**VERDICT (NOT CONVERGED)**

HEAD was and remains `e330ca80e144db346a4c7567de34583470747efd`. `git status --porcelain` returned no output, rc=0. No review file was written.

The positional case-name replacement introduces failures in both directions. The structural HEAD replacement introduces another false provenance token. Two withdrawal counterexamples also defeat round 2’s fixes.

## Blocking

None found.

## High

**H1 — Legitimate keyword and assigned case names become blocking errors.**  
`scripts/check-plan-code.py:1570–1577`

The replacement selects:

```python
if isinstance(n, ast.Call) and len(n.args) >= 2:
    cands = [n.args[0]]
```

Command run:

```bash
python3.12 - <<'PY'
import runpy,ast
c=runpy.run_path('scripts/check-plan-code.py')
for body in ['case(f"{x} works", guard(), 1)',
             'case(name=f"{x} works", got=guard(), want=1)',
             'name=f"{x} works"\ncase(name, guard(), 1)']:
    s='def guard():\n    return 1\nx="alpha"\n'+body+'\n'
    ast.parse(s)
    seen=[]
    exec(s,{'case':lambda name,got,want:seen.append((name,got,want))})
    e={'name':'probe','file':'scripts/demo.py',
       'edits':[['return 1','return 2']],'expect':seen[0][0]}
    errors,warnings=c['binding_problems']([e],{'scripts/demo.py':s})
    print(body.replace('\n','; '),'produced',seen,
          'errors',len(errors),'warnings',len(warnings))
PY
```

Output:

```text
case(f"{x} works", guard(), 1) produced [('alpha works', 1, 1)] errors 0 warnings 1
case(name=f"{x} works", got=guard(), want=1) produced [('alpha works', 1, 1)] errors 1 warnings 0
name=f"{x} works"; case(name, guard(), 1) produced [('alpha works', 1, 1)] errors 1 warnings 0
```

I also drove runnable temporary suites and valid manifests through `run_binding`. All three controls returned 0; all three AST-valid mutations returned 1 with `[FAIL] alpha works: got 2 want 1`. Binding returned **0, 1, 1**, respectively, falsely reporting the latter two cases as “GONE.”

**Required change:** resolve expressions that actually supply case names, including keywords and assigned names. Preserve rejection of unrelated output templates. Direct tuple-row comprehensions were recognized correctly.

**H2 — The acknowledged colon loophole has a live instance.**  
`scripts/check-withdrawal.py:268–271`; `docs/dashboard-entries.md:10440–10443`

The sentence rule has no boundary for this live lead-in:

```text
⚠ The API was used *instead of* `fly deploy` deliberately:
the running image is ...
**177 commits** since, **6 touching shipped code** ...
```

Command run, injecting a hypothetical correction while searching the unchanged real `docs/`:

```bash
python3.12 - <<'PY'
import runpy
w=runpy.run_path('scripts/check-withdrawal.py')
diff='--- a/docs/probe.md\n+++ b/docs/probe.md\n@@ -1 +1 @@\n-master carries **177 commits** since\n+master carries **179 commits** since\n'
w['main'].__globals__['git_diff']=lambda base,root:(diff,'')
print('actual docs rc=',w['main'](['--base','probe','--strict']))
PY
```

Output:

```text
ok — 1 figure(s) corrected, and none of them survives elsewhere in docs/.  (1 correction(s) examined across 393 document(s))
  suppressed as history: 1 hit(s) — 'was 'x1
actual docs rc= 0
```

A two-commit temporary repository containing this exact passage also returned 0. Changing only `deliberately:\n` to `deliberately.\n` returned **1**, reporting `master carries **177 commits** since` as a survivor.

**Required change:** a weak marker in this lead-in must not exempt the separate current claim introduced after it. Pin the live passage alongside a genuine wrapped-sentence control. This upgrades the previously constructed, acknowledged loophole.

**H3 — Repeated figures inherit the first occurrence’s history exemption.**  
`scripts/check-withdrawal.py:172–179, 303–322`

The implementation is:

```python
i = hit_text.find(figure)
return i if i >= 0 else 0
```

Command run:

```bash
python3.12 - <<'PY'
import runpy,pathlib,tempfile
w=runpy.run_path('scripts/check-withdrawal.py')
s='was 1,414. 1,414 anchors today'
diff=f'--- a/docs/fixed.md\n+++ b/docs/fixed.md\n@@ -1 +1 @@\n-{s}\n+{s.replace("1,414","1,416")}\n'
w['main'].__globals__['git_diff']=lambda base,root:(diff,'')
with tempfile.TemporaryDirectory() as td:
    root=pathlib.Path(td)
    (root/'docs').mkdir()
    (root/'docs/live.md').write_text(s)
    print('rc=',w['main'](['--strict'],root=root))
hit='was 1,414. 1,414 anchors'
print('first/second markers',
      repr(w['history_marker'](hit,w['figure_offset_in_hit'](hit,'1,414'))),
      repr(w['history_marker'](hit,hit.rfind('1,414'))))
PY
```

Output:

```text
ok — 2 figure(s) corrected, and none of them survives elsewhere in docs/.  (2 correction(s) examined across 1 document(s))
  suppressed as history: 2 hit(s) — 'was 'x2
rc= 0
first/second markers 'was ' ''
```

The same witness returned 0 in a real two-commit temporary repository. Single-number and previous-sentence controls returned 1.

**Required change:** carry the removed figure’s occurrence offset through signature construction and matching. `signature_of` also chooses the first containing token; changing `find` to `rfind` would merely choose a different occurrence without preserving identity.

## Medium

**M1 — Non-case templates still forgive invented expects; the “2 files” bound does not reproduce.**  
`scripts/check-plan-code.py:1570–1573`; `scripts/gen-dashboard.py:1784`

This actual expression becomes a case-name pattern:

```python
parts = html.split(f"<h2>{heading}</h2>", 1)
```

Command run using an existing valid mutation entry:

```bash
python3.12 - <<'PY'
import runpy,pathlib,copy
c=runpy.run_path('scripts/check-plan-code.py')
es,_=c['load_manifests'](pathlib.Path('.'))
f='scripts/gen-dashboard.py'
s=pathlib.Path(f).read_text()
e=copy.deepcopy(next(e for e in es if e['file']==f))
for ex in ['<h2>zz invented case that never existed</h2>',
           'zz case utterly absent']:
    e['expect']=ex
    print(ex,c['binding_problems']([e],{f:s}))
print('containment',c['expect_explained'](
    '<h2>zz invented case that never existed</h2>',
    c['case_name_literals'](s)))
PY
```

Output excerpts:

```text
<h2>zz invented case that never existed</h2> ([], ["... matches no string literal in scripts/gen-dashboard.py"])
zz case utterly absent (["... its expect names a case that is GONE ..."], [])
containment False
```

Re-derivation across all 62 target files:

```text
patterns old/new: 1585 / 96
live binding errors: 0
invented-expect downgrade: 62 / 25 files
first-pattern-only probe, current: 24 files
current downgrades explained ONLY by patterns, excluding containment: 12 files
```

For the reach probe, every `.*?` was replaced with `zz invented case that never existed`, regex escaping was decoded, and each generated expect was passed through shipped `binding_problems`. Genuine case templates contribute to these totals; the `.split` example proves that the residual population is not exclusively genuine case templates.

**Required change:** distinguish actual case-name producers from arbitrary multi-argument calls and sequences. Recompute and correct the bound in the script, backlog and roadmap.

**M2 — The structural HEAD expression admits invalid tokens and still accepts explicit non-measurements.**  
`scripts/check-provenance.py:309`

```python
r"|`HEAD[~^]?\d*`|\bHEAD[~^]\d*"
```

Command run:

```bash
python3.12 - <<'PY'
import runpy
p=runpy.run_path('scripts/check-provenance.py')
for suffix in ['at `HEAD123`','at HEAD~fiction',
               'we cannot measure at `HEAD`',
               '`` `HEAD` is only a syntax example ``']:
    row='| 999 | **47 s**; '+suffix+' |'
    print(repr(suffix),p['has_provenance'](row),
          p['findings_for']([row]))
PY
```

Output:

```text
'at `HEAD123`' True []
'at HEAD~fiction' True []
'we cannot measure at `HEAD`' True []
'`` `HEAD` is only a syntax example ``' True []
```

A separate `git rev-parse --verify` probe produced:

```text
HEAD~         git_rc 0   regex_match '`HEAD~`'
HEAD^^        git_rc 0   regex_match 'HEAD^'
HEAD~fiction  git_rc 128 regex_match 'HEAD~'
HEAD123       git_rc 128 regex_match '`HEAD123`'
```

`HEAD123` was **False at `31e8768a`, True at `e330ca80`**. The other two weaknesses above already existed: deleting the verb list did not remove their class.

**Required change:** reject malformed complete HEAD tokens and distinguish a quoted/negated ref mention from a measurement source—or explicitly state and pin that semantic limitation as a heuristic. Backticks do not establish that measurement happened.

**M3 — Metadata failures bypass the shared unreadable channel.**  
`scripts/find-claim.py:307–309`

```python
q = Path(dirpath) / fn
if not q.is_file():
    continue
```

Command run:

```bash
python3.12 - <<'PY'
import pathlib,tempfile,subprocess
with tempfile.TemporaryDirectory() as td:
    d=pathlib.Path(td)
    root=d/'root'; root.mkdir()
    (root/'ok.md').write_text('known control')
    lock=d/'locked'; lock.mkdir()
    (lock/'claim.md').write_text('live claim')
    (root/'claim.md').symlink_to(lock/'claim.md')
    lock.chmod(0)
    try:
        r=subprocess.run(['python3.12','scripts/find-claim.py',
            '--pattern','live claim','--control','known control',
            '--expect','absent',str(root)],capture_output=True,text=True)
        print('rc=',r.returncode)
        print(r.stderr.splitlines()[-1])
        print('CANNOT RUN' in r.stderr)
    finally:
        lock.chmod(0o700)
PY
```

Output:

```text
rc= 1
PermissionError: [Errno 13] Permission denied: '.../root/claim.md'
False
```

A deterministic mid-walk deletion probe also yielded **rc=0, “absent … so the search worked”** when a discovered file disappeared before `is_file`; disappearing directories correctly yielded rc=2.

**Required change:** report failures while classifying discovered entries through the same unreadable channel. `os.walk(onerror=...)` only covers traversal errors; it cannot catch this metadata failure.

## Low

**L1 — The real-path guard double-counts case-variant aliases on this macOS filesystem.**  
`scripts/find-claim.py:294–298`

```python
real = Path(dirpath).resolve()
if real in seen_real:
```

Command run:

```bash
python3.12 - <<'PY'
import runpy,pathlib,tempfile
f=runpy.run_path('scripts/find-claim.py')
with tempfile.TemporaryDirectory() as td:
    d=pathlib.Path(td)
    target=d/'CaseDir'; target.mkdir()
    (target/'claim.md').write_text('live claim')
    (d/'outer').mkdir()
    (d/'a').symlink_to(target)
    (d/'outer/b').symlink_to(d/'casedir')
    print('samefile',target.samefile(d/'casedir'),
          'resolved paths equal',target.resolve()==(d/'casedir').resolve())
    files,*_=f['collect_files']([str(d)])
    print('files',len(files),[str(p.relative_to(d)) for p in files])
    print('hits',len(f['search_files'](
        files,f['build_pattern']('live claim'))[0]))
PY
```

Output:

```text
samefile True resolved paths equal False
files 2 ['CaseDir/claim.md', 'outer/b/claim.md']
hits 2
```

**Required change:** use filesystem directory identity for the per-walk visited set. Case-preserving resolved strings do not identify the same directory consistently here. This overcounts; it did not produce an absence false negative.

## Checked and found SOUND

- **Required commands, Python 3.12.9:** all five suites returned rc=0 with actual counts **find-claim 71, withdrawal 81, provenance 123, plan-code 230, frontier 36**.
- `python3.12 scripts/check-selftest-counts.py` returned rc=0: **55 scripts, every declared count verified by running its suite**.
- `python3.12 scripts/check-plan-code.py --binding` returned rc=0: **1,506 anchors, 1,498 entries, 67 explained-expect warnings**, no live binding errors.
- `python3.12 scripts/check-fixture-variation.py` returned rc=0: **904 parameters across 67 files; 117 known-unvaried, 7 exemptions**.
- `--diff-coverage` ran, rc=0, and **warned about three uncovered changed functions**: `after_within_cell`, `_spy`, `_walk_error`. This is not evidence of complete mutation coverage.
- **Mutation execution:** shipped `stage_tree`, `run_suite`, `control_is_green` and `run_mutations` drove every mutation for the five changed guards. Four isolated partitions returned rc=0, green controls before and after, **49/49, 49/49, 49/49, 48/48 killed; zero survivors**. Total **195**: plan-code 126, provenance 19, withdrawal 18, frontier 11, find-claim 21.
- **Mutation integrity:** all **1,498** loaded mutations produced changed text and passed `ast.parse` after sequential application. No SyntaxError kills or textual no-op edits were credited.

The provenance measurements re-derived using each revision’s shipped functions were:

| Revision’s own backlog | Rows | Figure-bearing rows | Findings |
|---|---:|---:|---:|
| `1efc6c51` | 247 | 194 | 90 |
| `31e8768a` | 247 | 195 | 90 |
| `e330ca80` | 249 | 197 | 91 |

The **15 pinned HEAD witnesses pass**. Comparing the old and new guards over the **current 249 rows**, **zero rows lose provenance**, and both produce 197 figure-bearing rows and 91 findings. The current figure-bearing finding rate is **91/197 = 46.19%**; historical **90/195 = 46.15%** rounds identically. The current denominator is not 195.

Additional adversarial checks:

- `` `HEADS` ``, `` `head` `` and `` `git symbolic-ref HEAD` `` were rejected. `HEAD~` and `HEAD^^` resolve successfully in Git. Bare `measured at HEAD` rejection is the stated cost; I found no unavoidable prose-only HEAD witness.
- **Cell ownership:** inspected `check-docs`’s AST and entry-point guard. It is **724 lines**, not approximately 5,000, and executes no operational checks at import. A cache-reset import measured approximately **1.09 ms**. The owner is the guard’s sibling module, independent of the subject-root argument.
- **Cell boundaries:** last-cell/no-trailing-pipe and escaped pipes before and after the figure worked. A bare backticked pipe split exactly as `CELL_SPLIT` specifies; escaping it preserved the cell tail.
- **Warn-only justification holds:** `verdict(..., strict=False)` never returned 1 in the exercised finding/row combinations; strict=True did. Normal main delegates to it, and `--all` returns 0. CI’s provenance invocation omits `--strict`. The 16th witness, `**Chapter 3 findings** → ['3 findings']`, is another identifier false positive in the already pinned class.
- **Filesystem positives:** ordinary unreadable files, unreadable directories, unreadable directory symlinks, and disappearing directories returned **2**. An unreadable directory was reported before the dead-control verdict even when no control matched. Same-case aliases deduplicated; the self-cycle terminated.
- **Withdrawal positives:** genuine wraps remained one sentence. A previous-sentence marker did not suppress a single-number survivor. Two occurrences of the same signature, with history only beside the first and padding between them, correctly reported the second survivor.

## CANNOT RUN

- **Directory hardlink witness:** `os.link(directory, ...)` returned `PermissionError`, errno 1 on this host. That shape is scored neither pass nor fail.
- **No full 1,498-mutation kill verdict:** the broad sweep and its four replacement shards were intentionally interrupted while executing unchanged guards. Only the complete **195-mutation changed-guard sweep** is credited above.
