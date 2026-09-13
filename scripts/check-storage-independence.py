#!/usr/bin/env python3
"""No schema gate reads the `storage` schema — the claim that keeps the CI fixture honest.

    python3 scripts/check-storage-independence.py            # 0 = independent, 1 = a gate reads storage
    python3 scripts/check-storage-independence.py --self-test

⭐ WHY. `scripts/ci/storage-service-fixture.sql` is a MINIMAL stand-in for tables the storage-api
service creates and CI does not run. It is safe ONLY while no gate reads `storage.*`: the moment one
does, the fixture stops being scaffolding and becomes a test double that can be green while
production is broken. That header says so, and a header is a sentence — this is its falsifier.

⛔⛔ THE FIRST VERSION WAS A `grep` INSIDE THE WORKFLOW, AND IT SURVIVED THREE OF FIVE MUTATIONS.
⟳ r1 HIGH (claude), measured against the delivered step:

    M1  STORAGE_SQL = "select id from storage.objects"            caught
    M2  nspname = 'public'  ->  nspname in ('public','storage')   SURVIVED  <- the realistic one
    M3  the same literal written with triple quotes on one line   SURVIVED
    M4  a NEW gate script reading storage.buckets                 SURVIVED
    M5  code with a trailing `# comment`                          caught

Each survivor is the same root cause: a line-oriented grep with hand-written exclusions was standing
in for two questions it cannot answer — *is this text CODE or a COMMENT* and *which files are the
gates*. So:

  * **Comments are removed by PARSING, not by pattern.** `ast` does not hand back comments at all, so
    `# … storage.objects …` cannot match and a triple-quoted string CAN. The old `'''`-exclusion had
    it exactly backwards: a docstring is a string, and a string is executable data.
  * **The file set is DERIVED, not listed.** Any `scripts/*.py` that imports `m4_catalog`/`m4_base_db`
    or is invoked by `check-schema-gates.sh` is in scope, so M4's brand-new gate is covered the
    moment it is written rather than when someone remembers to add it here.
  * **The NAMESPACE SCOPE is checked as well as the name.** Nobody adds storage by typing
    `storage.objects` into `m4_catalog.py`; they widen `nspname = 'public'`. That edit contains the
    word `storage` but not the string `storage.`, which is why the grep could never see it.

⛔⛔ THE FIRST VERSION'S STATED BOUND WAS ITSELF FALSE — ⟳ r1 HIGH (codex). It read: *"a non-Python
gate … is real and bounded — the shell gates reach Postgres through these same Python modules."*
Gate 1 plainly does not. `verify-schema.sh` CONCATENATES `05_assert.sql` (2,517 lines, 122 assertion
sites) and executes it against Postgres directly, and gate 2 does the same through `mutate-schema.py`
— both under `docs/superpowers/specs/…/`, which the population never reached. So a future assertion
could query `storage.objects`, pass against the minimal CI fixture, and this guard would still report
green: the exact direction the fixture is dangerous in.

The population now covers three kinds, and the comment rule differs per kind because the available
precision does:

    .py    `ast` — EXACT. Comments never enter the tree; strings do.
    .sql   `--` to end of line and `/* … */` stripped, then matched
    .sh    `#` to end of line stripped when it starts a line or follows whitespace

⚠ THE LAST TWO ARE APPROXIMATIONS AND THAT IS STATED RATHER THAN HIDDEN: a `#` inside a shell string
is treated as a comment, so a reference written as `psql -c "select … storage.objects"` on a line
that also contains a `#` could be missed. It errs toward MISSING a reference, never toward inventing
one — a false alarm here would train someone to switch the guard off.

⚠ WHAT REMAINS UNSEEABLE: SQL assembled at runtime from fragments (`"storage" + "." + tbl`).
"""
from __future__ import annotations

import argparse
import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SUITE = ROOT / "scripts" / "check-schema-gates.sh"
SCRIPTS = ROOT / "scripts"

