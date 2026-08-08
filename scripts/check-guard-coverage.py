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
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "docs/superpowers/specs/2026-08-03-stable-blob-addressing"
SCHEMA = SPEC / "schema"
MUTATIONS = SPEC / "mutate-schema.py"
CONTAINER = "supabase_db_youtube-playlist-summaries-cloud"
TABLES = ("video_artifacts", "video_generations")

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
    "art_pending_is_leased":       ("SHAPE", ""),
    "art_pending_has_token":       ("SHAPE", ""),
    "art_pending_has_reserved_at": ("SHAPE", ""),
    "art_summary_has_no_source":   ("SHAPE", ""),
    "art_dig_has_span":            ("SHAPE", ""),
    "art_detached_is_dig":         ("SHAPE", ""),
    "art_detached_has_timestamp":  ("SHAPE", ""),
    "art_key_names_generation":    ("SHAPE", ""),
    # ── video_generations: SHAPE ────────────────────────────────────────────────
    "gen_complete_has_produced_at": ("SHAPE", ""),
    "gen_card_complete":            ("SHAPE", ""),
    "gen_summary_has_format":       ("SHAPE", ""),
    "gen_summary_has_hash":         ("SHAPE", ""),
    "gen_major_matches_card":       ("SHAPE", ""),
    # Auto-named inline CHECKs. Found by this ratchet on its first run — they had been
    # in the schema since round 4 and were never in anyone's mental inventory, which is
    # the exact failure mode it exists to remove.
    "video_artifacts_state_check":   ("SHAPE", ""),
    "video_generations_state_check": ("SHAPE", ""),
    # ── SEQUENCE: each must reconcile, and say how ──────────────────────────────
    "video_artifacts_inflight_uq": (
        "SEQUENCE",
        "reserve_artifact_slot upserts on it and returns typed busy|exhausted|reserved"),
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
    "forbid_collecting_current": (
        "SEQUENCE",
        "the sweeper selects THROUGH video_generations_collectable; trigger kept as a backstop "
        "for direct writes, deliberately NOT softened to a silent no-op (round 8 C3)"),
    # ── foreign keys are structural, never mutated; named explicitly, not skipped ─
    "video_artifacts_workspace_id_video_id_fkey":                    ("SHAPE", ""),
    "video_artifacts_workspace_id_video_id_generation_id_kind_fkey": ("SHAPE", ""),
    "video_artifacts_workspace_id_video_id_source_generation_id_fkey": ("SHAPE", ""),
    "video_generations_workspace_id_video_id_fkey":                  ("SHAPE", ""),
    "workspace_videos_workspace_id_fkey":                            ("SHAPE", ""),
    "videos_workspace_video_fk":                                     ("SHAPE", ""),
    # Pre-existing FKs on `videos`, not added by this spec. Classified rather than
    # filtered out of the query: an exclusion is a place a real guard can hide, and
    # naming them costs two lines.
    "videos_playlist_id_owner_id_fkey":                              ("SHAPE", ""),
    "videos_workspace_id_fkey":                                      ("SHAPE", ""),
}

# A SEQUENCE guard whose reconciler cannot be mutation-tested must say why here.
# Empty by design: if this grows, the ratchet is being talked out of rather than met.
MUTATION_EXEMPT: dict[str, str] = {}

CATALOG_SQL = f"""
select 'check:' || conname from pg_constraint
 where conrelid = any (array{list(TABLES)}::regclass[]) and contype = 'c'
union all
select 'fk:' || conname from pg_constraint
 where contype = 'f'
   and connamespace = 'public'::regnamespace
   and conrelid::regclass::text in ('video_artifacts','video_generations','workspace_videos','videos')
union all
select 'index:' || indexrelid::regclass::text from pg_index
 where indrelid = any (array{list(TABLES)}::regclass[]) and indisunique
   and indexrelid::regclass::text like '%_uq'
union all
select 'trigger:' || p.proname from pg_trigger t
  join pg_proc p on p.oid = t.tgfoid
 where t.tgrelid = any (array{list(TABLES)}::regclass[]) and not t.tgisinternal;
"""


def catalog_guards() -> set[str]:
    sql = "begin;\n"
    for f in sorted(SCHEMA.glob("0*.sql")):
        if f.name.startswith("05"):
            continue  # assertions, not schema
        sql += f.read_text() + "\n"
    sql += "\\echo ---GUARDS---\n" + CATALOG_SQL + "\nrollback;\n"
    p = subprocess.run(
        ["docker", "exec", "-i", CONTAINER, "psql", "-U", "postgres", "-d", "postgres",
         "-tAq", "-v", "ON_ERROR_STOP=1"],
        input=sql, capture_output=True, text=True)
    if p.returncode != 0:
        print("could not read the catalog — is the local Supabase container running?")
        print(p.stdout[-1500:] or p.stderr[-1500:])
        sys.exit(2)
    out = p.stdout.split("---GUARDS---", 1)[-1]
    return {ln.split(":", 1)[1] for ln in out.splitlines()
            if ":" in ln and ln.split(":", 1)[0] in {"check", "fk", "index", "trigger"}}


def main() -> int:
    live = catalog_guards()
    if not live:
        print("no guards found — the catalog query returned nothing, which is itself a failure")
        return 2
    mutation_text = MUTATIONS.read_text()
    problems: list[str] = []

    for name in sorted(live - set(GUARDS)):
        problems.append(
            f"UNCLASSIFIED  {name}\n"
            f"              A new guard reached the schema without a SHAPE/SEQUENCE decision.\n"
            f"              Ask: what does it do when the caller is merely SECOND?")

    for name in sorted(set(GUARDS) - live):
        problems.append(
            f"STALE         {name}\n"
            f"              Classified here but no longer in the schema — delete the entry.")

    for name in sorted(live & set(GUARDS)):
        kind, note = GUARDS[name]
        if kind != "SEQUENCE":
            continue
        if not note:
            problems.append(
                f"UNJUSTIFIED   {name}\n"
                f"              SEQUENCE guards must record HOW they reconcile.")
        if name in MUTATION_EXEMPT:
            continue
        if name not in mutation_text:
            problems.append(
                f"UNMUTATED     {name}\n"
                f"              A SEQUENCE guard with no mutation entry. Its reconciler is a claim,\n"
                f"              not a tested behaviour — add one to mutate-schema.py.")

    seq = sorted(n for n in live & set(GUARDS) if GUARDS[n][0] == "SEQUENCE")
    print(f"guards in schema: {len(live)}   "
          f"SHAPE: {len(live) - len(seq)}   SEQUENCE: {len(seq)}")
    for n in seq:
        print(f"  SEQUENCE  {n}\n            reconciles via: {GUARDS[n][1]}")

    if problems:
        print("\n" + "=" * 78)
        for p in problems:
            print("❌ " + p)
        print("=" * 78)
        print(f"{len(problems)} problem(s) — guard coverage NOT met")
        return 1
    print("\n✅ every guard classified; every SEQUENCE guard reconciles and is mutation-covered")
    return 0


if __name__ == "__main__":
    sys.exit(main())
