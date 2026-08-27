#!/usr/bin/env python3
"""Backlog 26's trigger, made observable: has a NON-TEST caller reached `record_artifact` yet?

    python3 scripts/check-paid-caller-arrival.py
    python3 scripts/check-paid-caller-arrival.py --self-test

    exit 0 = DORMANT — no production caller. Backlog 26 may remain open.
    exit 1 = FIRED   — a production caller exists. Backlog 26 must be closed FIRST.
    exit 2 = CANNOT RUN (treat as NOT RUN, never as dormant)

WHY THIS IS A SCRIPT AND NOT A SENTENCE
---------------------------------------
Backlog 26 is the attempt-ceiling decision: ADR-0007 deleted `reserve_artifact_slot`, and with it
the only per-kind attempt bound on the money path. The surviving bound is `jobs.max_attempts`, which
defaults to 5 — so shipping a real caller before that decision **silently promotes a summary from 1
paid attempt to 5**. It costs nothing today and costs money the day it ships.

Its trigger was prose: *"this must be closed BEFORE the schema ships to an environment where a
worker calls `record_artifact` for a `summary`"*. The M4 plan's Task 10 flagged that shape twice —
v3's own paragraph called it *"a decision wearing a checkbox"* and then wrote one — and
`docs/dev-process.md` says the same thing generally: **before adding a rule, ask whether it can be a
script.** This one can. The observation that makes it fail is exactly: a non-test file under
`lib/ app/ worker/ components/` names `record_artifact` outside a comment.

⛔⛔ THE FAILURE MODE THIS GUARD HAS TO SURVIVE IS ITS OWN VOCABULARY GOING STALE.
A grep for a symbol reports "no callers" just as happily when the symbol has been RENAMED as when it
genuinely has none — and it would then read DORMANT forever, which is the one answer that lets the
money defect ship. `hardcode-only-what-fails-loudly`: hardcode what announces its own wrongness.
So before looking for callers, this asserts the symbol still EXISTS in the shipped migration. If it
does not, that is a CANNOT RUN with the reason named — never a pass.

⚠ COMMENTS ARE NOT CALLERS, AND ARE REPORTED RATHER THAN DROPPED. Today's only matches are two
comment lines in `tests/lib/blob-addressing-caller-contract.test.ts` describing the schema's history.
A guard that fired on those would be red while nothing is wrong, and a guard that is red when
nothing is wrong gets disabled. But silently discarding them would hide the day one of them becomes
a call, so both counts are printed every run.

⚠ Backlog 26's own prose says the grep "returns one comment". MEASURED 2026-08-26: it is TWO lines,
in that same file. The number in the row is a second representation of what this script computes;
the script is the one that cannot drift.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The symbol whose first production caller is the event. Named once.
SYMBOL = "record_artifact"

# Where the shipped definition must still be found, or the vocabulary has rotted.
DEFINITION_SOURCES = (
    ROOT / "supabase/migrations/0027_stable_blob_addressing.sql",
    ROOT / "docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/04_artifacts.sql",
)
DEFINES = re.compile(rf"create\s+(or\s+replace\s+)?function\s+{SYMBOL}\b", re.IGNORECASE)

# Production surface. `tests/` is deliberately NOT here — it is counted separately below.
PRODUCTION_DIRS = ("lib", "app", "worker", "components")
TEST_DIRS = ("tests",)
SUFFIXES = (".ts", ".tsx")

LINE_COMMENT = re.compile(r"//.*$", re.MULTILINE)
BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.DOTALL)


def strip_comments(src: str) -> str:
    """Blank out comments, PRESERVING line count so reported line numbers stay true.

    ⚠ STRINGS ARE NOT STRIPPED, and that is deliberate: the call this guard hunts for is
    `supabase.rpc('record_artifact', …)` — the symbol lives INSIDE a string literal. Stripping
    string contents the way `run-schema-assertions.sh` does would make this guard blind to the only
    thing it is looking for. Opposite problem, opposite treatment.
    """
    def blank(m: re.Match[str]) -> str:
        return re.sub(r"[^\n]", " ", m.group(0))
    return LINE_COMMENT.sub(blank, BLOCK_COMMENT.sub(blank, src))


def scan(dirs: tuple[str, ...], root: Path) -> tuple[list[str], list[str]]:
    """(code hits, comment-only hits) as 'path:line: text'. PURE apart from reading files."""
    code, commented = [], []
    for d in dirs:
        base = root / d
        if not base.is_dir():
            continue
        for f in sorted(base.rglob("*")):
            if f.suffix not in SUFFIXES or not f.is_file():
                continue
            try:
                src = f.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            if SYMBOL not in src:
                continue
            stripped = strip_comments(src)
            for n, (raw, bare) in enumerate(zip(src.splitlines(), stripped.splitlines()), 1):
                if SYMBOL not in raw:
                    continue
                rel = f.relative_to(root)
                entry = f"{rel}:{n}: {raw.strip()[:120]}"
                (code if SYMBOL in bare else commented).append(entry)
    return code, commented


def definition_present(sources: tuple[Path, ...]) -> bool:
    """True when at least one shipped source still DEFINES the symbol."""
    return any(p.is_file() and DEFINES.search(p.read_text(encoding="utf-8")) for p in sources)


def report(root: Path, sources: tuple[Path, ...]) -> int:
    if not definition_present(sources):
        print(f"CANNOT RUN — no shipped source still defines `{SYMBOL}`.")
        print("  Either it was renamed, or the schema moved. Until this is reconciled, a search for")
        print("  callers proves nothing: it would report DORMANT for a symbol that no longer exists,")
        print("  which is the one answer that lets backlog 26's money defect ship. TREAT AS NOT RUN.")
        for p in sources:
            print(f"    looked in: {p.relative_to(root) if p.is_relative_to(root) else p}")
        return 2

    code, commented = scan(PRODUCTION_DIRS, root)
    test_code, test_commented = scan(TEST_DIRS, root)

    print(f"subject: `{SYMBOL}` · production dirs {'/'.join(PRODUCTION_DIRS)} · suffixes {' '.join(SUFFIXES)}")
    print(f"         production callers: {len(code)}   (comments, not callers: {len(commented)})")
    print(f"         tests: {len(test_code)} caller(s), {len(test_commented)} comment(s) — not a trigger")
    for e in commented + test_commented + test_code:
        print(f"           · {e}")

    if code:
        print()
        print(f"⛔ BACKLOG 26 HAS FIRED — {len(code)} production caller(s) reach `{SYMBOL}`:")
        for e in code:
            print(f"     {e}")
        print("  ADR-0007 deleted the only per-kind attempt bound on the money path. Until backlog 26")
        print("  decides which ceiling governs a paid slot, a summary that cost 1 paid attempt can now")
        print("  cost 5 (`jobs.max_attempts` defaults to 5, 0008_jobs_queue.sql:14). CLOSE 26 FIRST.")
        return 1

    print()
    print("DORMANT — no production caller. Backlog 26 may remain open; it costs nothing today.")
    return 0


def self_test() -> int:
    import tempfile
    cases = bad = 0

    def ck(name: str, want: int, got: int) -> None:
        nonlocal cases, bad
        cases += 1
        if want == got:
            print(f"  ✓ {name}")
        else:
            print(f"  ✗ {name} — wanted exit {want}, got {got}")
            bad += 1

    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        sql = t / "schema.sql"
        sql.write_text(f"create function {SYMBOL}(p uuid) returns text as $$ $$;\n")
        srcs = (sql,)
        for d in PRODUCTION_DIRS + TEST_DIRS:
            (t / d).mkdir(parents=True, exist_ok=True)

        lib = t / "lib" / "x.ts"

        lib.write_text("export const a = 1;\n")
        ck("a clean tree is DORMANT", 0, report(t, srcs))

        lib.write_text(f"await supabase.rpc('{SYMBOL}', {{ p: 1 }});\n")
        ck("a real rpc call FIRES", 1, report(t, srcs))

        lib.write_text(f'await supabase.rpc("{SYMBOL}");\n')
        ck("…double quotes too", 1, report(t, srcs))

        lib.write_text(f"// one day this will call {SYMBOL}\nexport const a = 1;\n")
        ck("a LINE comment is not a caller", 0, report(t, srcs))

        lib.write_text(f"/* history:\n * {SYMBOL} used to take a token\n */\nexport const a = 1;\n")
        ck("a BLOCK comment is not a caller", 0, report(t, srcs))

        # ⭐ The case the real repo is in today: the only mentions are comments, in tests.
        lib.write_text("export const a = 1;\n")
        (t / "tests" / "c.test.ts").write_text(f"// `{SYMBOL}` completes a generation\n")
        ck("comments in tests/ — today's actual state — is DORMANT", 0, report(t, srcs))

        # …and a genuine call from tests/ is still not the trigger: tests are not an environment.
        (t / "tests" / "c.test.ts").write_text(f"await supabase.rpc('{SYMBOL}');\n")
        ck("a real call from tests/ is NOT the trigger", 0, report(t, srcs))

        # ⭐⭐ THE ANTI-ROT CASE. Rename the symbol out of the schema and the guard must go loud,
        # not quiet — a silent DORMANT here is the failure that ships the money defect.
        (t / "tests" / "c.test.ts").write_text("export const a = 1;\n")
        sql.write_text("create function something_else(p uuid) returns text as $$ $$;\n")
        ck("the symbol GONE from the schema is CANNOT RUN, not dormant", 2, report(t, srcs))

        sql.unlink()
        ck("a missing schema source is CANNOT RUN", 2, report(t, srcs))

    print()
    print(f"{cases - bad} of {cases} self-test cases passed")
    return bad


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    sys.exit(report(ROOT, DEFINITION_SOURCES))
