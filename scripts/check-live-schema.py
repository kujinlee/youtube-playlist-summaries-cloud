#!/usr/bin/env python3
"""Does the DEPLOYED schema match what M4 claims — a RATCHET on the SUBJECT axis.

    python3 scripts/check-live-schema.py --expect-absent    # before 0027, or after the rollback
    python3 scripts/check-live-schema.py --expect-present   # after 0027
    python3 scripts/check-live-schema.py --self-test        # prints its own case count

WHY THIS EXISTS
---------------
`docs/reviews/architecture-review-2026-08-25.md` finding 3: **five of the six schema gates never read
a live database.** They REBUILD the schema from the spec files inside their own rolled-back
transaction. So the existing suite answers *"is the SPEC internally consistent?"* and cannot answer
*"did the migration APPLY?"* — the wrong question for the one milestone whose purpose is making the
spec execute. That is the **SUBJECT** axis: built-from-source vs introspected-from-live.

⭐ WHY IT CHECKS A DERIVED MANIFEST AND NOT A HAND-WRITTEN LIST
--------------------------------------------------------------
⟳ **r3 B2 (claude), 2026-08-25. User chose option (a).** This gate used to carry five hand-written
tuples naming **29 of 161** objects — **18%**. Zero views, zero indexes, zero policies, zero
constraints, 3 of 70 columns, and **7 of 14 triggers**, because the trigger tuple deliberately held
only the seven on *live* tables.

MEASURED: it reported **"M4 is PRESENT as expected", exit 0**, over a database with **all seven of
M4's own-table triggers dropped** — every append-only, freeze and immutability guard gone. The plan
called it *"the only instrument that can confirm M4-β happened"*, and Task 9 makes it the sole
production check, while the one-transaction property that would make a partial apply impossible is
itself marked NOT VERIFIED. **A gate asserting a claim four times wider than what it reads.**

It now compares against `docs/superpowers/specs/m4/live-manifest.txt`, which
`scripts/gen-m4-manifest.py` derives **by executing the schema and reading the catalog** — so the
expected set cannot drift from what Postgres actually creates, and nothing is covered "by being
remembered". `--check` on the generator is the staleness ratchet.

FAILS IF
--------
`--expect-absent` and ANY manifest object survives; `--expect-present` and any is missing; an
ADR-0011-removed object exists in either polarity; the manifest is missing or empty; or the database
is unreachable (exit 2 — treat as NOT RUN).
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m4_catalog import (by_kind, label, name_of, read_catalog, read_only_url,  # noqa: E402
                        summarise)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(REPO, "docs", "superpowers", "specs", "m4", "live-manifest.txt")

# ⚠ OBJECTS ADR-0011 DELETED. These must NEVER exist, in EITHER polarity.
# MEASURED 2026-08-25: with M4 built from the spec WITHOUT Tasks 1-2 applied, the rollback left
# these three behind and this gate reported "ABSENT — as expected", because the manifest describes
# the POST-ADR-0011 schema and so cannot mention anything ADR-0011 deletes. Their presence means
# Task 1 did not fully land; a surviving `videos_corrections_sync_*` trigger fires on every video
# write, calling a column that no longer exists.
ADR0011_REMOVED = {
    "trg:videos.videos_corrections_sync_ins_trg",
    "trg:videos.videos_corrections_sync_upd_trg",
    "fn:sync_corrections_to_workspace_video()",
    "col:workspace_videos.corrections",
    "col:workspace_videos.corrections_hash",
}


def load_manifest(path: str = MANIFEST) -> set[str]:
    """The derived expected object set, VERIFIED against its own header.

    ⛔ r4 B2 — A NON-EMPTY CHECK IS NOT AN INTEGRITY CHECK. This used to accept any file with at
    least one line. MEASURED: a manifest of one line, against a database holding that one object,
    produced **"M4 is PRESENT as expected — checked all 1 objects", exit 0** — over a database
    missing 160 of 161. Because the verdict is a SUBSET test, shrinking the manifest shrinks the
    claim, and the gate reports the smaller number as though it were the whole.

    That is r3 B2 recurring one level up: the trust root moved from a hand-written list to a derived
    file, and the *guarantee* did not move with it. So the file now states its own object count and
    a sha256 of its body, and both are checked here — a truncated or edited manifest is a CANNOT RUN.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"no manifest at {path}. Generate it: python3 scripts/gen-m4-manifest.py")
    with open(path) as f:
        text = f.read()
    objs = {ln.strip() for ln in text.splitlines() if ln.strip() and not ln.startswith("#")}
    if not objs:
        raise ValueError(
            f"the manifest at {path} is EMPTY. An empty expected set makes --expect-present pass\n"
            "over any database at all, which is the failure this gate exists to prevent.")

    claimed_n = re.search(r"^#\s*objects:\s*(\d+)\s*$", text, re.M)
    claimed_d = re.search(r"^#\s*sha256:\s*([0-9a-f]{64})\s*$", text, re.M)
    if not claimed_n or not claimed_d:
        raise ValueError(
            f"the manifest at {path} carries no `# objects:` / `# sha256:` header, so its\n"
            "completeness cannot be checked. Regenerate it: python3 scripts/gen-m4-manifest.py")
    if int(claimed_n.group(1)) != len(objs):
        raise ValueError(
            f"the manifest at {path} is INCOMPLETE: its header claims "
            f"{claimed_n.group(1)} objects, the file holds {len(objs)}.\n"
            "A short manifest silently shrinks what this gate promises. Regenerate it.")
    actual = hashlib.sha256(("\n".join(sorted(objs)) + "\n").encode()).hexdigest()
    if actual != claimed_d.group(1):
        raise ValueError(
            f"the manifest at {path} does not match its own sha256 — it has been edited by hand or\n"
            "is partially written. It is DERIVED: regenerate it with "
            "python3 scripts/gen-m4-manifest.py")
    return objs


