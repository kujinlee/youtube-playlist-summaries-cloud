"""The Python side of `scripts/m4-base-db.sh` — one import for every gate that rebuilds M4.

    from m4_base_db import subject_database

    with subject_database() as db:          # `db` is a database name; M4 is guaranteed ABSENT
        run_psql(db, spec_sql)              # ... so a rebuild-from-source cannot collide

WHY THIS IS A MODULE AND NOT THREE COPIES OF SIX LINES
------------------------------------------------------
Three ratchets need identical logic — `check-guard-coverage.py`, `check-sentinel-meanings.py` and
`check-vocabulary-collisions.py` — and this repo has already measured what happens when the same
rule is hand-copied to several sites: `docs/plugins.md` records a fix applied to the one place
someone noticed while a sibling kept the defect, and `check-vocabulary-collisions.py` exists
precisely because duplicate vocabulary is the observable shadow of a duplicate mechanism.

WHAT IT SOLVES (measured 2026-08-26)
------------------------------------
With 0027 applied to the local `postgres`, every gate that rebuilds M4 from source onto it — seven
of the fourteen — died on `relation "workspaces" already exists`. See `m4-base-db.sh`'s header for
the full account. These three did it inside a rolled-back transaction on `postgres` itself, which
was cheap and correct right up until `postgres` grew the very objects they create.

⚠ THE CONTEXT MANAGER ALWAYS DROPS THE DATABASE, INCLUDING ON AN EXCEPTION. A leaked base is 21 MB
  (it clones WITH data, deliberately — see the shell script), and a harness that litters throwaway
  databases across the shared local cluster is task #145's failure, one layer out.

⚠ WHEN 0027 IS *NOT* APPLIED, NO DATABASE IS BUILT AND `postgres` IS YIELDED UNCHANGED. That keeps
  the pre-promotion path exactly as fast as it was, and it means the cost of this fix is paid only
  in the phase that needs it. It is NOT a silent fallback: `postgres` genuinely is a valid pre-M4
  base then, which is the same condition the shell script checks before running the rollback.
"""
from __future__ import annotations

import contextlib
import os
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
CONTAINER = os.environ.get("PGCONTAINER", "supabase_db_youtube-playlist-summaries-cloud")
HELPER = REPO / "scripts" / "m4-base-db.sh"
LIVE_GATE = REPO / "scripts" / "check-live-schema.py"


class CannotRun(RuntimeError):
    """Raised when no pre-M4 subject can be produced. Callers must exit 2, never treat as a pass."""


def _m4_is_applied(db: str) -> bool:
    """True only on exit 0. `check-live-schema.py` exits 2 when it cannot reach the database, and
    reading that as 'not applied' is right here: the caller's rebuild then fails on its own terms
    rather than being silently redirected to a base that was never built."""
    p = subprocess.run(["python3", str(LIVE_GATE), "--database", db, "--expect-present"],
                       capture_output=True, text=True, stdin=subprocess.DEVNULL)
    return p.returncode == 0


def _drop(db: str) -> None:
    subprocess.run(["docker", "exec", "-i", CONTAINER, "psql", "-U", "postgres", "-d", "postgres",
                    "-tAq", "-c", f"drop database if exists {db} (force);"],
                   capture_output=True, text=True, stdin=subprocess.DEVNULL)


@contextlib.contextmanager
def subject_database(source: str = "postgres"):
    """Yield the name of a database with M4 ABSENT, building one only if `source` carries M4.

    `M4_DB` short-circuits everything: a caller that has already built a base (as
    `mutate-schema.py` does, once, for 58 mutations) passes it down rather than paying the ~7 s
    clone again. Nothing is dropped in that case — the owner owns the lifecycle.
    """
    preset = os.environ.get("M4_DB")
    if preset:
        yield preset
        return
    if not _m4_is_applied(source):
        yield source
        return
    if not HELPER.exists():
        raise CannotRun(f"0027 is applied to '{source}' and {HELPER} is missing.")
    db = f"m4_subject_{os.getpid()}"
    p = subprocess.run([str(HELPER), db], capture_output=True, text=True,
                       stdin=subprocess.DEVNULL)
    if p.returncode != 0:
        _drop(db)
        raise CannotRun(f"could not build a pre-M4 base database.\n{p.stdout}{p.stderr}")
    try:
        yield db
    finally:
        _drop(db)


def read_catalog(sql: str, marker: str, source: str = "postgres") -> str:
    """Run `sql` against a guaranteed-pre-M4 database and return everything after `marker`.

    The three coherence ratchets each carried a byte-identical copy of this — build the SQL, shell
    out to psql on `postgres`, print "could not read the catalog" and exit 2. All three broke the
    same day for the same reason, which is the argument for there being one of it.

    ⛔ EXIT 2, NOT 1, AND NEVER 0. A ratchet that cannot reach its subject has not passed; it has
    not run. The message says so out loud because "could not read the catalog" scrolling past in a
    fourteen-gate suite is how five dead gates went unnoticed for a day.
    """
    try:
        with subject_database(source) as db:
            p = subprocess.run(
                ["docker", "exec", "-i", CONTAINER, "psql", "-U", "postgres", "-d", db,
                 "-tAq", "-v", "ON_ERROR_STOP=1"],
                input=sql, capture_output=True, text=True)
            if p.returncode != 0:
                print(f"CANNOT RUN — could not read the catalog from '{db}'. TREAT THIS AS NOT RUN.")
                print(p.stdout[-1500:] or p.stderr[-1500:])
                raise SystemExit(2)
            return p.stdout.split(marker, 1)[-1]
    except CannotRun as e:
        print(f"CANNOT RUN — {e} TREAT THIS AS NOT RUN.")
        raise SystemExit(2)
