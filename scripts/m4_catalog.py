"""ONE description of what "the M4 object set" means, shared by the generator and the gate.

Both `gen-m4-manifest.py` (which derives the manifest by EXECUTION) and `check-live-schema.py`
(which compares a live database to it) import this. A second copy of the catalog query would be a
second definition of the thing they are supposed to agree about.

An object is one string, `kind:name@digest`. The comparison is set algebra:

    present : MANIFEST ⊆ live                     (matched by name@digest)
    absent  : no live object shares a manifest NAME   (matched by name — see check-live-schema.py B1)

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

⛔⛔ WHY THE DIGEST COVERS ENFORCEMENT STATE AND NOT ONLY DEFINITIONS — r5 B2 (codex + claude)
-----------------------------------------------------------------------------------------------
r4's fix moved the predicate from *"a name exists"* to *"its definition matches"*. Those are not the
same as *"the rule is in force"*, and the gap is exactly one Postgres flag wide. MEASURED on a fully
applied M4 database, EIGHT sabotages, every one **exit 0, "M4 is PRESENT as expected"**:

    alter table … disable row level security         relrowsecurity      → policies inert, digest identical
    alter table … no force row level security        relforcerowsecurity → owner bypasses every policy
    alter function … security invoker                prosecdef           → guard runs as the caller
    alter function … reset search_path               proconfig           → search-path hijack on a SECURITY DEFINER
    alter function … volatile                        provolatile         → planner may re-evaluate
    revoke select … ; grant insert to anon           relacl              → the table opens up
    alter view … set (security_invoker = true)       reloptions          → the view stops filtering
    policy recreated `as restrictive`                polpermissive       → AND/OR flips

#1 is the one to read twice: disabling RLS does not touch a single policy row, and the policy rows
were the entire policy input. **Byte-identical digest, five owner-scoping policies reported as
verified, none of them enforcing.** That is `tgenabled='D'` one layer out — in the layer r4's own fix
did not reach.

So the rule for this query is now stated as a question, because a list of columns invites the same
mistake a third time:

  ⭐ **"What does this SELECT not select?"** Every catalog column that decides whether a rule
     EXECUTES belongs in the digest. A column that merely describes the rule's text does not,
     because `pg_get_*def` already carries it.

`check-live-schema.py --self-test` asserts each column below still appears here, so deleting one is
a red test rather than a silently narrower gate.

WHAT EACH DIGEST COVERS
-----------------------
    table       RLS on/forced · ACL · persistence
    view        pg_get_viewdef · reloptions (security_invoker, security_barrier) · ACL
    column      exact type (format_type) · NOT NULL · default · identity · generated
    trigger     pg_get_triggerdef + tgenabled   -> DISABLE, timing, level, WHEN, deferrability
    function    prosrc · prosecdef · proconfig · provolatile · prokind · ACL
    constraint  pg_get_constraintdef            -> renders NOT VALID and DEFERRABLE (verified r5)
    index       pg_get_indexdef · indisvalid · indisready · indislive
    policy      cmd · permissive · roles · using · with check
    type        enum labels in order

DELIBERATELY EXCLUDED, with the reason (an unexplained omission is how B2 happened):
    owner (relowner/proowner)  legitimately differs between a container and a managed platform;
                               `relacl`+`prosecdef` already cover what ownership can do here.
    comments, statistics       cannot change whether a rule executes.
    convalidated               `pg_get_constraintdef` renders `NOT VALID` (MEASURED r5).
"""
from __future__ import annotations

import os
import re
import subprocess

CONTAINER = "supabase_db_youtube-playlist-summaries-cloud"

