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
# ⚠⚠ THAT LAST SENTENCE IS TRUE OF EVERY MUTATION IN THIS FILE AND NOT OF THE CLASS — ⟳ r8 L3
# (claude), proved the expensive way. Object-level grants are PER-DATABASE. **Role membership is
# CLUSTER-WIDE**: the reviewer's `grant service_role to anon` probe changed `pg_auth_members` and
# silently altered `has_table_privilege('anon', …)` in the container's shared `postgres` database as
# well as in every scratch clone, garbaging a result table before it was noticed. The brief for that
# round listed role membership as a candidate mutation, so the next person to reach for it will reach
# for it inside a harness that promises an isolation it does not have for that one case. If you add a
# role-scoped mutation here, it must create its OWN role and drop it, never grant an existing one.
#
# ⚠ AND TWO OF THESE MUST NOT RUN AT ONCE. `mutate-schema.py` (gate 2) works inside the SHARED
# `postgres` database, and during round 8 a reviewer and the coordinator ran it concurrently: one
# reported 23/63 with "baseline restored: STILL BROKEN" while the other, minutes later, measured
# 63/63 and a clean database. That was filed as a Blocking finding before it was traced. There is no
# lock here; serialise by hand.
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

# ⭐ FORK (a) STEP 3 — THE SECOND GATE. Session-role access to M4's relations left the digest and
# moved to `check-anon-exposure.py` RULE 3. Every mutation that used to be caught by `gate` and is
# now caught by `anon_gate` asserts BOTH halves: that the digest passes AND that the new home fails.
# One assertion would not distinguish "coverage moved" from "coverage was deleted", and deleting it
# is exactly what a careless reading of "remove privileges from the digest" produces.
#
# ⛔⛔ IT MATCHES THE NAMED PROBLEM, NOT THE EXIT CODE — ⟳ r8 B1 (codex), CONFIRMED by re-measurement.
# The first version tested `exit != 0` and that was a FALSE GREEN on every moved mutation. The
# template is built with `pg_dump --no-privileges`, which strips ACLs — and a Postgres function with
# no ACL is EXECUTABLE BY PUBLIC. So on an UNMUTATED M4 scratch the script is already red for two
# reasons that have nothing to do with M4:
#     UNLISTED           `exec_sql` is SECURITY DEFINER and anon-EXECUTable
#     UNLISTED           `record_correction_spend` is SECURITY DEFINER and anon-EXECUTable
#     LOWER THE BASELINE 0 money tables are TRUNCATE-able, baseline says 5
#     CONTROL EXIT = 1
# Every "RULE 3 FAILS" tick was therefore earned by that noise, not by the sabotage. The mutations
# proved the SCRIPT was red on the fixture; they proved nothing about coverage having moved.
#
# So `anon_gate` now takes the problem TOKEN it expects, and `anon_control` asserts that same token
# is ABSENT before the mutation — which is the discrimination the exit code could never provide.
# ⚠ NO PIPE INTO `grep -q`. This file runs under `set -o pipefail`, and `grep -q` exits the moment
# it matches — which SIGPIPEs the producer, and pipefail then returns the PRODUCER's status. So
# `anon_out … | grep -q X` reports FAILURE on the very runs where X was found. MEASURED here
# 2026-08-26: RULE 3 printed "M4 NOT READ-ONLY `anon` holds DELETE, INSERT, UPDATE on
# `video_artifacts`" while all four moved mutations reported MUTATION SURVIVED. Capture first, match
# second. (Third instance of a pipeline status being read as a verdict in this repo.)
# ⛔ BOTH HELPERS FAIL WHEN THE INSTRUMENT COULD NOT RUN — ⟳ r9 M2 (claude). `anon_out` used to
# discard the exit status, and `check-anon-exposure.py` exits 2 with a `CANNOT RUN —` banner on a
# missing manifest, an unreadable catalog, an unparseable row, an empty definer list, or a
# derived/declared mismatch. None of those outputs contains a problem token, so EVERY CONTROL PASSED.
# MEASURED: `anon_control <a database that does not exist> "M4 NOT READ-ONLY"` returned PASS.
# The control is the entire mechanism r8 B1 installed so a tick could not be earned by noise; a
# control that passes because nothing ran is that same defect one layer out.
anon_out() { python3 ./scripts/check-anon-exposure.py --local --database "$1" 2>&1; }
anon_ran() {
  local o rc; o=$(anon_out "$1"); rc=$?
  case "$rc:$o" in 2:*|*"CANNOT RUN"*) echo "$o" | head -2 >&2; return 1 ;; esac
  printf '%s' "$o"
}
anon_gate()    { local o; o=$(anon_ran "$1") || return 1; case "$o" in *"$2"*) return 0 ;; *) return 1 ;; esac; }
anon_control() { local o; o=$(anon_ran "$1") || return 1; case "$o" in *"$2"*) return 1 ;; *) return 0 ;; esac; }

