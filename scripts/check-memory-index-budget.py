#!/usr/bin/env python3
"""`docs/memory/MEMORY.md` is injected whole on every turn, and when it overflows the harness
TRUNCATES IT IN SILENCE.

WHY THIS EXISTS — measured 2026-10-19, and no gate in this repo could see it.
-----------------------------------------------------------------------------
The index reached **27,805 bytes against the harness's 24,985-byte limit**, so **2,820 bytes of
its tail did not arrive**. Every signal available in the repo was green:
`check-memory-link.py` verified the symlink, `recall-llm.py`'s `corpus_verdict` counted a healthy
corpus, `check-docs.py` enforced its line budget. None of them measures the one quantity that
decides whether a row ARRIVES — the byte size of the always-loaded file.

⟳ r1 CODEX #4 CORRECTED THE ROW FIGURE, AND THE ERROR WAS A POPULATION ERROR OF THE USUAL KIND.
This said "roughly 30 of its 118 rows". **146** lines began `- ` in the index that overflowed; my
118 was counted AFTER the rows had already been moved out, then written here as though it described
the file that failed. And the dropped amount is **2,820 bytes = 24 newlines of tail, beginning
MID-ROW** — so "30 rows" was never established by anything.

⛔ AND THE TRUNCATION ALGORITHM IS **NOT VERIFIED**, STATED PLAINLY BECAUSE IT BOUNDS THIS GUARD.
Nothing here can interrogate the injection harness. A quoted warning establishes that truncation
was REPORTED; it does not establish that the cut is a byte prefix rather than per-row, nor where it
lands. The byte total is the quantity the warning itself reports, which is why it is the quantity
enforced — but if the harness drops whole rows, or budgets after some transformation, this guard
measures a correlate rather than the cause.

⛔ THE FAILURE MODE IS THE ONE THIS REPO KEEPS PAYING FOR: a producer and its consumer disagreeing
with nothing in between to notice. The index's own header says *"all rows arrive every session,
unfiltered"*. That sentence was false, and it had no way to find out. Worse, WHICH part survived
was not a choice anyone made.

WHAT IT CHECKS
--------------
  R1  the always-loaded index fits the harness's injection budget, with a WARN band before the
      cliff so the first signal is not already a loss.

⛔ EVERY VERDICT NAMES THE FILE IT MEASURED (r1 CODEX #2a). Only the CANNOT RUN arms did, and
repointing `INDEX` at a different corpus file left all cases green — a guard that measures the
wrong file and reports "every row arrives" is worse than no guard, and the reader could not tell.

The remedy is always the same and is named in the message: move history-shaped rows into a
TRIGGERED corpus entry (`docs/memory/slice-history.md`), which is reached on demand instead of
loaded on every turn. Rows moved there still arrive — they just stop being a tax.

⛔ WHAT IT DELIBERATELY DOES NOT CHECK, and the measurement that settles it
--------------------------------------------------------------------------
The harness's warning blames row LENGTH (*"keep index entries to one line under ~200 chars"*). That
is not a rule here: measured 2026-10-19 over the index that ACTUALLY overflowed (`dff6a3f0^`), of
**146** `- ` lines, **35 exceed 200 characters and 38 exceed 200 bytes**, the longest being **602
characters / 620 bytes**. A gate red from birth on a quarter of its subject gets switched off —
#56's measured verdict — and the rows are long because they carry evidence. ⚠ Byte total is the
quantity the harness's own warning REPORTS, which is why it is enforced; see the NOT VERIFIED note
above for what that does and does not license.

⚠ THE FAILURE DIRECTION, STATED RATHER THAN HIDDEN. `LIMIT_BYTES` is a DECLARED constant read from
the harness's own warning text, not derived — nothing in the repo can interrogate the harness. So
if the harness ever LOWERS its limit, this guard goes quiet while truncation silently resumes: it
fails toward good news, which is the direction that gets believed. Two mitigations, both partial:
the WARN band fires at 90% so there is a signal before the cliff, and the constant carries the
verbatim warning it came from so a reader can compare it against what the harness says today.
⟳ r1 CODEX #5: the constant can be wrong in MORE ways than a lowered limit, and an earlier version
of this note called one observation "the ONLY" refutation, which was itself an overclaim. It can
also be wrong through the KB unit (1000 vs 1024), a harness or version change, or budgeting applied
after framing or transformation — and a RAISED limit makes this guard fail falsely rather than
quietly. ⛔ Refutations, none of them unique: the harness warning about truncation while this is
green; a controlled boundary experiment; or a published producer specification.

    python3 scripts/check-memory-index-budget.py
    python3 scripts/check-memory-index-budget.py --self-test  # 40 cases
"""
from __future__ import annotations

