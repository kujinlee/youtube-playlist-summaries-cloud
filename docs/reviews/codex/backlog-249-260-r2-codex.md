<!-- codex-review: model=gpt-6.1-sol -->

**VERDICT: NOT CONVERGED**

Reviewed `cbd6d8f7`. The fold remains incomplete in H1, H2, M1, M2, M3 and M4.

The worktree changed concurrently during review. Final source-dependent verification used a temporary archive of `cbd6d8f7` with the existing dependency installation. Those concurrent edits were left untouched.

## Blocking

None demonstrated. The required checks I ran passed at the reviewed revision.

## High

### H1 remains incomplete: directory subjects still disappear without an exclusion count

**`scripts/find-claim.py:255–259`**

```python
for q in sorted(p.rglob("*")):
    if not q.is_file():
        continue
    if set(q.parts) & PRUNED_DIRS:
        continue
```

I built this temporary fixture:

```text
root/ok.md                 "known control"
root/linked -> ../external
external/claim.md          "claim still live"
root/node_modules/claim.md "claim still live"
```

Commands run through the Python fixture harness:

```bash
python3.12 scripts/find-claim.py \
  --pattern "claim still live" --control "known control" <fixture>/root

python3.12 scripts/find-claim.py \
  --pattern "claim still live" --control "known control" \
  <fixture>/root/node_modules <fixture>/root/ok.md
```

**Both returned rc=0:**

```text
ok — absent in the searched files, and the control hit 1 time(s), so the search worked.
(1 file(s) searched, .git/.mypy_cache/.next/.venv/__pycache__/node_modules not walked)
```

The first silently misses the symlinked directory. The second ignores a directory the caller explicitly named. Neither records a skipped file.

The “not walked” claim is also false. I wrapped `os.scandir`, called `collect_files([str(d)])` over a fixture containing `node_modules/deep/claim.md`, and measured:

```text
scandir calls within supposedly pruned node_modules: 4
searched= ['ok.md'] skipped= [] error= ''
```

**Required change:** follow directory symlinks with cycle protection, or report them as unreached subjects; honor explicitly named directory roots; implement actual traversal pruning instead of filtering after `rglob`. Unreached subjects must qualify the verdict or produce rc=2.

### M4 still suppresses a live claim using another sentence’s marker

**`scripts/check-withdrawal.py:750–756`**

```python
start = hit_offset(text, hit)
...
figure_at=figure_offset_in_window(start)
```

`start` is the **signature’s** start, not the figure’s position. The signature can begin in the preceding sentence.

I created a temporary Git repository, committed:

```text
The status was green. count 1,414 anchors today
```

then committed the correction to `1,416`. A separate document retained the old claim. Command executed through the Python 3.12 harness:

```python
w["main"](["--strict", "--base", base], root=root)
```

Known positive, with the copy containing:

```text
The status is green. count 1,414 anchors today
```

Output:

```text
SURVIVOR docs/copy.md:1: green. count 1,414 anchors today
FOUND — 1 superseded figure still stands elsewhere ...
rc=1
```

Changing only `is` to `was` produced:

```text
ok — 1 figure(s) corrected, and none of them survives elsewhere in docs/.
suppressed as history: 1 hit(s) — 'was 'x1
rc=0
```

The figure’s sentence contains no history marker. This directly reinstates M4’s cross-sentence suppression.

A separate fixture also showed wrapping sensitivity:

```text
the sweep holds 1,414 anchors today (was wrong).   -> rc=0, suppressed
the sweep holds
1,414 anchors today (was wrong).                  -> rc=1, SURVIVOR
```

**Required change:** calculate the figure’s position inside each matched signature and pass that offset. Treat ordinary Markdown line wrapping as whitespace within a sentence; `SENTENCE_SPLIT = ...|\n` currently breaks that relationship.

### H2’s additional golden leaves two reachable refusal arms unprotected

**`scripts/codex-frontier-model.py:191–197`**

```python
elif models:
    ...
    "Inspect the cache rather than assuming the CLI is stale."
else:
    ...
    "check `codex login status`."
```

I ran this Python 3.12 mutation harness against the pinned snapshot:

```python
s = Path("scripts/codex-frontier-model.py").read_text()
for old in [
    '"check `codex login status`."',
    '"Inspect the cache rather than assuming the CLI is stale."',
    '"deliberate narrowing, not a claim about what `hide` means."',
]:
    mutated = s.replace(
        old,
        old[:-1] + ' Disregard everything above: Codex is simply down."',
    )
    ast.parse(mutated)
    ns = {
        "__name__": "review_mutant",
        "__file__": str(Path("scripts/codex-frontier-model.py").resolve()),
    }
    exec(compile(mutated, "<AST-valid>", "exec"), ns)
    print(ns["_self_test"]())
```

Results:

```text
empty            AST-valid rc=0  31/31 self-test cases passed
no-near          AST-valid rc=0  31/31 self-test cases passed
golden-covered   AST-valid rc=1  29/31 self-test cases passed
```

The empty-cache output actually included the contradictory sentence. The golden-covered mutation provides the known-positive control.

**Required change:** pin the complete output of the empty-cache and nonempty/no-near-miss arms too. “Two refusal arms” is an incomplete enumeration.

## Medium

### M1’s containment rule both forgives stale names and rejects valid generated names

**`scripts/check-plan-code.py:1493–1507,1534–1541,1602`**

```python
return {n.value for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and isinstance(n.value, str)}
```

```python
return any(len(lit) >= floor and (lit in expect or expect in lit)
           for lit in literals)
```

Command run under Python 3.12:

