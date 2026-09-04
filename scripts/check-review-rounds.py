#!/usr/bin/env python3
"""A review round has TWO halves, or a written reason why it does not — a RATCHET on silent gaps.

    python3 scripts/check-review-rounds.py             # audit docs/reviews/
    python3 scripts/check-review-rounds.py --self-test # 27 cases

WHY THIS EXISTS
---------------
`docs/plugins.md` requires both halves of every review — `codex:rescue` AND
`superpowers:requesting-code-review` — and the memory `dual-review-halves-are-not-redundant`
records what skipping one costs: Codex-only rounds 2-4 cleared a live money guard that the skipped
Claude half caught in one pass.

Nothing enforced it. On 2026-08-24 the M4 plan went through two rounds with only the Codex half,
and the gap was visible **only** as a paragraph in a commit message — which is the "prose instead of
a script" shape `docs/dev-process.md` warns about. The absence of a reviewer looks exactly like the
presence of a clean one.

⚠ **IT MUST NOT BLOCK WHEN A REVIEWER GENUINELY CANNOT RUN** (user decision, 2026-08-25). Codex hits
usage limits, auth failures and HTTP 400s routinely, and `docs/plugins.md` already answers that case:
*"do not wait, pause the phase, or burn time retrying — immediately run a rigorous Claude adversarial
review in Codex's place … and note the Codex gap in the review doc."* That documented fallback
already produces both things this check wants — a real review, and a recorded reason. So the check
fires on **silence**, never on unavailability.

WHAT IT ASSERTS
---------------
For each (subject, round) it can parse:

  * two distinct reviewer halves            -> pass
  * one half + a GAP LINE in any of its files -> pass  (this is the Codex-down path)
  * one half, no gap line                   -> FAIL, unless the round is in KNOWN below

The gap line is deliberately `REVIEW GAP:` rather than "unavailable" — because the M4 case was not
unavailability, it was **not invoked**, and a marker that only admits one of those would have
tempted a false reason. The check forces a reason to be STATED; judging it is a human's job.

    REVIEW GAP: claude — not invoked; the missing half ran as r3

⚠ COVERAGE IS REPORTED, NOT IMPLIED. Review filenames use four different shapes; only two carry a
round number. The audit prints how many files it could not parse, because an instrument whose
success line claims more than its input covers is this project's most-repeated defect — see
ADR-0007's note on `check-vocabulary-collisions.py`, whose green line covered a schema it could
not see.

⚠ IT IS A RATCHET, and `check-ratchet-contract.py` discovers ratchets two ways: a CI step, or the
word "ratchet" in this docstring. The first draft said neither, so the contract check could not see
it — an instrument invisible to the instrument that audits instruments. Both are now true.

FAILS IF
--------
a (subject, round) outside KNOWN has one reviewer half and no gap line; or `docs/reviews/` is
missing (exit 2 — treat as NOT RUN).
"""
from __future__ import annotations

import collections
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
REVIEWS = ROOT / "docs" / "reviews"

# Two naming shapes are in use. Measured 2026-08-25 across 718 files: 108 are `-r<N>-<who>`, 60 are
# `-<who>-r<N>`, 192 name a reviewer with no round, and 358 match neither. Supporting one shape
# would have covered 15% of the directory while printing a green line about all of it.
SHAPES = (
    re.compile(r"^(?P<subject>.+)-r(?P<round>\d+)-(?P<who>codex|claude|coordinator)\.md$"),
    re.compile(r"^(?P<subject>.+)-(?P<who>codex|claude|coordinator)-r(?P<round>\d+)\.md$"),
)

# A coordinator file ADJUDICATES the two halves; it is not itself a half. Counting it would let a
# round pass with one reviewer and its own summary — the shape this check exists to catch.
HALVES = ("codex", "claude")

# Emphasis may wrap the marker on EITHER side — `**REVIEW GAP:** codex — …` is the natural way to
# write it in a review doc, and the first version only tolerated it on the left. Caught by the
# self-test, which is why the case uses the bolded form rather than the bare one.
GAP = re.compile(
    r"^[*_>#\s-]*REVIEW GAP:[*_\s]*(codex|claude)\b[*_\s]*[—–-][*_\s]*(\S.*?)[*_\s]*$",
    re.M | re.I)

