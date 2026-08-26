#!/usr/bin/env python3
"""Every catalog column M4's digest could read is either DIGESTED or EXCLUDED WITH A REASON.

    python3 scripts/check-catalog-coverage.py              # against the live container
    python3 scripts/check-catalog-coverage.py --self-test  # the pure classifier's cases

    exit 0 = every column of every catalog we read is classified
    exit 1 = a column is neither digested nor excused — the digest may be silently narrower
    exit 2 = could not run (treat as NOT RUN)

⭐⭐ WHY THIS EXISTS — THE LIST WAS NEVER THE MECHANISM
------------------------------------------------------
`m4_catalog.ENFORCEMENT_COLUMNS` was assembled, twice, from the sabotages somebody had already run:

    r5  the digest covered DEFINITIONS   -> r5 B2 added 18 columns, chosen from 3 sabotages seen
    r6  `proisstrict` missing (codex)    -> `alter function record_artifact(…) strict` passed
    r6  `attacl` missing (claude)        -> `grant insert (blob_key) … to anon` passed

Both r6 misses have the same cause, and it is not carelessness: **"what did the last counter-example
have that my check missed?" is a question with an unbounded supply of answers and no stopping rule.**
Four rounds of the assertion selector went the same way (`anything` → `non-comment` → `;` →
`select 1`).

This script inverts it. It asks Postgres for the columns each catalog ACTUALLY HAS — so a column
nobody has thought of, or one a future Postgres adds, is a RED TEST rather than a silent gap. Every
exclusion must carry a written reason, which is the part that cannot be automated and is the part
worth a human's attention.

⚠ WHAT IT STILL CANNOT DO. It proves the digest is not narrowing. It cannot prove an excluded column
is *correctly* excluded — that judgement is in the REASONS below, and a wrong reason here is a real
defect that this script will happily report as green. Read them.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m4_catalog import CATALOG_SQL, _run  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent

CATALOGS = ("pg_class", "pg_proc", "pg_attribute", "pg_index",
            "pg_policy", "pg_constraint", "pg_trigger", "pg_type", "pg_rewrite")

# ── EXCLUSIONS, each with the reason it is safe to not digest ────────────────────────────────────
# Ordered: the FIRST matching rule wins, and the report names which rule classified each column.
EXCLUDED: tuple[tuple[str, str], ...] = (
    # ---- identity ------------------------------------------------------------------------------
    (r"^(oid|.*relid|.*namespace|.*owner|tgrelid|tgfoid|tgconstr.*|tgparentid|indexrelid|"
     r"indrelid|polrelid|conindid|conparentid|contypid|confrelid|ev_class)$",
     "an OID or a namespace/owner reference: differs between any two databases by construction, "
     "and the object's NAME is already the manifest key"),
    (r"^(relname|proname|attname|conname|polname|tgname|typname|rulename)$",
     "the object's own name — it IS the manifest key, so digesting it would be circular"),

    # ---- statistics and physical storage ---------------------------------------------------------
    (r"^(relpages|reltuples|relallvisible|attstattarget|procost|prorows|relfrozenxid|relminmxid|"
     r"relfilenode|reltablespace|reltoastrelid|attcacheoff|indcheckxmin|relrewrite)$",
     "planner statistics or physical placement: varies with DATA VOLUME and vacuum timing, not "
     "with whether any rule executes. Digesting these would make the gate red on production purely "
     "because production has rows"),

    # ---- derived from something already digested --------------------------------------------------
    (r"^(relnatts|relchecks|relhasindex|relhassubclass|relispopulated|relisshared|attndims|"
     r"attbyval|attalign|attlen|pronargs|pronargdefaults|indnatts|indnkeyatts|coninhcount|"
     r"conislocal|attinhcount|attislocal|relhastriggers)$",
     "derived: a count or cache of things the digest already enumerates object-by-object"),
    (r"^(indclass|indcollation|indkey|indoption|indexprs|indpred|conbin|conkey|confkey|conexclop|"
     r"conpfeqop|conppeqop|conffeqop|confmatchtype|confupdtype|confdeltype|confdelsetcols|"
     r"tgargs|tgattr|tgtype|tgqual|tgnewtable|tgoldtable|tgnargs|polqual|polwithcheck|polroles|"
     r"ev_qual|ev_action|ev_attr)$",
     "rendered in full by pg_get_indexdef / pg_get_constraintdef / pg_get_triggerdef / pg_get_expr, "
     "which ARE digested — the structured column is the same fact in a less readable form"),
    (r"^(atttypid|atttypmod|attcollation|prorettype|proargtypes|proallargtypes|proargmodes|"
     r"proargnames|provariadic|protrftypes|prolang)$",
     "rendered by format_type / pg_get_function_identity_arguments / pg_language.lanname, which are "
     "digested"),

    # ---- privileges: digested as EFFECTIVE ACCESS instead ----------------------------------------
    (r"^(relacl|proacl|attacl|typacl)$",
     "⛔⛔ THIS REASON WAS FALSE FOR SEVEN COMMITS AND SURVIVED TWO REVIEW ROUNDS. It said "
     "privileges were 'digested instead as EFFECTIVE ACCESS via has_table_privilege / "
     "has_any_column_privilege / has_function_privilege' — true until fork (a) step 5, which emptied "
     "REL_GRANTEES and FN_GRANTEES so that NOTHING privilege-shaped is digested at all. The "
     "correction was written and never landed: a `str.replace` whose target no longer matched, "
     "reported as done by an UNCONDITIONAL print. Round 7's headline was four FALSE exclusion "
     "reasons; this is the fifth, in the script that exists to keep them honest. "
     "⭐ THE TRUE REASON: ACL text cannot agree between the manifest's --no-privileges baseline and "
     "any deployed database — production's default ACL names `claude_ro`, a role no container has "
     "(r6 B1, measured against production). Privileges therefore left the digest ENTIRELY "
     "(ADR-0013) and are covered by EXECUTION instead: session roles by "
     "check-anon-exposure.py RULE 3 (gate 11/12, mutations 10/17/22/23/24/25/26), and service_role "
     "by 05_assert.sql's SERVICE-ROLE CAPABILITY blocks (gate 8/12). "
     "⚠ THAT SENTENCE IS ITSELF A CLAIM — see MOVED_COVERAGE below, which makes it fail loudly."),

    # ---- rows this query does not select at all ---------------------------------------------------
    (r"^(attisdropped|tgisinternal|relispartition|relpartbound)$",
     "a FILTER, not a property: CATALOG_SQL's WHERE clauses use these to decide which rows are M4 "
     "objects at all, so their value is fixed for every row that reaches a digest"),

    # ---- cannot change whether a rule executes ----------------------------------------------------
    (r"^(atthasmissing|attmissingval|attfdwoptions)$",
     "the fast-default machinery and foreign-table options: `attmissingval` is the value existing "
     "rows read for a column added with a default, which pg_get_expr on the default already "
     "covers; no foreign tables exist in this schema"),
    (r"^(typtype|typcategory|typispreferred|typisdefined|typdelim|typrelid|typelem|typarray|"
     r"typinput|typoutput|typreceive|typsend|typmodin|typmodout|typanalyze|typsubscript|"
     r"typalign|typstorage|typnotnull|typbasetype|typtypmod|typndims|typcollation|typdefaultbin|"
     r"typdefault|typlen|typbyval)$",
     "the physical and I/O properties of a TYPE. M4 creates exactly one type, an enum, and the "
     "behaviour-bearing part of an enum is its LABEL SET, which is digested. These describe how "
     "Postgres stores and parses a value, not whether any M4 rule runs"),
    (r"^(condeferrable|condeferred|connoinherit|convalidated|contype)$",
     "rendered by pg_get_constraintdef, which is digested — MEASURED r5: it emits `NOT VALID` "
     "before `validate constraint` and `NOT DEFERRABLE INITIALLY IMMEDIATE` on the constraint "
     "trigger"),
    (r"^(indisreplident|indisclustered)$",
     "replica identity and physical clustering: they affect logical replication and row order on "
     "disk, neither of which can admit or reject a write. `relreplident` IS digested, so a change "
     "of replica identity at the TABLE level is still visible"),
    (r"^(prosupport|probin)$",
     "a planner support function and a C-language shared-object path. M4 ships no C functions and "
     "declares no support function; neither can change whether a plpgsql body runs"),
    (r"^(proargdefaults)$",
     "the internal node tree of argument defaults, rendered as SQL text by "
     "pg_get_function_arguments, which IS digested (r7 M). ⛔ THIS ROW HELD A FALSE REASON FOR ONE "
     "ROUND: it claimed a default's VALUE changes the identity arguments. It does not — identity "
     "arguments OMIT DEFAULTS (MEASURED 2026-08-26: `a integer, b text` vs `a integer, b text "
     "DEFAULT 'x'::text`), so a changed default moved neither the symbol nor the digest while every "
     "omitted-argument call wrote different data"),
    (r"^(reltype|reloftype|relam)$",
     "the composite type Postgres auto-creates for every relation, the OF-type of a typed table "
     "(M4 declares none), and the access method. All three are OID references; `relam` would matter "
     "if a table were moved off heap, which no migration in this repo can do and which cannot "
     "change whether a guard fires"),
    (r"^(atthasdef)$",
     "a boolean cache of 'a row exists in pg_attrdef'. The DEFAULT ITSELF is digested via "
     "pg_get_expr(d.adbin, d.adrelid), so a default that is added, removed or changed already moves "
     "the column digest — this flag carries no fact the digest does not have"),
    (r"^(tgdeferrable|tginitdeferred)$",
     "rendered by pg_get_triggerdef, which is digested — MEASURED r5 on the constraint trigger: "
     "`CREATE CONSTRAINT TRIGGER … NOT DEFERRABLE INITIALLY IMMEDIATE FOR EACH ROW`"),
    (r"^(ev_type|is_instead|ev_enabled)$",
     "⚠ NOT skipped — these are read through the `m4_rules` fragment, which digests every "
     "pg_rewrite row attached to a manifest relation as `name:ev_type:is_instead` (r6 H1). They "
     "appear here only because the enumeration reads pg_rewrite's columns directly"),
)


# ⭐⭐ EVERY "COVERED ELSEWHERE" CLAIM NAMES ITS INSTRUMENT AND ITS MUTATION, AND BOTH ARE CHECKED.
#
# This is the mechanism the ACL row above went without, and it is the reason that row could be false
# for seven commits across two review rounds. An exclusion whose reason says a fact "moved" to
# another instrument is making a claim about a DIFFERENT FILE, which this script never opened.
#
# The pattern across rounds 8-9 was uniform and this is its narrowest form: a coverage claim written
# by the person who built the coverage, verified by reading it. `21 - 9 = 12` is arithmetic;
# "mutation 19 goes red" was never run; "covered elsewhere" named no one. Each was true-sounding and
# unexecuted, and each cost a review round.
#
# So a moved fact must name (a) the file that now covers it and (b) a mutation label in the harness
# that proves that file goes red. Both are checked HERE, mechanically. It does not prove the mutation
# is a good one — it proves the claim points at something that exists.
MOVED_COVERAGE: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (r"^(relacl|proacl|attacl|typacl)$",
     "scripts/check-anon-exposure.py",
     ("mutation 10", "mutation 17", "mutation 22", "mutation 23",
      "mutation 24", "mutation 25", "mutation 26")),
)
HARNESS = ROOT / "scripts/mutate-live-schema-check.sh"


def moved_coverage_problems() -> list[str]:
    """The shipped claims. Thin wrapper so `--self-test` can drive the rule with fixtures."""
    return _moved_problems_for(MOVED_COVERAGE)


def _moved_problems_for(claims) -> list[str]:
    """Every claim points at a file that exists and mutations that exist."""
    out: list[str] = []
    harness = HARNESS.read_text() if HARNESS.is_file() else ""
    if not harness:
        return [f"MOVED COVERAGE  cannot read {HARNESS} — the mutation half of every 'covered "
                "elsewhere' claim is unverifiable. TREAT THIS AS NOT RUN."]
    for pattern, instrument, mutations in claims:
        if not (ROOT / instrument).is_file():
            out.append(f"MOVED COVERAGE  {pattern} says its facts moved to `{instrument}`, and no "
                       "such file exists. The claim is prose.")
        for mut in mutations:
            if mut not in harness:
                out.append(f"MOVED COVERAGE  {pattern} cites `{mut}` as the proof that "
                           f"`{instrument}` catches what left the digest, and the harness contains "
                           "no such mutation.")
    return out


def digested_columns(sql: str = CATALOG_SQL) -> set[str]:
    """Every catalog column name that literally appears in the digest query. PURE."""
    return set(re.findall(r"\b[a-z]{2,}[a-z_]*\b", sql))


def classify(column: str, digested: set[str]) -> tuple[str, str]:
    """(verdict, reason) for one column. PURE. verdict is DIGESTED, EXCLUDED or UNCLASSIFIED."""
    if column in digested:
        return "DIGESTED", "read by CATALOG_SQL"
    for pattern, reason in EXCLUDED:
        if re.match(pattern, column):
            return "EXCLUDED", reason
    return "UNCLASSIFIED", (
        "neither read by CATALOG_SQL nor listed in EXCLUDED. If it can change whether a rule "
        "EXECUTES, add it to the digest and write a mutation. If it cannot, add it to EXCLUDED "
        "WITH THE REASON — an unexplained omission is exactly how r6 B2 and the proisstrict miss "
        "happened")


def self_test() -> int:
    cases = failures = 0

    def check(label: str, got: object, want: object) -> None:
        nonlocal cases, failures
        cases += 1
        ok = got == want
        print(("  ✓ " if ok else f"  ✗ [{got!r} != {want!r}] ") + label)
        failures += 0 if ok else 1

    d = digested_columns()
    check("proisstrict is DIGESTED (r6 codex B)", classify("proisstrict", d)[0], "DIGESTED")
    check("relhasrules is DIGESTED (r6 claude H1)", classify("relhasrules", d)[0], "DIGESTED")
    check("relrowsecurity is DIGESTED (r5 B2)", classify("relrowsecurity", d)[0], "DIGESTED")
    check("tgenabled is DIGESTED (r4 B1)", classify("tgenabled", d)[0], "DIGESTED")
    # ⟳ 2026-08-26 — the ACL reason was FALSE for seven commits and this self-test passed over it,
    # because it asserted the reason mentions `claude_ro`, not that the reason is TRUE. A keyword is
    # not a fact. MOVED_COVERAGE is the part that can actually fail.
    check("every MOVED_COVERAGE claim names a file that exists and mutations that exist",
          moved_coverage_problems(), [])
    check("the ACL row is the one that claims its facts moved",
          any(r"relacl" in pat for pat, _, _ in MOVED_COVERAGE), True)
    check("a claim citing a mutation that does not exist FAILS", bool([
        p2 for p2 in _moved_problems_for(
            ((r"^(x)$", "scripts/check-anon-exposure.py", ("mutation 999",)),))]), True)
    check("a claim naming a file that does not exist FAILS", bool([
        p2 for p2 in _moved_problems_for(
            ((r"^(x)$", "scripts/no-such-file.py", ("mutation 10",)),))]), True)
    check("relacl is EXCLUDED, not digested (r6 B1)", classify("relacl", d)[0], "EXCLUDED")
    check("…and its reason names the production divergence",
          "claude_ro" in classify("relacl", d)[1], True)
    check("attacl is EXCLUDED with the same reason (r6 B2)", classify("attacl", d)[0], "EXCLUDED")
    check("reltuples is EXCLUDED — statistics, not behaviour",
          classify("reltuples", d)[0], "EXCLUDED")
    check("…and its reason says why digesting it would be WRONG, not merely unnecessary",
          "production has rows" in classify("reltuples", d)[1], True)
    check("a column nobody has thought of is UNCLASSIFIED, not silently fine",
          classify("proinvented_in_pg19", d)[0], "UNCLASSIFIED")
    check("…and the message tells the reader what to do about it",
          "write a mutation" in classify("proinvented_in_pg19", d)[1], True)

    print(f"\n{cases - failures}/{cases} self-test cases passed")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--database", default="postgres")
    ap.add_argument("--verbose", action="store_true", help="print every column and its verdict")
    a = ap.parse_args()
    if a.self_test:
        return self_test()

    sql = "\n".join(
        f"select '{c}|' || a.attname from pg_attribute a "
        f"where a.attrelid = '{c}'::regclass and a.attnum > 0 and not a.attisdropped;"
        for c in CATALOGS)
    try:
        out = _run(sql, a.database, None, __import__("m4_catalog").CONTAINER)
    except RuntimeError as e:
        print(f"CANNOT RUN — could not read pg_attribute: {e}\nTreat this as NOT RUN.",
              file=sys.stderr)
        return 2

    digested = digested_columns()
    moved = moved_coverage_problems()
    for m in moved:
        print(m)
    rows = [ln.split("|", 1) for ln in out.splitlines() if "|" in ln]
    if not rows:
        print("CANNOT RUN — the catalog enumeration returned nothing. Treat this as NOT RUN.",
              file=sys.stderr)
        return 2

    counts = {"DIGESTED": 0, "EXCLUDED": 0, "UNCLASSIFIED": 0}
    bad: list[tuple[str, str, str]] = []
    for cat, col in rows:
        verdict, reason = classify(col, digested)
        counts[verdict] += 1
        if verdict == "UNCLASSIFIED":
            bad.append((cat, col, reason))
        elif a.verbose:
            print(f"  {verdict:12} {cat}.{col}")

    print(f"catalog coverage: {len(rows)} columns across {len(CATALOGS)} catalogs — "
          f"{counts['DIGESTED']} digested, {counts['EXCLUDED']} excluded with a reason")
    if moved:
        print(f"\n❌ {len(moved)} 'covered elsewhere' claim(s) point at nothing — a moved fact must "
              "name a file that exists and a mutation that proves it", file=sys.stderr)
        return 1
    if bad:
        print(f"\n❌ {len(bad)} column(s) are UNCLASSIFIED — the digest may be silently narrower "
              f"than it claims:\n", file=sys.stderr)
        for cat, col, reason in bad:
            print(f"      ✗ {cat}.{col}", file=sys.stderr)
        print(f"\n   {bad[0][2]}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
