#!/usr/bin/env python3
"""Does the DEPLOYED schema match what M4 claims — a RATCHET on the SUBJECT axis.

    python3 scripts/check-live-schema.py --expect-absent    # before 0027, or after 0028
    python3 scripts/check-live-schema.py --expect-present   # after 0027
    python3 scripts/check-live-schema.py --self-test        # 10 cases

WHY THIS EXISTS
---------------
`docs/reviews/architecture-review-2026-08-25.md` finding 3: **five of the six schema gates never read
a live database.** They REBUILD the schema from the spec files inside their own rolled-back
transaction — `verify-schema.sh:10`, `check-guard-coverage.py:195-206`, and the same shape in
`check-sentinel-meanings.py` and `check-vocabulary-collisions.py`. Only `check-docs.py` touches no
database at all.

So the existing suite answers *"is the SPEC internally consistent?"* and cannot answer *"did the
migration APPLY?"* — the wrong question for the one milestone whose purpose is making the spec
execute. r3 B2 named the *path* axis and the *transport* axis; this is the third, the **SUBJECT**
axis: built-from-source vs introspected-from-live.

⚠ WHY IT CHECKS FIVE KINDS AND NOT TWO
--------------------------------------
The first draft checked tables and columns. MEASURED 2026-08-25, in a rolled-back transaction:
`drop table workspaces cascade` — the fix Postgres' own HINT recommends — removes every M4 table and
column while leaving ALL SEVEN live-table triggers alive, still calling `public.workspaces`. On that
database a real signup fails with `relation "public.workspaces" does not exist` inside
`ensure_workspace_for_profile()`, so nobody can sign up — and the two-kind gate returned **exit 0**.

A gate that blesses an outage is worse than no gate. Absence must be proved across every kind M4
creates, because `drop table` removes only two of them.

FAILS IF
--------
`--expect-absent` and ANY M4 object survives in any kind; `--expect-present` and any is missing; or
the database is unreachable (exit 2 — treat as NOT RUN).
"""
from __future__ import annotations

import argparse
import subprocess
import sys

CONTAINER = "supabase_db_youtube-playlist-summaries-cloud"

# Post-ADR-0011. Counts verified against the schema, not the prose:
#   5 tables · 3 columns · 7 live-table triggers · 13 functions · 1 enum
M4_TABLES = ("workspaces", "workspace_videos", "video_generations",
             "video_artifacts", "video_artifact_sources")
M4_COLUMNS = ("playlists.workspace_id", "videos.workspace_id", "jobs.workspace_id")
# Triggers on M4's OWN tables die with `drop table`. These seven sit on LIVE tables — profiles,
# playlists, videos, jobs — whose tables survive, so nothing else removes them. They are the ones
# that turn a botched rollback into an outage.
M4_LIVE_TRIGGERS = ("profiles_ensure_workspace_trg",
                    "playlists_resolve_workspace_ins_trg", "playlists_resolve_workspace_upd_trg",
                    "videos_resolve_workspace_ins_trg", "videos_resolve_workspace_upd_trg",
                    "jobs_resolve_workspace_ins_trg", "jobs_resolve_workspace_upd_trg")
M4_FUNCTIONS = ("ensure_workspace_for_profile", "resolve_workspace_from_playlist", "record_artifact",
                "video_generations_freeze", "forbid_collecting_current",
                "video_artifacts_append_only", "video_artifacts_generation_complete",
                "video_artifact_sources_append_only", "video_artifact_sources_insert_once",
                "art_summary_has_no_source", "slot_kind", "corrections_hash_of",
                "no_corrections_hash")
M4_TYPES = ("artifact_kind",)

KINDS = ("tables", "columns", "triggers", "functions", "types")
EXPECTED = {"tables": set(M4_TABLES), "columns": set(M4_COLUMNS),
            "triggers": set(M4_LIVE_TRIGGERS), "functions": set(M4_FUNCTIONS),
            "types": set(M4_TYPES)}