# ---------------------------------------------------------------- pure verdict
def verdict(live: set[str], manifest: set[str], mode: str) -> bool:
    """PURE. True = pass.

    present: every manifest object is live.
    absent : no manifest object is live.
    BOTH   : nothing ADR-0011 removed is live.
    """
    if forbidden(live):
        return False
    if mode == "absent":
        return not (live & manifest)
    return manifest <= live


def residue(live: set[str], manifest: set[str], mode: str) -> set[str]:
    """What is wrong — so a failure NAMES the objects. PURE."""
    return (live & manifest) if mode == "absent" else (manifest - live)


def split_residue(live: set[str], manifest: set[str]) -> tuple[set[str], set[str]]:
    """(absent, redefined) — because those are DIFFERENT PROBLEMS with different causes.

    Now that objects carry a digest, an object whose definition changed is `manifest - live` just
    like one that was never created. Reporting a DISABLED trigger as "missing" would send a reader
    hunting for a migration that did not run, when the object is right there and inert. PURE.
    """
    live_names = {name_of(o) for o in live}
    missing = {o for o in manifest - live if name_of(o) not in live_names}
    redefined = {o for o in manifest - live if name_of(o) in live_names}
    return missing, redefined


def forbidden(live: set[str]) -> set[str]:
    """ADR-0011-removed objects that are nonetheless present. PURE.

    ⚠ Matched by NAME, not by the full `name@digest` string: `ADR0011_REMOVED` records things that
    must not exist at all, so their definition is irrelevant — and a digest-bearing comparison here
    would silently never match, which is how this check would have quietly died when digests landed.
    """
    return {o for o in live if name_of(o) in ADR0011_REMOVED}


def report(objs: set[str], prefix: str) -> list[str]:
    """Group and format offending objects for stderr. PURE."""
    lines = []
    for kind, items in by_kind(objs).items():
        lines.append(f"  {len(items)} {label(kind, len(items))}:")
        for o in items[:12]:
            lines.append(f"      {prefix} {o}")
        if len(items) > 12:
            lines.append(f"      … and {len(items) - 12} more")
    return lines


