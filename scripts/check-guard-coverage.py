#!/usr/bin/env python3
"""Ratchet: every guard in the blob-addressing schema is CLASSIFIED, and every
SEQUENCE guard is mutation-covered.

WHY THIS EXISTS
---------------
Two defects survived seven rounds of adversarial review, and neither was a wrong
line anywhere — both were ABSENCES. The free-render path had no reconciler because
no fixture ever wrote a free slot twice; the retention sweep could never run because
its safety rule aborted the batch.

Every other instrument this project owns is OPT-IN. An assertion exists because
someone thought of the case; a mutation because someone wrote one; a review finds
what a reviewer looked at. So they do not have independent blind spots — they share
ONE, and anything nobody thought of is invisible to all of them simultaneously.

An absence is only visible against an ENUMERATED WHOLE. This script enumerates the
whole from `pg_catalog` — the live schema, not a list someone maintains — so a guard
added tomorrow cannot be silently unclassified.

THE CLASSIFICATION (docs/dev-process.md, between-rounds step 4)
--------------------------------------------------------------
  SHAPE    - is this row well-formed and referentially sound?  A violation is a
             CALLER BUG.  Rejecting is correct.
  SEQUENCE - who got here first?  has this already happened?  is this in flight?
             A violation is CONCURRENCY: the caller did nothing wrong and may
             already have spent money.  It must RECONCILE - an upsert, a no-op, or
             a typed outcome - never a raw rejection.

The one question to ask of each guard is NOT "is it correct?" (both defects were in
guards that are plainly correct) but "what does it do when the caller is merely
SECOND?"

Usage:  ./scripts/check-guard-coverage.py     (exit 0 = every guard classified)
    --self-test  # 34 cases
"""
import ast
import re
import subprocess
import sys
from pathlib import Path

from subject_status import subject_banner

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "docs/superpowers/specs/2026-08-03-stable-blob-addressing"
SCHEMA = SPEC / "schema"
MUTATIONS = SPEC / "mutate-schema.py"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from m4_base_db import read_catalog  # noqa: E402

TABLES = ("video_artifacts", "video_generations")

# ⟳ ROUND 9 — THE ENUMERATED WHOLE WAS ITSELF SCOPED TOO NARROWLY, which is this script's own
# thesis used against it. Round 9's B3 fix added `resolve_workspace_from_playlist` as a trigger on
# `videos` and `jobs`; this ratchet enumerated triggers on TWO tables, so it reported ✅ and "32
# guards" with a brand-new guard sitting outside its query. `sync_corrections_to_workspace_video`
# (round 6) had been invisible the same way since the day this script was written.
#
# An absence is only visible against an enumerated whole — and the whole has to be "every table this
# spec puts a guard on", not the two that were interesting the day the query was typed.
# ⟳ 2026-09-14 (backlog #29, whose trigger fired when the schema gates reached CI) —
# `video_artifact_sources` WAS MISSING, and this is the THIRD time this list has been too
# short while the gate printed "every guard classified". Round 9 added four tables after
# `resolve_workspace_from_playlist` was invisible; round 11 fixed the FK clause for the same
# reason; this is the same defect on the table 04_artifacts.sql adds LAST.
# ⚠ NOT A MIGRATIONS PROBLEM — `video_artifact_sources` is created by M4's own schema files,
# so the gate BUILT it and then declined to look at it. MEASURED against a fully migrated
# database: three trigger functions on it, none of them in GUARDS, gate green at 41 guards.
# ⛔⛔ TWO SETS, AND THE SPLIT IS THE SCOPE DECISION backlog #29 ASKED FOR.
# ⟳ r1 (codex Medium + claude, 2026-09-14). Making all four clauses read ONE set was the first fix
# and it was wrong in the other direction: it pulled in 17 guards including `jobs_status_chk`,
# `playlists_pkey` and `videos_check` — pre-existing objects on tables M4 merely ADDS TRIGGERS TO.
# A blob-addressing ratchet classifying the jobs queue's own CHECKs is the overclaiming Codex named.
#
# The line that is actually defensible is the one M4's own manifest already draws:
#   OWNED    — relations M4 CREATES. Every guard on them is M4's, so all four clauses apply.
#              Derived from the manifest's `table:` entries, not hand-listed (check-live-schema.py
#              learned the same lesson: a hand-maintained list of what to check silently stops
#              matching).
#   FOREIGN  — `videos`, `jobs`, `playlists`, `profiles`. M4 adds TRIGGERS and FKs here and owns
#              nothing else, so only those two clauses apply. Their PKs and CHECKs predate M4 and
#              belong to whatever gate owns those tables — today, none. That gap is REAL and is
#              recorded in backlog #29, not papered over by pretending this gate covers it.
OWNED_TABLES = ("workspaces", "workspace_videos", "video_generations", "video_artifacts",
                "video_artifact_sources")
FOREIGN_TABLES = ("videos", "jobs", "playlists", "profiles")
TRIGGER_TABLES = OWNED_TABLES + FOREIGN_TABLES

