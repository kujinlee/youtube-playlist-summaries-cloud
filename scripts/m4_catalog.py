"""ONE description of what "the M4 object set" means, shared by the generator and the gate.

Both `gen-m4-manifest.py` (which derives the manifest by EXECUTION) and `check-live-schema.py`
(which compares a live database to it) import this. A second copy of the catalog query would be a
second definition of the thing they are supposed to agree about.

An object is one string, `kind:name@digest`, so set algebra is the whole comparison:

    present : MANIFEST ⊆ live
    absent  : MANIFEST ∩ live = ∅

⛔ WHY THE DIGEST — r4 B1 (claude), coordinator-verified 2026-08-25
--------------------------------------------------------------------
The previous version emitted `kind:name` and nothing else, so the gate answered *"does an object
with this name exist?"* and never *"is the guard in force?"* MEASURED, on a database with M4 fully
applied and then sabotaged three different ways, the gate printed
**"M4 is PRESENT as expected — checked all 161 objects", exit 0** every time:

  1. `alter table … disable trigger` on all seven own-table guards (`tgenabled='D'`, count 7);
  2. `create or replace` of two guard function bodies with a bare `return new`;
  3. `art_dig_has_span` dropped and re-added as `check (true)`.

⚠ **The mutation harness was one word from catching it and did not.** It proves the gate by
*dropping* guards; `disable` leaves every name intact. When the only way you can express a defect is
deletion, you are testing existence, not behaviour.

r3 B2 was read as a COUNTING problem — 29 names of 161 — and fixed by widening the count. It was a
PREDICATE problem: name-matching cannot see an inert rule. So each object now carries an `md5` of
its **definition**, and the definition is what the comparison is over.

WHAT EACH DIGEST COVERS
-----------------------
    trigger     pg_get_triggerdef + tgenabled   -> catches DISABLE and any redefinition
    function    prosrc                          -> catches `create or replace` with a new body
    constraint  pg_get_constraintdef            -> catches a predicate weakened to `check (true)`
    view        pg_get_viewdef                  -> catches a rewritten ranking
    index       indexdef                        -> catches a uniqueness or predicate change
    policy      cmd + roles + qual + with_check -> catches a widened RLS rule
    column      type + nullability + default    -> catches a dropped NOT NULL
    table/type  existence / enum labels
"""
from __future__ import annotations

import os
import re
import subprocess

CONTAINER = "supabase_db_youtube-playlist-summaries-cloud"

# ⚠ NO BACKTICKS ANYWHERE IN THIS STRING. psql performs shell command substitution on backquotes
# inside meta-command arguments, exactly as bash does (measured 2026-08-25).
CATALOG_SQL = r"""
select 'table:' || c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace
 where n.nspname = 'public' and c.relkind = 'r'
union all
select 'view:' || c.relname || '@' || md5(pg_get_viewdef(c.oid))
  from pg_class c join pg_namespace n on n.oid = c.relnamespace
 where n.nspname = 'public' and c.relkind in ('v', 'm')
union all
select 'col:' || table_name || '.' || column_name || '@' ||
       md5(data_type || is_nullable || coalesce(column_default, ''))
  from information_schema.columns where table_schema = 'public'
union all
-- tgenabled is the whole point: 'O' enabled, 'D' DISABLED. A disabled trigger keeps its name.
select 'trg:' || c.relname || '.' || t.tgname || '@' ||
       md5(pg_get_triggerdef(t.oid) || t.tgenabled::text)
  from pg_trigger t join pg_class c on c.oid = t.tgrelid
  join pg_namespace n on n.oid = c.relnamespace
 where not t.tgisinternal and n.nspname = 'public'
union all
select 'fn:' || p.proname || '(' || pg_get_function_identity_arguments(p.oid) || ')' || '@' ||
       md5(coalesce(p.prosrc, ''))
  from pg_proc p join pg_namespace n on n.oid = p.pronamespace where n.nspname = 'public'
union all
select 'type:' || t.typname || '@' || md5(coalesce(
         (select string_agg(e.enumlabel, ',' order by e.enumsortorder)
            from pg_enum e where e.enumtypid = t.oid), ''))
  from pg_type t join pg_namespace n on n.oid = t.typnamespace
 where n.nspname = 'public' and t.typtype = 'e'
union all
select 'idx:' || indexname || '@' || md5(indexdef) from pg_indexes where schemaname = 'public'
union all
select 'pol:' || tablename || '.' || policyname || '@' ||
       md5(cmd || coalesce(roles::text, '') || coalesce(qual, '') || coalesce(with_check, ''))
  from pg_policies where schemaname = 'public'
union all
select 'con:' || conrelid::regclass::text || '.' || conname || '@' ||
       md5(pg_get_constraintdef(c.oid))
  from pg_constraint c join pg_namespace n on n.oid = c.connamespace where n.nspname = 'public'
order by 1;
"""

