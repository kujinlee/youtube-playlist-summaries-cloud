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

⚠ WHAT THIS STILL CANNOT SEE, stated rather than implied: SQL assembled at runtime from fragments
(`"storage" + "." + tbl`), a gate that shells out to `psql` with a heredoc built elsewhere, or a
non-Python gate. The first two are contrivances; the third is real and bounded — the shell gates
reach Postgres through these same Python modules.
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

    # ⚠ THE `root` PARAMETER IS VARIED AGAINST THE REAL REPO, NOT ONLY BETWEEN TWO TEMP DIRS —
    # ⟳ `check-fixture-variation.py` refused this file until it was: every call above passes the
    # same `root` expression, so no case could tell that parameter from a constant and any clause
    # reading it was unguarded. These two also happen to be the only cases that prove the derivation
    # works on the SHIPPED tree rather than on fixtures I built to suit it.
    check("the default root derives a non-empty gate set from the real repo",
          len(gate_files()) > 5, True)
    check("...and every derived path is a real file under scripts/",
          all(p.is_file() and p.suffix == ".py" for p in gate_files()), True)
    check("the shipped tree is independent of storage (the live claim, as a case)",
          problems(gate_files()), [])

    print(f"self-test: {passed + failed} cases, {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
