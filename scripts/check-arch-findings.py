#!/usr/bin/env python3
"""Measure the acceptance criteria for the 2026-07-30 architecture review findings.

WHY THIS IS A SCRIPT AND NOT A CHECKLIST
----------------------------------------
Finding #2 of that review is literally "a correct module exists and nobody calls it."
So "did we build the fix?" is a worthless criterion here — the fix for #2 was already
built (`lib/storage/supabase/consistency.ts:writeArtifact`) and the finding is that it
changed nothing. Every metric below therefore measures ADOPTION at the call sites, not
the existence of a module.

RATCHET SEMANTICS
-----------------
Each metric carries a `baseline` (measured 2026-07-30) and a `target`.

  * current == target            -> PASS   (the finding is resolved on this axis)
  * target < current <= baseline -> OPEN   (not fixed yet; not getting worse)
  * current worse than baseline  -> REGRESSED -> exit 1

The REGRESSED case is the point of running this in CI. Finding #1 is "11 route files
fork on STORAGE_BACKEND"; nothing today stops that becoming 15. The ratchet does.

Usage:
    python3 scripts/check-arch-findings.py            # report, exit 1 only on regression
    python3 scripts/check-arch-findings.py --strict   # exit 1 unless every metric PASSes
    python3 scripts/check-arch-findings.py --json     # machine-readable

Full criteria, including the ones no script can judge:
    docs/reviews/architecture-findings-acceptance.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

CODE_SUFFIXES = {".ts", ".tsx"}


def _walk(rel_dirs: list[str], suffixes: set[str] = CODE_SUFFIXES) -> list[Path]:
    out: list[Path] = []
    for rel in rel_dirs:
        base = ROOT / rel
        if not base.exists():
            continue
        if base.is_file():
            out.append(base)
            continue
        for p in base.rglob("*"):
            if p.is_file() and p.suffix in suffixes and "node_modules" not in p.parts:
                out.append(p)
    return sorted(out)


def files_containing(rel_dirs: list[str], pattern: str, exclude: list[str] | None = None) -> list[str]:
    """Files whose text matches `pattern` (regex). Returns repo-relative paths."""
    rx = re.compile(pattern)
    excl = exclude or []
    hits = []
    for p in _walk(rel_dirs):
        rel = str(p.relative_to(ROOT))
        if any(e in rel for e in excl):
            continue
        try:
            if rx.search(p.read_text(encoding="utf-8", errors="ignore")):
                hits.append(rel)
        except OSError:
            continue
    return hits


def match_count(
    rel_dirs: list[str],
    pattern: str,
    exclude: list[str] | None = None,
    skip_comments: bool = True,
) -> list[str]:
    """One entry per MATCH (not per file), formatted 'path:line'.

    `skip_comments` drops `//` and `*` lines. This is not cosmetic: the FIRST run of this
    script reported #2/2a as REGRESSED because `sync-run.ts:329` is a *comment explaining*
    that promote() is create-if-absent — i.e. the one place that already fixed the bug got
    counted as a site still exhibiting it.
    """
    rx = re.compile(pattern)
    excl = exclude or []
    hits = []
    for p in _walk(rel_dirs):
        rel = str(p.relative_to(ROOT))
        if any(e in rel for e in excl):
            continue
        try:
            for i, line in enumerate(p.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                if skip_comments:
                    stripped = line.lstrip()
                    if stripped.startswith("//") or stripped.startswith("*") or stripped.startswith("/*"):
                        continue
                if rx.search(line):
                    hits.append(f"{rel}:{i}")
        except OSError:
            continue
    return hits


def glob_files(pattern: str) -> list[str]:
    return sorted(str(p.relative_to(ROOT)) for p in ROOT.glob(pattern) if p.is_file())


@dataclass
class Metric:
    finding: str
    metric_id: str
    what: str
    baseline: int
    target: int
    probe: Callable[[], list[str]]     # returns the evidence list; len() is the measurement
    lower_is_better: bool = True
    evidence: list[str] = field(default_factory=list)
    current: int = -1

    def run(self) -> str:
        self.evidence = list(self.probe())
        cur = len(self.evidence)
        self.current = cur
        if cur == self.target:
            return "PASS"
        if self.lower_is_better:
            if cur > self.baseline:
                return "REGRESSED"
            return "OPEN"
        else:
            if cur < self.baseline:
                return "REGRESSED"
            return "OPEN"


APP_LIB = ["app", "lib"]

METRICS: list[Metric] = [
    # ---------------------------------------------------------------- #1
    # Baseline is 12, not the review's 11: the review counted *route* files; app/page.tsx
    # forks on STORAGE_BACKEND too and is equally part of the finding. Widened rather than
    # narrowed — a criterion that excludes a real fork site would pass while the bug remains.
    Metric(
        "#1", "1a",
        "files under app/ that read STORAGE_BACKEND directly (11 routes + page.tsx)",
        baseline=12, target=0,
        probe=lambda: files_containing(["app"], r"STORAGE_BACKEND"),
    ),
    Metric(
        "#1", "1b",
        "UUID_RE definitions (should be one shared validator)",
        baseline=11, target=1,
        probe=lambda: match_count(APP_LIB, r"const\s+UUID_RE\b"),
    ),
    Metric(
        "#1", "1c",
        "files forking on serveLocal/serveCloud",
        baseline=8, target=0,
        probe=lambda: files_containing(["app"], r"serveLocal|serveCloud"),
    ),
    # ---------------------------------------------------------------- #2
    Metric(
        "#2", "2a",
        "promote() call sites OUTSIDE lib/storage (protocol must have one owner)",
        baseline=3, target=0,
        probe=lambda: match_count(
            ["app", "lib"], r"\.promote\(", exclude=["lib/storage/"]
        ),
    ),
    Metric(
        "#2", "2b",
        "PRODUCTION callers of writeArtifact (adoption, not existence)",
        baseline=0, target=3,
        lower_is_better=False,
        probe=lambda: match_count(
            ["app", "lib"], r"\bwriteArtifact\s*\(", exclude=["lib/storage/supabase/consistency.ts"]
        ),
    ),
    Metric(
        "#2", "2c",
        "distinct staged-write verification strategies in production writers",
        baseline=3, target=1,
        # The three strategies the review named, keyed on each one's distinct failure message:
        #   summary-handler.ts  -> exists(tempKey)
        #   write-dig-section-blob.ts -> exists(tempKey), different wording
        #   sync-run.ts         -> get(tempKey) + mdHash compare
        probe=lambda: sorted(set(
            m.split(":")[0] for m in match_count(
                ["app", "lib"],
                r"staged upload not verified|staged dig upload not verified|staged MD verify failed",
                exclude=["lib/storage/supabase/consistency.ts"],
            )
        )),
    ),
    # ---------------------------------------------------------------- #3 (done — regression guard)
    Metric(
        "#3", "3a",
        "InMemoryBlobStore adapter present (regression guard — PR #38)",
        baseline=1, target=1, lower_is_better=False,
        probe=lambda: glob_files("lib/storage/testing/in-memory-blob-store.ts"),
    ),
    Metric(
        "#3", "3b",
        "InMemoryBlobStore test file present (regression guard)",
        baseline=1, target=1, lower_is_better=False,
        probe=lambda: glob_files("tests/lib/storage/in-memory-blob-store.test.ts"),
    ),
    # ---------------------------------------------------------------- #4
    Metric(
        "#4", "4a",
        "sites computing the release predicate inline (should call one function)",
        baseline=2, target=0,
        probe=lambda: match_count(
            ["app", "lib"], r"releaseGateOpen\(\)\s*$|releaseGateOpen\(\)\s*&&",
            exclude=["lib/gemini-failure.ts"],
        ),
    ),
    Metric(
        "#4", "4b",
        "JobQueue.fail boolean flags (type must not permit invalid combinations)",
        baseline=3, target=0,
        probe=lambda: match_count(
            ["lib"], r"(retryable|billableSucceeded|metered)\s*:\s*boolean",
        ),
    ),
    # ---------------------------------------------------------------- #5
    Metric(
        "#5", "5a",
        "esc() definitions in lib/html-doc (should be one, exported)",
        baseline=2, target=1,
        probe=lambda: match_count(["lib/html-doc"], r"function\s+esc\s*\("),
    ),
    Metric(
        "#5", "5b",
        "esc() is EXPORTED (an unexported escaper cannot be unit-tested)",
        baseline=0, target=1, lower_is_better=False,
        probe=lambda: match_count(["lib/html-doc"], r"export\s+function\s+esc\s*\("),
    ),
    Metric(
        "#5", "5c",
        "dedicated test file for the HTML escaper",
        baseline=0, target=1, lower_is_better=False,
        probe=lambda: glob_files("tests/**/*esc*.test.ts") + glob_files("tests/**/*escape*.test.ts"),
    ),
    # ---------------------------------------------------------------- #6
    Metric(
        "#6", "6a",
        "self-written DRIFT WARNINGs in nav.ts",
        baseline=2, target=0,
        # skip_comments=False is REQUIRED here — a DRIFT WARNING *is* a comment. The first
        # version of this probe read 0 and looked PASS while both warnings were still there.
        probe=lambda: match_count(["lib/html-doc/nav.ts"], r"DRIFT WARNING", skip_comments=False),
    ),
    Metric(
        "#6", "6b",
        "unit test that executes the SHIPPED nav string (not a TS mirror)",
        baseline=0, target=1, lower_is_better=False,
        probe=lambda: glob_files("tests/**/*nav-shipped*.test.ts")
        + glob_files("tests/**/*nav-script*.test.ts"),
    ),
    # ---------------------------------------------------------------- #7
    Metric(
        "#7", "7a",
        "raw fetch() calls in LocalApp (CloudApp has 0)",
        baseline=10, target=0,
        probe=lambda: match_count(["components/local/LocalApp.tsx"], r"\bfetch\("),
    ),
    Metric(
        "#7", "7b",
        "raw EventSource use in LocalApp",
        baseline=2, target=0,
        probe=lambda: match_count(["components/local/LocalApp.tsx"], r"EventSource"),
    ),
    Metric(
        "#7", "7c",
        "dedicated LocalApp test files (CloudApp has 2)",
        baseline=0, target=2, lower_is_better=False,
        probe=lambda: glob_files("tests/components/*local-app*.test.tsx")
        + glob_files("tests/components/*LocalApp*.test.tsx"),
    ),
]

SYMBOL = {"PASS": "PASS", "OPEN": "OPEN", "REGRESSED": "REGRESSED"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--strict", action="store_true", help="exit 1 unless every metric PASSes")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--evidence", action="store_true", help="list the matched files/lines")
    args = ap.parse_args()

    results = []
    for m in METRICS:
        status = m.run()
        results.append((m, status))
    npass = sum(1 for _, s in results if s == "PASS")

    if args.json:
        print(json.dumps([
            {
                "finding": m.finding, "metric": m.metric_id, "what": m.what,
                "baseline": m.baseline, "target": m.target,
                "current": m.current, "status": s,
                "evidence": m.evidence,
            }
            for m, s in results
        ], indent=2))
    else:
        print("Architecture-review findings — acceptance criteria (2026-07-30 baseline)")
        print("Criteria doc: docs/reviews/architecture-findings-acceptance.md")
        print()
        print(f"{'#':<5}{'id':<5}{'base':>5}{'now':>5}{'goal':>6}  {'status':<11}what")
        print("-" * 100)
        last = None
        for m, s in results:
            if last is not None and m.finding != last:
                print()
            last = m.finding
            print(f"{m.finding:<5}{m.metric_id:<5}{m.baseline:>5}{m.current:>5}{m.target:>6}  "
                  f"{SYMBOL[s]:<11}{m.what}")
            if args.evidence and m.evidence:
                for e in m.evidence:
                    print(f"{'':>27}   - {e}")
        print()
        nreg = sum(1 for _, s in results if s == "REGRESSED")
        print(f"{npass}/{len(results)} criteria met; {nreg} regressed past baseline")

    regressed = [m for m, s in results if s == "REGRESSED"]
    if regressed:
        print("\nREGRESSED past the 2026-07-30 baseline — these got worse, not better:", file=sys.stderr)
        for m in regressed:
            print(f"  {m.finding}/{m.metric_id}: {m.what} "
                  f"(baseline {m.baseline}, now {m.current})", file=sys.stderr)
        return 1
    if args.strict and npass != len(results):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
