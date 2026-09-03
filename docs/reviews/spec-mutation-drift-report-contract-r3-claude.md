# Spec review round 3 — Claude half — mutation drift report contract

**Subject:** spec **v3**, SCOPED to v3's own changes (the state machine). **Date:** 2026-09-03.
**Verdict: NOT CONVERGED — 1 High.** ⛔ **CORRECTED AFTER THE CODEX HALF LANDED: there IS a
Blocking, and this half missed it. See §CORRECTION at the end. The "no Blocking" claim below and the
"five states are complete" claim in §Checked are both WRONG and are left standing so the error is
legible.**

> **METHOD.** Coordinator-written (standing session instruction). Written to the scratchpad **before**
> the Codex half was dispatched, not concurrently — the concrete application of round 2's finding that
> `codex-review.py` cannot distinguish the coordinator's writes from the agent's. Ordering fixes the
> cry-wolf; exclusion was never needed.

---

## H1 — 🟠 The same defect exists in a SECOND function, and §8 excludes it by CI status rather than by whether it is there

**MEASURED with `ast`, then read.** `check-plan-code.py` has **two** functions that build an `ev` and
hand it to a tally printer in `main`:

| producer | initializer | not-run return | measure call | printer |
|---|---|---|---|---|
| `mutate_delivered` `:576-663` | `:584` | `:586`, `:626`, `:646` | `run_mutations` `:647` | `main:2072-2074` |
| **`check` `:790-838`** | **`:793-794`** | **`:797`** | `run_mutations` `:832` | **`main:2107-2108`** |

`check:795-797`:

```python
if not files:
    report.append("no `<!-- file: … -->` tagged Python blocks found — nothing to assemble")
    return False, report, ev          # ev is still the :793 initializer
```

`main:2107` then renders that empty `ev` as:

```
FAILED — plan's copy only, NOT compared: 0 file(s), 0 mutation(s), 0 survivor(s)
```

**That is S0, in a second function, reached by a different mode.**

**What the spec says, and why it is not enough.** §8 reads: *"The `<plan> --compare --verify-evidence`
mode is untouched and remains out of CI."* That is a true statement about its **CI status**. It says
nothing about whether the defect this spec exists to fix is **present** there. It is.

**This is the shape the repo has a script for.** `mutate_delivered` and `check` are **two
implementations of one reporting contract** — same `ev` keys, same three-number final line, same
not-run hazard. Fixing one and silently leaving the other guarantees they diverge, which is
`check-vocabulary-collisions.py`'s whole subject: *one mechanism per concern*. And a spec that bounds
its scope without naming what is inside the excluded region is the completeness-claim failure this
project keeps catching — *"a claim in the one comment whose job is to bound a gap is worse than no
claim."*

**The enumeration extends cleanly, which is the good news.** `check` has no after-control, so it
cannot reach S4. Its states are a strict subset:

| | `mutate_delivered` | `check` |
|---|---|---|
| `"not-run"` | `:586`, `:626`, `:646` | `:797` |
| `"measured"` | `:648` | after `:832` |
| `"invalidated"` | `:657` | **unreachable — no after-control** |

So `ev["verdict"]` is **one contract with two producers**, and `check` simply never emits the third
value. That is a stronger design than v3 currently claims, and it costs one extra transition to say so.

**Required change — one of two, and the choice is real:**

- **(i) Widen the spec.** `ev["verdict"]` becomes the contract for *both* producers; `check` sets
  `"not-run"` at `:793` and `"measured"` after `:832`. Both printers honour R1. **Recommended** — it
  is two lines, and it is the difference between fixing an instance and fixing the class.
- **(ii) Keep the scope, state the defect.** §8 says explicitly that `check:797` has the same shape,
  that it is deliberately not fixed here, and why (out of CI, lower stakes). Acceptable only if the
  sentence names the defect rather than the CI status.

**Falsifier:** `python3 scripts/check-plan-code.py <a-plan-with-no-tagged-blocks>` — the final line
must not contain `mutation(s)`, `survivor(s)` or `file(s)`. ⚠ **NOT RUN** — I did not construct the
input. Labelled a hypothesis from reading `:795-797` and `:2107`, though the code path is unambiguous
and the `ast` enumeration of both functions was executed.

---

## Checked and correct in v3