# Every guard the schema ships, with its class. A guard present in the database and
# absent here FAILS THE RATCHET - that is the whole point: adding a guard forces a
# classification decision rather than allowing one to be skipped.
#
# `note` is required for SEQUENCE guards and records HOW it reconciles, because
# "this one is fine" is exactly the judgement that needs to survive the next reader.
GUARDS: dict[str, tuple[str, str]] = {
    # ── video_artifacts: SHAPE (well-formedness / referential integrity) ─────────
    "art_slot_kind":               ("SHAPE", ""),
    "art_paid_has_generation":     ("SHAPE", ""),
    # ⛔ FOUR ENTRIES STOOD HERE UNTIL T5 (2026-08-26): art_pending_is_leased, art_pending_has_token,
    # art_pending_has_reserved_at and art_summary_has_no_source. The first three were the RESERVATION
    # protocol ADR-0007 deleted; the fourth became a branch of the T3 provenance enforcer rather than
    # a constraint. All four were VERIFIED ABSENT from the schema before deletion, not assumed.
    "art_dig_has_span":            ("SHAPE", ""),
    "art_detached_is_dig":         ("SHAPE", ""),
    "art_detached_has_timestamp":  ("SHAPE", ""),
    "art_key_names_generation":    ("SHAPE", ""),
    "art_key_names_workspace":     ("SHAPE", ""),   # ⟳ round 9 H5; applies to FREE rows too
    # ── video_generations: SHAPE ────────────────────────────────────────────────
    "gen_complete_has_produced_at": ("SHAPE", ""),
    "gen_card_complete":            ("SHAPE", ""),
    "gen_summary_has_format":       ("SHAPE", ""),
    "gen_summary_has_hash":         ("SHAPE", ""),
    "gen_major_matches_card":       ("SHAPE", ""),
    # ⟳ T5 (2026-08-26): both reached the schema unclassified. `check (kind = 'summary' or X is null)`
    # reads only the row being written, so a merely-SECOND caller inserting a well-formed row is
    # untouched — SHAPE. Mutations 36 and 37 already covered them; only the decision was missing.
    "gen_card_is_summary_only":     ("SHAPE", ""),
    "gen_major_is_summary_only":    ("SHAPE", ""),
    # Auto-named inline CHECKs. Found by this ratchet on its first run — they had been
    # in the schema since round 4 and were never in anyone's mental inventory, which is
    # the exact failure mode it exists to remove.
    "video_artifacts_state_check":   ("SHAPE", ""),
    "video_generations_state_check": ("SHAPE", ""),
    # ── SEQUENCE: each must reconcile, and say how ──────────────────────────────
    # ⛔ `video_artifacts_inflight_uq` STOOD HERE — the reservation protocol's slot lock, deleted by
    # ADR-0007 along with reserve_artifact_slot. VERIFIED ABSENT from the schema before deletion.
    "video_artifacts_paid_uq": (
        "SEQUENCE",
        "record_artifact: on conflict do update (round 7 B1) - a restarted worker records in place"),
    "video_artifacts_free_uq": (
        "SEQUENCE",
        "record_artifact's free branch upserts, so a re-render overwrites (round 8 C1)"),
    # ── triggers, by function name ──────────────────────────────────────────────
    "video_artifacts_append_only":         ("SHAPE", ""),
    "video_artifacts_generation_complete": ("SHAPE", ""),
    "video_generations_freeze":            ("SHAPE", ""),
    "set_videos_updated_at":               ("SHAPE", ""),
    "guard_is_anonymous":                  ("SHAPE", ""),   # immutable field; a change is a caller bug
    # ── ⟳ ROUND 9 (round 8 M2): SHAPE *ONLY BECAUSE* SOMETHING ELSE RECONCILES ──
    # A guard is SHAPE given a reconciler, and the old two-way label stored that conclusion while
    # discarding its premise — so the reconcilers holding a SHAPE guard back from rejecting a
    # blameless second caller were exactly what nothing protected. These must name the reconciler
    # AND be mutation-covered, on the same terms as SEQUENCE.
    "resolve_workspace_from_playlist": (
        "SHAPE(reconciled)",
        "the manifest parent is `on conflict do nothing` — the same video in a SECOND playlist is a "
        "second videos row and ONE shared body, so the later insert must not collide or clobber"),
    "ensure_workspace_for_profile": (
        "SHAPE(reconciled)",
        "`on conflict (owner_id) do nothing` — every profile 01's seed already covered reaches this "
        "trigger too, and must not error on the workspace it already has"),
    # ⛔ `sync_corrections_to_workspace_video` STOOD HERE, classified SHAPE(reconciled) because its
    # INSERT half's WHEN clause skipped rows carrying no corrections — without it, the same video
    # added to a second playlist CLOBBERED the shared corrections (measured round 9). ADR-0011 (T2)
    # deletes the trigger and the denormalized copy it synchronised, so the reconciler has nothing
    # left to reconcile. VERIFIED ABSENT by this ratchet reporting it STALE before deletion.
    # ── ⟳ r1 (2026-09-14): the KEYS, visible for the first time once all four clauses read one set.
    # Each is classified from its WRITER, not its name — `pg_get_constraintdef` for the shape, then
    # the insert that can hit it. The reconciler for a key is almost always an `on conflict` arbiter,
    # and naming which one is the whole value of the entry.
    "workspaces_owner_id_fkey":  ("SHAPE", ""),   # FK -> profiles(id); reads the row being written
    "workspaces_owner_id_key": (
        "SEQUENCE",
        "ensure_workspace_for_profile inserts `values (new.id, new.id) on conflict (owner_id) do "
        "nothing` (03_generations.sql:143-144) — a second provisioning of the same profile is "
        "absorbed, not raised"),
    "workspaces_pkey": (
        "SHAPE",
        "id = owner_id for every row this schema writes, so a duplicate conflicts on the OWNER_ID "
        "arbiter first and the no-op above absorbs it: the SEQUENCE question has no reachable case, "
        "rather than a reconciler of its own (the idiom video_artifacts_identity_uq already uses)"),
    "workspaces_id_owner_id_key": (
        "SHAPE",
        "UNIQUE(id, owner_id) is implied by the two single-column keys above for every row this "
        "schema writes; it cannot fire before one of them does"),
    "workspace_videos_pkey": (
        "SEQUENCE",
        "the manifest-parent trigger inserts `on conflict (workspace_id, video_id) do nothing` "
        "(03_generations.sql:183-185) — two videos arriving at once leave one parent, not an error"),
    "video_generations_pkey": (
        "SEQUENCE",
        "record_artifact inserts the generation `on conflict (workspace_id, video_id, generation_id) "
        "do nothing` (04_artifacts.sql:447) — the second writer of a generation continues rather "
        "than raising, which is what makes a crash-retry safe"),
    "video_generations_workspace_id_video_id_generation_id_kind_key": (
        "SHAPE",
        "UNIQUE(ws, vid, gen, kind) is WEAKER than the PK(ws, vid, gen) above — any row the PK "
        "admits is already distinct here — so it cannot fire before the PK does"),
    "video_artifacts_pkey": (
        "SHAPE",
        "artifact_id is generated per insert and no writer uses it as a conflict arbiter (the two "
        "upserts arbitrate on the slot keys, 04_artifacts.sql:384 and :540), so a second caller "
        "never presents the same value: no reachable case"),
    "video_artifact_sources_pkey": (
        "SEQUENCE",
        "⭐ THE RECONCILER FOR insert_once, AND THE REASON THAT GUARD'S NOTE HAD TO CHANGE: a "
        "same-set re-statement inserts NOTHING here, so insert_once's transition table is empty and "
        "it never fires. 04_artifacts.sql:606-607 says that path 'is the path a crash-retry takes "
        "and must NOT be refused'. One row per (artifact, source), 04_artifacts.sql:231"),

    # ── video_artifact_sources ⟳ 2026-09-14: reached the schema unclassified because the TABLE was
    # outside TRIGGER_TABLES, not because anyone judged them. ⚠ `art_summary_has_no_source` is the
    # sharpest case: the deletion note above records it verified ABSENT as a CONSTRAINT in T5 — true,
    # and it was reborn the same day as a constraint TRIGGER, which nothing re-enumerated.
    # ⟳ 2026-09-14: the two FKs surfaced with the table — the FK clause is DERIVED from
    # TRIGGER_TABLES (round 11 made it so, for exactly this reason), so widening the trigger
    # list widened this too. Referential integrity reads only the row being written.
    "vas_artifact_fk":                    ("SHAPE", ""),
    "vas_source_generation_fk":           ("SHAPE", ""),
    "video_artifact_sources_append_only": (
        "SHAPE",
        "⟳ r1 MEDIUM (claude): the reason here used to read 'rejects the operation itself', which is "
        "true of the UPDATE half and FALSE of the DELETE half — that one raises only `if exists` an "
        "artifact for the row (04_artifacts.sql:1111-1117), which is a sequencing question wearing a "
        "well-formedness sentence. SHAPE is kept because the reviewer measured the blameless caller "
        "OUT of reach, not because the guard is unconditional: deleting a generation that owns an "
        "artifact dies first on video_artifacts' own FK (23503), and `delete from workspace_videos` "
        "dies earlier still on video_artifacts' append-only trigger (P0001). The remaining reachable "
        "case is a future §8 sweeper deleting source-only generations — so, in this file's own idiom "
        "(video_artifacts_identity_uq), the SEQUENCE question has no reachable case rather than a "
        "reconciler. What must not survive is a sentence that stops the next reader opening the body"),
    "art_summary_has_no_source":          ("SHAPE", ""),   # reads the inserted row and its parent's
                                                           # kind; a merely-SECOND caller inserting a
                                                           # well-formed row is untouched
    "video_artifact_sources_insert_once": (
        "SEQUENCE",
        "⟳ r1 HIGH (claude): this note used to say it does NOT reconcile and that 'no retry succeeds'. "
        "MEASURED false. The reconciler is TWO-PART — `video_artifact_sources_pkey` plus "
        "`record_artifact`'s same-set no-op (04_artifacts.sql:597-607): an idempotent re-statement "
        "inserts NOTHING, so the transition table is empty and this trigger never fires, and :606 "
        "says that path 'is the path a crash-retry takes and must NOT be refused'. Only a second "
        "statement that CHANGES the set is a caller bug; the error names both sets so the loser can "
        "see what it collided with. ⚠ The old note made this the first RECONCILING member naming no "
        "reconciler — delete record_artifact's same-set branch and the ratchet would have endorsed it"),
    "forbid_collecting_current": (
        "SEQUENCE",
        "the sweeper selects THROUGH video_generations_collectable; trigger kept as a backstop "
        "for direct writes, deliberately NOT softened to a silent no-op (round 8 C3)"),
    # ── foreign keys are structural, never mutated; named explicitly, not skipped ─
    "video_artifacts_workspace_id_video_id_fkey":                    ("SHAPE", ""),
    "video_artifacts_workspace_id_video_id_generation_id_kind_fkey": ("SHAPE", ""),
    # ⛔ `…_source_generation_id_fkey` STOOD HERE. T3 moved provenance onto `video_artifact_sources`,
    # so `source_generation_id` no longer exists ON `video_artifacts` — it lives on the join table
    # (04_artifacts.sql:230), whose own FK is classified below. VERIFIED before deletion: the column
    # survives, the FK on THIS table does not, and the name is what went stale.
    # ⟳ T5: a UNIQUE constraint that is a SUPERSET OF THE PRIMARY KEY, and therefore SHAPE.
    # `artifact_id` is `gen_random_uuid()` and is itself the PK (04_artifacts.sql:90-91); this states
    # the wider tuple only so `video_artifact_sources` can reference it (the schema says so at :99).
    # It cannot reject a merely-SECOND caller that the PK would admit, because a second caller draws
    # a different uuid — so the SEQUENCE question has no reachable case, rather than a reconciler.
    "video_artifacts_identity_uq": (
        "SHAPE",
        "superset of the PK on a gen_random_uuid() surrogate; exists as an FK target, not a lock"),
    "video_generations_workspace_id_video_id_fkey":                  ("SHAPE", ""),
    "workspace_videos_workspace_id_fkey":                            ("SHAPE", ""),
    "videos_workspace_video_fk":                                     ("SHAPE", ""),
    # Pre-existing FKs on `videos`, not added by this spec. Classified rather than
    # filtered out of the query: an exclusion is a place a real guard can hide, and
    # naming them costs two lines.
    "videos_playlist_id_owner_id_fkey":                              ("SHAPE", ""),
    "videos_workspace_id_fkey":                                      ("SHAPE", ""),
    # ⟳ ROUND 11 — surfaced the moment the FK clause stopped being a second hand-written list.
    # All referential and structural: a violation means the caller named a parent that is not
    # theirs or does not exist, which is a caller bug at any ordering. Note two of them
    # (`jobs_workspace_owner_fk`, `jobs_playlist_owner_fk`) are §14 Q6's CROSS-TENANT guards —
    # they had been outside every inventory this project keeps.
    "jobs_owner_id_fkey":                                            ("SHAPE", ""),
    "jobs_playlist_owner_fk":                                        ("SHAPE", ""),
    "jobs_workspace_id_fkey":                                        ("SHAPE", ""),
    "jobs_workspace_owner_fk":                                       ("SHAPE", ""),
    "playlists_owner_id_fkey":                                       ("SHAPE", ""),
    "playlists_workspace_id_fkey":                                   ("SHAPE", ""),
    "profiles_id_fkey":                                              ("SHAPE", ""),
}

