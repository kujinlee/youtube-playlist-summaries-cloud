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
from m4_catalog import (CATALOG_SQL, ENFORCEMENT_COLUMNS, by_kind, label,  # noqa: E402
                        name_of, read_catalog, read_identity, read_only_url, summarise,
                        symbol_of)

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


def _keys(obj: str) -> set[str]:
    """EVERY SPELLING under which `obj` could be one of the ADR-0011 objects. PURE.

    ⟳ r5 L2 (claude): `forbidden()` compared whole rendered names, and `ADR0011_REMOVED` records
    `fn:sync_corrections_to_workspace_video()` — one particular rendering. The same drift that makes
    a `drop function` signature a silent no-op (r5 B1, MEASURED) evades that match too: a survivor
    carrying one extra parameter renders as `…_workspace_video(uuid)` and is simply not in the set.
    A must-never-exist check that can be defeated by adding an argument is not a must-never-exist
    check, so it matches the SYMBOL, and — for triggers — the trigger name whatever table carries it.
    """
    n = name_of(obj)
    keys = {n, symbol_of(obj)}
    if n.startswith("trg:") and "." in n:
        keys.add("trg:" + n.rsplit(".", 1)[1])
    return keys


FORBIDDEN_KEYS = {k for o in ADR0011_REMOVED for k in _keys(o)}


