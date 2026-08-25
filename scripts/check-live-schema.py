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
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m4_catalog import by_kind, label, read_catalog, summarise  # noqa: E402

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
    """The derived expected object set. Raises FileNotFoundError / ValueError, never guesses."""
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"no manifest at {path}. Generate it: python3 scripts/gen-m4-manifest.py")
    with open(path) as f:
        objs = {ln.strip() for ln in f if ln.strip() and not ln.startswith("#")}
    if not objs:
        raise ValueError(
            f"the manifest at {path} is EMPTY. An empty expected set makes --expect-present pass\n"
            "over any database at all, which is the failure this gate exists to prevent.")
    return objs


# ---------------------------------------------------------------- pure verdict
def verdict(live: set[str], manifest: set[str], mode: str) -> bool:
    """PURE. True = pass.

    present: every manifest object is live.
    absent : no manifest object is live.
    BOTH   : nothing ADR-0011 removed is live.
    """
    if live & ADR0011_REMOVED:
        return False
    if mode == "absent":
        return not (live & manifest)
    return manifest <= live


def residue(live: set[str], manifest: set[str], mode: str) -> set[str]:
    """What is wrong — so a failure NAMES the objects. PURE."""
    return (live & manifest) if mode == "absent" else (manifest - live)


def forbidden(live: set[str]) -> set[str]:
    """ADR-0011-removed objects that are nonetheless present. PURE."""
    return live & ADR0011_REMOVED


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

    M = {"table:workspaces", "table:video_generations", "view:video_artifacts_current",
         "col:playlists.workspace_id", "trg:profiles.profiles_ensure_workspace_trg",
         "trg:video_artifacts.video_artifacts_append_only_trg",
         "fn:record_artifact(uuid)", "type:artifact_kind", "idx:va_pkey",
         "pol:workspaces.ws_owner", "con:videos.videos_workspace_video_fk"}
    none: set[str] = set()

    check("absent passes when nothing remains", verdict(none, M, "absent"), True)
    check("absent FAILS when a table survives", verdict({"table:workspaces"}, M, "absent"), False)
    check("absent IGNORES unrelated objects",
          verdict({"table:profiles", "idx:profiles_pkey"}, M, "absent"), True)
    check("present passes when complete", verdict(set(M), M, "present"), True)

    # ⭐ THE MEASURED B2 CASE — every own-table guard trigger dropped. The old gate returned 0 here.
    no_guard = set(M) - {"trg:video_artifacts.video_artifacts_append_only_trg"}
    check("present FAILS when an OWN-TABLE guard trigger is missing (r3 B2)",
          verdict(no_guard, M, "present"), False)
    for kind, obj in (("view", "view:video_artifacts_current"), ("index", "idx:va_pkey"),
                      ("policy", "pol:workspaces.ws_owner"),
                      ("constraint", "con:videos.videos_workspace_video_fk"),
                      ("column", "col:playlists.workspace_id")):
        check(f"present FAILS when a {kind} is missing — the old gate named ZERO of these",
              verdict(set(M) - {obj}, M, "present"), False)

    check("absent FAILS on the cascade residue (a live-table trigger alive, tables gone)",
          verdict({"trg:profiles.profiles_ensure_workspace_trg"}, M, "absent"), False)
    check("absent FAILS when a function survives — a wrong drop signature is a SILENT no-op",
          verdict({"fn:record_artifact(uuid)"}, M, "absent"), False)
    check("absent FAILS when the enum survives", verdict({"type:artifact_kind"}, M, "absent"), False)

    sync = {"fn:sync_corrections_to_workspace_video()"}
    check("absent FAILS when the ADR-0011 sync function survives", verdict(sync, M, "absent"), False)
    check("PRESENT also FAILS on an ADR-0011 object — a half-applied Task 1 is not a valid M4",
          verdict(set(M) | sync, M, "present"), False)
    check("forbidden NAMES the offending object", forbidden(sync), sync)
    check("forbidden is EMPTY on a clean schema", forbidden(set(M)), set())

    check("residue NAMES what is MISSING in present mode",
          residue(no_guard, M, "present"), {"trg:video_artifacts.video_artifacts_append_only_trg"})
    check("residue NAMES what SURVIVED in absent mode",
          residue({"table:workspaces"}, M, "absent"), {"table:workspaces"})

    # an empty manifest must never be treated as "everything is fine"
    check("an EMPTY manifest would make present vacuous — load_manifest must reject it, so the\n"
          "     verdict function is never asked", verdict(none, set(), "present"), True)

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
                    help="target database; used by the mutation harness to point at a scratch DB, "
                         "because this gate opens its own connection and so cannot be proved red "
                         "inside someone else's transaction")
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
    try:
        manifest = load_manifest(a.manifest)
        live = read_catalog(a.database)
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        print(f"CANNOT RUN — {e}\nTreat this as NOT RUN.", file=sys.stderr)
        return 2

    if verdict(live, manifest, mode):
        print(f"live schema: M4 is {mode.upper()} as expected — checked all {len(manifest)} "
              f"objects ({summarise(manifest)})")
        return 0

    gone = forbidden(live)
    if gone:
        print("FAILED — objects ADR-0011 DELETED are present, so Task 1 did not fully land and\n"
              "0027 carries objects the rollback never names:\n", file=sys.stderr)
        for line in report(gone, "✗"):
            print(line, file=sys.stderr)
        print(file=sys.stderr)

    bad = residue(live, manifest, mode)
    if bad:
        word = "SURVIVING" if mode == "absent" else "MISSING"
        print(f"FAILED — expected M4 {mode.upper()}; {len(bad)} of {len(manifest)} objects are "
              f"{word}:\n", file=sys.stderr)
        for line in report(bad, "✗"):
            print(line, file=sys.stderr)
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