import contextlib
import io
import os
import pathlib
import sys
import tempfile

OK, OVER_BUDGET, CANNOT_RUN = 0, 1, 2

ROOT = pathlib.Path(__file__).resolve().parent.parent
INDEX = ROOT / "docs" / "memory" / "MEMORY.md"
OVERFLOW_TARGET = "docs/memory/slice-history.md"
# ⟳ r1 CODEX: DERIVED from INDEX, not a second literal. `budget_verdict`'s `label` default was the
# string "docs/memory/MEMORY.md" while INDEX was built from ROOT — two expressions of one path, and
# `check-vocabulary-collisions` structurally cannot see it (it reads database coordination
# vocabulary). Deriving it means repointing INDEX cannot leave the reported name behind.
# ⚠ Hardcoding this back to the literal is an EQUIVALENT MUTANT on its own — behaviour is identical
# until INDEX also moves — so it is deliberately not in the manifest; the INDEX subject cases are
# what catch the pair.
INDEX_LABEL = str(INDEX.relative_to(ROOT))

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


def budget_verdict(n_bytes: int | None, limit: int, label: str = INDEX_LABEL) -> tuple[int, str]:
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
            f"CANNOT RUN — {label} could not be READ — it is absent, or present and unreadable "
            "— so the always-loaded budget was NOT measured. Treat this as NOT RUN, never as a "
            "pass.")
    if n_bytes == 0:
        return CANNOT_RUN, (
            f"CANNOT RUN — {label} is EMPTY. That is not a small index, it is a "
            "missing one; the budget was NOT measured. Treat this as NOT RUN, never as a pass.")

    warn_at = warn_threshold(limit)
    if n_bytes > limit:
        return OVER_BUDGET, (
            f"OVER BUDGET — {label} is {n_bytes:,} bytes against the harness's "
            f"{limit:,}-byte limit, so it is being TRUNCATED IN SILENCE and roughly the last "
            f"{n_bytes - limit:,} bytes of rows never arrive. Nothing chose which rows those are. "
            f"REMEDY: move history-shaped rows into {OVERFLOW_TARGET}, which is a TRIGGERED corpus "
            "entry — they still arrive, on demand, instead of being loaded every turn.")
    if n_bytes >= warn_at:
        return OK, (
            f"WARNING: {label} is {n_bytes:,} bytes, within "
            f"{limit - n_bytes:,} bytes of the harness's {limit:,}-byte limit "
            f"({100 * n_bytes // limit}% of budget). Nothing is being dropped YET. Move "
            f"history-shaped rows into {OVERFLOW_TARGET} before it is. (Advisory.)")
    return OK, (
        f"ok — {label} is {n_bytes:,} bytes, {limit - n_bytes:,} under the harness's "
        f"{limit:,}-byte limit, so nothing is being dropped. ⚠ 'Every row arrives' would "
        f"overclaim: the limit is DECLARED to one decimal place (r1 CODEX #5), so treat this as "
        f"within the budget as measured, not as a proof of delivery.")


