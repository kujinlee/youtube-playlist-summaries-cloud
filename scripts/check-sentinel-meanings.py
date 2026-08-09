#!/usr/bin/env python3
"""Ratchet: every nullable column means exactly ONE thing, and says so.

WHY THIS EXISTS
---------------
The single most repeated root cause in this project is one value encoding two
independent facts:

  * `workspace_videos.corrections_hash` nullable = "no corrections" OR "nobody
    ever computed this" — round 6 B4, measured on the money path: 2903 rows read
    as "uncorrected" by the top ranking rung.
  * `video_artifacts.generation_id is null` = "this is free" AND "this address
    may be overwritten" — one is a MONEY property, the other an ADDRESSING
    property, and the conflation produced five findings across rounds 8-12.
  * absent vs failed-to-read in Stage 3 cloud-sync, which is shape #1 in the
    standing root-cause list and was itself found twice.

Every one was invisible to the assertion suite, because an assertion tests what a
value DOES, never what its absence MEANS. Meaning lives in prose, prose is not
enumerated, and an absence is only visible against an enumerated whole.

THE TEST
--------
For every nullable column in the schema-owned tables, a one-sentence meaning must
be recorded here. The sentence is then checked for a CONJUNCTION — " and " / " or "
— because a meaning that needs two clauses is usually two meanings wearing one
column.

That heuristic has false positives, and they are cheap: write the justification in
CONJUNCTION_OK and move on. False NEGATIVES are the expensive direction, which is
why the test is deliberately blunt.

Usage:  ./scripts/check-sentinel-meanings.py     (exit 0 = every nullable classified)
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema"
CONTAINER = "supabase_db_youtube-playlist-summaries-cloud"

# Tables this spec owns or extends. Same set the guard ratchet uses, for the same
# reason: an exclusion is a place a real conflation can hide.
TABLES = ("video_artifacts", "video_generations", "workspace_videos",
          "videos", "jobs", "playlists", "workspaces")

# (table, column) -> what NULL means. ONE clause. If you need two, you have two columns.
MEANINGS: dict[tuple[str, str], str] = {
    # ── video_artifacts ─────────────────────────────────────────────────────────
    ("video_artifacts", "generation_id"):
        "CONFLATED — see CONJUNCTION_OK; ADR-0007 removes this",
    ("video_artifacts", "source_generation_id"):
        "this artifact was not derived from another generation",
    ("video_artifacts", "start_sec"):        "this artifact does not describe a time span",
    ("video_artifacts", "end_sec"):          "this artifact does not describe a time span",
    ("video_artifacts", "detached_at"):      "this artifact is not detached",
    ("video_artifacts", "lease_expires_at"): "this artifact is not in flight",
    ("video_artifacts", "lease_token"):      "this artifact is not in flight",
    ("video_artifacts", "reserved_at"):      "this artifact is not in flight",
    # ── video_generations ───────────────────────────────────────────────────────
    ("video_generations", "reserved_by"):    "no reservation is outstanding for this generation",
    ("video_generations", "card"):           "this generation has produced no card yet",
    ("video_generations", "md_hash"):        "this generation has produced no body yet",
    ("video_generations", "doc_version_major"): "this generation has produced no body yet",
    ("video_generations", "produced_at"):    "this generation has produced nothing yet",
    # ── workspace_videos ────────────────────────────────────────────────────────
    ("workspace_videos", "corrections"):     "this video carries no correction text",
    # ── pre-existing tables, recorded rather than excluded ──────────────────────
    ("jobs", "result"):                      "this job has not succeeded yet",
    ("jobs", "error"):                       "this job has not failed",
    ("jobs", "locked_by"):                   "this job is not leased",
    ("jobs", "lease_token"):                 "this job is not leased",
    ("jobs", "lease_expires_at"):            "this job is not leased",
    ("jobs", "progress_phase"):              "this job has reported no phase",
    ("jobs", "enqueue_ip"):                  "this job was not enqueued over HTTP",
    ("playlists", "playlist_title"):         "the playlist title has not been fetched",
}

# A meaning may contain a conjunction ONLY with a written reason. Empty is the goal.
CONJUNCTION_OK: dict[tuple[str, str], str] = {
    ("video_artifacts", "generation_id"): (
        "KNOWN CONFLATION, recorded rather than hidden.\n"
        "                NULL currently means BOTH 'this artifact is free' (a MONEY property) and\n"
        "                'this address may be overwritten' (an ADDRESSING property). The schema\n"
        "                literally defines free-ness as the absence of a generation id:\n"
        "                  (kind in ('summary','model','dig','digDeeper')) = (generation_id is not null)\n"
        "                Five findings across rounds 8-12 came out of that single conflation.\n"
        "\n"
        "                ⟳ 2026-08-09 — THE OLD DELETION TRIGGER WAS 'when renders get a derived\n"
        "                generation id'. That plan is DEAD: it was refuted by round 13 (B2), its\n"
        "                replacement was refuted by round 14 (B4), and render addressing has been\n"
        "                split out of ADR-0007 entirely. A trigger that can never fire is a rule\n"
        "                that rots, so it is restated rather than left pointing at a dead plan.\n"
        "                ADR-0007 no longer removes this defect — it is scoped to COORDINATION.\n"
        "                NEW TRIGGER: delete this entry when the render-addressing slice lands\n"
        "                (docs/superpowers/specs/2026-08-09-render-addressing-brief.md, backlog #25).\n"
        "                Do NOT delete it on the strength of either withdrawn design."),
}


def nullable_columns() -> set[tuple[str, str]]:
    sql = "begin;\n"
    for f in sorted(SCHEMA.glob("0*.sql")):
        if f.name.startswith("05"):
            continue  # assertions, not schema
        sql += f.read_text() + "\n"
    sql += ("\\echo ---COLS---\n"
            "select table_name || '.' || column_name from information_schema.columns\n"
            f" where table_schema = 'public' and table_name in {TABLES}\n"
            "   and is_nullable = 'YES'\n"
            " order by 1;\nrollback;\n")
    p = subprocess.run(
        ["docker", "exec", "-i", CONTAINER, "psql", "-U", "postgres", "-d", "postgres",
         "-tAq", "-v", "ON_ERROR_STOP=1"],
        input=sql, capture_output=True, text=True)
    if p.returncode != 0:
        print("could not read the catalog — is the local Supabase container running?")
        print(p.stdout[-1500:] or p.stderr[-1500:])
        sys.exit(2)
    out = p.stdout.split("---COLS---", 1)[-1]
    cols = set()
    for ln in out.splitlines():
        ln = ln.strip()
        if "." in ln and " " not in ln:
            t, c = ln.split(".", 1)
            cols.add((t, c))
    return cols


CONJUNCTION = re.compile(r"\b(and|or)\b", re.IGNORECASE)


def main() -> int:
    live = nullable_columns()
    if not live:
        print("no nullable columns found — the query returned nothing, itself a failure")
        return 2
    problems: list[str] = []

    for t, c in sorted(live - set(MEANINGS)):
        problems.append(
            f"UNDOCUMENTED  {t}.{c}\n"
            f"              A nullable column with no recorded meaning. Write ONE sentence:\n"
            f"              what does NULL mean here? If it needs two clauses, it is two columns.")

    for t, c in sorted(set(MEANINGS) - live):
        problems.append(f"STALE         {t}.{c}\n"
                        f"              Documented here but no longer nullable — delete the entry.")

    for key in sorted(live & set(MEANINGS)):
        meaning = MEANINGS[key]
        if not CONJUNCTION.search(meaning):
            continue
        if key in CONJUNCTION_OK:
            continue
        problems.append(
            f"CONFLATED?    {key[0]}.{key[1]}\n"
            f"              \"{meaning}\"\n"
            f"              The meaning contains a conjunction, which usually means NULL is\n"
            f"              carrying two facts. Split the column, or justify it in CONJUNCTION_OK.")

    print(f"nullable columns: {len(live)}   documented: {len(live & set(MEANINGS))}   "
          f"justified conjunctions: {len(CONJUNCTION_OK)}")
    for key, why in sorted(CONJUNCTION_OK.items()):
        print(f"  ⚠ {key[0]}.{key[1]}\n                {why}")

    if problems:
        print("\n" + "=" * 78)
        for p in problems:
            print("❌ " + p)
        print("=" * 78)
        print(f"{len(problems)} problem(s) — sentinel meanings NOT met")
        return 1
    print("\n✅ every nullable column means exactly one thing, and says so")
    return 0


if __name__ == "__main__":
    sys.exit(main())