# A SEQUENCE guard whose reconciler cannot be mutation-tested must say why here.
# Empty by design: if this grows, the ratchet is being talked out of rather than met.
MUTATION_EXEMPT: dict[str, str] = {
    # ⟳ r1 (2026-09-14). These three became visible when all four CATALOG_SQL clauses started reading
    # one set. Their reconcilers are REAL and named in GUARDS — each is an `on conflict … do nothing`
    # I read in the writer — but the ASSERTION CORPUS does not exercise the path, so a mutation that
    # removes the reconciler goes GREEN. That was MEASURED, not assumed: all three were written as
    # mutations, run, and reported `❌ GREEN`, which is why they are not in the mutation file
    # pretending to cover something.
    #
    # ⚠ WHY EACH PATH IS UNREACHED, because "the corpus does not test it" is not a reason on its own:
    "workspaces_owner_id_key":
        "the trigger's insert can only conflict when a workspace for that owner ALREADY exists, and "
        "a profile cannot be inserted twice (profiles_pkey fires first). Reaching it needs a "
        "workspace created before its profile row — a restore/replay shape the corpus never builds",
    "workspace_videos_pkey":
        "same shape one table over: the manifest-parent insert conflicts only when the (workspace, "
        "video) pair already exists, which the corpus only ever creates through this same trigger",
    "video_generations_pkey":
        "an identical retry short-circuits on `v_existed` before reaching the generation insert "
        "(04_artifacts.sql), so the corpus's idempotent-retry assertion never re-inserts the "
        "generation. Reaching it needs TWO SLOTS recorded against ONE generation",
}

