#!/usr/bin/env bash
# MUTATION HARNESS for check-live-schema.py — proves the gate goes RED on the state that matters.
#
#   ./scripts/mutate-live-schema-check.sh
#     exit 0 = every mutation was caught
#     exit 1 = a mutation SURVIVED — the gate is not load-bearing
#     exit 2 = could not run (treat as NOT RUN)
#
# WHY A SCRATCH DATABASE AND NOT A ROLLED-BACK TRANSACTION.
# `check-live-schema.py` opens its OWN connection, so it cannot see an uncommitted transaction in
# another session. The obvious proof — create the object in a transaction, run the gate, roll back —
# is therefore impossible, and an earlier draft of the M4 plan specified exactly that impossible
# proof. This builds the state FOR REAL in throwaway databases and drops them afterwards. The shared
# stack is never touched: `an-instrument-that-edits-the-repo-corrupts-its-peers`.
#
# ⭐ WHAT EACH GENERATION OF THIS HARNESS COULD NOT EXPRESS — the defect keeps moving one layer out:
#
#   r3  it could only DROP things              -> a name-matching gate passed, and DISABLE was invisible
#   r4  it could only sabotage PRESENT state   -> `--expect-absent` was effectively unmutated (r5 M1),
#                                                 which is why r5 B1 survived a "7/7 caught" report
#   r5  it could only express DEFINITIONS      -> RLS off, `security invoker`, `reset search_path`,
#                                                 grants and `as restrictive` all left the digest
#                                                 byte-identical
#
# So the question this file has to keep answering is not "does the gate catch my mutation?" but
# **"what kind of defect can this harness not currently write down?"**
set -uo pipefail
cd "$(dirname "$0")/.."
CONTAINER="${PGCONTAINER:-supabase_db_youtube-playlist-summaries-cloud}"
# ⟳ r6 L1 (claude): the prefix is PER-PROCESS. `cleanup()` drops every database
# matching it, and `(force)` terminates other sessions — so two concurrent runs used to
# destroy each other mid-read, which can report a mutation as CAUGHT for the wrong
# reason. The r6 reviewer hit this and had to rename into its own namespace to run at all.
PREFIX="m4_gate_mut_$$"
TPL="${PREFIX}_tpl"
SPEC="docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema"
ROLLBACK="supabase/rollback/rollback_0027_stable_blob_addressing.sql"

adm()  { docker exec -i "$CONTAINER" psql -U postgres -d postgres -tAq -v ON_ERROR_STOP=1 "$@"; }
db()   { local d="$1"; shift; docker exec -i "$CONTAINER" psql -U postgres -d "$d" -tAq "$@"; }
gate() { python3 ./scripts/check-live-schema.py --database "$1" "$2" >/dev/null 2>&1; }

cleanup() {
  for d in $(adm -c "select datname from pg_database where datname like '${PREFIX}%';" 2>/dev/null); do
    adm -c "drop database if exists $d (force);" >/dev/null 2>&1
  done
}
trap cleanup EXIT

if ! adm -c "select 1" >/dev/null 2>&1; then
  echo "CANNOT RUN — no Postgres at container $CONTAINER. Treat this as NOT RUN." >&2
  exit 2
fi
[ -r "$ROLLBACK" ] || { echo "CANNOT RUN — missing $ROLLBACK. Treat this as NOT RUN." >&2; exit 2; }
cleanup

fail=0
report() { # name expected actual
  if [ "$2" = "$3" ]; then echo "  ✓ $1"; else echo "  ✗ $1 — MUTATION SURVIVED"; fail=1; fi
}

# `create database … template` is ~100× cheaper than pg_dump + apply, which is what made the r4
# harness slow enough that adding absent-polarity coverage felt expensive. It was not expensive; it
# was untried.
fresh() {
  adm -c "drop database if exists $1 (force);" >/dev/null 2>&1
  adm -c "create database $1 template $TPL;" >/dev/null 2>&1 \
    || { echo "  ✗ could not clone $TPL into $1 — treat this case as NOT RUN"; fail=1; return 1; }
}

echo "═══ mutation 1: an EMPTY database must read ABSENT ═══"
adm -c "create database ${PREFIX}_empty;" >/dev/null 2>&1
gate "${PREFIX}_empty" --expect-absent && r=pass || r=fail
report "empty db -> --expect-absent passes" pass "$r"