# Rounds that predate the check. A NAME list, not a count: swapping one violation for another must
# not pass, and a stale entry announces itself the moment its files are renamed or completed.
# Measured 2026-08-25 — 20 of 86 parseable rounds, which is the finding, not the exception:
# `plan-serve-bounding` ran EIGHT single-reviewer rounds. This was never a one-off.
#
# ⟳ The first version of this list had 12 entries, built from a terminal display truncated at
# `[:12]`, and the check caught the other 8 on its first real run. Same instrument failure as the
# `ls | head -20` that caused the anchor work (ADR-0010) two days ago — a list read off a truncated
# view is a claim about the view, not about the set.
KNOWN: set[tuple[str, int]] = {
    ("b4-share-tolerate-skew", 1),
    ("backlog-37-sidebar-refresh", 2), ("backlog-37-sidebar-refresh", 3),
    ("backlog-37-sidebar-refresh", 4),
    ("m3-1-cloud-e2e", 2), ("m3-1-cloud-e2e", 3),
    ("plan-serve-bounding", 1), ("plan-serve-bounding", 2), ("plan-serve-bounding", 3),
    ("plan-serve-bounding", 4), ("plan-serve-bounding", 5), ("plan-serve-bounding", 6),
    ("plan-serve-bounding", 7), ("plan-serve-bounding", 8),
    ("spec-proven-absence", 1),
    ("spec-serve-deadline", 1), ("spec-serve-deadline", 2), ("spec-serve-deadline", 3),
}


def parse(name: str) -> tuple[str, int, str] | None:
    """(subject, round, who) or None. PURE."""
    for shape in SHAPES:
        if m := shape.match(name):
            return m.group("subject"), int(m.group("round")), m.group("who")
    return None


def has_gap_line(text: str) -> str | None:
    """The stated reason a half is missing, or None. PURE."""
    m = GAP.search(text)
    return f"{m.group(1)}: {m.group(2).strip()}" if m else None


# ── backlog #68 (d): THIS IS THE CONSUMER THAT IS NOT THE CALLER ───────────────────────────────
# `scripts/codex-review.py` now writes a verdict per run into `docs/reviews/verdicts/`, because its
# exit code has a single consumer and no memory: measured 2026-08-28, a caller wrapped the run as
# `… ; echo "WRAPPER_RC=$?"` and reported the ECHO's status, so `WRAPPER_RC=1` sat unread while the
# round was treated as reviewed.
#
# ⚠ WRITING THE VERDICT DOWN FIXES NOTHING BY ITSELF. A file the caller ignores is an exit code the
# caller ignores with extra steps. The mechanism is that THIS check reads it, in CI, where the
# caller cannot intervene. What it catches is the exact round-3 shape: the gate did not run, and an
# artifact bearing its name was filed anyway.
#
# ⚠ STATED LIMIT, NOT PAPERED OVER: this reads COMMITTED verdicts, so someone who deletes one
# before committing evades it entirely. That is deliberate scope, not an oversight. The failure
# being fixed was an ACCIDENT — a `$?` that read the wrong command's status — and an accident
# cannot delete a file. A determined caller can still defeat this; a distracted one cannot, and
# every occurrence so far has been the distracted kind. Claiming more would be the "green check
# over the wrong subject" this project keeps measuring.
VERDICT_DIRNAME = "verdicts"


def verdict_problems(records: "list[tuple[str, dict]]", review_names: "set[str]") -> list[str]:
    """One problem per verdict that contradicts what is on disk. PURE.

    `gate_ran` is READ, never re-derived from `exit_code`. Deriving it here would be a second
    implementation of the wrapper's rule, and the two would drift — this project has measured that.
    """
    out = []
    for src, rec in records:
        if rec.get("gate_ran"):
            continue
        review = rec.get("review") or "(unnamed)"
        if review in review_names:
            out.append(
                f"{src}: the Codex gate did NOT run ({rec.get('reason', 'no reason recorded')}), "
                f"yet `{review}` is filed in docs/reviews/. A failed gate must not leave an "
                f"artifact that reads as a completed one — delete it, or if it is a Claude "
                f"review, name it as one and record a `REVIEW GAP:` line")
    return out


