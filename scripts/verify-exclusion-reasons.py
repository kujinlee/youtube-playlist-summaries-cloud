#!/usr/bin/env python3
"""EXECUTE the written reasons in `check-catalog-coverage.py`, instead of re-reading them.

    python3 scripts/verify-exclusion-reasons.py            # against a scratch M4 database
    python3 scripts/verify-exclusion-reasons.py --self-test

    exit 0 = every executable reason was EXECUTED and held
    exit 1 = a reason is FALSE — the digest is blind to something a reason says it sees
    exit 2 = could not run (treat as NOT RUN)

⭐⭐ WHY THIS EXISTS — FIVE FALSE REASONS IN ONE FILE IS A RATE, NOT AN ACCIDENT
--------------------------------------------------------------------------------
`check-catalog-coverage.py` proves the digest is not silently NARROWING: every catalog column is
digested or excluded with a written reason. Its own docstring states the bound it could not close:

    "It cannot prove an excluded column is *correctly* excluded — that judgement is in the REASONS,
     and a wrong reason here is a real defect that this script will happily report as green."

That bound has now been hit five times:

    r7 (codex)   FOUR exclusion reasons false in one round, incl. `proargdefaults`
    2026-08-26   a FIFTH — `relacl` still claimed privileges were "digested as effective access"
                 seven commits after fork (a) step 5 removed them entirely

And the fifth is the one that matters for this file's existence: it was introduced by the commit
that fixed the fourth, and it survived BOTH halves of round 8 and BOTH halves of round 9. Every
reviewer was pointed at the instruments; nobody re-read the prose that says what the instruments
cover. A reason is a claim about behaviour, and this project's rule for claims about behaviour is
that they are executed, not read.

WHAT IT DOES
------------
Six of the eighteen rules say some variant of *"column X is not digested because it is RENDERED BY
Y, and Y IS digested"*. That is directly falsifiable: change the underlying fact and the digest must
move. If it does not, the reason is FALSE and the gate has a hole exactly the width of that claim.

⚠ WHAT IT DOES NOT DO, STATED SO THE NEXT READER DOES NOT HAVE TO REDERIVE IT:

 1. **One representative column per rule, not all of them.** Rule 5 covers 24 columns; this executes
    one mutation per RENDERING FUNCTION named in the reason. Claiming the rule is verified because
    one of its columns is would be the same defect this file exists to catch, so every run prints
    the columns it did NOT touch.
 2. **Seven more rules rest on a PREMISE ABOUT WHAT M4 CONTAINS**, not on the nature of a column —
    "no foreign tables exist in this schema", "M4 creates exactly one type, an enum", "M4 ships no
    C functions". Those are executable in one query each, and they are, below. ⚠ THEY WERE FILED
    UNDER "no executable form" UNTIL 2026-08-26, which was wrong and is the point of this section:
    a premise is TRUE WHEN WRITTEN and nothing re-reads it. The day M4 gains a DOMAIN type — whose
    CHECK admits or rejects writes — rule 10's reason becomes false, the type is absent from the
    manifest entirely (CATALOG_SQL selects `typtype = 'e'` and nothing else), and no observation
    fires. Same shape as the ACL reason that was false for seven commits, one level out.
 3. **The remaining rules have no executable form** — identity, statistics, derived counts, the two
    genuine WHERE-clause filters, index-level replica identity. They are printed as
    UNVERIFIED-BY-EXECUTION with their class, every run. Silence about them would read as coverage.
 4. It proves a reason is NOT FALSE in the direction tested. It cannot prove the exclusion is wise.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from m4_catalog import CONTAINER  # noqa: E402

PREFIX = "xr_verify"

# ── the executable claims ───────────────────────────────────────────────────────────────────────
# (rule, column, renderer, mutation SQL, PROBE SQL, sibling columns not touched)
#
# ⛔⛔ THE PROBE IS NOT OPTIONAL, AND THIS FILE LEARNED THAT THE HARD WAY ON ITS FIRST RUN.
# Rule 16's mutation was `alter table video_artifacts alter column state set default 'recorded'` —
# and `state` ALREADY defaulted to 'recorded'. Nothing changed, the digest correctly did not move,
# and this script reported the reason FALSE. A vacuous mutation reported as a finding, in the tool
# written to catch reasons that are not what they claim. With a column that genuinely has no default
# (`blob_key`) the digest goes red and the reason is TRUE.
#
# So every claim carries a PROBE: a scalar whose value must CHANGE across the mutation. If it does
# not, the case is NOT RUN — never TRUE, never FALSE. Same falsifier `mutate-live-schema-check.sh`
# already carries; not carrying it here is how the third instrument in one day shipped the defect it
# was hunting.
CLAIMS: tuple[tuple[str, str, str, str, str, str], ...] = (
    ("rule 5", "indkey/indoption", "pg_get_indexdef",
     "drop index if exists video_artifacts_paid_uq; "
     "create unique index video_artifacts_paid_uq on video_artifacts (workspace_id, video_id, slot);",
     "select pg_get_indexdef('public.video_artifacts_paid_uq'::regclass);",
     "indclass indcollation indexprs indpred"),

    ("rule 5", "conbin/conkey", "pg_get_constraintdef",
     "alter table video_artifacts drop constraint art_key_names_generation; "
     "alter table video_artifacts add constraint art_key_names_generation check (true);",
     "select pg_get_constraintdef(oid) from pg_constraint where conname='art_key_names_generation';",
     "confkey conexclop conpfeqop conppeqop conffeqop confmatchtype confupdtype confdeltype"),

    ("rule 5", "tgtype", "pg_get_triggerdef",
     "drop trigger if exists video_artifacts_append_only_trg on video_artifacts; "
     "create trigger video_artifacts_append_only_trg before update or delete on video_artifacts "
     "for each statement execute function video_artifacts_append_only();",
     "select pg_get_triggerdef(oid) from pg_trigger where tgname='video_artifacts_append_only_trg';",
     "tgargs tgattr tgqual tgnewtable tgoldtable tgnargs"),

    ("rule 5", "polqual", "pg_get_expr on pg_policy",
     "drop policy if exists video_artifacts_owner_read on video_artifacts; "
     "create policy video_artifacts_owner_read on video_artifacts for select using (true);",
     "select coalesce(pg_get_expr(polqual, polrelid),'<none>') from pg_policy where polname='video_artifacts_owner_read';",
     "polwithcheck polroles"),

    # ⚠ THIS CLAIM IS TESTED VIA `prorettype`, NOT via a COLUMN type, and the reason is measured:
    # Postgres refuses `alter column ... type` on any column a view depends on, and EVERY text column
    # of every M4 table has a view dependency (queried, 0 free columns). So the column-type half of
    # rule 6 is UNREACHABLE by this method and is named in UNVERIFIABLE below rather than quietly
    # dropped. `format_type` is the renderer the reason names for both, so testing it on a function
    # return type exercises the same claim about the same function — but not about the same catalog
    # column, and that distinction is the entire subject of this file.
    ("rule 6", "prorettype", "format_type",
     "drop function corrections_hash_of(text); "
     "create function corrections_hash_of(p text) returns varchar language sql immutable "
     "set search_path=public as $c$ select md5(coalesce(p,'')) $c$;",
     "select format_type(p.prorettype,null) from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and p.proname='corrections_hash_of';",
     "attcollation proargtypes proallargtypes proargmodes proargnames provariadic prolang"),

    ("rule 11", "convalidated", "pg_get_constraintdef renders NOT VALID",
     "alter table video_generations drop constraint gen_complete_has_produced_at; "
     "alter table video_generations add constraint gen_complete_has_produced_at "
     "check (produced_at is not null) not valid;",
     "select pg_get_constraintdef(oid) from pg_constraint where conname='gen_complete_has_produced_at';",
     "condeferrable condeferred connoinherit contype"),

    ("rule 14", "proargdefaults", "pg_get_function_arguments",
     "do $x$ declare s text; begin "
     "select 'create or replace function public.record_artifact(' || "
     "  regexp_replace(pg_get_function_arguments(p.oid), 'p_md_hash text DEFAULT [^,)]*', "
     "                 'p_md_hash text DEFAULT ''xr''::text') || "
     "  ') returns ' || pg_get_function_result(p.oid) || "
     "  ' language plpgsql security definer set search_path = '''' as ' || quote_literal(p.prosrc) "
     "  into s from pg_proc p join pg_namespace n on n.oid = p.pronamespace "
     " where n.nspname = 'public' and p.proname = 'record_artifact'; execute s; end $x$;",
     "select pg_get_function_arguments(p.oid) from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and p.proname='record_artifact';",
     "(this rule covers only proargdefaults)"),

    ("rule 16", "atthasdef", "pg_get_expr on pg_attrdef",
     "alter table video_artifacts alter column blob_key set default 'xr-injected';",
     "select coalesce(pg_get_expr(d.adbin,d.adrelid),'<none>') from pg_attribute a left join pg_attrdef d on d.adrelid=a.attrelid and d.adnum=a.attnum where a.attrelid='public.video_artifacts'::regclass and a.attname='blob_key';",
     "(this rule covers only atthasdef)"),

    ("rule 17", "tgdeferrable/tginitdeferred", "pg_get_triggerdef",
     "drop trigger if exists video_artifacts_generation_complete_trg on video_artifacts; "
     "create constraint trigger video_artifacts_generation_complete_trg after insert on "
     "video_artifacts deferrable initially deferred for each row "
     "execute function video_artifacts_generation_complete();",
     "select pg_get_triggerdef(oid) from pg_trigger where tgname='video_artifacts_generation_complete_trg';",
     "(this rule covers both columns it names)"),

    ("rule 18", "ev_type/is_instead", "the m4_rules fragment",
     "create rule xr_swallow as on delete to video_artifacts do instead nothing;",
     "select count(*)::text from pg_rewrite r join pg_class c on c.oid=r.ev_class where c.relname='video_artifacts';",
     "ev_enabled"),
)

# ── the reasons that rest on a PREMISE about what M4 CONTAINS ───────────────────────────────────
# (rule, the premise in words, SQL returning ONE scalar, the value that makes the reason hold)
#
# ⭐ THESE ARE NOT CLAIMS ABOUT A COLUMN — they are claims about THIS SCHEMA, and a schema grows.
# Every one was true when its reason was written and every one is executable in a single query, so
# filing them under "no executable form" (as this file did until 2026-08-26) bought nothing and hid
# a rot path: nothing re-reads a premise, so it goes false in silence.
#
# The sharpest is rule 10. CATALOG_SQL's type arm is `where n.nspname='public' and t.typtype='e'`.
# A DOMAIN is not an enum, its CHECK constraint decides whether a write is admitted, and it would be
# absent from the manifest ENTIRELY — not digested-wrongly, ABSENT. Present mode is `MANIFEST ⊆ live`
# and cannot see an object it never enumerated. So the premise IS the coverage.
PREMISES: tuple[tuple[str, str, str, str], ...] = (
    ("rule 8", "no partitioned table and no partition exists in `public`, so `relpartbound` is null "
               "on every row the manifest selects. ⚠ the written reason says CATALOG_SQL's WHERE "
               "clauses read these columns — TRUE of attisdropped and tgisinternal, but "
               "`relpartbound` appears NOWHERE in CATALOG_SQL, so this premise is its real reason",
     "select count(*)::text from pg_class c join pg_namespace n on n.oid = c.relnamespace "
     "where n.nspname = 'public' and (c.relkind = 'p' or c.relispartition);", "0"),

    ("rule 9", "no foreign table exists in `public`, so `attfdwoptions` carries nothing on any "
               "column the manifest selects",
     "select count(*)::text from pg_class c join pg_namespace n on n.oid = c.relnamespace "
     "where n.nspname = 'public' and c.relkind = 'f';", "0"),

    ("rule 10", "M4 creates exactly ONE type, so 'the behaviour-bearing part is its LABEL SET' is a "
                "statement about one known object rather than about types in general",
     "select count(*)::text from pg_type t join pg_namespace n on n.oid = t.typnamespace "
     "where n.nspname = 'public' and t.typtype = 'e';", "1"),

    ("rule 10", "…and `public` holds no type of any other user-definable kind — no domain ('d'), "
                "range ('r'), multirange ('m') or pseudo ('p'). 'b' and 'c' are the base/array rows "
                "and the per-relation composites Postgres creates unbidden. A DOMAIN would break the "
                "reason AND be invisible to the manifest",
     "select count(*)::text from pg_type t join pg_namespace n on n.oid = t.typnamespace "
     "where n.nspname = 'public' and t.typtype not in ('b','c','e');", "0"),

    ("rule 13", "M4 ships no C function and declares no planner support function, so `probin` and "
                "`prosupport` are empty on every function the manifest selects",
     "select count(*)::text from pg_proc p join pg_namespace n on n.oid = p.pronamespace "
     "where n.nspname = 'public' and (p.probin is not null or p.prosupport <> 0);", "0"),

    ("rule 15", "M4 declares no typed (OF-type) table, so `reloftype` is 0 on every relation",
     "select count(*)::text from pg_class c join pg_namespace n on n.oid = c.relnamespace "
     "where n.nspname = 'public' and c.reloftype <> 0;", "0"),

    ("rule 15", "every M4 relation is on the heap access method. ⚠ THE WRITTEN REASON SAID `relam` "
                "'would matter if a table were moved off heap, which no migration in this repo can "
                "do' — that is a claim about the REPO. This gate exists to detect drift in a "
                "DEPLOYED database, where nothing constrains what ran against it",
     "select count(*)::text from pg_class c join pg_namespace n on n.oid = c.relnamespace "
     "join pg_am a on a.oid = c.relam "
     "where n.nspname = 'public' and c.relkind = 'r' and a.amname <> 'heap';", "0"),
)

# ── the reasons that have NO executable form, printed every run ──────────────────────────────────
UNVERIFIABLE: tuple[tuple[str, str], ...] = (
    ("rules 1, 2, 15 (partial)",
     "IDENTITY — an OID, a namespace/owner reference, or the object's own name. The name IS the "
     "manifest key, so digesting it would be circular. Rule 15 is PARTIAL: `reltype` is a genuine "
     "OID reference, but its `reloftype` and `relam` halves rest on premises, EXECUTED above."),
    ("rule 3", "VARIES WITH DATA — planner statistics and physical placement. Digesting these would "
               "make the gate red on production purely because production has rows."),
    ("rule 4", "DERIVED — a count or cache of things the digest already enumerates object-by-object. "
               "There is no way to move the cache without moving what it counts."),
    ("rule 8 (partial)",
     "A FILTER, not a property — `not a.attisdropped` and `not t.tgisinternal` are WHERE clauses of "
     "CATALOG_SQL (VERIFIED by reading it), so their value is fixed for every row that reaches a "
     "digest. `relpartbound` is NOT one of them and is covered by a premise, EXECUTED above."),
    ("rule 12", "PHYSICAL — index-level replica identity and physical clustering. They affect "
                "logical replication and on-disk row order, neither of which can admit or reject a "
                "write. The reason's own escape hatch, that TABLE-level `relreplident` is digested, "
                "is asserted by --self-test against CATALOG_SQL's md5 payloads."),
    ("rule 6 (partial)", "atttypid/atttypmod ONLY — UNREACHABLE by this method. Postgres refuses "
                         "`alter column … type` on a column any view depends on, and a query over "
                         "the built schema found ZERO M4 text columns without one. The rule's other "
                         "renderer, format_type on prorettype, IS executed above."),
    ("rule 7", "MOVED — privileges left the digest entirely (ADR-0013). Verified instead by "
               "`check-catalog-coverage.MOVED_COVERAGE`, which requires the named instrument and its "
               "mutations to exist, and by harness mutations 10/17/22/23/24/25/26."),
)


def sh(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(args, capture_output=True, text=True)


def psql(db: str, sql: str) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", "exec", "-i", CONTAINER, "psql", "-U", "postgres",
                           "-d", db, "-tAq", "-v", "ON_ERROR_STOP=1"],
                          input=sql, capture_output=True, text=True)


def admin(sql: str) -> subprocess.CompletedProcess:
    return psql("postgres", sql)


def digest_red(db: str) -> bool:
    """True when the live-catalog gate REJECTS this database as not-M4."""
    p = sh("python3", str(ROOT / "scripts/check-live-schema.py"),
           "--database", db, "--expect-present")
    return p.returncode != 0


def build_template(tpl: str) -> bool:
    admin(f"drop database if exists {tpl} (force);")
    if admin(f"create database {tpl};").returncode != 0:
        return False
    dump = sh("docker", "exec", "-i", CONTAINER, "sh", "-c",
              f"pg_dump -U postgres -d postgres --schema-only --no-owner --no-privileges "
              f"| psql -U postgres -d {tpl} -q")
    if dump.returncode != 0:
        return False
    built = sh("python3", str(ROOT / "scripts/build-m4-schema.py"), "--quiet",
               "--out", "/tmp/xr-m4.sql")
    if built.returncode != 0:
        return False
    return psql(tpl, Path("/tmp/xr-m4.sql").read_text()).returncode == 0


def md5_payloads(sql: str) -> str:
    """Everything inside an md5(…) call of `sql`, comments stripped. PURE.

    A column named only in a JOIN, a WHERE clause or a comment contributes to NO digest, so
    `column in CATALOG_SQL` is not the same question as `column moves the digest`. This is the
    narrower reading, and --self-test uses it to hold rule 12's escape hatch honest.
    """
    text, out, i = re.sub(r"--[^\n]*", "", sql), [], 0
    while (j := text.find("md5(", i)) >= 0:
        k, depth = j + 4, 1
        while k < len(text) and depth:
            depth += (text[k] == "(") - (text[k] == ")")
            k += 1
        out.append(text[j + 4:k - 1])
        i = k
    return " ".join(out)


def run_premises(tpl: str) -> tuple[list[tuple[str, str, str, str]], list[tuple[str, str]]]:
    """Execute every premise against the built template. Returns (broken, not_run).

    ⛔ A premise that CANNOT BE READ is not a premise that holds — psql failing here lands in
    `not_run`, which main() reports as exit 2, never as a pass.
    """
    broken: list[tuple[str, str, str, str]] = []
    not_run: list[tuple[str, str]] = []
    for rule, premise, sql, want in PREMISES:
        got = psql(tpl, sql)
        value = got.stdout.strip()
        if got.returncode != 0 or not value:
            not_run.append((rule, (got.stderr or "the query returned nothing").strip()[:140]))
            continue
        held = value == want
        print(f"  {'✓ HOLDS' if held else '✗ BROKEN'}  {rule:8} {premise.split('.')[0][:88]}")
        if not held:
            print(f"           ⛔ expected {want!r}, measured {value!r} — the exclusion reason for "
                  f"{rule} rests on this and no longer holds.")
            broken.append((rule, premise, want, value))
    return broken, not_run


def self_test() -> int:
    cases = failures = 0

    def check(label: str, got, want) -> None:
        nonlocal cases, failures
        cases += 1
        ok = got == want
        if not ok:
            failures += 1
        print(f"  {'✓' if ok else '✗'} {label}" + ("" if ok else f"   got={got!r} want={want!r}"))

    check("every claim names a rule, column, renderer, mutation, PROBE and untouched siblings",
          all(len(c) == 6 and all(str(x).strip() for x in c) for c in CLAIMS), True)
    check("every claim states which sibling columns it did NOT touch",
          all(c[5].strip() for c in CLAIMS), True)
    check("every claim carries a PROBE — the vacuity falsifier this file shipped without",
          all(c[4].lower().startswith("select") for c in CLAIMS), True)
    # ⭐ the whole point: a rule that says "rendered by X" must have an executable claim, or be
    # listed as unverifiable. Neither list may silently omit a rule.
    import importlib.util as u
    spec = u.spec_from_file_location("cc", ROOT / "scripts/check-catalog-coverage.py")
    cc = u.module_from_spec(spec); spec.loader.exec_module(cc)
    rendered = {i for i, (_, r) in enumerate(cc.EXCLUDED, 1)
                if "rendered" in r.lower() or "digested via" in r.lower()}
    claimed = {int(c[0].split()[1]) for c in CLAIMS}
    check("every RENDERED-BY rule has at least one executable claim",
          sorted(rendered - claimed), [])
    check("the rule count has not drifted from what this file was written against",
          len(cc.EXCLUDED), 18)
    unver = {n for label, _ in UNVERIFIABLE
             for n in [int(t.strip(",")) for t in label.split() if t.strip(",").isdigit()]}
    premised = {int(p[0].split()[1]) for p in PREMISES}
    covered = claimed | unver | premised
    check("EVERY rule is executed, premised, or explicitly listed as unverifiable",
          sorted(set(range(1, len(cc.EXCLUDED) + 1)) - covered), [])

    # ── the premise machinery ───────────────────────────────────────────────────────────────────
    check("every premise names a rule, a premise, a SELECT and an expected value",
          all(len(p) == 4 and all(str(x).strip() for x in p) and p[2].lower().startswith("select")
              for p in PREMISES), True)
    check("every premise names a rule that EXISTS in check-catalog-coverage.EXCLUDED",
          sorted(n for n in premised if not 1 <= n <= len(cc.EXCLUDED)), [])
    # ⭐ A rule cannot be BOTH fully unverifiable and premised — that reads as coverage twice over.
    # Where a rule is genuinely split (15's `reltype` vs its `reloftype`/`relam` halves), the
    # UNVERIFIABLE label must SAY SO, or the two lists quietly disagree about the same rule.
    both = premised & unver
    check("a rule in BOTH lists is labelled (partial) in UNVERIFIABLE",
          sorted(n for n in both
                 if not any("partial" in label.lower()
                            and str(n) in [t.strip(",") for t in label.split()]
                            for label, _ in UNVERIFIABLE)), [])
    # ⭐ rule 12's reason escapes on "`relreplident` IS digested". That is a claim about a DIFFERENT
    # file, which is the exact shape the ACL reason used to be false in. `column in CATALOG_SQL` is
    # too weak to settle it — a JOIN key or a comment satisfies that — so this asks the narrower
    # question: does it feed an md5?
    import m4_catalog as m4c
    payloads = md5_payloads(m4c.CATALOG_SQL)
    check("rule 12's escape hatch is real: relreplident feeds an md5 of CATALOG_SQL",
          "relreplident" in payloads, True)
    check("md5_payloads is narrower than a substring match: a WHERE-only column is NOT in it",
          "attisdropped" in payloads, False)
    print(f"\n{cases - failures}/{cases} self-test cases passed")
    return 1 if failures else 0


def main() -> int:
    if admin("select 1").returncode != 0:
        print(f"CANNOT RUN — no Postgres at container {CONTAINER}. TREAT THIS AS NOT RUN.",
              file=sys.stderr)
        return 2
    tpl = f"{PREFIX}_tpl"
    print(f"building an M4 template ({tpl}) …")
    if not build_template(tpl):
        print("CANNOT RUN — could not build the M4 template. TREAT THIS AS NOT RUN.", file=sys.stderr)
        return 2
    if digest_red(tpl):
        print("CANNOT RUN — the UNMUTATED template is already rejected by the digest, so every "
              "verdict below would be unearned. TREAT THIS AS NOT RUN.", file=sys.stderr)
        admin(f"drop database if exists {tpl} (force);")
        return 2
    print("  control: the unmutated template PASSES the digest\n")

    false_reasons, not_run = [], []
    for i, (rule, column, renderer, sql, probe, untouched) in enumerate(CLAIMS):
        db = f"{PREFIX}_{i}"
        admin(f"drop database if exists {db} (force);")
        if admin(f"create database {db} template {tpl};").returncode != 0:
            not_run.append((rule, column, "could not clone the template"))
            continue
        before = psql(db, probe)
        applied = psql(db, sql)
        if applied.returncode != 0:
            not_run.append((rule, column, (applied.stderr or applied.stdout).strip()[:140]))
            admin(f"drop database if exists {db} (force);")
            continue
        after = psql(db, probe)
        # ⭐ THE FALSIFIER. A mutation that changed nothing can only produce a green digest, and
        # reading that as "the reason is FALSE" is how this file's first run filed a defect against
        # a reason that is true.
        if before.returncode != 0 or after.returncode != 0 or not before.stdout.strip():
            not_run.append((rule, column, "the probe returned nothing — cannot tell whether the "
                                          "mutation landed"))
            admin(f"drop database if exists {db} (force);")
            continue
        if before.stdout == after.stdout:
            not_run.append((rule, column, f"VACUOUS — the probe did not move: "
                                          f"{before.stdout.strip()[:80]!r}"))
            admin(f"drop database if exists {db} (force);")
            continue
        moved = digest_red(db)
        mark = "✓ TRUE " if moved else "✗ FALSE"
        print(f"  {mark}  {rule:8} {column:26} — reason says: rendered by {renderer}")
        if not moved:
            print(f"           ⛔ the digest did NOT move. The reason is FALSE and the gate is "
                  f"blind to {column}.")
            false_reasons.append((rule, column, renderer))
        print(f"           not touched by this claim: {untouched}")
        admin(f"drop database if exists {db} (force);")

    # ⭐ PREMISES RUN AGAINST THE TEMPLATE, SO THIS MUST PRECEDE THE DROP.
    print("\nPREMISES — reasons that rest on what M4 CONTAINS, not on the nature of a column:")
    broken, premise_not_run = run_premises(tpl)
    not_run.extend((rule, "(premise)", err) for rule, err in premise_not_run)
    admin(f"drop database if exists {tpl} (force);")

    print("\nREASONS WITH NO EXECUTABLE FORM — printed every run, because silence reads as coverage:")
    for label, why in UNVERIFIABLE:
        print(f"  ⚪ {label:22} {why}")

    if not_run:
        print("\n⛔ CLAIMS THAT COULD NOT RUN — these are FAILURES, not passes:", file=sys.stderr)
        for rule, column, err in not_run:
            print(f"  {rule} {column}: {err}", file=sys.stderr)
        return 2
    if false_reasons:
        print(f"\n❌ {len(false_reasons)} written reason(s) are FALSE — a column the reason says is "
              "covered is invisible to the digest", file=sys.stderr)
        return 1
    if broken:
        print(f"\n❌ {len(broken)} PREMISE(S) NO LONGER HOLD. The exclusion reason that rests on "
              "each is now false, and the digest has a hole exactly its width:", file=sys.stderr)
        for rule, premise, want, value in broken:
            print(f"  {rule}: expected {want!r}, measured {value!r} — {premise}", file=sys.stderr)
        print("  Fix the SCHEMA or rewrite the reason. Do not widen the expected value.",
              file=sys.stderr)
        return 1
    print(f"\n✅ {len(CLAIMS)} executable reason(s) EXECUTED and held; {len(PREMISES)} premise(s) "
          f"MEASURED and hold; {len(UNVERIFIABLE)} rule group(s) have no executable form and are "
          f"named above.")
    return 0


def premises_only(db: str) -> int:
    """Run ONLY the premises, against a database somebody else built. For the mutation harness.

    Exists so `mutate-live-schema-check.sh` can assert the pair that matters: the digest still
    PASSES (it is blind to the drift) while this goes RED. One assertion cannot tell "coverage
    moved" from "coverage deleted" — the same reason ADR-0013's mutations come in pairs.
    """
    if admin("select 1").returncode != 0:
        print(f"CANNOT RUN — no Postgres at container {CONTAINER}. TREAT THIS AS NOT RUN.",
              file=sys.stderr)
        return 2
    if psql(db, "select 1").returncode != 0:
        print(f"CANNOT RUN — cannot read database {db!r}. TREAT THIS AS NOT RUN.", file=sys.stderr)
        return 2
    broken, not_run = run_premises(db)
    if not_run:
        for rule, err in not_run:
            print(f"CANNOT RUN — {rule}: {err}", file=sys.stderr)
        return 2
    if broken:
        print(f"PREMISE BROKEN on {db}: " +
              "; ".join(f"{r} expected {w!r} measured {v!r}" for r, _, w, v in broken),
              file=sys.stderr)
        return 1
    print(f"all {len(PREMISES)} premises hold on {db}")
    return 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    if "--premises-only" in sys.argv:
        if "--database" not in sys.argv:
            print("--premises-only requires --database <name>", file=sys.stderr)
            sys.exit(2)
        sys.exit(premises_only(sys.argv[sys.argv.index("--database") + 1]))
    sys.exit(main())