# `storage.` with a word boundary in front, so `mystorage.x` does not match.
STORAGE_REF = re.compile(r"(?<![\w.])storage\s*\.\s*\w", re.I)
# Every namespace comparison in a SQL string, however spelled — and BOUNDED TO ITS OWN OPERAND.
# ⚠ The first version matched `nspname\s*(?:=|in)\s*([^\n]+)` and then pulled every quoted literal
# out of the rest of the line, so `where n.nspname = 'public' and c.relkind = 'r'` reported that the
# namespace scope "admits 'r'". Measured against the shipped catalog: 20 false positives across three
# files, and ZERO true ones. Caught by this file's own `the shipped scope is clean` case before the
# guard ran anywhere — which is the entire argument for writing the control case first.
NSPNAME_EQ = re.compile(r"nspname\s*=\s*'([^']*)'", re.I)
NSPNAME_IN = re.compile(r"nspname\s+in\s*\(([^)]*)\)", re.I)


def gate_files(root: pathlib.Path = ROOT) -> list[pathlib.Path]:
    """Every Python file that can reach Postgres for the suite. DERIVED, never listed.

    Two sources, unioned: what `check-schema-gates.sh` invokes, and what imports the two modules
    that own the connection. A new gate script is in scope the moment it imports one of them —
    which is the M4 hole the hand-written list had.
    """
    out: set[pathlib.Path] = set()
    suite = root / "scripts" / "check-schema-gates.sh"
    if suite.is_file():
        for m in re.findall(r"[\w./-]*scripts/[\w./-]+\.py", suite.read_text(encoding="utf-8")):
            p = root / m.lstrip("./")
            if p.is_file():
                out.add(p)
    for p in sorted((root / "scripts").glob("*.py")):
        try:
            src = p.read_text(encoding="utf-8")
        except OSError:
            continue
        if re.search(r"^\s*(?:from|import)\s+(?:m4_catalog|m4_base_db)\b", src, re.M):
            out.add(p)
    # ⟳ r1 HIGH (codex): the NON-PYTHON gates, and the SQL they execute. Gates 1 and 2 live under
    # `docs/superpowers/specs/…/` and were outside every branch above, so the guard's own stated
    # bound was false. Derived the same way as the rest — read out of the suite, not listed here.
    if suite.is_file():
        text = suite.read_text(encoding="utf-8")
        # ⚠ EXPAND THE SUITE'S OWN VARIABLES FIRST. Gates 1 and 2 are invoked as `"$SPEC/…"`, so a
        # literal-path regex finds neither — which is the SAME miss as the finding this fixes, one
        # level down: I looked for the shape I expected instead of the shape the file uses.
        for var, val in re.findall(r'^([A-Z_]+)="([^"$]+)"', text, re.M):
            text = text.replace(f'"${var}/', f'"{val}/').replace(f"${{{var}}}/", f"{val}/")
        for m in re.findall(r"[\w./-]+\.(?:sh|py|sql)", text):
            p = root / m.lstrip("./")
            # ⛔ A MIGRATION IS THE SUBJECT, NOT A GATE. `supabase/migrations/**` is excluded because
            # those files are what the gates READ THE CATALOG ABOUT — and `0007_storage_and_rpcs.sql`
            # uses `storage.buckets` on purpose. That use is the entire REASON the CI fixture exists,
            # so counting it as "a gate reads storage" inverts the rule: the guard fired on its own
            # premise. Measured when the population first widened: 3 hits, all in 0007, all correct
            # by the letter of the rule and all meaningless.
            # The population is things that read the catalog to reach a VERDICT, never things the
            # verdict is about.
            if str(p.relative_to(root)).startswith("supabase/"):
                continue
            if p.is_file() and p.suffix in (".sh", ".py", ".sql"):
                out.add(p)
                # a gate that executes SQL keeps it beside itself or in a `schema/` subdirectory;
                # those files ARE the gate's body as far as Postgres is concerned.
                for d in (p.parent, p.parent / "schema"):
                    if d.is_dir() and not str(d.relative_to(root)).startswith("supabase/"):
                        out.update(q for q in sorted(d.glob("*.sql")) if q.is_file())
    return sorted(out)


def storage_refs(src: str) -> list[str]:
    """Every `storage.<x>` occurring in CODE — string literals included, comments excluded. PURE.

    `ast` is the whole mechanism: comments never reach the tree, so no exclusion pattern is needed
    and none can be wrong. A file that does not parse is NOT silently clean — see `problems`.
    """
    tree = ast.parse(src)
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if STORAGE_REF.search(node.value):
                hits.append(f"line {node.lineno}: string contains a storage.* reference")
        elif isinstance(node, ast.Attribute) and node.attr and isinstance(node.value, ast.Name):
            if node.value.id == "storage":
                hits.append(f"line {node.lineno}: attribute access on a name `storage`")
    return hits


