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

from subject_status import subject_banner

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
        "this artifact is free and its address may be overwritten",   # ⚠ justified in CONJUNCTION_OK
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


def evaluate(
    live: set[tuple[str, str]],
    meanings: dict[tuple[str, str], str] | None = None,
    conjunction_ok: dict[tuple[str, str], str] | None = None,
) -> list[str]:
    """PURE — nullable columns in, problems out. No database, no filesystem.

    Split out of main() 2026-08-19 so `--self-test` can drive the RULE without a live Postgres,
    which is the only reason this ratchet had none: its sole entry point needed docker, so
    "test it" read as "stand up a database". The rule never needed the container; the FETCH did.
    """
    meanings = MEANINGS if meanings is None else meanings
    conjunction_ok = CONJUNCTION_OK if conjunction_ok is None else conjunction_ok
    problems: list[str] = []

    for t, c in sorted(live - set(meanings)):
        problems.append(
            f"UNDOCUMENTED  {t}.{c}\n"
            f"              A nullable column with no recorded meaning. Write ONE sentence:\n"
            f"              what does NULL mean here? If it needs two clauses, it is two columns.")

    for t, c in sorted(set(meanings) - live):
        problems.append(f"STALE         {t}.{c}\n"
                        f"              Documented here but no longer nullable — delete the entry.")

    # ⟳ 2026-08-19 — A JUSTIFICATION CANNOT OUTLIVE THE THING IT EXCUSED.
    #
    # Its sibling `check-vocabulary-collisions.py` has always failed on a stale ALLOWED entry
    # ("that is the difference between a ratchet and a mute button"). This script had no such rule,
    # and its ONE entry had already gone unreachable: the meaning for video_artifacts.generation_id
    # had been reworded to "CONFLATED — see CONJUNCTION_OK", which contains no conjunction, so the
    # search below `continue`d before ever consulting the allowlist. The conflation was still live
    # (backlog #25 is open) — the GUARD had been disarmed by an edit to the text it inspects, which
    # is this project's most-repeated defect shape. Found 2026-08-19 by this script's own new
    # --self-test consistency case, not by reading it.
    for key in sorted(set(conjunction_ok)):
        if key not in meanings:
            problems.append(
                f"ORPHAN JUST.  {key[0]}.{key[1]}\n"
                f"              Justified in CONJUNCTION_OK but absent from MEANINGS — it excuses\n"
                f"              a meaning that no longer exists. Delete the entry.")
        elif not CONJUNCTION.search(meanings[key]):
            problems.append(
                f"STALE JUST.   {key[0]}.{key[1]}\n"
                f"              Justified in CONJUNCTION_OK, but its meaning contains no\n"
                f"              conjunction, so the rule it excuses can never fire. Either the\n"
                f"              conflation is gone (delete the entry) or the meaning stopped\n"
                f"              admitting it (restore the conjunction). An unreachable\n"
                f"              justification is a mute button, not a ratchet.")

    for key in sorted(live & set(meanings)):
        meaning = meanings[key]
        if not CONJUNCTION.search(meaning):
            continue
        if key in conjunction_ok:
            continue
        problems.append(
            f"CONFLATED?    {key[0]}.{key[1]}\n"
            f"              \"{meaning}\"\n"
            f"              The meaning contains a conjunction, which usually means NULL is\n"
            f"              carrying two facts. Split the column, or justify it in CONJUNCTION_OK.")
    return problems



# ── --self-test ─────────────────────────────────────────────────────────────────────────────────
# Added 2026-08-19 (task #54). `check-ratchet-contract.py` has listed this script as missing a
# --self-test since 2026-08-11. See `evaluate` for why it stayed missing.

def self_test() -> int:
    cases: list[tuple[str, bool]] = []

    def case(name: str, ok: bool) -> None:
        cases.append((name, ok))

    K = ("jobs", "error")
    OK = {K: "this job has not failed"}

    case("a documented, single-clause meaning passes", not evaluate({K}, OK, {}))
    case("a nullable column with NO recorded meaning is caught",
         any("UNDOCUMENTED" in x for x in evaluate({K, ("jobs", "novel")}, OK, {})))
    case("a documented column that is no longer nullable is STALE",
         any("STALE" in x for x in evaluate(set(), OK, {})))

    conj = {K: "this job has not failed and has not been retried"}
    case("a conjunction in the meaning is caught",
         any("CONFLATED?" in x for x in evaluate({K}, conj, {})))
    case("a JUSTIFIED conjunction is silent", not evaluate({K}, conj, {K: "known conflation"}))
    case("the report quotes the meaning back at the reader",
         any("has not been retried" in x for x in evaluate({K}, conj, {})))
    case("'or' is a conjunction too",
         any("CONFLATED?" in x for x in evaluate({K}, {K: "no result or no error"}, {})))

    # CONJUNCTION uses \b — a word merely CONTAINING 'and'/'or' must not trip it, or the rule
    # would fire on ordinary English ("brand", "record") and get muted rather than obeyed.
    for word in ("this job carries no brand", "this job has no record"):
        case(f"a word containing a conjunction does not trip it: {word.split()[-1]!r}",
             not evaluate({K}, {K: word}, {}))

    # the shipped config must be internally consistent, or the check is arguing with itself
    case("every CONJUNCTION_OK key is also documented in MEANINGS",
         all(k in MEANINGS for k in CONJUNCTION_OK))
    case("every CONJUNCTION_OK entry actually contains a conjunction to justify",
         all(CONJUNCTION.search(MEANINGS[k]) for k in CONJUNCTION_OK if k in MEANINGS))

    # the general rule that the shipped-config case above is one instance of
    case("a justification whose meaning has NO conjunction is caught as STALE",
         any("STALE JUST." in x for x in evaluate({K}, OK, {K: "why"})))
    case("a justification for a meaning that does not exist is an ORPHAN",
         any("ORPHAN JUST." in x for x in evaluate({K}, OK, {("t", "gone"): "why"})))
    case("a LIVE justification is still silent", not evaluate({K}, conj, {K: "known conflation"}))

    failed = [n for n, ok in cases if not ok]
    for name, ok in cases:
        print(f"  {'✓' if ok else '✗'} {name}")
    print(f"\n{len(cases) - len(failed)}/{len(cases)} passed")
    return 1 if failed else 0



def main() -> int:
    for _line in subject_banner(SCHEMA, Path(__file__)):
        print(_line)
    live = nullable_columns()
    if not live:
        print("no nullable columns found — the query returned nothing, itself a failure")
        return 2
    problems = evaluate(live)

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
    sys.exit(self_test() if "--self-test" in sys.argv else main())