# Both classes carry the same obligations: name the reconciler, and mutate it. The distinction is
# only about who is at fault when the guard fires — never about how much proof it needs.
RECONCILING = {"SEQUENCE", "SHAPE(reconciled)"}

# Which mutation LABELS must exist for a guard, when the guard's own name is not in them.
# A guard absent from here is required to appear in a label verbatim.
COVERED_BY: dict[str, tuple[str, ...]] = {
    "resolve_workspace_from_playlist":     ("B3: workspace_id no longer derived",
                                            "B3: the manifest parent no longer created",
                                            "B3: a disagreeing workspace_id"),
    "ensure_workspace_for_profile":        ("B3: a new profile gets no workspace",),
    # ⛔ `sync_corrections_to_workspace_video` STOOD HERE, pointing at the two mutation labels
    # "the anti-drift trigger removed" and "the INSERT-half sync unguarded". ADR-0011 (T2) retired
    # the guard AND both mutations, so this entry named three things that no longer exist.
    # ⭐ FOUND BY --self-test ("every COVERED_BY key is a classified guard"), not by reading: the
    # LIVE ratchet went green the moment the guard left GUARDS, because its subject is the schema.
    # This map is a second inventory keyed on the first, and only the self-test compares them.
}

# ⛔⛔ ONE SET, FOUR CLAUSES — ⟳ r1 BLOCKING (codex AND claude, independently, 2026-09-14).
# This query had FOUR clauses reading THREE different scopes: CHECKs on `TABLES`, FKs and triggers on
# `TRIGGER_TABLES`, unique indexes on `TABLES` **and only if named `%_uq`**. Widening one clause is
# what round 9 did, and round 11, and what the first version of this branch did — three times a table
# entered the gate's world through one clause and stayed invisible to the others, while the script
# printed "every guard classified".
# MEASURED here, by widening only the two left behind:
#     jobs.jobs_kind_chk · jobs.jobs_progress_phase_check · jobs.jobs_status_chk · videos.videos_check
#     video_artifact_sources.video_artifact_sources_pkey                                 [p]
#     video_generations.video_generations_workspace_id_video_id_generation_id_kind_key   [u]
# ⚠ THE LAST ONE IS THE ARGUMENT AGAINST A NAME FILTER: `video_generations` was ALREADY in `TABLES`.
# The only thing hiding that unique constraint was `like '%_uq'` — a NAMING CONVENTION acting as a
# scope rule, so a guard that declines to be named `_uq` is not a guard. It is gone.
# ⚠ AND THE PK IS NOT A FORMALITY: `04_artifacts.sql:231` documents it as the rule "One row per
# (artifact, source)", and it is the RECONCILER that makes `insert_once`'s same-set retry succeed
# (see that guard's note). The gate could not see the object its own classification rests on.
CATALOG_SQL = f"""
select 'check:' || conname from pg_constraint
 where conrelid = any (array{list(OWNED_TABLES)}::regclass[]) and contype = 'c'
union all
-- ⟳ ROUND 11 (round 10) — DERIVED FROM THE SAME SET AS THE TRIGGERS, not a second hand-written
-- list. Round 9 widened the TRIGGER enumeration to six tables and left this clause on its original
-- four, so `jobs_workspace_owner_fk` was invisible while the gate printed "every guard classified"
-- — shape #10 committed INSIDE the fix that was widening an enumeration. One list, one place.
select 'fk:' || conname from pg_constraint
 where contype = 'f'
   and connamespace = 'public'::regnamespace
   and conrelid = any (array{list(TRIGGER_TABLES)}::regclass[])
union all
select 'index:' || indexrelid::regclass::text from pg_index
 where indrelid = any (array{list(OWNED_TABLES)}::regclass[]) and indisunique
union all
select distinct 'trigger:' || p.proname from pg_trigger t
  join pg_proc p on p.oid = t.tgfoid
 where t.tgrelid = any (array{list(TRIGGER_TABLES)}::regclass[]) and not t.tgisinternal;
"""


