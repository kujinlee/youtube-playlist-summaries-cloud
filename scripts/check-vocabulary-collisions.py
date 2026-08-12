#!/usr/bin/env python3
"""Ratchet: two tables may not independently model the same MECHANISM.

WHY THIS EXISTS
---------------
The blob-addressing spec built a second lease protocol beside the job queue's.
Six consecutive adversarial rounds found a Blocking or High in it, four of them
introduced by the previous round's own fix, and every one lived in the seam
between the two protocols. The mechanism was redundant from its first commit —
`jobs` already had exclusivity, idempotency, leases and a durable money guard.

Nothing caught it, because every gate this project owns asks "is this correct?",
which is a LOCAL question and can always be answered yes by patching. A duplicated
mechanism is never locally incorrect.

THE SIGNAL
----------
Duplicate mechanisms leave an observable shadow: DUPLICATE VOCABULARY.

    jobs.lease_token          video_artifacts.lease_token
    jobs.lease_expires_at     video_artifacts.lease_expires_at
    jobs.attempts             video_artifacts.lease_attempts
    jobs.locked_by            video_generations.reserved_by

Four collisions, present on day one, each a place where two tables independently
answer "who holds this work". This script would have failed on that first commit.

WHY A CURATED WORD LIST rather than "any repeated column name": `workspace_id`,
`video_id`, `owner_id`, `created_at` repeat everywhere and SHOULD — they are shared
identity, deliberately the same concept. What must not repeat is COORDINATION
vocabulary: the words that name a protocol. So the list below is the point of the
script, not an implementation detail, and adding to it is a design act.

False positives cost one line in ALLOWED with a reason. False negatives cost six
review rounds. The trade is deliberate.

Usage:  ./scripts/check-vocabulary-collisions.py    (exit 0 = no unjustified duplicate mechanism)
"""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema"
CONTAINER = "supabase_db_youtube-playlist-summaries-cloud"

TABLES = ("video_artifacts", "video_generations", "workspace_videos",
          "videos", "jobs", "playlists", "workspaces", "spend_ledger")

# Words that NAME A COORDINATION MECHANISM. A stem appearing on more than one table
# means two tables are modelling the same protocol — which is the thing to justify.
MECHANISM_STEMS = (
    "lease", "token", "lock", "claim", "attempt", "reserv", "holder",
    "heartbeat", "expires_at", "in_flight", "pending_at", "owner_by",
)

# stem -> why more than one table legitimately carries it.
# Empty is the goal. Every entry is a design decision someone must defend.
#
# ⚠ AN ENTRY HERE IS DEBT, NOT PERMISSION. The check below fails on a STALE entry —
# one whose stem no longer collides — so an allowlist cannot quietly outlive the
# thing it excused. That is the difference between a ratchet and a mute button.
ALLOWED: dict[str, str] = {
    # ── REMOVED 2026-08-12: `lease`, `token`, `expires_at`, `attempt` ──
    # These four recorded the duplicate lease protocol that `video_artifacts`/`video_generations`
    # had re-implemented on top of the job queue's — exclusivity, idempotency, expiry and an
    # attempt bound `jobs` already had. Every Blocking and High of rounds 7-12 lived in that seam.
    #
    # ADR-0007 deleted the artifact half, and the entries went stale exactly as this block
    # predicted they would: *"when it lands these four entries go STALE and must be removed —
    # which is this script reporting its own success."* It reported it. Removing them is the
    # acknowledgement; leaving them would have turned a ratchet into standing permission for the
    # next duplication, which is the failure mode the header warns about.
    #
    # They went stale on 2026-08-07 (ADR-0007) and were removed on 2026-08-12. The gap exists
    # because this checker needs a local Postgres and so is NOT in CI — nothing was watching. That
    # is the real lesson here, and it belongs to the whole class of not-yet-in-CI schema gates
    # (docs/dev-process.md → "Not yet in CI"), not to this entry.
    "reserv": (
        "SPLIT CONCEPT, not duplication: `jobs.reserved_cents` is a MONEY reservation\n"
        "            (spend held against a budget) while `video_artifacts.reserved_at` /\n"
        "            `video_generations.reserved_by` are WORK reservations. Same English word,\n"
        "            different mechanisms. ⚠ The work half is what ADR-0007 deletes — when it\n"
        "            lands, only jobs.reserved_cents remains and this entry should shrink to a\n"
        "            note that the collision is gone. MEASURED 2026-08-12: it has NOT landed for\n"
        "            this stem — `reserv` still collides, so the work-reservation columns survive\n"
        "            in the migrations even though the four lease stems above went stale. This\n"
        "            entry stays live; do not remove it on the assumption ADR-0007 covered it."),
}


def columns() -> list[tuple[str, str]]:
    sql = "begin;\n"
    for f in sorted(SCHEMA.glob("0*.sql")):
        if f.name.startswith("05"):
            continue
        sql += f.read_text() + "\n"
    sql += ("\\echo ---COLS---\n"
            "select table_name || '.' || column_name from information_schema.columns\n"
            f" where table_schema = 'public' and table_name in {TABLES}\n"
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
    cols = []
    for ln in out.splitlines():
        ln = ln.strip()
        if "." in ln and " " not in ln:
            t, c = ln.split(".", 1)
            cols.append((t, c))
    return cols


def main() -> int:
    cols = columns()
    if not cols:
        print("no columns found — the query returned nothing, itself a failure")
        return 2

    collisions: dict[str, list[str]] = {}
    for stem in MECHANISM_STEMS:
        hits = [f"{t}.{c}" for t, c in cols if stem in c]
        if len({h.split(".")[0] for h in hits}) > 1:
            collisions[stem] = sorted(hits)

    problems = []
    for stem in sorted(set(ALLOWED) - set(collisions)):
        problems.append(
            f"STALE JUSTIFICATION  '{stem}' no longer collides — delete its ALLOWED entry.\n"
            "                     The duplication it excused is gone; leaving the entry turns a\n"
            "                     ratchet into standing permission for the next one.")
    for stem, hits in sorted(collisions.items()):
        if stem in ALLOWED:
            continue
        tables = sorted({h.split(".")[0] for h in hits})
        problems.append(
            f"DUPLICATE MECHANISM  '{stem}' appears on {len(tables)} tables: {', '.join(tables)}\n"
            + "".join(f"                       {h}\n" for h in hits)
            + "                     Two tables modelling one protocol. Either one of them is\n"
              "                     redundant, or they are different concepts sharing a word —\n"
              "                     and if it is the second, say which in ALLOWED.")

    print(f"columns scanned: {len(cols)}   mechanism stems: {len(MECHANISM_STEMS)}   "
          f"collisions: {len(collisions)}   justified: {len(ALLOWED)}")
    for stem, why in sorted(ALLOWED.items()):
        if stem in collisions:
            print(f"  ⚠ '{stem}' — {why}")

    if problems:
        print("\n" + "=" * 78)
        for p in problems:
            print("❌ " + p)
        print("=" * 78)
        print(f"{len(problems)} unjustified duplicate mechanism(s)")
        return 1
    print("\n✅ no unjustified duplicate mechanism")
    return 0


if __name__ == "__main__":
    sys.exit(main())
