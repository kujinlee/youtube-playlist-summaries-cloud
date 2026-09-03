# Code review round 1 — Claude half — `ev["trustworthy"]` in check-plan-code.py

**Subject:** commit `4c3d3390`, `scripts/check-plan-code.py` + `scripts/mutations/check-plan-code.json`.
**Date:** 2026-09-03. **Verdict: ~~CONVERGED~~ → NOT CONVERGED.** ⛔ **CORRECTED after the Codex half: there IS
a Blocking and this half asserted the opposite. See §CORRECTION. The wrong verdict is left
standing so the error is legible.**

> **METHOD.** Coordinator-written (standing session instruction). ⚠ **I am the author of this code**,
> which is a real weakness; the mitigation was to enumerate reachability with `ast` and to **execute**
> every claim rather than reason about it. The one finding I expected to file was **refuted by
> running it**. The Codex half ran independently.
>
> ⚠ **THIS IS THE FIRST REVIEW OF THE CODE.** The three prior rounds reviewed the SPEC. The user
> asked directly whether dual review had happened; it had not, for the implementation.

---

## The reachability analysis — `ok` × `trustworthy`

`trustworthy` is only ever set False at four sites, and **every one of them also sets `ok = False`**
(the three skips in `run_mutations` and the after-control). Verified by reading all four.

| `ok` | `trustworthy` | reachable? | printer branch |
|---|---|---|---|
| True | True | yes — clean run | `OK — … tally` |
| False | True | yes — **real survivors / expect mismatch** | `FAILED — … tally` |
| False | False | yes — the five not-measured states | `NOT MEASURED — …` |
| **True** | **False** | **UNREACHABLE** | — |

**This is the property that matters:** the `NOT MEASURED` branch cannot be reached by a run that
succeeded, and a run with genuine survivors still prints its full tally — which is the requirement
that killed option (c) (branching on `ok`) in spec round 1. The two booleans are *not* redundant:
`trustworthy=False ⟹ ok=False`, but **not** the converse, and the converse is the whole point.

## The arithmetic is sound, not coincidental

`len(m_muts) == len(muts)` is the discriminator. Enumerated the per-mutation loop with `ast`:
**two append sites (`:753`, `:793`), each followed by `continue` or the end of the loop body**, so at
most one append per iteration. Therefore `len(ev_muts) ≤ len(muts)` always, with equality **iff no
mutation was skipped**. Two skips cannot cancel a double-append, because a double-append cannot
happen.

Both append sites record a real verdict (`caught` True or False). Neither records a skip. So the
equality means exactly *"every declared mutation produced a verdict"*.

## L1 — 🟢 REFUTED BY EXECUTION, recorded because I nearly filed it

**The claim I was going to make:** an empty manifest set gives `len(m_muts) == len(muts) == 0`, so
`trustworthy` would be True over zero mutations — a vacuous green, and *"a zero is the dangerous
shape"* is this project's own lesson.

**Ran it.** `EXPECTED_MUTATIONS = {}` with an empty `scripts/mutations/`:

```
NOT MEASURED — the mutation harness produced no coverage verdict. Treat this as NOT CHECKED.
```

**No false green.** `load_manifests` returns problems, so the function exits at the early return with
`trustworthy` still at its **initializer default of False**. The default-deny is doing real work here,
not just documenting intent — which is the argument for defaulting False rather than computing the
flag at the end.

**Left at 🟢 rather than dropped**, so the next reader knows the case was tested rather than
overlooked.

## Accepted scope gap — NOT a new finding

`check()` builds its own `ev` and `main` prints a tally from it at the other call site; neither sets
`trustworthy`, and that printer is unchanged. **No `KeyError` risk** — the only consumer of the key is
`main`'s `--mutate` branch, whose `ev` always comes from `mutate_delivered`, which always sets it in
the initializer.

This is the gap the Codex half of spec round 3 rated **Low**, correctly: `ci.yml:261-262` runs only
`--mutate .`, so `check()` is genuinely out of CI. **Restated here so it is a recorded decision rather
than an omission**, since the spec's §8 wording was criticised for describing the CI status instead of
the defect.

## Verified by execution, not by reading

- `--self-test` **160/160**, including the two new cases.
- `--mutate .` **163 mutations, 0 survivors, exit 0**, and the clean line is byte-identical to before
  the change: `OK — delivered scripts mutated: 7 file(s), 163 mutation(s), 0 survivor(s)`.