# ⭐ EVERY ENFORCEMENT COLUMN, ASSERTED BY THE SELF-TEST TO STILL BE IN `CATALOG_SQL`.
# r5 B2 was possible because nothing named the properties the digest was supposed to cover, so
# "we added the digest" and "the digest covers enforcement" could both be believed at once.
#
# ⚠ THIS LIST IS NOT THE MECHANISM. r6 proved it cannot be: `attacl` and `proisstrict` were both
# missing, and both were missing for the same reason — the list was assembled from the sabotages
# somebody had already run. `scripts/check-catalog-coverage.py` is the mechanism: it enumerates the
# columns each catalog ACTUALLY HAS, straight from `pg_attribute`, and fails unless every one is
# either digested or on a written EXCLUDED list with a reason. This tuple is the fast in-process
# assertion; that script is the one that can find a column nobody thought of.
ENFORCEMENT_COLUMNS = (
    "relrowsecurity", "relforcerowsecurity", "relpersistence", "reloptions", "relhasrules",
    "relreplident",
    "prosecdef", "proconfig", "provolatile", "prokind", "proisstrict", "proleakproof",
    "proparallel", "proretset", "prosqlbody",
    "polpermissive", "indisvalid", "indisready", "indislive", "indisprimary", "indisunique",
    "indimmediate", "indisexclusion",
    "attnotnull", "attidentity", "attgenerated", "attstorage", "attcompression",
    "tgenabled",
    # privileges are digested as EFFECTIVE ACCESS, never as ACL text — see PRIVILEGE_NOTE.
    # `has_any_column_privilege` rides in the TABLE digest, which is what catches r6 B2's
    # column-level `grant insert (blob_key) … to anon`. There is deliberately no PER-COLUMN
    # privilege digest — see the `col:` branch for the measurement that ruled it out.
    "has_table_privilege", "has_any_column_privilege", "has_function_privilege",
)

# ⛔⛔ WHY PRIVILEGES ARE DIGESTED AS EFFECTIVE ACCESS AND NOT AS `relacl`/`proacl`/`attacl` TEXT.
# ⟳ r6 B1 (claude), coordinator-verified against PRODUCTION 2026-08-25.
#
# r5 put `relacl` and `proacl` in the digest. The manifest is derived from a
# `pg_dump --no-owner --no-privileges` clone, so it records the ACL Postgres assigns when NO default
# privileges exist. **No deployed database is in that state.** MEASURED, same query, two subjects:
#
#     local container, public tables, owner postgres :  anon=Dxtm
#     PRODUCTION,      public tables, owner postgres :  anon=arwdDxtm , claude_ro=r
#     local roles                                    :  anon, authenticated, service_role
#     production roles                               :  anon, authenticated, service_role, CLAUDE_RO
#
# `claude_ro` does not exist in the container at all, so **no manifest generated on any developer
# machine can ever contain that grantee.** On a production-shaped database the reviewer measured 20
# objects reported as *"EXIST BUT DO NOT MATCH THEIR DEFINITION"*, and called 20 a lower bound.
#
# The plan's Step 7 runs `--prod --expect-present` immediately after an irreversible
# `supabase db push --linked`. With ACL text in the digest, that gate prints *"A PARTIALLY APPLIED M4
# IS THE DANGEROUS STATE"* over a migration that applied perfectly — and the documented response to
# that message is the rollback. **The gate built to prevent a bad cutover would argue for undoing a
# good one.**
#
# ⭐ The fix is not to drop privileges from the digest — r5's `grant insert to anon` case is real.
# It is to digest **what the spec asserts control over**: the EFFECTIVE access of the principals the
# schema actually revokes from and grants to. MEASURED to be environment-invariant, which is the
# whole point:
#
#     grantee        privilege             --no-privileges clone   production-shaped
#     anon           SELECT/INSERT/UPDATE/DELETE      r---              r---     ✅ agree
#     authenticated  SELECT/INSERT/UPDATE/DELETE      r---              r---     ✅ agree
#     service_role   SELECT/INSERT/UPDATE/DELETE      arwd              arwd     ✅ agree
#     (anon TRUNCATE/REFERENCES/TRIGGER/MAINTAIN      -                 Dxtm     ✗ diverge — excluded)
#
# The privileges that diverge are exactly the ones the M4 spec never mentions, and they are already
# covered by `check-anon-exposure.py`, which ratchets them against a recorded per-environment
# baseline — the right home, because it is environment-aware and this manifest cannot be.
#
# ⚠ `service_role` is deliberately EXCLUDED from the FUNCTION grantee list: production's default
# function ACL grants it EXECUTE and the container's does not (measured above), and the spec revokes
# only from `public, anon, authenticated`. Digesting an EXECUTE grant the spec never claimed to
# control would reintroduce this whole finding for twelve functions.
PRIVILEGE_NOTE = "effective access for the principals the spec revokes from and grants to"

