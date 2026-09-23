#!/usr/bin/env python3
"""ONE owner for the observer-log record — the grammar four Stop observers write.

    python3 scripts/observer_log.py --self-test  # 39 cases

⛔ WHY THIS EXISTS, AND IT IS NOT THE INJECTION HOLE. Four functions in three files wrote the same
tab-separated record and nothing shared a line of it:

    check-banner-armed.log_line    (reason, detail, when, session)   ->  .claude/banner-warnings.log
    check-banner-armed.flush_line  (before, after, when, session)    ->  .claude/banner-flush-observations.log
    check-ci-watched.log_line      (reason, detail, when, session)   ->  .claude/ci-unwatched.log
    check-closing-table.log_line   (acts, when, session, turn)       ->  .claude/closing-table-warnings.log

The architecture review of 2026-09-22 (`docs/reviews/architecture-review-2026-09-22-observer-family.md`)
measured what that cost, and the expensive finding was NOT that three of the four were injectable:

⭐ **THE GRAMMAR HAD ALREADY DRIFTED, SILENTLY, AND NOTHING COULD HAVE CAUGHT IT** (backlog #170).
Columns 3 and 4 of the banner warning log swapped meaning between generations of the SAME FILE:

    .claude/banner-warnings.pre-backlog96.log   when session `STEP 4 of 5` `unarmed`   detail, reason
    .claude/banner-warnings.log (live)          when session `unarmed` `STEP 2 of 5`   reason, detail

MEASURED across every `*.py`, `*.sh`, `*.ts`, `*.js`, `*.yml`, `*.md` in the repo: these four files
have **FOUR WRITERS AND ZERO READERS**. A grammar with no consumer has no falsifier, so its columns
can invert and no test, guard or reviewer observes it. That is why `VERSION` below is the
load-bearing part of this module and the sanitiser is the cheap part.

THE VERSION MARKER IS A LEADING COLUMN, ON PURPOSE
--------------------------------------------------
Every record carries its own format token, rather than the file carrying one header:

  * a header cannot reach a file that already exists, and these logs are append-only;
  * a header does not survive rotation, and `.claude/banner-warnings*.log` has already been
    rotated twice;
  * a per-record token makes backlog #170's own falsifier trivial — concatenate two generations and
    the boundary is visible on EVERY line, not inferable from the file's first line.

⚠ **Records written before this module have NO version column**, and that is the signal, not a gap:
absence means "pre-v1, column meanings unknown, not comparable". Do not backfill them — a backfilled
marker would assert a format nobody verified.

WHAT THIS MODULE DOES NOT DO
----------------------------
It does not parse. Nothing reads these logs today (measured), and writing a reader here would be
inventing a consumer to justify a format. When a reader is genuinely needed it belongs beside
whatever needs it, and `VERSION` is what lets it refuse a record it does not understand.
"""
from __future__ import annotations

import datetime as _dt
import pathlib

# ⛔ BUMP THIS ONLY WHEN THE COLUMN MEANINGS CHANGE, and when you do, say so in the module that
# writes them. A version that moves for a cosmetic reason teaches a reader to ignore it.
VERSION = "v1"

SEP = "\t"

#: The value written when a field is empty. A bare empty column is indistinguishable from a
#: truncated record; a sentinel is not.
EMPTY = "-"


def col(v: object) -> str:
    """One field, with every separator this grammar uses removed. PURE.

    ⛔ FIELD INJECTION. `session` comes from outside the process — the Stop hook's payload — and
    three of the four producers passed it in raw. Measured on the pre-consolidation code against
    the expected shape of one record:

        log_line("unwatched", "d", "T", "sess\\tinjected")  ->  5 columns, not 4
        log_line("unwatched", "d", "T", "sess\\nsecond")    ->  2 records, not 1

    ⚠ **THIS ASKS `splitlines()` RATHER THAN LISTING SEPARATORS**, and that is the whole technique.
    `begin-plan.py --pause` had the same class one file over, and its first repair hand-wrote the
    line rule and covered **2 of the 11** characters `str.splitlines()` honours — so eight
    separators re-opened the hole. Delegating to the consumer's own function cannot drift from it.

    ⚠ It is deliberately STRICTER than any consumer: `splitlines()` breaks on `\\v`, `\\f`,
    `\\x1c-\\x1e`, `\\u2028`, `\\u2029`, which a reader splitting on `"\\n"` would not. A producer
    stricter than its reader is the safe direction — it can never emit a record the reader
    mis-splits.
    """
    # ⚠ THREE STATEMENTS, NOT ONE EXPRESSION, and that is deliberate. Each does a separable
    # job — coerce, kill the column separator, kill every line separator — so each can be
    # mutated independently. Folded into one line they share an anchor, and the mutation
    # harness refuses two entries with the same anchor because the second measures nothing new.
    s = "" if v is None else str(v)
    flat = s.replace(SEP, " ")
    return " ".join(flat.splitlines()) if flat else ""