- **The new mutation is caught via its named case.** 0 survivors *and* no expect-mismatch report
  means the `expect` binding held — `run_mutations` verifies the named case actually went red, so a
  green run is proof the mutation reddens what it claims.
- All six states S0–S5 exercised; the two failing-message defects found during the build (the
  orphaned anchor, the self-contradicting S4 sentence) are fixed and re-run.

## Not checked

- **`--compare` / `--verify-evidence` end-to-end.** Out of CI and out of scope; I did not run it.
  A regression there would not be caught by anything I did.
- **Performance.** Two extra dict writes per run; not measured, and not plausibly material.

## Verdict

**CONVERGED.** No Blocking, no High. The design is the one the three spec rounds converged toward
only after the third attempt, and it is the first version whose discriminator is a fact about the run
rather than a position in the control flow.

⚠ **One reviewer's CONVERGED is not convergence** — this project has measured a confident-but-wrong
CONVERGED twice. The Codex half is the check on this one, and I am the author besides.


---

# CORRECTION — this half was WRONG, and wrong in the way it was reviewing

**Codex found a Blocking. My verdict was CONVERGED. I was the author.**

## The finding

`:751-757` — `rc == 2` is `run_suite`'s **CANNOT RUN** (a timeout). It **appends to `ev_muts`** and
to `ev_survivors`, so the cardinality balances, `trustworthy` stayed True, and the printer rendered:

```
FAILED — delivered scripts mutated: 1 file(s), 1 mutation(s), 1 survivor(s)
```

A two-minute NOT CHECKED presented as a survivor — **the exact defect class this change exists to
remove, surviving inside its own fix.** Codex reproduced it; I reproduced Codex's reproduction.

## Why this half missed it — and it is not the same excuse as last time

§*The arithmetic is sound* says: *"Both append sites record a real verdict (`caught` True or False).
Neither records a skip."* **The first clause is false.**

I enumerated the append sites **with `ast`, for cardinality** — that part is right, and the
"at most one append per iteration" claim still holds. Then I asserted what those appends **MEAN**
without reading the branch three lines above one of them. Cardinality was measured; semantics was
assumed.

⚠ **The code told me, in a comment, and I did not read it:**

> `# rc 2 is run_suite's CANNOT RUN — a timeout. Reading it as red records two minutes of NOT
> CHECKED as proof that a guard works… The comment on run_suite said rc 2 must not be readable as
> either verdict and its very next caller read it as one. Measured round 5, M2.`

That comment records the *same defect being found before*, at the same line, and my review walked
past it. **This is the fourth time today a `check-plan-code.py` guard has been fooled by counting the
right things and mis-reading what one of them meant.**

## The fix, and its falsifier

Entries are now marked: `"measured": False` on the cannot-run append, `"measured": True` on the
normal one. `trustworthy` requires **both** cardinality and every entry being a verdict:

```python
ev["trustworthy"] = (len(m_muts) == len(muts)
                     and all(m.get("measured") is True for m in m_muts))
```

`.get("measured") is True` **fails closed** — a future append site that forgets the key yields
`None`, which is not `True`, so the run is untrusted rather than trusted. That was chosen over
`m["measured"]` (which would crash the harness) and over `.get(..., True)` (which would default to
trusted, the exact shape being fixed).

**Verified against Codex's own scenario:** rebuilt its fixture, called `main(["--mutate", tmp])`
in-process with `run_suite` stubbed to time out the mutated run only —
`NOT MEASURED … Treat this as NOT CHECKED.`, exit 1.

**Coverage:** two new cases (**162/162**) — one asserting a timed-out mutation is counted but not
trusted, one asserting it is reported as a cannot-run. One new mutation deleting the `all(...)`
conjunct, reddening the first of those (**164 mutations, 0 survivors**). `EXPECTED_MUTATIONS` 22→23,
sum 163→164, docstring 160→162 — the last caught by `count_drift` for the third time today.

## What this says about the verdict I gave

**A CONVERGED from the author is the weakest verdict available**, and this is the record of why.
`docs/plugins.md` already says a single CONVERGED was wrong 4 of 5 times; add one.

The parts of this half that survive are the ones stated as **checkable claims** — the reachability
table, the at-most-one-append cardinality, the refuted vacuous-green case. The part that failed is
the one stated as a **characterisation**. That is a usable distinction for the next review: assert
what can be contradicted, and mark the rest as unverified.