# The principals whose access M4's own `grant`/`revoke` statements control.
REL_GRANTEES = ("public", "anon", "authenticated", "service_role")
FN_GRANTEES = ("public", "anon", "authenticated")
REL_PRIVS = ("SELECT", "INSERT", "UPDATE", "DELETE")

# ⚠ NO BACKTICKS ANYWHERE IN THIS STRING. psql performs shell command substitution on backquotes
# inside meta-command arguments, exactly as bash does (measured 2026-08-25).
#
# ⛔ TWO SESSION SETTINGS, BOTH LOad-BEARING — do not "tidy" them away:
#
# 1. `set search_path = pg_catalog` — ⟳ r5 M2 (claude). `conrelid::regclass::text` and
#    `format_type()` render RELATIVE TO THE SESSION'S search_path. MEASURED, same database, same
#    query, two sessions: `con:public.video_artifacts.art_dig_has_span` vs
#    `con:video_artifacts.art_dig_has_span` — all 38 constraints (24% of the manifest) change
#    identity. The manifest is generated as the container's `postgres`; `--prod` connects as
#    `claude_ro`, whose search_path is set by whoever created the role. In present mode that
#    mismatch is loud; in absent mode it was silent. **An identity key must not depend on how you
#    connected.** Schema names are therefore taken from the JOIN, never from a rendering.
# 2. `set session characteristics as transaction read only` — ⟳ r5 M5 (claude) / r5 H (codex).
#    "Read-only" used to be a LABEL derived from whether an env var was set. This is the mechanism:
#    the session cannot write, whoever it turns out to be connected as.
SESSION_SQL = """
set session characteristics as transaction read only;
set search_path = pg_catalog;
"""

def _guard(grantee: str, body: str) -> str:
    """`body`, or the literal 'ABSENT' when the role does not exist here. PURE.

    A role missing in one environment must CHANGE the digest, loudly, rather than be skipped — that
    is the difference between "this database grants nothing to anon" and "anon is not a thing here".
    `public` is a pseudo-role: `to_regrole('public')` is NULL but the privilege functions accept it.
    """
    if grantee == "public":
        return body
    return f"case when to_regrole('{grantee}') is null then 'ABSENT' else {body} end"


def _rel_priv(rel: str) -> str:
    """SQL expression: EFFECTIVE access on relation `rel`, for the principals the spec controls.

    Replaces `relacl`/`attacl` TEXT, which cannot agree between a `--no-privileges` clone and any
    deployed database (r6 B1). `has_any_column_privilege` is what makes a COLUMN-level grant
    visible: `grant insert (blob_key) on video_artifacts to anon` moved no ACL the old query read,
    so the 161-object digest was byte-identical while anon gained INSERT (r6 B2, measured).
    """
    parts = []
    for g in REL_GRANTEES:
        tbl = " || ".join(f"has_table_privilege('{g}', {rel}, '{p}')::text" for p in REL_PRIVS)
        col = " || ".join(f"has_any_column_privilege('{g}', {rel}, '{p}')::text"
                          for p in ("SELECT", "INSERT", "UPDATE"))
        parts.append(f"'{g}=' || " + _guard(g, f"({tbl} || '/' || {col})"))
    return "(" + " || ',' || ".join(parts) + ")"


def _fn_priv(fn: str) -> str:
    """SQL expression: effective EXECUTE, for the principals the spec revokes from. PURE.

    ⚠ `service_role` is DELIBERATELY ABSENT. Production's default function ACL grants it EXECUTE and
    the container's does not (measured), and the spec revokes only from `public, anon,
    authenticated`. Digesting a grant the spec never claimed to control would reintroduce r6 B1 for
    twelve functions.
    """
    parts = [f"'{g}=' || " + _guard(g, f"has_function_privilege('{g}', {fn}, 'EXECUTE')::text")
             for g in FN_GRANTEES]
    return "(" + " || ',' || ".join(parts) + ")"


def _rules(rel: str) -> str:
    """SQL expression: the rewrite RULES attached to `rel`. PURE.

    ⟳ r6 H1: `create rule swallow as on insert to video_artifacts do instead nothing` made every
    artifact write vanish — MEASURED, 0 rows after an insert — with the digest byte-identical,
    because `pg_rewrite` was not read at all. Present mode ignores EXTRA objects by design, and r5
    recorded that as correct because "a real database legitimately holds more than M4". True of most
    extra objects; **false of an object ATTACHED to a manifest relation**, which is not an addition
    to the database but a modification of that relation.
    """
    return (f"coalesce((select string_agg(r.rulename || ':' || r.ev_type::text || "
            f"r.is_instead::text, ',' order by r.rulename) from pg_rewrite r "
            f"where r.ev_class = {rel} and r.rulename <> '_RETURN'), '')")


