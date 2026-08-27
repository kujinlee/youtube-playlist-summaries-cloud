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

import json
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
DEFINES = re.compile(
    rf"create\s+(or\s+replace\s+)?(function|routine)\s+(public\.)?{SYMBOL}\b", re.IGNORECASE)
# ⟳ r11 H3 — THE DOCSTRING NAMED A RENAME AND THE PATTERN COULD NOT SEE ONE.
# `alter function … rename to` is the canonical rename and matched neither pattern, so a ledger
# renaming the symbol reported exists=True and the guard went on to answer DORMANT. `drop routine`
# is an equally standard spelling and missed too. MEASURED against a two-file fixture ledger before
# and after. The live catalog covers both when Docker answers — but the ledger is the authority in
# CI, which is exactly where an unnoticed rename would sit longest.
DROPS = re.compile(
    rf"(drop\s+(function|routine)\s+(if\s+exists\s+)?(public\.)?{SYMBOL}\b"
    rf"|alter\s+(function|routine)\s+(public\.)?{SYMBOL}\b[^;]*\brename\s+to\b)", re.IGNORECASE)

# Production surface. `tests/` is deliberately NOT here — it is counted separately below.
# ⟳ r10 M1: `scripts/` ADDED. It holds operational TypeScript that runs against PRODUCTION data —
# `cloud-sync.ts`, `rerender-html.ts`, `repair-timestamps.ts`, `backfill-serial-prefix.ts`,
# `fix-duplicate-summaries.ts`. A backfill populating the manifest for existing videos is the most
# plausible FIRST caller of `record_artifact` and would be written before any `lib/` path exists —
# and the directory was invisible to this guard: not a caller, not a comment, not printed.
PRODUCTION_DIRS = ("lib", "app", "worker", "components", "scripts")
TEST_DIRS = ("tests",)
SUFFIXES = (".ts", ".tsx")

SPANS_TOOL = ROOT / "scripts/ts-comment-spans.mjs"


class CannotRun(RuntimeError):
    """No degraded answer is available. The caller must exit 2."""


def comment_spans(files: list[Path]) -> dict[str, list[tuple[int, int]]]:
    """{path: [(start, end), …]} for every COMMENT, answered by the TypeScript compiler.

    ⭐⭐ r11 H1 — THIS REPLACES THE FOURTH HAND-WRITTEN ANSWER TO "is this inside a comment?".

        r10 H4  two regexes -> a `//` INSIDE A STRING hid a real `.rpc('record_artifact', …)` call
        r11 H1  a scanner   -> a REGEX LITERAL containing a quote opened a phantom string and
                               inverted inside/outside from there. MEASURED on the real tree: 14
                               files ended the scan inside a string; 240 real comment lines across
                               12 production files were being read as CODE. Both directions
                               reproduced — a comment reported as a money caller, and a live
                               `.rpc('record_artifact')` reported DORMANT.

    Each fix asked what the last counter-example had that ordinary code does not — a question about
    characters, with an unbounded supply of answers. `run-schema-assertions.sh` records the same
    sequence costing four rounds here. The way out is to stop proxying: `scripts/ts-comment-spans.mjs`
    asks the TypeScript compiler, which already ships in this repo and already has to know about
    regex literals, JSX, template interpolation, escapes and CRLF.

    ⛔ NO FALLBACK, DELIBERATELY. If node or typescript is missing this raises and the caller exits
    2. A hand-rolled degraded answer is exactly what the two rounds above were, and DORMANT is the
    one verdict that lets backlog 26's money defect ship.
    """
    if not files:
        return {}
    if not SPANS_TOOL.is_file():
        raise CannotRun(f"{SPANS_TOOL} is missing.")
    p = subprocess.run(["node", str(SPANS_TOOL), *[str(f) for f in files]],
                       capture_output=True, text=True, stdin=subprocess.DEVNULL)
    if p.returncode != 0:
        raise CannotRun(f"node could not compute comment spans: {(p.stderr or p.stdout)[-400:]}")
    try:
        raw = json.loads(p.stdout)
    except json.JSONDecodeError as e:
        raise CannotRun(f"comment-span output was not JSON: {e}") from e
    return {k: [(a, b) for a, b in v] for k, v in raw.items()}


