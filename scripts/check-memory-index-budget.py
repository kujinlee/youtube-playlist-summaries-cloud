#!/usr/bin/env python3
"""`docs/memory/MEMORY.md` is injected whole on every turn, and when it overflows the harness
TRUNCATES IT IN SILENCE.

WHY THIS EXISTS — measured 2026-10-19, and no gate in this repo could see it.
-----------------------------------------------------------------------------
The index reached **27,805 bytes against the harness's 24,985-byte limit**, so roughly 30 of its
118 rows were dropped before any of it was read. Every signal available in the repo was green:
`check-memory-link.py` verified the symlink, `recall-llm.py`'s `corpus_verdict` counted a healthy
corpus, `check-docs.py` enforced its line budget. None of them measures the one quantity that
decides whether a row ARRIVES — the byte size of the always-loaded file.

⛔ THE FAILURE MODE IS THE ONE THIS REPO KEEPS PAYING FOR: a producer and its consumer disagreeing
with nothing in between to notice. The index's own header says *"all rows arrive every session,
unfiltered"*. That sentence was false by about a tenth, and it had no way to find out. Worse, WHICH
rows survived was not a choice anyone made — truncation takes a prefix, so the rule that matters
most is simply the one furthest down.

WHAT IT CHECKS
--------------
  R1  the always-loaded index fits the harness's injection budget, with a WARN band before the
      cliff so the first signal is not already a loss.

The remedy is always the same and is named in the message: move history-shaped rows into a
TRIGGERED corpus entry (`docs/memory/slice-history.md`), which is reached on demand instead of
loaded on every turn. Rows moved there still arrive — they just stop being a tax.

⛔ WHAT IT DELIBERATELY DOES NOT CHECK, and the measurement that settles it
--------------------------------------------------------------------------
The harness's warning blames row LENGTH (*"keep index entries to one line under ~200 chars"*). That
is not a rule here: measured 2026-10-19, **32 of 118 rows (27%) already exceed 200 bytes and the
longest is 620**. A gate red from birth on 27% of its subject gets switched off — #56's measured
verdict — and the rows are long because they carry evidence. Total bytes is the quantity that
actually decides truncation, and it is the one enforced.

⚠ THE FAILURE DIRECTION, STATED RATHER THAN HIDDEN. `LIMIT_BYTES` is a DECLARED constant read from
the harness's own warning text, not derived — nothing in the repo can interrogate the harness. So
if the harness ever LOWERS its limit, this guard goes quiet while truncation silently resumes: it
fails toward good news, which is the direction that gets believed. Two mitigations, both partial:
the WARN band fires at 90% so there is a signal before the cliff, and the constant carries the
verbatim warning it came from so a reader can compare it against what the harness says today.
⛔ If you see the harness warn about truncation while this guard is green, the constant is stale —
that observation refutes it, and it is the ONLY thing that can.

    python3 scripts/check-memory-index-budget.py
    python3 scripts/check-memory-index-budget.py --self-test  # 26 cases
"""
from __future__ import annotations

import pathlib
import sys
import tempfile

OK, OVER_BUDGET, CANNOT_RUN = 0, 1, 2

ROOT = pathlib.Path(__file__).resolve().parent.parent
INDEX = ROOT / "docs" / "memory" / "MEMORY.md"
OVERFLOW_TARGET = "docs/memory/slice-history.md"

# OBSERVED, not derived. The harness emitted, verbatim, into a session on 2026-10-19:
#
#   "WARNING: MEMORY.md is 26.3KB (limit: 24.4KB) — index entries are too long. Only part of it
#    was loaded. Keep index entries to one line under ~200 chars; move detail into topic files."
#
# 24.4KB is reported to one decimal place, so this is the limit to within ~51 bytes. The WARN band
# below is what covers that imprecision: a file inside 90% of the limit cannot be near the cliff
# whichever way the rounding went.
LIMIT_BYTES = int(24.4 * 1024)  # 24,985
WARN_FRACTION = 0.90


def warn_threshold(limit: int) -> int:
    """PURE. -> the byte count at which the index is close enough to the cliff to say so.

    DERIVED from the limit on purpose. A second literal here would be a constant that agrees with
    `LIMIT_BYTES` only until someone edits one of them — this repo's most-measured defect class.
    """
    return int(limit * WARN_FRACTION)


