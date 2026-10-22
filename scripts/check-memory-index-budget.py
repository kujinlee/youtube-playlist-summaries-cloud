#!/usr/bin/env python3
"""`docs/memory/MEMORY.md` is injected whole on every turn, and when it overflows the harness
TRUNCATES IT IN SILENCE.

WHY THIS EXISTS — measured 2026-10-19, and no gate in this repo could see it.
-----------------------------------------------------------------------------
The index reached **26,930 characters against the harness's 24,985-character limit**, and **8 rows
of its tail did not arrive** — counted out of a consuming agent's own context, not modelled. Every
signal available in the repo was green: `check-memory-link.py` verified the symlink,
`recall-llm.py`'s `corpus_verdict` counted a healthy corpus, `check-docs.py` enforced its line
budget. None of them measures the one quantity that decides whether a row ARRIVES — the length of
the always-loaded file.

⟳ THE ROW FIGURE WAS WRONG ON BOTH HALVES AND TOOK TWO ROUNDS TO SETTLE (r1 CODEX #4, then
r1 CLAUDE H2). It read "roughly 30 of its 118 rows". The denominator was counted AFTER the rows had
been moved out and then written up as though it described the file that failed — the overflowing
index had **145** rows. The numerator was `(27,805 − 24,985) / mean-row-size`, an estimate dressed
as a count, and it is wrong because the overflow falls in the slice-history TAIL whose rows are the
longest in the file. **Measured, 8 rows.** The `a-retrospective-number-needs-provenance` tell was
present throughout: a round figure supporting a sound argument.

⛔ THE TRUNCATION UNIT IS NOW MEASURED, AND THIS DOCSTRING USED TO SAY IT COULD NOT BE — see
`index_chars`. What is STILL unverified is narrower: whether the cut is a strict prefix at that
character count, or whether whole rows are dropped, or whether framing is counted too. The observed
cut sat 27 characters under the declared limit, i.e. one row short of it, which is consistent with a
prefix cut and with a row-wise cut alike. So the UNIT is established and the ALGORITHM is not.

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
is not a rule here: measured over the index that ACTUALLY overflowed (`dff6a3f0^`), **35 of its 145
rows exceed 200 characters**, the longest being **602**. A gate red from birth on a quarter of its
subject gets switched off — #56's measured verdict — and the rows are long because they carry
evidence. ⟳ r1 CLAUDE L1: this exclusion was itself stated in BYTES (38 over 200) against a rule the
harness states in CHARACTERS — the same unit error as H1, which makes it a CLASS and not an
instance. Both are now characters.

⚠ THE FAILURE DIRECTION, STATED RATHER THAN HIDDEN. `LIMIT_CHARS` is a DECLARED constant read from
the harness's own warning text. So if the harness ever LOWERS its limit, this guard goes quiet while
truncation silently resumes: it fails toward good news, which is the direction that gets believed.
Two mitigations, both partial: the WARN band fires at 90% so there is a signal before the cliff, and
the constant carries the verbatim warning it came from.
⛔ AND THE SENTENCE THAT USED TO SIT HERE — *"nothing in the repo can interrogate the harness"* — IS
FALSE, which is the most useful thing this guard has learned. A session that RECEIVES the truncated
index is itself an observation of the producer: the cut point in its own context measures both the
unit and the limit directly. I had treated the harness as external to the system rather than as
something a reader of this repo IS. The check is reproducible by anyone who gets the warning, and
it is the refutation route to prefer over the other two below.
⟳ r1 CODEX #5: the constant can be wrong in MORE ways than a lowered limit, and an earlier version
of this note called one observation "the ONLY" refutation, which was itself an overclaim. It can
also be wrong through the KB unit (1000 vs 1024), a harness or version change, or budgeting applied
after framing or transformation — and a RAISED limit makes this guard fail falsely rather than
quietly. ⛔ Refutations, none of them unique: the harness warning about truncation while this is
green; a controlled boundary experiment; or a published producer specification.

    python3 scripts/check-memory-index-budget.py
    python3 scripts/check-memory-index-budget.py --self-test  # 59 cases
"""
from __future__ import annotations