def scan(dirs: tuple[str, ...], root: Path) -> tuple[list[str], list[str]]:
    """(code hits, comment-only hits) as 'path:line: text'."""
    candidates: list[Path] = []
    for d in dirs:
        base = root / d
        if not base.is_dir():
            continue
        for f in sorted(base.rglob("*")):
            if f.suffix in SUFFIXES and f.is_file():
                try:
                    if SYMBOL in f.read_text(encoding="utf-8"):
                        candidates.append(f)
                except (UnicodeDecodeError, OSError):
                    continue
    spans = comment_spans(candidates)
    code, commented = [], []
    for f in candidates:
        text = f.read_text(encoding="utf-8")
        fspans = spans.get(str(f), [])

        # ⛔⛔ OFFSETS ARE IN UTF-16 CODE UNITS, BECAUSE THAT IS WHAT TYPESCRIPT COUNTS.
        # Python counts CODE POINTS. A non-BMP character — `🖼` in
        # `lib/dig/cloud/parse-dig-section-blob.ts`, `→`-class emoji elsewhere — is ONE code point
        # and TWO UTF-16 units, so every offset after it drifts and a hit lands in the wrong span.
        # MEASURED while verifying this very fix: a genuine `//` comment two lines below an emoji
        # was being classified as CODE. Silent, direction-dependent, and on the money path.
        u16 = lambda t: len(t.encode("utf-16-le")) // 2  # noqa: E731 — one expression, used twice
        starts, off = [], 0
        for line in text.splitlines(keepends=True):
            starts.append(off)
            off += u16(line)
        lines = text.splitlines()
        for i, line in enumerate(lines):
            # ⟳ r12 BLOCKING (codex, reproduced by the coordinator). This was `line.find(SYMBOL)` —
            # the FIRST occurrence on the line decided the whole line. MEASURED on
            # `/* record_artifact historical note */ await sb.rpc('record_artifact');`:
            # `production callers: 0`, verdict DORMANT, rc 0 — over a real paid caller.
            #
            # A comment on the same line as a call is not exotic; it is the normal shape of
            # `await sb.rpc('record_artifact');  // charges 25c`. One occurrence must never speak
            # for another, so EVERY occurrence is classified on its own offset.
            #
            # A line can now appear in BOTH lists, and that is correct rather than a bug: it really
            # does contain a mention and a call. `report()` decides on `code` being non-empty, so a
            # commented twin can no longer mask a caller — the failure this guard exists to prevent.
            col = line.find(SYMBOL)
            while col >= 0:
                at = starts[i] + u16(line[:col])
                inside = any(a <= at < b for a, b in fspans)
                entry = f"{f.relative_to(root)}:{i + 1}: {line.strip()[:120]}"
                bucket = commented if inside else code
                if entry not in bucket:
                    bucket.append(entry)
                col = line.find(SYMBOL, col + len(SYMBOL))
    return code, commented