# ── the PREMISE half of gate 13 (mutations 28, 29) ──────────────────────────────────────────────
# Same three-way discipline as anon_ran, for the same measured reason: exit 2 is CANNOT RUN and must
# never be read as either verdict. `premise_gate` passes when the premises go RED (the drift was
# caught); `premise_control` passes when they all hold on an unmutated template. A gate with no
# control can be earned by a database that was already broken — r8 B1, measured.
premise_rc() {
  local o rc
  o=$(python3 ./scripts/verify-exclusion-reasons.py --premises-only --database "$1" 2>&1); rc=$?
  case "$rc:$o" in 2:*|*"CANNOT RUN"*) echo "$o" | head -2 >&2; return 2 ;; esac
  return "$rc"
}
premise_gate()    { premise_rc "$1"; [ "$?" -eq 1 ]; }
premise_control() { premise_rc "$1"; [ "$?" -eq 0 ]; }

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
# ⟳ 2026-08-26 — CLONE A *PRE-M4* BASE, NOT `postgres` DIRECTLY. Once 0027 was applied locally, the
# `pg_dump` clone already contained M4 and the apply below died on `relation "workspaces" already
# exists`, so this gate reported "the spec did not apply to the cloned schema" and stopped. It was
# one of seven with that single cause; `scripts/m4-base-db.sh` documents the set.
# ⚠ The base is named under $PREFIX so the existing EXIT trap reaps it with everything else, and it
# is built ONCE — every database below is a `template` clone of it, which the note above measures at
# ~100× cheaper than repeating the dump.
BASE="${PREFIX}_base"
if ! ./scripts/m4-base-db.sh "$BASE"; then
  echo "CANNOT RUN — could not build a pre-M4 base database. Treat this as NOT RUN." >&2
  exit 2
fi
if ! adm -c "create database $TPL template $BASE;" >/dev/null 2>&1; then
  echo "CANNOT RUN — could not clone $BASE into the template. Treat this as NOT RUN." >&2
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

echo "═══ mutation 3 ⭐ COLUMN DRIFT on an ENUMERATED relation ═══"
# ⟳ REWRITTEN 2026-08-26 — AND THE OLD VERSION'S SUBJECT NO LONGER EXISTS, WHICH IS WHY.
#
# It used to build the "pre-ADR-0011 residue" by applying the raw spec files 01/03/04, and assert
# that `--expect-present` REJECTED the result because of `sync_corrections_to_workspace_video()`
# and its two triggers. Task 1 (8907b5a) deleted all three FROM THOSE SPEC FILES, so the raw build
# is now byte-for-byte the post-ADR-0011 schema, `--expect-present` correctly passes, and the
# mutation reported MUTATION SURVIVED. VERIFIED before touching it: the only remaining occurrence
# of that function name in the spec or in 0027 is a COMMENT recording its deletion.
#
# ⭐⭐ AND THE REPLACEMENT'S FIRST DRAFT ASSERTED THE WRONG DIRECTION, WHICH IS THE FINDING.
#
# It was written expecting `--expect-present` to FAIL on an added column — "the manifest digests the
# column list of every relation it enumerates, so drift there is caught". MEASURED: the column
# landed (2 -> 3) and the gate PASSED. Present mode is `MANIFEST ⊆ live`, and the manifest
# enumerates columns as individual objects, so an EXTRA column is simply an extra live object and
# the subset still holds. The asymmetry is deliberate and worth stating: a REMOVED column breaks the
# subset and IS caught; an ADDED one is invisible.
#
# ⚠ SO THIS IS A THIRD FACE OF MUTATIONS 28 AND 29, NOT THEIR COMPLEMENT — and unlike those two it
#   has NO COMPENSATING PREMISE. `verify-exclusion-reasons.py` asserts "M4 creates exactly one type,
#   an enum" and "no partitioned table exists", which catch the domain and the partition. Nothing
#   asserts a column count. This mutation therefore DOCUMENTS a hole rather than guarding one, and
#   says so rather than being quietly written to pass. Whether that hole is worth closing is a
#   design question, not a defect to patch here.
if fresh "${PREFIX}_raw"; then
  before_c=$(db "${PREFIX}_raw" -c "select count(*) from information_schema.columns where table_schema='public' and table_name='workspace_videos';" | tr -d '[:space:]')
  db "${PREFIX}_raw" -v ON_ERROR_STOP=1 >/dev/null 2>&1 <<'SQL'
