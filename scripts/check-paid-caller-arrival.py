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
`lib/ app/ worker/ components/ scripts/` names `record_artifact` outside a comment.

⛔⛔ THE FAILURE MODE THIS GUARD HAS TO SURVIVE IS ITS OWN VOCABULARY GOING STALE.
A grep for a symbol reports "no callers" just as happily when the symbol has been RENAMED as when it
genuinely has none — and it would then read DORMANT forever, which is the one answer that lets the
money defect ship. `hardcode-only-what-fails-loudly`: hardcode what announces its own wrongness.
So before looking for callers, this asserts the symbol still EXISTS — from the LIVE CATALOG when a
database is reachable, otherwise from the migration ledger's NET EFFECT read in order. If it does
not, that is a CANNOT RUN with the reason named — never a pass.
⟳ r10 H3: this used to read the symbol out of `0027` alone. Migrations are append-only and never
edited, so that check was true forever and its stated falsifier could not fire. See the note by
DEFINES below — the fix is about WHICH SUBJECT ANSWERS, not about the check being absent.

⚠ COMMENTS ARE NOT CALLERS, AND ARE REPORTED RATHER THAN DROPPED. Today's only matches are two
comment lines in `tests/lib/blob-addressing-caller-contract.test.ts` describing the schema's history.
A guard that fired on those would be red while nothing is wrong, and a guard that is red when
nothing is wrong gets disabled. But silently discarding them would hide the day one of them becomes
a call, so both counts are printed every run.

⚠ Backlog 26's own prose says the grep "returns one comment". MEASURED 2026-08-26: it is TWO lines,
in that same file. The number in the row is a second representation of what this script computes;
the script is the one that cannot drift.

⛔ COMMENT DETECTION IS A SCANNER, NOT A REGEX — see `strip_comments`. The regex version filed a
real `.rpc('record_artifact', …)` call as a comment because a `https://` appeared earlier on the
same line (r10 H4, measured). Every self-test fixture before r10 put its `//` at column 0, which is
why 9 green cases certified it.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTAINER = os.environ.get("PGCONTAINER", "supabase_db_youtube-playlist-summaries-cloud")

# The symbol whose first production caller is the event. Named once.
SYMBOL = "record_artifact"

# ⟳⟳ r10 H3 — THE ANTI-ROT CHECK USED TO HAVE A SUBJECT THAT CAN NEVER CHANGE.
#
# It asked whether `0027_stable_blob_addressing.sql` still contains `create function record_artifact`.
# `supabase/migrations/` is an APPEND-ONLY LEDGER — `rollback_0027…sql` is a whole essay on why a
# correction must not be filed as a later migration precisely because applied files are never edited.
# So that check was true FOREVER, whatever the database does: a future `0028` renaming or dropping
# the function leaves it green and the script reports DORMANT for a symbol that no longer exists.
# The stated falsifier was unreachable by construction. It also used `any()` over two sources, so a
# stale spec file masked a rename in the migration and vice versa.
#
# The subject is now the LEDGER'S NET EFFECT, read in order — the last statement that mentions the
# symbol decides — with the LIVE CATALOG preferred when a database is reachable, because that is the
# only authority that cannot be stale. The spec file is no longer an authority at all.
MIGRATIONS_DIR = ROOT / "supabase/migrations"
DEFINES = re.compile(rf"create\s+(or\s+replace\s+)?function\s+(public\.)?{SYMBOL}\b", re.IGNORECASE)
DROPS = re.compile(rf"drop\s+function\s+(if\s+exists\s+)?(public\.)?{SYMBOL}\b", re.IGNORECASE)

# Production surface. `tests/` is deliberately NOT here — it is counted separately below.
# ⟳ r10 M1: `scripts/` ADDED. It holds operational TypeScript that runs against PRODUCTION data —
# `cloud-sync.ts`, `rerender-html.ts`, `repair-timestamps.ts`, `backfill-serial-prefix.ts`,
# `fix-duplicate-summaries.ts`. A backfill populating the manifest for existing videos is the most
# plausible FIRST caller of `record_artifact` and would be written before any `lib/` path exists —
# and the directory was invisible to this guard: not a caller, not a comment, not printed.
PRODUCTION_DIRS = ("lib", "app", "worker", "components", "scripts")
TEST_DIRS = ("tests",)
SUFFIXES = (".ts", ".tsx")