def index_size(path: pathlib.Path) -> int | None:
    """-> the file's size in BYTES, or None when it cannot be read.

    Bytes, not characters: the index is dense with multi-byte glyphs (⭐ ⛔ ⟳) and the two counts
    differ by nearly a kilobyte at this size — measured 27,805 bytes against 26,930 characters.
    ⟳ r1 CODEX #4 CORRECTED A FALSE CLAIM HERE. This said "a character count would have reported
    this index as fitting when it did not", and that is arithmetically wrong: 26,930 still exceeds
    24,985, so a character count would ALSO have caught this instance. The real argument is
    narrower and is the one that holds — the two counts diverge by ~3%, so a character count
    mis-measures the margin and would miss an index between 24,985 characters and 24,985 bytes.
    It is the wrong unit, not a unit that happened to fail here.

    ⟳ r1 CODEX #6: `read_bytes()` raised straight through, so an unreadable index produced a
    TRACEBACK instead of a named CANNOT RUN at rc 2 — the exit contract this guard advertises.
    Narrow `OSError`, and the returned None is a FAILING state, never a pass, so this is not the
    fail-open handler `check-ratchet-contract` R2 forbids.
    """
    if not path.is_file():
        return None
    try:
        return len(path.read_bytes())
    except OSError:
        return None


def unknown_args(argv: list[str]) -> list[str]:
    """PURE. -> the arguments this guard does not accept. `--self-test` is the only one it does.

    ⛔ A FUNCTION RATHER THAN AN INLINE FILTER, AND THE REASON IS A HAZARD IN THE SUITE, NOT STYLE.
    A case drove `main(["--self-test", "--bogus"])` to prove validation beats dispatch. Severing the
    filter then made that call re-enter `_self_test`, which called it again — UNBOUNDED RECURSION,
    surfacing as one red case repeated hundreds of times, and the mutation could not be attributed
    to the case that names it. Testing the PREDICATE needs no re-entry, so the property is witnessed
    without the suite being able to invoke itself.
    """
    return [a for a in argv if a != "--self-test"]


