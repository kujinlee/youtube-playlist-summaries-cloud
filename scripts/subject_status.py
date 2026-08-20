#!/usr/bin/env python3
"""Tell a ratchet's reader what its SUBJECT is, before it tells them the verdict.

WHY THIS EXISTS — measured 2026-08-19, in time spent rather than in defects.

Three schema ratchets (`check-guard-coverage`, `check-sentinel-meanings`,
`check-vocabulary-collisions`) read `docs/superpowers/specs/2026-08-03-stable-blob-addressing/
schema/` — an UNSHIPPED spec. Two of them exit 1. They have exited 1 since `1a7c076` on 2026-08-10,
the commit that implemented ADR-0007 and deleted the reservation protocol without updating the
classification tables that describe it. Nothing noticed: these need a live Postgres, so they are not
in CI, so they cannot fail a merge. PR #66 merged over its own gates.

That red state is CORRECT and worth keeping — the stale entries (`art_pending_has_token`,
`video_artifacts_inflight_uq`, `video_artifacts.reserved_at`, …) are the reservation protocol's
death certificate in executable form, and deleting them would destroy the record of what ADR-0007
removed. The defect is not the redness. **The defect is that the redness is AMBIGUOUS**: `exit 1`
looks identical whether you just broke something or you are meeting nine-day-old expected drift.
A fresh session pays a full re-derivation to tell those apart. This module makes the answer part of
the output.

EVERYTHING HERE IS DERIVED. Nothing records "parked" or a reconciliation date as a constant — this
project has deleted several such caches after watching them rot, and a banner asserting a stale fact
would be worse than no banner. Two questions, both answered from the tree as it is right now:

  1. IS THE SUBJECT SHIPPED?  Count runtime files mentioning its tables. Zero means the schema is
     design, not deployment — and the day someone ships it, this line changes by itself.
  2. HAS THE SUBJECT MOVED SINCE THIS SCRIPT DID?  `git log -1` on each. If the subject is newer,
     the findings below are drift the script has not been reconciled against, not news.

Usage (from a sibling script in scripts/):
    from subject_status import subject_banner
    for line in subject_banner(SCHEMA, Path(__file__), TABLES):
        print(line)

    python3 scripts/subject_status.py --self-test
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Where SHIPPED code lives. A table named only outside these is not deployed anywhere.
RUNTIME_DIRS = ("lib", "app", "components", "worker", "supabase/migrations")


def _git(*args: str) -> str | None:
    """One-line `git log` field, or None when git cannot answer.

    Deliberately NOT swallowed into a success value — the caller prints "unknown" rather than
    quietly omitting the line. A banner that vanishes when its input is missing is the fail-open
    shape this repo keeps measuring; an explicit "unknown" is not.
    """
    p = subprocess.run(["git", "-C", str(ROOT), "log", "-1", *args],
                       capture_output=True, text=True)
    if p.returncode != 0:
        return None
    out = p.stdout.strip()
    return out or None


def last_commit(path: Path) -> tuple[str, str] | None:
    """(short sha, committer date YYYY-MM-DD) of the newest commit touching `path`."""
    out = _git("--format=%h\t%cs", "--", str(path))
    if not out or "\t" not in out:
        return None
    sha, date = out.split("\t", 1)
    return sha.strip(), date.strip()


def subject_tables(subject: Path) -> tuple[str, ...]:
    """Tables the SUBJECT itself creates — derived from its `create table` statements.

    NOT the caller's scan list. `check-vocabulary-collisions` and `check-sentinel-meanings`
    deliberately scan `jobs`, `playlists`, `spend_ledger` and friends too, and those ARE shipped —
    so counting references to the scan list reported "SHIPPED — 100 runtime files" for a schema
    nothing deploys. Measured 2026-08-19, on the first run of this banner: the number was true and
    the sentence it supported was false, which is the failure this module exists to prevent.
    """
    names: list[str] = []
    for f in sorted(subject.glob("*.sql")):
        for m in re.finditer(r"create\s+table\s+(?:if\s+not\s+exists\s+)?(?:public\.)?(\w+)",
                             f.read_text(errors="ignore"), re.IGNORECASE):
            if m.group(1) not in names:
                names.append(m.group(1))
    return tuple(names)


def runtime_references(tables: tuple[str, ...]) -> int:
    """How many SHIPPED files mention any of these tables. Zero means unshipped."""
    if not tables:
        return -1                   # nothing to look for: the caller must say so, not assume zero
    seen: set[Path] = set()
    for d in RUNTIME_DIRS:
        base = ROOT / d
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if not p.is_file() or "node_modules" in p.parts or p in seen:
                continue
            if p.suffix not in {".ts", ".tsx", ".js", ".mjs", ".sql", ".py"}:
                continue
            try:
                text = p.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if any(t in text for t in tables):
                seen.add(p)
    return len(seen)


def subject_banner(subject: Path, script: Path) -> list[str]:
    """Lines to print BEFORE the verdict, describing what is being measured.

    ⚠ THIS DELIBERATELY REACHES NO VERDICT ON WHETHER THE SCRIPT IS RECONCILED, and the reason is
    a defect this function shipped with for about ten minutes. It first compared the subject's last
    commit date against the SCRIPT's and printed "reconciled" when the script was newer. That is
    false by construction: the script had been touched that same day to add a --self-test, which
    reconciled nothing. **A file's commit date is not evidence about its contents' meaning.**

    The findings below are already the reconciliation signal — a STALE or UNCLASSIFIED entry IS
    the drift. What a reader cannot get from those findings is WHEN the subject moved, so that is
    what this reports: an attribution, not a conclusion.
    """
    rel = subject.relative_to(ROOT) if subject.is_relative_to(ROOT) else subject
    lines = [f"subject: {rel}"]

    tables = subject_tables(subject)
    refs = runtime_references(tables)
    if not tables:
        lines.append("         ⚠ could not read any `create table` from the subject — shipped "
                     "status UNKNOWN. Treat this banner as NOT RUN.")
    elif refs == 0:
        lines.append(
            f"         UNSHIPPED — no file under {'/, '.join(RUNTIME_DIRS)}/ mentions any of "
            f"{', '.join(tables)}. This measures a DESIGN, not a deployment.")
    else:
        lines.append(f"         SHIPPED — {refs} runtime file(s) reference {', '.join(tables)}.")

    sub = last_commit(subject)
    if sub is None:
        lines.append("         ⚠ subject history UNKNOWN — git could not answer, so any finding "
                     "below is unattributed.")
    else:
        lines.append(f"         subject last moved at {sub[0]} ({sub[1]}). Any STALE or "
                     f"UNCLASSIFIED finding below dates from that change or earlier —")
        lines.append("         start there when reconciling. A finding is NOT necessarily new.")
    return lines


# ── --self-test ─────────────────────────────────────────────────────────────────────────────────

def self_test() -> int:
    cases: list[tuple[str, bool]] = []

    def case(name: str, ok: bool) -> None:
        cases.append((name, ok))

    schema = ROOT / "docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema"
    tracked = ROOT / "scripts/check-docs.py"
    missing = ROOT / "no-such-file-xyz.txt"

    case("last_commit answers for a tracked path", last_commit(tracked) is not None)
    case("last_commit returns (sha, YYYY-MM-DD)",
         (lambda c: c is not None and len(c[1]) == 10 and c[1][4] == "-")(last_commit(tracked)))
    case("last_commit on an untracked path returns None", last_commit(missing) is None)

    # ── the subject's OWN tables, derived from its create statements ─────────────────────────
    tabs = subject_tables(schema)
    case("subject_tables finds the tables the schema creates",
         "video_artifacts" in tabs and "video_generations" in tabs)
    case("subject_tables does NOT include tables the schema merely references",
         "spend_ledger" not in tabs and "jobs" not in tabs)
    case("subject_tables on a directory with no SQL is empty", subject_tables(ROOT / "scripts") == ())

    case("a table no file mentions counts zero", runtime_references(("zzz_not_a_table",)) == 0)
    case("a table the runtime DOES use counts more than zero",
         runtime_references(("spend_ledger",)) > 0)
    case("an EMPTY table list returns -1, never a misleading zero",
         runtime_references(()) == -1)

    b = subject_banner(schema, tracked)
    case("the banner names its subject", any("subject:" in x for x in b))
    # ⭐ the defect this banner shipped with for ten minutes: it counted references to the CALLER's
    # scan list (which includes shipped tables like `jobs`) and announced "SHIPPED — 100 files" for
    # a schema nothing deploys. The number was true; the sentence was false.
    case("the parked schema reports UNSHIPPED, not SHIPPED",
         any("UNSHIPPED" in x for x in b))
    case("the banner attributes the subject's last change",
         any("subject last moved at" in x for x in b))

    # ⭐ the second defect: it compared the subject's date against the SCRIPT's and printed
    # "reconciled" when the script was newer — false by construction, since the script had been
    # edited that day for an unrelated reason. The banner must reach NO such verdict.
    case("the banner never claims the script is reconciled",
         not any("reconciled —" in x for x in b))
    case("the banner warns a finding may not be new",
         any("NOT necessarily new" in x for x in b))

    b2 = subject_banner(ROOT / "supabase/migrations", tracked)
    case("a shipped subject reports SHIPPED, not UNSHIPPED",
         any("SHIPPED —" in x for x in b2) and not any("UNSHIPPED" in x for x in b2))

    # fail-open guards: an unanswerable question must SAY so, never go silent
    b3 = subject_banner(ROOT / "scripts", tracked)
    case("a subject with no create-table reports shipped status UNKNOWN",
         any("UNKNOWN" in x for x in b3))
    case("the banner is never empty", min(len(b), len(b2), len(b3)) >= 3)

    failed = [n for n, ok in cases if not ok]
    for name, ok in cases:
        print(f"  {'✓' if ok else '✗'} {name}")
    print(f"\n{len(cases) - len(failed)}/{len(cases)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(self_test() if "--self-test" in sys.argv else 0)
