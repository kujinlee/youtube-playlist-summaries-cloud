# Post-Plan Gate — round 1 — Codex half

**Subject:** `docs/superpowers/plans/2026-09-02-guard-inventory-population.md` (`3fd19b16`),
implementing spec v4. Branch `fix/guard-inventory-population`. **Backlog:** #72, #73.
**Date:** 2026-09-02.

**Provenance.** `scripts/codex-review.py --prompt-file`; `-sol`/`-terra`/`-luna` HTTP 400, fell
through to **`gpt-5.5`**; 3,046-char final message. `verdicts/plan-r1-codex.verdict.json`,
`gate_ran=true`.

**VERDICT: NOT CONVERGED** — 2 Blocking, 1 High, 1 Low. All four re-verified by the author; none
disputed.

---

## Blocking 1 — the plan's self-test snippets call a `case()` helper that does not exist

T1, T2 and T3 all write cases as `case("label", got, expected)`. **`scripts/check-ratchet-contract.py`
has no such helper.** Its `self_test()` (`:338`) is explicit loops over table constants:

```python
    for name, text, expected in CASES:
        got = sorted({v.rule for v in check_contract("t.py", text)})
        if got != sorted(expected):
            print(f"  FAIL {name}\n       expected {sorted(expected)}\n       got      {got}")
            failures += 1
```

T1's Step 4 would `NameError` rather than pass. **CONFIRMED** — `grep "def case"` over the target
returns nothing.

⚠ **The plan wrote tests against an API it imagined**, which is this repo's recorded
*"a mocked boundary tests the contract you IMAGINED"* shape, one level up. v2 either adds a real
`case()` helper as an explicit step, or writes every case in the file's existing idiom.

## Blocking 2 — T7's first mutation STILL survives: T1 extracted the function, not the call site

The manifest mutates `population_paths(ROOT / "scripts", "*.py")` — **the call site, which is inside
`main()`**. `check-plan-code.run_suite:376` runs only `check-ratchet-contract.py --self-test`, and
every case drives `population_paths(...)` and `discover_guards(...)` **directly**. `main()` is still
driven by nothing.

**Executed by the reviewer:**
```
control_payload=True  mutated_payload=True
mutated_line=population_paths(ROOT / "scripts", "check-*.py")
```

The named payload case stays green, so `--mutate .` records SURVIVED and CI fails.

⛔ **This is the author's own T1 fix failing at the next joint** — the fourth time in this slice that
a fix has been where the next defect lives. T1 made the *function* reachable; the mutation targets
the *argument at an unreachable call site*.

**Resolution for v2:** mutate the **default parameter in the signature**
(`pattern: str = "*.py"` → `"check-*.py"`), which the suite's own `population_paths(scripts)` call
does exercise — and restructure T1's cases so they call it without an explicit pattern, so the
default is load-bearing.

## High — the whitespace mutation turns TWO cases red; `expect` may name only one

`and value.value.strip()` → `and value.value is not None` accepts **both** `NOT_A_GUARD = ""` and
`NOT_A_GUARD = "   "`. `check-plan-code.py:782-786` requires each `expect` to match exactly one red
case.

**CONFIRMED, executed by the author across control and two candidate mutations:**

| case | control | plan's `is not None` | proposed `!= ""` |
|---|---|---|---|
| empty reason | green | **RED** | green |
| whitespace-only | green | **RED** | **RED** |
| real reason | green | green | green |

**Resolution for v2:** mutate to `and value.value != ""` — exactly one red case, and it is the one
the entry names.

## Low — the ordering section omits T2/T3-before-T7

T7's anchors (`tree.body`, `value.value.strip()`, `compile(...)`) and its expected case names
(`NOT_A_GUARD: …`, the widened payload case) do not exist until T2 and T3 land. The *"Known ordering
constraints"* block names only T1-before-T7 and T4-before-T7.

---

## Disposition

All four accepted. v2 must: supply or drop `case()`; retarget mutation 1 onto the signature default
and rewire T1's cases to depend on it; change mutation 3 to `!= ""`; and complete the ordering block.

Claude half: [`plan-guard-inventory-population-r1-claude.md`](plan-guard-inventory-population-r1-claude.md).
