#!/usr/bin/env python3
"""Refuse an `AskUserQuestion` card that does not follow `docs/portable-practices.md` §19.

    python3 scripts/check-selection-card.py < tool-input.json
    python3 scripts/check-selection-card.py --self-test  # 24 cases

WHY THIS FILE EXISTS
--------------------
§19 has specified the shape of an option list since 2026-09-04: every option carries a LETTER, a
label, a rationale and a trade-off; exactly one is marked *Recommended* with its reason; the last
option is always *"I have a question about these"*; and the question text names the axis.

MEASURED 2026-09-10, which is the entire justification. Three cards in one session:

    card 1 (which slice to pick)   recommendation ✓   letters ✗   question-exit ✗
    card 2 (two decisions)         recommendation ✗   letters ✗   question-exit ✗
    card 3 (after two corrections) recommendation ✓   letters ✓   question-exit ✓

The rule was not missing. It was in §19, and restated in two memory files, the whole time — and it
was reconstructed from recall at the moment of use instead of read. The user's words: *"you seem to
deviate proven style. I'd like to have this style recorded and followed."* It was already recorded.
Recording was not the gap.

This is the project's own §7 applied to its own §19: **before adding a rule, ask whether it can be a
script.** Three of §19's six clauses are exactly decidable from the tool input, so they are decided
here rather than remembered.

⛔ WHAT THIS DOES NOT CHECK, STATED RATHER THAN IMPLIED
-------------------------------------------------------
A guard that covers half a rule and reads as covering all of it is a hazard this repo has paid for
more than once, so the uncovered half is named here and in the block message:

  * **whether two options produce DIFFERENT WORK.** This is the defect that caused §19 to be
    written — two of four options were the same action in different words — and it is not decidable
    from text. A card can pass every check here and still offer a fake choice.
  * **whether the question text names the AXIS.** Detectable only by heuristics that would fire on
    healthy cards, and a detector people learn to skip is worse than none (backlog #92).
  * **whether the rationale is TRUE.** Only that something was written. The floor below is a floor
    against a bare label, not a test for reasoning.

FAILS IF
--------
  * an option label does not begin `A — ` / `B — ` / `C — ` (any dash, one letter, one space);
  * the letters are not consecutive from A, in order;
  * the number of options marked `(Recommended)` is wrong — exactly one for a single-select card, at
    least one for a multi-select one — or the recommended option is not FIRST;
  * the last option is not the question-shaped exit;
  * an option other than that exit carries a description shorter than `MIN_DESCRIPTION` characters;
  * the input is not readable as an `AskUserQuestion` payload -> exit 2, CANNOT RUN, never a pass.
"""

from typing import Any, Callable, Sequence

import argparse
import json
import re
import sys

# One capital, one dash of any of the three spellings a person actually types, one space. Strict on
# the letter and loose on the dash: blocking a card because someone typed a hyphen instead of an em
# dash would be the cry-wolf failure this guard is supposed to avoid.
LETTER = re.compile(r"^([A-Z])\s*[—–-]\s+\S")
RECOMMENDED = "(Recommended)"
QUESTION_EXIT = re.compile(r"i\s+have\s+a\s+question", re.I)
# A floor against a BARE LABEL, not a test for rationale. §19's own argument is that an option with
# no stated cost is either obviously right (so it should not have been asked) or not yet thought
# through (so it should not have been offered). 40 characters cannot tell those apart from a real
# rationale — it can only tell them from nothing at all, which is what it is for.
MIN_DESCRIPTION = 40