def _clause_body(sql: str, kind: str) -> str:
    """The text of one CATALOG_SQL clause, or "" if it is not there. PURE.

    ⚠ ONE LOCATOR, TWO READERS — `clause_scopes` and `clause_predicates` both need it, and the first
    version of the second one COPIED these four lines. That made a mutation anchor ambiguous (the
    harness refuses a `find` string that matches twice) and, worse, created a second implementation
    of the rule this repo has seven recorded instances of drifting. Located by the OUTPUT PREFIX
    rather than by `select '<kind>:`, because the trigger clause is `select distinct 'trigger:'`.
    """
    start = sql.find(f"'{kind}:")
    if start < 0:
        return ""
    nxt = sql.find("union all", start)
    return sql[start:nxt if nxt > 0 else len(sql)]


def clause_scopes(sql: str) -> dict[str, list[str]]:
    """Which table set each CATALOG_SQL clause reads. PURE — no database, no filesystem.

    ⛔⛔ THE FALSIFIER FOR THE COMPONENT THAT HAD NONE — ⟳ r1 MEDIUM 2 (claude), and the measurement
    behind it is the reason this exists: all 16 self-test cases and all 5 mutation entries drive
    `evaluate`. NOTHING tested `CATALOG_SQL` or the table tuples — the one part of this script that
    was short in round 9, short in round 11, and short again in this branch's first commit. Three for
    three, in the component with no test.

    The defect is always the same and it is STRUCTURAL, not a typo: the clauses disagree about scope,
    so a table enters the gate's world through one clause and stays invisible to the others. That is
    checkable without a database — the SQL is a formatted string, and which tuple each clause
    interpolates is right there in the text.

    ⚠ This cannot prove the SET is right (that is the scope decision, argued in the tuples' own
    comment). It proves the four clauses AGREE about it, which is the failure that actually happened.
    """
    out: dict[str, list[str]] = {}
    for kind in ("check", "fk", "index", "trigger"):
        body = _clause_body(sql, kind)
        if not body:
            out[kind] = []
            continue
        # ⚠ Read the INTERPOLATED array, not every quoted literal in the clause. The first version
        # took `'c'` from `contype = 'c'` and `'public'` from the FK clause's namespace test as table
        # names — a scope check that cannot tell a table from a catalog constant proves nothing.
        m = re.search(r"array\[(.*?)\]", body, re.S)
        out[kind] = sorted(re.findall(r"'([a-z_]+)'", m.group(1))) if m else []
    return out


def clause_predicates(sql: str) -> dict[str, list[str]]:
    """The conditions each clause applies BESIDES its table array. PURE.

    ⛔ THE ARRAY IS NOT THE WHOLE SCOPE — ⟳ r2 MEDIUM (codex). `clause_scopes()` compares which tables
    a clause names, so the prior defect can return without touching it:

        where indrelid = any (array{OWNED}::regclass[]) and indisunique
          and indexrelid::regclass::text like '%_uq'      <- array unchanged, scope narrowed

    That filter is exactly what hid a unique constraint on a table already in scope, and a check that
    reads only the array reports clean while it comes back. So the PREDICATES are pinned too: each
    clause may apply the conditions its kind needs and nothing else.
    """
    out: dict[str, list[str]] = {}
    for kind in ("check", "fk", "index", "trigger"):
        body = _clause_body(sql, kind)
        if not body:
            out[kind] = []
            continue
        where = body.find("where")
        if where < 0:
            out[kind] = []
            continue
        conds = re.split(r"\band\b", body[where + 5:])
        keep = []
        for c in conds:
            c = " ".join(c.replace(";", " ").split())
            if not c or "array[" in c:          # the table array is clause_scopes()'s subject
                continue
            keep.append(c)
        out[kind] = sorted(keep)
    return out


# What each clause is ALLOWED to test besides its table array. A clause applying anything else is
# narrowing its own scope, which is the defect `_uq` was.
EXPECTED_PREDICATES: dict[str, tuple[str, ...]] = {
    "check":   ("contype = 'c'",),
    "fk":      ("connamespace = 'public'::regnamespace", "contype = 'f'"),
    "index":   ("indisunique",),
    "trigger": ("not t.tgisinternal",),
}