# One query per kind. `\echo` markers delimit the sections; no backticks anywhere — psql performs
# shell command substitution on backquotes inside meta-command arguments, exactly as bash does
# (measured 2026-08-25: it printed `sh: public: not found` into the middle of a measurement).
CATALOG_SQL = r"""
\echo ---TABLES---
select c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace
 where n.nspname = 'public' and c.relkind = 'r';
\echo ---COLUMNS---
select table_name || '.' || column_name from information_schema.columns
 where table_schema = 'public' and column_name = 'workspace_id';
\echo ---TRIGGERS---
select t.tgname from pg_trigger t join pg_class c on c.oid = t.tgrelid
  join pg_namespace n on n.oid = c.relnamespace
 where not t.tgisinternal and n.nspname = 'public';
\echo ---FUNCTIONS---
select p.proname from pg_proc p join pg_namespace n on n.oid = p.pronamespace
 where n.nspname = 'public';
\echo ---TYPES---
select t.typname from pg_type t join pg_namespace n on n.oid = t.typnamespace
 where n.nspname = 'public' and t.typtype = 'e';
"""


def verdict(found: dict[str, set[str]], mode: str) -> bool:
    """PURE. True = pass.

    `found` maps kind -> the names actually present in the live catalog.
    absent : NOTHING of M4 may remain, in ANY kind.
    present: EVERY M4 object must be there, in every kind.
    """
    if mode == "absent":
        return all(not (found.get(k, set()) & EXPECTED[k]) for k in KINDS)
    return all(EXPECTED[k] <= found.get(k, set()) for k in KINDS)


def residue(found: dict[str, set[str]], mode: str) -> dict[str, set[str]]:
    """What is wrong, per kind — so a failure names the objects. PURE."""
    if mode == "absent":
        return {k: found.get(k, set()) & EXPECTED[k] for k in KINDS
                if found.get(k, set()) & EXPECTED[k]}
    return {k: EXPECTED[k] - found.get(k, set()) for k in KINDS
            if EXPECTED[k] - found.get(k, set())}


def parse_catalog(out: str) -> dict[str, set[str]]:
    """Split psql output on the ---KIND--- markers. PURE."""
    found: dict[str, set[str]] = {k: set() for k in KINDS}
    marker_to_kind = {"---TABLES---": "tables", "---COLUMNS---": "columns",
                      "---TRIGGERS---": "triggers", "---FUNCTIONS---": "functions",
                      "---TYPES---": "types"}
    current: str | None = None
    for line in out.splitlines():
        line = line.strip()
        if line in marker_to_kind:
            current = marker_to_kind[line]
        elif line and current:
            found[current].add(line)
    return found


def read_catalog(database: str = "postgres") -> dict[str, set[str]]:
    """Reads the LIVE database. Raises RuntimeError if it cannot be reached.

    ⚠ `--database` EXISTS SO THIS GATE CAN BE MUTATION-TESTED. This function opens its OWN
    connection, so it cannot see an uncommitted transaction in another session — which means the
    obvious "create the object in a rolled-back transaction, then run the gate" proof is impossible
    (measured; it was a real finding against an earlier draft of this gate's own plan). The only
    honest way to prove the gate goes RED is to build the state for real in a SCRATCH database and
    point the gate at it. `scripts/mutate-live-schema-check.sh` does exactly that.
    """
    p = subprocess.run(
        ["docker", "exec", "-i", CONTAINER, "psql", "-U", "postgres", "-d", database, "-tAq"],
        input=CATALOG_SQL, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or "psql failed with no message")
    return parse_catalog(p.stdout)