def card_problems(questions: Sequence[dict]) -> list[str]:
    """PURE. Every §19 clause that is exactly decidable, over one AskUserQuestion payload."""
    problems: list[str] = []
    if not questions:
        return ["CANNOT RUN — the payload carries no questions at all."]

    for qi, q in enumerate(questions, 1):
        where = f"question {qi} ({str(q.get('header') or q.get('question', ''))[:40]!r})"
        options = q.get("options") or []
        if len(options) < 2:
            problems.append(f"{where}: {len(options)} option(s) — a choice needs at least two.")
            continue

        labels = [str(o.get("label", "")) for o in options]

        # ── the letter prefix, and that the letters actually run A, B, C … ──────────────────────
        for li, label in enumerate(labels):
            if not LETTER.match(label):
                problems.append(
                    f"{where}: option {li + 1} is not lettered — {label[:48]!r}. "
                    f"§19: every option carries a letter, e.g. 'A — Keep the current shape'.")
        matched = [LETTER.match(label) for label in labels]
        if all(matched):
            got = [m.group(1) for m in matched if m]
            want = [chr(ord("A") + i) for i in range(len(got))]
            if got != want:
                problems.append(f"{where}: letters run {''.join(got)}, expected {''.join(want)}.")

        # ── exactly one recommendation, and it goes FIRST ───────────────────────────────────────
        marked = [i for i, label in enumerate(labels) if RECOMMENDED in label]
        multi = bool(q.get("multiSelect"))
        if not marked:
            problems.append(
                f"{where}: nothing is marked {RECOMMENDED}. §19: withholding a recommendation is "
                f"not neutrality, it is handing over an unfinished analysis.")
        elif not multi and len(marked) > 1:
            problems.append(
                f"{where}: {len(marked)} options marked {RECOMMENDED} on a single-select card; "
                f"§19 says exactly one.")
        elif marked[0] != 0:
            problems.append(
                f"{where}: the recommended option is #{marked[0] + 1}, not first. It goes first so "
                f"the reader meets the answer before the alternatives.")

        # ── the question-shaped exit ────────────────────────────────────────────────────────────
        if not QUESTION_EXIT.search(labels[-1]):
            problems.append(
                f"{where}: the last option is {labels[-1][:48]!r}, not a question-shaped exit. "
                f"§19: add '{chr(ord('A') + len(labels))} — I have a question about these'. "
                f"A form with no way to ask turns every clarification into a rejected choice.")

        # ── a floor against the bare label ──────────────────────────────────────────────────────
        for li, o in enumerate(options[:-1]):
            desc = str(o.get("description", "") or "")
            if len(desc.strip()) < MIN_DESCRIPTION:
                problems.append(
                    f"{where}: option {li + 1} carries {len(desc.strip())} characters of "
                    f"description. §19: each option states its rationale AND its trade-off — what "
                    f"it costs or gives up.")
    return problems


def payload_of(raw: str) -> list[dict]:
    """The questions, out of either a hook envelope or a bare tool input. Raises on anything else —
    a payload this cannot read is CANNOT RUN, and CANNOT RUN is a failure."""
    data: Any = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError(f"expected a JSON object, got {type(data).__name__}")
    # PreToolUse wraps it; a direct invocation does not. Accept both rather than making the caller
    # unwrap — the two shapes have appeared in this repo's hooks already.
    wrapped = data.get("tool_input")
    inner: dict = wrapped if isinstance(wrapped, dict) else data
    questions = inner.get("questions")
    if not isinstance(questions, list):
        raise ValueError("no `questions` list in the payload")
    return [q for q in questions if isinstance(q, dict)]


