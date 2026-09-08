#!/usr/bin/env python3
"""The coverage verdict is a type you cannot read wrongly.

    python3 scripts/coverage_verdict.py --self-test  # 21 cases

WHY THIS EXISTS
---------------
Seven consecutive adversarial review rounds each found a defect inside the previous round's
fix, and not one of those fixes was wrong. Measured by AST over the delivered file:

    ev keys: 7    written by: 2 functions    touched by: 7 functions
    ev['trustworthy']  WRITTEN by check, mutate_delivered
                       READ    by evidence, main            <- 2 of the 7
    check() reads mutations, survivors AND files — and never reads trustworthy

`ev` was a plain dict. Any producer wrote any key; any consumer read any key. The rule that
matters — **never read a tally without consulting the verdict** — lived only as convention,
re-implemented or forgotten at each site. Every one of the seven defects was one of two
shapes: a producer that set `trustworthy` while holding part of its contract, or a consumer
that read a tally without consulting it. The rounds were not failing. They were ENUMERATING,
one consumer per round, through a set a real interface closes in one move.

⛔ THE GUARDED-ACCESSOR ALTERNATIVE WAS REJECTED AND MUST NOT BE RE-PROPOSED. Keeping one
object and making `.tally()` return None when untrustworthy fails exactly as
`verdicts_are_trustworthy` already failed in r3: that helper WAS the "one shared rule" fix,
and it still shipped holding two of its three clauses, because nothing stopped a caller from
being wrong. A guarded accessor is a convention with a nicer name.

THE THREE PROPERTIES, AND THE THIRD EARNS THE CHANGE
-----------------------------------------------------
1. `NotMeasured` has NO `survivors` field at all. `0 survivor(s)` is this project's success
   sentence; on a run that measured nothing it is the single most misleading number
   available. It is not gated — it does not exist.
2. Its list is `entries`, NOT `mutations`. A consumer that copies a line from the measured
   path onto an unmeasured verdict gets an AttributeError, not a plausible wrong number.
   The rename is the mechanism, not cosmetics.
3. ⭐ `Measured`'s constructor enforces all three clauses, so there is no path to a tally
   that skips the checks — which is precisely what six rounds kept finding a path around.

⚠ `controls_green` IS AN InitVar, NOT A FIELD, AND THAT IS A DELIBERATE CHOICE THE SPEC LEFT
IMPLICIT. Spec §3 lists four fields (files, declared, mutations, survivors) but names three
clauses, one of which is "controls green" — a fact about the RUN, not a property of the
verdict. Storing it would invite a consumer to read `.controls_green` and re-derive the
judgement the constructor already made, which is the exact shape being deleted. As an
InitVar it is checked and discarded: you cannot ask a `Measured` whether its controls were
green, because a `Measured` only exists if they were.

⚠ `reason` IS THE RENDERED CLAUSE, NOT THE WHOLE SENTENCE — A CORRECTION TO SPEC §3.
The spec says `reason` is "the CANNOT RUN / shortfall sentence, ALREADY RENDERED". It cannot
be, and the reason is measurable rather than aesthetic: the shipped sentence is
`NOT MEASURED — {subject}the mutation harness produced no coverage verdict{short}.` and
`check-plan-code.py` calls it with THREE different subjects, one of which varies with the
command-line flags (`f"{mode}: "`). A subject is INVOCATION context — the verdict cannot
know it, and a fully pre-rendered string cannot have one inserted into its middle without
string surgery. So the split is: this module owns everything derived from the verdict's own
arithmetic (`not_measured_reason`), and the caller owns the `NOT MEASURED — ` head and the
subject. `reason` is still "already rendered" in the sense that earns the field — the
arithmetic is baked in at CONSTRUCTION, so no consumer can recompute it and get it wrong.

WHAT THIS DOES NOT FIX, stated rather than discovered later
------------------------------------------------------------
An interface stops a consumer reading a tally it should not. It does NOT stop a producer
computing `controls_green` wrongly — that was r4 M1, and the answer there was
`control_is_green(rc, out)`, already shipped. If a round finds an eighth defect, the honest
prediction is that it is in the PRODUCTION of a clause, not the CONSUMPTION of a verdict.
This narrows the class; it does not close it.
"""
from __future__ import annotations

import sys
from dataclasses import InitVar, dataclass, field


class VerdictContractError(ValueError):
    """A `Measured` was constructed over a run that did not earn one.

    A distinct type, not a bare ValueError, so a caller can catch exactly this without
    swallowing an unrelated ValueError from the same block — and so a test asserting the
    contract fires cannot pass on a typo that raises something else. This project has
    already recorded a negative test that caught "any error" and passed on a typo.
    """


