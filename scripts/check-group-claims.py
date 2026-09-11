#!/usr/bin/env python3
"""Every grouping on the backlog page is a CLAIM, and a claim has to be able to be wrong.

    python3 scripts/check-group-claims.py            # check the shipped GROUPS
    python3 scripts/check-group-claims.py --self-test  # 24 cases

WHY THIS EXISTS, and it is a policy guard rather than a defect guard. Adopted from
`docs/backlog.md` row #90 on 2026-09-11. A backlog page carries three things that all look like
ways of sorting items and are not:

  * a TAG   — read out of the Bundle column. Answers *what is this about?* It is a LABEL: it
              cannot be wrong, only useless.
  * a GROUP — hand-written. Answers *what do these items have in common worth asserting?* It is a
              CLAIM: it CAN be wrong, and somebody has to be able to say how.
  * a SLICE — not a container at all. Work that must land first, joined to items by dependency
              edges. Answers *in what order, and does this survive?*

Only the middle one needs policing, because it is the only one with a truth value.

⛔ WHAT THIS CANNOT DO, SAID PLAINLY SO PASSING IT IS NOT MISTAKEN FOR SAFETY. It cannot read a
framing sentence and tell you whether it is TRUE, and it cannot tell you whether a falsifier is a
good one. A group whose falsifier reads `"the sky is green"` passes every rule here. What it can
do is refuse the shapes that let a bin masquerade as a claim — an absent falsifier, a group too
small to be a group, and a member that does not exist. Judging the claim stays human, which is
where every other gate in this repo also stops.

⚠ ONE POLICY CLAUSE IS DELIBERATELY NOT IMPLEMENTED, and saying so is the point. Row #90 proposes
that a falsifier naming a COLUMN (Size, Bundle) should be EVALUATED — "every member's Size is XS"
is checkable. Measured 2026-09-11: **zero** of the six shipped falsifiers name a column; they are
all prose about root causes and subject matter. Building the evaluator today would add a clause
that cannot fire over the real population, which is the unfalsifiable-guard shape this project has
paid for repeatedly. ⭐ ITS TRIGGER IS EXPLICIT: the first falsifier written in the form
`<column> <op> <value>`. Add the evaluator then, with that group as its first case.

WHY THE INDEX IS NOT CAUGHT BY THIS, and it is the mechanical half of "the bin is not coming
back". `build()` appends a section called "The rest, one line each" for items no group names. That
section carries an EMPTY falsifier on purpose and is NOT in `GROUPS`, so it never reaches this
guard. An index that wanted to become a claim would have to be added to `GROUPS`, where rule 1
would demand a falsifier of it.
"""
from __future__ import annotations

import argparse
import importlib.util
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parent.parent
GEN = REPO / "scripts" / "gen-backlog-page.py"
BACKLOG = REPO / "docs" / "backlog.md"

MIN_OPEN = 2


# ── the rules. PURE — they take data, never read the disk. ────────────────────────────────────
def claim_errors(groups: list, open_nums: set[int], all_nums: set[int]) -> list[str]:
    """Every rule, over data supplied by the caller.

    ⚠ `groups` is the four-field shape `(title, framing, falsifier, members)`. A three-field
    entry is the OLD shape and is reported rather than crashing — a guard that dies on the input
    it exists to judge attributes nothing.
    """
    out: list[str] = []
    for g in groups:
        if len(g) != 4:
            out.append(f"{_name(g)}: has {len(g)} field(s), not 4 — the shape is "
                       f"(title, framing, falsifier, members)")
            continue
        title, _framing, falsifier, members = g
        # RULE 1 — a claim states how it could be wrong.
        if not str(falsifier).strip():
            out.append(f"{title!r}: no falsifier. A group is a claim; state the observation that "
                       f"would make it FAIL, or make this a tag instead")
        # RULE 2 — a group of one is an item with extra words.
        live = [n for n in members if n in open_nums]
        if len(live) < MIN_OPEN:
            out.append(f"{title!r}: {len(live)} open member(s), needs {MIN_OPEN}. Retire it and "
                       f"let the item render in the index")
        # RULE 3 — a member that does not exist cannot be judged against the claim.
        for n in members:
            if n not in all_nums:
                out.append(f"{title!r}: names #{n}, which is not a row in the backlog")
    return out


def _name(g) -> str:
    try:
        return repr(g[0])
    except Exception:
        return "<unnamed group>"