def strip_sql_noise(sql: str) -> str:
    """SQL with comments blanked, preserving length so offsets stay comparable. PURE.

    ⟳ r12 HIGH (codex, reproduced by the coordinator). `ledger_net_effect` ran its create/drop
    regexes over RAW text, so PROSE decided whether a production function exists. MEASURED: a file
    containing `drop function record_artifact(uuid);` followed by
    `-- TODO: create function record_artifact again if backlog 26 changes` reported
    `(True, '0028_drop.sql (creates it)')` — the ledger resurrected a dropped money function from a
    comment, and the guard then reported DORMANT for a symbol that no longer exists.

    Blanking rather than deleting keeps every offset identical, so `max(m.start())` still means what
    it meant — the fix must not perturb the ordering logic it is protecting.

    ⚠ It must know STRINGS too, not just comments. r11 H1 was a comment scanner that desynchronised
    on quoting, and the lesson there was that half a lexer is worse than none: `'-- not a comment'`
    is data, and Postgres bodies are routinely dollar-quoted (`$$ ... $$`, `$tag$ ... $tag$`) with
    `--` inside them. Block comments NEST in Postgres, so depth is counted rather than flagged.
    """
    out = list(sql)
    i, n = 0, len(sql)

    def blank(a: int, b: int) -> None:
        """Blank [a, b) but keep newlines, so line numbers and offsets both survive."""
        for k in range(a, min(b, n)):
            if out[k] != "\n":
                out[k] = " "

    while i < n:
        c = sql[i]
        if c == "'":                                    # single-quoted literal; '' escapes
            start = i
            i += 1
            while i < n:
                if sql[i] == "'":
                    if i + 1 < n and sql[i + 1] == "'":
                        i += 2
                        continue
                    i += 1
                    break
                i += 1
            # ⚠ CONTENTS BLANKED, not merely skipped. Found by this fix's own test: leaving them
            # intact meant `select '-- create function record_artifact';` still counted as a CREATE.
            # A symbol name inside a string is DATA. That hole predates r12 — raw text was always
            # scanned — so the comment fix alone would have been correct about the case it named and
            # silent about the identical one beside it.
            blank(start, i)
            continue
        if c == "$":                                    # dollar-quoted body: $$ or $tag$
            m = re.match(r"\$[A-Za-z_][A-Za-z0-9_]*\$|\$\$", sql[i:])
            if m:
                tag = m.group(0)
                end = sql.find(tag, i + len(tag))
                stop = n if end < 0 else end + len(tag)
                # Function BODIES live here. `create function` inside a body string is not a
                # top-level definition of that function, and `raise notice '…'` text is not SQL.
                blank(i, stop)
                i = stop
                continue
        if c == "-" and sql.startswith("--", i):        # line comment
            j = sql.find("\n", i)
            j = n if j < 0 else j
            for k in range(i, j):
                out[k] = " "
            i = j
            continue
        if c == "/" and sql.startswith("/*", i):        # block comment, NESTING
            depth, j = 1, i + 2
            while j < n and depth:
                if sql.startswith("/*", j):
                    depth += 1
                    j += 2
                elif sql.startswith("*/", j):
                    depth -= 1
                    j += 2
                else:
                    j += 1
            for k in range(i, min(j, n)):
                if out[k] != "\n":
                    out[k] = " "
            i = j
            continue
        i += 1
    return "".join(out)


def ledger_net_effect(migrations_dir: Path) -> tuple[bool, str]:
    """(symbol exists, how we know) from the migration ledger, read IN ORDER. PURE.

    The last file that mentions the symbol wins, and within a file a drop after a create wins. That
    is what an append-only ledger means: you cannot edit `0027`, you can only file `0028`.
    """
    if not migrations_dir.is_dir():
        return False, f"{migrations_dir} does not exist"
    exists, decided_by = False, "no migration mentions the symbol"
    for f in sorted(migrations_dir.glob("*.sql")):
        text = strip_sql_noise(f.read_text(encoding="utf-8"))
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
    # ⟳ r11 M4: an unguarded subprocess raised FileNotFoundError with no `docker` on PATH, and the
    # process exited 1 — which this script documents as FIRED, "a production caller exists". A
    # missing binary is not a money finding.
    try:
        p = subprocess.run(
            ["docker", "exec", "-i", CONTAINER, "psql", "-U", "postgres", "-d", "postgres", "-tAq",
             "-c", f"select count(*) from pg_proc p join pg_namespace n on n.oid = p.pronamespace "
                   f"where n.nspname = 'public' and p.proname = '{symbol}';"],
            capture_output=True, text=True, stdin=subprocess.DEVNULL)
    except (FileNotFoundError, OSError):
        return None
    if p.returncode != 0:
        return None
    out = p.stdout.strip()
    return out.isdigit() and int(out) > 0


