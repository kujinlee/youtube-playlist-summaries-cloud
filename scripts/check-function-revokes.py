#!/usr/bin/env python3
"""Ratchet: every NEWLY CREATED public function in a migration carries its own
`revoke ... on function ... from public`.

Backlog #54 half (a), the PREVENTION half — after the originally specified mechanism was
MEASURED not to work.

⛔ WHY NOT `alter default privileges`, which is what backlog #54 actually specifies.
MEASURED 2026-08-28 in scratch databases (create function, then `has_function_privilege`):

    setup                          stored default ACL      resulting function ACL
    revoke PUBLIC only             {} (empty)              (null)  = built-in default -> PUBLIC
    revoke PUBLIC -> grant anon    anon=X/postgres         =X/postgres, postgres=X, anon=X
    grant anon -> revoke PUBLIC    anon=X/postgres         =X/postgres, postgres=X, anon=X

`ALTER DEFAULT PRIVILEGES` cannot remove PUBLIC's built-in EXECUTE — stored entries behave as
ADDITIVE to it. So `anon` reaches a new function THROUGH PUBLIC, and revoking `anon` from the
default closes one of two routes while the other cannot be closed at that layer at all.

⚠ The one-line `revoke execute on functions from anon` version would have PASSED ON PRODUCTION
and been wrong everywhere else, because prod's default ACL happens to carry no PUBLIC entry. Right
by accident. That is backlog #33 in mirror image: #33 says "revoke from public does not remove
anon"; this is "revoke from anon does not remove PUBLIC".

WHAT ACTUALLY KEEPS PRODUCTION CLEAN, measured the same day: 3 of 44 public functions grant PUBLIC,
0 have a null ACL. Not one default privilege did that — **41 individual `revoke all on function
f(...) from public` statements did**, one per migration. The convention already works. It is just a
convention, i.e. every author remembering. This script is the mechanism for it.

WHAT IT ASSERTS
---------------
For each migration in filename order, every function CREATED for the first time must be followed,
in the SAME file, by a `revoke ... on function <name> ... from public`.

`CREATE OR REPLACE FUNCTION` over a function that already exists earlier in the sequence is a
REPLACEMENT, and PostgreSQL PRESERVES the existing ACL across a replace — so it needs no new
revoke, and requiring one would be a false positive. `DROP FUNCTION` puts the name back into the
"next create is a creation" state.

Exit 0 = every creation is covered.  1 = at least one is not.  2 = CANNOT RUN (treat as NOT RUN).
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MIGRATIONS = ROOT / "supabase" / "migrations"

# `create [or replace] function [public.]name(` — the paren anchors it to a definition, so a
# mention inside a comment or a string is not matched unless it looks exactly like a definition.
CREATE = re.compile(
    r"^\s*create\s+(?:or\s+replace\s+)?function\s+(?:public\.)?([a-z_][a-z0-9_]*)\s*\(",
    re.I | re.M,
)
DROP = re.compile(r"^\s*drop\s+function\s+(?:if\s+exists\s+)?(?:public\.)?([a-z_][a-z0-9_]*)", re.I | re.M)
# `revoke <anything> on function [public.]name(...) from ... public ...`
REVOKE = re.compile(
    r"revoke\s+[a-z, ]+?\s+on\s+function\s+(?:public\.)?([a-z_][a-z0-9_]*)\s*\([^)]*\)\s*from\s+([^;]+);",
    re.I | re.S,
)

# ── ALLOW-LIST. Every entry states WHY, and an entry without a reason is a parse error, not a
# ── warning — an unexplained exemption is indistinguishable from a mistake. Seeded 2026-08-28
# ── with exactly the functions PRODUCTION shows granting PUBLIC (measured, not guessed):
# ──   handle_new_user, guard_is_anonymous, set_videos_updated_at
# ── All three are invoked by the TRIGGER mechanism, not reachable as PostgREST RPC endpoints.
ALLOW: dict[str, str] = {
    "handle_new_user":      "auth trigger on auth.users; fires as the trigger owner, no RPC surface",
    "guard_is_anonymous":   "trigger guard; invoked by the trigger mechanism, not callable as RPC",
    "set_videos_updated_at": "BEFORE UPDATE trigger on videos; no RPC surface",
}


def migrations(d: pathlib.Path = MIGRATIONS) -> list[pathlib.Path]:
    return sorted(d.glob("*.sql"))


def audit(files: list[pathlib.Path], allow: dict[str, str] | None = None) -> list[str]:
    """Findings; empty means every first-creation carries its own revoke-from-public."""
    allow = ALLOW if allow is None else allow
    problems: list[str] = []
    seen: set[str] = set()          # functions that already exist at this point in the sequence

    for f in files:
        text = f.read_text()
        revoked_from_public = {
            name.lower()
            for name, grantees in REVOKE.findall(text)
            if re.search(r"\bpublic\b", grantees, re.I)
        }
        # Order matters within a file only for drop-then-create; take drops first so a file that
        # drops and recreates is treated as a creation.
        for name in (m.lower() for m in DROP.findall(text)):
            seen.discard(name)

        for name in (m.lower() for m in CREATE.findall(text)):
            if name in seen:
                continue                      # replacement — PostgreSQL preserves the ACL
            seen.add(name)
            if name in allow:
                continue
            if name not in revoked_from_public:
                problems.append(
                    f"{f.name}: `{name}` is CREATED here but never "
                    f"`revoke ... on function {name}(...) from public` in this file"
                )
    return problems


# ────────────────────────────────────────────────────────────── self-test
def _self_test() -> int:
    import tempfile

    passed = failed = 0

    def case(label: str, ok: bool) -> None:
        nonlocal passed, failed
        print(f"  {'✅' if ok else '❌'}  {label}")
        if ok:
            passed += 1
        else:
            failed += 1

    def tree(files: dict[str, str]) -> list[pathlib.Path]:
        d = pathlib.Path(tempfile.mkdtemp())
        for n, body in files.items():
            (d / n).write_text(body)
        return sorted(d.glob("*.sql"))

    mk = "create function f() returns int language sql as 'select 1';\n"
    rv = "revoke all on function f() from public;\n"

    case("a creation WITHOUT a revoke is a finding",
         len(audit(tree({"0001_a.sql": mk}), allow={})) == 1)
    case("a creation WITH a revoke is clean",
         audit(tree({"0001_a.sql": mk + rv}), allow={}) == [])
    case("revoke may appear before the create in the file",
         audit(tree({"0001_a.sql": rv + mk}), allow={}) == [])
    case("`create or replace` of an EXISTING function needs no new revoke",
         audit(tree({"0001_a.sql": mk + rv,
                     "0002_b.sql": "create or replace function f() returns int language sql as 'select 2';\n"}),
               allow={}) == [])
    case("first-ever `create or replace` DOES need one",
         len(audit(tree({"0001_a.sql": "create or replace function f() returns int language sql as 'select 1';\n"}),
                   allow={})) == 1)
    case("drop then recreate needs a fresh revoke",
         len(audit(tree({"0001_a.sql": mk + rv,
                         "0002_b.sql": "drop function f();\n" + mk}), allow={})) == 1)
    case("a revoke naming a DIFFERENT grantee does not count",
         len(audit(tree({"0001_a.sql": mk + "revoke all on function f() from anon;\n"}), allow={})) == 1)
    case("`from public, anon` counts",
         audit(tree({"0001_a.sql": mk + "revoke all on function f() from public, anon;\n"}), allow={}) == [])
    case("public.-qualified create is matched",
         len(audit(tree({"0001_a.sql": "create function public.f() returns int language sql as 'select 1';\n"}),
                   allow={})) == 1)
    case("public.-qualified revoke satisfies it",
         audit(tree({"0001_a.sql": "create function public.f() returns int language sql as 'select 1';\n"
                                   "revoke all on function public.f() from public;\n"}), allow={}) == [])
    case("an allow-listed function is exempt",
         audit(tree({"0001_a.sql": mk}), allow={"f": "because"}) == [])
    case("a function mentioned only in a COMMENT is not a creation",
         audit(tree({"0001_a.sql": "-- create function f() would need a revoke\n"}), allow={}) == [])
    case("two creations, one uncovered -> exactly one finding",
         len(audit(tree({"0001_a.sql": mk + rv +
                         "create function g() returns int language sql as 'select 1';\n"}), allow={})) == 1)
    case("ordering is by FILENAME, so 0002 sees 0001's function",
         audit(tree({"0002_b.sql": "create or replace function f() returns int language sql as 'select 2';\n",
                     "0001_a.sql": mk + rv}), allow={}) == [])
    case("every ALLOW entry carries a non-empty reason",
         all(isinstance(v, str) and v.strip() for v in ALLOW.values()))
    case("the real migrations directory is non-empty (else this gate is vacuous)",
         len(migrations()) > 0)

    print(f"\n{passed}/{passed + failed} self-test cases passed")
    return 1 if failed else 0


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return _self_test()

    if not MIGRATIONS.is_dir():
        print(f"CANNOT RUN — no migrations directory at {MIGRATIONS}. Treat this as NOT RUN.",
              file=sys.stderr)
        return 2
    files = migrations()
    if not files:
        print("CANNOT RUN — the migrations directory is EMPTY, so this gate would pass over "
              "nothing. Treat this as NOT RUN.", file=sys.stderr)
        return 2
    bad = [k for k, v in ALLOW.items() if not (isinstance(v, str) and v.strip())]
    if bad:
        print(f"CANNOT RUN — allow-list entries without a reason: {', '.join(sorted(bad))}. "
              "An unexplained exemption is indistinguishable from a mistake.", file=sys.stderr)
        return 2

    problems = audit(files)
    accepted = ", ".join(sorted(ALLOW))
    if problems:
        print("a public function is created without revoking PUBLIC's built-in EXECUTE:\n")
        for p in problems:
            print(f"  ✗ {p}")
        print("\nPostgreSQL grants EXECUTE on a new function to PUBLIC, and `alter default "
              "privileges`\nCANNOT remove it (measured 2026-08-28). The per-function revoke is "
              "the only mechanism\nthat works — add `revoke all on function <name>(...) from "
              "public;` beside the create.")
        return 1

    print(f"function revokes: {len(files)} migration(s) scanned, every newly created public "
          f"function revokes PUBLIC; allowing {accepted}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