def read_verdicts(directory: pathlib.Path) -> "tuple[list[tuple[str, dict]], list[str]]":
    """(records, unreadable). A malformed verdict is a CANNOT-RUN, never a silent skip.

    An absent directory is fine and returns nothing: verdicts only exist from the moment the
    wrapper started writing them, and back-filling history would be inventing testimony.
    """
    records, bad = [], []
    if not directory.is_dir():
        return records, bad
    for p in sorted(directory.glob("*.json")):
        try:
            rec = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            bad.append(f"{p.name}: unreadable ({exc})")
            continue
        if not isinstance(rec, dict) or "gate_ran" not in rec:
            bad.append(f"{p.name}: no `gate_ran` field — cannot tell whether the gate ran")
            continue
        records.append((p.name, rec))
    return records, bad


# ── WHERE A REVIEW HALF MAY LIVE — two layouts, and the reason is backlog #92, not taste ──────
# `scripts/codex-review.py` watches the TOP LEVEL of docs/reviews/ NON-RECURSIVELY so it can catch
# an agent that guesses its way into the artifact root; that is the round-3 failure and the
# detector is worth keeping. But the documented dual-review workflow also wrote BOTH halves there,
# so every run whose halves overlapped accused the agent falsely — recorded in four review docs —
# and on the failure path the wrapper MOVED a concurrent half out of the tree entirely (measured
# 2026-09-04). Halves now land in a per-writer SUBDIRECTORY, which the non-recursive snapshot
# cannot see. That makes the two mechanisms consistent instead of contradictory: nothing legitimate
# is written to the top level DURING a run, so anything appearing there really is an intrusion.
# The ~700 historical files stay flat and are still audited — this reads both layouts.
HALF_DIRS = ("codex", "claude", "coordinator")


def review_files(reviews: pathlib.Path) -> tuple[list[pathlib.Path], list[str]]:
    """Every review half on disk: the flat layout AND one level of per-writer subdirectories.

    ONE level, and `verdicts/` is excluded because it holds JSON testimony, not reviews.

    Returns `(paths, problems)`. A basename appearing in TWO places is a problem, never a silent
    pick: `rounds[key][who] = p` would keep whichever it saw last, so a duplicate would shrink
    coverage while the round still looked complete — a collision that overwrites cannot be found
    by counting what survived it.
    """
    flat = sorted(reviews.glob("*.md"))
    nested: list[pathlib.Path] = []
    for d in sorted(p for p in reviews.iterdir() if p.is_dir()):
        if d.name == VERDICT_DIRNAME:
            continue
        nested.extend(sorted(d.glob("*.md")))

    seen: dict[str, pathlib.Path] = {}
    problems: list[str] = []
    for p in flat + nested:
        if p.name in seen:
            problems.append(
                f"{p.name}: filed in BOTH `{seen[p.name].parent.name}/` and `{p.parent.name}/` — "
                f"two files cannot be the same review half, and pairing would keep only one"
            )
            continue
        seen[p.name] = p
    return list(seen.values()), problems


def audit(reviews: pathlib.Path, known: set[tuple[str, int]] = KNOWN) -> tuple[list[str], dict]:
    """(problems, stats). Reads `reviews`; the parsing above is pure."""
    rounds: dict[tuple[str, int], dict[str, pathlib.Path]] = collections.defaultdict(dict)
    unparsed = 0
    paths, path_problems = review_files(reviews)
    for p in paths:
        got = parse(p.name)
        if got is None:
            unparsed += 1
            continue
        subject, rnd, who = got
        rounds[(subject, rnd)][who] = p

    problems, exempt_used = list(path_problems), set()
    for key, files in sorted(rounds.items()):
        present = [w for w in HALVES if w in files]
        if len(present) >= 2:
            continue
        if any(has_gap_line(p.read_text(errors="replace")) for p in files.values()):
            continue
        if key in known:
            exempt_used.add(key)
            continue
        missing = [w for w in HALVES if w not in files] or ["both"]
        problems.append(
            f"{key[0]} round {key[1]}: only {'+'.join(present) or 'nothing'} — "
            f"{'/'.join(missing)} neither ran nor recorded a `REVIEW GAP:` line"
        )

    for stale in sorted(known - exempt_used):
        problems.append(
            f"KNOWN entry `{stale[0]}` round {stale[1]} is no longer a violation — remove it, "
            f"or the exemption outlives what it excused"
        )

    # The verdict half. `review_names` is what is ACTUALLY on disk, so the contradiction the
    # check reports is between two observations, never between an observation and an assumption.
    vrecs, vbad = read_verdicts(reviews / VERDICT_DIRNAME)
    # Both layouts, or a verdict naming a half filed in `claude/` would read as testimony about a
    # review that does not exist — the check contradicting itself over a file it can plainly see.
    review_names = {p.name for p in paths}
    problems.extend(verdict_problems(vrecs, review_names))

    return problems, {"rounds": len(rounds), "unparsed": unparsed, "exempt": len(exempt_used),
                      "verdicts": len(vrecs), "verdicts_bad": vbad}