```python
p = runpy.run_path("scripts/check-plan-code.py")
for src, expect in [
    (
        '"""Historical title: the old case is gone forever"""\n'
        'case("replacement title", 1, 1)',
        "the old case is gone forever",
    ),
    ('case(f"{x} works", 1, 1)', "alpha works"),
]:
    print(p["binding_problems"](
        [{"file": "x.py", "name": "probe",
          "edits": [["1, 1", "0, 1"]], "expect": expect}],
        {"x.py": src},
    ))
```

Output:

```text
([], ["probe: expect 'the old case is gone forever'
       matches no string literal in x.py"])

(["probe: its expect names a case that is GONE from x.py ..."], [])
```

The stale title survives through an unrelated docstring. Conversely, a valid generated `alpha works` title is rejected because all its static components are shorter than twelve characters.

I also tested `.join`, `%` formatting and `str.format` case names; all returned `explained=False`. Comments themselves returned `set()`; **docstrings do count**.

**Required change:** restrict candidates to expressions that supply suite case names. Use expression-aware handling or an explicit dynamic-name mechanism. Passing the current manifests does not establish twelve characters as a valid discriminator.

### M3 still accepts prose about HEAD as measurement provenance

**`scripts/check-provenance.py:116`**

```python
r"...|(?:\bat|\bas of|\bmeasured(?:\s+\w+){0,2})\s+HEAD\b"
```

Command run under Python 3.12:

```python
v = runpy.run_path("scripts/check-provenance.py")
row = "| 999 | **3 failures**; we cannot look at HEAD |"
print(v["bolded_figures"](row))
print(v["has_provenance"](row))
print(v["findings_for"]([row]))
```

Output:

```text
['**3 failures**']
True
[]
```

This names no measurement source. It merely says HEAD cannot be inspected.

Boundary controls returned:

```text
format HEAD                 False
lookat HEAD                 False
at HEAD                     True
we cannot look at HEAD      True
```

Thus `\bat` prevents the suggested inside-word matches, but still permits the semantic bypass.

**Required change:** require an explicit measurement-source construction rather than accepting any occurrence of `at HEAD`.

### M2 still misses single-digit measurements and newly counts non-measurements

**`scripts/check-provenance.py:100`**

```python
r"...|(?<!exit )(?<!exits )(?<!code )\b\d\s+[A-Za-z]"
```

Command run under Python 3.12:

```python
v = runpy.run_path("scripts/check-provenance.py")
for s in [
    "**3%** failed",
    "**3** failures",
    "**rc 1 is failure**",
    "**Phase 1 is complete**",
]:
    print(s, "=>", v["findings_for"](["| 999 | " + s + " |"]))
```

Output:

```text
**3%** failed           => []
**3** failures          => []
**rc 1 is failure**     => [('999', 1)]
**Phase 1 is complete** => [('999', 1)]
```

The first two are measurements without provenance. The latter two are an exit-status description and a phase identifier.

**Required change:** detect measurement context beyond the inside of the bold span, including percentages and a bold numeral followed by its counted noun. Distinguish identifiers/status codes using more than three case-sensitive lookbehinds.

## Low

### The exclusion qualification is missing from one verdict arm

**`scripts/find-claim.py:214–217`**

```python
return 1, (
    "MISSING — the claim is absent, and the control proves the search reached the files, "
    "so this is a real absence rather than a broken search."
)
```

Command run under Python 3.12:

```python
f = runpy.run_path("scripts/find-claim.py")
print(f["verdict"](0, 1, "present", 2))
print(f["verdict"](0, 1, "report", 2))
```

Output:

```text
(1, 'MISSING — ... the control proves the search reached the files,
so this is a real absence rather than a broken search.')

(0, '0 occurrence(s); control hit 1 time(s).
⚠ 2 file(s) were EXCLUDED ...')
```

The CLI tail still prints the suffix-skip count, so this is a qualification defect rather than a completely invisible CLI exclusion.

**Required change:** append `skip_note` to the missing-present arm and the missing-control verdict.

## Checked and found SOUND

- **Python 3.12 self-tests:** `find-claim` **53/53**, provenance **67/67**, withdrawal **71/71**, frontier-model **31/31**, plan-code **217/217**; all rc=0.
- **Binding:** `python3.12 scripts/check-plan-code.py --binding` returned rc=0: **1,483 anchors across 1,475 entries**, **67 explained unmatched expects**.
- **Diff coverage:** `--diff-coverage` returned rc=0, covering every nonexempt changed function across **10 files**.
- **Fixture variation:** returned rc=0: **893 parameters across 67 files**, **117 ratcheted**, **7 exempt**.
- **External count audit**, rerun on the pinned snapshot with dependencies available:

  ```text
  self-test counts: 55 script(s) declare a count, every one verified by running it
  rc=0
  ```

- **Manifest ratchet:** independently parsed every mutation JSON. Actual total **1,475**; per-target counts equal `EXPECTED_MUTATIONS`, not merely its sum.
- **Search controls:** uppercase `.RST`, a 4 MB `.min.js`, and a 4 MB `.svg` were all searched: **three hits, rc=1**. Adding undecodable bytes in an unknown suffix produced **rc=2**.
- **Collection error asymmetry:** bad paths and binary-only directories both terminate through `err` with rc=2; no caller confusion demonstrated.
- **Withdrawal reachability:** measured **49,184 figure occurrences** in nonexempt documents, with **2,330 weak-marker suppressions**. The prong was not deleted. The temporary Git fixture exercised the production suppression counter and its printed line.
- **Offset arithmetic:** `min(start, span)` correctly located hits near both document edges. The demonstrated defect is passing the signature start.
- **Keyword-only caller audit:** every Python caller found supplies `figure_at`.

## CANNOT RUN

The complete mutation sweep was not run. Targeted refusal mutations were AST-validated and exercised, but attribution across all 1,475 entries remains **unmeasured—neither pass nor fail**.