CATALOG_SQL = SESSION_SQL + r"""
select 'table:' || c.relname || '@' || md5(
         c.relrowsecurity::text || c.relforcerowsecurity::text || c.relpersistence::text ||
         c.relreplident::text || c.relhasrules::text || c.relispartition::text ||
         coalesce((select string_agg(o, ',' order by o) from unnest(c.reloptions) o), '') ||
         """ + _rel_priv("c.oid") + " || " + _rules("c.oid") + r""")
  from pg_class c join pg_namespace n on n.oid = c.relnamespace
 where n.nspname = 'public' and c.relkind = 'r'
union all
select 'view:' || c.relname || '@' || md5(
         pg_get_viewdef(c.oid) ||
         coalesce((select string_agg(o, ',' order by o) from unnest(c.reloptions) o), '') ||
         """ + _rel_priv("c.oid") + " || " + _rules("c.oid") + r""")
  from pg_class c join pg_namespace n on n.oid = c.relnamespace
 where n.nspname = 'public' and c.relkind in ('v', 'm')
union all
-- ⟳ r5 M3 (claude): this read information_schema.columns, which by SQL-standard definition shows
-- only columns the CURRENT USER holds a privilege on. MEASURED: 165 columns as `postgres`, 12 as a
-- role with SELECT on one table. Columns are 43% of the manifest, and the failure was asymmetric in
-- the dangerous direction — absent-mode over prod passed vacuously for every column claude_ro could
-- not see. pg_attribute is not privilege-filtered. format_type also fixes r5 L3: information_schema
-- reports every enum as `USER-DEFINED` and every array as `ARRAY`, carrying no length or precision,
-- so re-typing a column to a DIFFERENT enum was invisible.
select 'col:' || c.relname || '.' || a.attname || '@' || md5(
         format_type(a.atttypid, a.atttypmod) || a.attnotnull::text ||
         coalesce(pg_get_expr(d.adbin, d.adrelid), '') ||
         a.attidentity::text || a.attgenerated::text ||
         a.attstorage::text || a.attcompression::text ||
         coalesce((select string_agg(o, ',' order by o) from unnest(a.attoptions) o), '') ||
         -- ⚠ NO PER-COLUMN PRIVILEGES HERE, and that is a measured decision, not an omission.
         -- M4 adds columns to PRE-EXISTING tables (`videos`, `playlists`, `jobs`), and a column's
         -- effective access is inherited from its table. Those tables' ACLs come from migrations
         -- 0001-0026, which the manifest's `--no-privileges` baseline strips — so digesting them
         -- here made `col:jobs.workspace_id` and two siblings mismatch on every real database
         -- (MEASURED). A COLUMN-level grant on an M4 table is still caught: `has_any_column_privilege`
         -- rides in that table's own digest, which is where r6 B2's `grant insert (blob_key)` lands.
         '')
  from pg_attribute a
  join pg_class c on c.oid = a.attrelid
  join pg_namespace n on n.oid = c.relnamespace
  left join pg_attrdef d on d.adrelid = a.attrelid and d.adnum = a.attnum
 where n.nspname = 'public' and a.attnum > 0 and not a.attisdropped
   and c.relkind in ('r', 'v', 'm', 'p', 'f')
union all
-- tgenabled is the whole point: 'O' enabled, 'D' DISABLED. A disabled trigger keeps its name.
select 'trg:' || c.relname || '.' || t.tgname || '@' ||
       md5(pg_get_triggerdef(t.oid) || t.tgenabled::text)
  from pg_trigger t join pg_class c on c.oid = t.tgrelid
  join pg_namespace n on n.oid = c.relnamespace
 where not t.tgisinternal and n.nspname = 'public'
union all
-- ⟳ r6 B (codex): `proisstrict` was missing, and `alter function record_artifact(…) strict` passed
-- the gate at exit 0. A STRICT function RETURNS NULL WITHOUT EXECUTING ITS BODY whenever any
-- argument is NULL, so the paid write silently does not happen. Every pg_proc column that decides
-- how or whether the body runs is now here; `check-catalog-coverage.py` enumerates the rest.
select 'fn:' || p.proname || '(' || pg_get_function_identity_arguments(p.oid) || ')' || '@' ||
       md5(coalesce(p.prosrc, '') || coalesce(p.prosqlbody::text, '') ||
           p.prosecdef::text || p.provolatile::text || p.prokind::text ||
           p.proisstrict::text || p.proleakproof::text || p.proparallel::text ||
           p.proretset::text || format_type(p.prorettype, null) || l.lanname ||
           coalesce(array_to_string(p.proconfig, ','), '') ||
           """ + _fn_priv("p.oid") + r""")
  from pg_proc p join pg_namespace n on n.oid = p.pronamespace
  join pg_language l on l.oid = p.prolang where n.nspname = 'public'
union all
select 'type:' || t.typname || '@' || md5(coalesce(
         (select string_agg(e.enumlabel, ',' order by e.enumsortorder)
            from pg_enum e where e.enumtypid = t.oid), ''))
  from pg_type t join pg_namespace n on n.oid = t.typnamespace
 where n.nspname = 'public' and t.typtype = 'e'
union all
select 'idx:' || i.relname || '@' || md5(
         pg_get_indexdef(i.oid) || x.indisvalid::text || x.indisready::text || x.indislive::text ||
         x.indisunique::text || x.indisprimary::text || x.indisexclusion::text ||
         x.indimmediate::text || x.indnullsnotdistinct::text)
  from pg_index x join pg_class i on i.oid = x.indexrelid
  join pg_namespace n on n.oid = i.relnamespace where n.nspname = 'public'
union all
select 'pol:' || c.relname || '.' || pol.polname || '@' || md5(
         pol.polcmd::text || pol.polpermissive::text ||
         coalesce((select string_agg(r.rolname, ',' order by r.rolname)
                     from pg_roles r where r.oid = any (pol.polroles)), 'public') ||
         coalesce(pg_get_expr(pol.polqual, pol.polrelid), '') ||
         coalesce(pg_get_expr(pol.polwithcheck, pol.polrelid), ''))
  from pg_policy pol join pg_class c on c.oid = pol.polrelid
  join pg_namespace n on n.oid = c.relnamespace where n.nspname = 'public'
union all
select 'con:' || rel.relname || '.' || con.conname || '@' || md5(pg_get_constraintdef(con.oid))
  from pg_constraint con
  join pg_class rel on rel.oid = con.conrelid
  join pg_namespace n on n.oid = con.connamespace where n.nspname = 'public'
order by 1;
"""