echo "═══ building the REAL post-ADR-0011 M4 schema as a TEMPLATE ═══"
# ⟳ MEASURED: hand-written stand-in tables are NOT enough — the spec needs the `auth` schema,
# `handle_new_user`, pgcrypto in `extensions`, and the real constraint shapes. The faithful and
# simpler route is to clone the live pre-M4 schema, then apply the spec on top.
#
# ⛔ NOT `cat 01 03 04`. MEASURED 2026-08-25 — that is what this harness used to do, and it built a
# PRE-ADR-0011 schema: `sync_corrections_to_workspace_video()` plus both `videos_corrections_sync_*`
# triggers, none of which M4 ships. The gate was therefore being mutation-proven against a schema
# that will never exist. `build-m4-schema.py` applies Tasks 1-2 and ASSERTS the end state.
adm -c "create database $TPL;" >/dev/null 2>&1
if ! docker exec -i "$CONTAINER" sh -c \
      "pg_dump -U postgres -d postgres --schema-only --no-owner --no-privileges | psql -U postgres -d $TPL -q" \
      >/dev/null 2>&1; then
  echo "CANNOT RUN — could not clone the live schema into the template. Treat this as NOT RUN." >&2
  exit 2
fi
if ! python3 ./scripts/build-m4-schema.py --quiet --out /tmp/m4-mutation-schema.sql; then
  echo "CANNOT RUN — could not build the post-ADR-0011 schema. Treat this as NOT RUN." >&2
  exit 2
fi
if ! docker exec -i "$CONTAINER" psql -U postgres -d "$TPL" -tAq -v ON_ERROR_STOP=1 \
     < /tmp/m4-mutation-schema.sql >/dev/null 2>&1; then
  echo "CANNOT RUN — the spec did not apply to the cloned schema. Treat this as NOT RUN." >&2
  exit 2
fi
gate "$TPL" --expect-present && r=pass || r=fail
report "M4 applied -> --expect-present passes (the CONTROL for everything below)" pass "$r"

echo "═══ mutation 2 ⭐ drop table … cascade ═══"
# ⟳ r5 M1 (claude): this used to be labelled "(triggers survive)". MEASURED, the residue is 140 of
# 161 objects and is dominated by 67 columns and 29 constraints — the mutation passed for a reason
# other than the one stated, and would pass if the gate checked any ONE of the nine kinds. It is
# kept because the STATE is real (it is a live outage: `ensure_workspace_for_profile()` still fires
# on signup and calls a table that is gone), but it has almost no discriminating power, which is why
# mutations 8-9 below exist.
if fresh "${PREFIX}_casc"; then
  db "${PREFIX}_casc" -c "drop table workspaces cascade;" >/dev/null 2>&1
  gate "${PREFIX}_casc" --expect-absent && r=pass || r=fail
  report "post-cascade residue -> --expect-absent FAILS (140/161 objects survive)" fail "$r"
fi

echo "═══ mutation 3 ⭐ the ADR-0011 RESIDUE: a Task 1 that never landed ═══"
# MEASURED 2026-08-25: with the raw spec applied, the rollback left three objects behind and
# `--expect-absent` reported ABSENT — because the gate's inventory is post-ADR-0011 and could not
# see them. `--expect-present` must REJECT this schema: it is not a valid M4.
adm -c "create database ${PREFIX}_raw;" >/dev/null 2>&1
docker exec -i "$CONTAINER" sh -c \
  "pg_dump -U postgres -d postgres --schema-only --no-owner --no-privileges | psql -U postgres -d ${PREFIX}_raw -q" \
  >/dev/null 2>&1
if { cat "$SPEC"/01_workspaces.sql "$SPEC"/03_generations.sql "$SPEC"/04_artifacts.sql; } \
   | docker exec -i "$CONTAINER" psql -U postgres -d "${PREFIX}_raw" -tAq -v ON_ERROR_STOP=1 \
   >/dev/null 2>&1; then
  gate "${PREFIX}_raw" --expect-present && r=pass || r=fail
  report "pre-ADR-0011 schema -> --expect-present FAILS (sync fn + 2 triggers)" fail "$r"