- **The five states are complete for `mutate_delivered`.** Re-enumerated with `ast`: four returns
  (`:586`, `:626`, `:646`, `:663`), and `:663` splits on the after-control. No fifth return.
- **The three transition points are right.** `:584` initializer, `:648` immediately after
  `run_mutations` returns, `:657` beside `ok = False` in the after-control loop. Each sits where the
  fact becomes true, not at a convenient landmark — which was the whole point of (b).
- **The arity argument holds.** S3-with-survivors and S4 are both `ok=False` (`:773`, `:779` for the
  survivor path), so no boolean can separate them. Option (c) stays refuted for the second round.
- **F2's five recipes map one-to-one onto the five states**, and F2-S4 reuses the shipped fixture at
  `:1918-1933` rather than inventing one.
- **F4 names the right transition.** `:657` has no second reader; `:648`'s deletion is caught by
  F2-S3 losing its `OK —` line.
- **An exception escaping `run_mutations`** is not a sixth state: `mutate_delivered` raises rather
  than returns, so no final line is printed at all. Out of scope correctly, though the spec does not
  say so.

## Verdict

**NOT CONVERGED — 1 High, 0 Blocking.**

**This is the first round in nine with no Blocking, and the first whose finding is not inside the
previous round's fix.** H1 is about a region v3 deliberately did not touch, not about what it
changed. That is the signal (b) was supposed to produce: enumerating the states closed the class
*within* the enumerated function, and what remains is the boundary of the enumeration rather than
another hole inside it.

---

# CORRECTION — appended after the Codex half landed

**This half MISSED a Blocking, and the miss is the same class it was reviewing.**

Codex found a **sixth state** and I reproduced it. `run_mutations` can refuse a mutation before
applying it — `:703-708`, anchor not found → `ok = False`, report line, `src = None`, `break`, then
`continue` at `:711`, so the entry never enters `m_muts`. Control flow then proceeds normally:
`:648` assigns the (short) lists, the after-control at `:654-662` passes, and `:663` returns.

**Reproduced on the real corpus**, one anchor broken, entry count unchanged so no drift:

```
✗ mutation 'the allowlist stops being forced to shrink': anchor NOT FOUND — it was not
  applied, so its 'caught' verdict would be meaningless
FAILED — delivered scripts mutated: 7 file(s), 161 mutation(s), 0 survivor(s)
```

⚠ **161 of 162 — not zero.** Codex's minimal fixture had one declared mutation and so showed
`0 mutations`; on the real corpus the state prints a **nearly complete, entirely plausible tally**.
`0 survivor(s)` across 161 mutations reads as coverage confirmed. Under v3 this is `"measured"`.

## Why this half missed it, and it is not carelessness

§Checked says *"the five states are complete… re-enumerated with `ast`: four returns… no fifth
return."* **That claim is true and irrelevant.** I enumerated **return sites** and split the last one
by the after-control — which is a *finer-grained position*, not the property.

**So v3's state machine was still positional.** It is the same error as v1 (`copytree`) and v2
(`run_mutations` returned), at a third level of granularity, committed inside the artifact written
specifically to stop making it. The property is *"was every declared mutation applied and measured"*,
and it has a failure mode that has nothing to do with which line returned.

**The dimension I should have enumerated:** not *where does control leave*, but *what can make the
tally untrustworthy*. On that axis the list is longer and does not align with returns at all:

| # | what makes the tally untrustworthy | detected at |
|---|---|---|
| 1 | manifests unusable | `:586` |
| 2 | declared coverage disagrees | `:626` |
| 3 | control red before any mutation | `:646` |
| 4 | **a declared mutation was never applied** | `:703-708`, surfaces at `:663` |
| 5 | after-control red | `:657`, surfaces at `:663` |
| — | *survivors found* | `:773`/`:779` — **trustworthy**, a real verdict |

Note 4 and 5 both surface at the same return, and the last row is `ok=False` yet perfectly
trustworthy. **No partition of return sites can express that**, which is why three rounds of
increasingly fine landmarks kept failing.

## Verdict, corrected

**NOT CONVERGED — 1 Blocking (Codex), 1 High (this half), 2 Medium (Codex), 1 Low (Codex).**

The Low is this half's H1 at lower severity, and Codex is right to downgrade it: `ci.yml:261-262`
runs only `--mutate .`, so the `check()` path is genuinely out of CI. The wording fix stands.