def now() -> str:
    """The timestamp these records carry. PURE of arguments, not of the clock.

    ⛔ ONE SPELLING, because there were two. Measured 2026-09-22: `check-closing-table.py` used
    `strftime("%Y-%m-%dT%H:%M:%S%z")` -> `-0700` while the other three used `.isoformat()` ->
    `-07:00`. Both are valid ISO 8601 and `datetime.fromisoformat` accepts either on Python >= 3.11,
    so nothing was broken — but two spellings of one field in one grammar is the shape this module
    exists to remove.
    """
    return _dt.datetime.now().astimezone().replace(microsecond=0).isoformat()


def record(session: object, *fields: object, when: str | None = None) -> str:
    """One appended record, terminated. -> `VERSION⇥when⇥session⇥field…\\n`

    ⚠ **`when` IS INJECTABLE FOR TESTS AND DEFAULTS TO THE CLOCK.** A caller that stamps its own
    time and passes it in stays deterministic; one that omits it cannot be tested for its timestamp
    at all, which is how a frozen-clock case passes vacuously.

    ⚠ Every field goes through `col`, INCLUDING the ones a caller believes are safe. The caller who
    knows which of its arguments are externally sourced is exactly the caller who was wrong about it
    three times out of four.
    """
    stamped = when if when is not None else now()
    ts = col(stamped) or EMPTY
    sess = col(session) or EMPTY
    cells = [VERSION, ts, sess]
    cells += [col(f) or EMPTY for f in fields]
    return SEP.join(cells) + "\n"


