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

⛔ IT REFUSES TO RUN AGAINST A BASELINE THAT ALREADY HAS M4.
The manifest is a DIFF. If `0027` is already applied to the baseline database, `after EXCEPT before`
is empty or partial, and the generator would happily write a manifest asserting almost nothing —
a gate that passes over any database at all. That is the failure mode this whole finding is about,
so it fails closed instead.

FAILS IF
--------
the baseline already contains M4; Docker or the spec is unreachable (exit 2); or, with `--check`,
the committed manifest differs from what the schema now produces (exit 1).
"""
from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m4_catalog import CONTAINER, read_catalog, summarise, by_kind  # noqa: E402

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(REPO, "docs", "superpowers", "specs", "m4", "live-manifest.txt")
SCRATCH = "m4_manifest_gen"

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
    return subprocess.run(
        ["docker", "exec", "-i", CONTAINER, "psql", "-U", "postgres", "-d", db, "-tAq"],
        input=sql, capture_output=True, text=True)


def drop_scratch() -> None:
    psql("postgres", f"drop database if exists {SCRATCH} (force);")


def derive() -> set[str]:
    """Build the manifest by executing the schema. Raises RuntimeError with a reason."""
    try:
        before = read_catalog("postgres")
    except (RuntimeError, FileNotFoundError) as e:
        raise RuntimeError(f"could not read the baseline catalog: {e}") from e

    # fail closed: a baseline that already has M4 yields a manifest asserting nothing
    if any(o in before for o in ("table:workspaces", "table:video_generations")):
        raise RuntimeError(
            "the baseline database ALREADY HAS M4 applied, so `after EXCEPT before` would be empty\n"
            "or partial and this would write a manifest that passes over any database.\n"
            "Run the rollback first: supabase/rollback/rollback_0027_stable_blob_addressing.sql")

    drop_scratch()
    if psql("postgres", f"create database {SCRATCH};").returncode != 0:
        raise RuntimeError("could not create the scratch database")

    clone = subprocess.run(
        ["docker", "exec", "-i", CONTAINER, "sh", "-c",
         f"pg_dump -U postgres -d postgres --schema-only --no-owner --no-privileges "
         f"| psql -U postgres -d {SCRATCH} -q"],
        capture_output=True, text=True)
    if clone.returncode != 0:
        raise RuntimeError(f"could not clone the baseline schema: {clone.stderr.strip()[:200]}")

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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true",
                    help="regenerate and fail if the committed manifest differs")
    a = ap.parse_args()

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