# ---------------------------------------------------------------- self-test
def self_test() -> int:
    import tempfile
    cases = failures = 0

    def check(label: str, got: bool, want: bool) -> None:
        nonlocal cases, failures
        cases += 1
        ok = got == want
        print(("  ✓ " if ok else "  ✗ ") + label)
        failures += 0 if ok else 1

    check("shape A parsed", parse("plan-x-r2-codex.md") == ("plan-x", 2, "codex"), True)
    check("shape B parsed", parse("plan-x-claude-r2.md") == ("plan-x", 2, "claude"), True)
    check("no round number -> unparsed", parse("plan-x-codex.md") is None, True)
    check("unrelated file -> unparsed", parse("retrospective.md") is None, True)
    check("gap line found", has_gap_line("**REVIEW GAP:** codex — usage limit") is not None, True)
    check("gap line needs a reason", has_gap_line("REVIEW GAP: codex —") is None, True)
    check("prose mentioning a gap is not a gap line",
          has_gap_line("there was a review gap: codex was slow") is None, True)

    with tempfile.TemporaryDirectory() as td:
        def tree(files: dict[str, str]) -> pathlib.Path:
            d = pathlib.Path(td) / f"t{len(list(pathlib.Path(td).iterdir()))}"
            d.mkdir()
            for n, body in files.items():
                # A key may carry ONE subdirectory (`claude/p-r1-claude.md`), so the cases can
                # build the per-writer layout backlog #92 introduced, not only the flat one.
                (d / n).parent.mkdir(parents=True, exist_ok=True)
                (d / n).write_text(body)
            return d

        d = tree({"p-r1-codex.md": "x", "p-r1-claude.md": "y"})
        check("both halves pass", audit(d, set())[0] == [], True)

        d = tree({"p-r1-codex.md": "x"})
        check("solo half FAILS", len(audit(d, set())[0]) == 1, True)

        d = tree({"p-r1-codex.md": "REVIEW GAP: claude — not invoked; ran as r3"})
        check("solo half + gap line passes (the Codex-down path)", audit(d, set())[0] == [], True)

        d = tree({"p-r1-codex.md": "x"})
        check("KNOWN exempts it", audit(d, {("p", 1)})[0] == [], True)

        d = tree({"p-r1-codex.md": "x", "p-r1-claude.md": "y"})
        check("a KNOWN entry that is no longer violating is reported",
              len(audit(d, {("p", 1)})[0]) == 1, True)

        d = tree({"p-r1-codex.md": "x", "p-r1-coordinator.md": "adjudication"})
        check("coordinator is NOT a second half", len(audit(d, set())[0]) == 1, True)

        d = tree({"p-r1-codex.md": "x", "p-r1-claude.md": "y", "notes.md": "z"})
        check("unparsed files are counted, not judged", audit(d, set())[1]["unparsed"] == 1, True)

        # ── backlog #92: the per-writer layout ──
        # THE POINT OF THE WHOLE CHANGE. If this case fails, halves have become invisible to CI
        # and every round reads as half-missing — the loud failure, but still worth naming.
        d = tree({"codex/p-r1-codex.md": "x", "claude/p-r1-claude.md": "y"})
        check("halves in per-writer subdirectories pair normally", audit(d, set())[0] == [], True)

        # MIXED, because the migration is not atomic: ~700 files stay flat while new halves nest.
        d = tree({"p-r1-codex.md": "x", "claude/p-r1-claude.md": "y"})
        check("a nested half pairs with a flat one", audit(d, set())[0] == [], True)

        # A subdirectory must not RESCUE a solo half — the gate still wants two writers.
        d = tree({"claude/p-r1-claude.md": "y"})
        check("a solo half in a subdirectory still FAILS", len(audit(d, set())[0]) == 1, True)

        # ⛔ THE COLLISION, asserted rather than assumed. `rounds[key][who] = p` keeps the LAST
        # write, so without this the duplicate would vanish and the round would look complete.
        d = tree({"p-r1-claude.md": "y", "claude/p-r1-claude.md": "y2", "p-r1-codex.md": "x"})
        probs = audit(d, set())[0]
        check("the same half filed in two places is REPORTED, not silently deduped",
              any("filed in BOTH" in s for s in probs), True)

        # `verdicts/` holds JSON testimony; a stray .md there is not a review half. Without the
        # exclusion it would parse as one and invent a round.
        d = tree({"p-r1-codex.md": "x", "p-r1-claude.md": "y", "verdicts/q-r9-claude.md": "z"})
        check("verdicts/ is not scanned for review halves", audit(d, set())[0] == [], True)

    # ── backlog #68 (d): the verdict half ──
    # THE ROUND-3 SHAPE, as a case: the gate did not run and an artifact bearing its name is filed.
    # That is what actually happened — four models each overwrote a committed review while the
    # wrapper wrote nothing — and no check could see it, because the only signal was an exit code
    # the caller had already discarded.
    _filed = {"plan-x-r3-codex.md"}
    _did_not_run = ("plan-x-r3-codex.verdict.json",
                    {"gate_ran": False, "review": "plan-x-r3-codex.md", "reason": "no candidate"})
    _ran = ("plan-x-r3-codex.verdict.json",
            {"gate_ran": True, "review": "plan-x-r3-codex.md", "reason": "ok"})
    check("a failed gate with its artifact filed anyway is caught",
          len(verdict_problems([_did_not_run], _filed)) == 1, True)
    check("…and the message names the review",
          "plan-x-r3-codex.md" in verdict_problems([_did_not_run], _filed)[0], True)
    check("a failed gate that left NO artifact is not a contradiction",
          verdict_problems([_did_not_run], set()) == [], True)
    check("a gate that RAN is never a problem", verdict_problems([_ran], _filed) == [], True)
    # gate_ran is READ, not re-derived. A verdict claiming the gate ran while exiting 1 is
    # self-inconsistent, but it is the WRAPPER's job to be consistent; re-deriving here would be a
    # second implementation of that rule, and the two copies would drift.
    check("exit_code is not consulted",
          verdict_problems([("v.json", {"gate_ran": True, "exit_code": 1,
                                        "review": "plan-x-r3-codex.md"})], _filed) == [], True)

    with tempfile.TemporaryDirectory() as td:
        vd = pathlib.Path(td) / "verdicts"
        vd.mkdir()
        (vd / "good.json").write_text('{"gate_ran": true, "review": "a.md"}')
        (vd / "broken.json").write_text("{not json")
        (vd / "nofield.json").write_text('{"review": "b.md"}')
        recs, bad = read_verdicts(vd)
        check("a readable verdict is collected", len(recs) == 1, True)
        # A verdict that cannot be parsed must be a CANNOT RUN, never a silent skip: "unreadable"
        # and "the gate ran" are indistinguishable to a check that drops it.
        check("malformed and field-less verdicts are reported, not skipped", len(bad) == 2, True)
        check("an absent verdict directory is not an error",
              read_verdicts(pathlib.Path(td) / "nope") == ([], []), True)

    print(f"\n{cases - failures}/{cases} self-test cases passed")
    return 1 if failures else 0


