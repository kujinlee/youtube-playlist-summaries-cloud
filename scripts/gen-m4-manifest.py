#!/usr/bin/env python3
"""Derive the M4 object manifest BY EXECUTION, and write it where the gate can read it.

    python3 scripts/gen-m4-manifest.py            # writes the manifest
    python3 scripts/gen-m4-manifest.py --check    # regenerate and FAIL if it differs (ratchet)

    exit 0 = written (or, with --check, current)
    exit 1 = --check and the manifest is STALE
    exit 2 = could not run (treat as NOT RUN)

HOW IT DERIVES, AND WHY NOT BY PARSING
--------------------------------------
It clones the live PRE-M4 schema into a throwaway database, applies the schema
`build-m4-schema.py` emits, and takes `after EXCEPT before` over the full catalog. **The manifest is
therefore what Postgres actually creates**, not what someone read in a `.sql` file.

Parsing the SQL would reproduce the defect this replaces: the old gate's inventory was hand-written,
and separately, `grep -c "^create trigger"` undercounts by one because
`art_summary_has_no_source_trg` is a `create constraint trigger`. Any reader of the text inherits
that class of error; the catalog does not.

⛔ THE BASELINE IS A THROWAWAY CLONE, NOT THE DEVELOPER'S DATABASE — ⟳ r5 B3 (claude)
--------------------------------------------------------------------------------------
The manifest is a DIFF, so a baseline that already has M4 makes `after EXCEPT before` empty or
partial, and the generator would write a manifest asserting almost nothing — a gate that passes over
any database at all. The first version handled that by REFUSING when the local `postgres` database
had M4.

**Which made `M4_PHASE=post ./scripts/check-schema-gates.sh` permanently unsatisfiable.** In the post
phase the local database has 0027 applied *by definition* — that is what "post" means — so gate 7
exited 2, `run()` set `fail=1`, and the suite could never go green again from the moment the
milestone succeeded. MEASURED (exit 2). That was **the third unsatisfiable milestone this plan has
shipped, in the gate added to close the second**, and it was worse than a red suite: gate 7 is the
only thing that can detect an edited manifest (`check-live-schema.py:load_manifest` — the in-file
sha256 is self-consistent, so it cannot), and the post phase is exactly when the manifest carries the
production assertion.

The cause was not the refusal. It was reading `before` from **the machine's working database** at
all, which also made the diff asymmetric: `before` came from `postgres` while `after` came from a
`pg_dump --no-privileges` clone, so any privilege-sensitive digest would differ for reasons that have
nothing to do with M4 — and r5 B2 has just put ACLs in the digest. Both are gone: BOTH readings now
come from the same throwaway database, and if that clone arrives carrying M4 the ROLLBACK is applied
to it (never to anything shared) to produce the pre-M4 baseline. The generator no longer cares which
phase the developer is in.

⚠ It still fails closed if the rollback leaves M4 behind — an incomplete rollback would silently
shrink the manifest, which is the same class of defect one level down.

FAILS IF
--------
the baseline still contains M4 after the rollback; Docker or the spec is unreachable (exit 2); or,
with `--check`, the committed manifest differs from what the schema now produces (exit 1).
"""
from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m4_catalog import (CONTAINER, by_kind, read_catalog,  # noqa: E402
                        summarise, survivors)

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(REPO, "docs", "superpowers", "specs", "m4", "live-manifest.txt")
ROLLBACK = os.path.join(REPO, "supabase", "rollback", "rollback_0027_stable_blob_addressing.sql")
SCRATCH = f"m4_manifest_gen_{os.getpid()}"   # ⟳ r6 L1: per-process, see the harness