alter table public.workspace_videos add column m4_mut_residue text;
SQL
  after_c=$(db "${PREFIX}_raw" -c "select count(*) from information_schema.columns where table_schema='public' and table_name='workspace_videos';" | tr -d '[:space:]')
  echo "     workspace_videos columns: ${before_c:-<empty>} -> ${after_c:-<empty>}"
  if [ -z "$before_c" ] || [ "$before_c" = "$after_c" ]; then
    echo "  ✗ THE COLUMN DID NOT LAND — treat mutation 3 as NOT RUN"; fail=1
  else
    gate "${PREFIX}_raw" --expect-present && r=pass || r=fail
    report "an extra COLUMN -> the digest is blind and still PASSES (no premise covers it)" pass "$r"
    # The other direction, which is the one that IS guarded — and asserting it here is what keeps
    # the case above from reading as "the gate sees nothing".
    db "${PREFIX}_raw" -v ON_ERROR_STOP=1 >/dev/null 2>&1 <<'SQL'
alter table public.workspace_videos drop column m4_mut_residue;
alter table public.workspace_videos drop column video_id cascade;
SQL
    gate "${PREFIX}_raw" --expect-present && r=pass || r=fail
    report "a REMOVED column breaks MANIFEST ⊆ live -> --expect-present FAILS" fail "$r"
  fi
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
# ⟳ MOVED HOME 2026-08-26 (fork (a) step 3). This was a `gate` case for two rounds. The digest no
# longer carries session-role access, so the CORRECT verdict from check-live-schema is now PASS —
# and the whole question is whether anything else says no. Both halves are asserted.
if fresh "${PREFIX}_acl"; then
  db "${PREFIX}_acl" >/dev/null 2>&1 <<'SQL'
grant insert, update, delete on video_artifacts to anon;
SQL
  anon_control "$TPL" "M4 NOT READ-ONLY" && r=pass || r=fail
  report "CONTROL: an unmutated M4 reports no M4-NOT-READ-ONLY problem" pass "$r"
  gate "${PREFIX}_acl" --expect-present && r=pass || r=fail
  report "insert/update/delete to anon -> the DIGEST no longer claims to see it" pass "$r"
  anon_gate "${PREFIX}_acl" "M4 NOT READ-ONLY" && r=pass || r=fail
  report "insert/update/delete to anon -> RULE 3 names M4 NOT READ-ONLY" pass "$r"
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
    # ⟳ MOVED HOME 2026-08-26 with mutation 10. RULE 3 reads has_any_column_privilege for exactly
    # this: the grant moves no table ACL, so a check that only asked has_table_privilege would be
    # green here — which is how r6 B2 survived a 16/16 report.
    gate "${PREFIX}_colacl" --expect-present && r=pass || r=fail
    report "column-level insert to anon -> the DIGEST no longer claims to see it" pass "$r"
    anon_gate "${PREFIX}_colacl" "M4 NOT READ-ONLY" && r=pass || r=fail
    report "column-level insert to anon -> RULE 3 names M4 NOT READ-ONLY" pass "$r"
  fi
fi

