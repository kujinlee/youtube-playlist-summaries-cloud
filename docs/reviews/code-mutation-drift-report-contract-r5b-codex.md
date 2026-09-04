<!-- codex-review: model=gpt-5.5 -->

**Findings**

Medium: The new H1 self-test is vacuous for the corrected header line. The production behavior at `scripts/check-plan-code.py:1031-1034` is:

```python
if untrustworthy:
    out.append("  " + not_measured_line(ev))
    # NO `caught` figure. The count of entries is a fact; how many were caught is not.
    out.append(f"  mutation entries recorded: {len(ev['mutations'])}")
```

But the new case at `scripts/check-plan-code.py:2305-2306` only asserts absence:

```python
case("...and the word `caught` appears NOWHERE under that refusal",
     "caught" in evidence(_ev_ac), False)
```

I deleted the `mutation entries recorded` line in a temp copy outside the repo. Result: `183/183 passed`, exit `0`. That means the case does not prove the neutral replacement line exists; it only proves the forbidden word is absent. The manifest mutation for “regains its `caught` figure” kills the exact regression, but the self-test allows a broken/no-header fixture shape to pass.

Low: One new manifest anchor is especially cleanup-fragile. `scripts/mutations/check-plan-code.json:361-362` anchors on the exact implementation text:

```json
"    return rc == 0 and \"passed\" in out",
"    return rc == 0"
```

The implementation at `scripts/check-plan-code.py:432` is:

```python
return rc == 0 and "passed" in out
```

A reasonable cleanup to reuse the existing result regex, rename the helper, or spell the predicate across two lines would move/reword this anchor. If the manifest is left unchanged, `--mutate .` catches anchor-not-found; if someone “fixes” the count alongside a refactor, the only pin is arithmetic, not semantic identity.

**Checks Run**

`python3 scripts/check-plan-code.py --self-test`: `183/183 passed`.

`python3 scripts/check-plan-code.py --mutate .`: `OK — delivered scripts mutated: 7 file(s), 176 mutation(s), 0 survivor(s)`.

Targeted temp-copy probes:
- `if ev["trustworthy"]:` -> `if True:`: red, `181/183`, named `--mutate` case failed.
- `return rc == 0 and "passed" in out` -> `return rc == 0`: red, `179/183`.
- `NOT RUN if untrustworthy` -> `NOT RUN if False`: red, `180/183`.
- Header appends `, caught {caught}`: red, `182/183`.
- Delete the corrected neutral header line entirely: green, `183/183`.

**Consumers Enumerated**

From grep/AST, non-test verdict producers are `scripts/check-plan-code.py:785` and `:985`:

```python
ev["trustworthy"] = verdicts_are_trustworthy(...)
```

Non-test consumers/renderers are:
- `scripts/check-plan-code.py:1030` evidence block:
```python
untrustworthy = ev.get("declared") is not None and not ev.get("trustworthy")
```
Covered by existing plan/evidence mutations plus the new body/header cases, except for the vacuous header-presence hole above.

- `scripts/check-plan-code.py:2459` `--mutate` printer:
```python
if ev["trustworthy"]:
```
Covered by the new r4 B1 mutation and temp-proved red.

- `scripts/check-plan-code.py:2506` plan-mode final printer:
```python
if ev.get("trustworthy") or ev.get("declared") is None:
```
Covered by the existing plan-mode mutation.

I did not find a fourth live consumer in the code.

NOT CONVERGED