def budget_verdict(n_bytes: int | None, limit: int, label: str = "docs/memory/MEMORY.md",
                   ) -> tuple[int, str]:
    """PURE. -> (rc, message). Four outcomes, because they need four different responses.

    ⛔ `label` NAMES THE FILE THAT WAS ACTUALLY MEASURED, and it is a parameter because the first
    version hardcoded `INDEX`. Driving `main()` over a temp fixture then printed "docs/memory/
    MEMORY.md does not exist" about a file that was never opened — a CANNOT RUN that sends the
    reader to the wrong path is worse than one that says nothing.

    `n_bytes is None` means the file could not be read and `0` means it is empty. Both are
    CANNOT RUN rather than a comfortable "well under budget": a zero-byte index would sail
    through a naive size check while meaning the corpus index had been destroyed. "Cannot
    measure" and "measured, and it is fine" must never share an exit code.
    """
    if n_bytes is None:
        return CANNOT_RUN, (
            f"CANNOT RUN — {label} does not exist, so the always-loaded budget "
            "was NOT measured. Treat this as NOT RUN, never as a pass.")
    if n_bytes == 0:
        return CANNOT_RUN, (
            f"CANNOT RUN — {label} is EMPTY. That is not a small index, it is a "
            "missing one; the budget was NOT measured. Treat this as NOT RUN, never as a pass.")

    warn_at = warn_threshold(limit)
    if n_bytes > limit:
        return OVER_BUDGET, (
            f"OVER BUDGET — the always-loaded index is {n_bytes:,} bytes against the harness's "
            f"{limit:,}-byte limit, so it is being TRUNCATED IN SILENCE and roughly the last "
            f"{n_bytes - limit:,} bytes of rows never arrive. Nothing chose which rows those are. "
            f"REMEDY: move history-shaped rows into {OVERFLOW_TARGET}, which is a TRIGGERED corpus "
            "entry — they still arrive, on demand, instead of being loaded every turn.")
    if n_bytes >= warn_at:
        return OK, (
            f"WARNING: the always-loaded index is {n_bytes:,} bytes, within "
            f"{limit - n_bytes:,} bytes of the harness's {limit:,}-byte limit "
            f"({100 * n_bytes // limit}% of budget). Nothing is being dropped YET. Move "
            f"history-shaped rows into {OVERFLOW_TARGET} before it is. (Advisory.)")
    return OK, (
        f"ok — the always-loaded index is {n_bytes:,} bytes, {limit - n_bytes:,} under the "
        f"harness's {limit:,}-byte limit. Every row arrives.")


def index_size(path: pathlib.Path) -> int | None:
    """-> the file's size in BYTES, or None when it cannot be read.

    Bytes, not characters: the index is dense with multi-byte glyphs (⭐ ⛔ ⟳) and the two counts
    differ by nearly a kilobyte at this size — measured 27,805 bytes against 26,930 characters.
    A character count would have reported this index as fitting when it did not.
    """
    if not path.is_file():
        return None
    return len(path.read_bytes())


def main(argv: list[str], index: pathlib.Path = INDEX, limit: int = LIMIT_BYTES) -> int:
    """ADR-0014 D1: the world arrives as defaulted parameters BEYOND `argv`, so cases can drive
    this over a constructed index instead of only over the repo's real one.

    ⚠ `argv` carries real behaviour on purpose — an unknown flag exits CANNOT RUN rather than
    being ignored. A parameter a case can only pass `[]` to is indistinguishable from a constant,
    which is `check-fixture-variation`'s finding on this repo's other guards.
    """
    if "--self-test" in argv:
        return _self_test()
    unknown = [a for a in argv if a.startswith("-")]
    if unknown:
        print(f"CANNOT RUN — unrecognised flag(s) {unknown}. This guard takes no options but "
              "`--self-test`, so nothing was measured. Treat this as NOT RUN, never as a pass.")
        return CANNOT_RUN
    try:
        shown = str(index.relative_to(ROOT))
    except ValueError:
        shown = str(index)  # a fixture outside the repo, as the suite's driving cases pass
    rc, msg = budget_verdict(index_size(index), limit, shown)
    print(msg)
    return rc