import contextlib
import io
import os
import pathlib
import re
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
# 24.4KB is reported to one decimal place, so this is the limit to within ~51 CHARACTERS. The band
# below is what covers that imprecision: a file inside 90% of the limit cannot be near the cliff
# whichever way the rounding went.
LIMIT_CHARS = int(24.4 * 1024)  # 24,985
WARN_FRACTION = 0.90


def warn_threshold(limit: int) -> int:
    """PURE. -> the character count at which the index is close enough to the cliff to say so.

    DERIVED from the limit on purpose. A second literal here would be a constant that agrees with
    `LIMIT_CHARS` only until someone edits one of them — this repo's most-measured defect class.
    """
    return int(limit * WARN_FRACTION)


def budget_facts(n_chars: int | None, limit: int, label: str = INDEX_LABEL) -> dict[str, object]:
    """PURE. -> the FACTS of the verdict: rc, state, and every number the message will render.

    ⛔ THIS SPLIT IS A REDESIGN, NOT A REFACTOR, AND IT EXISTS BECAUSE PATCHING FAILED THREE ROUNDS
    RUNNING ON ONE FUNCTION. The history, because it is the justification:

      r1 CLAUDE N1  `"1 characters…" in msg` was vacuous — the overage `1` is a decimal SUFFIX of
                    the total `1,001`. A mutant printing the total survived.
      r2 CODEX #1   my repair banned the literal total. A mutant rendering `overage + 1000` gives
                    `1,007`, which still ends in `7`. Survived again. I had fixed the INSTANCE.
      r2 CLAUDE H2  the three messages render TEN numeric fields and only TWO carried a value
                    assertion. Seven more survivors, including the SAME defect in the WARNING arm.
      r2 CLAUDE H1  `{label}` replaced by the literal `docs/memory/MEMORY.md` survives 51/51 in all
                    three arms — so the guard can measure the WRONG FILE and NAME THE RIGHT ONE,
                    which is precisely the composite r1 CODEX #2a was fixed for.

    That is this repo's THRASHING shape: two consecutive rounds carrying findings caused by the
    previous round's own fix, in one component. The standing lesson is `refuse, don't widen` — change
    the KIND of fix. So the numbers stop being things a case greps out of prose and become VALUES a
    case reads directly; `render()` turns them into the message, and one case asserts that every fact
    reaches it. A new field is then covered by construction rather than by remembering to add a case.
    """
    if n_chars is None:
        # ⚠ No `limit` here: the message does not show it, because a limit is meaningless when
        # nothing was measured. The closed-loop case in the suite REFUSES a fact the reader
        # never sees, so this set is exactly what `render` conveys.
        return {"rc": CANNOT_RUN, "state": "unreadable", "label": label}
    if n_chars == 0:
        return {"rc": CANNOT_RUN, "state": "empty", "label": label}
    warn_at = warn_threshold(limit)
    common = {"label": label, "chars": n_chars, "limit": limit}
    if n_chars > limit:
        return {"rc": OVER_BUDGET, "state": "over", **common, "overage": n_chars - limit}
    if n_chars >= warn_at:
        return {"rc": OK, "state": "warn", **common, "headroom": limit - n_chars,
                "percent": 100 * n_chars // limit}
    return {"rc": OK, "state": "ok", **common, "headroom": limit - n_chars}


def render(f: dict[str, object]) -> str:
    """PURE. -> the reader-facing message for `f`. Every value comes FROM `f`, never recomputed.

    ⚠ Recomputing anything here would re-open the defect the split closes: a case asserting the
    facts would then be silent about what the reader is shown.
    """
    label = f["label"]
    state = f["state"]
    if state == "unreadable":
        return (f"CANNOT RUN — {label} could not be READ — it is absent, or present and unreadable "
                "— so the always-loaded budget was NOT measured. Treat this as NOT RUN, never as a "
                "pass.")
    if state == "empty":
        return (f"CANNOT RUN — {label} is EMPTY. That is not a small index, it is a missing one; the "
                "budget was NOT measured. Treat this as NOT RUN, never as a pass.")
    limit = f["limit"]
    if state == "over":
        return (f"OVER BUDGET — {label} is {f['chars']:,} CHARACTERS against the harness's "
                f"{limit:,}-character limit, so it is being TRUNCATED IN SILENCE and the last "
                f"{f['overage']:,} characters of its tail never arrive. Nothing chose what those "
                f"are. REMEDY: move history-shaped rows into {OVERFLOW_TARGET}, which is a TRIGGERED "
                "corpus entry — they still arrive, on demand, instead of being loaded every turn.")
    if state == "warn":
        return (f"WARNING: {label} is {f['chars']:,} characters, within {f['headroom']:,} characters "
                f"of the harness's {limit:,}-character limit ({f['percent']}% of budget). Nothing is "
                f"being dropped YET. Move history-shaped rows into {OVERFLOW_TARGET} before it is. "
                "(Advisory.)")
    return (f"ok — {label} is {f['chars']:,} characters, {f['headroom']:,} under the harness's "
            f"{limit:,}-character limit, so nothing is being dropped. ⚠ 'Every row arrives' would "
            f"overclaim: the limit is DECLARED to one decimal place (r1 CODEX #5), so treat this as "
            f"within the budget as measured, not as a proof of delivery.")


def budget_verdict(n_chars: int | None, limit: int, label: str = INDEX_LABEL) -> tuple[int, str]:
    """PURE. -> (rc, message). A thin composition of `budget_facts` and `render`, kept because
    `main` and every existing case read a pair. The two outcomes it must keep distinct are
    "cannot measure" and "measured, and it is fine" — they must never share an exit code.
    """
    f = budget_facts(n_chars, limit, label)
    return int(f["rc"]), render(f)  # type: ignore[arg-type]


def index_chars(path: pathlib.Path) -> int | None:
    """-> the file's length in CHARACTERS, or None when it cannot be read.

    ⛔ CHARACTERS, AND THIS WAS BYTES UNTIL r1 CLAUDE H1 MEASURED THE PRODUCER I HAD CALLED
    UNREACHABLE. The docstring above used to argue for bytes, and the argument was false twice over.
    Two independent measurements, both reproducible from any session that receives the warning:

      1. The harness's own reported figure. It printed `MEMORY.md is 26.3KB` about a file that is
         26,930 characters and 27,805 bytes. 26,930/1024 = 26.30 -> "26.3KB". 27,805/1024 = 27.15
         -> would have printed "27.2KB". The number it chose is the CHARACTER count.
      2. The truncation point, read out of a consuming agent's own injected context. The cut fell
         at character 24,958 (27 UNDER the declared 24,985) and byte 25,771 (786 OVER it). A byte
         limit of 24,985 cannot produce a cut at byte 25,771; a character limit produces exactly
         this one, to within a row.

    ⛔ WHAT THAT DOES AND DOES NOT ESTABLISH (r2 CODEX #4, correcting an overclaim of mine). It rules
    out BYTES. It does NOT settle WHICH character-like count: the index contains a non-BMP character
    (a red circle), so it is 26,930 code points but 26,931 UTF-16 units — and BOTH round to the
    reported 26.3KB, so the warning arithmetic cannot separate them. `len()` here counts Python code
    points. ⚠ A controlled producer boundary experiment was NOT run, so this is unresolved rather
    than decided, and the margin it costs is at most a handful of characters against a 2,900-character
    headroom. ⛔ Do not upgrade "not bytes" into "code points, confirmed" without running that
    experiment: a fixture of `24,984 x "x" + one astral character` counts 24,985 here and 24,986 in
    UTF-16, which is the input that would separate them.

    ⚠ THE OLD BEHAVIOUR WAS WRONG IN THE SAFE DIRECTION, WHICH IS WHY NOTHING CAUGHT IT. In UTF-8
    `len(bytes) >= len(chars)`, so counting bytes against a character limit fires EARLY: it could
    never produce a false green, only a false red, and the live margin it misstated was ~3%. ⛔ But
    the SUITE AND THE MANIFEST had pinned bytes as the invariant to protect — a manifest entry whose
    job is to forbid the right answer, which is the `a-guard-can-mandate-the-duplication-it-audits`
    shape and cannot be reworded out of.

    ⟳ r1 CODEX #6: `read_bytes()` raised straight through, so an unreadable index produced a
    TRACEBACK instead of a named CANNOT RUN at rc 2 — the exit contract this guard advertises.
    Narrow `OSError`, and the returned None is a FAILING state, never a pass, so this is not the
    fail-open handler `check-ratchet-contract` R2 forbids.
    """
    # ⛔ `is_file()` IS INSIDE THE TRY, and that is not tidiness — r3 CLAUDE High. On Python < 3.13
    # it RAISES `OSError` (ENAMETOOLONG) for an over-long path instead of returning False, which
    # `ci.yml`'s own python-pin comment documents as the divergence that cost PR #315 a day.
    try:
        if not path.is_file():
            return None
        # ⛔ `read_bytes().decode()`, NEVER `read_text()`. Two separate reasons, and the SECOND one
        # broke CI:
        #   1. `read_text` applies UNIVERSAL-NEWLINE TRANSLATION. Measured (r2 CODEX #4):
        #      9,000 x b"x\r\n" is 27,000 characters on disk and it reported 18,000 — one character
        #      lost per line. That UNDER-counts, i.e. reports "under budget" about an index that is
        #      over: the direction that fails toward good news.
        #   2. ⛔ MY FIX FOR (1) WAS `read_text(newline="")`, AND THAT PARAMETER IS PYTHON 3.13+.
        #      `ci.yml` pins 3.12, so the guard died with a TypeError IN THE REQUIRED `verify` JOB —
        #      measured on run 39375344140: `verify` failed AT THIS STEP, 47 of its 77 steps never
        #      ran, and every mutation shard reported NOT MEASURED because one red control voids the
        #      whole run. A guard that crashes takes down far more than itself.
        # ⚠ AND THIS REPO ALREADY HAD THE ANSWER UNDER A NAME I DID NOT SEARCH FOR:
        # `check-doc-citations.py:536` — "`read_bytes().decode(...)`, NEVER `read_text(...)`" — for
        # reason (1), recorded there as the second half of a fix that also shipped incomplete.
        return len(path.read_bytes().decode("utf-8"))
    except (OSError, UnicodeDecodeError):
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


def main(argv: list[str], index: pathlib.Path = INDEX, limit: int = LIMIT_CHARS) -> int:
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
    rc, msg = budget_verdict(index_chars(index), limit, shown)
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
    # ⛔ THE PARSED-FIELD CASES THAT STOOD HERE ARE DELETED, NOT WEAKENED, AND THAT IS THE POINT.
    # Three rounds of string assertions on ONE function — r1 CLAUDE N1, r2 CODEX #1, r2 CLAUDE H2 —
    # each covered the single field the previous round had found. I had written that parsing "is the
    # only form that cannot be fooled"; r2 CLAUDE falsified that with a float rendering. The facts
    # split above supersedes all of it: numbers are asserted as VALUES and one loop proves each
    # reaches the reader. A superseded mechanism kept "just in case" is one more thing to be wrong.

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

    # --- THE FACTS, AND THE RENDERING, AS A CLOSED LOOP (r2 CLAUDE H1 + H2) ---------------
    # ⛔ This block is why the split exists. Three rounds of string assertions each covered the ONE
    # field the previous round had found; ten fields were rendered and two were asserted. Here the
    # facts are asserted as VALUES, and then ONE loop asserts every fact REACHES the reader — so a
    # field added later is covered without anyone remembering to add a case.
    LBL = "fixture/INDEX.md"  # deliberately NOT the module literal, so H1's mutation cannot hide

    def _shown(v: object) -> str:
        return f"{v:,}" if isinstance(v, int) else str(v)

    def _shows(msg: str, val: str) -> bool:
        """-> True when `val` appears in `msg` as a WHOLE number, not inside a longer one.

        ⛔ A BARE `in` CANNOT DO THIS, and that is the fifth appearance of one defect. `414` IS a
        substring of `1,414`, so a mutant adding 1000 to the headroom survived the closed loop even
        after its pairwise precondition — the vacuity there is between a value and its OWN mutated
        rendering, which comparing facts to each other can never see. The lookarounds reject a
        digit or comma on either side, so `414` does not match inside `1,414` while `within 414 `
        still does.
        """
        return re.search(r"(?<![\d,])" + re.escape(val) + r"(?![\d,])", msg) is not None

    def _vacuous_pairs(vals: list[str]) -> list[str]:
        """-> renderings that are SUBSTRINGS of one another, which makes an `in` test vacuous.

        ⛔ THIS PRECONDITION IS THE POINT. My first closed loop used chars=920/limit=1000, giving
        headroom 80 and percent 92 — and `"80"` is a substring of `"1,080"` while `"92"` hides
        inside `"920"`. Two mutants survived the very loop written to catch them: the FOURTH
        consecutive appearance of the suffix defect on this one function. A fixture whose values
        can contain each other cannot witness anything, so the suite REFUSES such a fixture
        instead of trusting that someone chose well.
        """
        return [f"{a!r} is inside {b!r}" for a in vals for b in vals if a != b and a in b]

    OVER_F = budget_facts(9876, 8191, LBL)   # overage 1,685
    WARN_F = budget_facts(7777, 8191, LBL)   # headroom 414, percent 94
    OK_F = budget_facts(123, 8191, LBL)      # headroom 8,068
    check("the OVER facts are exact", OVER_F,
          {"rc": 1, "state": "over", "label": LBL, "chars": 9876, "limit": 8191, "overage": 1685})
    check("the WARN facts are exact", WARN_F,
          {"rc": 0, "state": "warn", "label": LBL, "chars": 7777, "limit": 8191,
           "headroom": 414, "percent": 94})
    check("the OK facts are exact", OK_F,
          {"rc": 0, "state": "ok", "label": LBL, "chars": 123, "limit": 8191, "headroom": 8068})
    check("the CANNOT RUN facts name the state and keep the label",
          (budget_facts(None, 8191, LBL), budget_facts(0, 8191, LBL)),
          ({"rc": 2, "state": "unreadable", "label": LBL},
           {"rc": 2, "state": "empty", "label": LBL}))

    # ⛔ THE CLOSED LOOP, with its own vacuity guarded. Every fact must REACH the message, and no
    # fact's rendering may be a substring of another's — otherwise the `in` below proves nothing.
    # This kills r2 CLAUDE H1 (a literal label) and H2 (any numeric field replaced or shifted) in
    # EVERY arm at once, which is what three rounds of one-field-per-round patches could not do.
    _missing: list[str] = []
    _vacuous: list[str] = []
    for _f in (OVER_F, WARN_F, OK_F, budget_facts(None, 8191, LBL), budget_facts(0, 8191, LBL)):
        _msg = render(_f)
        _vals = [_shown(v) for k, v in _f.items() if k not in ("rc", "state")]
        _vacuous += [f"{_f['state']}: {d}" for d in _vacuous_pairs(_vals)]
        _missing += [f"{_f['state']}.{k}={_shown(v)!r}" for k, v in _f.items()
                     if k not in ("rc", "state") and not _shows(_msg, _shown(v))]
    check("no fact's rendering hides inside another's, so the membership test is not vacuous",
          _vacuous, [])
    # ⛔ A KNOWN POSITIVE FOR THE PRECONDITION ITSELF. Without this the rule above is correct and
    # UNEXERCISED — the shipped fixture has no concealing pair, so neutering `_vacuous_pairs` to
    # `return []` changed nothing and the mutation SURVIVED. A guard that never fires on its own
    # fixture is indistinguishable from one that does nothing; these are the exact values that
    # defeated the first closed loop.
    check("_vacuous_pairs DETECTS a concealing pair (the 80-inside-1,080 that defeated the first "
          "loop)", _vacuous_pairs(["80", "1,080"]), ["'80' is inside '1,080'"])
    check("_vacuous_pairs is silent on values that cannot conceal each other",
          _vacuous_pairs(["414", "9,876"]), [])

    # ⛔ A SECOND LABEL AND A SECOND LIMIT, because `check-fixture-variation` REFUSED the block
    # above: every call passed the same two values, so no case could tell either parameter from a
    # constant. `exercise-the-producer-at-two-distinct-inputs`, caught by the guard rather than by
    # me, in the very block written to fix a coverage defect.
    ALT = "other/PLACE.md"
    check("the label and the limit are both THREADED, not read from module state",
          budget_facts(500, 400, ALT),
          {"rc": 1, "state": "over", "label": ALT, "chars": 500, "limit": 400, "overage": 100})
    check("render() is called on an independently built fact set too, not only the loop's",
          render({"state": "ok", "label": ALT, "chars": 7, "limit": 400, "headroom": 393})
          .startswith(f"ok — {ALT} is 7 characters, 393 under"), True)
    # The delimited matcher, exercised at the exact input that defeated the bare `in`.
    check("a number is matched as a WHOLE token: 414 is NOT found inside 1,414",
          (_shows("within 414 characters", "414"), _shows("within 1,414 characters", "414")),
          (True, False))
    check("EVERY fact reaches the rendered message, in every state", _missing, [])

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
    # ⟳ r1 CLAUDE H3 mutation G: merging the two arms (`is None or == 0`) left 40/40 GREEN, because
    # every case here read only the rc and the shared tail. The two states need DIFFERENT remedies —
    # a missing file is a path problem, an empty one is a destroyed index — so the messages must be
    # distinguishable, not merely both rc 2.
    check("an EMPTY index says EMPTY and an ABSENT one does not",
          ("EMPTY" in budget_verdict(0, L)[1], "EMPTY" in budget_verdict(None, L)[1]), (True, False))
    check("an ABSENT index says it could not be read, and the EMPTY one does not claim that",
          ("could not be READ" in budget_verdict(None, L)[1],
           "could not be READ" in budget_verdict(0, L)[1]), (True, False))

    # --- the warn band is DERIVED, exercised at two DISTINCT inputs -----------------------
    # One input could be satisfied by a constant that happens to equal it; two cannot.
    check("the warn threshold tracks the limit it is given",
          (warn_threshold(1000), warn_threshold(2000)), (900, 1800))

    # --- CHARACTERS, not bytes (r1 CLAUDE H1). ⛔ THIS CASE WAS INVERTED. It pinned BYTES, and the
    # manifest entry guarding it would therefore have killed the CORRECT behaviour once the unit was
    # established — a mutation whose job was to forbid the right answer, which is the
    # `a-guard-can-mandate-the-duplication-it-audits` shape. The unit is the harness's own, measured
    # two independent ways from a consuming agent's context; see `index_chars`.
    with tempfile.TemporaryDirectory() as td:
        f = pathlib.Path(td) / "glyphs.md"
        f.write_text("⭐⛔⟳\n")  # 3 glyphs x 3 bytes + newline = 10 BYTES but 4 CHARACTERS
        check("index_chars counts CHARACTERS, not bytes (multi-byte glyphs)", index_chars(f), 4)
        check("the byte count genuinely differs, so this case is not a tautology",
              len(f.read_bytes()), 10)
        # ⛔ r2 CODEX #4: CRLF. `read_text` without newline="" TRANSLATES line endings, so this
        # file counted 18,000 instead of 27,000 — one character lost per line. ⚠ That under-counts,
        # i.e. it reports "under budget" about an index that is over: the DANGEROUS direction, the
        # opposite of the byte/character error this guard was built on.
        crlf = pathlib.Path(td) / "crlf.md"
        crlf.write_bytes(b"x\r\n" * 9)
        check("index_chars does NOT translate CRLF away (27 chars, not 18)", index_chars(crlf), 27)
        # r2 CODEX #5: dropping UnicodeDecodeError from the handler let invalid UTF-8 ESCAPE.
        bad = pathlib.Path(td) / "invalid.md"
        bad.write_bytes(b"x" * 10 + b"\xff\xfe" + b"x" * 10)
        try:
            rc_bad: object = main([], index=bad, limit=1000)
        except UnicodeDecodeError:
            rc_bad = "RAISED UnicodeDecodeError instead of returning CANNOT RUN"
        check("an index that is not valid UTF-8 is CANNOT RUN, not a traceback", rc_bad, 2)
        check("the translated count genuinely differs, so that case is not a tautology",
              len(crlf.read_text(encoding="utf-8")), 18)

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
        check("main() reads the limit it is given, not LIMIT_CHARS",
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
    # ⛔ r2 CODEX #2: extracting `unknown_args` to escape the recursion ALSO DELETED the only case
    # that tested ORDER. Measured: moving the self-test dispatch back above the validation passes
    # 43/43 while `main(["--self-test","--bogus"])` returns 0 again — the predicate stays correct
    # while its CALLER violates the contract. ⛔ Driving the real suite recurses, so STUB it: the
    # stub records invocation, which is the observation that distinguishes the two orders.
    _selftest_calls: list[int] = []
    _real_selftest = globals()["_self_test"]
    globals()["_self_test"] = lambda: (_selftest_calls.append(1), OK)[1]
    try:
        rc_both = main(["--self-test", "--bogus"])
    finally:
        globals()["_self_test"] = _real_selftest
    check("validation runs BEFORE dispatch: an unknown flag beside --self-test is refused and the "
          "suite is NOT entered", (rc_both, _selftest_calls), (2, []))

    # ── r2 CODEX #5: three branches with no witness. ──────────────────────────────────────
    check("WARN_FRACTION is the declared 0.90, pinned so a near-miss like 0.9004 cannot slip",
          WARN_FRACTION, 0.90)
    check("warn_threshold TRUNCATES rather than rounding (int, not round)",
          (warn_threshold(1001), warn_threshold(1005)), (900, 904))

    # --- ⟳ r1 CODEX #2a: THE SUBJECT ITSELF. Repointing INDEX at another corpus file left all
    # 26 cases green, which defeats the guard's whole purpose — it would cheerfully measure the
    # wrong file and report "every row arrives" about a file nothing injects. Nothing asserted
    # WHAT is measured; every case supplied its own path or size.
    check("INDEX is the always-loaded index, not some other corpus file", INDEX.name, "MEMORY.md")
    check("INDEX is built from the repo root, so it survives a cwd change",
          INDEX, ROOT / "docs" / "memory" / "MEMORY.md")
    # ⟳ r2 CLAUDE medium: this was named "the file the harness symlink actually serves" while
    # asserting only `is_file()`, which says nothing about the symlink. Named for what it checks.
    check("INDEX exists as a regular file in this checkout", INDEX.is_file(), True)

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
            main([], index=INDEX, limit=LIMIT_CHARS)
        # ⟳ r1 CLAUDE L3: this was `"docs/memory/MEMORY.md" in ...`, which an ABSOLUTE path also
        # satisfies as a substring — so dropping `relative_to` survived at 40/40. Assert the
        # absolute form is ABSENT, which is the property that actually distinguishes them.
        printed_ok = buf2.getvalue()
        check("an OK verdict names the file REPO-RELATIVE, with no absolute prefix",
              ("docs/memory/MEMORY.md" in printed_ok, str(ROOT) in printed_ok), (True, False))

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
            # ⟳ r1 CLAUDE N1, same class: `except OSError: return 0` also yields rc 2, so the rc
            # alone cannot tell "unreadable" from "empty" — and they need different remedies.
            buf3 = io.StringIO()
            with contextlib.redirect_stdout(buf3):
                try:
                    main([], index=locked, limit=1000)
                except OSError:
                    pass
            locked_msg = buf3.getvalue()
            check("an UNREADABLE index says it could not be read, and does NOT claim to be EMPTY",
                  ("could not be READ" in locked_msg, "EMPTY" in locked_msg), (True, False))
        finally:
            locked.chmod(0o600)
    check("a CANNOT RUN names the file it ACTUALLY examined, not the module default",
          "nowhere/absent.md" in budget_verdict(None, 1000, "nowhere/absent.md")[1], True)
    check("the label defaults to the real index when none is given",
          "docs/memory/MEMORY.md" in budget_verdict(None, 1000)[1], True)
    check("the default label is DERIVED from INDEX, so it cannot be left behind by a repoint",
          INDEX_LABEL, str(INDEX.relative_to(ROOT)))

    # --- the declared constant, and the live file -----------------------------------------
    check("LIMIT_CHARS matches the 24.4KB the harness reported", LIMIT_CHARS, 24985)
    # ⛔ THE "LIVE INDEX IS WITHIN BUDGET" CASE IS DELETED — r3 CLAUDE High, and the blast radius is
    # why. It asserted `budget_verdict(index_chars(INDEX), …) == OK`, which coupled THIS SUITE'S
    # RESULT TO THE LENGTH OF `MEMORY.md`. The mutation harness treats one red control as
    # `NotMeasured` for the WHOLE RUN, so an index merely growing past budget would have made all
    # 1,573 manifest entries report NO COVERAGE VERDICT — a repo-wide false alarm triggered by a
    # document. ⚠ And it bought nothing: `ci.yml`'s "Memory index injection budget" step runs the
    # guard against the live index three lines above the step that runs this suite, so the property
    # was already enforced where it belongs — in a CALLER, not inside the suite that must stay
    # measurable. A suite case should assert the RULE; a caller asserts the WORLD.
    check("INDEX is measurable at all here, which is the only live property this suite needs",
          index_chars(INDEX) is not None, True)

    print(f"self-test: {ok}/{ok + fail} cases passed")
    return OK if fail == 0 else OVER_BUDGET


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
