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
import ast
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "docs/superpowers/specs/2026-08-03-stable-blob-addressing"
SCHEMA = SPEC / "schema"
MUTATIONS = SPEC / "mutate-schema.py"
CONTAINER = "supabase_db_youtube-playlist-summaries-cloud"
TABLES = ("video_artifacts", "video_generations")

# ⟳ ROUND 9 — THE ENUMERATED WHOLE WAS ITSELF SCOPED TOO NARROWLY, which is this script's own
# thesis used against it. Round 9's B3 fix added `resolve_workspace_from_playlist` as a trigger on
# `videos` and `jobs`; this ratchet enumerated triggers on TWO tables, so it reported ✅ and "32
# guards" with a brand-new guard sitting outside its query. `sync_corrections_to_workspace_video`
# (round 6) had been invisible the same way since the day this script was written.
#
# An absence is only visible against an enumerated whole — and the whole has to be "every table this
# spec puts a guard on", not the two that were interesting the day the query was typed.
TRIGGER_TABLES = TABLES + ("videos", "jobs", "workspace_videos", "playlists", "profiles")

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
    "art_key_names_workspace":     ("SHAPE", ""),   # ⟳ round 9 H5; applies to FREE rows too
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
    "sync_corrections_to_workspace_video": (
        "SHAPE(reconciled)",
        "the INSERT half's WHEN clause skips rows carrying no corrections; without it the same video "
        "added to a second playlist CLOBBERED the shared corrections (measured round 9)"),
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
    "sync_corrections_to_workspace_video": ("the anti-drift trigger removed",
                                            "the INSERT-half sync unguarded"),
}

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
select distinct 'trigger:' || p.proname from pg_trigger t
  join pg_proc p on p.oid = t.tgfoid
 where t.tgrelid = any (array{list(TRIGGER_TABLES)}::regclass[]) and not t.tgisinternal;
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


def main() -> int:
    live = catalog_guards()
    if not live:
        print("no guards found — the catalog query returned nothing, which is itself a failure")
        return 2
    labels = mutation_labels()
    if not labels:
        print("no mutation labels parsed — the coverage check would pass vacuously")
        return 2
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
        if name in MUTATION_EXEMPT:
            continue
        # Match the guard against mutation LABELS, never the file body (round 8 M1).
        wanted = COVERED_BY.get(name, (name,))
        for token in wanted:
            if not any(token in label for label in labels):
                problems.append(
                    f"UNMUTATED     {name}\n"
                    f"              No mutation label contains {token!r}. Its reconciler is a claim,\n"
                    f"              not a tested behaviour — add one to mutate-schema.py.")

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
    print("\n✅ every guard classified; every SEQUENCE guard reconciles and is mutation-covered")
    return 0


if __name__ == "__main__":
    sys.exit(main())
