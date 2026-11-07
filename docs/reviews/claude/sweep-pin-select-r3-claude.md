Reviewed head: 248172e0984debfd4af9fab2d5465dff2ab55af4

# Round 3: `sweep-pin-select` (PR #526, backlog #533), Claude half

Scope: the r2 fold `git diff 2c659dfb 248172e0`, which added `module_writes`, plus a final-tree check of
`git diff origin/master...HEAD`. origin/master is `319bd152` and is an ancestor of HEAD. **No BLOCKER.**

## Gates run

- `HOME=<scratch> python3 scripts/check-merge-ready.py --self-test` gave **265/265, rc 0**.
- `HOME=<scratch> python3 scripts/check-plan-code.py --self-test` gave **323/323, rc 0**.
- Both new mutations were applied to temp copies made with `git archive HEAD scripts`, with `HOME`
  redirected. Each went red through the case it names:
  - "walk the whole tree" (`if isinstance(child, _SCOPES):` → `if False:`): `[FAIL] ⛔ sweep-pin-select r2 F2: …`.
  - "ignore `global`" (`visit(child, decl)` → `visit(child, False)`): `[FAIL] ⛔ F1: a harness whose
    EXPECTED_MUTATIONS …`, which got `[True, True, True, True, False, True, True]`.
  - Each mutant had 34 reds. An unmutated control copy had 33 reds, all from the copy having no `docs/`
    or git context, and **0** of them were the two named cases. Each mutation therefore adds exactly
    its named case.

## The module_writes probe

I appended each shape below to the REAL `scripts/check-plan-code.py` and called
`harness_binding_problems` on it.

**Legitimate shapes. These must be `[]`:**

| Shape | At HEAD `248172e0` | At r1 `2c659dfb` |
|---|---|---|
| the real harness | `[]` | `[]` |
| a local in a nested function | `[]` | refused |
| a class attribute | `[]` | refused |
| a method local | `[]` | refused |
| a comprehension target inside a function | `[]` | refused |
| a walrus inside a lambda | `[]` | `[]` |
| a module-level comprehension target, `[PINS_FILE for PINS_FILE in …]` | **refused** | refused |
| an outer-function local whose NESTED function declares `global PINS_FILE` | **refused** (3 writes) | refused |

**Module writes. These must be refused:**