def text_refs(src: str, kind: str) -> list[str]:
    """Every `storage.<x>` in a NON-Python subject, comments removed by kind. PURE.

    ⟳ r1 HIGH (codex). `ast` is exact and only exists for Python; these two are approximations, and
    they err toward MISSING a reference rather than inventing one. A false alarm in a guard like this
    is worse than a miss: it trains the reader to switch the guard off, and then both directions are
    unguarded.
    """
    if kind == ".sql":
        body = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)          # block comments
        body = re.sub(r"--[^\n]*", " ", body)                       # line comments
    elif kind == ".sh":
        body = re.sub(r"(?m)(?:^|(?<=\s))#[^\n]*", " ", src)        # `#` at line start or after space
    else:
        body = src
    return [f"line {body[:m.start()].count(chr(10)) + 1}: {kind[1:]} reads storage.*"
            for m in STORAGE_REF.finditer(body)]


def namespace_scopes(sql: str) -> list[str]:
    """Every namespace comparison in a SQL string that admits anything other than `public`. PURE.

    This is M2, the realistic edit. `nspname in ('public','storage')` contains no `storage.` and is
    invisible to any search for the qualified name.
    """
    bad = []
    for m in NSPNAME_EQ.finditer(sql):
        if m.group(1) != "public":
            bad.append(f"namespace scope admits '{m.group(1)}': {m.group(0).strip()[:60]}")
    for m in NSPNAME_IN.finditer(sql):
        for n in re.findall(r"'([^']*)'", m.group(1)):
            if n != "public":
                bad.append(f"namespace scope admits '{n}': {m.group(0).strip()[:60]}")
    return bad


def problems(files: list[pathlib.Path], root: pathlib.Path = ROOT) -> list[str]:
    """One line per finding. An unreadable or unparseable gate is CANNOT RUN, never clean."""
    out: list[str] = []
    if not files:
        return ["CANNOT RUN — no gate files were derived. This check no longer reads its subject."]
    for p in files:
        rel = p.relative_to(root)
        try:
            src = p.read_text(encoding="utf-8")
        except OSError as e:
            out.append(f"CANNOT RUN — {rel}: unreadable ({e})")
            continue
        if p.suffix != ".py":
            # ⟳ r1 HIGH: gates 1 and 2 are a shell script and the SQL it executes. Sending those
            # through `ast` would report every one as CANNOT RUN — a guard drowning in refusals is
            # switched off just as fast as one that never fires.
            for hit in text_refs(src, p.suffix):
                out.append(f"{rel}: {hit}")
            for node_sql in (src,):
                for bad in namespace_scopes(node_sql):
                    out.append(f"{rel}: {bad}")
            continue
        try:
            for hit in storage_refs(src):
                out.append(f"{rel}: {hit}")
        except SyntaxError as e:
            out.append(f"CANNOT RUN — {rel}: does not parse ({e.msg} line {e.lineno})")
            continue
        for node in ast.walk(ast.parse(src)):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and "nspname" in node.value:
                for bad in namespace_scopes(node.value):
                    out.append(f"{rel}: line {node.lineno}: {bad}")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    if a.self_test:
        return self_test()

    files = gate_files()
    found = problems(files)
    cannot = [f for f in found if f.startswith("CANNOT RUN")]
    if cannot:
        print("\n".join(cannot), file=sys.stderr)
        print("TREAT THIS AS NOT RUN.", file=sys.stderr)
        return 2
    if found:
        print("❌ a schema gate now reads the `storage` schema:")
        for f in found:
            print(f"   {f}")
        print("\n   scripts/ci/storage-service-fixture.sql is a MINIMAL stand-in and has just become")
        print("   load-bearing — it can now be green while production is broken. Replace it with the")
        print("   real service schema. Do NOT extend the fixture to match.")
        return 1
    print(f"✅ no gate reads storage.* — the CI fixture stays scaffolding ({len(files)} gate files checked)")
    return 0


