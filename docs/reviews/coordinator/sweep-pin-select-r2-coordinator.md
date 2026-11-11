# Round 2 — `sweep-pin-select` (PR #526, backlog #533) — coordinator — NOT CONVERGED (Codex); one Medium DECLINED as pre-existing, one Low FIXED

Codex half: `docs/reviews/codex/sweep-pin-select-r2-codex.md` (NOT CONVERGED), on `2c659dfb`.

```yaml
round: 2
fixes_nontrivial: true
subject: sweep-pin-select
halves:
  codex: ran
  claude: gap
findings:
  - {id: R2-F1, severity: Medium, aim: deliverable, fix_induced: false, component: merge-ready-pins, disposition: declined}
  - {id: R2-F2, severity: Low, aim: deliverable, fix_induced: true, component: merge-ready-pins, disposition: fixed}
```

REVIEW GAP: claude — alternation (r2 runs ONE half).

**R2-F1 — DECLINED as a pre-existing class; filed as backlog #535.** Codex found three routes past
`harness_binding_problems`:
- `globals()['PINS_FILE'] = ...`;
- an imported `PINS_FILE`;
- an `own_pins_path()` that returns another file.

Each one left the merge gate READY while the harness enforced a lowered pin.

The class is "the merge gate trusts the harness's own pin loading". It was measured on origin/master `319bd152`, in a
temp worktree. In each run `check-anchors.py`'s manifest lost one entry and its pin literal stayed at 5. Each run was
scored by `pin_pair` + `pin_falls` + `hold_reasons`, by the head harness's `own_pin_problems`, `load_manifests` and
`pin_drift`, and by the harness's own `--self-test`:

| Variant on master | merge-ready | harness | `--self-test` |
|---|---|---|---|
| E1: a module-level `globals()['EXPECTED_MUTATIONS'] = {...4}`, with no other edit | head pin 5, `pin_falls` `[]`, `hold_reasons` `[]` | `own_pin_problems` reports 5 vs 4 | **rc 2, PINS_REFUSAL: caught** |
| E2: one line in `load_manifests`, `if target == "scripts/check-anchors.py": EXPECTED_MUTATIONS[target] = len(entries)` (backlog #431's input) | head pin 5, `[]`, `[]` | held 4, `pin_drift` `[]` | 310/310 rc 0; `--mutate . --only scripts/check-anchors.py`: 4 killed, rc 0 |
| E3: E1 plus an edit to `own_pin_problems` | head pin 5, `[]`, `[]` | `own_pin_problems` `[]`, `pin_drift` `[]` | 310/310 rc 0 |

A one-line harness edit on master (E2) lowers the enforced pin with every gate green. So R2-F1 is not a regression
introduced by this PR. ⚠ One route does differ. The bare data rebinding (E1) is refused on master, because master's
self-assertion reads `__file__`. The branch's self-assertion resolves through the same mutable `PINS_FILE`, so the
branch accepts that route. Every such route still edits `check-plan-code.py`. That edit selects the FULL sweep and is
in the reviewed diff, as E2 is on master.

Adding more AST shape checks would close one spelling at a time, so this fold does not add any. Backlog #535 names
the real defences: a harness-code change is FULL and reviewed, or `check-merge-ready` HOLDs any diff that touches the
pin-loading code. The r1 fix stays, because it closes the plain `PINS_FILE = "pins_v2.py"` rebinding that r1
measured. The BOUND comment above `PINS_BINDING` now names r2 and backlog #535.

**R2-F2 — FIXED, test-first.** The binding scan walked the whole tree. A helper's LOCAL `PINS_FILE` was therefore
counted as a second module binding, and the real harness became CANNOT RUN. The new case appends the reviewer's exact
helper (`def _helper(): PINS_FILE = "fixture.py"`) to the REAL harness. It also adds a local `EXPECTED_MUTATIONS` and
a class attribute to the synthetic harness. Before the fix the case was red ("PINS_FILE is written 2 times, not
once"). The new `module_writes` counts:
- stores in module scope, including under `if`, `for` and `try`;
- stores in a function that declares the name `global`.

It does NOT count a function's or a class's locals.

⚠ Counting only `tree.body`, as first proposed, would have reopened r1's refused case, "a `global` write in a
function". That case stays green.

Two mutations were added. Each was applied to a temp copy with `HOME` redirected. Each went red via the case it
names, and that case was green in an unmutated control copy (the control's 33 other reds come from the copy holding
only `scripts/`):
- "walk the whole tree" (`if isinstance(child, _SCOPES):` → `if False:`) is killed by the new F2 case;
- "ignore a function's `global` declaration" (`visit(child, decl)` → `visit(child, False)`) is killed by r1's
  rebinding case.

Self-test: `check-merge-ready` 264 → 265. Pin: `scripts/check-merge-ready.py` 102 → 104 in
`scripts/mutations/expected_mutations.py`.
Reviewed head: 2c659dfbe442ff20d400f58cf932026dfc9ebb3e