# ⛔ r4 B2 (codex + claude) — THE FILE MUST ASSERT ITS OWN COMPLETENESS.
# The loader used to accept any non-empty file. MEASURED: a manifest containing one line, against a
# database containing that one object, printed "M4 is PRESENT as expected — checked all 1 objects",
# exit 0 — over a database missing 160 of 161. Truncating the trust root silently REDEFINES what
# "complete" means, which is r3 B2 again, one level up. These two lines are checked by the loader,
# so a short file is a CANNOT RUN rather than a pass.
HEADER = """\
# M4 LIVE MANIFEST — every object migration 0027 creates, DERIVED BY EXECUTION.
#
# objects: {total}
# sha256: {digest}
#
# ⛔ DO NOT HAND-EDIT. Regenerate:  python3 scripts/gen-m4-manifest.py
#    Verify it is current:          python3 scripts/gen-m4-manifest.py --check
#
# Produced by cloning the live pre-M4 schema into a throwaway database, applying the output of
# `build-m4-schema.py`, and taking `after EXCEPT before` over the full catalog. One line per object,
# `kind:name`, sorted. `check-live-schema.py` compares a live database against exactly this set.
#
# ⟳ r3 B2: the gate this replaces named 29 of these {total} objects (18%) and reported
#   "M4 is PRESENT as expected" over a database with all seven of M4's own-table guard triggers
#   dropped.
#
# {summary}
"""


def psql(db: str, sql: str) -> subprocess.CompletedProcess[str]:
    # ON_ERROR_STOP, because the rollback is applied through here and a returncode that ignores SQL
    # errors would make "the rollback applied" unfalsifiable — the exact shape this plan keeps
    # shipping. (The has_m4 re-check below is the second line of defence, not the first.)
    return subprocess.run(
        ["docker", "exec", "-i", CONTAINER, "psql", "-U", "postgres", "-d", db, "-tAq",
         "-v", "ON_ERROR_STOP=1"],
        input=sql, capture_output=True, text=True)


def drop_scratch() -> None:
    psql("postgres", f"drop database if exists {SCRATCH} (force);")


M4_MARKERS = ("table:workspaces", "table:video_generations")


def has_m4(catalog: set[str], manifest: set[str] | None = None) -> bool:
    """Does this catalog carry M4? PURE.

    ⟳ r6 M1 (claude): this was TWO TABLE NAMES, and the docstring above claimed it "fails closed if
    the rollback leaves M4 behind". MEASURED — a rollback with four `drop` lines commented out left
    `corrections_hash_of`, `no_corrections_hash`, `slot_kind` and the `artifact_kind` ENUM behind,
    and this returned False over all four. What actually failed closed was the schema's
    NON-IDEMPOTENCY (zero `create or replace`, zero `if not exists`, so re-applying over a survivor
    is a hard error) — an accident, not the stated guarantee, and one line of `create or replace`
    away from being gone.

    `check-live-schema.survivors()` already answers this question correctly over all 161 objects. A
    second, weaker definition of "does this database have M4" is exactly the duplicate-mechanism
    shape `check-vocabulary-collisions.py` exists to find — in the file that fixed the
    `read_only_url` duplication this same round.
    """
    if manifest:
        return bool(survivors(catalog, manifest))
    names = {o.split("@", 1)[0] for o in catalog}
    return any(m in names for m in M4_MARKERS)


def _committed() -> set[str] | None:
    """The committed manifest's object set, or None. Used only to give `has_m4` the real predicate."""
    return read_committed()