def main(argv: list[str], index: pathlib.Path = INDEX, limit: int = LIMIT_BYTES) -> int:
    """ADR-0014 D1: the world arrives as defaulted parameters BEYOND `argv`, so cases can drive
    this over a constructed index instead of only over the repo's real one.

    ⚠ `argv` carries real behaviour on purpose — an unknown flag exits CANNOT RUN rather than
    being ignored. A parameter a case can only pass `[]` to is indistinguishable from a constant,
    which is `check-fixture-variation`'s finding on this repo's other guards.
    """
    # ⟳ r1 CODEX #7: VALIDATION COMES BEFORE DISPATCH. It ran after, so
    # `main(["--self-test", "--bogus"])` returned 0 — the self-test arm swallowed the bogus flag
    # and the unknown-flag contract was unenforceable whenever `--self-test` was also present.
    # Positional garbage was accepted silently for the same reason: the filter only read flags.
    unknown = unknown_args(argv)
    if unknown:
        print(f"CANNOT RUN — unrecognised argument(s) {unknown}. This guard takes no operands and "
              "no options but `--self-test`, so nothing was measured. Treat this as NOT RUN, "
              "never as a pass.")
        return CANNOT_RUN
    if "--self-test" in argv:
        return _self_test()
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
    # ⟳ r1 CODEX #7: validation must beat dispatch. ⛔ Tested through the PURE predicate, never by
    # driving main() with `--self-test` — see `unknown_args` for the recursion that cost.
    check("an unknown flag is still unknown alongside --self-test",
          unknown_args(["--self-test", "--bogus"]), ["--bogus"])
    check("--self-test alone leaves nothing unknown", unknown_args(["--self-test"]), [])
    check("a positional operand counts as unknown, not as an accepted operand",
          unknown_args(["junk"]), ["junk"])
    check("main() refuses a positional operand rather than ignoring it", main(["junk"]), 2)

    # --- ⟳ r1 CODEX #2a: THE SUBJECT ITSELF. Repointing INDEX at another corpus file left all
    # 26 cases green, which defeats the guard's whole purpose — it would cheerfully measure the
    # wrong file and report "every row arrives" about a file nothing injects. Nothing asserted
    # WHAT is measured; every case supplied its own path or size.
    check("INDEX is the always-loaded index, not some other corpus file", INDEX.name, "MEMORY.md")
    check("INDEX is built from the repo root, so it survives a cwd change",
          INDEX, ROOT / "docs" / "memory" / "MEMORY.md")
    check("INDEX is the file the harness symlink actually serves", INDEX.is_file(), True)

    # --- ⟳ r1 CODEX #2b: THE EXACT BOUNDARY, end to end. The coarse 2000-vs-1000 pair below let a
    # `size - 1` mutation in main() survive: a real 24,986-byte index then passed. An integration
    # case must sit ON the boundary, not near it.
    with tempfile.TemporaryDirectory() as td:
        at_limit = pathlib.Path(td) / "at.md"
        at_limit.write_bytes(b"x" * 1000)
        over_by_one = pathlib.Path(td) / "over1.md"
        over_by_one.write_bytes(b"x" * 1001)
        check("main() passes a file of EXACTLY the limit", main([], index=at_limit, limit=1000), 0)
        check("main() fails a file ONE BYTE over, measured end to end",
              main([], index=over_by_one, limit=1000), 1)

    # --- ⟳ r1 CODEX #2c: the label main() prints was never witnessed, so replacing it with a
    # constant survived. Capture stdout and assert the real path reaches the reader.
    with tempfile.TemporaryDirectory() as td:
        absent = pathlib.Path(td) / "gone.md"
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc_absent = main([], index=absent, limit=1000)
        printed = buf.getvalue()
        check("main()'s CANNOT RUN reaches stdout naming the path it was GIVEN",
              (rc_absent, "gone.md" in printed), (2, True))
        buf2 = io.StringIO()
        with contextlib.redirect_stdout(buf2):
            main([], index=INDEX, limit=LIMIT_BYTES)
        check("an OK verdict NAMES the file too, repo-relative — not just the CANNOT RUN arms",
              "docs/memory/MEMORY.md" in buf2.getvalue(), True)

    # --- ⟳ r1 CODEX #6: present but UNREADABLE must be rc 2, not a traceback.
    with tempfile.TemporaryDirectory() as td:
        locked = pathlib.Path(td) / "locked.md"
        locked.write_bytes(b"x" * 100)
        locked.chmod(0o000)
        try:
            # ⛔ The precondition is ASSERTED, not assumed: as root the chmod is ignored and this
            # case would pass vacuously, which is the ambient-reason failure this repo keeps paying
            # for. A vacuous pass must look like a failure.
            check("the unreadable fixture is genuinely unreadable (precondition, not an assumption)",
                  os.access(locked, os.R_OK), False)
            # ⛔ The call is WRAPPED so that restoring the escape produces a RED CASE rather
            # than a crash. A crashing suite gives the mutation harness no case to attribute, and
            # this repo has already paid for a harness reading a cause from a child's text.
            try:
                rc_locked: object = main([], index=locked, limit=1000)
            except OSError as exc:
                rc_locked = f"RAISED {type(exc).__name__} instead of returning CANNOT RUN"
            check("a present-but-unreadable index is CANNOT RUN, not a traceback", rc_locked, 2)
        finally:
            locked.chmod(0o600)
    check("a CANNOT RUN names the file it ACTUALLY examined, not the module default",
          "nowhere/absent.md" in budget_verdict(None, 1000, "nowhere/absent.md")[1], True)
    check("the label defaults to the real index when none is given",
          "docs/memory/MEMORY.md" in budget_verdict(None, 1000)[1], True)
    check("the default label is DERIVED from INDEX, so it cannot be left behind by a repoint",
          INDEX_LABEL, str(INDEX.relative_to(ROOT)))

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