else
  echo "  ✗ could not build the raw pre-ADR-0011 schema — treat mutation 3 as NOT RUN"; fail=1
fi

echo "═══ mutation 4 ⭐⭐ r3 B2: DROP EVERY OWN-TABLE GUARD TRIGGER ═══"
# THE CASE THE 29-OBJECT GATE COULD NOT SEE. `M4_LIVE_TRIGGERS` named only the seven triggers on
# LIVE tables, so a database with every append-only / freeze / immutability guard dropped reported
# "M4 is PRESENT as expected", exit 0. The manifest names all 14.
if fresh "${PREFIX}_drop"; then
  db "${PREFIX}_drop" >/dev/null 2>&1 <<'SQL'
drop trigger if exists video_generations_freeze_trg              on video_generations;
drop trigger if exists forbid_collecting_current_trg             on video_generations;
drop trigger if exists video_artifacts_append_only_trg           on video_artifacts;
drop trigger if exists video_artifacts_generation_complete_trg   on video_artifacts;
drop trigger if exists video_artifact_sources_append_only_trg    on video_artifact_sources;
drop trigger if exists video_artifact_sources_insert_once_trg    on video_artifact_sources;
drop trigger if exists art_summary_has_no_source_trg             on video_artifact_sources;
SQL
  gate "${PREFIX}_drop" --expect-present && r=pass || r=fail
  report "ALL SEVEN own-table guards dropped -> --expect-present FAILS" fail "$r"
fi

echo "═══ mutation 5 ⭐⭐⭐ r4 B1: DISABLE, do not drop — the name stays, the rule dies ═══"
# THE MUTATION THIS HARNESS WAS ONE WORD FROM CATCHING. Mutation 4 DROPS the guards; a gate that
# compares names catches that. `alter table … disable trigger` leaves every name in place and every
# rule inert, and the name-only gate returned exit 0 over it — measured on a real database.
if fresh "${PREFIX}_dis"; then
  db "${PREFIX}_dis" >/dev/null 2>&1 <<'SQL'
alter table video_artifacts        disable trigger video_artifacts_append_only_trg;
alter table video_artifacts        disable trigger video_artifacts_generation_complete_trg;
alter table video_generations      disable trigger video_generations_freeze_trg;
alter table video_generations      disable trigger forbid_collecting_current_trg;
alter table video_artifact_sources disable trigger video_artifact_sources_append_only_trg;
alter table video_artifact_sources disable trigger video_artifact_sources_insert_once_trg;
alter table video_artifact_sources disable trigger art_summary_has_no_source_trg;
SQL
  n_dis=$(db "${PREFIX}_dis" -c \
    "select count(*) from pg_trigger where tgenabled='D' and not tgisinternal;" | tr -d '[:space:]')
  echo "     triggers now DISABLED (tgenabled='D'): $n_dis  — every NAME still present"
  gate "${PREFIX}_dis" --expect-present && r=pass || r=fail
  report "7 guards DISABLED (not dropped) -> --expect-present FAILS" fail "$r"
fi

echo "═══ mutation 6 ⭐ a guard FUNCTION BODY replaced with a no-op ═══"
if fresh "${PREFIX}_body"; then
  db "${PREFIX}_body" >/dev/null 2>&1 <<'SQL'
create or replace function video_artifacts_append_only() returns trigger
  language plpgsql as $$ begin return new; end $$;
SQL
  gate "${PREFIX}_body" --expect-present && r=pass || r=fail
  report "guard body replaced by 'return new' -> --expect-present FAILS" fail "$r"
fi

# ───────────────────────────────────────────────────────────────────────────────────────────────
# ⭐⭐⭐⭐ r5 B2 — ENFORCEMENT STATE. Every mutation below leaves the object's DEFINITION untouched,
# so every one of them was exit 0 against the r4 gate. `disable row level security` does not modify
# a single policy row, and policy rows were the entire policy input: byte-identical digest, five
# owner-scoping policies reported as verified, none of them enforcing.
# ───────────────────────────────────────────────────────────────────────────────────────────────
echo "═══ mutation 7 ⭐⭐⭐⭐ r5 B2: RLS DISABLED — every policy digest stays byte-identical ═══"
if fresh "${PREFIX}_rls"; then
  db "${PREFIX}_rls" >/dev/null 2>&1 <<'SQL'