def derive(source: str = "postgres") -> set[str]:
    """Build the manifest by executing the schema. Raises RuntimeError with a reason.

    Both readings come from SCRATCH, never from `source` — see the module docstring (r5 B3).
    Nothing here writes to the source database.

    `source` exists so the POST-PHASE PATH CAN BE PROVEN. Without it the rollback branch below is
    only reachable on a machine that has already crossed M4-β, i.e. exactly when it is too late to
    discover it does not work — and "the fix for the unsatisfiable gate is itself unexercised" is
    the shape this review round keeps finding. `--self-test` points it at a scratch M4 database.
    """
    drop_scratch()
    if psql("postgres", f"create database {SCRATCH};").returncode != 0:
        raise RuntimeError("could not create the scratch database")

    clone = subprocess.run(
        ["docker", "exec", "-i", CONTAINER, "sh", "-c",
         f"pg_dump -U postgres -d {source} --schema-only --no-owner --no-privileges "
         f"| psql -U postgres -d {SCRATCH} -q"],
        capture_output=True, text=True)
    if clone.returncode != 0:
        raise RuntimeError(f"could not clone the baseline schema: {clone.stderr.strip()[:200]}")

    try:
        before = read_catalog(SCRATCH)
    except (RuntimeError, FileNotFoundError) as e:
        raise RuntimeError(f"could not read the baseline catalog: {e}") from e

    # ⟳ r5 B3: the clone carries M4 exactly when the developer is in the POST phase. Roll it back —
    # ON THE THROWAWAY, never on anything shared — instead of refusing, which made the post-phase
    # suite unsatisfiable. This also means every `--check` run EXERCISES the rollback file, which
    # until now nothing executed.
    if has_m4(before, _committed()):
        if not os.path.exists(ROLLBACK):
            raise RuntimeError(
                f"the baseline clone has M4 applied and there is no rollback at {ROLLBACK} to\n"
                "produce a pre-M4 baseline from it.")
        with open(ROLLBACK) as f:
            rolled = psql(SCRATCH, f.read())
        if rolled.returncode != 0:
            raise RuntimeError(
                f"the rollback did not apply to the baseline clone: {rolled.stderr.strip()[-300:]}")
        before = read_catalog(SCRATCH)
        # fail closed: an INCOMPLETE rollback shrinks the diff, which silently shrinks the manifest
        if has_m4(before, _committed()):
            raise RuntimeError(
                "the rollback ran on the baseline clone and M4 IS STILL THERE, so `after EXCEPT\n"
                "before` would be partial and this would write a manifest that passes over any\n"
                f"database. Fix {os.path.relpath(ROLLBACK, REPO)} first — and note that the same\n"
                "incompleteness would leave objects behind in production.")

    built = subprocess.run(
        [sys.executable, os.path.join(REPO, "scripts", "build-m4-schema.py"), "--quiet"],
        capture_output=True, text=True)
    if built.returncode != 0:
        raise RuntimeError(f"build-m4-schema.py failed: {built.stderr.strip()[:300]}")

    applied = subprocess.run(
        ["docker", "exec", "-i", CONTAINER, "psql", "-U", "postgres", "-d", SCRATCH,
         "-tAq", "-v", "ON_ERROR_STOP=1"],
        input=built.stdout, capture_output=True, text=True)
    if applied.returncode != 0:
        raise RuntimeError(f"the schema did not apply: {applied.stderr.strip()[-300:]}")

    after = read_catalog(SCRATCH)
    manifest = after - before
    if not manifest:
        raise RuntimeError("the diff is EMPTY — the schema applied but created nothing new")
    return manifest


def body_digest(manifest: set[str]) -> str:
    """sha256 over the sorted body, exactly as written. PURE."""
    return hashlib.sha256(("\n".join(sorted(manifest)) + "\n").encode()).hexdigest()


def render(manifest: set[str]) -> str:
    return (HEADER.format(total=len(manifest), summary=summarise(manifest),
                          digest=body_digest(manifest))
            + "\n".join(sorted(manifest)) + "\n")


def read_committed() -> set[str] | None:
    if not os.path.exists(MANIFEST):
        return None
    with open(MANIFEST) as f:
        return {ln.strip() for ln in f if ln.strip() and not ln.startswith("#")}