def scope_problems(scopes: dict[str, list[str]], owned: tuple[str, ...],
                   trigger: tuple[str, ...],
                   predicates: "dict[str, list[str]] | None" = None) -> list[str]:
    """One line per clause reading a set it should not. PURE."""
    want = {"check": sorted(owned), "index": sorted(owned),
            "fk": sorted(trigger), "trigger": sorted(trigger)}
    out = []
    if predicates is not None:
        for kind, allowed in EXPECTED_PREDICATES.items():
            extra = sorted(set(predicates.get(kind, [])) - set(allowed))
            if extra:
                out.append(f"the {kind} clause applies an extra predicate that NARROWS its scope "
                           f"without changing its table array: {extra}")
    for kind, expected in want.items():
        got = scopes.get(kind, [])
        if not got:
            out.append(f"CANNOT RUN — the {kind} clause was not found in CATALOG_SQL, so its scope "
                       f"is unknown. This check no longer reads what it claims to.")
        elif got != expected:
            missing = sorted(set(expected) - set(got))
            extra = sorted(set(got) - set(expected))
            out.append(f"the {kind} clause reads a different set than it should"
                       + (f" — missing {missing}" if missing else "")
                       + (f" — unexpected {extra}" if extra else ""))
    return out


def catalog_guards() -> set[str]:
    sql = "begin;\n"
    for f in sorted(SCHEMA.glob("0*.sql")):
        if f.name.startswith("05"):
            continue  # assertions, not schema
        sql += f.read_text() + "\n"
    sql += "\\echo ---GUARDS---\n" + CATALOG_SQL + "\nrollback;\n"
    # ⟳ 2026-08-26 — was a byte-identical copy in three ratchets, all reading `postgres`
    # directly. Once 0027 was applied there, all three died on `relation "workspaces"
    # already exists`. `read_catalog` runs it against a guaranteed pre-M4 subject.
    out = read_catalog(sql, "---GUARDS---")
    return {ln.split(":", 1)[1] for ln in out.splitlines()
            if ":" in ln and ln.split(":", 1)[0] in {"check", "fk", "index", "trigger"}}