def strip_comments(src: str) -> str:
    """Blank out comments, PRESERVING line count so reported line numbers stay true.

    ⚠ STRINGS ARE NOT STRIPPED, and that is deliberate: the call this guard hunts for is
    `supabase.rpc('record_artifact', …)` — the symbol lives INSIDE a string literal. Stripping
    string contents the way `run-schema-assertions.sh` does would make this guard blind to the only
    thing it is looking for. Opposite problem, opposite treatment.

    ⟳⟳ r10 H4 — AND THE FIRST DRAFT'S REGEXES DID NOT KNOW THAT, WHICH LOST A REAL MONEY CALL.
    It used `re.compile(r"//.*$", re.MULTILINE)` and blanked from the FIRST `//` on the line —
    including one inside a string. MEASURED, verbatim, one line:

        const base = 'https://example.com/api'; const o = await sb.rpc('record_artifact', {…});
        -> production callers: 0   (comments, not callers: 1)   DORMANT   exit 0

    A live production caller of the money path, filed as a comment. `https://` does it, so does any
    protocol-relative path, and a `/*` inside a string opens a DOTALL block comment that swallows
    everything after it. That is precisely the outcome this file's own header calls "the one answer
    that lets backlog 26's money defect ship".

    So this is a scanner, not a regex: it walks the source tracking whether it is inside a single,
    double or template string (honouring backslash escapes) and only treats `//` and `/*` as comment
    openers OUTSIDE one. A regex cannot express that, and the previous one silently pretended to.
    """
    out = list(src)
    i, n = 0, len(src)
    quote: str | None = None
    while i < n:
        c = src[i]
        if quote:
            if c == "\\":
                i += 2
                continue
            if c == quote:
                quote = None
            i += 1
            continue
        if c in "'\"`":
            quote = c
            i += 1
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "/":
            while i < n and src[i] != "\n":
                out[i] = " "
                i += 1
            continue
        if c == "/" and i + 1 < n and src[i + 1] == "*":
            j = src.find("*/", i + 2)
            j = n if j < 0 else j + 2
            for k in range(i, j):
                if out[k] != "\n":
                    out[k] = " "
            i = j
            continue
        i += 1
    return "".join(out)


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


def ledger_net_effect(migrations_dir: Path) -> tuple[bool, str]:
    """(symbol exists, how we know) from the migration ledger, read IN ORDER. PURE.

    The last file that mentions the symbol wins, and within a file a drop after a create wins. That
    is what an append-only ledger means: you cannot edit `0027`, you can only file `0028`.
    """
    if not migrations_dir.is_dir():
        return False, f"{migrations_dir} does not exist"
    exists, decided_by = False, "no migration mentions the symbol"
    for f in sorted(migrations_dir.glob("*.sql")):
        text = f.read_text(encoding="utf-8")
        last_create = max((m.start() for m in DEFINES.finditer(text)), default=-1)
        last_drop = max((m.start() for m in DROPS.finditer(text)), default=-1)
        if last_create < 0 and last_drop < 0:
            continue
        exists = last_create > last_drop
        decided_by = f"{f.name} ({'creates' if exists else 'drops'} it)"
    return exists, decided_by