echo "═══ mutation 22 ⭐⭐⭐ r7 M4 (codex): TRUNCATE — the verb NO gate could see until today ═══"
# THE FINDING THIS STEP CLOSES. `grant truncate on video_artifacts to anon` passed BOTH gates: the
# digest's REL_PRIVS listed only SELECT/INSERT/UPDATE/DELETE, and this script's money-table rule
# covers five tables, none of them M4's. TRUNCATE fires neither RLS nor row triggers, so it walks
# past every append-only guard in the schema — and `video_artifacts` is the PAID manifest.
#
# ⚠ Note the fix shape: TRUNCATE was NOT added to the digest as a fifth privilege. That is the whole
# argument of fork (a) — a fifth redefinition of the fingerprint is what the previous four rounds
# each did, and each was correct and insufficient.
if fresh "${PREFIX}_trunc"; then
  before_t=$(db "${PREFIX}_trunc" -c "select has_table_privilege('anon','video_artifacts','TRUNCATE')::text;" | tr -d '[:space:]')
  db "${PREFIX}_trunc" -v ON_ERROR_STOP=1 >/dev/null 2>&1 <<'SQL'
grant truncate on video_artifacts to anon;
SQL
  after_t=$(db "${PREFIX}_trunc" -c "select has_table_privilege('anon','video_artifacts','TRUNCATE')::text;" | tr -d '[:space:]')
  echo "     anon TRUNCATE on video_artifacts: ${before_t:-<empty>} -> ${after_t:-<empty>}"
  if [ -z "$before_t" ] || [ -z "$after_t" ]; then
    echo "  ✗ A PROBE RETURNED NOTHING — treat mutation 22 as NOT RUN"; fail=1
  elif [ "$before_t" = "$after_t" ]; then
    echo "  ✗ THE GRANT DID NOT LAND — treat mutation 22 as NOT RUN"; fail=1
  else
    # ⟳ r9 H1 (codex): the token used to be the bare word `TRUNCATE`, which ALSO appears in RULE 2's
    # own message — "LOWER THE BASELINE 0 money tables are TRUNCATE-able" — and that message is
    # present on the unmutated template. So the tick could be earned while RULE 3 said nothing about
    # any M4 relation. This is the SAME defect the anon_gate repair was written to fix, surviving in
    # one of the four call sites: a token is only a discriminator if the control cannot contain it.
    anon_control "$TPL" "holds TRUNCATE on" && r=pass || r=fail
    report "CONTROL: an unmutated M4 reports no TRUNCATE on any M4 relation" pass "$r"
    anon_gate "${PREFIX}_trunc" "holds TRUNCATE on \`video_artifacts\`" && r=pass || r=fail
    report "TRUNCATE granted to anon -> RULE 3 names TRUNCATE on video_artifacts" pass "$r"
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

echo "═══ mutation 21 ⭐⭐⭐ r7 M (codex): an ARGUMENT DEFAULT changed — same symbol, same body ═══"
# The narrowest sabotage in this suite. `prosrc` is untouched and the identity arguments are
# untouched — identity arguments OMIT DEFAULTS — so before r7 the digest was byte-identical, while
# every caller that OMITS the argument writes a different value. TWO falsifiers below: if
# pg_get_function_arguments does not move, the mutation did not happen; if anything ELSE moves, the
# gate could go red for a reason round 5 already covered and this case proves nothing.
if fresh "${PREFIX}_argdef"; then
  # A default cannot be changed by ALTER FUNCTION — only by CREATE OR REPLACE at the same signature,
  # which is exactly the hot-fix shape. Everything except the one default is rebuilt FROM THE
  # CATALOG, so the replacement is byte-identical in body, volatility, config and security context.
  probe="from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public' and p.proname='record_artifact'"
  # ⚠ EVERY CAST HERE IS LOAD-BEARING. Without `::text` on prosecdef/provolatile this SELECT dies
  # with `operator is not unique: text || "char"`, both probes come back EMPTY, and empty == empty
  # makes the narrowness check PASS WITHOUT RUNNING. Measured 2026-08-26 — it reported ✓ on its very
  # first run. That is why the emptiness guard below exists: silence must not read as agreement.
  narrow="select pg_get_function_identity_arguments(p.oid)||'|'||md5(p.prosrc)||'|'||p.prosecdef::text||'|'||coalesce(array_to_string(p.proconfig,','),'')||'|'||p.provolatile::text $probe;"
  argsql="select pg_get_function_arguments(p.oid) $probe;"
  before_a=$(db "${PREFIX}_argdef" -c "$argsql")
  before_n=$(db "${PREFIX}_argdef" -c "$narrow")
  db "${PREFIX}_argdef" -v ON_ERROR_STOP=1 >/dev/null 2>&1 <<'SQL'