def self_test() -> int:
    passed = failed = 0

    def check(name, actual, expected):
        nonlocal passed, failed
        if actual == expected:
            passed += 1
        else:
            failed += 1
            print(f"  ✗ {name}\n      wanted {expected!r}\n      got    {actual!r}")

    # ── the five mutations from r1 HIGH, each by the case it names ──────────────────────────
    check("M1 a storage.* string literal is CAUGHT",
          bool(storage_refs('X = "select id from storage.objects"')), True)
    check("M3 the SAME literal in triple quotes is CAUGHT (the old grep excluded it)",
          bool(storage_refs('X = """select id from storage.objects"""')), True)
    check("M5 code with a trailing comment is CAUGHT",
          bool(storage_refs('X = "storage.objects"  # a trailing comment')), True)
    check("a COMMENT mentioning storage.objects is NOT a finding",
          storage_refs("# we never read storage.objects here\nX = 1"), [])
    check("a DOCSTRING is a string, so it IS checked — the old exclusion had this backwards",
          bool(storage_refs('"""we read storage.objects"""')), True)
    check("M2 widening the namespace scope is CAUGHT",
          bool(namespace_scopes("where n.nspname in ('public','storage')")), True)
    check("the shipped scope is clean",
          namespace_scopes("where n.nspname = 'public' and c.relkind = 'r'"), [])
    check("a scope naming only another schema is CAUGHT",
          bool(namespace_scopes("where nspname = 'auth'")), True)
    check("a parameterised scope names no literal, so it is not a false positive",
          namespace_scopes("where nspname = %s"), [])
    # ⚠ the three cases the FIRST version of this rule failed, on the shipped catalog
    check("a trailing relkind on the same line is NOT a namespace",
          namespace_scopes("where n.nspname = 'public' and c.relkind = 'r'"), [])
    check("a trailing relkind IN-list is NOT a namespace",
          namespace_scopes("where n.nspname = 'public' and c.relkind in ('v','m')"), [])
    check("a trailing proname is NOT a namespace",
          namespace_scopes("where nspname='public' and p.proname='record_artifact'"), [])
    check("...and widening the namespace itself is still CAUGHT beside them",
          bool(namespace_scopes("where n.nspname in ('public','storage') and c.relkind = 'r'")), True)
    check("`mystorage.x` is not a storage reference",
          storage_refs('X = "select mystorage.x"'), [])
    check("attribute access on a name `storage` is CAUGHT",
          bool(storage_refs("storage.objects()")), True)
    check("whitespace around the dot does not hide it",
          bool(storage_refs('X = "storage . objects"')), True)

    # ── M4: the file set must be DERIVED, so a NEW gate is covered the moment it is written ──
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        (root / "scripts").mkdir()
        (root / "scripts" / "check-schema-gates.sh").write_text("run './scripts/check-known.py'\n")
        (root / "scripts" / "check-known.py").write_text("X = 1\n")
        (root / "scripts" / "check-storage-drift.py").write_text(
            "from m4_catalog import CATALOG_SQL\nX = 'select * from storage.buckets'\n")
        (root / "scripts" / "unrelated.py").write_text("X = 'storage.buckets'\n")
        names = {p.name for p in gate_files(root)}
        check("M4 a NEW gate importing m4_catalog is in scope without being listed",
              "check-storage-drift.py" in names, True)
        check("a script the suite invokes is in scope", "check-known.py" in names, True)
        check("an unrelated script is NOT in scope", "unrelated.py" in names, False)
        found = problems(sorted(gate_files(root)), root)
        check("M4 the new gate's storage read is REPORTED",
              any("check-storage-drift.py" in f for f in found), True)
        check("the unrelated script's storage string is NOT reported",
              any("unrelated.py" in f for f in found), False)

        # an unparseable gate is CANNOT RUN, never silently clean
        (root / "scripts" / "check-broken.py").write_text("from m4_base_db import CONTAINER\ndef (\n")
        found2 = problems(sorted(gate_files(root)), root)
        check("an unparseable gate is CANNOT RUN", any(f.startswith("CANNOT RUN") for f in found2), True)

    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        (root / "scripts").mkdir()
        # ⚠ `bool(res) and …`, NOT `res[0]`. With the guard mutated to `return []` the indexed
        # form raises IndexError and takes the whole suite down: the run is red, but the CASE cannot
        # say so, and the harness reports a kill it cannot attribute. A case that DIES from the
        # defect it guards is weaker than one that REPORTS it — measured here, on this file's own
        # mutation 5, which went "RED but NOT via its case" until this line changed.
        res = problems([], root)
        check("an EMPTY derived set is CANNOT RUN, not a clean sweep",
              bool(res) and res[0].startswith("CANNOT RUN"), True)

    # ── ⟳ r1 HIGH (codex): the non-Python kinds, and the population that missed them ──────────
    check("a .sql gate reading storage.objects is CAUGHT",
          bool(text_refs("select 1 from storage.objects;", ".sql")), True)
    check("a SQL `--` comment mentioning it is NOT",
          text_refs("-- we never read storage.objects\nselect 1;", ".sql"), [])
    check("a SQL /* block */ comment is NOT",
          text_refs("/* storage.objects is not read here */ select 1;", ".sql"), [])
    check("a .sh gate reading storage.buckets is CAUGHT",
          bool(text_refs('psql -c "select id from storage.buckets"', ".sh")), True)
    check("a shell `#` comment is NOT",
          text_refs("# storage.buckets is never read\necho hi", ".sh"), [])
    check("a `#` mid-line after whitespace still comments the rest out",
          text_refs("echo hi   # storage.buckets", ".sh"), [])
    check("a `#` with no leading whitespace is NOT treated as a comment",
          bool(text_refs("X=a#storage.buckets", ".sh")), True)

    with tempfile.TemporaryDirectory() as td:
        root = pathlib.Path(td)
        (root / "scripts").mkdir()
        spec = root / "docs" / "spec"
        (spec / "schema").mkdir(parents=True)
        (root / "supabase" / "migrations").mkdir(parents=True)
        # the suite invokes its gates through a VARIABLE, exactly as the real one does
        # ⚠ THE SUITE MUST NAME THE MIGRATION, or the exclusion case cannot fail: a file that was
        # never a candidate is absent for a reason that has nothing to do with the rule. Measured —
        # the mutation that removes the exclusion went RED but NOT via this case until the fixture
        # made the migration a genuine candidate.
        (root / "scripts" / "check-schema-gates.sh").write_text(
            'SPEC="docs/spec"\nrun "1/15 x" "$SPEC/verify-schema.sh"\n'
            'psql -f supabase/migrations/0007.sql\n')
        (spec / "verify-schema.sh").write_text('psql -f "$DIR/schema/05_assert.sql"\n')
        (spec / "schema" / "05_assert.sql").write_text("select 1 from storage.objects;\n")
        (root / "supabase" / "migrations" / "0007.sql").write_text(
            "insert into storage.buckets values ('x');\n")
        names = {p.name for p in gate_files(root)}
        check("r1 HIGH: a gate invoked through a shell VARIABLE is in scope",
              "verify-schema.sh" in names, True)
        check("r1 HIGH: the SQL that gate executes is in scope",
              "05_assert.sql" in names, True)
        check("a MIGRATION is the subject, not a gate — excluded",
              "0007.sql" in names, False)
        found = problems(sorted(gate_files(root)), root)
        check("r1 HIGH: storage read from that SQL is REPORTED",
              any("05_assert.sql" in f for f in found), True)
        check("...and the migration's legitimate storage use is NOT",
              any("0007.sql" in f for f in found), False)

    # ⚠ THE `root` PARAMETER IS VARIED AGAINST THE REAL REPO, NOT ONLY BETWEEN TWO TEMP DIRS —
    # ⟳ `check-fixture-variation.py` refused this file until it was: every call above passes the
    # same `root` expression, so no case could tell that parameter from a constant and any clause
    # reading it was unguarded. These two also happen to be the only cases that prove the derivation
    # works on the SHIPPED tree rather than on fixtures I built to suit it.
    check("the default root derives a non-empty gate set from the real repo",
          len(gate_files()) > 5, True)
    # ⟳ r1 HIGH widened this deliberately: the population is no longer Python-only, because gates 1
    # and 2 are a shell script and the SQL it executes. The case moves with the rule instead of being
    # deleted — a case quietly dropped when it fails is how a rule loses its only observer.
    check("...and every derived path is a real file of a kind this guard can read",
          all(p.is_file() and p.suffix in (".py", ".sh", ".sql") for p in gate_files()), True)
    check("the shipped tree is independent of storage (the live claim, as a case)",
          problems(gate_files()), [])

    print(f"self-test: {passed + failed} cases, {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