# ---------------------------------------------------------------- self-test
def self_test() -> int:
    cases = failures = 0

    def check(label_: str, got: object, want: object) -> None:
        nonlocal cases, failures
        cases += 1
        ok = got == want
        print(("  ✓ " if ok else f"  ✗ [{got!r} != {want!r}] ") + label_)
        failures += 0 if ok else 1

    # objects carry `@digest`; the digest is what makes the verdict about BEHAVIOUR, not names.
    TRG = "trg:video_artifacts.video_artifacts_append_only_trg@aaa111"
    FN = "fn:record_artifact(uuid)@bbb222"
    CON = "con:video_artifacts.art_dig_has_span@ccc333"
    M = {"table:workspaces", "view:video_artifacts_current@v1",
         "col:playlists.workspace_id@c1", "trg:profiles.profiles_ensure_workspace_trg@t1",
         TRG, FN, CON, "type:artifact_kind@e1", "idx:va_pkey@i1",
         "pol:workspaces.ws_owner@p1"}
    none: set[str] = set()

    check("absent passes when nothing remains", verdict(none, M, "absent"), True)
    check("absent FAILS when a table survives", verdict({"table:workspaces"}, M, "absent"), False)
    check("absent IGNORES unrelated objects",
          verdict({"table:profiles", "idx:profiles_pkey@x"}, M, "absent"), True)
    check("present passes when complete", verdict(set(M), M, "present"), True)

    # ⭐⭐ THE r4 B1 CASES — the name is present, the BEHAVIOUR is not. Every one of these returned
    # exit 0 before digests, including on a real database.
    for label_, obj, changed in (
            ("a trigger is DISABLED (tgenabled D, name unchanged)", TRG,
             "trg:video_artifacts.video_artifacts_append_only_trg@DISABLED"),
            ("a guard function is `create or replace`d with a new body", FN,
             "fn:record_artifact(uuid)@REPLACED"),
            ("a constraint is weakened to `check (true)`", CON,
             "con:video_artifacts.art_dig_has_span@WEAKENED")):
        live = (set(M) - {obj}) | {changed}
        check(f"present FAILS when {label_}", verdict(live, M, "present"), False)
        miss, redef = split_residue(live, M)
        check(f"…and it is reported as REDEFINED, not missing — {label_[:28]}",
              (miss, redef) == (set(), {obj}), True)

    check("a genuinely NEVER-CREATED object is reported as missing, not redefined",
          split_residue(set(M) - {TRG}, M) == ({TRG}, set()), True)

    for kind, obj in (("view", "view:video_artifacts_current@v1"), ("index", "idx:va_pkey@i1"),
                      ("policy", "pol:workspaces.ws_owner@p1"),
                      ("constraint", CON), ("column", "col:playlists.workspace_id@c1")):
        check(f"present FAILS when a {kind} is missing — the 29-object gate named ZERO of these",
              verdict(set(M) - {obj}, M, "present"), False)

    check("absent FAILS on the cascade residue (a live-table trigger alive, tables gone)",
          verdict({"trg:profiles.profiles_ensure_workspace_trg@t1"}, M, "absent"), False)
    check("absent FAILS when a function survives — a wrong drop signature is a SILENT no-op",
          verdict({FN}, M, "absent"), False)

    # ADR-0011 objects are matched by NAME: they must not exist whatever their definition, and a
    # digest-bearing comparison here would silently never match.
    sync = {"fn:sync_corrections_to_workspace_video()@whatever"}
    check("absent FAILS when the ADR-0011 sync function survives, ANY digest",
          verdict(sync, M, "absent"), False)
    check("PRESENT also FAILS on an ADR-0011 object — a half-applied Task 1 is not a valid M4",
          verdict(set(M) | sync, M, "present"), False)
    check("forbidden matches by NAME, ignoring the digest", forbidden(sync), sync)
    check("forbidden is EMPTY on a clean schema", forbidden(set(M)), set())

    check("residue NAMES what SURVIVED in absent mode",
          residue({"table:workspaces"}, M, "absent"), {"table:workspaces"})
    check("name_of strips the digest", name_of(TRG),
          "trg:video_artifacts.video_artifacts_append_only_trg")

    print(f"\n{cases - failures}/{cases} self-test cases passed")
    if failures == 0:
        print("⚠ the last case documents WHY load_manifest raises on an empty file: the pure\n"
              "  verdict cannot distinguish 'nothing expected' from 'all present'.")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--expect-absent", action="store_true")
    g.add_argument("--expect-present", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--database", default="postgres",
                    help="target database INSIDE the local container; used by the mutation harness "
                         "to point at a scratch DB, because this gate opens its own connection and "
                         "so cannot be proved red inside someone else's transaction")
    ap.add_argument("--prod", action="store_true",
                    help="read PRODUCTION over CLAUDE_RO_DATABASE_URL instead of the local "
                         "container. ⟳ r4 B2: without this the gate could only ever read the "
                         "laptop, while the plan said to point it at prod.")
    ap.add_argument("--manifest", default=MANIFEST)
    a = ap.parse_args()

    if a.self_test:
        return self_test()
    if not (a.expect_absent or a.expect_present):
        print("CANNOT RUN — pass --expect-absent or --expect-present. There is no default: a gate\n"
              "that guesses which polarity to assert is how this plan shipped an unsatisfiable\n"
              "milestone twice. Treat this as NOT RUN.", file=sys.stderr)
        return 2

    mode = "absent" if a.expect_absent else "present"
    url = None
    if a.prod:
        url = read_only_url()
        if not url:
            print("CANNOT RUN — --prod needs CLAUDE_RO_DATABASE_URL (checked env and .env.local).\n"
                  "Without it this would silently read the LOCAL container and report on the wrong\n"
                  "database. Treat this as NOT RUN.", file=sys.stderr)
            return 2
    try:
        manifest = load_manifest(a.manifest)
        live = read_catalog(a.database, url=url)
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        print(f"CANNOT RUN — {e}\nTreat this as NOT RUN.", file=sys.stderr)
        return 2

    subject = "PRODUCTION (read-only claude_ro)" if url else f"local container db '{a.database}'"
    if verdict(live, manifest, mode):
        print(f"live schema [{subject}]: M4 is {mode.upper()} as expected — checked all "
              f"{len(manifest)} objects, BY DEFINITION not just by name ({summarise(manifest)})")
        return 0

    gone = forbidden(live)
    if gone:
        print("FAILED — objects ADR-0011 DELETED are present, so Task 1 did not fully land and\n"
              "0027 carries objects the rollback never names:\n", file=sys.stderr)
        for line in report(gone, "✗"):
            print(line, file=sys.stderr)
        print(file=sys.stderr)

    bad = residue(live, manifest, mode)
    if bad and mode == "absent":
        print(f"FAILED — expected M4 ABSENT; {len(bad)} of {len(manifest)} objects are SURVIVING:\n",
              file=sys.stderr)
        for line in report(bad, "✗"):
            print(line, file=sys.stderr)
    elif bad:
        missing, redefined = split_residue(live, manifest)
        if missing:
            print(f"FAILED — expected M4 PRESENT; {len(missing)} of {len(manifest)} objects were "
                  f"NEVER CREATED:\n", file=sys.stderr)
            for line in report(missing, "✗"):
                print(line, file=sys.stderr)
        if redefined:
            print(f"\n⛔ AND {len(redefined)} object(s) EXIST BUT DO NOT MATCH THEIR DEFINITION —\n"
                  "   the name is there and the behaviour is not. A DISABLED trigger, a "
                  "`create or replace`d\n   function body, or a constraint weakened to "
                  "`check (true)` all look like this:\n", file=sys.stderr)
            for o in sorted(redefined):
                print(f"      ✗ {name_of(o)}", file=sys.stderr)
        if mode == "absent" and any(o.startswith("trg:") for o in bad):
            print("\n⚠ A SURVIVING TRIGGER ON A LIVE TABLE MEANS THE PRODUCT IS DOWN, not merely\n"
                  "  untidy — it still calls tables that are gone. Signup, playlist creation and\n"
                  "  enqueue all fail. This is the state `drop table … cascade` produces.",
                  file=sys.stderr)
        if mode == "present":
            print("\n⚠ A PARTIALLY APPLIED M4 IS THE DANGEROUS STATE: the guard triggers are what\n"
                  "  make the artifact tables append-only. A schema with the tables and without\n"
                  "  their guards accepts writes the design forbids.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