do $$ declare s text; begin
  select 'create or replace function public.record_artifact(' ||
         regexp_replace(pg_get_function_arguments(p.oid),
                        'p_md_hash text DEFAULT [^,)]*',
                        'p_md_hash text DEFAULT ''r7-default''::text') ||
         ') returns ' || pg_get_function_result(p.oid) ||
         ' language plpgsql security definer set search_path = '''' as ' || quote_literal(p.prosrc)
    into s
    from pg_proc p join pg_namespace n on n.oid = p.pronamespace
   where n.nspname = 'public' and p.proname = 'record_artifact';
  execute s;
end $$;
SQL
  after_a=$(db "${PREFIX}_argdef" -c "$argsql")
  after_n=$(db "${PREFIX}_argdef" -c "$narrow")
  echo "     p_md_hash: $(echo "$before_a" | grep -o 'p_md_hash[^,)]*') -> $(echo "$after_a" | grep -o 'p_md_hash[^,)]*')"
  if [ -z "$before_a" ] || [ -z "$before_n" ] || [ -z "$after_n" ]; then
    echo "  ✗ A PROBE RETURNED NOTHING — the narrowness check cannot run, so a CAUGHT verdict here"
    echo "    would be unearned. treat mutation 21 as NOT RUN"; fail=1
  elif [ "$before_a" = "$after_a" ]; then
    echo "  ✗ THE DEFAULT DID NOT CHANGE — treat mutation 21 as NOT RUN"; fail=1
  elif [ "$before_n" != "$after_n" ]; then
    # ⭐ WITHOUT THIS, A CAUGHT VERDICT PROVES NOTHING. If the rebuild also moved prosrc, prosecdef,
    # proconfig or the identity args, the gate would have gone red on a column it already digested
    # in round 5 — and the r7 finding would read as fixed while the narrow case stayed invisible.
    echo "  ✗ THE MUTATION IS NOT NARROW — identity/body/secdef/config/volatility also moved:"
    echo "      before: $before_n"
    echo "      after:  $after_n"
    echo "    treat mutation 21 as NOT RUN"; fail=1
  else
    gate "${PREFIX}_argdef" --expect-present && r=pass || r=fail
    report "an argument DEFAULT changed, NOTHING else -> --expect-present FAILS" fail "$r"
  fi
fi

echo "═══ mutation 23 ⭐⭐⭐ step 5: anon EXECUTE on an M4 function — the OTHER half that left ═══"
# `FN_GRANTEES` left the digest in step 5, so RULE 3's function half is now the ONLY thing asserting
# that no session role can call an M4 function. On production the platform grants EXECUTE at CREATE
# time, so this is not a hypothetical sabotage — it is the state the schema ARRIVES IN unless the
# revoke lands. Both gates are asserted: the digest is blind (correctly), RULE 3 is not.
if fresh "${PREFIX}_fnacl"; then
  before_f=$(db "${PREFIX}_fnacl" -c "select has_function_privilege('anon','public.slot_kind(text)','EXECUTE')::text;" | tr -d '[:space:]')
  db "${PREFIX}_fnacl" -v ON_ERROR_STOP=1 >/dev/null 2>&1 <<'SQL'
grant execute on function slot_kind(text) to anon;
SQL
  after_f=$(db "${PREFIX}_fnacl" -c "select has_function_privilege('anon','public.slot_kind(text)','EXECUTE')::text;" | tr -d '[:space:]')
  echo "     anon EXECUTE on slot_kind: ${before_f:-<empty>} -> ${after_f:-<empty>}"
  if [ -z "$before_f" ] || [ -z "$after_f" ]; then
    echo "  ✗ A PROBE RETURNED NOTHING — treat mutation 23 as NOT RUN"; fail=1
  elif [ "$before_f" = "$after_f" ]; then
    echo "  ✗ THE GRANT DID NOT LAND — treat mutation 23 as NOT RUN"; fail=1
  else
    anon_control "$TPL" "M4 FN EXECUTABLE" && r=pass || r=fail
    report "CONTROL: an unmutated M4 does not report slot_kind as session-executable" pass "$r"
    gate "${PREFIX}_fnacl" --expect-present && r=pass || r=fail
    report "anon EXECUTE on an M4 function -> the DIGEST no longer claims to see it" pass "$r"
    anon_gate "${PREFIX}_fnacl" "M4 FN EXECUTABLE" && r=pass || r=fail
    report "anon EXECUTE on an M4 function -> RULE 3 names M4 FN EXECUTABLE" pass "$r"
  fi
fi

echo "═══ mutation 24 ⭐⭐⭐⭐ r8 B1 (claude): a total session-role READ OUTAGE ═══"
# THE POLARITY THE WHOLE INSTRUMENT WAS MISSING. Every mutation above asks whether a privilege was
# ADDED. The digest that was removed carried BOTH directions — SELECT was in REL_PRIVS, so a revoke
# moved it. MEASURED at 522e766, one statement, all three instruments green over a database on which
# no logged-in user can read a single M4 row.
# ⚠ ADR-0012 makes this MORE likely: revoke-from-all-four-then-grant-back means the grant-back line
# is now the only thing between the schema and this state.
if fresh "${PREFIX}_readout"; then
  anon_control "$TPL" "M4 READ LOST" && r=pass || r=fail
  report "CONTROL: an unmutated M4 reports no lost read" pass "$r"
  before_r=$(db "${PREFIX}_readout" -c "select has_table_privilege('authenticated','video_artifacts','SELECT')::text;" | tr -d '[:space:]')
  db "${PREFIX}_readout" -v ON_ERROR_STOP=1 >/dev/null 2>&1 <<'SQL'
revoke select on video_artifacts, video_generations, workspace_videos, workspaces,
                 video_artifact_sources, video_artifacts_current, video_summary_current
  from anon, authenticated;
SQL
  after_r=$(db "${PREFIX}_readout" -c "select has_table_privilege('authenticated','video_artifacts','SELECT')::text;" | tr -d '[:space:]')
  echo "     authenticated SELECT on video_artifacts: ${before_r:-<empty>} -> ${after_r:-<empty>}"
  if [ -z "$before_r" ] || [ -z "$after_r" ]; then
    echo "  ✗ A PROBE RETURNED NOTHING — treat mutation 24 as NOT RUN"; fail=1
  elif [ "$before_r" = "$after_r" ]; then
    echo "  ✗ THE REVOKE DID NOT LAND — treat mutation 24 as NOT RUN"; fail=1
  else
    gate "${PREFIX}_readout" --expect-present && r=pass || r=fail
    report "a total read outage -> the DIGEST cannot see it (this is the trade)" pass "$r"
    anon_gate "${PREFIX}_readout" "M4 READ LOST" && r=pass || r=fail
    report "a total read outage -> RULE 3 names M4 READ LOST" pass "$r"
  fi
fi

echo "═══ mutation 26 ⭐⭐⭐⭐ r9 B1 (claude): a read outage with a ONE-COLUMN grant-back ═══"
# STRICTLY MORE REACHABLE THAN MUTATION 24. That one needs a grant-back to be FORGOTTEN; this one
# needs it to be WRITTEN WITH A COLUMN LIST, which is how people narrow a grant. The read rule used
# the UNION of table- and column-level privileges, so one surviving column kept SELECT in the set and
# the rule fell silent while every `select *` raised 42501.
if fresh "${PREFIX}_colread"; then
  anon_control "$TPL" "M4 READ LOST" && r=pass || r=fail
  report "CONTROL: an unmutated M4 reports no lost read (column split)" pass "$r"
  db "${PREFIX}_colread" -v ON_ERROR_STOP=1 >/dev/null 2>&1 <<'SQL'
revoke select on video_artifacts, video_generations, workspace_videos, workspaces,
                 video_artifact_sources, video_artifacts_current, video_summary_current
  from anon, authenticated;
grant select (workspace_id) on video_artifacts        to anon, authenticated;
grant select (workspace_id) on video_generations      to anon, authenticated;
grant select (workspace_id) on workspace_videos       to anon, authenticated;
grant select (id)           on workspaces             to anon, authenticated;
grant select (workspace_id) on video_artifact_sources to anon, authenticated;
grant select (workspace_id) on video_artifacts_current to anon, authenticated;
grant select (workspace_id) on video_summary_current  to anon, authenticated;
SQL
  tbl_c=$(db "${PREFIX}_colread" -c "select has_table_privilege('authenticated','video_artifacts','SELECT')::text;" | tr -d '[:space:]')
  col_c=$(db "${PREFIX}_colread" -c "select has_any_column_privilege('authenticated','video_artifacts','SELECT')::text;" | tr -d '[:space:]')
  echo "     authenticated on video_artifacts: table=$tbl_c  any-column=$col_c  (the whole point)"
  if [ "$tbl_c" != "false" ] || [ "$col_c" != "true" ]; then
    echo "  ✗ THE MUTATION DID NOT PRODUCE THE COLUMN-ONLY STATE — treat mutation 26 as NOT RUN"; fail=1
  else
    anon_gate "${PREFIX}_colread" "M4 READ LOST" && r=pass || r=fail
    report "a column-only grant-back -> RULE 3 still names M4 READ LOST" pass "$r"
  fi
fi

echo "═══ mutation 27 ⭐⭐⭐⭐ r9 H2 (claude): a SIXTH policy opens every tenant's manifest ═══"
# RLS IS PERMISSIVE-OR, so ONE added `using (true)` policy defeats all five owner-scoping policies at
# once WITHOUT TOUCHING ANY OF THEM. Present mode is MANIFEST ⊆ live and ignores extra objects — true
# of most extra objects, FALSE of one ATTACHED to a manifest relation, which is a MODIFICATION of that
# relation. r6 H1 acted on that sentence for pg_rewrite and only for pg_rewrite.
# MEASURED before the fix: anon went from 0 rows to reading another tenant's blob_key, and the digest
# printed "M4 is PRESENT as expected … 5 policies" over a database holding six.
if fresh "${PREFIX}_pol"; then
  before_p=$(db "${PREFIX}_pol" -c "select count(*) from pg_policy pol join pg_class c on c.oid=pol.polrelid where c.relname='video_artifacts';" | tr -d '[:space:]')
  db "${PREFIX}_pol" -v ON_ERROR_STOP=1 >/dev/null 2>&1 <<'SQL'
create policy r9_wide on video_artifacts for select to anon, authenticated using (true);
SQL
  after_p=$(db "${PREFIX}_pol" -c "select count(*) from pg_policy pol join pg_class c on c.oid=pol.polrelid where c.relname='video_artifacts';" | tr -d '[:space:]')
  echo "     policies on video_artifacts: ${before_p:-<empty>} -> ${after_p:-<empty>}"
  if [ -z "$before_p" ] || [ "$before_p" = "$after_p" ]; then
    echo "  ✗ THE POLICY DID NOT LAND — treat mutation 27 as NOT RUN"; fail=1
  else
    gate "${PREFIX}_pol" --expect-present && r=pass || r=fail
    report "a SIXTH policy on video_artifacts -> --expect-present FAILS" fail "$r"
  fi
fi

echo "═══ mutation 25 ⭐⭐ r8 H1 (claude): SELECT on the OUT-OF-REACH relation ═══"
# The rule always said "any session-role privilege here is a defect". The FETCH could not feed it:
# SELECT was in neither probe list, so `held` was empty and the branch never fired — while a
# self-test case built from the hand-typed fixture "SELECT," passed in green over the gap.
if fresh "${PREFIX}_oor"; then
  anon_control "$TPL" "M4 OUT OF REACH" && r=pass || r=fail
  report "CONTROL: an unmutated M4 reports no out-of-reach privilege" pass "$r"
  before_o=$(db "${PREFIX}_oor" -c "select has_table_privilege('anon','video_generations_collectable','SELECT')::text;" | tr -d '[:space:]')
  db "${PREFIX}_oor" -v ON_ERROR_STOP=1 >/dev/null 2>&1 <<'SQL'
grant select on video_generations_collectable to anon;
SQL
  after_o=$(db "${PREFIX}_oor" -c "select has_table_privilege('anon','video_generations_collectable','SELECT')::text;" | tr -d '[:space:]')
  echo "     anon SELECT on the collectable view: ${before_o:-<empty>} -> ${after_o:-<empty>}"
  if [ -z "$before_o" ] || [ "$before_o" = "$after_o" ]; then
    echo "  ✗ THE GRANT DID NOT LAND — treat mutation 25 as NOT RUN"; fail=1
  else
    anon_gate "${PREFIX}_oor" "M4 OUT OF REACH" && r=pass || r=fail
    report "SELECT on the out-of-reach view -> RULE 3 names M4 OUT OF REACH" pass "$r"
  fi
fi

echo "═══ mutation 28 ⭐⭐⭐⭐ a DOMAIN type — the manifest never enumerates it ═══"
# CATALOG_SQL's type arm is `where n.nspname='public' and t.typtype='e'`. A DOMAIN is not an enum, so
# it is not digested WRONGLY — it is ABSENT, and present mode (MANIFEST ⊆ live) cannot see an object
# it never enumerated. A domain's CHECK decides whether a write is admitted, so this is a guard the
# gate is structurally blind to.
# The exclusion reason for rule 10 covers this by asserting "M4 creates exactly one type, an enum".
# That is a PREMISE ABOUT THIS SCHEMA, true when written and re-read by nothing until 2026-08-26.
# ⭐ BOTH HALVES ARE ASSERTED. One would not distinguish "coverage moved" from "coverage deleted".
if fresh "${PREFIX}_dom"; then
  before_t=$(db "${PREFIX}_dom" -c "select count(*) from pg_type t join pg_namespace n on n.oid=t.typnamespace where n.nspname='public' and t.typtype='d';" | tr -d '[:space:]')
  db "${PREFIX}_dom" -v ON_ERROR_STOP=1 >/dev/null 2>&1 <<'SQL'
create domain public.m4_mut_positive as integer check (value > 0);
SQL
  after_t=$(db "${PREFIX}_dom" -c "select count(*) from pg_type t join pg_namespace n on n.oid=t.typnamespace where n.nspname='public' and t.typtype='d';" | tr -d '[:space:]')
  echo "     domain types in public: ${before_t:-<empty>} -> ${after_t:-<empty>}"
  if [ -z "$before_t" ] || [ "$before_t" = "$after_t" ]; then
    echo "  ✗ THE DOMAIN DID NOT LAND — treat mutation 28 as NOT RUN"; fail=1
  else
    premise_control "$TPL" && r=pass || r=fail
    report "CONTROL: an unmutated M4 template satisfies every premise" pass "$r"
    gate "${PREFIX}_dom" --expect-present && r=pass || r=fail
    report "a DOMAIN type -> the DIGEST is blind and still PASSES" pass "$r"
    premise_gate "${PREFIX}_dom" && r=pass || r=fail
    report "a DOMAIN type -> the rule-10 PREMISE breaks and gate 13 FAILS" pass "$r"
  fi
fi

echo "═══ mutation 29 ⭐⭐⭐ a PARTITIONED table — relkind 'p' is never selected ═══"
# Same shape one catalog over: CATALOG_SQL's table arm is `c.relkind='r'`, so relkind 'p' is absent
# from the manifest entirely. Rule 8's written reason claims these columns are WHERE-clause filters —
# TRUE of attisdropped and tgisinternal, and FALSE of `relpartbound`, which appears NOWHERE in
# CATALOG_SQL. Its real reason is the premise that M4 has no partitions.
if fresh "${PREFIX}_part"; then
  before_pt=$(db "${PREFIX}_part" -c "select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='public' and (c.relkind='p' or c.relispartition);" | tr -d '[:space:]')
  db "${PREFIX}_part" -v ON_ERROR_STOP=1 >/dev/null 2>&1 <<'SQL'
create table public.m4_mut_part (id int, k text) partition by range (id);
SQL
  after_pt=$(db "${PREFIX}_part" -c "select count(*) from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname='public' and (c.relkind='p' or c.relispartition);" | tr -d '[:space:]')
  echo "     partitioned tables/partitions in public: ${before_pt:-<empty>} -> ${after_pt:-<empty>}"
  if [ -z "$before_pt" ] || [ "$before_pt" = "$after_pt" ]; then
    echo "  ✗ THE PARTITIONED TABLE DID NOT LAND — treat mutation 29 as NOT RUN"; fail=1
  else
    gate "${PREFIX}_part" --expect-present && r=pass || r=fail
    report "a PARTITIONED table -> the DIGEST is blind and still PASSES" pass "$r"
    premise_gate "${PREFIX}_part" && r=pass || r=fail
    report "a PARTITIONED table -> the rule-8 PREMISE breaks and gate 13 FAILS" pass "$r"
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