def report(root: Path, migrations_dir: Path, use_live: bool = True) -> int:
    live = live_catalog_has(SYMBOL) if use_live else None
    ledger, decided_by = ledger_net_effect(migrations_dir)
    # ⟳⟳ r11 M4 — THE LIVE ANSWER USED TO WIN UNCONDITIONALLY, AND THAT MADE THIS GUARD A PERMANENT
    # CANNOT RUN ON EVERY MACHINE WHERE 0027 IS NOT YET APPLIED — i.e. every developer before
    # promotion, and production today. Same repo, same commit, two verdicts decided by whether a
    # container happened to be running.
    #
    # The two authorities answer different questions. The ledger says what the schema WILL be; the
    # catalog says what THIS database has. `live=False, ledger=True` is the ordinary
    # pending-migration state, not rot — the symbol exists and callers are what matter. CANNOT RUN
    # is reserved for BOTH agreeing it is gone, which is the actual rot this check exists for.
    exists = ledger or bool(live)
    if live is None:
        authority = f"migration ledger — {decided_by}"
    elif live == ledger:
        authority = f"live catalog and ledger agree — {decided_by}"
    else:
        authority = f"ledger ({decided_by}); live catalog disagrees"
        print(f"⚠ ledger and live catalog DISAGREE about `{SYMBOL}` "
              f"(ledger: {ledger} via {decided_by}; live: {live}).")
        print("  That is the ordinary pending-migration state when the ledger says PRESENT. The"
              " ledger decides, because it is what a caller would be written against.")

    if not exists:
        print(f"CANNOT RUN — `{SYMBOL}` does not exist according to the {authority}.")
        print("  Either it was renamed or dropped. Until that is reconciled, a search for callers")
        print("  proves nothing: it would report DORMANT for a symbol that no longer exists, which")
        print("  is the one answer that lets backlog 26's money defect ship. TREAT AS NOT RUN.")
        return 2

    try:
        code, commented = scan(PRODUCTION_DIRS, root)
        test_code, test_commented = scan(TEST_DIRS, root)
    except CannotRun as e:
        print(f"CANNOT RUN — {e}")
        print("  Comment detection is answered by the TypeScript compiler and has NO fallback: the")
        print("  two hand-written versions before it each shipped a false verdict on the money path")
        print("  (r10 H4, r11 H1). TREAT THIS AS NOT RUN.")
        return 2

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

        # ⭐⭐ r12 BLOCKING — A REAL COMMENT SHARING A LINE WITH A REAL CALL.
        # r10 H4 (above) proved a comment-like thing inside a STRING must not hide the call. This is
        # its mirror and it survived that fix: a GENUINE comment, correctly identified, whose only
        # crime was coming FIRST. `line.find(SYMBOL)` classified the line by its first occurrence,
        # so the call after `*/` was recorded as "a comment, not a caller" — `production callers: 0`,
        # DORMANT, rc 0, over a paid caller.
        #
        # Note what this says about the r11 fix that preceded it: replacing the regex scanner with a
        # real TypeScript parse made comment DETECTION exact and left comment ATTRIBUTION per-line.
        # An exact answer to the wrong question. Both directions are now covered.
        lib.write_text(f"/* {SYMBOL} historical note */ await sb.rpc('{SYMBOL}');\n")
        ck("a real comment BEFORE a real call on one line does not hide it (r12 B1)", 1, run())

        lib.write_text(f"await sb.rpc('{SYMBOL}'); // {SYMBOL} charges 25c\n")
        ck("…and the same line with the comment AFTER the call still fires", 1, run())

        lib.write_text(f"/* {SYMBOL} then {SYMBOL} twice, both commented */\nexport const a = 1;\n")
        ck("…while two mentions in ONE comment are still not callers", 0, run())

        # A comment AFTER real code on the same line is still a comment.
        lib.write_text(f"const a = 1; // someday: {SYMBOL}\n")
        ck("a trailing comment mentioning the symbol is not a caller", 0, run())

        # ⭐ r10 M1 — scripts/ is production surface and used to be invisible entirely.
        lib.write_text("export const a = 1;\n")
        (t / "scripts" / "backfill.ts").write_text(f"await sb.rpc('{SYMBOL}');\n")
        ck("a caller in scripts/ FIRES (r10 M1)", 1, run())
        (t / "scripts" / "backfill.ts").unlink()

        # ⭐⭐ r11 H1 — THE TWO DIRECTIONS THE HAND-WRITTEN SCANNER GOT WRONG, both measured on
        # the real tree. The construct in the first is live at lib/html-doc/file-response.ts:8.
        lib.write_text(
            "export const clean = (s: string) => s.replace(/[\"\\\\/;]/g, '_');\n"
            f"// TODO: once {SYMBOL} lands, encode the manifest key here\n")
        ck("a regex literal with a quote does not turn a COMMENT into a caller (r11 H1)", 0, run())

        lib.write_text(
            "const label = 'Don\\'t';\n"
            "const GLOB = 'src/*';\n"
            f"await sb.rpc('{SYMBOL}');\n")
        ck("…nor does it hide a REAL call behind a phantom string (r11 H1)", 1, run())

        lib.write_text(f"const s = `${{/* {SYMBOL} */ v}}`;\n")
        ck("a comment inside template interpolation is a COMMENT, not a caller", 0, run())

        lib.write_text(f"const s = `${{sb.rpc('{SYMBOL}')}}`;\n")
        ck("…but a CALL inside template interpolation FIRES", 1, run())

        # ⭐ r11 H3 — the rename spellings the ledger could not see.
        lib.write_text("export const a = 1;\n")
        (migs / "0028_rename.sql").write_text(
            f"alter function public.{SYMBOL}(uuid, text) rename to {SYMBOL}_v2;\n")
        ck("ALTER FUNCTION … RENAME TO is CANNOT RUN (r11 H3)", 2, run())
        (migs / "0028_rename.sql").write_text(f"drop routine if exists public.{SYMBOL}(uuid);\n")
        ck("DROP ROUTINE is CANNOT RUN (r11 H3)", 2, run())
        (migs / "0028_rename.sql").unlink()

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
        (migs / "0029_restore.sql").unlink()

        # ⭐⭐ r12 HIGH — PROSE MUST NOT BE A SCHEMA OPERATION.
        # `0028` really drops the function; the COMMENT below it merely talks about recreating it.
        # The ledger regexes ran over raw text, so the comment won by position and reported
        # `(True, '0028 creates it)'` — a dropped money function resurrected by a TODO, and the
        # guard then answering DORMANT for a symbol that does not exist.
        (migs / "0028_rename.sql").write_text(
            f"drop function {SYMBOL}(uuid);\n"
            f"-- TODO: create function {SYMBOL} again if backlog 26 changes\n")
        ck("a comment cannot resurrect a dropped symbol (r12 H1)", 2, run())

        # Found by the r12 fix's OWN test, and it predates r12: the same hole with a string literal.
        # Fixing only the case the finding named would have been correct about `--` and silent about
        # the identical defect one quote away.
        (migs / "0028_rename.sql").write_text(
            f"drop function {SYMBOL}(uuid);\n"
            f"select 'create function {SYMBOL} -- someday';\n")
        ck("…nor can a STRING literal", 2, run())

        (migs / "0028_rename.sql").write_text(
            f"drop function {SYMBOL}(uuid);\n"
            f"do $$ begin raise notice 'create function {SYMBOL}'; end $$;\n")
        ck("…nor a dollar-quoted body", 2, run())

        (migs / "0028_rename.sql").write_text(
            f"drop function {SYMBOL}(uuid);\n"
            f"/* outer /* nested */ create function {SYMBOL}() */\n")
        ck("…nor a NESTED block comment (Postgres nests them)", 2, run())

        # The mirror: the stripper must not eat a REAL definition. Without this, blanking everything
        # would pass all four cases above and the guard would be vacuous.
        (migs / "0029_restore.sql").write_text(
            f"create function {SYMBOL}(p uuid) returns text as $$ $$;\n")
        ck("…and a REAL create after the drop still restores it", 0, run())
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