def _self_test() -> int:
    ok = fail = 0

    def check(label: str, got, want) -> None:
        nonlocal ok, fail
        if got == want:
            ok += 1
        else:
            fail += 1
            print(f"  [FAIL] {label}\n         got  {got!r}\n         want {want!r}")

    L = 1000  # a round synthetic limit, so the boundaries below are readable
    warn_at = warn_threshold(L)  # 900

    # --- the three verdicts, and the message each must carry -------------------------------
    check("well under budget is OK", budget_verdict(10, L)[0], OK)
    check("an OK message states the headroom", "990 under" in budget_verdict(10, L)[1], True)
    check("over budget is rc 1", budget_verdict(L + 1, L)[0], OVER_BUDGET)
    check("the OVER message states the overage, not just the size",
          "1 bytes of rows never arrive" in budget_verdict(L + 1, L)[1], True)
    check("the OVER message names the remedy file",
          OVERFLOW_TARGET in budget_verdict(L + 1, L)[1], True)

    # --- boundaries, as ADJACENT pairs: a forced choice between absurd inputs cannot fail ---
    check("exactly AT the limit is not over", budget_verdict(L, L)[0], OK)
    check("one byte PAST the limit is over", budget_verdict(L + 1, L)[0], OVER_BUDGET)
    check("exactly at the warn threshold warns",
          budget_verdict(warn_at, L)[1].startswith("WARNING"), True)
    check("one byte BELOW the warn threshold does not warn",
          budget_verdict(warn_at - 1, L)[1].startswith("ok"), True)
    check("a warning is ADVISORY — it must not block", budget_verdict(warn_at, L)[0], OK)

    # --- CANNOT RUN is never a pass -------------------------------------------------------
    # ⛔ LITERALS, NOT THE SYMBOLS. These two compared against `CANNOT_RUN` and a mutation setting
    # `CANNOT_RUN = 0` SURVIVED: both sides of the assertion moved together, so the suite stayed
    # green while an unmeasurable index reported success. A case that reads the constant it is
    # testing is satisfied by whatever that constant happens to say.
    check("a missing index exits 2, pinned as a literal", budget_verdict(None, L)[0], 2)
    check("an EMPTY index exits 2 too — not a comfortable zero", budget_verdict(0, L)[0], 2)
    check("the three exit codes are the DECLARED values and are pairwise distinct",
          (OK, OVER_BUDGET, CANNOT_RUN), (0, 1, 2))
    check("both CANNOT RUN messages say to treat it as NOT RUN",
          all("NOT RUN, never as a pass" in budget_verdict(v, L)[1] for v in (None, 0)), True)

    # --- the warn band is DERIVED, exercised at two DISTINCT inputs -----------------------
    # One input could be satisfied by a constant that happens to equal it; two cannot.
    check("the warn threshold tracks the limit it is given",
          (warn_threshold(1000), warn_threshold(2000)), (900, 1800))

    # --- bytes, NOT characters. The docstring calls this load-bearing, so a case must pin it ---
    # Found by running the mutation that swaps read_bytes() for read_text(): no case reddened,
    # because the live index is under budget either way. An argument in a docstring that no case
    # witnesses is a bound I asserted rather than measured.
    with tempfile.TemporaryDirectory() as td:
        f = pathlib.Path(td) / "glyphs.md"
        f.write_text("⭐⛔⟳\n")  # 3 glyphs x 3 bytes + newline = 10 bytes, but 4 characters
        check("index_size counts BYTES, not characters (multi-byte glyphs)", index_size(f), 10)
        check("a character count would have disagreed, which is why this case exists",
              len(f.read_text()), 4)

    # --- main() driven over a CONSTRUCTED index (ADR-0014 D1) -----------------------------
    with tempfile.TemporaryDirectory() as td:
        under = pathlib.Path(td) / "under.md"
        under.write_text("x" * 100)
        over = pathlib.Path(td) / "over.md"
        over.write_text("x" * 2000)
        check("main() returns OK for an index inside the limit it is GIVEN",
              main([], index=under, limit=1000), 0)
        check("main() returns 1 for an index over the limit it is GIVEN",
              main([], index=over, limit=1000), 1)
        # The SAME file, two limits: proves main threads `limit` through rather than reading the
        # module constant. One input could be satisfied by a constant; two cannot.
        check("main() reads the limit it is given, not LIMIT_BYTES",
              (main([], index=over, limit=1000), main([], index=over, limit=5000)), (1, 0))
        check("main() CANNOT RUNs on a missing index rather than passing",
              main([], index=pathlib.Path(td) / "absent.md", limit=1000), 2)
    check("main() CANNOT RUNs on an unrecognised flag", main(["--bogus"]), 2)
    check("a CANNOT RUN names the file it ACTUALLY examined, not the module default",
          "nowhere/absent.md" in budget_verdict(None, 1000, "nowhere/absent.md")[1], True)
    check("the label defaults to the real index when none is given",
          "docs/memory/MEMORY.md" in budget_verdict(None, 1000)[1], True)

    # --- the declared constant, and the live file -----------------------------------------
    check("LIMIT_BYTES matches the 24.4KB the harness reported", LIMIT_BYTES, 24985)
    live = index_size(INDEX)
    check("the LIVE index is measurable and within budget "
          f"(it is {live if live is not None else 'UNREADABLE'} bytes)",
          budget_verdict(live, LIMIT_BYTES)[0], OK)

    print(f"self-test: {ok}/{ok + fail} cases passed")
    return OK if fail == 0 else OVER_BUDGET


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
