# The coverage verdict becomes a type you cannot read wrongly

> **Anchor:** `status-visibility` — **ADR:** none
> **Goal:** A person who was away can see the current state, what changed, and what needs them —
> without reading the chat transcript.

**Backlog #91.** v1.1 — §5 Q1 decided (own module). From Architecture Review #7 (`docs/reviews/architecture-review-2026-09-03b.md`),
which fired on the four-non-converging-rounds trigger. **v1, 2026-09-04.**

⚠ **Header order is load-bearing** — `check-anchors.py:61` sets `HEAD_LINES = 10`, so the Anchor and
Goal must sit in the first ten lines. Version notes go **below** the declaration. This has turned the
gate red before.

---

## 1. The problem, measured

Seven consecutive adversarial review rounds each found a defect inside the previous round's fix. Not
one of those fixes was wrong. Measured by AST over the delivered file (`scratchpad/phase6-ev.py`):

```
  ev keys: 7    written by: 2 functions    touched by: 6 functions
  ev['trustworthy']  WRITTEN by check, mutate_delivered
                     READ    by evidence, main            <- 2 of the 6
  check() reads mutations, survivors AND files — and never reads trustworthy
```

`ev` is a plain dict. Any producer writes any key; any consumer reads any key. The rule that matters
— **never read a tally without consulting the verdict** — lives only as convention, re-implemented or
forgotten at each of six sites.

**Every one of the seven defects was one of two shapes:**

| shape | rounds |
|---|---|
| a **producer** set `trustworthy` while holding only part of its contract | r3 (2 of 3 clauses), r4 M1 (`controls_green` meant two things) |
| a **consumer** read a tally without consulting `trustworthy` | r2 (`check`), r3 B4 (`evidence` header), r4 B1 (`--mutate` printer), r4 H1 (`evidence` body) |

The rounds were not failing. **They were enumerating** — one consumer per round — through a set a
real interface closes in one move.

## 2. The decision

**A tagged union.** The numbers exist *only* on the measured variant, so a consumer cannot reach a
tally without having first handled the not-measured case — there is nothing to reach.

⛔ **The guarded-accessor alternative is REJECTED, and the reason must not be re-litigated.** Keeping
one object and making `.tally()` return `None` when untrustworthy fails exactly as
`verdicts_are_trustworthy` already failed in r3: that helper **was** the "one shared rule" fix, and it
still shipped holding two of its three clauses, because nothing stopped a caller from being wrong. A
guarded accessor is a convention with a nicer name. This project has now paid seven rounds to learn
that conventions are forgotten in the sibling.

## 3. The interface

```python
@dataclass(frozen=True)
class Measured:
    """Every declared mutation produced a real verdict, over green controls."""
    files:     dict[str, dict]
    declared:  int
    mutations: list[dict]      # len() == declared, every entry measured
    survivors: list[str]

@dataclass(frozen=True)
class NotMeasured:
    """The run produced no coverage verdict. There is no tally to read."""
    reason:    str             # the CANNOT RUN / shortfall sentence, already rendered
    declared:  int | None      # None when mutations were never attempted
    entries:   list[dict]      # NOT `mutations`. See below.
    files:     dict[str, dict] # control runs only — never a coverage claim

CoverageVerdict = Measured | NotMeasured
```

**Three properties, and the third is the one that earns the change:**

1. **`NotMeasured` has no `survivors` field at all.** `0 survivor(s)` is this project's success
   sentence; on a run that measured nothing it is the single most misleading number available. It is
   not gated — it does not exist.
2. **The list is called `entries`, not `mutations`.** A consumer that copies a line from the measured
   path onto an unmeasured verdict gets an **`AttributeError`**, not a plausible wrong number. The
   rename is the mechanism, not cosmetics.
3. ⭐ **`Measured`'s constructor enforces all three clauses.** The contract moves out of a predicate a
   caller may forget to call and into a constructor that cannot be bypassed:
   - controls green,
   - `len(mutations) == declared`,
   - every entry `measured is True`.

   Constructing a `Measured` that violates any of them raises. **There is no path to a tally that
   skips the checks** — which is precisely what six rounds kept finding a path around.

## 4. Falsifiers

Each is an observation that would make this spec **fail**. A guard with no falsifier is a checkbox.

| # | Falsifier | Expected |
|---|---|---|
| F1 | Construct `Measured` with `len(mutations) != declared` | **raises** |
| F2 | Construct `Measured` with any entry whose `measured` is not `True` | **raises** |
| F3 | Construct `Measured` with `controls_green=False` | **raises** |
| F4 | Read `.survivors` on a `NotMeasured` | **AttributeError** |
| F5 | Read `.mutations` on a `NotMeasured` | **AttributeError** (the field is `entries`) |
| F6 | ⭐ A clean `--mutate .` run's stdout, byte-for-byte vs today | **identical** (F2-S3) |
| F7 | A clean plan-mode run's stdout and evidence block, byte-for-byte | **identical** |
| F8 | Delete the constructor's clause-checking and run `--self-test` | **goes red**, naming the case |

⚠ **F6 and F7 are the ones that make this safe to ship.** Every previous round preserved them, and
the one time round 4's fix changed output on a path nobody printed, the mutation harness caught it.

## 5. Open questions — carried in deliberately, not resolved here

**Q1 — ⭐ DECIDED 2026-09-04 by the user: its OWN MODULE, `scripts/coverage_verdict.py`.**
Not an open question any more. Only `count_drift` is importable by another guard today, so a separate
module is where a shared seam can later grow; staying inline would help exactly one guard and mean
moving it the moment a second wanted the same thing. **Cost accepted: one more file, and the import
must not create a cycle** — `check-plan-code.py` imports the verdict, never the reverse. ⚠ **This does
NOT pre-commit the wider seam of Architecture Review #7 finding 2** (one self-test-result module
across sixteen guards). One adapter is a hypothetical seam; that stays a separate decision with its
own cost argument.

**Q2. What happens to `verify_evidence`?** It re-derives the evidence block and compares against the
pasted one. Under the union it would render and compare a `NotMeasured` block — correct, but it makes
**the pasted block's grammar part of the interface**. That is a real widening and should be stated in
the plan, not discovered in review round 5.

**Q3. The ~10 hand-built `ev` dicts in `_self_test`.** They become constructor calls. Some deliberately
build *invalid* states to test the renderer; those must be able to keep doing so, or F1–F3 make them
unwritable. Likely needs an explicit escape hatch for tests, which is itself a hole worth naming now.

## 6. Out of scope

- Findings 2, 3 and 4 of Architecture Review #7 (the shared self-test seam; splitting the 2,517-line
  module; the two guards CI never runs). Separate items.
- Any change to *what* the harness measures. This is about how the result is **reported and read**.
- The six other guards' evidence structures. One guard first; generalise only if a second wants it —
  **one adapter is a hypothetical seam, two adapters is a real one.**

## 7. What this does NOT fix, stated rather than discovered later

An interface stops a consumer reading a tally it should not. **It does not stop a producer computing
`controls_green` wrongly** — that was r4 M1, and the answer there was `control_is_green(rc, out)`,
already shipped. If round 5 finds an eighth defect, the honest prediction is that it will be in the
*production* of a clause, not the *consumption* of a verdict. This spec narrows the class; it does not
close it, and claiming otherwise would repeat the overclaim that has cost this slice six rounds.