# ⟳ r5 M5 (claude) / r5 H (codex): the subject line said "PRODUCTION (read-only claude_ro)" purely
# because an env var was set. MEASURED: pointed at a LOCAL scratch database as the `postgres` role,
# the gate printed exactly that. Given that r4 B2 was the gate reading the laptop while claiming
# production, a label that cannot be wrong in the safe direction is worth one extra round trip.
IDENTITY_SQL = SESSION_SQL + """
select current_user || '|' || current_database() || '|' ||
       coalesce(host(inet_server_addr()), 'local-socket') || '|' ||
       current_setting('transaction_read_only');
"""

KIND_ORDER = ("table", "view", "col", "trg", "fn", "type", "idx", "pol", "con")
KIND_LABEL = {"table": ("table", "tables"), "view": ("view", "views"),
              "col": ("column", "columns"), "trg": ("trigger", "triggers"),
              "fn": ("function", "functions"), "type": ("type", "types"),
              "idx": ("index", "indexes"), "pol": ("policy", "policies"),
              "con": ("constraint", "constraints")}


def read_only_url() -> str | None:
    """The production READ-ONLY URL, from the environment or `.env.local`.

    ⟳ r5 M4 (claude): this is now the ONE implementation. `check-anon-exposure.py` imports it rather
    than carrying its own, which had drifted in three ways — it matched unstripped lines (so an
    indented assignment was missed), stripped double quotes but not single, and returned `None`
    where this returned `""`. Two readers of one config value that disagree about which values exist
    is `check-vocabulary-collisions.py`'s own subject, one layer below where that script looks.
    """
    if os.environ.get("CLAUDE_RO_DATABASE_URL"):
        return os.environ["CLAUDE_RO_DATABASE_URL"]
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env = os.path.join(repo, ".env.local")
    if os.path.exists(env):
        with open(env) as f:
            for line in f:
                m = re.match(r"^\s*(?:export\s+)?CLAUDE_RO_DATABASE_URL=(.*)$", line.rstrip("\n"))
                if m:
                    v = m.group(1).strip()
                    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                        v = v[1:-1]
                    return v or None
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

    ⟳ r5 L1 (claude) / r5 H (codex) — THE URL NO LONGER APPEARS IN ARGV. It used to be passed as
    `-e PGU=<url>`, and argv is world-readable: MEASURED, `ps` showed the full URL including the
    password. `docker exec -e PGU` with NO `=value` takes the value from the calling process's
    environment, so the secret travels through `psql_env()` instead and `ps` shows only the name.
    """
    if url:
        return ["docker", "exec", "-i", "-e", "PGU", container,
                "bash", "-c", 'psql "$PGU" -tAq -v ON_ERROR_STOP=1']
    return ["docker", "exec", "-i", container, "psql", "-U", "postgres", "-d", database,
            "-tAq", "-v", "ON_ERROR_STOP=1"]


def psql_env(url: str | None) -> dict[str, str] | None:
    """The environment `psql_cmd`'s remote form expects, or None for the local form. PURE."""
    if not url:
        return None
    return {**os.environ, "PGU": url}