# ---------------------------------------------------------------- self-test
def self_test() -> int:
    cases = failures = 0

    def check(label: str, got: bool, want: bool) -> None:
        nonlocal cases, failures
        cases += 1
        ok = got == want
        print(("  ✓ " if ok else "  ✗ ") + label)
        failures += 0 if ok else 1

    none: dict[str, set[str]] = {k: set() for k in KINDS}
    all_: dict[str, set[str]] = {k: set(EXPECTED[k]) for k in KINDS}

    check("absent passes when nothing remains", verdict(none, "absent"), True)
    check("absent FAILS when a table survives",
          verdict({**none, "tables": {"workspaces"}}, "absent"), False)
    # ⭐ THE CASE THAT MATTERS — the measured post-cascade state. No tables, no columns, but the
    # live-table triggers alive and calling a dropped table. Signup is dead here, and the two-kind
    # version of this gate returned exit 0.
    check("absent FAILS on the cascade residue (triggers alive, tables gone)",
          verdict({**none, "triggers": {"profiles_ensure_workspace_trg"}}, "absent"), False)
    check("absent FAILS when a function survives — a wrong drop signature is a SILENT no-op",
          verdict({**none, "functions": {"record_artifact"}}, "absent"), False)
    check("absent FAILS when the enum survives",
          verdict({**none, "types": {"artifact_kind"}}, "absent"), False)
    check("absent IGNORES unrelated objects",
          verdict({**none, "tables": {"profiles", "playlists"}}, "absent"), True)
    check("present passes when complete", verdict(all_, "present"), True)
    check("present FAILS on a partial apply (one table)",
          verdict({**all_, "tables": {"workspaces"}}, "present"), False)
    check("present FAILS when the triggers are missing",
          verdict({**all_, "triggers": set()}, "present"), False)
    check("residue NAMES the surviving object",
          residue({**none, "functions": {"slot_kind"}}, "absent") == {"functions": {"slot_kind"}},
          True)

    print(f"\n{cases - failures}/{cases} self-test cases passed")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--expect-absent", action="store_true")
    g.add_argument("--expect-present", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--database", default="postgres",
                    help="target database; used by the mutation harness to point at a "
                         "scratch DB, because this gate opens its own connection and so "
                         "cannot be proved red inside someone else's transaction")
    a = ap.parse_args()

    if a.self_test:
        return self_test()
    if not (a.expect_absent or a.expect_present):
        print("CANNOT RUN — pass --expect-absent or --expect-present. There is no default: a gate\n"
              "that guesses which polarity to assert is how this plan shipped an unsatisfiable\n"
              "milestone twice. Treat this as NOT RUN.", file=sys.stderr)
        return 2

    mode = "absent" if a.expect_absent else "present"
    try:
        found = read_catalog(a.database)
    except (RuntimeError, FileNotFoundError) as e:
        print(f"CANNOT RUN — could not read the live catalog: {e}\nTreat this as NOT RUN.",
              file=sys.stderr)
        return 2

    if verdict(found, mode):
        print(f"live schema: M4 is {mode.upper()} as expected "
              f"({len(EXPECTED['tables'])} tables, {len(EXPECTED['columns'])} columns, "
              f"{len(EXPECTED['triggers'])} live triggers, {len(EXPECTED['functions'])} functions, "
              f"{len(EXPECTED['types'])} type)")
        return 0

    bad = residue(found, mode)
    word = "SURVIVING" if mode == "absent" else "MISSING"
    print(f"FAILED — expected M4 {mode.upper()}, but these objects are {word}:\n", file=sys.stderr)
    for kind in KINDS:
        if kind in bad:
            for name in sorted(bad[kind]):
                print(f"  ✗ {kind[:-1]}: {name}", file=sys.stderr)
    if mode == "absent" and "triggers" in bad:
        print("\n⚠ A SURVIVING LIVE-TABLE TRIGGER MEANS THE PRODUCT IS DOWN, not merely untidy — it\n"
              "  still calls tables that are gone. Signup, playlist creation and enqueue all fail.\n"
              "  This is the state `drop table … cascade` produces. Do not use cascade in 0028.",
              file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