def self_test() -> int:
    cases: list[tuple[str, Callable[[], object]]] = []

    def case(name, fn):
        cases.append((name, fn))

    def card(labels, descs=None, multi=False, question="Which one? A/B differ in scope."):
        descs = descs or ["x" * 60] * len(labels)
        return [dict(question=question, header="H", multiSelect=multi,
                     options=[dict(label=lb, description=d) for lb, d in zip(labels, descs)])]

    GOOD = ["A — Do the thing (Recommended)", "B — Do a different thing",
            "C — I have a question about these"]

    case("a card following §19 passes", lambda: card_problems(card(GOOD)) == [])
    case("an unlettered option is refused",
         lambda: any("not lettered" in p for p in card_problems(
             card(["Do the thing (Recommended)", "B — Other", "C — I have a question"]))))
    case("a hyphen is accepted, not just an em dash",
         lambda: card_problems(card(["A - Do it (Recommended)", "B - Other",
                                     "C - I have a question about these"])) == [])
    case("an en dash is accepted too",
         lambda: card_problems(card(["A – Do it (Recommended)", "B – Other",
                                     "C – I have a question about these"])) == [])
    case("letters out of order are refused",
         lambda: any("letters run" in p for p in card_problems(
             card(["A — One (Recommended)", "C — Two", "D — I have a question"]))))
    case("a missing recommendation is refused",
         lambda: any("nothing is marked" in p for p in card_problems(
             card(["A — One", "B — Two", "C — I have a question about these"]))))
    case("two recommendations on a single-select card are refused",
         lambda: any("2 options marked" in p for p in card_problems(
             card(["A — One (Recommended)", "B — Two (Recommended)",
                   "C — I have a question about these"]))))
    # ⚠ On a multi-select card "exactly one" is the wrong rule — several can legitimately be
    # advised together — so the clause relaxes to "at least one" rather than being switched off.
    case("two recommendations on a MULTI-select card are allowed",
         lambda: card_problems(card(["A — One (Recommended)", "B — Two (Recommended)",
                                     "C — I have a question about these"], multi=True)) == [])
    case("a multi-select card with NO recommendation is still refused",
         lambda: any("nothing is marked" in p for p in card_problems(
             card(["A — One", "B — Two", "C — I have a question"], multi=True))))
    case("a recommendation that is not first is refused",
         lambda: any("not first" in p for p in card_problems(
             card(["A — One", "B — Two (Recommended)", "C — I have a question about these"]))))
    case("a missing question-exit is refused",
         lambda: any("question-shaped exit" in p for p in card_problems(
             card(["A — One (Recommended)", "B — Two", "C — Three"]))))
    case("the question-exit is matched loosely, not by exact wording",
         lambda: card_problems(card(["A — One (Recommended)", "B — Two",
                                     "C — I Have A Question, actually several"])) == [])
    case("a bare label is refused",
         lambda: any("characters of description" in p for p in card_problems(
             card(GOOD, descs=["short", "x" * 60, "x" * 60]))))
    # ⚠ THE EXIT OPTION IS EXEMPT from the floor: "say what is unclear" needs no trade-off, and
    # demanding one would teach the writer to pad it.
    case("the question-exit option needs no rationale",
         lambda: card_problems(card(GOOD, descs=["x" * 60, "x" * 60, "ask"])) == [])
    case("a one-option card is refused",
         lambda: any("at least two" in p for p in card_problems(card(["A — Only one"]))))
    case("an empty payload is CANNOT RUN, not a pass",
         lambda: card_problems([]) and "CANNOT RUN" in card_problems([])[0])
    case("every question in a multi-question payload is checked",
         lambda: len(card_problems(card(GOOD) + card(["A — One", "B — Two", "C — Three"]))) == 2)
    case("the problem names WHICH question, so a two-question card is actionable",
         lambda: all(p.startswith("question ") for p in card_problems(
             card(["A — One", "B — Two", "C — Three"]))))

    case("a PreToolUse envelope is unwrapped",
         lambda: payload_of(json.dumps({"tool_name": "AskUserQuestion",
                                        "tool_input": {"questions": card(GOOD)}}))
         == card(GOOD))
    case("a bare tool input is accepted too",
         lambda: payload_of(json.dumps({"questions": card(GOOD)})) == card(GOOD))
    case("a payload with no questions list RAISES rather than passing",
         lambda: _raises(lambda: payload_of(json.dumps({"tool_input": {}})), ValueError))
    case("a JSON array RAISES rather than passing",
         lambda: _raises(lambda: payload_of("[]"), ValueError))
    case("malformed JSON RAISES rather than passing",
         lambda: _raises(lambda: payload_of("{not json"), json.JSONDecodeError))
    # ⭐ The clause this guard does NOT cover, pinned so nobody reads its silence as coverage.
    case("two options that are the SAME WORK pass — this guard cannot see that",
         lambda: card_problems(card(["A — Merge both, in order (Recommended)",
                                     "B — Merge both, review after",
                                     "C — I have a question about these"])) == [])

    failed = 0
    for name, fn in cases:
        why = ""
        try:
            ok = bool(fn())
        except Exception as exc:                                   # noqa: BLE001 - report, not hide
            ok, why = False, repr(exc)
        if ok:
            print(f"  ok     {name}")
        else:
            print(f"  [FAIL] {name}")
            if why:
                print(f"    raised: {why}")
        failed += not ok
    print(f"\n{len(cases) - failed}/{len(cases)} passed")
    return 1 if failed else 0


def _raises(fn, exc: type[BaseException]) -> bool:
    try:
        fn()
    except exc:
        return True
    except Exception:                                              # noqa: BLE001
        return False
    return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()

    raw = sys.stdin.read()
    try:
        questions = payload_of(raw)
    except Exception as exc:                                       # noqa: BLE001
        print(f"CANNOT RUN — {exc}. Treat this as NOT CHECKED, never as a pass.", file=sys.stderr)
        return 2

    problems = card_problems(questions)
    if not problems:
        return 0
    for p in problems:
        print(f"  ✗ {p}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