def mutation_labels() -> list[str]:
    """The LABEL of every entry in mutate-schema.py's MUTATIONS list.

    ⟳ ROUND 9 (round 8 M1). This used to be `if name not in mutation_text` — a substring search over
    the whole file. Measured by the round-8 reviewer: every SEQUENCE guard's requirement was met by
    its name appearing inside a mutation's label string and by nothing else, so a guard name left in
    a COMMENT after its mutation was deleted would still satisfy the ratchet. The script's own
    docstring says an absence is only visible against an enumerated whole, and then verified
    coverage against free text.

    Parsed with `ast`, not regex: a mutation's `find`/`replace` strings are SQL full of guard names,
    so anything reading the file body cannot tell a label from the code being mutated.
    """
    tree = ast.parse(MUTATIONS.read_text())
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(getattr(t, "id", None) == "MUTATIONS" for t in node.targets):
            continue
        out = []
        for elt in getattr(node.value, "elts", []):
            first = getattr(elt, "elts", [None])[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                out.append(first.value)
        return out
    return []


def evaluate(
    live: set[str],
    labels: list[str],
    guards: dict | None = None,
    covered_by: dict | None = None,
    exempt=None,
) -> list[str]:
    """PURE — catalog guard names + mutation labels in, problems out. No database, no filesystem.

    Split out of main() 2026-08-19 so `--self-test` can drive the RULE without a live Postgres.
    That coupling is the whole reason this ratchet had no self-test: its only entry point needed
    docker, so "test it" read as "stand up a database". The rule never needed the container.
    """
    guards = GUARDS if guards is None else guards
    covered_by = COVERED_BY if covered_by is None else covered_by
    exempt = MUTATION_EXEMPT if exempt is None else exempt
    problems: list[str] = []

    for name in sorted(live - set(guards)):
        problems.append(
            f"UNCLASSIFIED  {name}\n"
            f"              A new guard reached the schema without a SHAPE/SEQUENCE decision.\n"
            f"              Ask: what does it do when the caller is merely SECOND?")

    for name in sorted(set(guards) - live):
        problems.append(
            f"STALE         {name}\n"
            f"              Classified here but no longer in the schema — delete the entry.")

    for name in sorted(live & set(guards)):
        kind, note = guards[name]
        if kind not in RECONCILING:
            if kind != "SHAPE":
                problems.append(
                    f"UNKNOWN KIND  {name}\n"
                    f"              '{kind}' is not one of: SHAPE, SHAPE(reconciled), SEQUENCE.")
            continue
        if not note:
            problems.append(
                f"UNJUSTIFIED   {name}\n"
                f"              {kind} guards must record HOW the second caller is reconciled.")
        if name in exempt:
            continue
        # Match the guard against mutation LABELS, never the file body (round 8 M1).
        wanted = covered_by.get(name, (name,))
        for token in wanted:
            if not any(token in label for label in labels):
                problems.append(
                    f"UNMUTATED     {name}\n"
                    f"              No mutation label contains {token!r}. Its reconciler is a claim,\n"
                    f"              not a tested behaviour — add one to mutate-schema.py.")
    return problems



# ── --self-test ─────────────────────────────────────────────────────────────────────────────────
# Added 2026-08-19 (task #54). `check-ratchet-contract.py` has listed this script as missing a
# --self-test since 2026-08-11. See `evaluate` for why it stayed missing.

def self_test() -> int:
    cases: list[tuple[str, bool]] = []

    def case(name: str, ok: bool) -> None:
        cases.append((name, ok))

    # ── ⟳ r1 MEDIUM 2 (claude): the enumeration finally has cases ────────────────────────────
    _sql = CATALOG_SQL
    _sc = clause_scopes(_sql)
    case("every clause is located, including the `select distinct` one",
         sorted(k for k, v in _sc.items() if v) == ["check", "fk", "index", "trigger"])
    case("the shipped clauses agree about scope",
         scope_problems(_sc, OWNED_TABLES, TRIGGER_TABLES) == [])
    case("a clause reading the WIDER set is caught",
         len(scope_problems({**_sc, "check": sorted(TRIGGER_TABLES)}, OWNED_TABLES, TRIGGER_TABLES)) == 1)
    case("a clause reading the NARROWER set is caught",
         len(scope_problems({**_sc, "trigger": sorted(OWNED_TABLES)}, OWNED_TABLES, TRIGGER_TABLES)) == 1)
    case("a clause that vanishes is CANNOT RUN, not a pass",
         scope_problems({**_sc, "index": []}, OWNED_TABLES, TRIGGER_TABLES)[0].startswith("CANNOT RUN"))
    case("a catalog constant is not read as a table name",
         not ("c" in _sc["check"] or "public" in _sc["fk"]))
    case("owned is a subset of trigger, or the split is incoherent",
         set(OWNED_TABLES) <= set(TRIGGER_TABLES))

    # ⟳ `check-fixture-variation.py` refused the three new parameters until a case told them apart
    # from a constant — every call above passed the same `_sql`, `OWNED_TABLES`, `TRIGGER_TABLES`.
    # These vary all three over a hand-built query, which also proves the extractor reads the SQL it
    # is given rather than the module-level one it happens to sit beside.
    _toy = ("select 'check:' || conname from pg_constraint\n"
            " where conrelid = any (array['a', 'b']::regclass[]) and contype = 'c'\n"
            "union all\n"
            "select 'fk:' || conname from pg_constraint where contype = 'f'\n"
            "   and conrelid = any (array['a', 'b', 'c']::regclass[])\n"
            "union all\n"
            "select 'index:' || indexrelid::regclass::text from pg_index\n"
            " where indrelid = any (array['a', 'b']::regclass[]) and indisunique\n"
            "union all\n"
            "select distinct 'trigger:' || p.proname from pg_trigger t\n"
            " where t.tgrelid = any (array['a', 'b', 'c']::regclass[]) and not t.tgisinternal;\n")
    # ── ⟳ r2 MEDIUM (codex): the array is not the whole scope ────────────────────────────────
    _pr = clause_predicates(CATALOG_SQL)
    case("the shipped clauses apply no predicate beyond what their kind needs",
         scope_problems(_sc, OWNED_TABLES, TRIGGER_TABLES, _pr) == [])
    case("re-adding the `_uq` filter is CAUGHT even though the array is unchanged",
         len(scope_problems(_sc, OWNED_TABLES, TRIGGER_TABLES,
                            {**_pr, "index": sorted(_pr["index"]
                                    + ["indexrelid::regclass::text like '%_uq'"])})) == 1)
    case("a narrowing predicate on any OTHER clause is caught too",
         len(scope_problems(_sc, OWNED_TABLES, TRIGGER_TABLES,
                            {**_pr, "check": sorted(_pr["check"] + ["conname like 'art_%'"])})) == 1)
    case("the table array itself is not mistaken for a predicate",
         all("array[" not in c for v in _pr.values() for c in v))
    case("each kind's own marker is present, or the clause was mis-located",
         _pr["check"] == ["contype = 'c'"] and _pr["index"] == ["indisunique"])
    # ⟳ the variation guard refused `clause_predicates.sql` until a case passed it something other
    # than CATALOG_SQL. The toy query below carries a deliberate narrowing filter, which is also the
    # only case that proves the extractor finds one in a query it has never seen.
    _toy_narrowed = ("select 'index:' || indexrelid::regclass::text from pg_index\n"
                     " where indrelid = any (array['a']::regclass[]) and indisunique\n"
                     "   and indexrelid::regclass::text like '%_uq';\n")
    case("a narrowing filter is found in a query this function has never seen",
         any("like" in c for c in clause_predicates(_toy_narrowed)["index"]))
    case("...and a clause with only its own marker reads clean",
         clause_predicates(_toy) ["check"] == ["contype = 'c'"])

    case("a DIFFERENT query is read as itself, not as CATALOG_SQL",
         clause_scopes(_toy)["check"] == ["a", "b"])
    case("...and its wider clauses are read as wider",
         clause_scopes(_toy)["trigger"] == ["a", "b", "c"])
    case("a DIFFERENT owned/trigger split is honoured",
         scope_problems(clause_scopes(_toy), ("a", "b"), ("a", "b", "c")) == [])
    case("...and the same query against the WRONG split is caught",
         len(scope_problems(clause_scopes(_toy), ("a", "b", "c"), ("a", "b", "c"))) == 2)

    SHAPE = {"g_shape": ("SHAPE", "")}
    SEQ = {"g_seq": ("SEQUENCE", "loser re-reads and retries")}

    case("a classified SHAPE guard with no mutation is fine",
         not evaluate({"g_shape"}, [], SHAPE, {}, set()))
    case("a guard in the schema but not classified is caught",
         any("UNCLASSIFIED" in x for x in evaluate({"g_shape", "g_new"}, [], SHAPE, {}, set())))
    case("the UNCLASSIFIED message asks the SEQUENCE question",
         any("merely SECOND" in x for x in evaluate({"g_new"}, [], {}, {}, set())))
    case("a classified guard no longer in the schema is STALE",
         any("STALE" in x for x in evaluate(set(), [], SHAPE, {}, set())))
    case("an unknown kind is caught",
         any("UNKNOWN KIND" in x for x in evaluate({"g"}, [], {"g": ("SHAPEY", "")}, {}, set())))

    # a reconciling guard must say HOW, and must be mutation-covered
    case("a SEQUENCE guard with no reconciliation note is UNJUSTIFIED",
         any("UNJUSTIFIED" in x
             for x in evaluate({"g_seq"}, ["g_seq"], {"g_seq": ("SEQUENCE", "")}, {}, set())))
    case("a SEQUENCE guard with no matching mutation label is UNMUTATED",
         any("UNMUTATED" in x for x in evaluate({"g_seq"}, ["unrelated"], SEQ, {}, set())))
    case("a SEQUENCE guard WITH a matching mutation label passes",
         not evaluate({"g_seq"}, ["mutate g_seq: drop it"], SEQ, {}, set()))
    case("SHAPE(reconciled) is treated as reconciling too",
         any("UNMUTATED" in x
             for x in evaluate({"g"}, [], {"g": ("SHAPE(reconciled)", "note")}, {}, set())))

    # the two escape hatches must actually work, or people will stop trusting them
    case("MUTATION_EXEMPT suppresses only the mutation requirement",
         not evaluate({"g_seq"}, [], SEQ, {}, {"g_seq"}))
    case("COVERED_BY lets a differently-named mutation label satisfy a guard",
         not evaluate({"g_seq"}, ["mutate the alias"], SEQ, {"g_seq": ("alias",)}, set()))
    case("COVERED_BY requires EVERY listed token, not just one",
         any("UNMUTATED" in x for x in
             evaluate({"g_seq"}, ["has one"], SEQ, {"g_seq": ("one", "two")}, set())))

    # ⭐ the round-8 M1 defect, written as a test: coverage was once checked against the whole
    # mutate-schema.py FILE BODY, so a guard name surviving in a COMMENT satisfied the ratchet.
    # `labels` is now the parsed label list, so a name that is not a label cannot satisfy it.
    # The label list is what `mutation_labels()` parses with `ast` — a guard name surviving only in
    # a COMMENT or inside a mutation's SQL body never reaches it, so it cannot satisfy coverage.
    case("round-8 M1 — a guard name present but NOT as a label does not count",
         any("UNMUTATED" in x for x in evaluate({"g_seq"}, ["an unrelated mutation"], SEQ, {}, set())))

    # the shipped config must be internally consistent
    case("every COVERED_BY key is a classified guard", all(k in GUARDS for k in COVERED_BY))
    case("every MUTATION_EXEMPT key is a classified guard",
         all(k in GUARDS for k in MUTATION_EXEMPT))
    case("every classified kind is SHAPE or a known reconciling kind",
         all(k[0] == "SHAPE" or k[0] in RECONCILING for k in GUARDS.values()))

    failed = [n for n, ok in cases if not ok]
    for name, ok in cases:
        # ⛔ `[FAIL] {name}: got … want …` IS A CONTRACT with check-plan-code.py, which
        # attributes a killed mutation from lines STARTING WITH "[FAIL] " via
        # `.strip()[7:].rsplit(": got ", 1)[0]`. A `✗` is invisible to it.
        print(f"  ✓ {name}" if ok else f"  [FAIL] {name}: got {ok!r} want {True!r}")
    print(f"\n{len(cases) - len(failed)}/{len(cases)} passed")
    return 1 if failed else 0



def main() -> int:
    # ⛔ THE ENUMERATION IS CHECKED BEFORE ITS OUTPUT IS TRUSTED — ⟳ r1 MEDIUM 2 (claude).
    # Three rounds found this component short and nothing could have caught any of them.
    scope_bad = scope_problems(clause_scopes(CATALOG_SQL), OWNED_TABLES, TRIGGER_TABLES,
                               clause_predicates(CATALOG_SQL))
    if scope_bad:
        for line in scope_bad:
            print(f"❌ SCOPE  {line}")
        print("\n  CATALOG_SQL's clauses disagree about which tables they read. A table that enters")
        print("  through one clause is invisible to the others, which is how this gate reported")
        print("  'every guard classified' three times over a guard it had never enumerated.")
        return 2 if any(x.startswith("CANNOT RUN") for x in scope_bad) else 1

    for _line in subject_banner(SCHEMA, Path(__file__)):
        print(_line)
    live = catalog_guards()
    if not live:
        print("no guards found — the catalog query returned nothing, which is itself a failure")
        return 2
    labels = mutation_labels()
    if not labels:
        print("no mutation labels parsed — the coverage check would pass vacuously")
        return 2
    problems = evaluate(live, labels)

    seq = sorted(n for n in live & set(GUARDS) if GUARDS[n][0] in RECONCILING)
    print(f"guards in schema: {len(live)}   "
          f"SHAPE: {len(live) - len(seq)}   reconciling: {len(seq)}")
    for n in seq:
        print(f"  {GUARDS[n][0]:18} {n}\n            reconciles via: {GUARDS[n][1]}")

    if problems:
        print("\n" + "=" * 78)
        for p in problems:
            print("❌ " + p)
        print("=" * 78)
        print(f"{len(problems)} problem(s) — guard coverage NOT met")
        return 1
    # ⟳ r1 MEDIUM (codex): this said "every guard classified", which is not what the gate checks.
    # Its subject is the relations M4 OWNS plus the triggers and FKs M4 adds to four foreign
    # tables. 25 CHECK constraints on the MONEY tables — guardrail_config (13), spend_ledger,
    # usage_counters, correction_spend, serve_model_charge, serve_owner_budget,
    # quota_allowance, share_tokens — are OUTSIDE it, and they are real guards rather than
    # non-guards. Leaving them out is defensible ONLY while the sentence says what is covered:
    # "every guard" turns a scope decision into an invisible gap. Recorded in backlog #29.
    print("\n✅ every BLOB-ADDRESSING SCHEMA guard classified; every SEQUENCE guard reconciles "
          "and is mutation-covered")
    return 0


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else main())