def not_measured_reason(entries: int, declared: "int | None") -> str:
    """The clause that says a run produced no coverage verdict, with its arithmetic.

    ⚠ THE PARENTHETICAL APPEARS ONLY WHEN A SHORTFALL IS THE REASON. On the after-control
    path the counts are complete and the reason is the CANNOT RUN line printed above, so
    "(165 of 165 … produced a verdict)" beside "produced no coverage verdict" would
    contradict itself — measured 2026-09-03 on F2-S4's first run.

    It lives HERE, not at the renderer, because it is arithmetic over the verdict's own
    two numbers. Rendering it at each consumer is what let the header print
    `len(mutations)` while calling the number DECLARED, so two dropped entries were
    invisible (r3 B4).
    """
    short = (f" ({entries} of {declared} declared mutation(s) produced a verdict)"
             if declared is not None and entries != declared else "")
    return (f"the mutation harness produced no coverage verdict{short}. "
            f"Treat this as NOT CHECKED.")


@dataclass(frozen=True)
class Measured:
    """Every declared mutation produced a real verdict, over green controls.

    Constructing this IS the claim that the tally below means something. If any clause
    fails, the object does not come into existence — there is nothing to misread.
    """

    files: dict
    declared: int
    mutations: list
    survivors: list
    controls_green: InitVar[bool] = True

    def __post_init__(self, controls_green: bool) -> None:
        # Clause 1 — the suites were green WITHOUT the mutation. Every `caught` claims the
        # suite went red BECAUSE of its mutation, and that claim is empty over a suite that
        # was never green. r3 B1 found `check()` asserting trustworthy over a red control.
        if controls_green is not True:
            raise VerdictContractError(
                "controls were not green — a mutation cannot be 'caught' by a suite that "
                "was already failing, so this run earned no coverage verdict")
        # Clause 2 — every DECLARED mutation produced a verdict. `run_mutations` skips
        # without appending at four places; this catches all four and any fifth added later.
        if len(self.mutations) != self.declared:
            raise VerdictContractError(
                f"{len(self.mutations)} verdict(s) for {self.declared} declared mutation(s) "
                "— a mutation that never ran cannot be counted as caught")
        # Clause 3 — every entry is a real verdict rather than a cannot-run. `is True`
        # rejects a value that is truthy but not True (1, 'yes', a non-empty dict), which is
        # what an append site would produce through a JSON round-trip.
        bad = [i for i, m in enumerate(self.mutations) if m.get("measured") is not True]
        if bad:
            raise VerdictContractError(
                f"mutation(s) at index {bad} are not measured — a cannot-run is not a verdict")


@dataclass(frozen=True)
class NotMeasured:
    """The run produced no coverage verdict. There is no tally to read.

    ⚠ NOTE WHAT IS ABSENT: there is no `survivors` field, and the list is `entries`. Both
    absences are load-bearing and neither is cosmetic — see the module docstring.

    ⚠ `declared is None` IS A THIRD STATE INSIDE THIS ONE VARIANT, and it is not decoration.
    `None` means no mutation was ever ATTEMPTED (a plan that assembles nothing), which
    `check-plan-code.py` has shipped as an HONEST ZERO since backlog #93 — as opposed to a
    verdict WITHHELD, which is what a non-None `declared` on this variant means. Two
    consumers branch on it. Read `main()`'s two printer gates before changing that.
    """

    reason: str                      # the rendered clause, WITHOUT the `NOT MEASURED — ` head
    declared: "int | None" = None    # None when mutations were never attempted
    entries: list = field(default_factory=list)   # NOT `mutations`
    files: dict = field(default_factory=dict)     # control runs only — never a coverage claim

    @classmethod
    def from_counts(cls, entries: list, declared: "int | None",
                    files: "dict | None" = None) -> "NotMeasured":
        """The ONLY constructor production code uses, so `reason` cannot disagree with
        `entries` and `declared`. A hand-set `reason` that says "1 of 3" over a list of two
        is exactly the drift a derived field invites; the factory removes the opportunity
        rather than adding a check nobody runs."""
        return cls(reason=not_measured_reason(len(entries), declared),
                   declared=declared, entries=list(entries), files=dict(files or {}))


CoverageVerdict = "Measured | NotMeasured"


