#!/usr/bin/env python3
"""Every living spec and plan says whether it is alive — and the goals page renders it.

    python3 scripts/check-goal-status.py              # enforce for the armed anchors
    python3 scripts/check-goal-status.py --self-test  # 34 cases

WHY THIS EXISTS, AND IT IS A DEFECT THE OWNER FOUND BY READING THE PAGE
----------------------------------------------------------------------
2026-10-21, on `/goals.html`: *"I cannot know status of each items (current|finished|obsolete
etc)"*. Seven threads under `review-decides-itself`, several with a design and no implementation,
and nothing on any card said which were finished, which were abandoned, and which were waiting on
a human. The page rendered spec/plan PRESENCE and PR counts, and presence is not status.

⛔⛔ STATUS CANNOT BE DERIVED, AND THAT IS MEASURED, NOT ASSUMED. The obvious implementation is to
count a plan's ticked tasks. Measured over those same seven threads, a derived status is wrong on
SEVEN OF SEVEN:

    thread                               ticks   derived        truth
    review-decision-procedure            0/36    NOT STARTED    SHIPPED — live in CI, PR #303
    development-velocity-RECONSTRUCTED   0/12    NOT STARTED    ABANDONED — tombstoned deliverable
    decision-log-model-redesign          0/9     NOT STARTED    DEFERRED, and partly shipped
    rounds-to-convergence-is-rising      no plan  UNPLANNED     awaiting the human gate
    memory-recall-survey                 no plan  UNPLANNED     unjudged survey
    memory-recall-S1-worksheet           no plan  UNPLANNED     companion instrument, unjudged
    decision-card-soundness              no plan  UNPLANNED     PARKED behind backlog #117

Two independent reasons, and the second is the one that settles it. (1) Plans here are executed
without ticking boxes — `review-decision-procedure` shipped a 1,225-line guard with 0 of 36 ticked.
(2) ⭐ NO MECHANICAL SIGNAL CAN SEPARATE *ABANDONED* FROM *NOT YET STARTED*, or *PARKED* from
*AWAITING A DECISION*: those differ by human intent, which is not observable in the tree. So the
status is DECLARED, and this guard is what stops a declaration from being optional.

⚠ A `**Status:**` LINE ALREADY EXISTED ON 92 OF 198 DOCUMENTS AND COULD NOT BE READ. Measured the
same day: 46% coverage, and of those 92 the leading token was unparseable on 64. The values in use
were `CONVERGED`, `HIGH`, `APPROVED`, `DRAFT`, `BOTH`, `GATED` — six vocabularies, no taxonomy. So
this grammar is additive and narrow: it reads a MARKER, and prose may follow it freely.

THE VOCABULARY IS REUSED, NOT INVENTED (the owner's choice, 2026-10-21)
----------------------------------------------------------------------
Every marker below already carries this meaning somewhere in the repository, which is the point:
`check-vocabulary-collisions.py` exists because duplicate coordination vocabulary is the shadow of
a duplicate mechanism, and a seventh taxonomy for "is this alive" would have been exactly that.

    ✅ shipped    the work is done and in the tree         (backlog.md's closed rows)
    🟠 current    alive, and the next move is the agent's  (backlog.md's open rows)
    🟠 needs-you  alive, and a DECISION waits on the human (dashboard-entries.md's [needs-you])
    ⏸️ parked     stopped on purpose, named blocker        (backlog.md's deferred rows)
    ⛔ obsolete   this THREAD is dead; its question may not be

⭐ `needs-you` EARNS ITS PLACE AND IS NOT A SYNONYM FOR `current`. Measured at the moment the
vocabulary was chosen: 3 of the 7 threads were waiting on the human, and under a four-word
vocabulary all three render as `current` — indistinguishable from work in progress. That is the
most actionable fact on the page, so a vocabulary that cannot express it fails the question that
prompted the feature.

⚠ WHAT THIS GUARD DOES NOT DO, STATED RATHER THAN HIDDEN. It cannot tell whether a declaration is
TRUE. A document may say `✅ shipped` over work that never shipped, and nothing here would object —
the same structural limit `check-decision-scheme.py` records about its own authored rows. What it
buys is that the claim EXISTS and is in one vocabulary, so a reader is told something rather than
left to infer from presence. The falsifier for truthfulness is a human reading the card against the
tree, which is what found the defect in the first place.

ITS SCOPE IS ARMED PER ANCHOR, DELIBERATELY
-------------------------------------------
`ARMED_ANCHORS` holds the anchors where a missing status FAILS. Everywhere else it WARNS and the
run still exits 0. Reason: 106 of 198 documents carry no status line at all, and a gate that is red
from birth across half its corpus gets switched off — that is backlog #56, measured. So an anchor
joins the armed set when its threads have been audited and declared, which makes widening a
deliberate act with a visible diff rather than a 106-file backfill nobody reviews.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SUBDIRS = ("superpowers/specs", "superpowers/plans")

# The anchors where a missing declaration FAILS. See the docstring: widening is deliberate.
# ⟳ 2026-10-22: ALL THIRTEEN ARMED, the day after the first. The owner read the page and
# asked why 39 of 49 cards said "no status declared" — the answer was that arming bounded
# it to one anchor. Every thread under every anchor now declares a state, each carrying the
# evidence for its claim (a merged PR, and what is in the tree), so arming the rest costs
# nothing and makes the page answer the question it exists to answer. ⚠ A NEW anchor is
# still not armed automatically: it joins this tuple when its threads have been audited,
# which keeps widening a deliberate act with a visible diff.
ARMED_ANCHORS = (
    "cloud-blob-key-encoding",
    "cloud-publishing",
    "cloud-sync",
    "corrections-in-cloud",
    "explanation-on-demand",
    "feature-map",
    "prod-smoke",
    "review-decides-itself",
    "serve-money-guard",
    "serve-path-bounding",
    "share-and-download",
    "stable-blob-addressing",
    "status-visibility",
)

# marker -> state. ORDER IS THE READING ORDER on the page's legend, cheapest claim first.
# ⚠ `⏸️` is the EMOJI PRESENTATION SEQUENCE (U+23F8 U+FE0F). A document written with the bare
# U+23F8 must parse too — they are indistinguishable to a reader and the variation selector is
# invisible in an editor, so refusing one would be a trap rather than a rule.
STATES = {
    "✅": "shipped",
    "🟠": "current",
    "⏸": "parked",
    "⛔": "obsolete",
}
# `needs-you` shares 🟠 with `current` because both are ALIVE; the word is what distinguishes them,
# and the word is required when the marker is 🟠.
ALIVE_WORDS = ("current", "needs-you")

STATUS_LINE = re.compile(r"^\*\*Status:\*\*\s*(.+)$", re.M)
ANCHOR_LINE = re.compile(r"\*\*Anchor:\*\*\s*`([^`]+)`")
HEAD_LINES = 18


def _norm(marker: str) -> str:
    """PURE. A marker with its variation selector stripped, so ⏸️ and ⏸ are one marker."""
    return marker.replace("️", "")


def parse_status(text: str) -> tuple[str | None, str | None]:
    """PURE. (state, None) for a well-formed declaration, else (None, why-not).

    ⛔ THIS FUNCTION IS THE GRAMMAR AND IS IMPORTED BY `gen-goals-page.py` RATHER THAN RESTATED
    THERE. A second copy of a parser is this repository's most-measured defect (17 recorded
    instances, `check-vocabulary-collisions.py`), and the page and the guard disagreeing about what
    a status IS would mean the gate passes documents the page cannot render — which is the exact
    shape of the `NO-REVIEW:` heading defect from earlier the same day, where a declaration was
    valid to a human and invisible to its parser.

    ⚠ ONLY THE FIRST `HEAD_LINES` ARE SEARCHED, for the same reason `check-anchors.py` bounds its
    own window: a status that can hide anywhere in a 900-line design document is one a reader does
    not find, and the point of this feature is a reader finding it.

    A missing line is (None, None) — ABSENT, not malformed. The caller decides whether absence is a
    failure, because that depends on whether the anchor is armed; a parser that also judged would
    be a parser whose refusal nobody can read.
    """
    head = "\n".join(text.splitlines()[:HEAD_LINES])
    m = STATUS_LINE.search(head)
    if not m:
        return None, None
    rest = m.group(1).strip()
    if not rest:
        return None, "`**Status:**` is empty — declare one of " + ", ".join(
            f"{k} {v}" for k, v in STATES.items())
    marker = _norm(rest[0])
    if marker not in STATES:
        return None, (f"`**Status:**` starts with {rest[0]!r}, which is not a status marker. "
                      f"Use one of: " + ", ".join(f"{k} {v}" for k, v in STATES.items()))
    state = STATES[marker]
    if marker == "🟠":
        # ⭐ THE WORD IS LOAD-BEARING HERE AND NOWHERE ELSE. `current` and `needs-you` share a
        # marker because both are alive; collapsing them loses the one state the page exists to
        # surface, so when the marker is ambiguous the word is required.
        words = _norm(rest[1:]).strip().lower()
        hit = next((w for w in ALIVE_WORDS if words.startswith(w)), None)
        if hit is None:
            return None, (f"🟠 is ambiguous on its own — follow it with {' or '.join(ALIVE_WORDS)}"
                          f" ('needs-you' when a DECISION waits on the human)")
        state = hit
    return state, None


def living_documents(repo: Path | None = None) -> list[dict]:
    """Every spec and plan, with its anchor and parsed status. RAISES on an unreadable tree.

    A document that cannot be read is CANNOT RUN, never an absent status — silence there is
    indistinguishable from a clean result, which this repository treats as a failure.
    """
    root = (repo or REPO) / "docs"
    out = []
    for sub in SUBDIRS:
        d = root / sub
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.md")):
            try:
                text = f.read_text(errors="replace")
            except OSError as exc:
                raise ValueError(f"{f} could not be read: {exc}") from exc
            head = "\n".join(text.splitlines()[:HEAD_LINES])
            am = ANCHOR_LINE.search(head)
            state, why = parse_status(text)
            out.append({"rel": f"docs/{sub}/{f.name}", "name": f.name,
                        "anchor": am.group(1) if am else None,
                        "state": state, "why": why})
    return out


def verdict(docs: list[dict], armed: tuple[str, ...]) -> tuple[int, list[str]]:
    """PURE. (rc, lines). rc=1 only for an ARMED anchor's document that is missing or malformed.

    ⛔⛔ CORRECTED ON THIS GUARD'S FIRST LIVE RUN, AND THE FIRST VERSION WAS HOSTILE. It read
    *"a malformed declaration fails even outside an armed anchor"*, on the reasoning that arming
    bounds who must DECLARE but does not license an unparseable declaration. Measured immediately:
    **78 documents failed**, and not one was broken. They carry a DIFFERENT FIELD under the same
    name — the design's review state, in months of legitimate prose:

        **Status:** Approved
        **Status:** Draft v3 — hardened after two Codex passes
        **Status:** v7 — CONVERGED across seven dual adversarial rounds

    Those are not malformed versions of this vocabulary; they are a different question answered in
    the same slot. Refusing them would have made this guard red from birth across 40% of its
    corpus — ⚠ which is BACKLOG #56, the exact failure the per-anchor arming exists to avoid, and
    the docstring above claimed to avoid while this function undid it one screen below.

    So: outside an armed anchor a non-marker `**Status:**` is NOT DECLARED IN THIS VOCABULARY, and
    that is fine, because the anchor is not armed. Inside one, it is a defect — there the document
    IS claiming to speak this vocabulary, and a reader will be shown whatever it says.
    """
    missing, broken, counts = [], [], {}
    for d in docs:
        armed_here = d["anchor"] in armed
        if d["why"] and armed_here:
            broken.append(f"  ✗ {d['rel']}: {d['why']}")
        elif d["state"] is None:
            if armed_here:
                missing.append(f"  ✗ {d['rel']}: no `**Status:**` line in the first {HEAD_LINES}"
                               f" lines, or one that is not in this vocabulary, and "
                               f"`{d['anchor']}` is armed")
        else:
            counts[d["state"]] = counts.get(d["state"], 0) + 1
    lines = []
    declared = sum(counts.values())
    if broken or missing:
        lines.append(f"FAILED — {len(broken) + len(missing)} document(s) cannot tell a reader "
                     f"whether they are alive:")
        lines += broken + missing
        lines.append("")
        lines.append("Add ONE line under the Anchor/Goal block, e.g.:")
        lines.append("    **Status:** 🟠 needs-you — four options, awaiting the human gate")
        return 1, lines
    unarmed_blank = sum(1 for d in docs
                        if d["state"] is None and d["anchor"] not in armed and d["anchor"])
    lines.append(f"goal status OK — {declared} of {len(docs)} document(s) declare a state "
                 f"({', '.join(f'{v} {k}' for k, v in sorted(counts.items()))})")
    lines.append(f"  armed anchors: {', '.join(armed)}")
    if unarmed_blank:
        lines.append(f"  ⚠ {unarmed_blank} document(s) under UNARMED anchors declare nothing — "
                     f"their goal pages cannot show a status. Arm an anchor once its threads are "
                     f"audited (see the docstring).")
    return 0, lines


def main(argv: list[str], *, repo: Path | None = None,
         armed: tuple[str, ...] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Every living spec and plan says whether it is alive.")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        return _self_test()
    try:
        docs = living_documents(repo)
    except ValueError as exc:
        print(f"CANNOT RUN — {exc}")
        return 2
    if not docs:
        print("CANNOT RUN — no spec or plan documents were found, so nothing was checked.")
        return 2
    rc, lines = verdict(docs, ARMED_ANCHORS if armed is None else armed)
    print("\n".join(lines))
    return rc


def _self_test() -> int:
    """The suite, inside `fixture_git.isolated()`: every `--self-test` runs isolated (backlog #382)."""
    import fixture_git
    with fixture_git.isolated():
        return _self_test_body()


def _self_test_body() -> int:
    import tempfile as _tf
    cases = failures = 0

    def case(name, got, want):
        nonlocal cases, failures
        cases += 1
        if got != want:
            failures += 1
            print(f"  [FAIL] {name}\n    got:  {got!r}\n    want: {want!r}")

    # ── the grammar ──────────────────────────────────────────────────────────────────────────
    case("a shipped declaration parses", parse_status("**Status:** ✅ shipped"), ("shipped", None))
    case("an obsolete declaration parses",
         parse_status("**Status:** ⛔ obsolete — the thread, not the question"), ("obsolete", None))
    case("a parked declaration parses",
         parse_status("**Status:** ⏸️ parked behind backlog #117"), ("parked", None))
    # ⚠ THE VARIATION SELECTOR IS INVISIBLE IN AN EDITOR, so both spellings must parse or the rule
    # becomes a trap. U+23F8 bare and U+23F8+U+FE0F are the same character to a reader.
    case("...and the BARE pause marker parses identically, selector or not",
         (parse_status("**Status:** ⏸ parked")[0], parse_status("**Status:** ⏸️ parked")[0]),
         ("parked", "parked"))
    # ⛔⛔ THE CASE ABOVE PASSED FOR AN AMBIENT REASON AND A MUTATION PROVED IT. `rest[0]` is ONE
    # character, so a selector is never part of the marker — `_norm` is a no-op there and both
    # spellings parsed with it REMOVED. Where it is load-bearing is the WORD after an alive
    # marker: `🟠️ needs-you` leaves the selector glued to the front of `needs-you`, which then
    # matches nothing. This is the input that actually exercises it.
    case("⭐ a selector after the ALIVE marker is stripped, which is where _norm is load-bearing",
         parse_status("**Status:** 🟠️ needs-you — a decision waits"), ("needs-you", None))
    case("a current declaration parses", parse_status("**Status:** 🟠 current"), ("current", None))
    case("⭐ needs-you is its OWN state, not a synonym for current",
         parse_status("**Status:** 🟠 needs-you — one yes/no"), ("needs-you", None))
    # ⛔ THE DISCRIMINATING NEGATIVE. Without it this is indistinguishable from accepting any 🟠.
    case("⛔ ...so a bare 🟠 is REFUSED, because it cannot say which of the two it is",
         parse_status("**Status:** 🟠 alive and well")[1],
         "🟠 is ambiguous on its own — follow it with current or needs-you "
         "('needs-you' when a DECISION waits on the human)")
    case("an absent line is ABSENT, not malformed — the caller judges",
         parse_status("# T\n\nno status here"), (None, None))
    case("an empty declaration is malformed and names the vocabulary",
         "is empty" in (parse_status("**Status:**   ")[1] or ""), True)
    case("a non-marker first character is refused by its own repr",
         "starts with 'D'" in (parse_status("**Status:** DRAFT")[1] or ""), True)
    # ⚠ MEASURED: 6 vocabularies were already in use (CONVERGED/HIGH/APPROVED/DRAFT/BOTH/GATED).
    # Each must be REFUSED rather than guessed at, or the page renders a word it cannot map.
    case("...and every vocabulary already in the corpus is refused rather than guessed",
         [parse_status(f"**Status:** {w}")[0]
          for w in ("CONVERGED", "HIGH", "APPROVED", "DRAFT", "BOTH", "GATED")],
         [None] * 6)
    case("prose after the marker is free, and does not change the state",
         parse_status("**Status:** ✅ shipped — PR #303, live in CI since 2026-09-15"),
         ("shipped", None))
    # ⚠ The window is bounded for the same reason check-anchors bounds its own: a status a reader
    # cannot find is not a status.
    case("a declaration BELOW the window is not found, so it cannot hide in a long document",
         parse_status("\n" * HEAD_LINES + "**Status:** ✅ shipped"), (None, None))
    case("...and one ON the last line of the window IS found, so the bound is not off by one",
         parse_status("\n" * (HEAD_LINES - 1) + "**Status:** ✅ shipped"), ("shipped", None))
    case("the marker set is PINNED to a literal, so adding or reordering a state reddens by name",
         sorted(STATES.items()),
         sorted({"✅": "shipped", "🟠": "current", "⏸": "parked", "⛔": "obsolete"}.items()))
    case("the alive words are pinned too", ALIVE_WORDS, ("current", "needs-you"))

    # ── the verdict ──────────────────────────────────────────────────────────────────────────
    _armed = ("armed-anchor",)
    _ok = {"rel": "docs/a.md", "name": "a.md", "anchor": "armed-anchor",
           "state": "shipped", "why": None}
    case("a declared document under an armed anchor passes",
         verdict([_ok], _armed)[0], 0)
    case("⭐ a BLANK document under an ARMED anchor FAILS, and the message names the file",
         (verdict([{**_ok, "state": None}], _armed)[0],
          "docs/a.md" in "\n".join(verdict([{**_ok, "state": None}], _armed)[1])),
         (1, True))
    # ⚠ ADJACENT: the same blank document under an UNARMED anchor must pass — that is the whole
    # point of arming, and without this case the feature is indistinguishable from a 198-file gate.
    case("...while the SAME blank document under an UNARMED anchor passes, which is what arming IS",
         verdict([{**_ok, "state": None, "anchor": "other"}], _armed)[0], 0)
    case("...and it is COUNTED and reported, so an unarmed blank is visible rather than silent",
         "1 document(s) under UNARMED anchors declare nothing" in
         "\n".join(verdict([{**_ok, "state": None, "anchor": "other"}], _armed)[1]), True)
    # ⛔⛔ REVERSED ON THE FIRST LIVE RUN. This case used to assert that a malformed declaration
    # fails ANYWHERE — and that refused 78 documents whose `**Status:**` carries the design's
    # review state in legitimate prose ("Approved", "v7 — CONVERGED"). A different field under the
    # same name is not a broken version of this one, and failing them is backlog #56 (a gate red
    # from birth gets switched off).
    case("⛔ a non-marker status under an UNARMED anchor is NOT a failure — it is another field",
         verdict([{**_ok, "state": None, "why": "bad marker", "anchor": "other"}], _armed)[0], 0)
    # ⚠ ADJACENT, and this is the pair that makes arming mean something: the SAME malformed line
    # inside an ARMED anchor IS a defect, because there the document claims this vocabulary.
    case("⛔ ...while the SAME malformed line inside an ARMED anchor fails, naming the file",
         (verdict([{**_ok, "state": None, "why": "bad marker"}], _armed)[0],
          "docs/a.md" in "\n".join(verdict([{**_ok, "state": None, "why": "bad marker"}],
                                            _armed)[1])),
         (1, True))
    case("the passing line reports the per-state counts a reader can act on",
         "1 shipped" in "\n".join(verdict([_ok], _armed)[1]), True)
    case("two states are both counted, so the tally is not a constant",
         "1 current, 1 shipped" in "\n".join(verdict(
             [_ok, {**_ok, "rel": "docs/b.md", "state": "current"}], _armed)[1]), True)
    case("a document with NO anchor and no status is not demanded of",
         verdict([{**_ok, "anchor": None, "state": None}], _armed)[0], 0)
    # ⛔ `armed` VARIED, not exempted — `check-fixture-variation` found every call site passing
    # the same tuple, which leaves every clause that reads it unguarded. An EMPTY armed set is the
    # distinct input that matters: it proves ARMING is what produces the failure, rather than
    # anything about the document. Same blank document, two armed sets, two verdicts.
    case("⭐ arming is what fails a blank document: the SAME input passes with nothing armed",
         (verdict([{**_ok, "state": None}], _armed)[0],
          verdict([{**_ok, "state": None}], ())[0]),
         (1, 0))

    # ── main() over a constructed world ──────────────────────────────────────────────────────
    with _tf.TemporaryDirectory() as _d:
        _r = Path(_d)
        (_r / "docs" / "superpowers" / "specs").mkdir(parents=True)
        (_r / "docs" / "superpowers" / "plans").mkdir(parents=True)
        (_r / "docs" / "superpowers" / "specs" / "2026-01-01-x-design.md").write_text(
            "# X\n\n> **Anchor:** `armed-anchor`\n\n**Status:** ✅ shipped\n")
        case("main() exits 0 over a world whose armed document declares a state",
             main([], repo=_r, armed=("armed-anchor",)), 0)
        (_r / "docs" / "superpowers" / "plans" / "2026-01-01-x.md").write_text(
            "# X plan\n\n> **Anchor:** `armed-anchor`\n\nno status\n")
        case("...and exits 1 once an armed document declares nothing",
             main([], repo=_r, armed=("armed-anchor",)), 1)
        case("...and 0 again when that anchor is not armed, over the SAME tree",
             main([], repo=_r, armed=("other",)), 0)
    with _tf.TemporaryDirectory() as _d2:
        case("an empty tree is CANNOT RUN (2), never a pass — nothing was checked",
             main([], repo=Path(_d2), armed=("armed-anchor",)), 2)
    # ⛔ AN UNREADABLE DOCUMENT IS CANNOT RUN, NOT AN ABSENT STATUS. Silence there would be
    # indistinguishable from a clean result, which is this repository's loudest rule.
    with _tf.TemporaryDirectory() as _d3:
        _r3 = Path(_d3)
        (_r3 / "docs" / "superpowers" / "specs").mkdir(parents=True)
        # ⛔ A READABLE SIBLING IS REQUIRED, and a mutation proved why: with only the unreadable
        # document present, skipping it emptied the corpus and `main()` returned 2 through the
        # "no documents" branch — the right code for the wrong reason, so the case passed with
        # the read-failure path deleted.
        (_r3 / "docs" / "superpowers" / "specs" / "2026-01-01-ok-design.md").write_text(
            "# OK\n\n> **Anchor:** `armed-anchor`\n\n**Status:** ✅ shipped\n")
        _bad = _r3 / "docs" / "superpowers" / "specs" / "2026-01-01-y-design.md"
        _bad.write_text("# Y\n\n> **Anchor:** `armed-anchor`\n\n**Status:** ✅ shipped\n")
        _bad.chmod(0o000)
        try:
            case("an UNREADABLE document is CANNOT RUN (2), never an absent status",
                 main([], repo=_r3, armed=("armed-anchor",)), 2)
        finally:
            _bad.chmod(0o644)

    # ⛔ THE PAGE MUST IMPORT THIS GRAMMAR, NOT RESTATE IT. If the generator grows its own copy the
    # two drift and the gate starts passing documents the page cannot render.
    _gen = (REPO / "scripts" / "gen-goals-page.py")
    if _gen.is_file():
        _src = _gen.read_text()
        case("the goals page IMPORTS this grammar rather than re-implementing it",
             ("check-goal-status" in _src and "parse_status" in _src), True)
        case("...and does not carry its own copy of the marker table",
             '"✅": "shipped"' in _src, False)

    print(f"\n{cases - failures}/{cases} self-test cases passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