def live_catalog_has(symbol: str) -> bool | None:
    """True/False from the live catalog, or None when no database is reachable.

    Preferred over the ledger because it is the only authority that cannot be stale — but optional,
    because this guard must remain runnable in CI and on a laptop with no stack up. `None` is a
    third outcome and is NOT folded into False: "cannot see" and "is absent" are different claims,
    which is the distinction this repo files under `rls-denial-is-indistinguishable-from-absence`.
    """
    p = subprocess.run(
        ["docker", "exec", "-i", CONTAINER, "psql", "-U", "postgres", "-d", "postgres", "-tAq",
         "-c", f"select count(*) from pg_proc p join pg_namespace n on n.oid = p.pronamespace "
               f"where n.nspname = 'public' and p.proname = '{symbol}';"],
        capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if p.returncode != 0:
        return None
    out = p.stdout.strip()
    return out.isdigit() and int(out) > 0


def report(root: Path, migrations_dir: Path, use_live: bool = True) -> int:
    live = live_catalog_has(SYMBOL) if use_live else None
    ledger, decided_by = ledger_net_effect(migrations_dir)
    authority = "live catalog" if live is not None else f"migration ledger — {decided_by}"
    exists = ledger if live is None else live

    if live is not None and live != ledger:
        # Not fatal, and worth saying: the ledger and the database disagree, which usually means
        # migrations are pending or the local stack drifted. The LIVE answer wins — it is the one
        # that decides whether a caller would actually reach anything.
        print(f"⚠ ledger and live catalog DISAGREE about `{SYMBOL}` "
              f"(ledger: {ledger} via {decided_by}; live: {live}). Trusting the live catalog.")

    if not exists:
        print(f"CANNOT RUN — `{SYMBOL}` does not exist according to the {authority}.")
        print("  Either it was renamed or dropped. Until that is reconciled, a search for callers")
        print("  proves nothing: it would report DORMANT for a symbol that no longer exists, which")
        print("  is the one answer that lets backlog 26's money defect ship. TREAT AS NOT RUN.")
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
            print(f"  \u2713 {name}")
        else:
            print(f"  \u2717 {name} — wanted exit {want}, got {got}")
            bad += 1

    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        migs = t / "supabase" / "migrations"
        migs.mkdir(parents=True)
        (migs / "0027_x.sql").write_text(
            f"create function {SYMBOL}(p uuid) returns text as $$ $$;\n")
        for d in PRODUCTION_DIRS + TEST_DIRS:
            (t / d).mkdir(parents=True, exist_ok=True)

        # ⚠ use_live=False throughout: the self-test's subject is its own fixture tree, and letting
        # it consult the real local catalog would make every case depend on whether Docker is up.
        def run() -> int:
            return report(t, migs, use_live=False)

        lib = t / "lib" / "x.ts"
        lib.write_text("export const a = 1;\n")
        ck("a clean tree is DORMANT", 0, run())

        lib.write_text(f"await supabase.rpc('{SYMBOL}', {{ p: 1 }});\n")
        ck("a real rpc call FIRES", 1, run())

        lib.write_text(f'await supabase.rpc("{SYMBOL}");\n')
        ck("…double quotes too", 1, run())

        lib.write_text(f"// one day this will call {SYMBOL}\nexport const a = 1;\n")
        ck("a LINE comment is not a caller", 0, run())

        lib.write_text(f"/* history:\n * {SYMBOL} used to take a token\n */\nexport const a = 1;\n")
        ck("a BLOCK comment is not a caller", 0, run())

        # ⭐⭐ r10 H4 — THE CASE THAT SHIPPED A FALSE DORMANT OVER A REAL MONEY CALL.
        # Every pre-r10 fixture put its `//` at column 0, so none of them could see that the
        # regex blanked from the first `//` ANYWHERE on the line, including inside a string.
        lib.write_text(
            "const base = 'https://example.com/api';\n"
            f"const o = await sb.rpc('{SYMBOL}', {{ p_ws: ws }});\n")
        ck("a URL earlier on the line does NOT hide the call (r10 H4)", 1, run())

        lib.write_text(f"const u = 'a//b'; await sb.rpc('{SYMBOL}');\n")
        ck("…nor does a bare // inside a string", 1, run())

        lib.write_text(f"const g = '/* not a comment */'; await sb.rpc('{SYMBOL}');\n")
        ck("…nor does a /* inside a string (it opened a DOTALL swallow)", 1, run())

        lib.write_text(f"const t = `x//y`; await sb.rpc('{SYMBOL}');\n")
        ck("…nor does one in a TEMPLATE literal", 1, run())

        lib.write_text(f"const e = 'it\\'s // fine'; await sb.rpc('{SYMBOL}');\n")
        ck("…and an escaped quote does not desynchronise the scanner", 1, run())

        # A comment AFTER real code on the same line is still a comment.
        lib.write_text(f"const a = 1; // someday: {SYMBOL}\n")
        ck("a trailing comment mentioning the symbol is not a caller", 0, run())

        # ⭐ r10 M1 — scripts/ is production surface and used to be invisible entirely.
        lib.write_text("export const a = 1;\n")
        (t / "scripts" / "backfill.ts").write_text(f"await sb.rpc('{SYMBOL}');\n")
        ck("a caller in scripts/ FIRES (r10 M1)", 1, run())
        (t / "scripts" / "backfill.ts").unlink()

        # ⭐ Today's actual state: the only mentions are comments, in tests.
        (t / "tests" / "c.test.ts").write_text(f"// `{SYMBOL}` completes a generation\n")
        ck("comments in tests/ — today's actual state — is DORMANT", 0, run())

        (t / "tests" / "c.test.ts").write_text(f"await supabase.rpc('{SYMBOL}');\n")
        ck("a real call from tests/ is NOT the trigger", 0, run())
        (t / "tests" / "c.test.ts").write_text("export const a = 1;\n")

        # ⭐⭐ r10 H3 — THE ANTI-ROT CASES, AND THE OLD ONES COULD NOT FIRE.
        # The subject used to be `0027` alone, which is an append-only file nobody ever edits, so
        # the check was true forever. The subject is now the LEDGER'S NET EFFECT, in order.
        (migs / "0028_rename.sql").write_text(f"drop function {SYMBOL}(uuid);\n")
        ck("a LATER migration dropping the symbol is CANNOT RUN (r10 H3)", 2, run())

        (migs / "0029_restore.sql").write_text(
            f"create function {SYMBOL}(p uuid) returns text as $$ $$;\n")
        ck("…and a later one restoring it is DORMANT again", 0, run())
        (migs / "0028_rename.sql").unlink()
        (migs / "0029_restore.sql").unlink()

        (migs / "0027_x.sql").write_text("create function something_else(p uuid) returns text as $$ $$;\n")
        ck("the symbol absent from the whole ledger is CANNOT RUN", 2, run())

        (migs / "0027_x.sql").unlink()
        ck("an empty ledger is CANNOT RUN, not dormant", 2, run())

    print()
    print(f"{cases - bad} of {cases} self-test cases passed")
    return bad


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    sys.exit(report(ROOT, MIGRATIONS_DIR))