def duplicate_errors(groups: list) -> list[str]:
    """A member claimed by two groups is claimed by two CLAIMS, which cannot both be the reason.

    ⚠ The page's `sanitise_groups` silently keeps the first and drops the second, which is right
    for RENDERING — a page that refuses tells the reader nothing. It is wrong for a gate: the
    render-time repair means nobody ever sees the contradiction. So it is reported HERE, where
    failing costs a commit rather than a page.
    """
    seen, dupes = {}, []
    for g in groups:
        if len(g) != 4:
            continue
        title, _f, _x, members = g
        for n in members:
            if n in seen:
                dupes.append(f"#{n} is claimed by both {seen[n]!r} and {title!r}")
            else:
                seen[n] = title
    return dupes


# ── the fetch. Separated from the rules so the rules are testable without the repo. ───────────
def load_groups() -> list:
    spec = importlib.util.spec_from_file_location("_gbp", GEN)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {GEN}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return list(mod.GROUPS)


ROW = re.compile(r"^\|\s*(\d+)\s*\|")


def load_rows(text: str) -> tuple[set[int], set[int]]:
    """(all numbers, open numbers). Closed iff the Status cell carries a check mark.

    ⚠ The two tables in `docs/backlog.md` have DIFFERENT column counts, so the Status cell is
    taken from the END of the row rather than by index. A positional read on this file has
    previously closed two open rows by hitting the wrong cell.
    """
    all_nums, open_nums = set(), set()
    for line in text.split("\n"):
        m = ROW.match(line)
        if not m:
            continue
        n = int(m.group(1))
        all_nums.add(n)
        cells = line.split("|")
        status = cells[-2] if len(cells) >= 3 else ""
        if "✅" not in status:
            open_nums.add(n)
    return all_nums, open_nums


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return self_test()

    if not BACKLOG.is_file():
        print(f"CANNOT RUN: {BACKLOG} not found — treat this as NOT RUN, not as a pass")
        return 2
    try:
        groups = load_groups()
    except Exception as e:                                    # noqa: BLE001
        print(f"CANNOT RUN: could not import GROUPS from {GEN}: {e}")
        return 2
    if not groups:
        print("CANNOT RUN: GROUPS is empty — a zero over an unread population is not a finding")
        return 2

    all_nums, open_nums = load_rows(BACKLOG.read_text(encoding="utf-8"))
    if not all_nums:
        print(f"CANNOT RUN: parsed 0 rows from {BACKLOG} — the format moved")
        return 2

    problems = claim_errors(groups, open_nums, all_nums) + duplicate_errors(groups)
    if problems:
        print(f"FAILED — {len(problems)} grouping problem(s) (policy: docs/backlog.md row #90):")
        for p in problems:
            print(f"  ✗ {p}")
        print("  A group is a CLAIM. If it cannot be wrong it is a tag; if it has one open member "
              "it is an item.")
        return 1
    print(f"group claims OK — {len(groups)} group(s), every one with a falsifier and "
          f"{MIN_OPEN}+ open members")
    return 0