def _run(sql: str, database: str, url: str | None, container: str) -> str:
    p = subprocess.run(psql_cmd(database, url, container), input=sql,
                       capture_output=True, text=True, env=psql_env(url))
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or p.stdout.strip() or "psql failed with no message")
    return p.stdout


def read_catalog(database: str = "postgres", url: str | None = None,
                 container: str = CONTAINER) -> set[str]:
    """The live catalog as a set of `kind:name@digest`. Raises RuntimeError if unreachable."""
    return {ln.strip() for ln in _run(CATALOG_SQL, database, url, container).splitlines()
            if ln.strip()}


def read_identity(database: str = "postgres", url: str | None = None,
                  container: str = CONTAINER) -> str:
    """WHO the connection actually is, MEASURED — `user@host/db, read_only=on`.

    Printed in every verdict line so the subject can never be a claim. Raises RuntimeError.
    """
    line = _run(IDENTITY_SQL, database, url, container).strip().splitlines()
    if not line:
        raise RuntimeError("the identity query returned nothing")
    user, db, host, ro = (line[0].split("|") + ["?", "?", "?", "?"])[:4]
    return f"{user}@{host}/{db}, read_only={ro}"


def name_of(obj: str) -> str:
    """`kind:name@digest` -> `kind:name`. PURE."""
    return obj.split("@", 1)[0]


def symbol_of(obj: str) -> str:
    """The bare identity of an object, ignoring both its digest and its ARGUMENT LIST. PURE.

    ⟳ r5 L2 (claude): `ADR0011_REMOVED` holds `fn:sync_corrections_to_workspace_video()` — the
    zero-argument rendering. The same drift that makes a `drop function` signature a silent no-op
    (r5 B1, MEASURED) also evades a name match: a survivor with one added parameter renders as
    `fn:sync_corrections_to_workspace_video(uuid)` and is simply not in the set. A must-never-exist
    check has to match the SYMBOL, not one spelling of it.
    """
    return name_of(obj).split("(", 1)[0]



def survivors(live: set[str], manifest: set[str]) -> set[str]:
    """Live objects M4 created that are STILL THERE — matched by SYMBOL, and for functions also by
    DIGEST. PURE. The full reasoning lives on `check-live-schema.verdict`'s absent branch.

    ⟳ r6 M1: this lives HERE, not in the gate, because `gen-m4-manifest.py` needs the same question
    answered and had grown its own two-table approximation of it.
    """
    symbols = {symbol_of(o) for o in manifest}
    fn_digests = {o.split("@", 1)[1] for o in manifest if o.startswith("fn:") and "@" in o}
    return {o for o in live
            if symbol_of(o) in symbols
            or (o.startswith("fn:") and "@" in o and o.split("@", 1)[1] in fn_digests)}

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
