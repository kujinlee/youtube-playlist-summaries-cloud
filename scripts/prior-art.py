#!/usr/bin/env python3
"""Search every project document for identifiers before designing against them.

NOT a ratchet — a research tool. It exists because of a measured failure:

  The model blob was originally keyed by `id` (2026-07-02 stage-1c design). The address drifted
  to `base`. A reviewer CAUGHT the drift and filed it Minor, under a "Carry-forward" heading, in
  task-1f-a-6-materialize-helper.md:19 — where nothing carried it. Three months later backlog #36
  spent thirteen review rounds and a design review rediscovering the same fact, on a paid artifact.

  All three references were on disk the whole time. Nobody searched.

Why a script rather than "remember to grep":
  * `grep` is ugrep on this machine and silently returns nothing (measured, cost a wrong conclusion);
  * 600+ review files means an ad-hoc search returns hundreds of lines and gets abandoned;
  * ranking by document CLASS is what makes the output readable — a decision in a spec or ADR
    outranks the same word appearing in a test transcript.

Usage:
    python3 scripts/prior-art.py MODEL_KEY videoId          # any number of identifiers
    python3 scripts/prior-art.py --decisions sourceMd       # narrow: decision/deferral vocabulary only
    python3 scripts/prior-art.py --self-test

⚠ SHOWING EVERY HIT IS THE DEFAULT, ON PURPOSE. The first version of this script defaulted to
decision-vocabulary lines only, and `prior-art.py MODEL_KEY` then printed "No hits" — while
`--all` surfaced Phase-6 finding #2, the stage-1c design and the m3.1 review. A research tool whose
default answer is a FALSE NEGATIVE is worse than no tool, because "I searched and found nothing"
is the exact belief it exists to prevent. Narrowing is opt-in.
"""
from __future__ import annotations

import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Ordered by how load-bearing a statement in that document is. A decision recorded in an ADR or a
# spec outranks the same string in a review transcript, which outranks a plan.
CLASSES: list[tuple[str, str, int]] = [
    ("docs/adr", "ADR — a decision, binding until superseded", 0),
    ("docs/superpowers/specs", "SPEC — a design, possibly parked", 1),
    ("docs", "PROCESS/ROADMAP/BACKLOG", 2),
    ("docs/reviews", "REVIEW — findings, carry-forwards, deferrals", 3),
    ("docs/superpowers/plans", "PLAN", 4),
]

# Lines matching these are where a decision or a deferral lives — surfaced first within a file.
SIGNAL = re.compile(
    r"decision|decided|DECIDED|carry.?forward|deferred|defer\b|parked|PARKED|supersede|"
    r"instead of|must ensure|follow.?up|out of scope|not doing|declined|rejected",
    re.I,
)


def classify(path: str) -> tuple[int, str]:
    rel = os.path.relpath(path, ROOT)
    best = (99, "OTHER")
    for prefix, label, rank in CLASSES:
        if rel.startswith(prefix) and rank < best[0]:
            best = (rank, label)
    # docs/reviews is under docs/, so the more specific prefix must win
    if rel.startswith("docs/reviews"):
        best = (3, "REVIEW — findings, carry-forwards, deferrals")
    if rel.startswith("docs/superpowers/specs"):
        best = (1, "SPEC — a design, possibly parked")
    if rel.startswith("docs/superpowers/plans"):
        best = (4, "PLAN")
    return best


def search(terms: list[str], show_all: bool) -> dict:
    pat = re.compile("|".join(re.escape(t) for t in terms))
    by_class: dict[tuple[int, str], list[tuple[str, int, str, bool]]] = {}
    files_scanned = 0
    for base, dirs, files in os.walk(os.path.join(ROOT, "docs")):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for f in sorted(files):
            if not f.endswith(".md"):
                continue
            path = os.path.join(base, f)
            files_scanned += 1
            try:
                text = open(path, encoding="utf8", errors="replace").read()
            except OSError:
                continue
            for i, line in enumerate(text.split("\n"), 1):
                if not pat.search(line):
                    continue
                signal = bool(SIGNAL.search(line))
                if not signal and not show_all:
                    continue
                key = classify(path)
                by_class.setdefault(key, []).append(
                    (os.path.relpath(path, ROOT), i, line.strip()[:180], signal)
                )
    return {"hits": by_class, "files_scanned": files_scanned}


def report(terms: list[str], show_all: bool) -> int:
    res = search(terms, show_all)
    print(f"prior-art: {' '.join(terms)}   ({res['files_scanned']} documents scanned)")
    if res["files_scanned"] == 0:
        print("\n  NO DOCUMENTS SCANNED -> TREAT THIS AS NOT RUN, not as 'no prior art'.")
        return 2
    total = sum(len(v) for v in res["hits"].values())
    if total == 0:
        mode = "all lines" if show_all else "decision/deferral lines only (--decisions)"
        print(f"\n  No hits ({mode}).")
        if not show_all:
            print("  ⚠ You narrowed the search. Re-run WITHOUT --decisions before concluding anything.")
        return 0
    for key in sorted(res["hits"]):
        _, label = key
        rows = res["hits"][key]
        print(f"\n=== {label}  ({len(rows)} lines) ===")
        last = None
        for rel, ln, line, signal in rows[:40]:
            if rel != last:
                print(f"\n  {rel}")
                last = rel
            print(f"    {'*' if signal else ' '} {ln}: {line}")
        if len(rows) > 40:
            print(f"    … {len(rows) - 40} more (narrow the terms)")
    print("\n  '*' = the line also matches decision/deferral vocabulary.")
    print("  Cite what you found in the spec's prior-art section, including 'searched X, found nothing'.")
    return 0


def self_test() -> int:
    """The regression this tool exists for: it must find all three #36 references."""
    cases = [
        (["MODEL_KEY", "videoId"], "docs/superpowers/specs/2026-07-02-stage-1c-supabase-adapters-design.md"),
        (["base", "videoId"], "docs/reviews/task-1f-a-6-materialize-helper.md"),
        (["videoId"], "docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md"),
    ]
    failures = 0
    for terms, expect in cases:
        res = search(terms, show_all=True)
        found = any(rel == expect for rows in res["hits"].values() for rel, *_ in rows)
        print(f"  {'ok  ' if found else 'FAIL'} {' '.join(terms):<24} -> {expect}")
        failures += 0 if found else 1
    # a term that cannot exist must return nothing — otherwise the matcher is vacuous
    res = search(["zzzz-no-such-identifier-zzzz"], show_all=True)
    empty = sum(len(v) for v in res["hits"].values()) == 0
    print(f"  {'ok  ' if empty else 'FAIL'} nonsense term returns no hits (matcher is not vacuous)")
    failures += 0 if empty else 1
    print(f"\n  {'PASS' if failures == 0 else f'{failures} FAILURE(S)'}")
    return 1 if failures else 0


def main() -> int:
    args = [a for a in sys.argv[1:]]
    if "--self-test" in args:
        return self_test()
    show_all = "--decisions" not in args
    terms = [a for a in args if not a.startswith("--")]
    if not terms:
        print(__doc__)
        return 1
    return report(terms, show_all)


if __name__ == "__main__":
    sys.exit(main())
