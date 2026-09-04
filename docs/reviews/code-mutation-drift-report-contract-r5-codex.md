<!-- codex-review: model=gpt-5.5 -->

**Findings**

High: `control_is_green()` still accepts a failing summary as a green control.

`scripts/check-plan-code.py:417-432`:

```python
def control_is_green(rc: int, out: str) -> bool:
    ...
    return rc == 0 and "passed" in out
```

The r4 fix correctly stopped accepting a silent `rc == 0`, but it only moved the weakness one token over. A suite that prints a failure summary such as `0/1 passed` and exits 0 still satisfies this predicate because `"passed" in out` is true.

The file already has a result-line parser, but it is also too loose for this predicate:

`scripts/check-plan-code.py:138-139`:

```python
# A suite's result line: "45/45 passed", "5/5 cannot-run cases passed", …
RESULT = re.compile(r"\b\d+/\d+\b.*\bpassed\b")
```

That accepts `0/1 passed` too. The control predicate says it proves “the suite works”; this does not prove that. The consumer in `check()` then trusts it:

`scripts/check-plan-code.py:965-970`:

```python
if not control_is_green(rc, out):
    ok = False
    controls_green = False
    report.append(f"{name}: --self-test exited {rc}\n    {out[-600:]}" if rc != 0 else
                  f"{name}: --self-test exited 0 but printed no result — "
                  f"a script with no entrypoint exits 0 silently. Got: {tail!r}")
```

In a plan with no mutations, a broken self-test that prints `[FAIL] ...` plus `0/1 passed` but returns 0 can pass the checker: `run_mutations()` sees zero mutations, `declared == 0`, and `verdicts_are_trustworthy([], 0, True)` returns true. That is a false green over a broken fixture.

The new r4 mutation only guards one narrower regression:

`scripts/mutations/check-plan-code.json:357-365`:

```json
"name": "a control is called green on its EXIT CODE alone (r4 M1)",
...
"    return rc == 0 and \"passed\" in out",
"    return rc == 0"
```

That proves “not silent”; it does not prove “green.” The missing falsifier is a zero-exit control that prints a failing ratio, e.g. `0/1 passed`.

**Consumer Enumeration**

From the code, the verdict is produced in two places:

`scripts/check-plan-code.py:785`:

```python
ev["trustworthy"] = verdicts_are_trustworthy(m_muts, len(muts), controls_green)
```

`scripts/check-plan-code.py:985`:

```python
ev["trustworthy"] = verdicts_are_trustworthy(m_muts, len(muts), controls_green)
```

It is read/rendered in three live places:

`scripts/check-plan-code.py:1030-1036`:

```python
untrustworthy = ev.get("declared") is not None and not ev.get("trustworthy")
if untrustworthy:
    out.append("  " + not_measured_line(ev))
    out.append(f"  mutation entries recorded: {len(ev['mutations'])}")
else:
    out.append(f"  mutations declared and run: {len(ev['mutations'])}, caught {caught}")
```

`scripts/check-plan-code.py:2459-2462`:

```python
if ev["trustworthy"]:
    print(("OK — " if ok else "FAILED — ")
          + f"delivered scripts mutated: {len(ev['files'])} file(s), "
            f"{len(ev['mutations'])} mutation(s), {len(ev['survivors'])} survivor(s)")
```

`scripts/check-plan-code.py:2506-2512`:

```python
if ev.get("trustworthy") or ev.get("declared") is None:
    print(("OK — " if ok else "FAILED — ") + f"{mode}: {len(ev['files'])} file(s), "
          f"{len(ev['mutations'])} mutation(s), {len(ev['survivors'])} survivor(s)")
else:
    print(not_measured_line(ev, f"{mode}: "))
```

`verify_evidence()` does not independently consume the verdict; it calls `evidence(ev)` at `scripts/check-plan-code.py:1095`.

**Checks**

The new `--mutate` printer falsifier is real by inspection. Its mutation anchors directly on `scripts/check-plan-code.py:2459`, and the case at `scripts/check-plan-code.py:2229-2230` asserts both `NOT MEASURED` appears and `survivor(s)` does not. Opening the gate to `if True:` would print the tally branch and fail that case.

All 35 manifest anchors currently bind exactly once by text. The four new r4 anchors bind at lines 2459, 432, 1049, and 1034. They are still brittle text anchors, but not currently orphaned.

`EXPECTED_MUTATIONS` pins the current total at `scripts/check-plan-code.py:2408`:

```python
case("the declared counts are the real ones", sum(EXPECTED_MUTATIONS.values()), 176)
```

and pins the per-file count at `scripts/check-plan-code.py:562`:

```python
"scripts/check-plan-code.py": 35,
```

Removal without updating the code-side counts is caught. Removal plus deliberate rebasing is still a human-review problem, not mechanically prevented.

NOT RUN: I did not run `--self-test` or `--mutate .` because this review’s output contract said not to create, modify, or delete anything on disk, and those paths create temporary files/directories.

NOT CONVERGED.