def main() -> int:
    if "--self-test" in sys.argv:
        return self_test()

    if not REVIEWS.is_dir():
        print(f"CANNOT RUN — no review directory at {REVIEWS}. Treat this as NOT RUN.",
              file=sys.stderr)
        return 2

    problems, stats = audit(REVIEWS)
    if problems:
        print(f"FAILED — {len(problems)} review round(s) with one half and no stated reason:\n")
        for p in problems:
            print(f"  ✗ {p}")
        print("\nEither run the missing half, or record why it could not run:")
        print("    REVIEW GAP: codex — usage limit; Claude ran in its place per docs/plugins.md")
        return 1

    if stats["verdicts_bad"]:
        print("CANNOT RUN — a codex-review verdict could not be read, so whether that gate ran is "
              "UNKNOWN. Treat these as NOT CHECKED:\n", file=sys.stderr)
        for b in stats["verdicts_bad"]:
            print(f"  ? {b}", file=sys.stderr)
        return 2

    print(f"review rounds: {stats['rounds']} parsed, {stats['exempt']} pre-existing exemptions, "
          f"0 silent gaps; {stats['verdicts']} codex-review verdict(s) read, none contradicted")
    print(f"  ⚠ {stats['unparsed']} files in docs/reviews/ carry no round number and are NOT "
          f"covered by this check")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