| Shape | At HEAD |
|---|---|
| `global` in a function, in a nested function, in a method, or in an `async def` | refused |
| a module-level walrus, or a walrus in a module-level comprehension | refused |
| a `for` target | refused |
| `with … as` | refused |
| tuple unpacking, a starred target, `+=`, `del` | refused |
| **`global PINS_FILE` in a CLASS body** | **`[]`, not refused** (R3-F1) |
| `import … as`, `from … import`, `def PINS_FILE`, `except … as`, `match` capture, `globals()[…]` | `[]` (the backlog #535 class, as r2 declared) |

`nonlocal` cannot reach a module global, since `nonlocal` binds only an enclosing function scope. Once
`global` is handled, a chain of them needs no separate case.

## Findings

### R3-F1: Low, fix-induced. A `global` declaration in a CLASS body rebinds `PINS_FILE` and is no longer counted

`scripts/check-merge-ready.py:1081`:

```python
decl = isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and any(
```

Python lets a class body declare a name `global`, and the class body runs at import. I checked this:
`X='orig'; class C: global X; X='redirected'` leaves `X` equal to `'redirected'`. `module_writes`
enters a `ClassDef` with `is_global=False` and never checks it for a `global`. The r1 code used
`ast.walk` and counted every `Name` store, so it REFUSED this shape (`PINS_FILE is written 2 times`).
The r2 fold reopened it.

**Failure scenario, measured end to end on a temp copy of `scripts/`:**

1. Insert the following just above `def own_pins_path` in `check-plan-code.py`:

   ```python
   class _Cfg:
       global PINS_FILE
       PINS_FILE = 'scripts/mutations/pins_v2.py'
   ```

2. Add `scripts/mutations/pins_v2.py` with `check-anchors.py` lowered from 5 to 4.

Results:

- `harness_binding_problems` returns `[]`.
- The harness's `PINS_FILE` is `scripts/mutations/pins_v2.py`, and it ENFORCES 4.
- The `expected_mutations.py` display that `check-merge-ready` reads still says 5.
- `own_pin_problems()` returns `[]`.

That is r1's divergence, reached through a plain `ast.Name` store. The fold says it keeps refusing that
kind of write. The r2 coordinator document says counting only `tree.body` "would have reopened r1's
refused case, a `global` write in a function". This is the same case in a class.

**Why Low, not BLOCKER:**

- The route costs the same as the `globals()['PINS_FILE']` route that r2 declined and filed as backlog
  #535: one harness edit plus a new data file.
- It edits `check-plan-code.py`, so the change selects the FULL sweep and appears in the reviewed diff.
- No case covers a class scope in either direction, so no mutation could have noticed.

**Fix, one token, measured.** Add `ast.ClassDef` to the tuple on line 1081. With that change, the
whole probe above gives the same answers, except that the class-body `global` is refused. The class
attribute (no `global`) and the method local stay `[]`.

**Test.** Add the class-body `global` to the r1 F1 rebinding case. Add a mutation that removes
`ast.ClassDef` from the tuple, named for that case.

**Alternative.** Fold the shape into backlog #535 as one more spelling. That is defensible, because #535
already says AST shape checks are not the defence. If you choose it, the BOUND comment above
`PINS_BINDING` (lines 1060-1063) should list this shape too, since it is a `Name` store and readers will
assume it is caught.

### R3-F2: Info, not fix-induced. Two contrived shapes are still falsely refused, which fails CLOSED

1. A module-level comprehension target, `_l = [PINS_FILE for PINS_FILE in …]`. In Python 3 a
   comprehension has its own scope, but `module_writes` does not treat comprehensions as scopes.
2. An outer-function local `PINS_FILE` whose nested function declares `global PINS_FILE`. `decl` uses
   `ast.walk(child)`, so the nested `global` leaks into the outer function's decision.

Both shapes were also refused at r1, so the fold made neither worse. Both are CANNOT RUN (rc 2), never
a false READY. The real harness has neither shape. No action is needed. They are listed so a later
reader does not mistake them for a regression.

## R2-F1 decline (backlog #535): sound

**What changed on the branch.** I checked the one route that differs, master's E1. On the branch, a
module-level `globals()['EXPECTED_MUTATIONS'] = dict(…, check-anchors=4)` added after line 1455, with
no other edit, is STILL caught. `own_pin_problems()` returns
`['scripts/check-anchors.py: the display says 5, this process holds 4']`, measured on a temp copy. So
master's `__file__` self-check survives the move for the data-rebinding route.

**What the branch admits that master does not.** It admits only the redirect: rebind `PINS_FILE`
through `globals()`, an import, a class-body `global` (R3-F1), or `own_pins_path`, and add a second pins
file. Each one needs:

- an edit to `check-plan-code.py`, which is `SWEEP_HARNESS` (`check-plan-code.py:338`), so it is FULL
  and reviewed;
- a NEW file under `scripts/mutations/`, which shows up in the diff.

Master's E2 (backlog #431's input) is a single line in `load_manifests` and needs no new file. So master
already admits an edit that is no harder and less visible, with every gate green, as the r2 coordinator
document measured.

**Conclusion.** The branch weakens one spelling. It does not open a cheaper route than master already
has, so it is not a regression that should block. The defence belongs to #535 (HOLD on any change to
the pin-loading code), not to more shape checks.

## Final tree

These are not re-litigated here. The r1 and r2 items stand as recorded:

- the binding check;
- `read_pins`'s reason consumer, `pin_file_problems`;
- the `PINS_FILE` / `PINS_SCRIPT` fallback in `pins_home`;
- the pin bump to 104, which is consistent with the two added manifest entries;
- the selector change, in which a `PINS_FILE`-only diff selects only the bumped scripts' manifests and a
  harness diff selects FULL. This is checked by the `_rh` / `_r533` cases near `check-plan-code.py:5315`,
  which pass in the 323/323 run.

I found nothing new in the final tree beyond R3-F1.

VERDICT: NOT CONVERGED
