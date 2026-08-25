"""ONE description of what "the M4 object set" means, shared by the generator and the gate.

Both `gen-m4-manifest.py` (which derives the manifest by EXECUTION) and `check-live-schema.py`
(which compares a live database to it) import this. A second copy of the catalog query would be a
second definition of the thing they are supposed to agree about.

An object is one string, `kind:name`, so set algebra is the whole comparison:

    present : MANIFEST ⊆ live
    absent  : MANIFEST ∩ live = ∅

⟳ WHY THIS EXISTS — r3 B2 (claude), 2026-08-25. The gate used to carry five hand-written tuples
naming **29 of 161** objects (18%): zero views, zero indexes, zero policies, zero constraints,
3 of 70 columns, 7 of 14 triggers. MEASURED: it reported "M4 is PRESENT as expected", exit 0, over a
database with ALL SEVEN of M4's own-table triggers dropped — every append-only, freeze and
immutability guard gone — because `M4_LIVE_TRIGGERS` only ever named the seven on *live* tables.
The plan called it "the only instrument that can confirm M4-β happened".

Option (a) was chosen by the user: derive the manifest from what the schema actually creates.
"""
from __future__ import annotations

import subprocess

CONTAINER = "supabase_db_youtube-playlist-summaries-cloud"

# ⚠ NO BACKTICKS ANYWHERE IN THIS STRING. psql performs shell command substitution on backquotes
# inside meta-command arguments, exactly as bash does (measured 2026-08-25: it printed
# `sh: public: not found` into the middle of a measurement).
#
# Every kind M4 can create. `pg_get_function_identity_arguments` is used rather than the bare name
# because that is the form `drop function` needs, and a wrong signature is a SILENT no-op.
CATALOG_SQL = r"""
select 'table:' || c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace
 where n.nspname = 'public' and c.relkind = 'r'
union all
select 'view:' || c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace
 where n.nspname = 'public' and c.relkind in ('v', 'm')
union all
select 'col:' || table_name || '.' || column_name from information_schema.columns
 where table_schema = 'public'
union all
select 'trg:' || c.relname || '.' || t.tgname from pg_trigger t
  join pg_class c on c.oid = t.tgrelid
  join pg_namespace n on n.oid = c.relnamespace
 where not t.tgisinternal and n.nspname = 'public'
union all
select 'fn:' || p.proname || '(' || pg_get_function_identity_arguments(p.oid) || ')'
  from pg_proc p join pg_namespace n on n.oid = p.pronamespace where n.nspname = 'public'
union all
select 'type:' || t.typname from pg_type t join pg_namespace n on n.oid = t.typnamespace
 where n.nspname = 'public' and t.typtype = 'e'
union all
select 'idx:' || indexname from pg_indexes where schemaname = 'public'
union all
select 'pol:' || tablename || '.' || policyname from pg_policies where schemaname = 'public'
union all
select 'con:' || conrelid::regclass::text || '.' || conname from pg_constraint c
  join pg_namespace n on n.oid = c.connamespace where n.nspname = 'public'
order by 1;
"""

KIND_ORDER = ("table", "view", "col", "trg", "fn", "type", "idx", "pol", "con")
# singular, plural — because "12 indexs · 5 policys" is what naive +s produced, and a summary line
# is the part of a gate a human actually reads.
KIND_LABEL = {"table": ("table", "tables"), "view": ("view", "views"),
              "col": ("column", "columns"), "trg": ("trigger", "triggers"),
              "fn": ("function", "functions"), "type": ("type", "types"),
              "idx": ("index", "indexes"), "pol": ("policy", "policies"),
              "con": ("constraint", "constraints")}


def read_catalog(database: str = "postgres", container: str = CONTAINER) -> set[str]:
    """The live catalog as a set of `kind:name`. Raises RuntimeError if unreachable."""
    p = subprocess.run(
        ["docker", "exec", "-i", container, "psql", "-U", "postgres", "-d", database, "-tAq"],
        input=CATALOG_SQL, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or "psql failed with no message")
    return {ln.strip() for ln in p.stdout.splitlines() if ln.strip()}


def by_kind(objects: set[str]) -> dict[str, list[str]]:
    """Group `kind:name` strings for reporting. PURE."""
    out: dict[str, list[str]] = {k: [] for k in KIND_ORDER}
    for o in sorted(objects):
        kind = o.split(":", 1)[0]
        out.setdefault(kind, []).append(o)
    return {k: v for k, v in out.items() if v}


def label(kind: str, n: int) -> str:
    """Human name for a kind, correctly pluralised. PURE."""
    sing, plur = KIND_LABEL.get(kind, (kind, kind + "s"))
    return sing if n == 1 else plur


def summarise(objects: set[str]) -> str:
    """One line: how many of each kind. PURE."""
    return " · ".join(f"{len(v)} {label(k, len(v))}" for k, v in by_kind(objects).items())