def load_manifest(path: str = MANIFEST) -> set[str]:
    """The derived expected object set, VERIFIED against its own header.

    ⛔ r4 B2 — A NON-EMPTY CHECK IS NOT AN INTEGRITY CHECK. This used to accept any file with at
    least one line. MEASURED: a manifest of one line, against a database holding that one object,
    produced **"M4 is PRESENT as expected — checked all 1 objects", exit 0** — over a database
    missing 160 of 161. Because the verdict is a SUBSET test, shrinking the manifest shrinks the
    claim, and the gate reports the smaller number as though it were the whole.

    That is r3 B2 recurring one level up: the trust root moved from a hand-written list to a derived
    file, and the *guarantee* did not move with it. So the file states its own object count and a
    sha256 of its body, and both are checked here.

    ⛔ WHAT THAT HEADER DOES AND DOES NOT BUY — ⟳ r5 H1 (claude) / r5 M (codex).
    **It is a self-consistency check, not an integrity check, and this docstring used to claim
    otherwise.** `objs` is parsed from the very file that carries the claimed digest, so any editor
    who changes the body can recompute both fields. MEASURED: the committed manifest reduced to ONE
    object with its two header fields recomputed — about three lines of Python — and the gate printed
    **"M4 is PRESENT as expected — checked all 1 objects", exit 0** against a full M4 database. That
    is r4 B2 verbatim, restored. The r4 fix raised the price of the attack from *delete lines* to
    *delete lines and rerun a hash*; it did not change its category.

    So state the defence honestly, because a reader who believes this file self-authenticates will
    not look for the real one:
        * TRUNCATION and partial writes  -> caught here.
        * A DELIBERATE OR MISTAKEN EDIT  -> caught by **gate 7** (`gen-m4-manifest.py --check`),
          which re-derives the set by executing the schema, and by review of the diff in git.
    Gate 7 is therefore load-bearing, not a convenience — which is why r5 B3 (it could not run in
    the post phase, the one phase where this manifest carries the production assertion) was Blocking.
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
            f"the manifest at {path} does not match its own sha256, so it is TRUNCATED or partially\n"
            "written. (An edit that recomputes the header passes this check — see load_manifest;\n"
            "the defence against an edit is gate 7, gen-m4-manifest.py --check, plus the git diff.)\n"
            "It is DERIVED: regenerate it with python3 scripts/gen-m4-manifest.py")
    return objs


# ---------------------------------------------------------------- pure verdict
def survivors(live: set[str], manifest: set[str]) -> set[str]:
    """Live objects M4 created that are STILL THERE — matched by NAME, not by digest. PURE.

    ⛔⛔ r5 B1 (codex + claude), the round's headline. The two polarities ask DIFFERENT QUESTIONS,
    and r4 moved both to the same predicate:

        present : "does the live object match the definition M4 shipped?"   -> name@digest. Right.
        absent  : "does an object M4 created still exist AT ALL?"           -> name. The definition
                  is irrelevant, and requiring it to match makes every drifted survivor invisible.

    MEASURED by both halves independently, on a real database, after the REAL rollback:

      * a guard function `create or replace`d once before the rollback (the shape of any hotfix) —
        the rollback misses it, and `--expect-absent` goes from exit 1 to **exit 0**;
      * `record_artifact` drifted by one defaulted parameter, so the rollback's exact 13-type
        `drop function if exists` is a silent no-op — leaving a live **SECURITY DEFINER** M4 function
        on a database this gate certified as M4-free, printing
        *"M4 is ABSENT as expected — checked all 161 objects, BY DEFINITION not just by name"*.

    ⚠ `forbidden()` below already carried the correct reasoning IN THIS FILE, IN THE SAME COMMIT —
    *"a digest-bearing comparison here would silently never match"* — and it was not applied here.
    That is the round's whole lesson: the guarantee was carried across in one direction only.

    ⭐ MATCHED ON THE SYMBOL, NOT ON `name_of`, AND THAT DISTINCTION IS THE WHOLE SECOND CASE.
    Both review halves prescribed `name_of`. **`name_of` does not fix the case they measured.** A
    function that drifted by one added parameter renders as `fn:record_artifact(…, text)`, whose
    `name_of` is not the manifest's `fn:record_artifact(…)` either — so the survivor stays invisible
    under the prescribed fix, and only the first of the two measured cases would have gone red. The
    predicate has to drop the argument list as well as the digest, which is the same normalisation
    `_keys` needed for r5 L2. Adopting a review's fix DIRECTION without re-deriving it against its
    own evidence is how a round produces a fix that passes its own test and not the defect.

    Over-matching here is deliberate and fail-closed: a `record_artifact` of ANY signature sitting on
    a database that is supposed to be M4-free is worth stopping the rollback for.
    """
    symbols = {symbol_of(o) for o in manifest}
    return {o for o in live if symbol_of(o) in symbols}


def verdict(live: set[str], manifest: set[str], mode: str) -> bool:
    """PURE. True = pass.

    present: every manifest object is live, BY DEFINITION (name@digest).
    absent : no object M4 created is live, BY NAME (see `survivors`).
    BOTH   : nothing ADR-0011 removed is live.
    """
    if forbidden(live):
        return False
    if mode == "absent":
        return not survivors(live, manifest)
    return manifest <= live


def residue(live: set[str], manifest: set[str], mode: str) -> set[str]:
    """What is wrong — so a failure NAMES the objects. PURE.

    Absent mode reports the LIVE objects (with their current digests), because what the reader needs
    is the thing still sitting in the database, not the manifest line it failed to match.
    """
    return survivors(live, manifest) if mode == "absent" else (manifest - live)


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
    **That sentence describes r5 B1 exactly, and `verdict`'s absent branch did not apply it.**

    ⟳ r5 L2: matched on every spelling (see `_keys`), so an added argument cannot smuggle one past.
    """
    return {o for o in live if _keys(o) & FORBIDDEN_KEYS}


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
    check("absent FAILS when a function survives byte-identical", verdict({FN}, M, "absent"), False)

    # ⭐⭐ THE r5 B1 CASES. Every one of these printed "M4 is ABSENT as expected", exit 0, on a real
    # database — the rollback gate blessing live M4 objects, including a SECURITY DEFINER function.
    #
    # ⚠ THE OLD FIXTURE COULD NOT EXHIBIT THE BUG IT WAS NAMED AFTER. The case above was labelled
    # "a wrong drop signature is a SILENT no-op" and passed `{FN}` — an element OF the manifest. A
    # wrong drop signature is BY DEFINITION the case where the live signature is not the manifest's,
    # so the fixture asserted the one shape that was never broken. A test whose fixture cannot
    # express its own title is a green light bolted to the wall.
    for label_, survivor in (
            ("its BODY was hot-fixed before the rollback (same name, new digest)",
             "fn:record_artifact(uuid)@HOTFIXED"),
            ("it drifted by one DEFAULTED PARAMETER, so `drop function` was a silent no-op",
             "fn:record_artifact(uuid, text)@DRIFTED"),
            ("a trigger survived with a rewritten definition",
             "trg:video_artifacts.video_artifacts_append_only_trg@REWRITTEN")):
        check(f"absent FAILS when an M4 object survives and {label_}",
              verdict({survivor}, M, "absent"), False)
        check(f"…and residue names the LIVE object, not the manifest line — {label_[:26]}",
              residue({survivor}, M, "absent"), {survivor})

    check("absent still IGNORES a same-named object of a DIFFERENT KIND",
          verdict({"idx:record_artifact@i9"}, M, "absent"), True)

    # ADR-0011 objects are matched by SYMBOL: they must not exist whatever their definition OR
    # ARGUMENT LIST, and a digest-bearing comparison here would silently never match.
    sync = {"fn:sync_corrections_to_workspace_video()@whatever"}
    check("absent FAILS when the ADR-0011 sync function survives, ANY digest",
          verdict(sync, M, "absent"), False)
    check("PRESENT also FAILS on an ADR-0011 object — a half-applied Task 1 is not a valid M4",
          verdict(set(M) | sync, M, "present"), False)
    check("forbidden matches by NAME, ignoring the digest", forbidden(sync), sync)
    check("forbidden is EMPTY on a clean schema", forbidden(set(M)), set())

    # ⟳ r5 L2 — the ADR-0011 set records ONE rendering of each object.
    drifted_sync = {"fn:sync_corrections_to_workspace_video(uuid)@x"}
    check("forbidden catches the ADR-0011 function with an ADDED ARGUMENT (r5 L2)",
          forbidden(drifted_sync), drifted_sync)
    moved_trg = {"trg:workspace_videos.videos_corrections_sync_ins_trg@x"}
    check("forbidden catches the ADR-0011 trigger on a DIFFERENT TABLE (r5 L2)",
          forbidden(moved_trg), moved_trg)
    check("forbidden does NOT fire on an unrelated function that merely shares a prefix",
          forbidden({"fn:sync_corrections_to_workspace_video_v2()@x"}), set())

    check("residue NAMES what SURVIVED in absent mode",
          residue({"table:workspaces"}, M, "absent"), {"table:workspaces"})
    check("name_of strips the digest", name_of(TRG),
          "trg:video_artifacts.video_artifacts_append_only_trg")
    check("symbol_of strips the digest AND the argument list", symbol_of(FN), "fn:record_artifact")

    # ⭐ r5 B2 — "WHAT DOES THIS SELECT NOT SELECT?" asked mechanically.
    # The digest covered definitions and not enforcement state, and nothing named the properties it
    # was supposed to cover — so "we added a digest" and "the digest covers enforcement" could both
    # be believed at once. Deleting a column from CATALOG_SQL is now a RED TEST rather than a
    # silently narrower gate. This cannot prove the list is COMPLETE; it proves it is not shrinking.
    for col in ENFORCEMENT_COLUMNS:
        check(f"CATALOG_SQL still reads {col} — the flag that decides whether a rule EXECUTES",
              col in CATALOG_SQL, True)

    print(f"\n{cases - failures}/{cases} self-test cases passed")
    if failures == 0:
        print("⚠ TWO THINGS THESE CASES DO NOT PROVE:\n"
              "  * that ENFORCEMENT_COLUMNS is COMPLETE — only that it is not shrinking. The\n"
              "    behavioural proof is scripts/mutate-live-schema-check.sh, which sabotages a real\n"
              "    database and requires RED.\n"
              "  * that an EMPTY manifest is safe: the pure verdict cannot distinguish 'nothing\n"
              "    expected' from 'all present', which is why load_manifest raises on one.")
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
        # ⟳ r5 M5 (claude) / r5 H (codex): WHO answered, measured on the same connection, before the
        # verdict. The subject used to be inferred from whether an env var was set, so pointing
        # CLAUDE_RO_DATABASE_URL at a local scratch database as `postgres` printed
        # "PRODUCTION (read-only claude_ro)". After r4 B2 — the gate reading the laptop while
        # claiming production — the one property this line must have is that it cannot be a claim.
        identity = read_identity(a.database, url=url)
        live = read_catalog(a.database, url=url)
    except (FileNotFoundError, ValueError, RuntimeError) as e:
        print(f"CANNOT RUN — {e}\nTreat this as NOT RUN.", file=sys.stderr)
        return 2

    where = "--prod" if url else f"local container db '{a.database}'"
    subject = f"{where} — {identity}"
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