def self_test() -> int:
    ok = fail = 0

    # ⚠ `want: object`, not the inferred `bool`. With a bare `want=True` default a checker infers
    # `bool` and then rejects every case expecting a list or a count — which is most of them.
    def case(name: str, got, want: object = True) -> None:
        nonlocal ok, fail
        try:
            v = got() if callable(got) else got
        except Exception as e:                                # noqa: BLE001
            v = f"raised {e!r}"
        if v == want:
            ok += 1
            print(f"  ok     {name}")
        else:
            fail += 1
            print(f"  [FAIL] {name}: got {v!r}, want {want!r}")

    G = lambda t, f, x, m: (t, f, x, m)                       # noqa: E731
    ALL, OPEN = {1, 2, 3, 4}, {1, 2, 3}

    # ── rule 1: a falsifier must be present ────────────────────────────────────────────────
    case("a group with a falsifier and two open members passes",
         claim_errors([G("t", "f", "a member that is blue", [1, 2])], OPEN, ALL), [])
    case("an EMPTY falsifier is refused",
         len(claim_errors([G("t", "f", "", [1, 2])], OPEN, ALL)), 1)
    case("...and a whitespace-only falsifier is refused too — not just the empty string",
         len(claim_errors([G("t", "f", "   ", [1, 2])], OPEN, ALL)), 1)
    case("...and the message says what to do instead of just refusing",
         lambda: "make this a tag instead"
         in claim_errors([G("t", "f", "", [1, 2])], OPEN, ALL)[0])
    case("...and it names the group, so it can be found",
         lambda: "'t'" in claim_errors([G("t", "f", "", [1, 2])], OPEN, ALL)[0])

    # ── rule 2: fewer than two OPEN members ────────────────────────────────────────────────
    case("a group with one open member is refused",
         len(claim_errors([G("t", "f", "x", [1])], OPEN, ALL)), 1)
    case("...and the count in the message is the OPEN count, not the member count",
         lambda: "1 open member(s)"
         in claim_errors([G("t", "f", "x", [1, 4])], OPEN, ALL)[0])
    case("...so a group of two whose members are both CLOSED is refused",
         len(claim_errors([G("t", "f", "x", [4])], OPEN, ALL)), 1)
    case("a group with exactly two open members is accepted — the boundary is >=, not >",
         claim_errors([G("t", "f", "x", [1, 2])], OPEN, ALL), [])
    case("an EMPTY group is refused rather than ignored",
         len(claim_errors([G("t", "f", "x", [])], OPEN, ALL)), 1)

    # ── rule 3: a member must exist ────────────────────────────────────────────────────────
    case("a member that is not a row at all is refused",
         len(claim_errors([G("t", "f", "x", [1, 2, 99])], OPEN, ALL)), 1)
    case("...and the message names the missing number",
         lambda: "#99" in claim_errors([G("t", "f", "x", [1, 2, 99])], OPEN, ALL)[0])
    case("a CLOSED member is NOT a missing member — it exists, it is just done",
         claim_errors([G("t", "f", "x", [1, 2, 4])], OPEN, ALL), [])

    # ── the POPULATION is read, not assumed ────────────────────────────────────────────────
    # ⚠ A SECOND POPULATION, and `check-fixture-variation` is what asked for it BY NAME: every
    # case above passed the same `OPEN` and `ALL`, so no case could tell those two parameters
    # from constants, and any clause reading them was unguarded. Exempting was the other option
    # and would have been wrong — one value is not right here, it was just convenient.
    ALT_ALL, ALT_OPEN = {7, 8, 9}, {7, 8}
    case("the open set is READ — the same shape of group passes under a different population",
         claim_errors([G("t", "f", "x", [7, 8])], ALT_OPEN, ALT_ALL), [])
    case("...and with only one of its members open, that same group is refused",
         len(claim_errors([G("t", "f", "x", [7, 9])], ALT_OPEN, ALT_ALL)), 1)
    case("the all set is READ too — #1 exists in the other population and is missing from this one",
         lambda: "#1" in claim_errors([G("t", "f", "x", [7, 8, 1])], ALT_OPEN, ALT_ALL)[0])

    # ── the old shape is reported, not crashed on ──────────────────────────────────────────
    # ⚠ LAMBDAS, and the mutation run is what proved they had to be. Passed eagerly, the call is
    # evaluated BEFORE `case` runs, so when the shape guard is removed the `ValueError` escapes and
    # the whole suite DIES — red, but attributable to nothing. A case that dies from its defect is
    # weaker than one that reports it; inside a lambda the exception lands in `case`'s handler and
    # the failure carries this line's name.
    case("a three-field group is reported as a shape error, not an exception",
         lambda: len(claim_errors([("t", "f", [1, 2])], OPEN, ALL)), 1)
    case("...and the message says what the four fields are",
         lambda: "(title, framing, falsifier, members)"
         in claim_errors([("t", "f", [1, 2])], OPEN, ALL)[0])

    # ── duplicates across groups ───────────────────────────────────────────────────────────
    case("one item claimed by two groups is reported",
         len(duplicate_errors([G("a", "f", "x", [1]), G("b", "g", "y", [1])])), 1)
    case("...and the message names BOTH groups, since either could be the wrong one",
         lambda: all(s in duplicate_errors([G("a", "f", "x", [1]), G("b", "g", "y", [1])])[0]
                     for s in ("'a'", "'b'")))
    case("distinct membership is silent",
         duplicate_errors([G("a", "f", "x", [1]), G("b", "g", "y", [2])]), [])

    # ── the row reader: two tables, different widths ───────────────────────────────────────
    SIX = "| 5 | item | touches | S | (tag) | **OPEN** |"
    SIX_DONE = "| 6 | item | touches | S | (tag) | ✅ **DONE** |"
    THREE = "| 7 | item | ✅ done |"
    case("a six-column open row is read as open",
         load_rows(SIX), ({5}, {5}))
    case("a six-column closed row is read as closed",
         load_rows(SIX_DONE), ({6}, set()))
    case("a THREE-column row is read from the same end, so the narrow table works too",
         load_rows(THREE), ({7}, set()))

    print(f"\n{ok}/{ok + fail} passed")
    if ok + fail != 24:
        print(f"  [DRIFT] the docstring declares 24 cases; the suite ran {ok + fail}")
        return 1
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