alter table video_artifacts disable row level security;
SQL
  same=$(db "${PREFIX}_rls" -c \
    "select case when count(*) = 0 then 'NO POLICIES' else 'policies unchanged' end
       from pg_policy p join pg_class c on c.oid = p.polrelid where c.relname='video_artifacts';")
  echo "     RLS is now OFF and the policy rows are untouched ($(echo "$same" | tr -d '[:space:]'))"
  gate "${PREFIX}_rls" --expect-present && r=pass || r=fail
  report "RLS DISABLED on video_artifacts -> --expect-present FAILS" fail "$r"
fi

echo "═══ mutation 8 ⭐ r5 B2: NO FORCE — the owner silently bypasses every policy ═══"
if fresh "${PREFIX}_force"; then
  db "${PREFIX}_force" >/dev/null 2>&1 <<'SQL'
alter table video_artifacts no force row level security;
SQL
  gate "${PREFIX}_force" --expect-present && r=pass || r=fail
  report "NO FORCE row level security -> --expect-present FAILS" fail "$r"
fi

echo "═══ mutation 9 ⭐⭐ r5 B2: SECURITY INVOKER + search_path reset on a SECURITY DEFINER guard ═══"
# `reset search_path` on a SECURITY DEFINER function is the textbook search-path hijack; neither this
# nor `security invoker` changes prosrc, so neither changed the r4 digest.
if fresh "${PREFIX}_secdef"; then
  db "${PREFIX}_secdef" >/dev/null 2>&1 <<'SQL'
alter function video_artifacts_append_only() security invoker;
alter function video_artifacts_generation_complete() reset search_path;
SQL
  gate "${PREFIX}_secdef" --expect-present && r=pass || r=fail
  report "security invoker + reset search_path -> --expect-present FAILS" fail "$r"
fi

echo "═══ mutation 10 ⭐⭐ r5 B2: GRANTS — the table opens up to anon, definitions untouched ═══"
if fresh "${PREFIX}_acl"; then
  db "${PREFIX}_acl" >/dev/null 2>&1 <<'SQL'
grant insert, update, delete on video_artifacts to anon;
SQL
  gate "${PREFIX}_acl" --expect-present && r=pass || r=fail
  report "insert/update/delete granted to anon -> --expect-present FAILS" fail "$r"
fi

echo "═══ mutation 11 ⭐ r5 B2: a policy recreated AS RESTRICTIVE — same cmd, roles and qual ═══"
if fresh "${PREFIX}_perm"; then
  db "${PREFIX}_perm" >/dev/null 2>&1 <<'SQL'
do $$
declare p record;
begin
  select polname, c.relname as tbl, pg_get_expr(polqual, polrelid) as q
    into p
    from pg_policy join pg_class c on c.oid = polrelid
   where c.relname = 'video_artifacts' and polqual is not null
   limit 1;
  if p.polname is null then raise exception 'no policy to mutate on video_artifacts'; end if;
  execute format('drop policy %I on %I', p.polname, p.tbl);
  execute format('create policy %I on %I as restrictive for select using (%s)',
                 p.polname, p.tbl, p.q);
end $$;
SQL
  gate "${PREFIX}_perm" --expect-present && r=pass || r=fail
  report "policy flipped PERMISSIVE -> RESTRICTIVE -> --expect-present FAILS" fail "$r"
fi

echo "═══ mutation 12 ⭐ r5 B2: a view switched OFF security_invoker ═══"
# ⚠ THE DIRECTION MATTERS, AND WRITING IT THE OTHER WAY IS A VACUOUS MUTATION.
# M4 ships all three views with `security_invoker=true` already (MEASURED), so
# `set (security_invoker = true)` is a NO-OP: reloptions is byte-identical before and after, and a
# gate reporting "not caught" would be reporting on a sabotage that never happened. `= false` is the
# dangerous direction — the view then reads with the DEFINER's privileges and stops filtering by
# the caller. The r5 claude review listed the `= true` form among its surviving sabotages, so that
# row of its table is not evidence; rows 1-6 and 8 establish B2 on their own.
if fresh "${PREFIX}_view"; then
  before_ro=$(db "${PREFIX}_view" -c "select coalesce(reloptions::text,'<null>') from pg_class c
      join pg_namespace n on n.oid=c.relnamespace
     where n.nspname='public' and relname='video_artifacts_current';" | tr -d '[:space:]')
  db "${PREFIX}_view" >/dev/null 2>&1 <<'SQL'
alter view video_artifacts_current set (security_invoker = false);
SQL
  after_ro=$(db "${PREFIX}_view" -c "select coalesce(reloptions::text,'<null>') from pg_class c
      join pg_namespace n on n.oid=c.relnamespace
     where n.nspname='public' and relname='video_artifacts_current';" | tr -d '[:space:]')
  echo "     reloptions: $before_ro -> $after_ro"
  if [ "$before_ro" = "$after_ro" ]; then
    echo "  ✗ THE MUTATION DID NOT CHANGE ANYTHING — treat mutation 12 as NOT RUN"; fail=1
  else
    gate "${PREFIX}_view" --expect-present && r=pass || r=fail
    report "view set (security_invoker = false) -> --expect-present FAILS" fail "$r"
  fi
fi

# ───────────────────────────────────────────────────────────────────────────────────────────────
# ⭐⭐⭐⭐ r5 B1 + M1 — THE ABSENT POLARITY, which had exactly TWO mutations and no discriminating
# power. These run the REAL rollback file (the first thing in this repo that ever executed it) and
# then leave ONE drifted survivor behind, which is what a missed `drop` actually looks like.
# ───────────────────────────────────────────────────────────────────────────────────────────────
echo "═══ mutation 13 ⭐ CONTROL: the real rollback leaves a database that reads ABSENT ═══"
if fresh "${PREFIX}_rb"; then
  if db "${PREFIX}_rb" -v ON_ERROR_STOP=1 < "$ROLLBACK" >/dev/null 2>&1; then
    gate "${PREFIX}_rb" --expect-absent && r=pass || r=fail
    report "rollback applied -> --expect-absent passes" pass "$r"
  else
    echo "  ✗ the rollback did not apply — treat mutations 13-15 as NOT RUN"; fail=1
  fi
fi

echo "═══ mutation 14 ⭐⭐⭐⭐ r5 B1: a survivor whose BODY drifted (the hot-fix shape) ═══"
# MEASURED by both r5 halves: one `create or replace` before the rollback is the entire difference
# between exit 1 and exit 0, because `live & manifest` cannot see an object whose digest moved.
if fresh "${PREFIX}_surv"; then
  db "${PREFIX}_surv" -v ON_ERROR_STOP=1 < "$ROLLBACK" >/dev/null 2>&1
  db "${PREFIX}_surv" >/dev/null 2>&1 <<'SQL'
create function video_artifacts_append_only() returns trigger
  language plpgsql as $$ begin return new; end $$;
SQL
  n=$(db "${PREFIX}_surv" -c \
      "select count(*) from pg_proc p join pg_namespace n on n.oid=p.pronamespace
        where n.nspname='public' and p.proname='video_artifacts_append_only';" | tr -d '[:space:]')
  echo "     surviving guard functions after the rollback: $n (body differs from the manifest)"
  gate "${PREFIX}_surv" --expect-absent && r=pass || r=fail
  report "drifted M4 guard survives the rollback -> --expect-absent FAILS" fail "$r"
fi

echo "═══ mutation 15 ⭐⭐⭐⭐ r5 B1: a survivor whose SIGNATURE drifted (the silent no-op shape) ═══"
# A `drop function` names exact types, so ONE added defaulted parameter makes it a no-op and leaves
# a live SECURITY DEFINER M4 function behind. ⚠ `name_of` matching — the fix BOTH review halves
# prescribed — does NOT catch this: the rendered name differs too. Only the SYMBOL does.
if fresh "${PREFIX}_sig"; then
  db "${PREFIX}_sig" -v ON_ERROR_STOP=1 < "$ROLLBACK" >/dev/null 2>&1
  db "${PREFIX}_sig" >/dev/null 2>&1 <<'SQL'
create function record_artifact(p_ws uuid, p_trace text) returns void
  language plpgsql security definer set search_path = '' as $$ begin end $$;
SQL
  echo "     surviving: record_artifact(uuid, text), SECURITY DEFINER — a signature the manifest"
  echo "     does not contain, on a database this gate would otherwise certify M4-free"
  gate "${PREFIX}_sig" --expect-absent && r=pass || r=fail
  report "drifted-SIGNATURE M4 function survives -> --expect-absent FAILS" fail "$r"
fi

# ───────────────────────────────────────────────────────────────────────────────────────────────
# ⭐⭐⭐⭐ r6 — THE FIXTURE WAS THE BLIND SPOT, NOT THE PREDICATE.
# Every mutation above clones $TPL, and $TPL is built with `pg_dump --no-privileges` — the same
# construction the manifest generator uses. So the harness and the thing it validates shared one
# blind spot, and a 16/16 green report was structurally incapable of noticing that the manifest's
# ACLs matched no deployed database (r6 B1). Mutation 19 is a CONTROL, not a sabotage, and it is the
# one this suite lacked for five rounds.
# ───────────────────────────────────────────────────────────────────────────────────────────────
echo "═══ mutation 16 ⭐⭐ r6 B (codex): a guard made STRICT — the body stops running ═══"
# A STRICT function returns NULL WITHOUT EXECUTING ITS BODY when any argument is NULL. `prosrc` is
# untouched, so the r5 digest was byte-identical.
if fresh "${PREFIX}_strict"; then
  before_s=$(db "${PREFIX}_strict" -c "select proisstrict::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and proname='record_artifact';" | tr -d '[:space:]')
  db "${PREFIX}_strict" -v ON_ERROR_STOP=1 >/dev/null 2>&1 <<'SQL'
do $$ declare s text; begin
  select 'alter function public.'||p.proname||'('||pg_get_function_identity_arguments(p.oid)||') strict'
    into s from pg_proc p join pg_namespace n on n.oid=p.pronamespace
   where n.nspname='public' and p.proname='record_artifact';
  execute s; end $$;
SQL
  after_s=$(db "${PREFIX}_strict" -c "select proisstrict::text from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and proname='record_artifact';" | tr -d '[:space:]')
  echo "     record_artifact proisstrict: $before_s -> $after_s"
  if [ "$before_s" = "$after_s" ]; then
    echo "  ✗ THE MUTATION DID NOT CHANGE ANYTHING — treat mutation 16 as NOT RUN"; fail=1
  else
    gate "${PREFIX}_strict" --expect-present && r=pass || r=fail
    report "record_artifact made STRICT -> --expect-present FAILS" fail "$r"
  fi
fi

echo "═══ mutation 17 ⭐⭐ r6 B2 (claude): a COLUMN-level grant, which moves no table ACL ═══"
if fresh "${PREFIX}_colacl"; then
  before_c=$(db "${PREFIX}_colacl" -c "select has_column_privilege('anon','video_artifacts','blob_key','INSERT')::text;" | tr -d '[:space:]')
  db "${PREFIX}_colacl" -v ON_ERROR_STOP=1 >/dev/null 2>&1 <<'SQL'
grant insert (workspace_id, video_id, slot, generation_id, kind, state, blob_key)
  on video_artifacts to anon;
SQL
  after_c=$(db "${PREFIX}_colacl" -c "select has_column_privilege('anon','video_artifacts','blob_key','INSERT')::text;" | tr -d '[:space:]')
  echo "     anon INSERT on video_artifacts.blob_key: $before_c -> $after_c  (table ACL unchanged)"
  if [ "$before_c" = "$after_c" ]; then
    echo "  ✗ THE MUTATION DID NOT CHANGE ANYTHING — treat mutation 17 as NOT RUN"; fail=1
  else
    gate "${PREFIX}_colacl" --expect-present && r=pass || r=fail
    report "column-level insert granted to anon -> --expect-present FAILS" fail "$r"
  fi
fi

echo "═══ mutation 18 ⭐⭐ r6 H1 (claude): a REWRITE RULE swallows every write ═══"
if fresh "${PREFIX}_rule"; then
  db "${PREFIX}_rule" -v ON_ERROR_STOP=1 >/dev/null 2>&1 <<'SQL'
create rule swallow as on insert to video_artifacts do instead nothing;
SQL
  n_rules=$(db "${PREFIX}_rule" -c "select count(*) from pg_rewrite r join pg_class c on c.oid=r.ev_class where c.relname='video_artifacts' and r.rulename<>'_RETURN';" | tr -d '[:space:]')
  echo "     rules on video_artifacts: $n_rules  — every insert now vanishes silently"
  if [ "$n_rules" = "0" ]; then
    echo "  ✗ THE MUTATION DID NOT CHANGE ANYTHING — treat mutation 18 as NOT RUN"; fail=1
  else
    gate "${PREFIX}_rule" --expect-present && r=pass || r=fail
    report "DO INSTEAD NOTHING rule on video_artifacts -> --expect-present FAILS" fail "$r"
  fi
fi

echo "═══ mutation 20 ⭐⭐ r6 H (codex): a RENAMED survivor of the rollback ═══"
# `alter function … rename to …_old` then the real rollback: the drop skips with a NOTICE and a live
# SECURITY DEFINER guard remains. Symbol matching cannot see it — the symbol is what changed. But
# `prosrc` does not contain the function's own name, so the survivor's DIGEST is byte-identical to
# the manifest's, and absent mode matches fn: objects on digest as well as symbol.
if fresh "${PREFIX}_ren"; then
  db "${PREFIX}_ren" -v ON_ERROR_STOP=1 >/dev/null 2>&1 <<'SQL'
alter function public.video_artifacts_append_only() rename to video_artifacts_append_only_old;
SQL
  db "${PREFIX}_ren" -v ON_ERROR_STOP=1 < "$ROLLBACK" >/dev/null 2>&1
  surv=$(db "${PREFIX}_ren" -c "select proname||' secdef='||prosecdef from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and proname like '%append_only%';" | tr -d '[:space:]')
  echo "     surviving after the full rollback: ${surv:-<none>}"
  if [ -z "$surv" ]; then
    echo "  ✗ THE RENAMED FUNCTION DID NOT SURVIVE — treat mutation 20 as NOT RUN"; fail=1
  else
    gate "${PREFIX}_ren" --expect-absent && r=pass || r=fail
    report "RENAMED M4 guard survives the rollback -> --expect-absent FAILS" fail "$r"
  fi
fi

echo "═══ mutation 19 ⭐⭐⭐⭐ r6 B1: a PRODUCTION-SHAPED database must PASS ═══"
# THE CONTROL THE SUITE LACKED. Production carries `alter default privileges` granting
# anon/authenticated/service_role ALL on every new public table (MEASURED on prod: anon=arwdDxtm,
# plus a `claude_ro` grantee the container does not even have). With ACL TEXT in the digest this
# went red on 20+ objects — the plan's Step 7 would have argued for rolling back a good migration.
adm -c "drop database if exists ${PREFIX}_prodshape (force);" >/dev/null 2>&1
adm -c "create database ${PREFIX}_prodshape;" >/dev/null 2>&1
docker exec -i "$CONTAINER" sh -c \
  "pg_dump -U postgres -d postgres --schema-only --no-owner | psql -U postgres -d ${PREFIX}_prodshape -q" \
  >/dev/null 2>&1
db "${PREFIX}_prodshape" -v ON_ERROR_STOP=1 >/dev/null 2>&1 <<'SQL'
alter default privileges for role postgres in schema public
  grant all on tables to anon, authenticated, service_role;
alter default privileges for role postgres in schema public
  grant execute on functions to anon, authenticated, service_role;
SQL
n_def=$(db "${PREFIX}_prodshape" -c "select count(*) from pg_default_acl d join pg_namespace n on n.oid=d.defaclnamespace where n.nspname='public';" | tr -d '[:space:]')
db "${PREFIX}_prodshape" -v ON_ERROR_STOP=1 < /tmp/m4-mutation-schema.sql >/dev/null 2>&1
echo "     pg_default_acl rows for public: $n_def (the container's own template has 0 after --no-privileges)"
if [ "$n_def" = "0" ]; then
  echo "  ✗ THE DEFAULT PRIVILEGES DID NOT INSTALL — treat mutation 19 as NOT RUN"; fail=1
else
  gate "${PREFIX}_prodshape" --expect-present && r=pass || r=fail
  report "M4 on a PRODUCTION-SHAPED database -> --expect-present PASSES" pass "$r"
fi

echo
if [ "$fail" -eq 0 ]; then
  echo "✅ every mutation caught — check-live-schema.py is load-bearing"
else
  echo "❌ a mutation survived — the gate does not detect what it claims to"
fi
exit "$fail"