def append(path: pathlib.Path, line: str) -> bool:
    """Best effort. -> True on success, False on any failure. NEVER raises.

    ⛔ A log that cannot be written must not turn an observer into a traceback — the observer's job
    is to report on someone else's work, and dying while doing it is strictly worse than staying
    silent.

    ⚠ **IT RETURNS THE FAILURE RATHER THAN SWALLOWING IT.** `check-ratchet-contract.py` refuses a
    guard with a fail-open handler, and rightly: the caller is the only place that knows whether a
    verdict is already being printed, so only the caller can decide whether a failed write is worth
    a word to the human.
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line)
        return True
    except OSError:
        return False


# ── --self-test ─────────────────────────────────────────────────────────────────────────────────

def _self_test() -> int:
    cases: list[tuple[str, bool]] = []

    def case(name: str, got: object, want: object) -> None:
        cases.append((name, got == want))
        if got != want:
            print(f"  [FAIL] {name}: got {got!r} want {want!r}")
        else:
            print(f"  ✓ {name}")

    # ── col: the separators ──────────────────────────────────────────────────────────────────
    case("col strips a TAB", col("a\tb"), "a b")
    case("col strips a NEWLINE", col("a\nb"), "a b")
    case("col strips a CARRIAGE RETURN", col("a\rb"), "a b")
    case("col strips CRLF as ONE break", col("a\r\nb"), "a b")
    # ⚠ These four are the eight separators a hand-written list missed one file over.
    case("col strips a VERTICAL TAB", col("a\vb"), "a b")
    case("col strips a FORM FEED", col("a\fb"), "a b")
    case("col strips U+2028 LINE SEPARATOR", col("a b"), "a b")
    case("col strips U+2029 PARAGRAPH SEPARATOR", col("a b"), "a b")
    case("col strips FILE SEPARATOR U+001C", col("a\x1cb"), "a b")
    case("col leaves ordinary text alone", col("plain text"), "plain text")
    case("col on empty is empty", col(""), "")
    case("col on None is empty", col(None), "")
    case("col stringifies a non-str", col(42), "42")
    # ⚠ TWO DISTINCT INPUTS: a case asserting a derived value must exercise its producer twice,
    # or a constant satisfies it. (backlog #164)
    case("col is not a constant (a)", col("x\ty"), "x y")
    case("col is not a constant (b)", col("p\tq\tr"), "p q r")

    # ── record: shape ────────────────────────────────────────────────────────────────────────
    r = record("sess", "reason", "detail", when="T")
    # ⛔ THE LITERAL, NEVER THE SYMBOL. r1 BLOCKING 2: this read `..., VERSION)`, so blanking
    # `VERSION` made both sides "" and the case could not observe its own subject. The mutation
    # `VERSION = ""` SURVIVED 37/37 — a test that cannot fail, in the module whose entire point
    # is that column.
    case("record starts with the VERSION column", r.split(SEP)[0], "v1")
    case("...and the version cell is NON-EMPTY, which is what blanking the constant attacks",
         bool(r.split(SEP)[0]), True)
    case("record puts `when` second", r.split(SEP)[1], "T")
    case("record puts `session` third", r.split(SEP)[2], "sess")
    case("record appends the fields in order", r.split(SEP)[3:], ["reason", "detail\n"])
    case("record terminates with a newline", r.endswith("\n"), True)
    case("record has version+when+session+2 fields = 5 columns", len(r.split(SEP)), 5)
    # two distinct inputs again — a frozen field count would pass a single case
    r3 = record("s", "a", "b", "c", when="T")
    case("record column count tracks the field count", len(r3.split(SEP)), 6)

    # ── record: the injection the module exists to close ─────────────────────────────────────
    inj_tab = record("sess\tinjected", "reason", "detail", when="T")
    case("an injected TAB cannot add a column", len(inj_tab.split(SEP)), 5)
    inj_nl = record("sess\nsecond", "reason", "detail", when="T")
    case("an injected NEWLINE cannot add a record",
         len(inj_nl.rstrip("\n").split("\n")), 1)
    case("an injected separator survives as TEXT, not structure",
         "injected" in inj_tab, True)
    case("a field is sanitised too, not only the session",
         len(record("s", "x\ty", when="T").split(SEP)), 4)
    case("`when` is sanitised as well",
         len(record("s", "f", when="T\tZ").split(SEP)), 4)

    # ── record: empties degrade to a sentinel, never to a bare column ─────────────────────────
    # ⛔ LITERALS AGAIN (r1 HIGH 3): these compared against `EMPTY`, so blanking it passed.
    case("an empty session becomes the sentinel", record("", "f", when="T").split(SEP)[2], "-")
    case("a None session becomes the sentinel", record(None, "f", when="T").split(SEP)[2], "-")
    case("an empty field becomes the sentinel", record("s", "", when="T").split(SEP)[3], "-\n")
    case("a session that is ONLY a separator becomes the sentinel",
         record("\n", "f", when="T").split(SEP)[2], "-")

    # ── now(): one spelling ──────────────────────────────────────────────────────────────────
    stamp = now()
    case("now() offset uses a COLON (isoformat, not %z)",
         bool(stamp[-6] == "+" or stamp[-6] == "-") and stamp[-3] == ":", True)
    case("now() carries no microseconds", "." not in stamp.split("T")[1], True)
    # ⛔ r1 HIGH 4: this was `!= ""`, which `col(x) or EMPTY` can never be — true for EVERY
    # implementation, including a frozen `ts`. The retired R5-646c property came back here.
    case("record carries the `when` it was GIVEN, at two distinct inputs",
         (record("s", "f", when="T1").split(SEP)[1],
          record("s", "f", when="T2").split(SEP)[1]), ("T1", "T2"))
    case("record defaults `when` to a real stamp when omitted, not to the sentinel",
         record("s", "f").split(SEP)[1] not in ("", EMPTY, "T1"), True)

    # ── append: never raises, reports its failure ────────────────────────────────────────────
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        p = pathlib.Path(td) / "sub" / "x.log"
        case("append creates missing parents and writes", append(p, "a\n"), True)
        case("append is additive", (append(p, "b\n"), p.read_text())[1], "a\nb\n")
    # a directory is not writable as a file -> False, never an exception
    with tempfile.TemporaryDirectory() as td:
        d = pathlib.Path(td) / "adir"
        d.mkdir()
        case("append returns False on OSError rather than raising", append(d, "x\n"), False)

    failed = [n for n, ok in cases if not ok]
    print(f"\n{len(cases) - len(failed)}/{len(cases)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    import sys
    sys.exit(_self_test() if "--self-test" in sys.argv else 0)
