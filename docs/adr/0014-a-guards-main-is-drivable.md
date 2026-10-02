---
status: accepted 2026-10-01 (scoped Phase 6 architecture review, armed by THRASHING after nine
  review rounds on `semantic-recall-replication`; user chose the review over folding per-instance).
  Records a rule about the VERIFICATION STACK, which until now was governed by nothing — all
  thirteen prior ADRs govern the product. Supersedes nothing; it BOUNDS how a guard is built, which
  had no stated bound before, and it supersedes backlog #213's proposed remedy.
  ⚠ ACCEPTED IS NOT IMPLEMENTED: 1 of 36 guards satisfied this before today and a second
  (`check-ratchet-contract.py`) satisfies it now. The remaining 29 are pinned debt, not compliance.
---

> **Anchor:** `review-decides-itself` — **ADR:** 0014
> **Goal:** A review loop decides its own next step — run, stop, or escalate — from recorded evidence rather than recall, and reaches the human only for decisions that are genuinely theirs.

# ADR-0014 — A guard's `main()` takes its world as a parameter, and its self-test drives it

## Context

One defect recurred **eleven times in nine review rounds** on one fold, while every other component
of that fold converged. Its shape: a rule's result is computed and then discarded at its call site,
with every named self-test case still green and the live guard printing OK over a real violation.

Each round fixed its instance correctly. Each fix created the next one. The fossil record is in the
code's own docstrings, two generations deep — `check-ratchet-contract.py:219` *"EXTRACTED FOR THE
WIRING, not for tidiness"*, then one level out at `:990` *"EXTRACTED TO MAKE THE WIRING TESTABLE —
round 8's two Blockings"*.

**The mechanism.** Every `main()` resolved its world from module globals (`ROOT`, `MATCHER`,
`HOOK`, `BASELINE`, …). A case can call any function a guard defines, but it cannot point `main` at
a world it built — so `main` is the one region no case reaches. The standard repair, *extract the
rule so its internals become testable*, acts on the **callee**: it shrinks the uncovered region and
can never empty it, because `main`'s last act is always to build the world and hand it over, and
that act is below nobody.

> **The repair's direction is downward; the defect's home is upward.** Each correct fix relocates
> one statement from *coverable* into *the residue*, and the residue is exactly what no case reaches.

⭐ **The decision below was already implemented, once, by someone who hit this in another file and
fixed it properly.** `scripts/check-ci-watched.py:860` — *"Extracting `payload_from` was only half
the repair; the line that CALLS it was still unreachable."* It was the only guard of 36 built this
way, and the only one the class never touched in nine rounds. **It propagated to zero siblings**,
because a docstring is read by whoever opens that file and nothing carries it anywhere else. That
is why this is an ADR and not another comment.

## Decision

**A guard's `main()` takes its world as a defaulted parameter, and the guard's `--self-test` drives
`main()` over a world the case constructed.**

```python
def main(argv: list[str], root: Path = ROOT) -> int:
    ci_path = root / ".github/workflows/ci.yml"     # not ROOT
```

The default is the existing global, so behaviour is unchanged: `__main__` binds the real repo, a
case binds a temporary tree. Two consequences are part of the decision, not side effects:

1. **A case that drives `main` covers the residue.** Measured on `check-ratchet-contract.py`: the
   driven-`main` case catches round 9's Blocking **and** a `if len(other_v) > BASELINE:` severance
   that is not a call at all, which no per-call-site rule would ever demand an entry for.
2. **It does not reduce the number of obligations** — four rule results still need four assertions.
   It changes their **kind**: a `case(...)` written by reflex with feedback in seconds, instead of a
   mutation-manifest entry authored blind against a 27-minute loop (backlog #208).

## Rejected alternatives

**A per-call-site AST detector** (backlog #213's proposal) — *implemented and run before rejection,
not argued away.* It demands 11 entries across the three guards and **108 repo-wide** (+9% on the
sweep). ⛔ **Its subject is the region a correct repair empties:** `check-ratchet-contract.py` has 2
demanded entries inside `main` and 16 whole-file, and round 8's extraction is what moved three of
them out. **Its reach shrinks at exactly the rate the repair proceeds.** It also misses the newest
instance three ways (inside `observe()` not `main`; a comprehension not a call; flowing to
`subprocess.run(env=)` not a verdict), at least one demanded entry is unkillable
(`ratchets = discover_guards(...)` — `evaluate` re-derives it, rc 1 both ways), and its subject is
absent in 7 of 43 guards.

**A registry of rules iterated by one call site** — rejected on this repo's own prior measurement,
`check-ratchet-contract.py:159`: *"a registry is evadable by simply not registering… The filesystem
cannot be evaded by omission."* An unregistered rule is a one-line deletion no case sees; restoring
visibility needs a completeness check, which is the rejected detector relocated.

**A verdict function taking rule FUNCTIONS rather than their results** — `verdict(coverage_fn=lambda
*_: [])` is exactly as invisible as `problems = []`. Nine of eleven instances are a result computed
and not read; the one dropped-argument instance was droppable only because a parameter carried a
default, already banned at `check-rc-contract.py:385`. It also re-merges the fetch into the rule,
inverting the separation `check-ratchet-contract.py:317` was written to protect.

## Consequences

- **29 of 36 guards with a `main()` do not satisfy this today** (coordinator re-derivation; 7 drive
  `main` at all, 1 took its world as a parameter before today, 2 do now). This ships as a **pinned
  identity debt set** like `WIDENED_MANIFEST_DEBT`, paid down one guard at a time, never as a
  baseline-0 ratchet that would be red on day one and switched off (backlog #56's measured verdict).
- **The enforcing rule (D2) is NOT YET WRITTEN, and must admit three routes, not two.** A guard may
  reach a constructed world by taking a parameter, by the suite rebinding the globals `main` reads,
  **or by the suite passing an `argv` that names a constructed path**. ⛔ The third was missed in the
  review's draft, and omitting it false-positives on `check-fixture-variation.py`, which drives
  `main()` **14 times from `_self_test()`** and is the repo's best worked example of this ADR.
- **7 guards have no `main()` at all** and are outside the population — stated here rather than left
  to a `KeyError`.
- **This ADR exists because there was no venue.** All thirteen prior ADRs govern the product; the
  verification stack was governed by script docstrings and backlog rows, so a structural choice
  about it could be *discovered* but never *decided*, and never protected from re-litigation.
  CONTEXT.md's Verification Stack section — created by architecture review #7 for the adjacent
  failure — carries vocabulary only.

## Falsifier

**A later instance of this class whose severed statement lives in the `main` of a guard that already
has a case driving `main` over a constructed world.** That would show the end-to-end case does not
cover the residue and the per-call-site detector was needed after all.

⚠ Instances in guards **without** such a case confirm this ADR rather than refute it, and must not
be counted against it. The prediction offered for judgement: apply this to the three guards of the
`semantic-recall-replication` fold and the next instance appears in one of the other 29 — because
that is where the exposure is and nobody has looked there.

Full derivation, with the measurements: `docs/reviews/architecture-review-2026-10-01.md`.
