#!/usr/bin/env python3
"""Refuse an `AskUserQuestion` card that does not follow `docs/portable-practices.md` §19.

    python3 scripts/check-selection-card.py < tool-input.json
    python3 scripts/check-selection-card.py --self-test  # 42 cases

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
import subprocess
import sys

# One capital, one dash of any of the three spellings a person actually types, one space. Strict on
# the letter and loose on the dash: blocking a card because someone typed a hyphen instead of an em
# dash would be the cry-wolf failure this guard is supposed to avoid.
# One capital, then a dash of any of the three spellings a person actually types, then AT LEAST ONE
# SPACE — the trailing space is required and the leading one is not, which the first docstring got
# backwards (r1 M-3). Strict on the letter, loose on the dash: refusing a card over a hyphen would be
# the cry-wolf failure this guard exists to avoid.
LETTER = re.compile(r"^([A-Z])\s*[—–-]\s+\S")
# ⚠ ANCHORED AT THE END, and the two halves of r1 wanted opposite things here. Codex: a bare
# substring test made prose ABOUT the marker into a marker — `A — Explain what (Recommended) means`
# was read as a recommendation. Claude: an exact-literal test refused §19's OWN phrasing, since §19
# says "exactly one is marked Recommended, WITH ITS REASON", and `(Recommended — it is reversible)`
# was reported as *no recommendation at all*. Requiring the parenthesis to CLOSE the label satisfies
# both: a reason may ride inside it, prose in the middle of a label cannot pose as one. Trailing
# markdown emphasis is tolerated because `**(Recommended)**` already passed and removing that would
# be a regression nobody asked for.
RECOMMENDED = re.compile(r"\(\s*recommended\b[^)]*\)[\s*_`]*$", re.I)
QUESTION_EXIT = re.compile(r"i\s+have\s+a\s+question", re.I)
# A floor against a BARE LABEL, not a test for rationale. §19's own argument is that an option with
# no stated cost is either obviously right (so it should not have been asked) or not yet thought
# through (so it should not have been offered). 40 characters cannot tell those apart from a real
# rationale — it can only tell them from nothing at all, which is what it is for.
MIN_DESCRIPTION = 40
# The same floor for a description written without spaces — see `card_problems`.
MIN_DESCRIPTION_DENSE = 15
# `AskUserQuestion` accepts 2–4 options. NOT a style choice: it is the tool's schema, and the block
# message has to respect it or it prescribes a repair that fails (r1 Blocking).
MAX_OPTIONS = 4


def card_problems(questions: Sequence[dict]) -> list[str]:
    """PURE. Every §19 clause that is exactly decidable, over one AskUserQuestion payload."""
    problems: list[str] = []
    if not questions:
        return ["CANNOT RUN — the payload carries no questions at all."]

    for qi, q in enumerate(questions, 1):
        where = f"question {qi} ({str(q.get('header') or q.get('question', ''))[:40]!r})"
        options = q.get("options") or []
        # ⚠ THREE, not two (r1 M-1). The floor was written before the question-exit became
        # mandatory; with it, a two-option card offers exactly ONE course of action — a
        # confirmation dialog wearing a selection card, which is the defect §19 is about.
        if len(options) < 3:
            problems.append(
                f"{where}: {len(options)} option(s). With the mandatory question-exit that leaves "
                f"{max(0, len(options) - 1)} real choice(s) — §19 wants a decision, not a confirm.")
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
        marked = [i for i, label in enumerate(labels) if RECOMMENDED.search(label)]
        multi = bool(q.get("multiSelect"))
        if not marked:
            problems.append(
                f"{where}: nothing is marked (Recommended). §19: withholding a recommendation is "
                f"not neutrality, it is handing over an unfinished analysis.")
        elif not multi and len(marked) > 1:
            problems.append(
                f"{where}: {len(marked)} options marked (Recommended) on a single-select card; "
                f"§19 says exactly one.")
        elif not multi and marked[0] != 0:
            # ⚠ SINGLE-SELECT ONLY (r1 M-5). The reason for "first" is that the reader meets the
            # answer before the alternatives — which does not survive an answer that is a SET. On a
            # multi-select card the first slot is often "none of these", or the options carry an
            # intrinsic order, and demanding a recommendation there is an arbitrary line.
            problems.append(
                f"{where}: the recommended option is #{marked[0] + 1}, not first. It goes first so "
                f"the reader meets the answer before the alternatives.")

        # ── the question-shaped exit ────────────────────────────────────────────────────────────
        if not QUESTION_EXIT.search(labels[-1]):
            # ⛔ THE ADVICE HAS TO BE POSSIBLE, and the first version's was not (r1 Blocking).
            # `AskUserQuestion` accepts 2–4 options. Measured over 49 real historical questions:
            # 29 already use all four slots, and 22 of those were being told to "add a fifth" — an
            # instruction the schema refuses, so following it produces a SECOND failure and leaves
            # the reader to work out unaided that the repair was to REPLACE, not append. A guard
            # that blocks correctly and then misdirects the repair is worse at the moment of use
            # than the prose it replaced, because prose never asserted a wrong next step.
            fix = (f"add '{chr(ord('A') + len(labels))} — I have a question about these'"
                   if len(labels) < MAX_OPTIONS else
                   f"REPLACE option {len(labels)} with "
                   f"'{chr(ord('A') + len(labels) - 1)} — I have a question about these' — the tool "
                   f"accepts {MAX_OPTIONS} options at most, so the exit costs you a choice")
            problems.append(
                f"{where}: the last option is {labels[-1][:48]!r}, not a question-shaped exit. "
                f"§19: {fix}. "
                f"A form with no way to ask turns every clarification into a rejected choice.")

        # ── a floor against the bare label ──────────────────────────────────────────────────────
        for li, o in enumerate(options[:-1]):
            desc = str(o.get("description", "") or "").strip()
            # ⚠ A DENSE SCRIPT CARRIES MORE PER CHARACTER (r1 M-4). 24 CJK characters hold roughly
            # what 60 ASCII ones do, rationale and trade-off included, and were being refused. The
            # floor's own claim is about INFORMATION, not `len()`, so a description with no spaces
            # in it is measured against the lower floor rather than turned away.
            floor = MIN_DESCRIPTION if len(desc.split()) > 1 else MIN_DESCRIPTION_DENSE
            if len(desc) < floor:
                problems.append(
                    f"{where}: option {li + 1} carries {len(desc)} characters of "
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
    case("the question-exit ignores case and trailing words",
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
         lambda: any("real choice" in p for p in card_problems(card(["A — Only one"]))))
    # ⭐ r1 M-1. Two options plus the mandatory exit is ONE course of action.
    case("a card whose only alternative is the exit is refused",
         lambda: any("real choice" in p for p in card_problems(
             card(["A — Ship it (Recommended)", "B — I have a question about these"]))))

    # ⭐⭐ r1 BLOCKING (Claude), measured over 49 real questions: 29 already use all four option
    # slots, and 22 of those were told to add a fifth — which the tool's schema refuses. The advice
    # has to change shape at the ceiling, or following it produces a second, different failure.
    def _exit_advice(n: int) -> str:
        labels = [f"{chr(ord('A') + i)} — Option {i}" for i in range(n)]
        labels[0] += " (Recommended)"
        return " ".join(card_problems(card(labels)))

    case("below the ceiling the advice is to ADD the exit",
         lambda: "add 'D — I have a question" in _exit_advice(3))
    case("AT the ceiling the advice is to REPLACE, because the tool takes four options",
         lambda: "REPLACE option 4" in _exit_advice(4)
         and "add 'E" not in _exit_advice(4))

    # ⭐ r1: Codex's High and Claude's M-2 wanted this token looser and stricter respectively.
    # Anchoring at the END of the label is what satisfies both.
    case("a reason may ride inside the marker — §19 asks for one",
         lambda: card_problems(card(["A — Ship it (Recommended — it is reversible)",
                                     "B — Wait", "C — I have a question about these"])) == [])
    case("the marker is case-insensitive",
         lambda: card_problems(card(["A — Ship it (recommended)", "B — Wait",
                                     "C — I have a question about these"])) == [])
    case("markdown emphasis around the marker still counts",
         lambda: card_problems(card(["A — Ship it **(Recommended)**", "B — Wait",
                                     "C — I have a question about these"])) == [])
    case("prose ABOUT the marker, mid-label, is not a recommendation",
         lambda: any("nothing is marked" in p for p in card_problems(
             card(["A — Explain what (Recommended) means to a reader", "B — Use plainer wording",
                   "C — I have a question about these"]))))

    # ⭐ r1 M-5. "First" exists so the reader meets the answer before the alternatives; that reason
    # does not survive an answer which is a SET.
    case("on a MULTI-select card the recommendation need not be first",
         lambda: card_problems(card(["A — Neither of these", "B — Do it (Recommended)",
                                     "C — I have a question about these"], multi=True)) == [])
    case("on a single-select card it must still be first",
         lambda: any("not first" in p for p in card_problems(
             card(["A — Neither", "B — Do it (Recommended)",
                   "C — I have a question about these"]))))

    # ⭐ r1 M-4. 24 CJK characters carry what ~60 ASCII ones do; the floor's claim is about
    # information, not len().
    case("a dense description with no spaces clears the lower floor",
         lambda: card_problems(card(GOOD, descs=["今すぐ出荷する。巻き戻せるがレビューを一回失う。",
                                                 "x" * 60, "ask"])) == [])
    case("a dense description that is still bare is refused",
         lambda: any("characters of description" in p for p in card_problems(
             card(GOOD, descs=["出荷", "x" * 60, "ask"]))))
    # ⭐ r1 L-2. The manifest mutated the floor to 0, which the 5-character fixture kills; the
    # NUMBER 40 — what §19's floor actually claims — was pinned only above 5. A boundary pair pins
    # it, and pins the `.strip()` at the same time.
    case("the floor is 40 exactly — 39 is refused, 40 is accepted",
         lambda: any("characters of description" in p
                     for p in card_problems(card(GOOD, descs=["a b" + "x" * 36, "x" * 60, "ask"])))
         and card_problems(card(GOOD, descs=["a b" + "x" * 37, "x" * 60, "ask"])) == [])
    case("whitespace does not count toward the floor",
         lambda: any("characters of description" in p for p in card_problems(
             card(GOOD, descs=["a b" + " " * 60, "x" * 60, "ask"]))))
    case("an empty payload is CANNOT RUN, not a pass",
         lambda: card_problems([]) and "CANNOT RUN" in card_problems([])[0])
    case("every question in a multi-question payload is checked",
         lambda: len(card_problems(card(GOOD) + card(["A — One", "B — Two", "C — Three"]))) == 2)
    # ⚠ `bool(probs) and` — r1 L-1. Without it, `all([])` is True and the case stayed GREEN with
    # `card_problems` neutered to `return []`: an assertion that deleting the subject satisfies.
    case("the problem names WHICH question, so a two-question card is actionable",
         lambda: (lambda probs: bool(probs) and all(p.startswith("question ") for p in probs))(
             card_problems(card(["A — One", "B — Two", "C — Three"]))))

    case("a PreToolUse envelope is unwrapped",
         lambda: payload_of(json.dumps({"tool_name": "AskUserQuestion",
                                        "tool_input": {"questions": card(GOOD)}}))
         == card(GOOD))
    case("a non-dict entry in the questions list is dropped, not passed on",
         lambda: payload_of(json.dumps({"questions": ["not a question", {"header": "H"}]}))
         == [{"header": "H"}])
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

    # ⭐⭐ r1 H-2. The hook reads exactly ONE thing from this script — its exit code — and nothing
    # executed `main()`. `return 2` -> `return 0` left 24/24 green, so the manifest was green, so CI
    # was green, while every malformed card was admitted. The fail-open one layer OUT of the one the
    # manifest already guarded.
    def _rc_for(raw: str) -> int:
        return subprocess.run([sys.executable, __file__], input=raw,
                              capture_output=True, text=True).returncode

    case("a bad card EXITS 2 — the exit code is all the hook can see",
         lambda: _rc_for(json.dumps({"questions": card(["A — One", "B — Two", "C — Three"])})) == 2)
    case("a good card exits 0",
         lambda: _rc_for(json.dumps({"questions": card(GOOD)})) == 0)
    case("an unreadable payload exits 2, never 0",
         lambda: _rc_for("{not json") == 2 and _rc_for("") == 2)
    # ⭐ r1 L-5. A malformed option shape raised through `main` and rendered a Python traceback as
    # the body of the refusal panel. Still fail-closed, now with the CANNOT RUN sentence instead.
    case("a malformed option shape is CANNOT RUN, not a traceback",
         lambda: _rc_for(json.dumps({"questions": [{"header": "H", "options": "nope"}]})) == 2)

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

    try:
        problems = card_problems(questions)
    except Exception as exc:                                       # noqa: BLE001
        # ⚠ r1 L-5. `options` as a dict, or a list of strings, raised through here and rendered a
        # Python traceback as the body of the refusal panel. The DIRECTION was already right —
        # fail closed — so only the message changes.
        print(f"CANNOT RUN — the card could not be read ({exc!r}). Treat this as NOT CHECKED.",
              file=sys.stderr)
        return 2
    if not problems:
        return 0
    for p in problems:
        print(f"  ✗ {p}", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