def self_test() -> int:
    """⭐ r5 B3 — PROVE THE POST-PHASE PATH, which is otherwise only reachable after M4-β.

    Builds a scratch database that HAS M4, points `derive()` at it as the baseline, and requires the
    SAME 161-object manifest a pre-M4 baseline produces. Before this fix that call raised
    "the baseline database ALREADY HAS M4 applied", which is what made
    `M4_PHASE=post ./scripts/check-schema-gates.sh` permanently red.
    """
    m4db = f"m4_manifest_gen_post_{os.getpid()}"
    cases = failures = 0

    def check(label: str, ok: bool) -> None:
        nonlocal cases, failures
        cases += 1
        print(("  ✓ " if ok else "  ✗ ") + label)
        failures += 0 if ok else 1

    def drop() -> None:
        psql("postgres", f"drop database if exists {m4db} (force);")

    try:
        pre = derive()
        check(f"a PRE-M4 baseline derives a manifest ({len(pre)} objects)", len(pre) > 100)

        drop()
        if psql("postgres", f"create database {m4db};").returncode != 0:
            print("  ✗ CANNOT RUN — could not create the post-phase probe database")
            return 1
        subprocess.run(["docker", "exec", "-i", CONTAINER, "sh", "-c",
                        f"pg_dump -U postgres -d postgres --schema-only --no-owner --no-privileges "
                        f"| psql -U postgres -d {m4db} -q"], capture_output=True, text=True)
        built = subprocess.run([sys.executable, os.path.join(REPO, "scripts", "build-m4-schema.py"),
                                "--quiet"], capture_output=True, text=True)
        applied = subprocess.run(
            ["docker", "exec", "-i", CONTAINER, "psql", "-U", "postgres", "-d", m4db,
             "-tAq", "-v", "ON_ERROR_STOP=1"], input=built.stdout, capture_output=True, text=True)
        if applied.returncode != 0:
            print(f"  ✗ CANNOT RUN — could not build an M4 database: {applied.stderr[-200:]}")
            return 1
        check("the probe database really has M4", has_m4(read_catalog(m4db)))

        post = derive(source=m4db)
        check("a POST-M4 baseline derives a manifest at all (r5 B3: this used to RAISE)", bool(post))
        check(f"…and it is the SAME manifest — {len(post)} vs {len(pre)} objects, "
              f"{len(pre ^ post)} differing", pre == post)
    except (RuntimeError, FileNotFoundError) as e:
        print(f"  ✗ CANNOT RUN — {e}")
        return 1
    finally:
        drop()
        drop_scratch()

    print(f"\n{cases - failures}/{cases} self-test cases passed")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="regenerate and fail if the committed manifest differs")
    ap.add_argument("--self-test", action="store_true",
                    help="prove the post-phase path (r5 B3) against a scratch M4 database")
    a = ap.parse_args()

    if a.self_test:
        return self_test()

    try:
        manifest = derive()
    except (RuntimeError, FileNotFoundError) as e:
        print(f"CANNOT RUN — {e}\nTreat this as NOT RUN.", file=sys.stderr)
        return 2
    finally:
        drop_scratch()

    if a.check:
        committed = read_committed()
        if committed is None:
            print(f"FAILED — no manifest at {MANIFEST}. Run without --check to write it.",
                  file=sys.stderr)
            return 1
        # ⟳ r4 MEDIUM (codex) — --check compared OBJECT SETS, so a stale HEADER survived it. Proof:
        # the committed file read "12 indexs · 5 policys" (a pluralisation bug fixed in code and
        # never regenerated) while --check reported "manifest is current". Compare the RENDERED
        # FILE, so the whole artifact is the subject, not just the part that is easy to compare.
        on_disk = open(MANIFEST).read() if os.path.exists(MANIFEST) else ""
        if committed == manifest and on_disk != render(manifest):
            print("FAILED — the manifest's OBJECT SET is current, but the FILE differs from what\n"
                  "this generator would write now (header, counts or ordering are stale).\n"
                  "Regenerate: python3 scripts/gen-m4-manifest.py", file=sys.stderr)
            return 1
        if committed != manifest:
            missing, extra = manifest - committed, committed - manifest
            print("FAILED — the committed manifest is STALE. The schema now produces a different\n"
                  "object set, so the gate is asserting yesterday's shape.\n", file=sys.stderr)
            for label, s in (("+ now created, not in the manifest", missing),
                             ("- in the manifest, no longer created", extra)):
                if s:
                    print(f"  {label}:", file=sys.stderr)
                    for o in sorted(s):
                        print(f"      {o}", file=sys.stderr)
            print("\nRegenerate: python3 scripts/gen-m4-manifest.py", file=sys.stderr)
            return 1
        print(f"manifest is current — {len(manifest)} objects ({summarise(manifest)})")
        return 0

    os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)
    with open(MANIFEST, "w") as f:
        f.write(render(manifest))
    print(f"wrote {MANIFEST}\n  {len(manifest)} objects — {summarise(manifest)}")
    for kind, objs in by_kind(manifest).items():
        print(f"    {kind:6} {len(objs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