KIND_ORDER = ("table", "view", "col", "trg", "fn", "type", "idx", "pol", "con")
KIND_LABEL = {"table": ("table", "tables"), "view": ("view", "views"),
              "col": ("column", "columns"), "trg": ("trigger", "triggers"),
              "fn": ("function", "functions"), "type": ("type", "types"),
              "idx": ("index", "indexes"), "pol": ("policy", "policies"),
              "con": ("constraint", "constraints")}


def read_only_url() -> str | None:
    """The production READ-ONLY URL, from the environment or `.env.local`.

    Same source `check-anon-exposure.py` uses. Read-only by construction: `claude_ro` holds no write
    grant on any public table.
    """
    if os.environ.get("CLAUDE_RO_DATABASE_URL"):
        return os.environ["CLAUDE_RO_DATABASE_URL"]
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env = os.path.join(repo, ".env.local")
    if os.path.exists(env):
        with open(env) as f:
            for line in f:
                m = re.match(r"^CLAUDE_RO_DATABASE_URL=(.*)$", line.strip())
                if m:
                    return m.group(1).strip().strip('"').strip("'")
    return None


def psql_cmd(database: str = "postgres", url: str | None = None,
             container: str = CONTAINER) -> list[str]:
    """The command that reaches a target. PURE (builds a list, runs nothing).

    ⟳ r4 B2 (claude) — THE GATE COULD NOT REACH PRODUCTION AT ALL. It hard-coded
    `docker exec … -d <database>`, which names a database INSIDE the local container, while the plan
    said to run it "pointed at prod". Run literally after M4-β it would have read the LAPTOP — which
    by then has 0027 applied — printed PASS, and proved nothing about production.

    The remote form uses the container as a psql CLIENT against a remote URL: the same one mechanism
    `check-anon-exposure.py` already uses, deliberately not a second driver.
    """
    if url:
        return ["docker", "exec", "-i", "-e", f"PGU={url}", container,
                "bash", "-c", 'psql "$PGU" -tAq -v ON_ERROR_STOP=1']
    return ["docker", "exec", "-i", container, "psql", "-U", "postgres", "-d", database,
            "-tAq", "-v", "ON_ERROR_STOP=1"]


def read_catalog(database: str = "postgres", url: str | None = None,
                 container: str = CONTAINER) -> set[str]:
    """The live catalog as a set of `kind:name@digest`. Raises RuntimeError if unreachable."""
    p = subprocess.run(psql_cmd(database, url, container),
                       input=CATALOG_SQL, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or p.stdout.strip() or "psql failed with no message")
    return {ln.strip() for ln in p.stdout.splitlines() if ln.strip()}


def name_of(obj: str) -> str:
    """`kind:name@digest` -> `kind:name`. PURE. Used only for REPORTING, never for the verdict."""
    return obj.split("@", 1)[0]


def by_kind(objects: set[str]) -> dict[str, list[str]]:
    """Group `kind:name@digest` strings for reporting. PURE."""
    out: dict[str, list[str]] = {k: [] for k in KIND_ORDER}
    for o in sorted(objects):
        out.setdefault(o.split(":", 1)[0], []).append(o)
    return {k: v for k, v in out.items() if v}


def label(kind: str, n: int) -> str:
    """Human name for a kind, correctly pluralised. PURE."""
    sing, plur = KIND_LABEL.get(kind, (kind, kind + "s"))
    return sing if n == 1 else plur


def summarise(objects: set[str]) -> str:
    """One line: how many of each kind. PURE."""
    return " · ".join(f"{len(v)} {label(k, len(v))}" for k, v in by_kind(objects).items())
