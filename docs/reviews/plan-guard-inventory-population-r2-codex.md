# Post-Plan Gate — round 2 — Codex half

**Subject:** `docs/superpowers/plans/2026-09-02-guard-inventory-population.md` **v2** (`7e5811fb`).
**Scoped to v2's own fixes.** Branch `fix/guard-inventory-population`. **Backlog:** #72, #73.
**Date:** 2026-09-03.

**Provenance.** `scripts/codex-review.py --prompt-file`; fell through to **`gpt-5.5`**; 2,282-char
final message. `verdicts/plan-r2-codex.verdict.json`, `gate_ran=true`.

**VERDICT: NOT CONVERGED** — 2 Blocking, 1 High. (Round 1 was 4 Blocking; the curve is decaying but
⚠ a decaying curve from one half is not convergence.)

> **REVIEW GAP: claude** — the Claude half of this round **DID NOT RUN**. Dispatched twice against
> this same commit (`7e5811fb`); both attempts died on `API Error: 529 Overloaded`, a server-side
> fault, writing nothing and leaving the tree clean. `docs/plugins.md` permits a single re-run and
> then requires falling back rather than burning time, so the round ships one-sided **and says so**.
>
> ⚠ **Treat this half as NOT RUN, not as clean.** In every prior round of this slice the second half
> found Blockings the first missed — including the one that corrected the author's own guard count.
> The Codex verdict stands on its own findings only.
>
> **Partial substitute, executed by the author** rather than asserted: Blocking 1 was reproduced by
> building T1 Step 1 exactly as v2 wrote it in a temp copy and adding one deliberately failing case —
> `[FAIL] a DELIBERATELY failing probe … self-test: 21/21 passed … rc=0`. That recovers the *executed
> evidence* the missing half would have produced; it does **not** recover its independent search.
> **Re-attempt the Claude half against v3 in round 3.**

> **The scoping paid for the fifth time running.** Both Blockings are defects in v2's own fixes.

---

## Blocking 1 — `case()` is inert until T4, so T1–T3's red-green loops are FALSE

v2 added the helper in T1 Step 1 and left `self_test()`'s tally and return value on the **old**
`failures` variable and the old static `total` (`check-ratchet-contract.py:378-381`) until T4.

**Executed:**
```
$ python3 scripts/check-ratchet-contract.py --self-test; echo rc=$?
[FAIL] population_paths uses its default pattern: got ['scripts/check-a.py']
       expected ['scripts/check-a.py', 'scripts/gen-b.py']
self-test: 21/21 passed
rc=0
```

A new case fails, prints `[FAIL]`, and the command **exits 0 claiming every case passed**. Every
"Run it to make sure it fails" / "make sure they pass" step in T1, T2 and T3 is therefore
unfalsifiable — across multiple commits.

⛔ **v2's own fix, failing one joint on — the fifth instance in this slice.** T1 introduced the
helper's *state* and deferred the *accounting* that reads it.

**Resolution for v3:** the tally and return move into **T1 Step 1**, with the helper:
```python
    print(f"self-test: {state['total'] - state['failures']}/{state['total']} passed")
    return 1 if state["failures"] else 0
```
Every pre-existing loop is converted in the same step, so there is never a build where two accounting
systems disagree. T4 then covers only the CANNOT-RUN exit.

## Blocking 2 — T9's expected backlog counts are arithmetically impossible

T9 closes #72 and #73 **and** (Step 3, added in v2) files a new **open** `NO-CALLER:` row. The stated
expectation still reads `87 / 57 / 30`.

**Recomputed through the owning parser:**
```
now                                              TOTAL 87  OPEN 59  CLOSED 28
close #72,#73 (−2 open, +2 closed) + add 1 open  TOTAL 88  OPEN 58  CLOSED 30
plan v2 says                                     TOTAL 87  OPEN 57  CLOSED 30
```

T9 Step 5's own assertion would fail. ⚠ **The number was right before v2 added the row, in the same
editing pass, and was never re-derived — the seventh instance in this slice of stating a count from a
prior state.** v3 states `88 / 58 / 30`.

## High — the closed-row marker belongs in the ITEM cell, not the Status cell

v2 says *"each closed row's **status cell** must lead `✅ (was 🟠)`"*. The guard
(`scripts/check-docs.py:456`) is:

```python
        num, item, status = cells[1].strip(), cells[2].strip(), cells[-2].strip()
        if "✅" in status and item[:1] in severity:
```

— the **Item** cell must stop leading with a bare severity marker once the Status cell contains `✅`,
and the error text says *"Write `✅ (was {item[:1]})` instead"*. A literal implementation of v2 leaves
the Item cell as `🟠 …` and `check-docs.py` fails.

---

## Disposition

All three accepted; all re-verified by the author against the code. v3 moves the tally into T1 Step 1,
restates the counts as 88/58/30, and points the marker instruction at the Item cell.

Claude half: [`plan-guard-inventory-population-r2-claude.md`](plan-guard-inventory-population-r2-claude.md).
