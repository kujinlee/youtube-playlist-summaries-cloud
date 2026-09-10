#!/usr/bin/env python3
"""Does a backlog row still say OPEN about work that already merged? (backlog #98)

WHY THIS EXISTS
---------------
Row 88's status cell was 1422 characters reading "OPEN — filed 2026-09-03, not started" while
`gh pr view 224` said MERGED and `git log` carried the squash titled with the row's own subject,
verbatim. A session trusting the row would have rebuilt shipped work; the one that caught it was
saved by cross-checking `gh` on a hunch, not by any rule.

⭐ WHY NOTHING ALREADY CATCHES IT — this is the part worth understanding, not the symptom.
`check-docs.py` DOES enforce a consistency rule here, and it fires: "item #97 is CLOSED (its
Status cell has ✅) but still leads with 🟠". But that rule compares the SEVERITY MARKER to the
STATUS CELL, and both fields live INSIDE THE ROW. When a row is stale, the marker and the status
agree with each other perfectly and disagree only with GIT — so every internal check passes.

The existing gate is ONE-DIRECTIONAL: it sees closed-but-marked-open and is structurally blind
to shipped-but-recorded-open. Same shape as backlog #95 (the banner detector saw
banner-without-plan, was blind to plan-without-banner) and the same shape as "a green check over
the wrong subject": the check is real, runs, and passes, over a subject that cannot express the
failure. This script supplies the missing direction by comparing the row against something
OUTSIDE it.

FIVE MEASURED INSTANCES, none caught by a machine:
    #88, #97   2026-09-06, found while choosing the next item in a bundle
    #81, #99   2026-09-09, found while answering "what is the status of this bundle?"
    #82        2026-09-09, found by THIS RULE before this script existed — see below

⛔ IT WARNS. IT DOES NOT BLOCK, and that was settled by measurement rather than taste.
Backlog #56 already carries the verdict for this whole class of check — comparing the written
record against git: "Do NOT rebuild the reconciliation as a gate: it fires on every docs-only
commit and gets disabled." A blocking gate on a docs-only mismatch is the thing that gets
switched off, at which point the guard is worse than none because its presence implies coverage.

⚠ WARN-ONLY IS A REAL RISK HERE and the mitigation is stated rather than assumed: this runs in
CI, where the output IS the durable record. It needs no separate log (unlike the warn-only banner
detector, which observes a session nobody re-reads). If this ever moves to a context with no
retained output, it needs a log before it can be trusted.

THE DISCRIMINATOR, AND THE MEASUREMENT THAT CHOSE IT
----------------------------------------------------
⛔ THE OBVIOUS RULE IS WRONG, AND MEASURING IS THE ONLY WAY THAT SHOWS. Backlog #98 proposes
"extract the item ids their messages name". Measured over 1,497 commits on the default branch:

    ANY occurrence of `(backlog #N)`     18 ids matched, would fire on 10   ← 56% false
    `(backlog #N)` at the SUBJECT TAIL    7 ids matched, would fire on  1   ← the real one

The token means "this commit TOUCHED item N", not "this commit CLOSED item N". `(backlog #17)`
appears twice and #17 is a large open design item; `docs(backlog #53): …` is a FILING commit.
Firing on those is exactly what row #98 warns against in its own text — "a false positive here is
worse than the gap, because it would train the reader to skip the gate".

What separates them is WHERE the token sits. A closing squash puts it at the END of the subject,
optionally followed by GitHub's ` (#PR)`:

    "One renderer for four pages: the inline markup seam (backlog #71) (#180)"   CLOSES
    "docs(backlog #53): the commit-drift residue, filed with a trigger"          FILES

⚠ THIS IS A HEURISTIC OVER A CONVENTION, not a proof, and it fails in one known direction: a
close whose subject does NOT end with the token is invisible here. That is the honest residue —
the check is a floor on detection, never a ceiling. It is stated so nobody reads a clean run as
"every row is current".

⛔ EXTENDING THIS TO A HEAD-FORM SUBJECT WAS PROPOSED AND REJECTED — the user's decision, 2026-09-09.
It is recorded HERE because this docstring is where the next person will propose it again, and the
measurement that refuses it is two lines long.

The gap above was first hit in practice by row #91: PR #269's subject LEADS with "Backlog #91 —",
so this check returned rc=0 over a row that had been stale for two days (three ways over, in fact).
The obvious repair is to ALSO match an id at the START of a subject. Measured against master, that
fires on FILING commits, which is the same 56%-false direction the table above already priced:

    "File backlog #85 (three fence scanners) — and repair a landmine PR #206 shipped …"   FILES
    "File backlog #99 — a paused plan kept ticking, with the Stop guard disarmed"         FILES

Both lead with an id and close nothing. So the residue stays a residue ON PURPOSE: an honest floor
is worth more than a gate the reader learns to skip. Row #91 was corrected by hand in PR #278.

FIRST LIVE RUN FOUND A REAL ONE. Applied to master 2026-09-09 the rule fired on exactly one id,
#82, and it is a TRUE positive verified by hand: commit `3ec912f6` "The gate reads the store, not
a patch — so it can finally judge a reference (backlog #82) (#232)", PR #232 MERGED 2026-09-06
with +412 lines into `check-dashboard-entry.py`, whose `:1278` reads "the referential half needs
the STORE, not the patch (backlog #82)" — while row 82 still said "OPEN … this row is the
referential half only".

EXIT SEMANTICS, in all three directions
    0  ran, and either found nothing or WARNED (warn-only: findings do not fail the build)
    2  CANNOT RUN — and this is a FAILURE, never a quiet pass. Raised when the backlog is
       missing or unparseable, when git is absent or the clone is SHALLOW (a shallow clone sees
       fewer commits and would report a confident, smaller answer), or when the scan matched
       ZERO closing tokens, because a zero over an empty corpus is not a finding.

Usage:
    python3 scripts/check-backlog-closure.py
    python3 scripts/check-backlog-closure.py --self-test  # 20 cases
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKLOG = ROOT / "docs" / "backlog.md"

# ⚠ ANCHORED AT THE SUBJECT TAIL. `\(#\d+\)` is GitHub's squash suffix and is OPTIONAL because a
# direct commit has none. Chosen by measurement, not by taste — see the docstring's table.
CLOSING = re.compile(r"\(backlog #(\d+)\)(?:\s*\(#\d+\))?\s*$")

# ⚠ A ROW IS `| id | description | … | tag | status |`, and the DESCRIPTION carries the marker.
# Rows are NOT a fixed width: one holds a literal `|` inside backticks (a shell pipe) and parses
# to 7 cells where the normal row has 6; another has 9. Every field is therefore read by a
# NEGATIVE index or by index 0/1, never by a fixed positive index into the middle — measured
# 2026-09-09, when a `$6` read silently undercounted a tag population 5-for-6 with no error.
ROW = re.compile(r"^\| (\d+) ")
CLOSED_MARKER = "✅"


def closing_ids(subjects: list[str]) -> dict[str, str]:
    """Item ids whose CLOSING token sits at the tail of a commit subject -> that subject.

    Pure: takes subjects, touches no git. Keeping the RULE callable without the FETCH is why the
    self-test can run in CI without a repository — the recorded shape where three ratchets went
    eight days untestable because their entry point needed a live service.
    """
    found: dict[str, str] = {}
    for s in subjects:
        m = CLOSING.search(s.strip())
        if m:
            found.setdefault(m.group(1), s.strip())
    return found


def row_markers(text: str) -> dict[str, str]:
    """Item id -> the leading marker of its description cell (may be '' if the cell is bare)."""
    out: dict[str, str] = {}
    for line in text.split("\n"):
        m = ROW.match(line)
        if not m:
            continue
        cells = [c.strip() for c in line.split("|")][1:-1]
        if len(cells) < 2:
            continue  # too short to carry a description; not a data row
        out[m.group(1)] = cells[1][:1]
    return out


def findings(closes: dict[str, str], markers: dict[str, str]) -> tuple[list[str], list[str]]:
    """(stale, orphaned) — rows recorded open despite a close, and ids naming no row.

    An ORPHANED id is reported separately and never as staleness: a commit naming an id that no
    longer has a row is a different problem, and folding the two together would let one hide in
    the other's count.
    """
    stale, orphan = [], []
    for item in sorted(closes, key=int):
        if item not in markers:
            orphan.append(item)
        elif markers[item] != CLOSED_MARKER:
            stale.append(item)
    return stale, orphan


def _git(*args: str) -> tuple[int, str]:
    try:
        p = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        # ⚠ NOT a fail-open handler: it converts an unavailable instrument into CANNOT RUN,
        # which the caller turns into exit 2. It never returns a success verdict.
        return 127, str(exc)
    return p.returncode, p.stdout


def cannot_run(reason: str) -> int:
    print(f"CANNOT RUN — {reason} Treat this as NOT CHECKED.", file=sys.stderr)
    return 2


def main() -> int:
    if not BACKLOG.exists():
        return cannot_run(f"{BACKLOG.relative_to(ROOT)} does not exist.")
    markers = row_markers(BACKLOG.read_text(encoding="utf-8"))
    if not markers:
        return cannot_run("the backlog parsed to ZERO rows, so nothing could be compared.")

    rc, shallow = _git("rev-parse", "--is-shallow-repository")
    if rc != 0:
        return cannot_run("git could not be run, so no commit could be read.")
    if shallow.strip() == "true":
        return cannot_run(
            "this is a SHALLOW clone. It would see fewer commits and report a smaller, "
            "confident answer. Re-run with full history (CI uses fetch-depth: 0)."
        )

    rc, out = _git("log", "--format=%s", "HEAD")
    if rc != 0:
        return cannot_run("`git log` failed, so no commit subject could be read.")
    subjects = [s for s in out.split("\n") if s.strip()]
    closes = closing_ids(subjects)
    if not closes:
        return cannot_run(
            f"scanned {len(subjects)} commit subject(s) and matched ZERO `(backlog #N)` closing "
            "tokens. Either the history is not this repo's, or the convention has lapsed — "
            "a zero over an empty corpus is not a clean result."
        )

    stale, orphan = findings(closes, markers)
    print(f"backlog closure: {len(subjects)} subject(s) scanned, "
          f"{len(closes)} closing token(s), {len(markers)} row(s) read")
    for item in orphan:
        print(f"  ? #{item}: a commit closes it, but no row with that id exists")
        print(f"      {closes[item]}")
    for item in stale:
        print(f"  ⚠ #{item}: MERGED but its row does not carry {CLOSED_MARKER}")
        print(f"      {closes[item]}")
    if stale or orphan:
        # ⛔ WARN-ONLY BY DESIGN (backlog #56's measured verdict). Exit 0 with findings printed.
        print(f"\nWARN — {len(stale)} row(s) may be stale, {len(orphan)} orphaned id(s). "
              "Not a failure: this is hygiene, and a blocking gate on a docs-only mismatch is "
              "the thing backlog #56 measured getting switched off.")
    else:
        print("ok — every id closed by a commit carries a closed marker on its row")
    return 0


# ─── self-test ────────────────────────────────────────────────────────────────────────────────
def _self_test() -> int:
    ok = fail = 0

    def case(name: str, got, want) -> None:
        nonlocal ok, fail
        if got == want:
            ok += 1
        else:
            fail += 1
            print(f"[FAIL] {name}: got {got!r}, want {want!r}")

    # ── the discriminator: what counts as a CLOSING token ──────────────────────────────────
    case("subject tail matches", closing_ids(["Some seam (backlog #71)"]), {"71": "Some seam (backlog #71)"})
    case("squash suffix still matches",
         list(closing_ids(["A thing (backlog #97) (#230)"])), ["97"])
    case("trailing whitespace tolerated", list(closing_ids(["A thing (backlog #12)   "])), ["12"])
    # ⚠ THE FALSE-POSITIVE GUARD. Measured: firing on ANY occurrence gave 10 false fires of 18.
    case("a FILING prefix does NOT match", closing_ids(["docs(backlog #53): the residue, filed"]), {})
    case("mid-subject mention does NOT match",
         closing_ids(["fix (backlog #17) then more words"]), {})
    case("a body-only mention does NOT match (subjects only reach here)",
         closing_ids(["unrelated subject"]), {})
    case("no token at all", closing_ids(["chore: tidy"]), {})
    case("first subject wins for a repeated id",
         closing_ids(["newer (backlog #5)", "older (backlog #5)"])["5"], "newer (backlog #5)")
    case("two ids both collected", sorted(closing_ids(["a (backlog #1)", "b (backlog #2)"])), ["1", "2"])

    # ── reading the row marker, across the shapes this file actually has ───────────────────
    NORMAL = "| 71 | ✅ (was 🟠) **Done thing** | files | M | (tag) | ✅ CLOSED |"
    OPENR = "| 82 | 🟡 **Open thing** | files | S | (tag) | **OPEN — filed** |"
    WIDE = "| 103 | 🟠 **Has a `a \\| b` pipe** | files | S–M | (tag) | **OPEN** |"
    case("closed marker read", row_markers(NORMAL), {"71": "✅"})
    case("open marker read", row_markers(OPENR), {"82": "🟡"})
    # ⚠ THE ROW-WIDTH CASE. A literal `|` inside backticks makes this row parse WIDER; the marker
    # must still be read, because a positive index into the middle silently reads another column.
    case("a WIDER row still yields its marker", row_markers(WIDE), {"103": "🟠"})
    case("non-row lines ignored", row_markers("# heading\ntext\n"), {})
    # ⚠ CATCHES rather than dies. The guard this case defends exists to prevent an IndexError,
    # so a mutation removing it makes `row_markers` RAISE — which kills the whole suite and leaves
    # the harness unable to attribute the death to any case ("matched 0 red cases", measured
    # 2026-09-09). Converting the raise into a comparable value is what makes this case the named
    # observer of its own defect instead of a casualty of it.
    def _short_row():
        try:
            return row_markers("| 9 |")
        except Exception as exc:  # noqa: BLE001 - the raise IS the observation, not a swallow
            return f"raised {type(exc).__name__}"

    case("a too-short row is skipped, not crashed", _short_row(), {})

    # ── the verdict ────────────────────────────────────────────────────────────────────────
    case("closed row is quiet", findings({"71": "s"}, {"71": "✅"}), ([], []))
    case("open row is flagged stale", findings({"82": "s"}, {"82": "🟡"}), (["82"], []))
    case("missing row is ORPHANED, not stale", findings({"99": "s"}, {"71": "✅"}), ([], ["99"]))
    case("stale ids come back in numeric order",
         findings({"9": "s", "10": "s"}, {"9": "🟡", "10": "🟡"})[0], ["9", "10"])

    # ⭐ BACKLOG #98's OWN FALSIFIER, quoted from the row: "restore row 88's stale wording and the
    # check must FAIL naming #88 specifically; against the corrected wording it must pass."
    STALE_88 = "| 88 | 🟡 **A /brief page outlives its session** | f | S | (tag) | **OPEN — not started** |"
    FIXED_88 = "| 88 | ✅ (was 🟡) **A /brief page outlives its session** | f | S | (tag) | ✅ FIXED — PR #224 |"
    CLOSE_88 = {"88": "A /brief page can be answered tomorrow (backlog #88) (#224)"}
    case("FALSIFIER: stale row 88 fires, naming #88",
         findings(CLOSE_88, row_markers(STALE_88)), (["88"], []))
    case("FALSIFIER: corrected row 88 is quiet",
         findings(CLOSE_88, row_markers(FIXED_88)), ([], []))

    print(f"\n{ok}/{ok + fail} passed")
    return 1 if fail else 0


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(_self_test())
    sys.exit(main())