def _self_test() -> int:
    """21 cases. Run after touching this file."""
    cases, failed = 0, 0

    def chk(label, actual, expected):
        nonlocal cases, failed
        cases += 1
        if actual != expected:
            failed += 1
            print(f"  [FAIL] {label}: got {actual!r} want {expected!r}")

    def raises(label, fn):
        """⚠ THE FAILURE LINE MUST MATCH `check-plan-code.run_mutations`' PARSER, and the
        first draft of this file did not. That parser reads a red case name as
        `l.strip()[7:].rsplit(": got ", 1)[0]`, so a line saying `did not raise` yields the
        case name WITH the diagnosis glued on, and no `expect` can ever equal it. MEASURED
        2026-09-08: all four mutations pointed at this module went red and were reported
        `caught by something else` — coverage that exists and cannot be seen, which is the
        recorded shape where a report FORMAT is a contract. Hence `: got … want …`."""
        nonlocal cases, failed
        cases += 1
        try:
            fn()
        except VerdictContractError:
            return
        except Exception as exc:                       # noqa: BLE001
            failed += 1
            print(f"  [FAIL] {label}: got {type(exc).__name__!r} want 'VerdictContractError'")
            return
        failed += 1
        print(f"  [FAIL] {label}: got 'no exception' want 'VerdictContractError'")

    ok = [{"measured": True}]

    # --- the happy path exists at all ---
    m = Measured(files={}, declared=1, mutations=ok, survivors=[], controls_green=True)
    chk("a complete run constructs", (m.declared, len(m.mutations), m.survivors), (1, 1, []))

    # --- F1: len(mutations) != declared ---
    raises("F1 declared=2 with 1 verdict",
           lambda: Measured(files={}, declared=2, mutations=ok, survivors=[], controls_green=True))
    raises("F1 declared=0 with 1 verdict",
           lambda: Measured(files={}, declared=0, mutations=ok, survivors=[], controls_green=True))

    # --- F2: an entry that is not measured ---
    raises("F2 measured missing",
           lambda: Measured(files={}, declared=1, mutations=[{}], survivors=[], controls_green=True))
    raises("F2 measured is falsy",
           lambda: Measured(files={}, declared=1, mutations=[{"measured": False}],
                            survivors=[], controls_green=True))
    # ⚠ the case that `is True` buys and plain truthiness does NOT
    raises("F2 measured truthy but not True (1)",
           lambda: Measured(files={}, declared=1, mutations=[{"measured": 1}],
                            survivors=[], controls_green=True))
    raises("F2 measured truthy but not True ('yes')",
           lambda: Measured(files={}, declared=1, mutations=[{"measured": "yes"}],
                            survivors=[], controls_green=True))

    # --- F3: controls not green ---
    raises("F3 controls_green=False",
           lambda: Measured(files={}, declared=1, mutations=ok, survivors=[], controls_green=False))
    # ⚠ same `is True` discipline on the clause itself, not only on the entries
    raises("F3 controls_green truthy but not True",
           lambda: Measured(files={}, declared=1, mutations=ok, survivors=[], controls_green=1))

    # --- F4/F5: the absences are real, not gated ---
    nm = NotMeasured(reason="nothing was staged")
    chk("F4 NotMeasured has no survivors", hasattr(nm, "survivors"), False)
    chk("F5 NotMeasured has no mutations", hasattr(nm, "mutations"), False)
    chk("F5 NotMeasured carries entries instead", nm.entries, [])

    # --- the union's own shape ---
    chk("NotMeasured declared defaults to None", nm.declared, None)

    # ── the reason clause, and its arithmetic ─────────────────────────────────────
    # These four are the falsifiers for the sentence `check-plan-code.py` prints on every
    # refusal path. The arithmetic moved HERE with the field it describes, so the mutation
    # that used to pin it in the renderer pins it here (see scripts/mutations/).
    chk("a COMPLETE count states no arithmetic — it would contradict the refusal",
        not_measured_reason(3, 3),
        "the mutation harness produced no coverage verdict. Treat this as NOT CHECKED.")
    chk("a PARTIAL shortfall names how many of how many",
        "(1 of 3 declared mutation(s) produced a verdict)" in not_measured_reason(1, 3), True)
    # ⚠ the TOTAL shortfall is a DIFFERENT fixture from the partial one, and this project has
    # measured a weakened predicate surviving because only the partial case existed.
    chk("a TOTAL shortfall names it too — 0 is not 'nothing to say'",
        "(0 of 2 declared mutation(s) produced a verdict)" in not_measured_reason(0, 2), True)
    chk("declared=None states no arithmetic — nothing was ever attempted",
        "produced a verdict)" in not_measured_reason(0, None), False)

    # ── the factory cannot let `reason` disagree with the counts ──────────────────
    f = NotMeasured.from_counts([{"name": "a"}], 3, files={"x.py": {}})
    chk("from_counts derives the shortfall from the entries it was given",
        "(1 of 3 declared mutation(s) produced a verdict)" in f.reason, True)
    chk("...and keeps the entries and declared it derived from", (len(f.entries), f.declared), (1, 3))
    chk("...and carries the control-run files without calling them coverage", sorted(f.files), ["x.py"])
    # The presence twin of the absence above: a factory-built verdict still has no survivors.
    chk("...and STILL has no survivors field", hasattr(f, "survivors"), False)

    print(f"\n{cases - failed}/{cases} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(_self_test())
    print("coverage_verdict: a library. Run --self-test.", file=sys.stderr)
    sys.exit(2)
