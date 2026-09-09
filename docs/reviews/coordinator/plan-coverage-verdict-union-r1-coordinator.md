# Post-Plan Gate round 1 — coordinator half — backlog #91 coverage-verdict union

Branch `coverage-verdict-union-91`. Subject: the union, the rewire, the retargeted manifest, and
`docs/superpowers/plans/2026-09-08-coverage-verdict-union.md`.

Partner half: [`../claude/plan-coverage-verdict-union-r1-claude.md`](../claude/plan-coverage-verdict-union-r1-claude.md)
— **NOT CONVERGED**, 0 Blocking, 3 High, 2 Medium, 4 Low.

---

## The Codex half CANNOT RUN — treat it as NOT RUN, not as a pass

**REVIEW GAP:** codex — every candidate model failed (3× HTTP 400, gpt-5.5 timed out); the wrapper
recorded `gate_ran=false` and wrote no review. A Claude adversarial half ran in its place per
`docs/plugins.md`; a replacement half is dispatched for round 2. Re-attempt Codex before merge if
access returns.

`scripts/codex-review.py` was run from the coordinator with `dangerouslyDisableSandbox`, prompt in a
file. **Every candidate model failed**, so the wrapper refused to write a review and recorded
`gate_ran=false` — the correct behaviour, and the reason a caller must never trust an exit code alone:

```
gpt-5.6-sol:   try_next — CLI reported HTTP 400
gpt-5.6-terra: try_next — CLI reported HTTP 400
gpt-5.6-luna:  try_next — CLI reported HTTP 400
gpt-5.5:       try_next — timed out — any partial message is an incomplete review
rc=1   "no candidate produced a usable review"
```

Verdict artifact: `docs/reviews/verdicts/plan-coverage-verdict-union-r1-codex.verdict.json`.

⚠ **Renamed on arrival.** The wrapper derives the verdict stem from `--out`, and `--out …/r.md`
produced `r.verdict.json` — a generic name in a namespace with **no allocator**, where a collision
overwrites silently and `ls | uniq -c` can never see one. It was untracked, so nothing was lost;
renamed to the review's stem. **Pass a distinctive `--out` stem.**

**Per `docs/plugins.md`, Codex-unavailable is never a blocker:** fall back to a Claude adversarial
review and note the gap. A replacement adversarial half is dispatched for round 2, with a different
lens rather than a re-run of the same one — a decaying severity curve from one reviewer is not
convergence, and this project has a recorded case of a single confident CONVERGED clearing a live
defect. **The Codex-specific pass should be re-attempted before merge if access returns.**

---

## Adjudication — all three Highs ACCEPTED and FIXED

I read each finding against the code rather than taking the verdict. All three are production-side,
which is what spec §7 predicted; the reviewer correctly noted that three-for-three is corroboration,
not proof, and that the prediction is close to unfalsifiable once consumption is a type error.

### H1 — `controls_green` defaulted to `True` — ACCEPTED

The finding lands on the coordinator directly. This branch removed `evidence()`'s `ctx=RunContext()`
default and argued *at length* that a defaulted parameter is a fail-open of the exact class the change
exists to remove — then left `controls_green: InitVar[bool] = True` one file away, on the single clause
r2 dropped and r3 B1 had to restore. Fixing the instance and not the class, inside the change that
argues against doing so.

**Fixed:** default removed; `check-plan-code.py`'s honest-zero return passes it explicitly.

### H2 — the honest zero hardcoded `declared=0` — ACCEPTED

`extract()` can return non-empty `muts` with empty `files`, and the early return threw `muts` away, so
clause 2 passed over a number the producer *invented*. Master printed the same words but carried
`declared: None` — honestly "never attempted"; a `Measured` positively asserts zero *were* declared.
The union makes the lie explicit and typed, which is an argument for fixing it, not for tolerating it.

**Fixed:** branch on `muts` — `Measured` for the true honest zero, `NotMeasured.from_counts` otherwise.

### H3 — `RunContext.compared` was `None` on the early return even with `--compare` — ACCEPTED

Pre-existing (master reproduces it), but High because it is live, it is on the **durable** artifact,
and this branch's own T5 claims the class is closed. T5 removed the default-argument route to the
wrong subject line and left the early-return route — the one reachable from the command line. The
reviewer flagged this as a shape and explicitly did **not** implement or run it; the coordinator did.

**Fixed:** `compared = {} if compare is not None else None` before the early return.

---

## Verification of the fold — every fix has a falsifier, and each was RUN

`scratchpad/verify_r1_fixes.py`, throwaway copies, **control first** (`coverage_verdict` 22/22 rc=0,
`check-plan-code` 201/201 rc=0). Each fix reverted; the suite must go red **through the case added
for it**, not merely red:

| reverted | suite | result |
|---|---|---|
| H1 — restore `= True` | `coverage_verdict` | 21/22 — ✅ red via `H1 clause 1 has no default` |
| H2 — hardcode `declared=0` | `check-plan-code` | 199/201 — ✅ red via `declaring mutations with nothing to assemble` |
| H3 — `compared=None` | `check-plan-code` | 200/201 — ✅ red via `does NOT report 'compare was not given'` |

H2 and H3 each ship with a **presence twin**, because an absence assertion alone is vacuous here:
the honest zero must still be a `Measured(declared=0)` (T2a preserved), and a run *without*
`--compare` must still say so.

Counts moved 196 → **201** and 21 → **22**; both declared counts updated, and
`check-selftest-counts.py` reports **29 declare, every one verified by running it**.

## Mediums and Lows

M1 (`NotMeasured`'s integrity is a convention, not a constructor) and M2 (`Measured` is frozen but
stores lists by reference, while `NotMeasured.from_counts` copies) are **real and unfixed**. Both are
about the *unmeasured* variant and the mutability of an already-validated object; neither is reachable
from a current call site. They are carried to round 2 rather than fixed silently, because M1 in
particular argues the union is asymmetric in exactly the way the module's own thesis warns about.

## Verdict

**NOT CONVERGED at round 1** — 3 High found, all fixed and each falsified. Round 2 is required, and
must be scoped to **round 1's own fixes**, because this project's recorded failure mode is a defect
introduced by the previous round's fix. The Codex half remains **NOT RUN**.
